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
            f"[{i}] [{a['score_total']:.1f}] "
            f"Title: {a['title']}\n"
            f"    Source: {a['source_name']} | {a['published']}\n"
            f"    Summary: {a['summary'][:200]}\n"
        )

    prompt = f"""从以下 {len(candidates)} 篇候选文章中选出最重要的 {count} 篇进行中文翻译和解读。

要求：
1. 筛选最值得关注的 AI 新闻/论文
2. title_cn: 中文标题（保留核心技术名词英文，20字以内）
3. summary_cn: 中文摘要（60-100字，突出核心信息）
4. why_it_matters: 一句话（30字内），说明对 AI 从业者的实际影响或意义

返回严格 JSON 数组格式：
[
  {{"id": <article_id>, "title_cn": "...", "summary_cn": "...", "why_it_matters": "..."}},
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
