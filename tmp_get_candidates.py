import sqlite3, json
conn = sqlite3.connect('data/ai_intel.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT id, title, source_name, score_total, summary, link, published, paper_id,
           title_cn, summary_cn, why_it_matters
    FROM articles
    WHERE curated = 0 AND score_total > 0
    ORDER BY score_total DESC
    LIMIT 20
""").fetchall()

results = []
for r in rows:
    results.append({
        "id": r["id"],
        "title": r["title"],
        "source": r["source_name"],
        "score": round(r["score_total"], 1),
        "link": r["link"] or "",
        "published": r["published"],
        "paper_id": r["paper_id"] or ""
    })

print(json.dumps(results, ensure_ascii=False, indent=2))
conn.close()
