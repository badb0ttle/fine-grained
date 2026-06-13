#!/usr/bin/env python3
"""Stage 4: Curator — select top articles for LLM curation and apply results."""

import json
from datetime import datetime, timezone

from . import get_db


def get_candidates(limit: int = 20) -> list[dict]:
    """Get top-scored articles that haven't been curated yet."""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, link, summary, published, source_name, category,
               score_total, score_authority, score_timeliness, score_depth, score_relevance
        FROM articles
        WHERE score_total > 0
        ORDER BY score_total DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_curation_prompt(candidates: list[dict], count: int = 10) -> str:
    """Generate a prompt for the LLM to curate articles.

    The LLM should return a JSON array with curated entries containing
    title_cn, summary_cn, and an optional why_it_matters field.
    """
    articles_text = []
    for i, a in enumerate(candidates, 1):
        articles_text.append(
            f"[{i}] [DB ID: {a['id']}] [{a['score_total']:.1f}] "
            f"Title: {a['title']}\n"
            f"    Source: {a['source_name']} | {a['published']}\n"
            f"    Summary: {a['summary'][:200]}\n"
        )

    prompt = f"""你是资深 AI 技术编辑。从以下 {len(candidates)} 篇候选文章中选出最重要的 {count} 篇，写中文标题和摘要。

【筛选标准】
- 优先选有实际影响、可操作、反常识、或刚发布的新内容
- 跳过纯 PR 稿、泛泛而谈、重复已有共识的文章

【写作规范 — 严禁以下 AI 套话】
禁止使用这些词汇和句式：
- "在...方面" "不仅...而且..." "展现出..." "具有重要意义"
- "标志着..." "为...提供了..." "进一步..." "全面/深入/系统"
- "推动...发展" "实现了...突破" "引发...思考"

写作原则：
- 用口语化短句，像和朋友聊天那样写，不要论文腔
- 只说一件事，信息密度优先
- 技术名词保留英文（如 "RLHF" "LoRA"），不硬翻
- 标题要有信息量，不说废话。比如 "小型 LLM 在生物医学声明验证中的高效微调" 比 "一项关于小模型微调的研究" 好
- 禁止使用任何 emoji 表情符号

每条输出：
1. title_cn: ≤20字，信息量优先，技术名词保留英文
2. summary_cn: 40-80字，只讲核心发现+方法，不铺垫不总结
3. why_it_matters: ≤25字，说清楚对谁有什么实际影响

返回严格 JSON 数组（id 使用 DB ID）：
[
  {{"id": <DB ID>, "title_cn": "...", "summary_cn": "...", "why_it_matters": "..."}},
  ...
]

候选文章：
{chr(10).join(articles_text)}"""

    return prompt


def apply_curation(curated: list[dict]) -> dict:
    """Apply LLM curation results to the database.

    Args:
        curated: list of dicts with at least 'id', 'title_cn', 'summary_cn'
                 optionally 'why_it_matters'
    """
    conn = get_db()
    curated_at = datetime.now(timezone.utc).isoformat()
    updated = 0

    for item in curated:
        if "id" not in item:
            continue
        conn.execute("""
            UPDATE articles SET
            title_cn = ?,
            summary_cn = ?,
            why_it_matters = ?,
            curated = 1,
            curated_at = ?
            WHERE id = ?
        """, (
            item.get("title_cn", ""),
            item.get("summary_cn", ""),
            item.get("why_it_matters", ""),
            curated_at,
            item["id"]
        ))
        updated += 1

    # Update daily_stats
    date_str = datetime.now().strftime("%Y-%m-%d")
    conn.execute("""
        UPDATE daily_stats SET curated_count = ?
        WHERE date = ?
    """, (updated, date_str))

    conn.commit()
    conn.close()

    print(f"⭐ Curator: {updated} articles curated at {curated_at}")
    return {"curated": updated, "curated_at": curated_at}


def export_latest_json() -> dict:
    """Export curated articles as latest.json compatible format."""
    conn = get_db()

    # Get stats
    stats = conn.execute("""
        SELECT date, total_sources, successful_sources, total_articles, curated_count
        FROM daily_stats
        ORDER BY date DESC LIMIT 1
    """).fetchone()

    # Get curated articles
    rows = conn.execute("""
        SELECT title, link, summary, published, source_name, category,
               title_cn, summary_cn, why_it_matters, score_total
        FROM articles
        WHERE curated = 1
        ORDER BY score_total DESC
    """).fetchall()

    conn.close()

    articles = []
    for r in rows:
        a = {
            "title": r["title"],
            "link": r["link"],
            "summary": r["summary"],
            "published": r["published"],
            "source": r["source_name"],
            "category": r["category"],
            "title_cn": r["title_cn"],
            "summary_cn": r["summary_cn"],
        }
        if r["why_it_matters"]:
            a["why_it_matters"] = r["why_it_matters"]
        articles.append(a)

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "curated_at": datetime.now(timezone.utc).isoformat(),
        "total_sources": stats["total_sources"] if stats else 0,
        "successful_sources": stats["successful_sources"] if stats else 0,
        "total_articles": stats["total_articles"] if stats else 0,
        "curated_count": len(articles),
        "articles": articles,
    }

    return result


if __name__ == "__main__":
    candidates = get_candidates(20)
    print(f"📋 {len(candidates)} candidates ready for curation")
    if candidates:
        print(f"   Top: [{candidates[0]['score_total']:.1f}] {candidates[0]['title'][:60]}")
        prompt = get_curation_prompt(candidates[:5], 3)
        print(f"\n--- LLM Prompt Preview (first 300 chars) ---")
        print(prompt[:300])
