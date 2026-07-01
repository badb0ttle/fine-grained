#!/usr/bin/env python3
"""
数据迁移模块 (DB Migrate)
=========================
将旧的 JSON 格式数据（raw.json / latest.json / history/*.json）迁移到 SQLite 数据库。

迁移内容：
1. sources 表：从 SOURCES 定义注册所有信源
2. articles 表：从 raw.json 导入原始扫描文章
3. curated 数据：从 latest.json 应用精选标记 + 中文翻译
4. daily_stats 表：从 history/ 目录的 JSON 文件导入每日统计

迁移策略：所有写入使用 INSERT OR IGNORE，幂等可重复执行。
"""

import hashlib
import json
import sqlite3
from pathlib import Path

# ── 路径常量 ──
REPO_DIR = Path(__file__).parent.parent
DB_PATH = REPO_DIR / "data" / "ai_intel.db"
RAW_JSON = REPO_DIR / "data" / "raw.json"
LATEST_JSON = REPO_DIR / "data" / "latest.json"
HISTORY_DIR = REPO_DIR / "data" / "history"

# ── 信源定义（与 rss_scanner.py 的 SOURCES 保持一致） ──
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
    {"name": "TechCrunch AI",        "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Blog"},
    {"name": "VentureBeat AI",       "url": "https://feeds.feedburner.com/venturebeat/SZYF",       "category": "Blog"},
]


def content_hash(title: str, link: str) -> str:
    """
    计算文章内容的去重哈希值。

    使用 SHA256 对 "title|link"（小写+去空白）生成64位十六进制摘要。
    与 db_init.py 中 content_hash 字段的 UNIQUE 约束配合使用。

    Args:
        title: 文章标题。
        link: 文章链接。

    Returns:
        str: SHA256 哈希十六进制字符串。
    """
    return hashlib.sha256(f"{title.strip().lower()}|{link.strip()}".encode()).hexdigest()


def migrate_sources(conn: sqlite3.Connection):
    """
    将 SOURCES 定义注册到 sources 表。

    使用 INSERT OR IGNORE，重复执行不会产生重复记录。

    Args:
        conn: SQLite 数据库连接。
    """
    for s in SOURCES:
        conn.execute(
            """INSERT OR IGNORE INTO sources (name, url, category)
               VALUES (?, ?, ?)""",
            (s["name"], s["url"], s["category"])
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    print(f"  📡 Sources: {count} registered")


def migrate_raw(conn: sqlite3.Connection):
    """
    从 raw.json 导入原始扫描文章到 articles 表。

    每条记录计算 content_hash 用于去重，使用 INSERT OR IGNORE 跳过重复。

    Args:
        conn: SQLite 数据库连接。
    """
    if not RAW_JSON.exists():
        print("  ⚠️  raw.json not found, skipping")
        return

    data = json.loads(RAW_JSON.read_text())
    scanned_at = data.get("scanned_at", "")  # 批次时间戳
    articles = data.get("articles", [])
    inserted = 0

    for a in articles:
        h = content_hash(a["title"], a["link"])  # 计算去重哈希
        try:
            conn.execute(
                """INSERT OR IGNORE INTO articles
                   (title, link, summary, published, source_name, category,
                    content_hash, scanned_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (a["title"], a["link"], a.get("summary", ""),
                 a.get("published", ""), a.get("source", ""),
                 a.get("category", ""), h, scanned_at)
            )
            # 注意：INSERT OR IGNORE 跳过的行不会触发 total_changes 递增
            if conn.total_changes > 0:
                inserted += 1
        except sqlite3.IntegrityError:
            pass  # 唯一约束冲突，静默跳过

    conn.commit()
    print(f"  📄 raw.json: {inserted} articles imported (total {len(articles)} in file)")


def migrate_curated(conn: sqlite3.Connection):
    """
    从 latest.json 应用精选数据到 articles 表。

    更新字段：title_cn（中文标题）、summary_cn（中文摘要）、
    curated=1（精选标记）、curated_at（精选时间）。
    通过 link 字段匹配文章。

    Args:
        conn: SQLite 数据库连接。
    """
    if not LATEST_JSON.exists():
        print("  ⚠️  latest.json not found, skipping")
        return

    data = json.loads(LATEST_JSON.read_text())
    curated_at = data.get("curated_at", "")  # 精选时间
    articles = data.get("articles", [])
    updated = 0

    for a in articles:
        try:
            conn.execute(
                """UPDATE articles SET
                   title_cn = ?,
                   summary_cn = ?,
                   curated = 1,
                   curated_at = ?
                   WHERE link = ?""",
                (a.get("title_cn", ""), a.get("summary_cn", ""),
                 curated_at, a["link"])
            )
            updated += conn.total_changes
        except Exception as e:
            print(f"  ⚠️  Failed to update {a.get('title', '?')}: {e}")

    conn.commit()
    print(f"  ⭐ latest.json: {updated} articles marked curated + translated")


def migrate_history(conn: sqlite3.Connection):
    """
    从 history/ 目录的 JSON 文件导入每日统计到 daily_stats 表。

    文件名格式："YYYY‑MM‑DD.json"，作为 daily_stats 的 date 主键。
    使用 INSERT OR IGNORE 确保幂等性。

    Args:
        conn: SQLite 数据库连接。
    """
    if not HISTORY_DIR.exists():
        print("  ⚠️  history dir not found, skipping")
        return

    count = 0
    for f in sorted(HISTORY_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        date_str = f.stem  # 文件名（不含扩展名）如 "2026-06-02"
        scanned_at = data.get("scanned_at", "")

        try:
            conn.execute(
                """INSERT OR IGNORE INTO daily_stats
                   (date, total_sources, successful_sources, total_articles)
                   VALUES (?, ?, ?, ?)""",
                (date_str, data.get("total_sources", 0),
                 data.get("successful_sources", 0),
                 data.get("total_articles", 0))
            )
            count += 1
        except sqlite3.IntegrityError:
            pass  # 主键冲突，跳过

    conn.commit()
    print(f"  📅 History: {count} daily stats imported")


def main():
    """
    主迁移流程：依次执行 sources → raw → curated → history 迁移。
    """
    conn = sqlite3.connect(str(DB_PATH))
    # 启用 WAL 模式提升并发写入性能
    conn.execute("PRAGMA journal_mode=WAL")

    print("🔄 Migrating data to SQLite...\n")
    migrate_sources(conn)
    migrate_raw(conn)
    migrate_curated(conn)
    migrate_history(conn)

    # 输出迁移后汇总统计
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    curated = conn.execute("SELECT COUNT(*) FROM articles WHERE curated=1").fetchone()[0]
    conn.close()

    print(f"\n✅ Migration complete!")
    print(f"   📰 Total articles: {total}")
    print(f"   ⭐ Curated: {curated}")


if __name__ == "__main__":
    main()
