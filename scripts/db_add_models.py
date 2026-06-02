#!/usr/bin/env python3
"""Add model tracking tables to SQLite."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.pipeline import get_db

conn = get_db()
conn.executescript("""
CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    provider    TEXT,
    release_date TEXT,
    parameters  TEXT,
    context_window TEXT,
    modalities  TEXT,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS model_benchmarks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id    INTEGER REFERENCES models(id),
    benchmark   TEXT NOT NULL,
    score       TEXT NOT NULL,
    source_article TEXT,
    reported_at TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mb_model ON model_benchmarks(model_id);
CREATE INDEX IF NOT EXISTS idx_mb_benchmark ON model_benchmarks(benchmark);
""")
conn.commit()
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'model%'").fetchall()
print(f"✅ Added: {[t[0] for t in tables]}")
conn.close()
