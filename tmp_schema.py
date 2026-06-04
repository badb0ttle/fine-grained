import sqlite3
conn = sqlite3.connect('data/ai_intel.db')
schema = conn.execute("PRAGMA table_info(articles)").fetchall()
for row in schema:
    print(row)
conn.close()
