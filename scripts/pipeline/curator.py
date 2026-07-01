#!/usr/bin/env python3
"""
阶段4: Curator — LLM 精选翻译模块。

================================================================================
模块功能
================================================================================
Pipeline 第四阶段：利用 DeepSeek 大模型对高评分文章进行精选和中文翻译。
  1. get_candidates: 从数据库获取 top-N 未精选的高分文章
  2. get_curation_prompt: 生成包含筛选标准、写作规范、去 AI 套话规则的 Prompt
  3. apply_curation: 将 LLM 返回的精选结果写回数据库
  4. export_latest_json: 导出精选文章为前端可用的 JSON 格式

================================================================================
核心设计
================================================================================
【Prompt 工程】
  - 系统角色设定: "资深 AI 技术编辑"，明确任务边界
  - 筛选标准: 优先有实际影响、可操作、反常识、新发布的内容
  - 跳过 PR 稿和泛泛而谈的内容

【去 AI 套话规范 (Anti-AI-Slop Rules)】
  - 黑名单词汇: "在...方面" "不仅...而且..." "展现出..." "具有重要意义" 等
  - 写作原则: 口语化短句、信息密度优先、技术名词保留英文
  - 这是本模块最关键的 Prompt 工程部分，直接影响输出质量

【输出格式】
  - 严格 JSON 数组，每个元素包含: id, title_cn, summary_cn, why_it_matters
  - title_cn ≤20 字, summary_cn 40-80 字, why_it_matters ≤25 字
  - 使用数据库中的 DB ID 关联，确保写回时能精确匹配
"""

import json
from datetime import datetime, timezone

from . import get_db


def get_candidates(limit: int = 20) -> list[dict]:
    """
    获取待精选的高分文章候选列表。

    筛选条件:
      - score_total > 0: 已评分（通常 Scanner+Scorer 已运行）
      - curated IS NULL OR curated = 0: 尚未被精选过
      - 按 score_total DESC 排序，取 top-N

    返回的字段包含全部评分维度，方便 LLM 做综合判断。

    Args:
        limit: 返回的候选数量，默认 20（通常精选 10 篇，多取一些给 LLM 选择空间）

    Returns:
        文章字典列表，每个元素包含 id/title/link/summary/published/source_name/
        category/score_total/score_authority/score_timeliness/score_depth/score_relevance
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, link, summary, published, source_name, category,
               score_total, score_authority, score_timeliness, score_depth, score_relevance
        FROM articles
        WHERE score_total > 0
          AND (curated IS NULL OR curated = 0)
        ORDER BY score_total DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_curation_prompt(candidates: list[dict], count: int = 10) -> str:
    """
    生成 LLM 精选 Prompt。

    Prompt 设计分为四个部分:
      1. 【角色与任务】: "资深 AI 技术编辑"，从 N 篇中选 count 篇
      2. 【筛选标准】: 有实际影响、可操作、反常识、新发布
      3. 【写作规范 — 去 AI 套话】: 这是最关键的工程部分
         - 黑名单: 列出了 AI 常见套话词汇，明确禁止
         - 写作原则: 口语化、信息密度优先、技术名词保留英文
         - 字数限制: title_cn ≤20, summary_cn 40-80, why_it_matters ≤25
      4. 【候选文章列表】: 带编号、评分、来源的格式化文章数据

    Args:
        candidates: 候选文章列表（来自 get_candidates）
        count:     精选数量，默认 10

    Returns:
        完整的 LLM Prompt 字符串
    """
    # 构建候选文章列表文本（带 DB ID 和评分，方便 LLM 回填）
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
    """
    将 LLM 精选结果写回数据库。

    对每篇精选文章更新:
      - title_cn:      中文标题
      - summary_cn:    中文摘要
      - why_it_matters: 为什么重要（可选）
      - curated = 1:   标记为已精选
      - curated_at:    精选时间戳

    同时更新 daily_stats 表中的 curated_count 字段。

    Args:
        curated: LLM 返回的精简列表，每项包含:
                 - id (必需):            数据库文章 ID
                 - title_cn (必需):      中文标题
                 - summary_cn (必需):    中文摘要
                 - why_it_matters (可选): 重要性说明

    Returns:
        { curated: int, curated_at: str } — 已精选数量和操作时间
    """
    conn = get_db()
    curated_at = datetime.now(timezone.utc).isoformat()
    updated = 0

    for item in curated:
        # 跳过缺少 id 的无效条目（LLM 可能返回不符合格式的数据）
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

    # 同步更新每日统计中的精选计数
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
    """
    导出精选文章为 latest.json 兼容格式。

    返回的 JSON 结构专为前端设计:
      - 顶层元信息: scanned_at, curated_at, total_sources 等
      - articles 数组: 每篇包含原文信息 + 中文翻译 + 评分

    注意: 此函数被 publisher.py 的 run() 调用，生成的 JSON 最终写入 data/latest.json

    Returns:
        {
          "scanned_at": str,
          "curated_at": str,
          "total_sources": int,
          "successful_sources": int,
          "total_articles": int,
          "curated_count": int,
          "articles": [
            { title, link, summary, published, source, category, title_cn, summary_cn, why_it_matters }
          ]
        }
    """
    conn = get_db()

    # 获取最新的 daily_stats 记录作为元信息
    stats = conn.execute("""
        SELECT date, total_sources, successful_sources, total_articles, curated_count
        FROM daily_stats
        ORDER BY date DESC LIMIT 1
    """).fetchone()

    # 获取所有已精选的文章，按评分降序排列
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
        # why_it_matters 是可选字段，只在有值时添加
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
