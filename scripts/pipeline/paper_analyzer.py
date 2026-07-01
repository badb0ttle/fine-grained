#!/usr/bin/env python3
"""
论文分析模块 (Paper Analyzer)
==============================
对 ArXiv 论文进行结构化深度分析，提取核心方法、Benchmark 结果和一句话启发。

工作流程：
1. 从 articles 表中查询 is_paper=1 且 paper_method 为空的论文
2. 构造 LLM Prompt（含论文标题 + ArXiv ID + Abstract）
3. 调用方传入 LLM 返回的 JSON 结果
4. apply_analysis() 将结果写回 articles 表的 paper_method/paper_benchmark/paper_takeaway 字段

职责边界：本模块只负责 DB 读写和 Prompt 构造，不直接调用 LLM API。
"""

from . import get_db


def get_unanalyzed_papers(limit: int = 5) -> list[dict]:
    """
    获取尚未分析的论文列表。

    筛选条件：is_paper=1 且 paper_method 为空或 NULL。
    按 score_total 降序排列，优先分析高质量论文。

    Args:
        limit: 最大返回数量，默认 5 篇（避免单次 LLM 调用太长）。

    Returns:
        list[dict]: 论文字典列表，含 id, title, link, summary, source_name,
                    paper_id, score_total 等字段。
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, link, summary, source_name, paper_id, score_total
        FROM articles
        WHERE is_paper = 1 AND (paper_method IS NULL OR paper_method = '')
        ORDER BY score_total DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analysis_prompt(papers: list[dict]) -> str:
    """
    生成论文分析 Prompt。

    为每篇论文提供 ID、标题、ArXiv编号和前400字摘要，
    要求 LLM 提取：核心方法、关键 Benchmark、一句话启发。

    Args:
        papers: 论文列表，每篇含 id, title, paper_id, summary。

    Returns:
        str: 发送给 LLM 的分析 Prompt 文本。
    """
    # 构造每篇论文的文本块
    paper_texts = []
    for i, p in enumerate(papers, 1):
        paper_texts.append(
            f"[ID={p['id']}] Paper: {p['title']}\n"
            f"    ArXiv: {p['paper_id']}\n"
            f"    Abstract: {p['summary'][:400]}\n"
        )

    # 组装 Prompt：要求返回包含 ID 的严格 JSON 数组
    prompt = f"""分析以下 {len(papers)} 篇 ArXiv 论文，对每篇提取结构化信息。

对每篇论文返回：
- paper_method: 核心方法（50字内，中文，说清楚用了什么技术）
- paper_benchmark: 关键 Benchmark 结果（如 "MMLU 92.5%, HumanEval 94.2%"，如无则写"未报告"）
- paper_takeaway: 一句话启发（30字内，对从业者的意义）

返回严格 JSON 数组：
[
  {{"id": <article_id>, "paper_method": "...", "paper_benchmark": "...", "paper_takeaway": "..."}},
  ...
]

论文列表：
{chr(10).join(paper_texts)}"""
    return prompt


def apply_analysis(results: list[dict]) -> int:
    """
    将 LLM 分析结果写回数据库。

    更新 articles 表的 paper_method、paper_benchmark、paper_takeaway 三个字段。

    Args:
        results: LLM 返回的分析结果列表，每项含 id, paper_method, paper_benchmark, paper_takeaway。

    Returns:
        int: 成功更新的论文数量。
    """
    conn = get_db()
    updated = 0
    for r in results:
        if "id" not in r:
            continue  # 跳过缺少 ID 的无效结果
        conn.execute("""
            UPDATE articles SET
            paper_method = ?,
            paper_benchmark = ?,
            paper_takeaway = ?
            WHERE id = ?
        """, (
            r.get("paper_method", ""),
            r.get("paper_benchmark", ""),
            r.get("paper_takeaway", ""),
            r["id"]
        ))
        updated += 1
    conn.commit()
    conn.close()

    print(f"📄 Paper Analyzer: {updated} papers analyzed")
    return updated


if __name__ == "__main__":
    # 独立运行时的快速测试：查询待分析论文并打印 Prompt 预览
    papers = get_unanalyzed_papers(5)
    print(f"📄 {len(papers)} papers awaiting analysis")
    if papers:
        print(f"   Top: {papers[0]['title'][:60]}...")
        prompt = get_analysis_prompt(papers[:3])
        print(f"\n{prompt[:500]}...")
