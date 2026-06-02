#!/usr/bin/env python3
"""Migrate existing JSON data into SQLite."""

import hashlib
import json
import sqlite3
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent
DB_PATH = REPO_DIR / "data" / "ai_intel.db"
RAW_JSON = REPO_DIR / "data" / "raw.json"
LATEST_JSON = REPO_DIR / "data" / "latest.json"
HISTORY_DIR = REPO_DIR / "data" / "history"

# Source definitions (mirror of rss_scanner.py SOURCES)
SOURCES = [
    {"name": "OpenAI Blog",          "url": "https://openai.com/blog/rss.xml",                    "category": "AI Lab"},
    {"name": "Google AI",            "url": "https://blog.research.google/feeds/posts/default",   "category": "AI Lab"},
    {"name": "ArXiv cs.AI",          "url": "https://rss.arxiv.org/rss/cs.AI",                    "category": "Paper"},
    {"name": "ArXiv cs.LG",          "url": "https://rss.arxiv.org/rss/cs.LG",                    "category": "Paper"},
    {"name": "ArXiv cs.CL",          "url": "https://rss.arxiv.org/rss/cs.CL",                    "category": "Paper"},
    {"name": "ArXiv cs.CV",          "url": "https://rss.arxiv.org/rss/cs.CV",                    "category": "Paper"},
    {"name": "ArXiv stat.ML",        "url": "https://rss.arxiv.org/rss/stat.ML",                  "category": "Paper"},
    {"name": "HuggingFace Blog",     "url": "https://huggingface.co/blog/feed.xml",               "category": "Community"},
    {"name": "Google DeepMind",      "url": "https://blog.google/technology/ai/rss/",             "category": "AI Lab"},
    {"name": "Apple ML Research",    "url": "https://machinelearning.apple.com/rss.xml",           "category": "AI Lab"},
    {"name": "NVIDIA Blog",          "url": "https://developer.nvidia.com/blog/feed",              "category": "AI Lab"},
    {"name": "PyTorch Blog",         "url": "https://pytorch.org/blog/feed.xml",                  "category": "Community"},
    {"name": "雷锋网 AI",         "url": "https://www.leiphone.com/feed",                        "category": "中文媒体"},
    {"name": "TechCrunch AI",        "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Blog"},
    {"name": "VentureBeat AI",       "url": "https://feeds.feedburner.com/venturebeat/SZYF",       "category": "Blog"},
]


def content_hash(title: str, link: str) -> str:
    return hashlib.sha256(f"{title.strip().lower()}|{link.strip()}".encode()).hexdigest()


def migrate_sources(conn: sqlite3.Connection):
    """Populate sources table from SOURCES definitions."""
    for s in SOURCES:
        conn.execute(
            """INSERT OR IGNORE INTO sources (name, url, category)
               VALUES (?, ?, ?)""",
            (s["name"], s["url"], s["category"])
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    print(f"  📡 Sources: {count} registered")


def migrate_raw(conn: sqlite3.Connection):
    """Import raw.json articles."""
    if not RAW_JSON.exists():
        print("  ⚠️  raw.json not found, skipping")
        return

    data = json.loads(RAW_JSON.read_text())
    scanned_at = data.get("scanned_at", "")
    articles = data.get("articles", [])
    inserted = 0

    for a in articles:
        h = content_hash(a["title"], a["link"])
        try:
            conn.execute(
                """INSERT OR IGNORE INTO articles
                   (title, link, summary, published, source_name, category,
                    content_hash, scanned_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (a["title"], a["link"], a.get("summary", ""),
                 a.get("published", ""), a.get("source", ""),
                 a.get("category", ""), h, scanned_at)
            )
            if conn.total_changes > 0:
                inserted += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    print(f"  📄 raw.json: {inserted} articles imported (total {len(articles)} in file)")


def migrate_curated(conn: sqlite3.Connection):
    """Apply curated data from latest.json (title_cn, summary_cn, curated flag)."""
    if not LATEST_JSON.exists():
        print("  ⚠️  latest.json not found, skipping")
        return

    data = json.loads(LATEST_JSON.read_text())
    curated_at = data.get("curated_at", "")
    articles = data.get("articles", [])
    updated = 0

    for a in articles:
        try:
            conn.execute(
                """UPDATE articles SET
                   title_cn = ?,
                   summary_cn = ?,
                   curated = 1,
                   curated_at = ?
                   WHERE link = ?""",
                (a.get("title_cn", ""), a.get("summary_cn", ""),
                 curated_at, a["link"])
            )
            updated += conn.total_changes
        except Exception as e:
            print(f"  ⚠️  Failed to update {a.get('title', '?')}: {e}")

    conn.commit()
    print(f"  ⭐ latest.json: {updated} articles marked curated + translated")


def migrate_history(conn: sqlite3.Connection):
    """Import daily_stats from history JSON files."""
    if not HISTORY_DIR.exists():
        print("  ⚠️  history dir not found, skipping")
        return

    count = 0
    for f in sorted(HISTORY_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        date_str = f.stem  # "2026-06-02"
        scanned_at = data.get("scanned_at", "")

        try:
            conn.execute(
                """INSERT OR IGNORE INTO daily_stats
                   (date, total_sources, successful_sources, total_articles)
                   VALUES (?, ?, ?, ?)""",
                (date_str, data.get("total_sources", 0),
                 data.get("successful_sources", 0),
                 data.get("total_articles", 0))
            )
            count += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    print(f"  📅 History: {count} daily stats imported")


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    print("🔄 Migrating data to SQLite...\n")
    migrate_sources(conn)
    migrate_raw(conn)
    migrate_curated(conn)
    migrate_history(conn)

    # Summary
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    curated = conn.execute("SELECT COUNT(*) FROM articles WHERE curated=1").fetchone()[0]
    conn.close()

    print(f"\n✅ Migration complete!")
    print(f"   📰 Total articles: {total}")
    print(f"   ⭐ Curated: {curated}")


if __name__ == "__main__":
    main()
