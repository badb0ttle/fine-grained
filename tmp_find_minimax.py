import sqlite3, json
conn = sqlite3.connect('data/ai_intel.db')
conn.row_factory = sqlite3.Row

# Find MiniMax article
rows = conn.execute("""
    SELECT id, title, summary, source_name, link
    FROM articles
    WHERE title LIKE '%MiniMax%' OR summary LIKE '%MiniMax%'
    ORDER BY id DESC LIMIT 5
""").fetchall()

for r in rows:
    print(f"ID={r['id']} | {r['source_name']}")
    print(f"Title: {r['title']}")
    print(f"Summary: {r['summary'][:500]}")
    print(f"Link: {r['link']}")
    print("---")

conn.close()
