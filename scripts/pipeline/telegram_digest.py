#!/usr/bin/env python3
"""
阶段6: Telegram 推送摘要 — 从 latest.json 读取精选文章，格式化为 Telegram Markdown。

================================================================================
模块功能
================================================================================
Pipeline 补充阶段：将精选文章转换为 Telegram 频道推送格式。
  1. format_digest:         生成每日精选摘要（从 latest.json 读取）
  2. format_weekly_digest:  生成每周回顾摘要（从 daily_stats + latest.json 读取）

两种摘要格式都输出 Telegram Markdown（`**粗体**`, `[文本](URL)`），
由外部调度系统（如 Hermes Agent）通过 Telegram Bot API 发送。

================================================================================
每日摘要格式
================================================================================
  [AllOfAI] **每日精选**
  [日期] YYYY-MM-DD · 成功信源/总信源 · 总文章数

  1. [分类标签] [来源] [中文标题](原文链接)
     [意义] why_it_matters (仅 top 3)

  2. [分类标签] [来源] [中文标题](原文链接)
  ...
  [网站] [ai.hjhai.xyz](https://ai.hjhai.xyz) | [仪表盘] [dashboard](...)

================================================================================
每周摘要格式
================================================================================
  [AllOfAI] **本周回顾**
  [日期] 周
  [统计] 新增N篇 · 精选N篇 · N天数据

  [热门] **本周热门模型**
    1. name (provider) — N次提及

  [精选] **本周精选**
    · [中文标题](链接)
  ...
  [网站] ... | [周报] [weekly](...)
"""

import json
from pathlib import Path
from datetime import datetime

REPO_DIR = Path(__file__).resolve().parent.parent.parent


def format_digest(data: dict = None) -> str:
    """
    从 latest.json 数据生成每日精选的 Telegram Markdown 摘要。

    摘要结构:
      - Header: 日期 + 信源状态 + 文章总数
      - Body: Top-10 精选文章，前 3 篇带 why_it_matters
      - Footer: 网站链接 + 仪表盘链接

    分类标签映射:
      AI Lab → [Lab], Paper → [论文], Blog → [博客], Community → [社区],
      中文媒体 → [中文], Discussion → [讨论]

    标题超长处理: 超过 80 字符的标题截断为 77 字符 + "..."

    Args:
        data: latest.json 解析后的字典。为 None 时自动从 data/latest.json 读取。

    Returns:
        Telegram Markdown 格式的文本字符串。
        如果无数据，返回 "[空] 暂无数据" 或 "[空] 今日无精选文章"。
    """
    # 自动加载 latest.json（如果未传入数据）
    if data is None:
        latest = REPO_DIR / "data" / "latest.json"
        if not latest.exists():
            return "[空] 暂无数据"
        data = json.loads(latest.read_text(encoding="utf-8"))

    articles = data.get("articles", [])
    if not articles:
        return "[空] 今日无精选文章"

    # 提取元信息
    scanned = (data.get("scanned_at") or "")[:10]  # 取日期部分
    total = data.get("total_articles", 0)
    sources_ok = data.get("successful_sources", 0)
    sources_total = data.get("total_sources", 0)

    # ---- Header ----
    lines = [
        f"[AllOfAI] **每日精选**",
        f"[日期] {scanned} · {sources_ok}/{sources_total} 信源 · {total} 篇文章",
        "",
    ]

    # ---- 分类标签（文本标记代替 emoji，兼容性更好） ----
    cat_icons = {
        "AI Lab": "[Lab]", "Paper": "[论文]", "Blog": "[博客]",
        "Community": "[社区]", "中文媒体": "[中文]", "Discussion": "[讨论]",
    }

    # ---- Body: Top-10 精选文章 ----
    # 前 3 篇额外展示 why_it_matters（重要性说明）
    top = articles[:10]
    for i, a in enumerate(top, 1):
        title = a.get("title_cn") or a.get("title", "")
        link = a.get("link", "")
        source = a.get("source", "")
        cat = a.get("category", "")
        wim = a.get("why_it_matters", "")
        cat_icon = cat_icons.get(cat, "[其他]")

        # 超长标题截断: Telegram 每条消息有 4096 字符限制，但标题过长影响阅读
        if len(title) > 80:
            title = title[:77] + "..."

        num = f"{i}."

        if i <= 3 and wim:
            # Top 3 展示重要性说明
            lines.append(f"{num} {cat_icon} [{source}] [{title}]({link})")
            lines.append(f"   [意义] {wim}")
        else:
            lines.append(f"{num} {cat_icon} [{source}] [{title}]({link})")
        lines.append("")  # 空行分隔

    # ---- Footer ----
    lines.append(f"[网站] [ai.hjhai.xyz](https://ai.hjhai.xyz) | [仪表盘] [dashboard](https://ai.hjhai.xyz/dashboard.html)")

    return "\n".join(lines)


def format_weekly_digest() -> str:
    """
    生成每周回顾的 Telegram Markdown 摘要（用于周日推送）。

    数据来源:
      - daily_stats 表: 最近 7 天的统计汇总（新增文章数、精选数）
      - models 表: 本周被提及最多的模型（热门模型）
      - latest.json: 精选文章中取前 5 篇

    格式结构与每日摘要类似，但包含:
      - 热门模型列表: 本周被 benchmark 提及次数最多的模型
      - 本周精选: 取前 5 篇精选文章

    Returns:
        Telegram Markdown 格式的周报摘要。
        如果本周无数据，返回 "[空] 本周暂无数据"。
    """
    from . import get_db
    import json

    conn = get_db()

    # ---- 1. 最近 7 天统计 ----
    stats = conn.execute("""
        SELECT date, total_articles, new_articles, curated_count, successful_sources, total_sources
        FROM daily_stats
        ORDER BY date DESC LIMIT 7
    """).fetchall()

    if not stats:
        conn.close()
        return "[空] 本周暂无数据"

    # 汇总一周数据
    total_new = sum(s["new_articles"] for s in stats)
    total_curated = sum(s["curated_count"] for s in stats)

    # ---- 2. 本周热门模型 (top 5) ----
    # 通过 model_benchmarks 表统计最近 7 天被提及最多的模型
    models = conn.execute("""
        SELECT m.name, m.provider, COUNT(*) as mentions
        FROM models m
        JOIN model_benchmarks mb ON mb.model_id = m.id
        WHERE mb.reported_at >= date('now', '-7 days')
        GROUP BY m.id
        ORDER BY mentions DESC LIMIT 5
    """).fetchall()

    conn.close()

    # ---- 3. 本周精选文章 (top 5) ----
    latest = REPO_DIR / "data" / "latest.json"
    articles = []
    if latest.exists():
        data = json.loads(latest.read_text(encoding="utf-8"))
        articles = data.get("articles", [])[:5]

    # ---- 组装输出 ----
    lines = [
        "[AllOfAI] **本周回顾**",
        f"[日期] {stats[0]['date'] if stats else '?'} 周",
        f"[统计] 新增 {total_new} 篇 · 精选 {total_curated} 篇 · {len(stats)} 天数据",
        "",
    ]

    # 热门模型部分
    if models:
        lines.append("[热门] **本周热门模型**")
        for i, m in enumerate(models, 1):
            lines.append(f"  {i}. {m['name']} ({m['provider']}) — {m['mentions']} 次提及")
        lines.append("")

    # 精选文章部分
    if articles:
        lines.append("[精选] **本周精选**")
        for a in articles[:5]:
            title = (a.get("title_cn") or a.get("title", ""))[:60]  # 截断到 60 字符
            link = a.get("link", "")
            lines.append(f"  · [{title}]({link})")
        lines.append("")

    lines.append(f"[网站] [ai.hjhai.xyz](https://ai.hjhai.xyz) | [周报] [weekly](https://ai.hjhai.xyz/data/weekly/)")

    return "\n".join(lines)


if __name__ == "__main__":
    # 测试: 从 latest.json 生成每日摘要
    digest = format_digest()
    print(digest)
    print(f"\n---\n{len(digest)} chars")
