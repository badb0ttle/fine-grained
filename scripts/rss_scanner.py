#!/usr/bin/env python3
"""
AI 情报 RSS 扫描器 (RSS Scanner)
=================================
独立运行的全量 RSS 扫描脚本，覆盖 15 个 AI 信源。

扫描流程：
1. 依次请求每个信源的 RSS/Atom feed（feedparser 解析）
2. 每条记录提取标题、链接、摘要（去HTML）、发布时间
3. 合并所有信源结果，按时间降序排序
4. 按标题前80字符去重（同标题只保留第一条）
5. 输出到 data/raw.json（最新快照）+ data/history/YYYY-MM-DD.json（每日存档）

信源覆盖：
- AI Lab：OpenAI, Google AI, DeepMind, Apple ML, NVIDIA
- Paper：ArXiv (cs.AI, cs.LG, cs.CL, cs.CV, stat.ML)
- Community：HuggingFace, PyTorch
- 中文媒体：雷锋网 AI
- Blog：TechCrunch AI, VentureBeat AI

技术栈：feedparser（RSS解析），requests（HTTP），re（HTML清洗）
"""

import json
import time
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

# ── 路径常量 ──
DATA_DIR = Path(__file__).parent.parent / "data"
SUMMARY_FILE = DATA_DIR / "raw.json"       # 最新快照
HISTORY_DIR = DATA_DIR / "history"          # 每日存档目录


# ── 信源定义 ──
SOURCES = [
    # ✅ Working: AI Labs & Research
    {"name": "OpenAI Blog",          "url": "https://openai.com/blog/rss.xml",                    "category": "AI Lab"},
    {"name": "Google AI",            "url": "https://blog.research.google/feeds/posts/default",   "category": "AI Lab"},

    # ✅ Working: ArXiv（最新论文）
    {"name": "ArXiv cs.AI",          "url": "https://rss.arxiv.org/rss/cs.AI",                    "category": "Paper"},
    {"name": "ArXiv cs.LG",          "url": "https://rss.arxiv.org/rss/cs.LG",                    "category": "Paper"},
    {"name": "ArXiv cs.CL",          "url": "https://rss.arxiv.org/rss/cs.CL",                    "category": "Paper"},
    {"name": "ArXiv cs.CV",          "url": "https://rss.arxiv.org/rss/cs.CV",                    "category": "Paper"},
    {"name": "ArXiv stat.ML",        "url": "https://rss.arxiv.org/rss/stat.ML",                  "category": "Paper"},

    # ✅ Working: Community
    {"name": "HuggingFace Blog",     "url": "https://huggingface.co/blog/feed.xml",               "category": "Community"},

    # 🔄 Alternative sources（可能因网络波动不稳定）
    {"name": "Google DeepMind",      "url": "https://blog.google/technology/ai/rss/",             "category": "AI Lab"},
    {"name": "Apple ML Research",    "url": "https://machinelearning.apple.com/rss.xml",           "category": "AI Lab"},
    {"name": "NVIDIA Blog",          "url": "https://developer.nvidia.com/blog/feed",              "category": "AI Lab"},
    {"name": "PyTorch Blog",         "url": "https://pytorch.org/blog/feed.xml",                  "category": "Community"},

    # 🇨🇳 中文 AI 源
    {"name": "雷锋网 AI",         "url": "https://www.leiphone.com/feed",                        "category": "中文媒体"},

    {"name": "TechCrunch AI",        "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Blog"},
    {"name": "VentureBeat AI",       "url": "https://feeds.feedburner.com/venturebeat/SZYF",       "category": "Blog"},
]


def fetch_feed(source):
    """
    抓取并解析单个 RSS/Atom feed。

    每条记录提取：
    - title：标题
    - link：原文链接
    - summary：清洗 HTML 标签后的摘要（截断至500字）
    - published：发布时间（fallback 到 updated 时间）
    - source / category：信源元信息

    Args:
        source: 信源定义字典，含 name, url, category。

    Returns:
        list[dict]: 文章字典列表，失败返回空列表。
    """
    try:
        # HTTP GET + feedparser 解析（支持 RSS 2.0 和 Atom）
        resp = requests.get(source["url"], timeout=15, headers={
            "User-Agent": "AI-Intel-Scanner/1.0"
        })
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        articles = []
        for entry in feed.entries[:20]:  # 每个信源取前20条
            # 解析发布时间：优先 published，其次 updated
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.updated_parsed)

            summary = entry.get("summary", "") or ""
            # 清洗 HTML 标签，保留纯文本（截断至500字）
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
    """
    扫描所有信源并返回合并结果。

    处理逻辑：
    - 逐信源抓取（带进度显示）
    - 按发布时间降序排序（Unknown 排最后）
    - 按标题前80字符去重

    Returns:
        dict: 扫描结果，含 scanned_at, total_sources, successful_sources,
              total_articles, articles。
    """
    print(f"🤖 AI Intel Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 Scanning {len(SOURCES)} sources...\n")

    all_articles = []
    success_count = 0

    # 逐信源抓取
    for i, source in enumerate(SOURCES, 1):
        print(f"  [{i}/{len(SOURCES)}] {source['name']}...", end=" ", flush=True)
        articles = fetch_feed(source)
        if articles:
            success_count += 1
            all_articles.extend(articles)
            print(f"✅ {len(articles)} articles")
        else:
            print("⚠️  skipped")

    # 按发布时间降序排序（Unknown 日期排末尾）
    def sort_key(a):
        try:
            return a["published"]
        except:
            return ""
    all_articles.sort(key=sort_key, reverse=True)

    # 按标题前80字符去重（跨信源的相同新闻只保留第一条）
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
    """
    保存扫描结果到 JSON 文件。

    输出两份：
    1. data/raw.json — 最新快照（覆盖写）
    2. data/history/YYYY-MM-DD.json — 每日存档（一份一天）

    Args:
        result: scan_all() 返回的结果字典。
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # 覆盖写入最新快照
    with open(SUMMARY_FILE, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 每日存档（按日期命名，同一天多次运行只保留最后一次）
    date_str = datetime.now().strftime("%Y-%m-%d")
    history_file = HISTORY_DIR / f"{date_str}.json"
    with open(history_file, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved: {len(result['articles'])} articles to raw.json")
    print(f"💾 History: {history_file.name}")

    return result


def print_summary(result):
    """
    打印人类可读的扫描摘要（适合 cron 输出）。

    按分类分组显示，每个分类最多展示5篇文章。

    Args:
        result: scan_all() 返回的结果字典。
    """
    articles = result["articles"]

    # 按分类分组
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

    # 按分类展示
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
    # 独立运行：扫描 → 保存 → 打印摘要
    result = scan_all()
    save_result(result)
    print_summary(result)
