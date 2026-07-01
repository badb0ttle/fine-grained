#!/usr/bin/env python3
"""
周日周报生成器 — 生成中英双语 Prompt 供 LLM 撰写 AI 行业周报。

================================================================================
模块功能
================================================================================
每周日运行的周报生成模块，不直接调用 LLM API，而是:
  1. get_week_articles: 从数据库提取过去 7 天的高分文章和相关统计数据
  2. get_weekly_prompt: 生成中文 Prompt，供 LLM 撰写中文周报
  3. get_weekly_prompt_en: 生成英文 Prompt，供 LLM 撰写英文周报

实际 LLM 调用由外部调度系统（如 Hermes Agent Cron）执行。

================================================================================
周报结构
================================================================================
【中文版】
  ### [头条] 本周头条 (1-2段): 深入分析最重要的 1-2 件事
  ### [趋势] 趋势观察 (2-3段): 提炼 2-3 个趋势，用具体文章例证
  ### [总结] 一句话总结: 概括本周 AI 行业主题

【英文版】结构相同，英文输出:
  ### [Headlines] This Week's Top Story
  ### [Trends] Trend Watch
  ### [TL;DR] One-Sentence Summary

================================================================================
去 AI 套话规则
================================================================================
中英双语都需要严格遵循反 AI 套话规则:
  - 中文黑名单: "在...方面" "展现出..." "具有重要意义" 等
  - 英文黑名单: "In the realm of..." "showcases..." "a testament to..." 等
  - 写作原则: 口语化短句、信息密度优先、禁止 emoji
"""

from datetime import datetime, timedelta

from . import get_db


def get_week_articles(days: int = 7) -> dict:
    """
    获取过去 N 天的周报所需数据。

    提取四个维度:
      1. top_articles (最多 50 篇): 高分文章列表，含中英文标题和摘要
      2. categories: 按分类聚合的文章数量分布
      3. curated_count: 本周精选文章数量
      4. source_health: 信源健康状态（含连续失败次数）

    时间筛选使用 published >= since，确保只包含本周发布的文章。
    注意: 使用 datetime.utcnow() 而非 timezone.utc，保持与数据库时间格式一致。

    Args:
        days: 统计天数，默认 7（一周）

    Returns:
        {
          top_articles: [{ title, title_cn, summary_cn, why_it_matters, source_name, category, score_total, published }],
          categories: [{ category, cnt }],
          curated_count: int,
          source_health: [{ name, consecutive_failures, article_count_last }],
          period_start: str (ISO 格式起始日期),
          period_days: int,
        }
    """
    conn = get_db()
    # 计算起始日期: 当前 UTC 时间 - days 天
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # ---- 1. 本周高分文章 (top 50) ----
    top = conn.execute("""
        SELECT title, title_cn, summary_cn, why_it_matters, source_name,
               category, score_total, published
        FROM articles
        WHERE score_total > 0 AND published >= ?
        ORDER BY score_total DESC
        LIMIT 50
    """, (since,)).fetchall()

    # ---- 2. 分类分布 ----
    cats = conn.execute("""
        SELECT category, COUNT(*) as cnt
        FROM articles
        WHERE score_total > 0 AND published >= ?
        GROUP BY category ORDER BY cnt DESC
    """, (since,)).fetchall()

    # ---- 3. 精选文章计数 ----
    curated = conn.execute("""
        SELECT COUNT(*) FROM articles
        WHERE curated = 1 AND curated_at >= ?
    """, (since,)).fetchone()[0]

    # ---- 4. 信源健康状态 ----
    # 按连续失败次数降序，优先展示有问题的信源
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
    """
    生成中文周报的 LLM Prompt。

    Prompt 结构:
      1. 角色设定: "资深 AI 行业分析师"
      2. 数据概览: 精选文章数、分类分布
      3. 本周重点文章: 最多 20 篇格式化列表
      4. 写作要求:
         - [头条] 深入分析 1-2 件事
         - [趋势] 提炼 2-3 个趋势
         - [总结] 一句话概括
      5. 去 AI 味写作规则（与 curator.py 保持一致）
      6. 格式要求: 中文输出、纯 HTML、article 包裹

    输出格式为纯 HTML（含 DOCTYPE 和 CSS 引用），可直接在浏览器打开。
    保存路径: data/weekly/{date}.html

    Args:
        data: get_week_articles() 的返回值

    Returns:
        完整的中文 Prompt 字符串
    """
    arts = data["top_articles"]
    # 构建文章列表文本（最多 20 篇，取最重要的）
    article_text = []
    for i, a in enumerate(arts[:20], 1):
        # 优先使用中文标题，回退到英文原文标题
        title = a["title_cn"] or a["title"]
        wim = f" — {a['why_it_matters']}" if a.get("why_it_matters") else ""
        article_text.append(
            f"{i}. [{a['category']}] {title}{wim}\n"
            f"   {a['summary_cn'] or a.get('summary','')[:120]}\n"
            f"   来源: {a['source_name']} | {a['published']}\n"
        )

    # 构建分类分布文本
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
选最重要的 1-2 件事深入分析。不要复述标题，要解读背后的趋势和实际影响。

### [趋势] 趋势观察 (2-3 段)
从本周文章中提炼 2-3 个值得关注的趋势，用具体文章作为例证。

### [总结] 一句话总结
用一句话概括本周 AI 行业的主题。

## 去 AI 味写作规则（严格执行）
禁止以下 AI 套话词汇和句式：
- "在...方面" "不仅...而且..." "展现出..." "具有重要意义"
- "标志着..." "为...提供了..." "推动...发展"
- "进一步..." "全面/深入/系统" "实现了...突破"
- "引发...思考" "值得我们关注" "令人瞩目"

写作原则：
- 用口语化短句，像写 newsletter 给朋友看，不要论文腔和官腔
- 只说事实和判断，不铺垫，不要"随着...的发展"这类废话开头
- 数据要具体，少用"众多""大量""广泛"这种模糊词
- 禁止使用任何 emoji 表情符号
- 技术名词保留英文

## 格式要求
- 中文输出
- 文章总长 400-600 字
- 提到具体公司/模型/论文时用原文名称
- 输出纯 HTML（可直接在浏览器打开），包含完整 <!DOCTYPE html>...<link rel="stylesheet" href="../../assets/style.css">...
- 正文用 <article> 包裹，样式 class 参考 index.html 中的 article-item
- 保存到 data/weekly/{{date}}.html"""

    return prompt


def get_weekly_prompt_en(data: dict) -> str:
    """
    生成英文周报的 LLM Prompt。

    结构与中文版完全对应，但:
      - 使用英文角色设定和写作要求
      - 使用原始英文标题（不使用中文翻译）
      - 英文特有的反 AI 套话规则

    输出格式同样是纯 HTML，保存为 data/weekly/{date}_en.html。

    Args:
        data: get_week_articles() 的返回值

    Returns:
        完整的英文 Prompt 字符串
    """
    arts = data["top_articles"]
    article_text = []
    for i, a in enumerate(arts[:20], 1):
        # 英文版使用原始英文标题
        title = a["title"]
        wim = f" — {a['why_it_matters']}" if a.get("why_it_matters") else ""
        article_text.append(
            f"{i}. [{a['category']}] {title}{wim}\n"
            f"   {a.get('summary','')[:120]}\n"
            f"   Source: {a['source_name']} | {a['published']}\n"
        )

    cat_text = "\n".join(f"- {c['category']}: {c['cnt']} articles" for c in data["categories"])

    prompt = f"""You are a senior AI industry analyst. Write a "This Week in AI" briefing based on the following data ({data['period_start'][:10]} to now).

## Data Overview
- Curated articles this week: {data['curated_count']}
- Category breakdown:
{cat_text}

## Top Articles This Week
{chr(10).join(article_text)}

## Writing Requirements

Write a coherent analytical piece in Markdown (not a listicle), covering:

### [Headlines] This Week's Top Story (1-2 paragraphs)
Pick the 1-2 most important developments. Don't just restate titles — interpret the trends and real-world impact behind them.

### [Trends] Trend Watch (2-3 paragraphs)
Extract 2-3 notable trends from this week's articles, using specific stories as evidence.

### [TL;DR] One-Sentence Summary
Sum up the theme of this week in AI in a single sentence.

## Anti-AI-Slop Rules (strictly enforced)
Banned phrases and patterns:
- "In the realm of..." "It is noteworthy that..." "Furthermore..." "Moreover..."
- "showcases..." "underscores..." "highlights the importance of..."
- "a testament to..." "ushers in a new era..." "marks a significant milestone..."
- "delve into..." "unpack..." "it's worth noting that..." "arguably..."

Writing principles:
- Write like a newsletter to a smart friend — conversational, punchy, no academic throat-clearing
- Facts and judgments only, no padding. Never start with "As AI continues to evolve..."
- Be specific with numbers and names. Avoid "many" "several" "various"
- No emoji
- Keep technical terms in their original form

## Format Requirements
- English output
- 400-600 words total
- Use original names for companies/models/papers
- Output pure HTML (ready to open in browser), including <!DOCTYPE html>...<link rel="stylesheet" href="../../assets/style.css">...
- Wrap body text in <article> tags, with classes referencing index.html article-item styles
- Save to data/weekly/{{date}}_en.html"""

    return prompt


if __name__ == "__main__":
    data = get_week_articles(7)
    print(f"📋 Weekly: {data['curated_count']} curated, {len(data['top_articles'])} top scored")
    prompt = get_weekly_prompt(data)
    print(f"\n--- PROMPT (first 500 chars) ---")
    print(prompt[:500])
    print(f"\n--- EN PROMPT (first 500 chars) ---")
    prompt_en = get_weekly_prompt_en(data)
    print(prompt_en[:500])
