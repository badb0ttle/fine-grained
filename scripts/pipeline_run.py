#!/usr/bin/env python3
"""
AI Intel Pipeline 主入口 (Pipeline Run)
========================================
串联全部 Pipeline 阶段，支持全流程运行或按阶段独立执行。

完整流程（5 阶段）：
  1. Scanner    — RSS 信源扫描，采集文章
  2. Dedup      — 文章去重（标题/哈希）
  3. Scorer     — 质量评分（四维：权威性/时效性/深度/相关性）
  4. Curator    — 精选候选筛选 + LLM Curation Prompt 生成
  5. GitHub Trending — GitHub 热门 AI/ML 仓库抓取

用法：
  python pipeline_run.py           # 运行完整 Pipeline
  python pipeline_run.py scanner   # 仅运行扫描阶段
  python pipeline_run.py scorer    # 仅运行评分阶段
"""

import argparse
import time
from pathlib import Path

from pipeline import scanner, dedup, scorer, curator, publisher, paper_analyzer, github_trending


def run_full():
    """
    执行完整 Pipeline 全流程。

    流程说明：
    - Stage 1-3：自动运行（扫描→去重→评分）
    - Stage 4：筛选候选文章并生成 LLM Curation Prompt（保存为文件供 Agent 消费）
    - Stage 5：抓取 GitHub Trending 数据

    Returns:
        dict: 各阶段统计汇总，含 scan, dedup, scorer, candidates, elapsed。
    """
    t0 = time.time()
    print("=" * 60)
    print("🤖 AI Intel Pipeline")
    print("=" * 60)

    # ---- Stage 1: Scanner（RSS 扫描） ----
    print("\n[1/4] Scanner")
    scan_stats = scanner.run()

    # ---- Stage 2: Dedup（去重） ----
    print("\n[2/4] Dedup")
    dedup_stats = dedup.run()

    # ---- Stage 3: Scorer（质量评分） ----
    print("\n[3/4] Scorer")
    scorer_stats = scorer.run()

    # ---- Stage 4: Curator（精选候选 + Prompt） ----
    # 注意：此阶段只做候选筛选，不调用 LLM；LLM 精选由 Agent 单独处理
    print("\n[4/5] Curator (candidate selection)")
    candidates = curator.get_candidates(20)
    top_n = min(10, len(candidates))  # 精选 Top N
    print(f"   {len(candidates)} candidates ready for LLM curation")
    if candidates:
        print(f"   Top: [{candidates[0]['score_total']:.1f}] {candidates[0]['title'][:60]}...")

        # 生成 LLM Curation Prompt 并保存到文件
        # Agent 读取此文件，调用 LLM 获取精选结果后再写回数据库
        prompt = curator.get_curation_prompt(candidates, top_n)
        prompt_path = Path(__file__).parent.parent / "data" / "curation_prompt.txt"
        prompt_path.write_text(prompt)
        print(f"   📝 Curation prompt saved to data/curation_prompt.txt")

    # ---- Stage 5: GitHub Trending（热门仓库） ----
    print("\n[5/5] GitHub Trending")
    trending_stats = github_trending.run()

    # 汇总耗时与统计
    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"✅ Pipeline complete in {elapsed:.1f}s")
    print(f"   📰 {scan_stats.get('new_articles', 0)} new articles")
    print(f"   📊 {scorer_stats.get('scored', 0)} scored")
    print(f"   📋 {len(candidates)} awaiting curation")
    print(f"{'=' * 60}")

    return {
        "scan": scan_stats,
        "dedup": dedup_stats,
        "scorer": scorer_stats,
        "candidates": len(candidates),
        "elapsed": elapsed,
    }


def run_stage(stage: str):
    """
    运行单个 Pipeline 阶段（用于调试或独立执行）。

    支持阶段：scanner, dedup, scorer, curator, paper, publisher

    Args:
        stage: 阶段名称字符串。
    """
    stages = {
        "scanner": scanner.run,
        "dedup": dedup.run,
        "scorer": scorer.run,
        "curator": lambda: curator.get_candidates(10),
        "paper": lambda: paper_analyzer.get_unanalyzed_papers(5),
        "publisher": publisher.run,
    }
    if stage not in stages:
        print(f"❌ Unknown stage: {stage}")
        print(f"   Available: {', '.join(stages.keys())}")
        return
    stages[stage]()


if __name__ == "__main__":
    # ── 命令行参数解析 ──
    parser = argparse.ArgumentParser(description="AI Intel Pipeline")
    parser.add_argument("stage", nargs="?", default="full",
                        choices=["full", "scanner", "dedup", "scorer", "curator", "publisher"],
                        help="Pipeline stage to run (default: full)")
    args = parser.parse_args()

    if args.stage == "full":
        run_full()
    else:
        run_stage(args.stage)
