#!/usr/bin/env python3
"""Headless scanner — runs scanner → dedup → scorer, zero LLM cost.
Designed for no_agent cron (120s timeout): uses aggressive timeouts to fit.

Runs in ~90s: 6s per-source timeout, 0 retries, parallel-friendly.
Silent stdout on success, errors to stderr.
"""
import os
import sys
import time
from pathlib import Path

# ── Monkey-patch: shorter HTTP timeouts (cron has 120s hard limit) ──
import requests as _requests
_original_request = _requests.Session.request

def _fast_request(self, method, url, **kwargs):
    kwargs.setdefault("timeout", 6)  # 6s per source
    return _original_request(self, method, url, **kwargs)

_requests.Session.request = _fast_request

# Cron script runs from ~/.hermes/scripts/, need to find the project
_project_root = Path(os.environ.get("HERMES_CRON_WORKDIR", Path.cwd()))
if not (_project_root / "scripts" / "pipeline").exists():
    _project_root = Path("/root/fine-grained")  # server fallback
sys.path.insert(0, str(_project_root / "scripts"))

from pipeline import scanner, dedup, scorer

# ── Override fetch_feed to use 0 retries (saves ~30s total) ──
_original_fetch = scanner.fetch_feed

def _fetch_feed_fast(source: dict) -> list[dict]:
    return _original_fetch(source, retries=0)

scanner.fetch_feed = _fetch_feed_fast

t0 = time.time()

try:
    scan_stats = scanner.run()
    dedup_stats = dedup.run()
    scorer_stats = scorer.run()

    elapsed = time.time() - t0
    new_count = scan_stats.get("new_articles", 0)
    success = scan_stats.get("successful_sources", 0)
    total_src = scan_stats.get("total_sources", 0)

    summary = (
        f"[scanner] {elapsed:.0f}s | sources={success}/{total_src} "
        f"new={new_count} "
        f"deduped={dedup_stats.get('removed', 0)} "
        f"scored={scorer_stats.get('scored', 0)}"
    )
    print(summary, file=sys.stderr)

    # Always silent stdout on success — no notification spam

except Exception as e:
    elapsed = time.time() - t0
    print(f"❌ Scanner failed after {elapsed:.0f}s: {e}", file=sys.stderr)
    sys.exit(1)
