"""Public API routes — read-only endpoints serving frontend data.

These endpoints directly reuse existing pipeline functions so
there is zero duplication of business logic.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query, HTTPException

from api.db import get_db
from api import PROJECT_DIR

router = APIRouter(prefix="/api", tags=["public"])


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
    return curator.export_latest_json()


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
            results.append({
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
            })

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
    """Get external model rankings (OpenRouter / Chatbot Arena)."""
    lb = _import_pipeline("model_leaderboard")
    return lb.fetch_and_export()


# ════════════════════════════════════════════════════════════════════
# GET /api/clusters — topic clusters (replaces data/clusters.json)
# ════════════════════════════════════════════════════════════════════

@router.get("/clusters")
def get_clusters():
    """Get topic clusters for visualization."""
    cluster = _import_pipeline("cluster_viz")
    return cluster.compute_clusters()


# ════════════════════════════════════════════════════════════════════
# GET /api/weekly — weekly AI reports
# ════════════════════════════════════════════════════════════════════

@router.get("/weekly")
def list_weekly():
    """List available weekly reports."""
    weekly_dir = PROJECT_DIR / "data" / "weekly"
    if not weekly_dir.exists():
        return {"reports": []}

    reports = []
    for f in sorted(weekly_dir.glob("*.json"), reverse=True):
        reports.append({
            "id": f.stem,
            "file": f.name,
            "size": f.stat().st_size,
        })

    return {"reports": reports}


@router.get("/weekly/{report_id}")
def get_weekly(report_id: str):
    """Get a specific weekly report by ID (e.g. '2026-W25')."""
    path = PROJECT_DIR / "data" / "weekly" / f"{report_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Weekly report '{report_id}' not found")

    data = json.loads(path.read_text())
    return data
