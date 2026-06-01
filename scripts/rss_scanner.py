#!/usr/bin/env python3
"""AI Intelligence RSS Scanner — scan top AI sources and output structured data."""

import json
import time
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
SUMMARY_FILE = DATA_DIR / "latest.json"
HISTORY_DIR = DATA_DIR / "history"

SOURCES = [
    # AI Labs & Research
    {"name": "OpenAI Blog",       "url": "https://openai.com/blog/rss.xml",                "category": "AI Lab"},
    {"name": "Google AI",         "url": "https://blog.research.google/feeds/posts/default", "category": "AI Lab"},
    {"name": "DeepMind Blog",     "url": "https://deepmind.google/discover/blog/rss.xml",    "category": "AI Lab"},
    {"name": "Meta AI",           "url": "https://ai.meta.com/blog/rss.xml",                "category": "AI Lab"},
    {"name": "Anthropic Blog",    "url": "https://www.anthropic.com/feed.xml",              "category": "AI Lab"},
    {"name": "Mistral AI News",   "url": "https://mistral.ai/news/rss.xml",                 "category": "AI Lab"},
    
    # ArXiv (ML recent papers)
    {"name": "ArXiv cs.AI",       "url": "https://rss.arxiv.org/rss/cs.AI",                 "category": "Paper"},
    {"name": "ArXiv cs.LG",       "url": "https://rss.arxiv.org/rss/cs.LG",                 "category": "Paper"},
    {"name": "ArXiv cs.CL",       "url": "https://rss.arxiv.org/rss/cs.CL",                 "category": "Paper"},
    {"name": "ArXiv stat.ML",     "url": "https://rss.arxiv.org/rss/stat.ML",               "category": "Paper"},
    
    # Tech & AI Media
    {"name": "HuggingFace Blog",  "url": "https://huggingface.co/blog/feed.xml",            "category": "Community"},
    {"name": "Hacker News (AI)",  "url": "https://hnrss.org/frontpage?q=AI+OR+LLM+OR+GPT+OR+neural&count=15", "category": "Discussion"},
    {"name": "The Gradient",      "url": "https://thegradient.pub/feed.xml",                "category": "Blog"},
    {"name": "Lil'Log (Lilian Weng)", "url": "https://lilianweng.github.io/feed.xml",      "category": "Blog"},
    {"name": "Stability AI",      "url": "https://stability.ai/feed.xml",                   "category": "AI Lab"},
    {"name": "Cohere Research",   "url": "https://cohere.com/blog/feed.xml",                "category": "AI Lab"},
]


def fetch_feed(source):
    """Fetch and parse a single RSS feed."""
    try:
        resp = requests.get(source["url"], timeout=15, headers={
            "User-Agent": "AI-Intel-Scanner/1.0"
        })
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        
        articles = []
        for entry in feed.entries[:20]:  # Keep top 20 per source
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.updated_parsed)
            
            summary = entry.get("summary", "") or ""
            # Strip HTML tags for clean display
            clean_summary = re.sub(r"<[^>]+>", "", summary)[:500]
            
            articles.append({
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "summary": clean_summary,
                "published": pub_date or "Unknown",
                "source": source["name"],
                "category": source["category"],
            })
        
        return articles
    except Exception as e:
        print(f"  ⚠️  {source['name']}: {e}")
        return []


def scan_all():
    """Scan all sources and return combined results."""
    print(f"🤖 AI Intel Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 Scanning {len(SOURCES)} sources...\n")
    
    all_articles = []
    success_count = 0
    
    for i, source in enumerate(SOURCES, 1):
        print(f"  [{i}/{len(SOURCES)}] {source['name']}...", end=" ", flush=True)
        articles = fetch_feed(source)
        if articles:
            success_count += 1
            all_articles.extend(articles)
            print(f"✅ {len(articles)} articles")
        else:
            print("⚠️  skipped")
    
    # Sort by date (newest first), handling "Unknown"
    def sort_key(a):
        try:
            return a["published"]
        except:
            return ""
    all_articles.sort(key=sort_key, reverse=True)
    
    # Deduplicate by title
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"].strip().lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    
    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_sources": len(SOURCES),
        "successful_sources": success_count,
        "total_articles": len(unique),
        "articles": unique,
    }
    
    return result


def save_result(result):
    """Save scan result to JSON files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save latest
    with open(SUMMARY_FILE, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # Save history snapshot (one per day)
    date_str = datetime.now().strftime("%Y-%m-%d")
    history_file = HISTORY_DIR / f"{date_str}.json"
    with open(history_file, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved: {len(result['articles'])} articles to latest.json")
    print(f"💾 History: {history_file.name}")
    
    return result


def print_summary(result):
    """Print a human-readable summary (for cron delivery)."""
    articles = result["articles"]
    by_cat = {}
    for a in articles:
        cat = a["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(a)
    
    print(f"\n{'='*60}")
    print(f"📊  SUMMARY — {result['scanned_at'][:10]}")
    print(f"   Sources: {result['successful_sources']}/{result['total_sources']}")
    print(f"   Articles: {len(articles)}")
    print(f"{'='*60}\n")
    
    for cat, items in sorted(by_cat.items()):
        print(f"▸ {cat} ({len(items)})")
        for a in items[:5]:
            print(f"  • {a['title']}")
            print(f"    {a['source']} | {a['published']}")
            print(f"    {a['link']}")
        if len(items) > 5:
            print(f"    ... +{len(items)-5} more")
        print()


if __name__ == "__main__":
    result = scan_all()
    save_result(result)
    print_summary(result)
