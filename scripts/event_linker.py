#!/usr/bin/env python3
"""
Multi-Source Event Linker — 多源事件聚合。
从最近 7 天文章中提取标题关键词 → 计算 Jaccard 相似度 → 聚类 → DeepSeek 事件摘要。
输出: data/events.json
"""
import json, os, re, sqlite3, sys, time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ── Paths ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "ai_intel.db"
OUTPUT_FILE = DATA_DIR / "events.json"
CACHE_FILE = DATA_DIR / ".events_cache.json"

# ── Config ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SIMILARITY_THRESHOLD = 0.25
MIN_CLUSTER_SIZE = 3
MAX_CLUSTERS = 12
LOOKBACK_DAYS = 7


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def fetch_recent_articles(db_path: str = str(DB_PATH), days: int = LOOKBACK_DAYS) -> list[dict]:
    """Fetch articles from the past N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, title, title_cn, published, source_name, category, link, summary
           FROM articles
           WHERE published >= ?
           ORDER BY published DESC""",
        (cutoff,),
    ).fetchall()
    conn.close()
    articles = []
    for r in rows:
        t = r["title_cn"] if r["title_cn"] else r["title"]
        articles.append(
            {
                "id": r["id"],
                "title": r["title"],
                "title_cn": r["title_cn"],
                "display_title": t,
                "published": r["published"],
                "source_name": r["source_name"],
                "category": r["category"] or "Other",
                "link": r["link"],
                "summary": r["summary"],
            }
        )
    return articles


def tokenize_title(title: str) -> set[str]:
    """Break title into meaningful tokens (Chinese 2-char slices + English words)."""
    tokens = set()
    # Lowercase
    title = title.lower()
    # English word tokens (3+ chars)
    for w in re.findall(r"[a-z]{3,}", title):
        tokens.add(w)
    # Chinese char bigrams
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", title)
    for i in range(len(chinese_chars) - 1):
        tokens.add(chinese_chars[i] + chinese_chars[i + 1])
    return tokens


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compute_similarity_matrix(articles: list[dict]) -> list[tuple[int, int, float]]:
    """Compute pairwise Jaccard similarity on display_title."""
    titles = [(i, tokenize_title(a["display_title"])) for i, a in enumerate(articles)]
    pairs = []
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            sim = jaccard_similarity(titles[i][1], titles[j][1])
            if sim >= SIMILARITY_THRESHOLD:
                pairs.append((titles[i][0], titles[j][0], round(sim, 3)))
    return sorted(pairs, key=lambda x: -x[2])


def union_find(n: int):
    parent = list(range(n))
    size = [1] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if size[rx] < size[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        size[rx] += size[ry]

    return find, union


def cluster_articles(articles: list[dict], sim_pairs: list[tuple[int, int, float]]) -> list[list[dict]]:
    """Union-Find clustering based on similarity pairs."""
    n = len(articles)
    find, union = union_find(n)

    for i, j, _ in sim_pairs:
        union(i, j)

    groups = defaultdict(list)
    for idx, a in enumerate(articles):
        root = find(idx)
        groups[root].append(a)

    # Sort by recency and filter by min size
    clusters = []
    for cluster_articles in groups.values():
        if len(cluster_articles) >= MIN_CLUSTER_SIZE:
            cluster_articles.sort(key=lambda a: a["published"] or "", reverse=True)
            clusters.append(cluster_articles)

    clusters.sort(key=lambda c: c[0]["published"] or "", reverse=True)
    return clusters[:MAX_CLUSTERS]


def generate_event_summary(cluster: list[dict]) -> str:
    """Generate a concise Chinese event summary using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        return ""

    title_list = "\n".join(
        f"- [{a['source_name']}] {a['display_title']}" for a in cluster[:8]
    )
    prompt = (
        "以下是同一AI事件的多个信源报道标题列表。请用一句中文（不超过100字）总结这个事件的核心内容，"
        "提取事件关键词、涉及的组织/模型/技术、以及为什么重要。"
        "只输出一句话，不要列表、不要前缀、不要换行：\n\n"
        f"{title_list}"
    )

    try:
        resp = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个AI行业分析助手，擅长用一句话概括技术事件。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            },
            timeout=30,
        )
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text if text else ""
    except Exception:
        return ""


def export_events_json() -> dict:
    """Main entry: fetch articles → cluster → summarize → export."""
    articles = fetch_recent_articles()

    if not articles:
        return _empty_result("No recent articles available")

    sim_pairs = compute_similarity_matrix(articles)
    clusters = cluster_articles(articles, sim_pairs)

    if not clusters:
        return _empty_result("No event clusters detected")

    # Load cache for summary reuse
    cache = load_cache()
    cache_key_base = str(DB_PATH)

    events = []
    for ci, cluster in enumerate(clusters):
        sources = sorted(set(a["source_name"] for a in cluster))
        categories = sorted(set(a["category"] for a in cluster))
        time_range = {
            "start": cluster[-1]["published"],
            "end": cluster[0]["published"],
        }
        article_ids = [a["id"] for a in cluster]
        cache_key = f"{cache_key_base}_{sorted(article_ids)}"

        # Try cache
        summary = cache.get(cache_key, "")
        if not summary:
            summary = generate_event_summary(cluster)
            if summary:
                cache[cache_key] = summary

        events.append(
            {
                "id": f"evt_{ci+1}",
                "title": summary or cluster[0]["display_title"][:60],
                "sources": sources,
                "categories": categories,
                "time_range": time_range,
                "article_count": len(cluster),
                "articles": [
                    {
                        "id": a["id"],
                        "title": a["display_title"],
                        "source": a["source_name"],
                        "category": a["category"],
                        "link": a["link"],
                        "published": a["published"],
                    }
                    for a in cluster[:6]
                ],
            }
        )

    save_cache(cache)

    result = {
        "generated_at": now_utc(),
        "source_articles": len(articles),
        "events": events,
    }
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"💾 events.json: {len(events)} event clusters from {len(articles)} articles")
    return result


def _empty_result(reason: str) -> dict:
    result = {
        "generated_at": now_utc(),
        "source_articles": 0,
        "events": [],
        "_reason": reason,
    }
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def run():
    return export_events_json()


if __name__ == "__main__":
    result = export_events_json()
    print(f"✅ event_linker: {len(result.get('events', []))} events")
