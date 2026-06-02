#!/usr/bin/env python3
"""Stage 1: Scanner — fetch RSS feeds, save raw articles to SQLite."""

import hashlib
import re
import time
from datetime import datetime, timezone

import feedparser
import requests

from . import SOURCES, get_db


def content_hash(title: str, link: str) -> str:
    return hashlib.sha256(f"{title.strip().lower()}|{link.strip()}".encode()).hexdigest()


def fetch_feed(source: dict) -> list[dict]:
    """Fetch a single RSS feed, return list of article dicts."""
    try:
        resp = requests.get(source["url"], timeout=15, headers={
            "User-Agent": "AI-Intel-Scanner/2.0"
        })
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        articles = []
        for entry in feed.entries[:20]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.updated_parsed)

            summary = entry.get("summary", "") or ""
            clean_summary = re.sub(r"<[^>]+>", "", summary)[:500]

            articles.append({
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "summary": clean_summary,
                "published": pub_date or "Unknown",
                "source_name": source["name"],
                "category": source["category"],
            })
        return articles
    except Exception as e:
        print(f"  ⚠️  {source['name']}: {e}")
        return []


def run() -> dict:
    """Run scanner, return stats dict."""
    print(f"📡 Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   {len(SOURCES)} sources configured\n")

    scanned_at = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    all_articles = []
    success_count = 0
    new_articles = 0

    for i, source in enumerate(SOURCES, 1):
        name = source["name"]
        print(f"  [{i}/{len(SOURCES)}] {name}...", end=" ", flush=True)
        articles = fetch_feed(source)

        if articles:
            success_count += 1
            all_articles.extend(articles)
            inserted = 0
            for a in articles:
                h = content_hash(a["title"], a["link"])
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO articles
                           (title, link, summary, published, source_name, category,
                            content_hash, scanned_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (a["title"], a["link"], a["summary"],
                         a["published"], a["source_name"], a["category"],
                         h, scanned_at)
                    )
                    if conn.total_changes > 0:
                        inserted += 1
                        new_articles += 1
                except Exception:
                    pass

            # Update source stats
            conn.execute(
                """INSERT INTO sources (name, url, category, last_success, article_count_last)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                   last_success = excluded.last_success,
                   consecutive_failures = 0,
                   article_count_last = excluded.article_count_last""",
                (name, source["url"], source["category"],
                 scanned_at, len(articles))
            )
            print(f"✅ {len(articles)} articles ({inserted} new)")
        else:
            conn.execute(
                """INSERT INTO sources (name, url, category, last_failure, consecutive_failures)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(name) DO UPDATE SET
                   last_failure = excluded.last_failure,
                   consecutive_failures = consecutive_failures + 1""",
                (name, source["url"], source["category"], scanned_at)
            )
            print("⚠️  failed")

    conn.commit()

    # Save daily stats
    date_str = datetime.now().strftime("%Y-%m-%d")
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.execute(
        """INSERT INTO daily_stats
           (date, total_sources, successful_sources, total_articles, new_articles)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
           total_sources = excluded.total_sources,
           successful_sources = excluded.successful_sources,
           total_articles = excluded.total_articles,
           new_articles = excluded.new_articles""",
        (date_str, len(SOURCES), success_count, total, new_articles)
    )
    conn.commit()
    conn.close()

    stats = {
        "scanned_at": scanned_at,
        "total_sources": len(SOURCES),
        "successful_sources": success_count,
        "total_articles": total,
        "new_articles": new_articles,
    }

    print(f"\n✅ Scanner done: {success_count}/{len(SOURCES)} sources, "
          f"{new_articles} new articles, {total} total in DB")
    return stats


if __name__ == "__main__":
    run()
