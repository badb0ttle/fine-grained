#!/usr/bin/env python3
"""Paper Analyzer — structured extraction for ArXiv papers."""

from . import get_db


def get_unanalyzed_papers(limit: int = 5) -> list[dict]:
    """Get papers that need analysis (is_paper=1, no paper_method yet)."""
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
    """Generate a prompt for the LLM to analyze papers."""
    paper_texts = []
    for i, p in enumerate(papers, 1):
        paper_texts.append(
            f"[ID={p['id']}] Paper: {p['title']}\n"
            f"    ArXiv: {p['paper_id']}\n"
            f"    Abstract: {p['summary'][:400]}\n"
        )

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
    """Apply paper analysis results to DB."""
    conn = get_db()
    updated = 0
    for r in results:
        if "id" not in r:
            continue
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
    papers = get_unanalyzed_papers(5)
    print(f"📄 {len(papers)} papers awaiting analysis")
    if papers:
        print(f"   Top: {papers[0]['title'][:60]}...")
        prompt = get_analysis_prompt(papers[:3])
        print(f"\n{prompt[:500]}...")
