#!/usr/bin/env python3
"""Generate sitemap.xml for ai.hjhai.xyz."""

import json
import sys
from pathlib import Path
from datetime import datetime

REPO_DIR = Path(__file__).resolve().parent.parent
SITE_URL = "https://ai.hjhai.xyz"

def generate() -> str:
    urls = [
        ("/", "daily", "1.0"),
        ("/leaderboard", "daily", "0.9"),
        ("/timeline", "daily", "0.8"),
        ("/clusters", "weekly", "0.7"),
        ("/weekly", "daily", "0.9"),
        ("/about", "monthly", "0.8"),
    ]

    # Add weekly detail pages
    weekly_index = REPO_DIR / "data" / "weekly" / "index.json"
    if weekly_index.exists():
        index_data = json.loads(weekly_index.read_text())
        weeks = index_data.get("reports", [])
        for w in weeks[:12]:
            date = w.get("date", "")
            if date:
                urls.append((f"/weekly/{date}", "weekly", "0.7"))

    now = datetime.utcnow().strftime("%Y-%m-%d")
    entries = []
    for path, freq, pri in urls:
        entries.append(f"""  <url>
    <loc>{SITE_URL}{path}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{pri}</priority>
  </url>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(entries)}
</urlset>"""

def main():
    sitemap = generate()
    out_path = REPO_DIR / "docs" / "sitemap.xml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(sitemap)
    print(f"✅ Sitemap: {out_path} ({len(sitemap)} bytes)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
