#!/usr/bin/env python3
"""AI Intel Pipeline — run stages independently or as a full chain."""

import argparse
import time
from pathlib import Path

from pipeline import scanner, dedup, scorer, curator, publisher


def run_full():
    """Run complete pipeline: scan → dedup → score → publish.
    
    Note: curation (Stage 4) requires LLM and is handled by the agent separately.
    """
    t0 = time.time()
    print("=" * 60)
    print("🤖 AI Intel Pipeline")
    print("=" * 60)

    # Stage 1: Scanner
    print("\n[1/4] Scanner")
    scan_stats = scanner.run()

    # Stage 2: Dedup
    print("\n[2/4] Dedup")
    dedup_stats = dedup.run()

    # Stage 3: Scorer
    print("\n[3/4] Scorer")
    scorer_stats = scorer.run()

    # Stage 4: Curator — prepare candidates for LLM
    print("\n[4/4] Curator (candidate selection)")
    candidates = curator.get_candidates(20)
    top_n = min(10, len(candidates))
    print(f"   {len(candidates)} candidates ready for LLM curation")
    if candidates:
        print(f"   Top: [{candidates[0]['score_total']:.1f}] {candidates[0]['title'][:60]}...")

        # Output candidates as JSON for the agent to process
        prompt = curator.get_curation_prompt(candidates, top_n)
        prompt_path = Path(__file__).parent.parent / "data" / "curation_prompt.txt"
        prompt_path.write_text(prompt)
        print(f"   📝 Curation prompt saved to data/curation_prompt.txt")

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
    """Run a single pipeline stage."""
    stages = {
        "scanner": scanner.run,
        "dedup": dedup.run,
        "scorer": scorer.run,
        "curator": lambda: curator.get_candidates(10),
        "publisher": publisher.run,
    }
    if stage not in stages:
        print(f"❌ Unknown stage: {stage}")
        print(f"   Available: {', '.join(stages.keys())}")
        return
    stages[stage]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Intel Pipeline")
    parser.add_argument("stage", nargs="?", default="full",
                        choices=["full", "scanner", "dedup", "scorer", "curator", "publisher"],
                        help="Pipeline stage to run (default: full)")
    args = parser.parse_args()

    if args.stage == "full":
        run_full()
    else:
        run_stage(args.stage)
