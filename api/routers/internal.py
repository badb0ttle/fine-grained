"""Internal API routes — write endpoints protected by API key.

These endpoints are called by the cron pipeline (publisher.py) and 
require Bearer token authentication + idempotency-key support.
"""

import json
import secrets
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.db import get_db
from api.config import API_KEY_PREFIX, API_KEY_LENGTH, MAX_ARTICLES_PER_BATCH

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer(auto_error=True)


# ── In-memory API key (loaded once from env) ──
# In production this is set via .env on ECS
import os
_API_KEY = os.getenv("AI_INTEL_API_KEY", "")
if not _API_KEY:
    # Generate a temporary dev key — cron jobs must set AI_INTEL_API_KEY
    _API_KEY = API_KEY_PREFIX + secrets.token_hex(API_KEY_LENGTH // 2)
    print(f"⚠️  No AI_INTEL_API_KEY set — generated temporary dev key")


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate Bearer token against the configured API key."""
    token = credentials.credentials
    if not token or token != _API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# ════════════════════════════════════════════════════════════════════
# POST /api/admin/batch — cron batch insert (articles + stats)
# ════════════════════════════════════════════════════════════════════

@router.post("/batch")
def post_batch(
    payload: dict,
    request: Request,
    _token: str = Depends(verify_api_key),
):
    """Receive a batch of articles from the cron scanner pipeline.

    Request body:
    {
        "scan_id": "2026-06-21T14:00:00Z",
        "articles": [
            {
                "id": null,              // null = auto-assign
                "title": "...",
                "link": "...",
                "summary": "...",
                "published": "2026-06-21T12:00:00Z",
                "source_name": "ArXiv",
                "category": "llm",
                "score_total": 75.5,
                ...
            }
        ],
        "stats": {                       // optional daily_stats update
            "date": "2026-06-21",
            "total_sources": 8,
            "successful_sources": 7,
            "total_articles": 120,
            "new_articles": 45,
            "curated_count": 10
        }
    }

    Idempotency: include X-Idempotency-Key header.
    """
    idempotency_key = request.headers.get("X-Idempotency-Key", "")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header required")

    conn = get_db()
    try:
        # ── Idempotency check ──
        existing = conn.execute(
            "SELECT status, created_at FROM api_idempotency_keys WHERE key = ?",
            (idempotency_key,)
        ).fetchone()
        if existing:
            return {
                "status": "duplicate",
                "message": f"Batch already processed at {existing['created_at']}",
                "original_status": existing["status"],
            }

        # Record idempotency key
        conn.execute(
            "INSERT INTO api_idempotency_keys (key, status) VALUES (?, 'processing')",
            (idempotency_key,)
        )
        conn.commit()

        # ── Insert articles ──
        articles = payload.get("articles", [])
        if len(articles) > MAX_ARTICLES_PER_BATCH:
            conn.execute(
                "UPDATE api_idempotency_keys SET status = 'rejected' WHERE key = ?",
                (idempotency_key,)
            )
            conn.commit()
            raise HTTPException(
                status_code=413,
                detail=f"Too many articles: {len(articles)} > {MAX_ARTICLES_PER_BATCH}"
            )

        inserted = 0
        skipped = 0
        cur = conn.cursor()

        for a in articles:
            # Require content_hash — enforced at DB level too (NOT NULL + trigger)
            if not a.get("content_hash"):
                skipped += 1
                continue

            # Dedup: skip if content_hash already in DB
            dup = conn.execute(
                "SELECT id FROM articles WHERE content_hash = ?",
                (a["content_hash"],)
            ).fetchone()
            if dup:
                skipped += 1
                continue

            cur.execute("""
                INSERT INTO articles (
                    title, link, summary, published, source_name, category,
                    score_total, score_authority, score_timeliness,
                    score_depth, score_relevance, content_hash,
                    is_paper, paper_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a.get("title", ""),
                a.get("link", ""),
                a.get("summary", ""),
                a.get("published", ""),
                a.get("source_name", "unknown"),
                a.get("category", "general"),
                a.get("score_total", 0),
                a.get("score_authority", 0),
                a.get("score_timeliness", 0),
                a.get("score_depth", 0),
                a.get("score_relevance", 0),
                a.get("content_hash", ""),
                int(a.get("is_paper", False)),
                a.get("paper_id", ""),
            ))
            inserted += 1

        # ── Update daily_stats ──
        stats = payload.get("stats")
        if stats:
            conn.execute("""
                INSERT INTO daily_stats (
                    date, total_sources, successful_sources,
                    total_articles, new_articles, curated_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_sources = excluded.total_sources,
                    successful_sources = excluded.successful_sources,
                    total_articles = excluded.total_articles,
                    new_articles = excluded.new_articles,
                    curated_count = excluded.curated_count
            """, (
                stats.get("date", ""),
                stats.get("total_sources", 0),
                stats.get("successful_sources", 0),
                stats.get("total_articles", 0),
                stats.get("new_articles", 0),
                stats.get("curated_count", 0),
            ))

        conn.commit()

        # Update idempotency key status
        conn.execute(
            "UPDATE api_idempotency_keys SET status = 'completed' WHERE key = ?",
            (idempotency_key,)
        )
        conn.commit()

        return {
            "status": "ok",
            "inserted": inserted,
            "skipped": skipped,
            "scan_id": payload.get("scan_id", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        # Mark idempotency key as failed if we recorded it
        try:
            conn.execute(
                "UPDATE api_idempotency_keys SET status = ? WHERE key = ?",
                (f"error: {str(e)[:200]}", idempotency_key)
            )
            conn.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════
# POST /api/admin/curation — push curation results
# ════════════════════════════════════════════════════════════════════

@router.post("/curation")
def post_curation(
    payload: dict,
    request: Request,
    _token: str = Depends(verify_api_key),
):
    """Apply LLM curation results to existing articles.

    Request body:
    {
        "curated": [
            {"id": 123, "title_cn": "中文标题", "summary_cn": "中文摘要", "why_it_matters": "…"},
            ...
        ],
        "scan_id": "optional reference"
    }
    """
    idempotency_key = request.headers.get("X-Idempotency-Key", "")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header required")

    conn = get_db()
    try:
        # Idempotency check
        existing = conn.execute(
            "SELECT status FROM api_idempotency_keys WHERE key = ?",
            (idempotency_key,)
        ).fetchone()
        if existing:
            return {"status": "duplicate", "original_status": existing["status"]}

        conn.execute(
            "INSERT INTO api_idempotency_keys (key, status) VALUES (?, 'processing')",
            (idempotency_key,)
        )
        conn.commit()

        curated_at = datetime.now(timezone.utc).isoformat()
        updated = 0

        for item in payload.get("curated", []):
            if "id" not in item:
                continue
            conn.execute("""
                UPDATE articles SET
                    title_cn = ?, summary_cn = ?, why_it_matters = ?,
                    curated = 1, curated_at = ?
                WHERE id = ?
            """, (
                item.get("title_cn", ""),
                item.get("summary_cn", ""),
                item.get("why_it_matters", ""),
                curated_at,
                item["id"],
            ))
            updated += 1

        conn.execute(
            "UPDATE api_idempotency_keys SET status = 'completed' WHERE key = ?",
            (idempotency_key,)
        )
        conn.commit()

        return {"status": "ok", "curated": updated, "curated_at": curated_at}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════
# GET /api/admin/recent-runs — recent cron run history
# ════════════════════════════════════════════════════════════════════

@router.get("/recent-runs")
def get_recent_runs(
    _token: str = Depends(verify_api_key),
    limit: int = 20,
):
    """List recent idempotency key runs for debugging."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT key, status, created_at FROM api_idempotency_keys ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return {
            "total": len(rows),
            "runs": [
                {"key": r["key"][:16] + "…", "status": r["status"], "created_at": r["created_at"]}
                for r in rows
            ]
        }
    finally:
        conn.close()
