#!/usr/bin/env python3
"""
阶段1: Scanner — RSS/API 采集器。

================================================================================
模块功能
================================================================================
Pipeline 第一阶段：从 16 个配置好的信源采集文章。
  1. 遍历 SOURCES 列表，对每个信源发起 HTTP 请求
  2. 支持两种协议：标准 RSS feed（feedparser 解析）和 WordPress REST API（JSON 解析）
  3. 使用指数退避 + 随机抖动的重试策略（最多 3 次）
  4. 对每条文章计算 SHA256 content_hash，用于后续跨源去重
  5. 通过 INSERT OR IGNORE 写入 SQLite，避免重复入库
  6. 记录每个信源的健康状态（成功/失败次数、文章数）

================================================================================
核心算法
================================================================================
- content_hash: SHA256(title.lower()|link) → 唯一标识一篇文章
  注意：使用 title+link 而非 title+content，因为 RSS 摘要可能被截断
- extract_paper_id: 从 ArXiv URL 中提取论文 ID（如 `2412.12345`）
- 指数退避重试: 第 i 次重试等待 2^i + random(0,1) 秒，避免惊群效应
- 入库去重: INSERT OR IGNORE 基于 UNIQUE(content_hash) 约束，重复文章静默跳过
"""

import hashlib
import json
import random
import re
import time
from datetime import datetime, timezone

import feedparser
import requests

from . import SOURCES, get_db

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
# 模拟浏览器 User-Agent，避免部分站点（如 TechCrunch）拒绝对爬虫返回内容
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def content_hash(title: str, link: str) -> str:
    """
    计算文章内容的 SHA256 哈希值，作为全局唯一标识。

    使用 title + link 组合（而非正文），原因：
      - RSS 摘要可能被截断，正文不可靠
      - title + link 组合在绝大多数情况下足以唯一标识一篇文章
      - 同一篇文章从不同信源采集时 title 可能略有差异，但 link 唯一

    Args:
        title: 文章标题（会做 strip + lower 标准化）
        link:  文章链接（会做 strip 标准化）

    Returns:
        64 字符的十六进制 SHA256 哈希字符串
    """
    return hashlib.sha256(f"{title.strip().lower()}|{link.strip()}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# ArXiv 论文 ID 提取
# ---------------------------------------------------------------------------
# 匹配 arxiv.org/abs/XXXX.XXXXX 或 arxiv.org/pdf/XXXX.XXXXX
_ARXIV_ID_RE = re.compile(r'arxiv\.org/(?:abs|pdf)/([\w.-]+)')

def extract_paper_id(link: str) -> str | None:
    """
    从文章链接中提取 ArXiv 论文 ID。

    支持的 URL 格式:
      - https://arxiv.org/abs/2412.12345
      - https://arxiv.org/pdf/2412.12345v1

    Args:
        link: 文章 URL

    Returns:
        论文 ID 字符串（如 "2412.12345"），非 ArXiv 链接返回 None
    """
    m = _ARXIV_ID_RE.search(link)
    return m.group(1) if m else None


def fetch_feed(source: dict, retries: int = 3) -> list[dict]:
    """
    使用 feedparser 获取标准 RSS feed 的文章列表。

    重试策略（指数退避 + 随机抖动）:
      - 第 0 次重试: 等待 ~1s  (2^0 + random)
      - 第 1 次重试: 等待 ~2s  (2^1 + random)
      - 第 2 次重试: 等待 ~4s  (2^2 + random)
      随机抖动 [0,1) 秒可避免同时重试的多个请求产生"惊群效应"

    取前 20 条文章，对每条提取:
      - 发布时间（优先 published_parsed，回退 updated_parsed）
      - 摘要（去除 HTML 标签，截断至 500 字符）

    Args:
        source:  信源配置字典（包含 name, url, category）
        retries: 最大重试次数，默认 3

    Returns:
        文章字典列表，每篇包含 title/link/summary/published/source_name/category
        如果全部重试失败，返回 None（区分于空 feed 返回的 []）
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            # 发起 HTTP GET，使用浏览器 UA 避免被拒
            resp = requests.get(source["url"], timeout=20, headers={
                "User-Agent": _BROWSER_UA
            })
            resp.raise_for_status()  # 非 2xx 状态码抛出异常
            feed = feedparser.parse(resp.content)

            articles = []
            # 只取前 20 条，兼顾时效性和处理效率
            for entry in feed.entries[:20]:
                pub_date = None
                # 优先使用 published（首次发布时间），回退 updated（最后更新时间）
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.published_parsed)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_date = time.strftime("%Y-%m-%d %H:%M:%S", entry.updated_parsed)

                # 去除 HTML 标签，截断到 500 字符，防止超长摘要撑大数据库
                summary = entry.get("summary", "") or ""
                clean_summary = re.sub(r"<[^>]+>", "", summary)[:500]

                articles.append({
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "summary": clean_summary,
                    "published": pub_date or "Unknown",
                    "source_name": source["name"],
                    "category": source["category"],
                })
            return articles
        except Exception as e:
            last_error = e
            if attempt < retries:
                # 计算指数退避等待时间: 2^attempt + 随机抖动 [0,1)
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"  🔄 {source['name']}: retry {attempt+1}/{retries} in {wait:.1f}s ({e})")
                time.sleep(wait)
            else:
                print(f"  ⚠️  {source['name']}: {last_error}")
    # 返回 None 表示真正的抓取错误（而非空 feed），调用方据此区分处理
    return None


def fetch_wp_api(source: dict, retries: int = 2) -> list[dict]:
    """
    获取 WordPress REST API 端点的文章列表。

    与标准 RSS 不同，WP API 返回 JSON 数组，每个元素是 post 对象:
      - title:       嵌套对象 { "rendered": "标题文本" }
      - excerpt:     嵌套对象 { "rendered": "摘要HTML" }
      - link:        文章 URL
      - date/date_gmt: 发布时间

    专为量子位等使用 WordPress 的中文媒体设计。

    Args:
        source:  信源配置字典（需包含 type="wp_api"）
        retries: 最大重试次数，默认 2（WP API 通常较稳定）

    Returns:
        文章字典列表，失败时返回空列表 []
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            # WP API 使用独立的 User-Agent，与 RSS feed 请求区分
            resp = requests.get(source["url"], timeout=20, headers={
                "User-Agent": "AI-Intel-Scanner/2.0"
            })
            resp.raise_for_status()
            posts = json.loads(resp.text)
            # 防御性检查：确保返回的是列表而非错误对象
            if not isinstance(posts, list):
                print(f"    ⚠️  Unexpected WP API response type: {type(posts).__name__}")
                return []

            articles = []
            for post in posts[:20]:
                # WP API 的 title 是嵌套对象 {"rendered": "标题"}，需解包
                title = post.get("title", {})
                if isinstance(title, dict):
                    title = title.get("rendered", "Untitled")

                # excerpt 同样可能是嵌套对象
                excerpt = post.get("excerpt", {})
                if isinstance(excerpt, dict):
                    excerpt_text = excerpt.get("rendered", "")
                else:
                    excerpt_text = str(excerpt)

                # 去除 HTML 标签，截断至 500 字符
                summary = re.sub(r"<[^>]+>", "", excerpt_text)[:500]

                link = post.get("link", "")
                # 优先使用本地时区的 date，回退 GMT 时间
                pub_date = post.get("date", "") or post.get("date_gmt", "")

                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": pub_date or "Unknown",
                    "source_name": source["name"],
                    "category": source["category"],
                })
            return articles
        except Exception as e:
            last_error = e
            if attempt < retries:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"  🔄 {source['name']}: retry {attempt+1}/{retries} in {wait:.1f}s ({e})")
                time.sleep(wait)
            else:
                print(f"  ⚠️  {source['name']}: {last_error}")
    # WP API 失败返回空列表（而非 None），因为非关键信源
    return []


def run(skip_stats: bool = False) -> dict:
    """
    运行 Scanner 主流程：遍历所有信源，采集文章并入库。

    完整流程:
      1. 遍历 SOURCES 中的每个信源，根据 type 选择 fetch_feed 或 fetch_wp_api
      2. 对每条文章计算 content_hash 和 paper_id
      3. 使用 INSERT OR IGNORE 去重入库（基于 content_hash UNIQUE 约束）
      4. 更新 sources 表的信源健康状态（成功/失败计数）
      5. 写入 daily_stats 表记录每日采集统计

    Args:
        skip_stats: 是否跳过 daily_stats 表的写入。
                    增量 Scanner 调用时应设为 True，避免覆盖主 Pipeline 的正确统计数据。

    Returns:
        统计字典: { scanned_at, total_sources, successful_sources, total_articles, new_articles }
    """
    print(f"📡 Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   {len(SOURCES)} sources configured\n")

    scanned_at = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    all_articles = []
    success_count = 0
    new_articles = 0

    for i, source in enumerate(SOURCES, 1):
        name = source["name"]
        # 根据信源类型选择对应的抓取函数
        source_type = source.get("type", "rss")
        print(f"  [{i}/{len(SOURCES)}] {name}...", end=" ", flush=True)
        articles = fetch_wp_api(source) if source_type == "wp_api" else fetch_feed(source)

        if articles:
            # ---- 信源采集成功 ----
            success_count += 1
            all_articles.extend(articles)
            inserted = 0
            for a in articles:
                # 计算内容哈希（用于后续跨源去重）
                h = content_hash(a["title"], a["link"])
                # 提取 ArXiv 论文 ID（非 ArXiv 文章为 None）
                paper_id = extract_paper_id(a["link"])
                is_paper = 1 if paper_id else 0
                try:
                    # INSERT OR IGNORE: 如果 content_hash 已存在则静默跳过
                    conn.execute(
                        """INSERT OR IGNORE INTO articles
                           (title, link, summary, published, source_name, category,
                            content_hash, scanned_at, is_paper, paper_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (a["title"], a["link"], a["summary"],
                         a["published"], a["source_name"], a["category"],
                         h, scanned_at, is_paper, paper_id)
                    )
                    # 检查实际插入的行数 (changes() 返回最近一条语句影响的行数)
                    if conn.execute("SELECT changes()").fetchone()[0]:
                        inserted += 1
                        new_articles += 1
                except Exception:
                    # 个别文章入库失败不影响整个信源的采集
                    pass

            # 更新信源健康状态：记录成功、重置连续失败计数
            conn.execute(
                """INSERT INTO sources (name, url, category, last_success, article_count_last)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                   last_success = excluded.last_success,
                   consecutive_failures = 0,
                   article_count_last = excluded.article_count_last""",
                (name, source["url"], source["category"],
                 scanned_at, len(articles))
            )
            print(f"✅ {len(articles)} articles ({inserted} new)")
        else:
            # ---- 信源采集失败 ----
            # 更新 consecutive_failures，用于健康监控告警
            conn.execute(
                """INSERT INTO sources (name, url, category, last_failure, consecutive_failures)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(name) DO UPDATE SET
                   last_failure = excluded.last_failure,
                   consecutive_failures = consecutive_failures + 1""",
                (name, source["url"], source["category"], scanned_at)
            )
            print("⚠️  failed")

    conn.commit()

    # 写入每日统计（增量 Scanner 可跳过此步，避免覆盖主流程数据）
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    if not skip_stats:
        date_str = datetime.now().strftime("%Y-%m-%d")
        conn.execute(
            """INSERT INTO daily_stats
               (date, total_sources, successful_sources, total_articles, new_articles)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
               total_sources = excluded.total_sources,
               successful_sources = excluded.successful_sources,
               total_articles = excluded.total_articles,
               new_articles = excluded.new_articles""",
            (date_str, len(SOURCES), success_count, total, new_articles)
        )
        conn.commit()
    conn.close()

    stats = {
        "scanned_at": scanned_at,
        "total_sources": len(SOURCES),
        "successful_sources": success_count,
        "total_articles": total,
        "new_articles": new_articles,
    }

    print(f"\n✅ Scanner done: {success_count}/{len(SOURCES)} sources, "
          f"{new_articles} new articles, {total} total in DB")
    return stats


if __name__ == "__main__":
    run()
