"""API client for the AllOfAI backend — called by cron pipelines.

This module POSTs scan/curation results to the FastAPI backend so the
frontend fetches live data instead of static JSON files.

Usage:
    from .api_client import post_batch, post_curation

    post_batch(articles=[...], stats={...}, scan_id="2026-W25")
    post_curation(curated=[...], scan_id="2026-W25")
"""

import json
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ── Config ──

# Default: local FastAPI server (ECS runs API on 127.0.0.1:8001 behind OpenResty)
API_BASE = os.getenv("AI_INTEL_API_BASE", "http://127.0.0.1:8001")
API_KEY = os.getenv("AI_INTEL_API_KEY", "")
# 如果环境变量未设置，从 .env 文件读取（cron 环境不自动加载 .env）
if not API_KEY:
    from pathlib import Path as _P
    _envf = _P(os.getenv("HERMES_HOME", "/root/.hermes")) / ".env"
    if not _envf.exists():
        _envf = _P("/root/fine-grained/.env")
    if _envf.exists():
        for _l in _envf.read_text().splitlines():
            _l = _l.strip()
            if _l.startswith("AI_INTEL_API_KEY="):
                API_KEY = _l.split("=", 1)[1].strip().strip('"').strip("'")
                break

API_ENABLED = os.getenv("AI_INTEL_API_ENABLED", "1") == "1"


def _request(method: str, path: str, body: dict) -> dict:
    """Send an authenticated request to the API. Returns parsed JSON response."""
    if not API_ENABLED:
        return {"status": "disabled", "reason": "AI_INTEL_API_ENABLED=0"}

    url = f"{API_BASE}{path}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    # Generate idempotency key: scan_id + timestamp for retry safety
    scan_id = body.get("scan_id", "unknown")
    idempotency_key = f"{scan_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "X-Idempotency-Key": idempotency_key,
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"status": "error", "http_status": e.code, "detail": body}
    except urllib.error.URLError as e:
        return {"status": "error", "reason": str(e.reason)}


def post_batch(articles: list, stats: dict = None, scan_id: str = "") -> dict:
    """POST a batch of articles + daily stats to the API.

    Args:
        articles: list of article dicts (same shape as DB rows)
        stats: optional daily_stats dict
        scan_id: identifier for this scan run
    """
    if not API_ENABLED:
        return {"status": "disabled"}

    # Build API-compatible article list
    api_articles = []
    for a in articles:
        api_articles.append({
            "title": a.get("title", ""),
            "link": a.get("link", ""),
            "summary": a.get("summary", ""),
            "published": a.get("published", ""),
            "source_name": a.get("source_name", "unknown"),
            "category": a.get("category", "general"),
            "score_total": a.get("score_total", 0),
            "score_authority": a.get("score_authority", 0),
            "score_timeliness": a.get("score_timeliness", 0),
            "score_depth": a.get("score_depth", 0),
            "score_relevance": a.get("score_relevance", 0),
            "content_hash": a.get("content_hash", ""),
            "is_paper": bool(a.get("is_paper", False)),
            "paper_id": a.get("paper_id", ""),
        })

    payload = {
        "scan_id": scan_id,
        "articles": api_articles,
    }
    if stats:
        payload["stats"] = stats

    return _request("POST", "/api/admin/batch", payload)


def post_curation(curated: list, scan_id: str = "") -> dict:
    """POST curation results to the API.

    Args:
        curated: list of dicts with 'id', 'title_cn', 'summary_cn', 'why_it_matters'
        scan_id: identifier for this curation run
    """
    return _request("POST", "/api/admin/curation", {
        "scan_id": scan_id,
        "curated": curated,
    })


def health_check() -> dict:
    """Check if the API is reachable."""
    try:
        url = f"{API_BASE}/health"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "error", "reason": str(e)}
