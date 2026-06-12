#!/usr/bin/env python3
"""Headless scanner — runs scanner → dedup → scorer, zero LLM cost.
Designed for no_agent cron: silent stdout on success, errors to stderr.
"""
import os
import sys
import time
from pathlib import Path

# Cron script runs from ~/.hermes/scripts/, need to find the project
# Try current workdir first, fall back to known path
_project_root = Path(os.environ.get("HERMES_CRON_WORKDIR", Path.cwd()))
if not (_project_root / "scripts" / "pipeline").exists():
    _project_root = Path("/root/fine-grained")  # server fallback
sys.path.insert(0, str(_project_root / "scripts"))

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
    
    # Always silent stdout on success — no notification spam
    # All output goes to stderr for journal/diagnostic use
    
except Exception as e:
    print(f"❌ Scanner failed: {e}", file=sys.stderr)
    sys.exit(1)
