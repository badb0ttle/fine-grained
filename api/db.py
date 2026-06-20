"""Database connection — thin wrapper over existing pipeline SQLite access."""

import sqlite3
import sys
from pathlib import Path

# Allow importing from scripts/pipeline
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from scripts.pipeline import get_db as _pipeline_get_db
from api.config import DB_PATH


def get_db() -> sqlite3.Connection:
    """Get a WAL-mode SQLite connection with row_factory.

    Delegates to the existing pipeline implementation so both
    the API and cron jobs share the exact same DB access logic.
    """
    return _pipeline_get_db()


def check_db_health() -> dict:
    """Quick health check — can we connect and query? Returns status dict."""
    try:
        conn = get_db()
        row = conn.execute("SELECT COUNT(*) as cnt FROM articles").fetchone()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        return {
            "status": "ok",
            "article_count": row["cnt"],
            "tables": [t["name"] for t in tables],
            "db_path": str(DB_PATH),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def ensure_schema() -> list[str]:
    """Create any missing tables needed by the API layer.

    The core schema (articles, sources, daily_stats, FTS5) is managed by
    db_init.py — this only adds API-specific tables.
    """
    conn = get_db()
    created = []
    try:
        # ── Idempotency keys (for cron batch dedup) ──
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_idempotency_keys (
                key         TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'processing',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Trigger to auto-update updated_at
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS api_idempotency_keys_updated
            AFTER UPDATE ON api_idempotency_keys
            FOR EACH ROW
            BEGIN
                UPDATE api_idempotency_keys SET updated_at = datetime('now') WHERE key = NEW.key;
            END
        """)
        conn.commit()
        created.append("api_idempotency_keys")
    finally:
        conn.close()
    return created
