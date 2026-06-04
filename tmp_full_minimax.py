import sqlite3
conn = sqlite3.connect('data/ai_intel.db')
r = conn.execute("SELECT id, title, summary FROM articles WHERE id = 8").fetchone()
print(f"ID={r[0]} | Title: {r[1]}")
print(f"Summary: {r[2]}")
conn.close()
