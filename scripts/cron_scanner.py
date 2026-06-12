#!/usr/bin/env python3
"""Headless scanner — runs scanner → dedup → scorer, zero LLM cost.
Designed for no_agent cron: silent stdout on success, errors to stderr.
"""
import sys
import time
from pathlib import Path

# Make sure scripts/ is on the path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import scanner, dedup, scorer

t0 = time.time()

try:
    # Stage 1: Scanner
    scan_stats = scanner.run()
    
    # Stage 2: Dedup
    dedup_stats = dedup.run()
    
    # Stage 3: Scorer
    scorer_stats = scorer.run()
    
    elapsed = time.time() - t0
    new_count = scan_stats.get("new_articles", 0)
    
    summary = (
        f"[scanner] {elapsed:.0f}s | "
        f"fetched={scan_stats.get('fetched', 0)} "
        f"new={new_count} "
        f"deduped={dedup_stats.get('removed', 0)} "
        f"scored={scorer_stats.get('scored', 0)}"
    )
    print(summary, file=sys.stderr)
    
    # Silent stdout on success → no notification spam
    # Only print to stdout if there are new articles (optional notification)
    if new_count > 0:
        print(f"📡 {new_count} new articles collected")
    
except Exception as e:
    print(f"❌ Scanner failed: {e}", file=sys.stderr)
    sys.exit(1)
