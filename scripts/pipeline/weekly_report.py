#!/usr/bin/env python3
"""Weekly Report — generate a prompt for LLM to write a weekly AI briefing."""

from datetime import datetime, timedelta

from . import get_db


def get_week_articles(days: int = 7) -> dict:
    """Get curated articles from the past N days for weekly analysis."""
    conn = get_db()
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # Top scored articles this week
    top = conn.execute("""
        SELECT title, title_cn, summary_cn, why_it_matters, source_name,
               category, score_total, published
        FROM articles
        WHERE score_total > 0 AND published >= ?
        ORDER BY score_total DESC
        LIMIT 50
    """, (since,)).fetchall()

    # Category breakdown
    cats = conn.execute("""
        SELECT category, COUNT(*) as cnt
        FROM articles
        WHERE score_total > 0 AND published >= ?
        GROUP BY category ORDER BY cnt DESC
    """, (since,)).fetchall()

    # Curated count
    curated = conn.execute("""
        SELECT COUNT(*) FROM articles
        WHERE curated = 1 AND curated_at >= ?
    """, (since,)).fetchone()[0]

    # Source stats
    sources = conn.execute("""
        SELECT name, consecutive_failures, article_count_last
        FROM sources ORDER BY consecutive_failures DESC
    """).fetchall()

    conn.close()

    return {
        "top_articles": [dict(r) for r in top],
        "categories": [dict(r) for r in cats],
        "curated_count": curated,
        "source_health": [dict(r) for r in sources],
        "period_start": since,
        "period_days": days,
    }


def get_weekly_prompt(data: dict) -> str:
    """Generate a prompt for LLM to write a weekly AI briefing."""
    arts = data["top_articles"]
    article_text = []
    for i, a in enumerate(arts[:20], 1):
        title = a["title_cn"] or a["title"]
        wim = f" — {a['why_it_matters']}" if a.get("why_it_matters") else ""
        article_text.append(
            f"{i}. [{a['category']}] {title}{wim}\n"
            f"   {a['summary_cn'] or a.get('summary','')[:120]}\n"
            f"   来源: {a['source_name']} | {a['published']}\n"
        )

    cat_text = "\n".join(f"- {c['category']}: {c['cnt']} 篇" for c in data["categories"])

    prompt = f"""你是一位资深 AI 行业分析师。请根据以下本周（{data['period_start'][:10]} 至今）的 AI 情报数据，撰写一份「本周 AI 大事记」。

## 数据概览
- 本周精选文章: {data['curated_count']} 篇
- 分类分布:
{cat_text}

## 本周重点文章
{chr(10).join(article_text)}

## 写作要求

用 Markdown 格式写一篇连贯的分析文章（不是列表），包含：

### [头条] 本周头条 (1-2 段)
选最重要的 1-2 件事深入分析。不要复述标题，要解读背后的趋势和影响。

### [趋势] 趋势观察 (2-3 段)
从本周文章中提炼 2-3 个值得关注的趋势，用具体文章作为例证。

### [总结] 一句话总结
用一句话概括本周 AI 行业的主题。

## 格式要求
- 中文输出
- 文章总长 500-800 字
- 提到具体公司/模型/论文时用原文名称
- 不要用"本周"开头，直接进入分析
- 禁止使用任何 emoji 表情符号（如 🔥 📊 🏷️ 等），用纯文本标记替代
- 输出纯 HTML（可直接在浏览器打开），包含完整 <!DOCTYPE html>...<link rel="stylesheet" href="../../assets/style.css">...
- 正文用 <article> 包裹，样式 class 参考 index.html 中的 article-item
- 保存到 data/weekly/{{date}}.html"""

    return prompt


if __name__ == "__main__":
    data = get_week_articles(7)
    print(f"📋 Weekly: {data['curated_count']} curated, {len(data['top_articles'])} top scored")
    prompt = get_weekly_prompt(data)
    print(f"\n--- PROMPT (first 500 chars) ---")
    print(prompt[:500])
