#!/usr/bin/env python3
"""Initialize SQLite database for AI Intel."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ai_intel.db"


SCHEMA = """
-- ========== Articles (主表) ==========
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    link            TEXT    NOT NULL UNIQUE,
    summary         TEXT,
    published       TEXT,
    source_name     TEXT    NOT NULL,
    category        TEXT,
    content_hash    TEXT,                          -- SHA256(title+link) for dedup
    -- LLM processing fields (Phase 2)
    title_cn        TEXT,
    summary_cn      TEXT,
    why_it_matters  TEXT,
    -- Quality scores (Phase 2)
    score_authority    REAL DEFAULT 0,
    score_timeliness   REAL DEFAULT 0,
    score_depth        REAL DEFAULT 0,
    score_relevance    REAL DEFAULT 0,
    score_total        REAL DEFAULT 0,
    -- Paper-specific fields (Phase 2)
    is_paper        INTEGER DEFAULT 0,
    paper_id        TEXT,
    paper_authors   TEXT,
    paper_method    TEXT,
    paper_benchmark TEXT,
    paper_takeaway  TEXT,
    github_repo     TEXT,                          -- linked GitHub repo
    -- Curation
    curated         INTEGER DEFAULT 0,             -- 1 = in top 10
    curated_at      TEXT,
    -- Metadata
    scanned_at      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- ========== Sources (信源健康监控) ==========
CREATE TABLE IF NOT EXISTS sources (
    name                 TEXT PRIMARY KEY,
    url                  TEXT,
    category             TEXT,
    last_success         TEXT,
    last_failure         TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    article_count_last   INTEGER DEFAULT 0,
    avg_response_ms      REAL
);

-- ========== Daily Stats (每日统计) ==========
CREATE TABLE IF NOT EXISTS daily_stats (
    date               TEXT PRIMARY KEY,            -- YYYY-MM-DD
    total_sources      INTEGER,
    successful_sources INTEGER,
    total_articles     INTEGER,
    new_articles       INTEGER,
    curated_count      INTEGER,
    pipeline_duration_ms INTEGER,
    top_categories     TEXT                         -- JSON
);

-- ========== Indexes ==========
CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source_name);
CREATE INDEX IF NOT EXISTS idx_articles_category  ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_published  ON articles(published);
CREATE INDEX IF NOT EXISTS idx_articles_scanned    ON articles(scanned_at);
CREATE INDEX IF NOT EXISTS idx_articles_curated    ON articles(curated);
CREATE INDEX IF NOT EXISTS idx_articles_score      ON articles(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_articles_is_paper   ON articles(is_paper);
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_hash ON articles(content_hash);

-- ========== FTS5 全文搜索 ==========
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title,
    summary,
    title_cn,
    summary_cn,
    source_name,
    category,
    content='articles',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS trg_articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES (new.id, new.title, new.summary, new.title_cn, new.summary_cn, new.source_name, new.category);
END;

CREATE TRIGGER IF NOT EXISTS trg_articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES ('delete', old.id, old.title, old.summary, old.title_cn, old.summary_cn, old.source_name, old.category);
END;

CREATE TRIGGER IF NOT EXISTS trg_articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES ('delete', old.id, old.title, old.summary, old.title_cn, old.summary_cn, old.source_name, old.category);
    INSERT INTO articles_fts(rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES (new.id, new.title, new.summary, new.title_cn, new.summary_cn, new.source_name, new.category);
END;
"""


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create database and tables if not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_db()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"✅ Database initialized at {DB_PATH}")
    print(f"📊 Tables: {', '.join(t[0] for t in tables)}")
    conn.close()
