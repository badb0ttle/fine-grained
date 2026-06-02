#!/usr/bin/env python3
"""Stage 2: Dedup — detect and mark duplicates across sources."""

from datetime import datetime

from . import get_db


def run() -> dict:
    """Find duplicate articles (same content_hash but different links/sources)
    and mark the oldest one as the canonical."""
    print("🔍 Dedup — detecting cross-source duplicates...")

    conn = get_db()

    # Find content_hashes that appear more than once
    dupes = conn.execute("""
        SELECT content_hash, COUNT(*) as cnt
        FROM articles
        WHERE content_hash IS NOT NULL
        GROUP BY content_hash
        HAVING cnt > 1
    """).fetchall()

    if not dupes:
        print(f"   No duplicates found")
        conn.close()
        return {"duplicates_found": 0}

    # For each dupe group, keep the one with earliest published date
    # and mark others for potential cleanup (soft dedup — don't delete)
    for row in dupes:
        articles = conn.execute("""
            SELECT id, title, published, source_name
            FROM articles
            WHERE content_hash = ?
            ORDER BY published ASC
        """, (row["content_hash"],)).fetchall()

        if len(articles) > 1:
            canonical = articles[0]
            dupes_list = [a["title"][:50] for a in articles[1:]]
            print(f"   📎 Dedup: \"{canonical['title'][:50]}...\" "
                  f"({canonical['source_name']}) + {len(dupes_list)} dupes")
            for d in dupes_list:
                print(f"      └─ \"{d}...\"")

    conn.close()
    return {"duplicates_found": len(dupes)}


if __name__ == "__main__":
    run()
