#!/usr/bin/env python3
"""AI Intel Pipeline — shared config and DB access."""

import sqlite3
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent
DB_PATH = REPO_DIR / "data" / "ai_intel.db"

SOURCES = [
    {"name": "OpenAI Blog",          "url": "https://openai.com/blog/rss.xml",                    "category": "AI Lab"},
    {"name": "Google AI",            "url": "https://blog.research.google/feeds/posts/default",   "category": "AI Lab"},
    {"name": "ArXiv cs.AI",          "url": "https://rss.arxiv.org/rss/cs.AI",                    "category": "Paper"},
    {"name": "ArXiv cs.LG",          "url": "https://rss.arxiv.org/rss/cs.LG",                    "category": "Paper"},
    {"name": "ArXiv cs.CL",          "url": "https://rss.arxiv.org/rss/cs.CL",                    "category": "Paper"},
    {"name": "ArXiv cs.CV",          "url": "https://rss.arxiv.org/rss/cs.CV",                    "category": "Paper"},
    {"name": "ArXiv stat.ML",        "url": "https://rss.arxiv.org/rss/stat.ML",                  "category": "Paper"},
    {"name": "HuggingFace Blog",     "url": "https://huggingface.co/blog/feed.xml",               "category": "Community"},
    {"name": "Google DeepMind",      "url": "https://blog.google/technology/ai/rss/",             "category": "AI Lab"},
    {"name": "Apple ML Research",    "url": "https://machinelearning.apple.com/rss.xml",           "category": "AI Lab"},
    {"name": "NVIDIA Blog",          "url": "https://developer.nvidia.com/blog/feed",              "category": "AI Lab"},
    {"name": "PyTorch Blog",         "url": "https://pytorch.org/blog/feed.xml",                  "category": "Community"},
    {"name": "雷锋网 AI",         "url": "https://www.leiphone.com/feed",                        "category": "中文媒体"},
    {"name": "量子位",           "url": "https://www.qbitai.com/wp-json/wp/v2/posts?per_page=20", "category": "中文媒体", "type": "wp_api"},
    {"name": "TechCrunch AI",        "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Blog"},
    {"name": "VentureBeat AI",       "url": "https://feeds.feedburner.com/venturebeat/SZYF",       "category": "Blog"},
]


def get_db() -> sqlite3.Connection:
    """Get a WAL-mode SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
