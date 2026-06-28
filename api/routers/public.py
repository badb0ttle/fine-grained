"""Public API routes — read-only endpoints serving frontend data.

These endpoints directly reuse existing pipeline functions so
there is zero duplication of business logic.
"""

import json
import time
import html
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

from api.db import get_db
from api import PROJECT_DIR

router = APIRouter(prefix="/api", tags=["public"])


# ── In-memory cache for reading static JSON files ──

_leaderboard_cache: dict | None = None
_leaderboard_cache_time: float = 0.0
_LEADERBOARD_CACHE_TTL = 600  # 10 minutes

_clusters_cache: dict | None = None
_clusters_cache_time: float = 0.0
_CLUSTERS_CACHE_TTL = 600  # 10 minutes

# ── HTML entity cleaner ──

_ENTITY_RE = re.compile(r'&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;')

def _clean_html_entities(text: str | None) -> str:
    """Decode HTML entities like &nbsp; &quot; &#x27; in text fields."""
    if not text:
        return ""
    text = html.unescape(text)
    # Second pass: catch any entities missed by unescape
    text = _ENTITY_RE.sub('', text)
    return text

def _clean_article_fields(article: dict) -> dict:
    """Clean HTML entities from text fields in an article dict."""
    for key in ("title", "title_cn", "summary", "summary_cn"):
        if key in article and isinstance(article[key], str):
            article[key] = _clean_html_entities(article[key])
    return article

# ── Helpers ──

def _import_pipeline(module: str):
    """Lazy import a pipeline module."""
    import importlib
    return importlib.import_module(f"scripts.pipeline.{module}")


# ════════════════════════════════════════════════════════════════════
# GET /api/latest — curated articles (replaces data/latest.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/latest")
def get_latest():
    """Get curated articles — same output as export_latest_json()."""
    curator = _import_pipeline("curator")
    result = curator.export_latest_json()
    articles = result.get("articles", [])
    for a in articles:
        _clean_article_fields(a)
    return result


# ════════════════════════════════════════════════════════════════════
# GET /api/stats — dashboard stats (replaces data/stats.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/stats")
def get_stats():
    """Get dashboard stats — sources, score distribution, daily trends."""
    publisher = _import_pipeline("publisher")
    return publisher.export_stats_json()


# ════════════════════════════════════════════════════════════════════
# GET /api/search — FTS5 full-text search
# ════════════════════════════════════════════════════════════════════

@router.get("/search")
def search(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Full-text search via SQLite FTS5."""
    conn = get_db()
    try:
        # Use FTS5 prefix matching
        rows = conn.execute("""
            SELECT a.id, a.title, a.title_cn, a.link, a.summary, a.summary_cn,
                   a.source_name, a.category, a.published, a.score_total,
                   a.is_paper, a.paper_id,
                   snippet(articles_fts, 2, '<mark>', '</mark>', '…', 40) as snippet
            FROM articles_fts fts
            JOIN articles a ON fts.rowid = a.id
            WHERE articles_fts MATCH ? || '*'
            ORDER BY rank
            LIMIT ? OFFSET ?
        """, (q, limit, offset)).fetchall()

        results = []
        for r in rows:
            result = {
                "id": r["id"],
                "title": r["title"],
                "title_cn": r["title_cn"],
                "link": r["link"],
                "summary": (r["summary"] or "")[:300],
                "summary_cn": (r["summary_cn"] or "")[:300],
                "source": r["source_name"],
                "category": r["category"],
                "published": r["published"],
                "score": round(r["score_total"], 1) if r["score_total"] else 0,
                "is_paper": bool(r["is_paper"]),
                "paper_id": r["paper_id"],
                "snippet": r["snippet"],
            }
            results.append(_clean_article_fields(result))

        # Total count
        count_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM articles_fts WHERE articles_fts MATCH ? || '*'",
            (q,)
        ).fetchone()

        return {
            "query": q,
            "total": count_row["cnt"],
            "limit": limit,
            "offset": offset,
            "results": results,
        }
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════
# GET /api/trending — GitHub trending repos (replaces data/trending.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/trending")
def get_trending():
    """Get GitHub trending repos."""
    trending = _import_pipeline("github_trending")
    return trending.export_trending_json()


# ════════════════════════════════════════════════════════════════════
# GET /api/leaderboard — model leaderboard (replaces data/leaderboard.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/leaderboard")
def get_leaderboard():
    """Get model benchmark leaderboard."""
    tracker = _import_pipeline("model_tracker")
    return tracker.export_leaderboard_json()


# ════════════════════════════════════════════════════════════════════
# GET /api/model-leaderboard — external model rankings (replaces data/model_leaderboard.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/model-leaderboard")
def get_model_leaderboard():
    """Get model rankings from pre-generated model_leaderboard.json.
    
    Returns the cached file (refreshed every 10 min from disk).
    The file itself is regenerated by the publisher on each cron run.
    """
    global _leaderboard_cache, _leaderboard_cache_time
    
    if _leaderboard_cache is not None and (time.time() - _leaderboard_cache_time) < _LEADERBOARD_CACHE_TTL:
        return _leaderboard_cache
    
    path = DATA_DIR / "model_leaderboard.json"
    if not path.exists():
        return {"models": [], "error": "not_generated_yet"}
    
    result = json.loads(path.read_text())
    _leaderboard_cache = result
    _leaderboard_cache_time = time.time()
    return result


# ════════════════════════════════════════════════════════════════════
# GET /api/clusters — topic clusters (replaces data/clusters.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/clusters")
def get_clusters():
    """Get topic clusters from pre-generated clusters.json.
    
    Returns the cached file (refreshed every 10 min from disk).
    The file itself is regenerated by the publisher on each cron run.
    """
    global _clusters_cache, _clusters_cache_time
    
    if _clusters_cache is not None and (time.time() - _clusters_cache_time) < _CLUSTERS_CACHE_TTL:
        return _clusters_cache
    
    path = DATA_DIR / "clusters.json"
    if not path.exists():
        return {"clusters": [], "points": [], "error": "not_generated_yet"}
    
    result = json.loads(path.read_text())
    _clusters_cache = result
    _clusters_cache_time = time.time()
    return result


# ════════════════════════════════════════════════════════════════════
# GET /api/weekly — weekly AI reports
# ════════════════════════════════════════════════════════════════════

@router.get("/weekly")
def list_weekly():
    """List available weekly reports from index.json."""
    weekly_dir = PROJECT_DIR / "data" / "weekly"
    index_path = weekly_dir / "index.json"
    if not index_path.exists():
        return {"reports": []}

    try:
        data = json.loads(index_path.read_text())
        return {"reports": data.get("reports", [])}
    except Exception:
        return {"reports": []}


@router.get("/weekly/{report_id}")
def get_weekly(report_id: str, lang: str = "zh"):
    """Get a specific weekly report HTML by date (e.g. '2026-06-28')."""
    suffix = "_en" if lang == "en" else ""
    path = PROJECT_DIR / "data" / "weekly" / f"{report_id}{suffix}.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Weekly report '{report_id}' not found")

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=path.read_text(), media_type="text/html; charset=utf-8")
