#!/usr/bin/env python3
"""Generate RSS 2.0 feed from latest curated articles."""

import json
import sys
from pathlib import Path
from datetime import datetime
from html import escape

REPO_DIR = Path(__file__).resolve().parent.parent

SITE_URL = "https://ai.hjhai.xyz"
SITE_TITLE = "AllOfAI — 每日 AI 技术动态"
SITE_DESC = "每日自动扫描全球 AI 信源，由 LLM 精选并深度解读的 AI 技术情报"

def rfc822_date(iso_str: str) -> str:
    """Convert ISO date string to RFC 822 format."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

def generate() -> str:
    data_path = REPO_DIR / "data" / "latest.json"
    if not data_path.exists():
        print(f"⚠️  {data_path} not found", file=sys.stderr)
        return ""

    data = json.loads(data_path.read_text())
    articles = data.get("articles", [])[:30]  # last 30 for RSS
    now = rfc822_date(data.get("curated_at", datetime.utcnow().isoformat()))

    items = []
    for i, a in enumerate(articles):
        title = a.get("title_cn") or a.get("title", "")
        link = a.get("link", "")
        summary = (a.get("summary_cn") or a.get("summary", ""))[:500]
        pub_date = rfc822_date(a.get("published", ""))
        source = a.get("source", "")
        category = a.get("category", "")
        why = a.get("why_it_matters", "")

        desc_parts = [f"<p>{escape(summary)}</p>"]
        if why:
            desc_parts.append(f"<p><strong>重要性：</strong>{escape(why)}</p>")
        desc_parts.append(f"<p>来源：{escape(source)} · 分类：{escape(category)}</p>")

        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <link>{escape(link)}</link>
      <guid isPermaLink="false">ai-intel-{a.get('link','').split('/')[-1] or i}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{"".join(desc_parts)}</description>
      <category>{escape(category)}</category>
      <source url="{SITE_URL}">{escape(source)}</source>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_TITLE}</title>
    <link>{SITE_URL}</link>
    <description>{SITE_DESC}</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>
    <generator>AllOfAI Pipeline</generator>
{chr(10).join(items)}
  </channel>
</rss>"""
    return rss

def main():
    rss = generate()
    if not rss:
        return 1

    # Write to docs/ for deployment
    out_dir = REPO_DIR / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rss.xml"
    out_path.write_text(rss)
    print(f"✅ RSS: {out_path} ({len(rss)} bytes)")

    # Also write to data/ for reference
    data_out = REPO_DIR / "data" / "rss.xml"
    data_out.write_text(rss)

    return 0

if __name__ == "__main__":
    sys.exit(main())
