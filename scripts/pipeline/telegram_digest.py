#!/usr/bin/env python3
"""Phase 6: Telegram daily digest — reads latest.json, formats for Telegram."""

import json
from pathlib import Path
from datetime import datetime

REPO_DIR = Path(__file__).resolve().parent.parent.parent


def format_digest(data: dict = None) -> str:
    """Format a daily digest from latest.json data. Returns Telegram-markdown formatted text."""
    if data is None:
        latest = REPO_DIR / "data" / "latest.json"
        if not latest.exists():
            return "[空] 暂无数据"
        data = json.loads(latest.read_text(encoding="utf-8"))

    articles = data.get("articles", [])
    if not articles:
        return "[空] 今日无精选文章"

    scanned = (data.get("scanned_at") or "")[:10]
    total = data.get("total_articles", 0)
    sources_ok = data.get("successful_sources", 0)
    sources_total = data.get("total_sources", 0)

    # Header
    lines = [
        f"[AllOfAI] **每日精选**",
        f"[日期] {scanned} · {sources_ok}/{sources_total} 信源 · {total} 篇文章",
        "",
    ]

    # Category icons — text markers instead of emoji
    cat_icons = {
        "AI Lab": "[Lab]", "Paper": "[论文]", "Blog": "[博客]",
        "Community": "[社区]", "中文媒体": "[中文]", "Discussion": "[讨论]",
    }

    # Top 10 or all curated
    top = articles[:10]
    for i, a in enumerate(top, 1):
        title = a.get("title_cn") or a.get("title", "")
        link = a.get("link", "")
        source = a.get("source", "")
        cat = a.get("category", "")
        wim = a.get("why_it_matters", "")
        cat_icon = cat_icons.get(cat, "[其他]")

        # Trim title to reasonable length
        if len(title) > 80:
            title = title[:77] + "..."

        num = f"{i}."

        if i <= 3 and wim:
            # Top 3: with why_it_matters
            lines.append(f"{num} {cat_icon} [{source}] [{title}]({link})")
            lines.append(f"   [意义] {wim}")
        else:
            lines.append(f"{num} {cat_icon} [{source}] [{title}]({link})")
        lines.append("")

    # Footer
    lines.append(f"[网站] [ai.hjhai.xyz](https://ai.hjhai.xyz) | [仪表盘] [dashboard](https://ai.hjhai.xyz/dashboard.html)")

    return "\n".join(lines)


def format_weekly_digest() -> str:
    """Format a weekly digest for Sunday delivery. Scans latest week's data."""
    from . import get_db
    import json

    conn = get_db()

    # Get last 7 days of stats
    stats = conn.execute("""
        SELECT date, total_articles, new_articles, curated_count, successful_sources, total_sources
        FROM daily_stats
        ORDER BY date DESC LIMIT 7
    """).fetchall()

    if not stats:
        conn.close()
        return "[空] 本周暂无数据"

    total_new = sum(s["new_articles"] for s in stats)
    total_curated = sum(s["curated_count"] for s in stats)

    # Get top models mentioned this week
    models = conn.execute("""
        SELECT m.name, m.provider, COUNT(*) as mentions
        FROM models m
        JOIN model_benchmarks mb ON mb.model_id = m.id
        WHERE mb.created_at >= date('now', '-7 days')
        GROUP BY m.id
        ORDER BY mentions DESC LIMIT 5
    """).fetchall()

    conn.close()

    # Read latest week's curated
    latest = REPO_DIR / "data" / "latest.json"
    articles = []
    if latest.exists():
        data = json.loads(latest.read_text(encoding="utf-8"))
        articles = data.get("articles", [])[:5]

    lines = [
        "[AllOfAI] **本周回顾**",
        f"[日期] {stats[0]['date'] if stats else '?'} 周",
        f"[统计] 新增 {total_new} 篇 · 精选 {total_curated} 篇 · {len(stats)} 天数据",
        "",
    ]

    if models:
        lines.append("[热门] **本周热门模型**")
        for i, m in enumerate(models, 1):
            lines.append(f"  {i}. {m['name']} ({m['provider']}) — {m['mentions']} 次提及")
        lines.append("")

    if articles:
        lines.append("[精选] **本周精选**")
        for a in articles[:5]:
            title = (a.get("title_cn") or a.get("title", ""))[:60]
            link = a.get("link", "")
            lines.append(f"  · [{title}]({link})")
        lines.append("")

    lines.append(f"[网站] [ai.hjhai.xyz](https://ai.hjhai.xyz) | [周报] [weekly](https://ai.hjhai.xyz/data/weekly/)")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test: generate digest from latest.json
    digest = format_digest()
    print(digest)
    print(f"\n---\n{len(digest)} chars")
