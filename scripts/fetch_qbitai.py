#!/usr/bin/env python3
"""Fetch 量子位 (qbitai.com) articles via WP REST API, output JSON for import."""
import json, re, sys
import requests

SOURCE = {
    "name": "量子位",
    "url": "https://www.qbitai.com/wp-json/wp/v2/posts?per_page=20",
    "category": "中文媒体",
}

def fetch():
    resp = requests.get(SOURCE["url"], timeout=20, headers={
        "User-Agent": "AI-Intel-Scanner/2.0"
    })
    resp.raise_for_status()
    posts = json.loads(resp.text)
    if not isinstance(posts, list):
        print(json.dumps({"error": f"Unexpected type: {type(posts).__name__}", "articles": []}))
        return

    articles = []
    for post in posts[:20]:
        title = post.get("title", {})
        if isinstance(title, dict):
            title = title.get("rendered", "Untitled")
        excerpt = post.get("excerpt", {})
        if isinstance(excerpt, dict):
            excerpt_text = excerpt.get("rendered", "")
        else:
            excerpt_text = str(excerpt)
        summary = re.sub(r"<[^>]+>", "", excerpt_text)[:500]
        link = post.get("link", "")
        pub_date = post.get("date", "") or post.get("date_gmt", "")

        articles.append({
            "title": title,
            "link": link,
            "summary": summary,
            "published": pub_date or "Unknown",
            "source_name": SOURCE["name"],
            "category": SOURCE["category"],
        })

    print(json.dumps({"source": SOURCE["name"], "count": len(articles), "articles": articles}, ensure_ascii=False))

if __name__ == "__main__":
    try:
        fetch()
    except Exception as e:
        print(json.dumps({"error": str(e), "articles": []}))
