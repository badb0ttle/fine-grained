#!/usr/bin/env python3
"""Headless scanner for no_agent cron — fast sources only, ~60s runtime.

Skips slow/flaky sources (量子位, TechCrunch, VentureBeat).
Full 16-source scan is done by the 08:00 LLM daily job.
"""
import os
import sys
import time
from pathlib import Path

# ── Monkey-patch: 4s HTTP timeout (cron has 120s hard limit) ──
import requests as _requests
_original_request = _requests.Session.request

def _fast_request(self, method, url, **kwargs):
    kwargs.setdefault("timeout", 4)
    return _original_request(self, method, url, **kwargs)

_requests.Session.request = _fast_request

# Find project root
_project_root = Path(os.environ.get("HERMES_CRON_WORKDIR", Path.cwd()))
if not (_project_root / "scripts" / "pipeline").exists():
    _project_root = Path("/root/fine-grained")
sys.path.insert(0, str(_project_root / "scripts"))

from pipeline import scanner, dedup, scorer
import pipeline  # for direct SOURCES access

# ── Fast sources only: skip flaky ones that waste time through proxy ──
SKIP_SOURCES = {"量子位", "TechCrunch AI", "VentureBeat AI"}
_original_sources = list(pipeline.SOURCES)
pipeline.SOURCES[:] = [s for s in pipeline.SOURCES if s["name"] not in SKIP_SOURCES]

# Override fetch to use 0 retries
_original_fetch = scanner.fetch_feed

def _fetch_fast(source: dict) -> list[dict]:
    return _original_fetch(source, retries=0)

t0 = time.time()

try:
    # Run scanner with fast sources only (in-place replacement)
    scanner.fetch_feed = _fetch_fast
    
    scan_stats = scanner.run()
    
    # Restore full source list
    pipeline.SOURCES[:] = _original_sources
    
    dedup_stats = dedup.run()
    scorer_stats = scorer.run()

    elapsed = time.time() - t0
    new_count = scan_stats.get("new_articles", 0)
    success = scan_stats.get("successful_sources", 0)
    total_src = scan_stats.get("total_sources", 0)

    print(
        f"[scanner] {elapsed:.0f}s | {success}/{total_src} sources "
        f"new={new_count} "
        f"deduped={dedup_stats.get('removed', 0)} "
        f"scored={scorer_stats.get('scored', 0)}",
        file=sys.stderr,
    )

except Exception as e:
    elapsed = time.time() - t0
    print(f"❌ Scanner failed after {elapsed:.0f}s: {e}", file=sys.stderr)
    sys.exit(1)
