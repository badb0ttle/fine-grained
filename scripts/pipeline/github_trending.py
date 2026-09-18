#!/usr/bin/env python3
"""
GitHub Trending 追踪模块 (GitHub Trending Scraper)
==================================================
每日抓取 github.com/trending 页面，筛选 AI/ML 相关仓库，记录 star 增量数据，
并尝试与数据库中已有的 ArXiv 论文进行关联。

技术选型：复用项目已有的 BeautifulSoup，按 HTML 结构解析仓库卡片。
数据存储：github_trending 表（自建表，不在 db_init 中统一管理）。
"""

import json
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from . import get_db

# AI/ML 相关关键词列表，用于判断仓库是否与AI相关
# 使用正则 pattern 格式（. 匹配任意字符），覆盖算法、框架、模型、Agent等维度
AI_KEYWORDS = [
    "machine.learning", "deep.learning", "large.language.model",
    "natural.language", "computer.vision", "reinforcement.learning",
    "generative.ai", "diffusion.model", "neural.network",
    "transformer", "llm", "rag", "fine.tuning",
    "pytorch", "tensorflow", "jax", "langchain",
    "openai", "llama", "mistral", "gemma", "qwen",
    "embedding", "tokenizer", "inference.engine",
    "multi.modal", "vision.model", "speech.model",
    "agent", "mcp", "ai.agent", "coding.agent",
]


def _is_ai_repo(text: str) -> bool:
    """
    判断仓库描述/名称是否与 AI/ML 相关。

    对输入的文本（仓库全名 + 描述）进行小写转换后，
    逐一匹配 AI_KEYWORDS 中的正则模式。

    Args:
        text: 仓库 full_name + description 拼接字符串。

    Returns:
        bool: True 表示为 AI/ML 相关仓库。
    """
    text_lower = text.lower()
    for kw in AI_KEYWORDS:
        if re.search(kw, text_lower):
            return True
    return False


def fetch_trending() -> list[dict]:
    """
    抓取 GitHub Trending 页面并提取 AI/ML 仓库信息。

    解析策略：
    1. HTTP GET 请求 github.com/trending?since=daily（最多重试2次）
    2. 用 HTML 解析器提取 article.Box-row 仓库卡片
    3. 从每个卡片中提取：repo_full, description, language, stars_today, total_stars
    4. 过滤非 AI/ML 仓库
    5. 按 stars_today 降序排列，返回前30个

    Returns:
        list[dict]: 仓库字典列表，每项含 repo_full, description, language,
                    stars_today, total_stars, url。
    """
    html = None
    # 最多 2 次请求尝试，间隔 3 秒
    for attempt in range(2):
        try:
            resp = requests.get(
                "https://github.com/trending?since=daily",
                timeout=15,
                headers={"User-Agent": "AI-Intel-Scanner/2.0"}
            )
            resp.raise_for_status()
            html = resp.text
            break
        except Exception as e:
            if attempt == 1:
                print(f"  ⚠️ GitHub Trending fetch failed: {e}")
                return []
            time.sleep(3)

    if not html:
        return []

    repos = []
    seen = set()  # 去重集合

    # 按 HTML 结构定位，不依赖样式类顺序或最后一张卡片之后的内容。
    soup = BeautifulSoup(html, "html.parser")
    for block in soup.select("article.Box-row"):
        repo_link = block.select_one("h2 a[href]")
        if repo_link is None:
            continue
        repo_path = str(repo_link.get("href", ""))
        if not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?", repo_path):
            continue
        repo_full = repo_path.strip("/")
        if repo_full in seen:
            continue

        # 描述不依赖 pr-4/tmp-pr-4 等展示类，同时解码实体并折叠空白。
        desc = block.find("p")
        description = " ".join(desc.get_text(" ", strip=True).split()) if desc else ""
        if not _is_ai_repo(f"{repo_full} {description}"):
            continue
        seen.add(repo_full)

        lang = block.select_one('[itemprop="programmingLanguage"]')
        language = lang.get_text(strip=True) if lang else ""

        stars_today = 0
        for span in block.select("span.float-sm-right"):
            match = re.search(r"([\d,]+)\s+stars?\s+today", span.get_text(" ", strip=True), re.IGNORECASE)
            if match:
                stars_today = int(match.group(1).replace(",", ""))
                break

        # 仅使用该仓库的 stargazers 链接，不能把 forks 或其他数字当作 stars。
        star_link = block.find("a", href=f"/{repo_full}/stargazers")
        star_text = star_link.get_text(strip=True).replace(",", "") if star_link else ""
        total_stars = int(star_text) if star_text.isdigit() else 0

        repos.append({
            "repo_full": repo_full,
            "description": description[:500],  # 截断过长描述
            "language": language,
            "stars_today": stars_today,
            "total_stars": total_stars,
            "url": f"https://github.com/{repo_full}",
        })

    # 按今日 Star 数降序排列，返回 Top 30
    repos.sort(key=lambda r: r["stars_today"], reverse=True)
    return repos[:30]


def ensure_table(conn):
    """
    确保 github_trending 表及其索引存在（幂等操作）。

    表结构：
    - repo_full + snapshot_at 联合唯一约束（同一天不重复记录同一仓库）
    - 索引覆盖 snapshot_at（按时间查询）和 repo_full（按仓库查询）

    Args:
        conn: SQLite 数据库连接对象。
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS github_trending (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_full   TEXT NOT NULL,
            description TEXT,
            language    TEXT,
            stars_today INTEGER DEFAULT 0,
            total_stars INTEGER DEFAULT 0,
            url         TEXT,
            snapshot_at TEXT NOT NULL,
            paper_linked INTEGER DEFAULT 0,
            paper_id    TEXT,
            UNIQUE(repo_full, snapshot_at)
        );

        CREATE INDEX IF NOT EXISTS idx_trending_snapshot
        ON github_trending(snapshot_at DESC);

        CREATE INDEX IF NOT EXISTS idx_trending_repo
        ON github_trending(repo_full);
    """)


def cross_link_papers(conn) -> int:
    """
    将 Trending 仓库与数据库中的 ArXiv 论文进行关联。

    关联策略（两阶段）：
    1. 精确匹配：articles.github_repo 字段是否包含仓库名
    2. 模糊匹配：仓库名分词后，匹配论文标题中的关键词组合

    Args:
        conn: SQLite 数据库连接对象。

    Returns:
        int: 成功关联的仓库数量。
    """
    # 仅处理当次快照中尚未关联的仓库
    rows = conn.execute("""
        SELECT id, repo_full FROM github_trending
        WHERE paper_linked = 0 AND snapshot_at = (
            SELECT MAX(snapshot_at) FROM github_trending
        )
    """).fetchall()

    linked = 0
    for row in rows:
        # 提取仓库名（owner/repo → repo）
        repo_name = row["repo_full"].split("/")[-1].lower()

        # ---- 策略1：精确 github_repo 字段匹配 ----
        papers = conn.execute("""
            SELECT paper_id, github_repo FROM articles
            WHERE github_repo IS NOT NULL AND LOWER(github_repo) LIKE ?
            LIMIT 3
        """, (f"%{repo_name}%",)).fetchall()

        if papers:
            conn.execute(
                "UPDATE github_trending SET paper_linked=1, paper_id=? WHERE id=?",
                (papers[0]["paper_id"], row["id"])
            )
            linked += 1
            continue

        # ---- 策略2：模糊标题关键词匹配 ----
        # 将仓库名的连字符/下划线替换为空格后分词
        words = repo_name.replace("-", " ").replace("_", " ").split()
        if len(words) >= 2:
            # 构造 LIKE 模式：%word1%word2%word3%
            pattern = "%" + "%".join(words[:3]) + "%"
            paper_matches = conn.execute("""
                SELECT paper_id FROM articles
                WHERE is_paper=1 AND paper_id IS NOT NULL
                AND (LOWER(title) LIKE ? OR LOWER(title) LIKE ?)
                LIMIT 1
            """, (pattern, f"%{words[0]}%{words[-1]}%")).fetchall()
            if paper_matches:
                conn.execute(
                    "UPDATE github_trending SET paper_linked=1, paper_id=? WHERE id=?",
                    (paper_matches[0]["paper_id"], row["id"])
                )
                linked += 1

    return linked


def run() -> dict:
    """
    执行完整的 GitHub Trending 抓取流程。

    流程：抓取 → 建表 → 入库存 → 论文关联 → 统计输出

    Returns:
        dict: {"repos_found": int, "new_repos": int, "paper_linked": int}
    """
    print(f"\n🔥 GitHub Trending — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    repos = fetch_trending()
    if not repos:
        print("   No AI/ML repos found on trending today")
        return {"repos_found": 0, "new_repos": 0, "paper_linked": 0}

    conn = get_db()
    ensure_table(conn)
    snapshot_at = datetime.now(timezone.utc).isoformat()  # 当前快照时间戳
    inserted = 0

    # 逐条 INSERT OR IGNORE（联合唯一约束自动跳过当天重复记录）
    for repo in repos:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO github_trending
                   (repo_full, description, language, stars_today, total_stars,
                    url, snapshot_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (repo["repo_full"], repo["description"], repo["language"],
                 repo["stars_today"], repo["total_stars"], repo["url"], snapshot_at)
            )
            if conn.execute("SELECT changes()").fetchone()[0]:
                inserted += 1
        except Exception:
            pass  # 静默跳过写入失败的单条记录

    conn.commit()

    # 尝试与论文关联
    linked = cross_link_papers(conn)
    conn.commit()

    # 输出 Top 3 仓库名
    top3 = ", ".join(r["repo_full"].split("/")[-1] for r in repos[:3])
    print(f"   ✅ {len(repos)} AI/ML repos ({inserted} new, {linked} paper-linked)")
    print(f"   🔝 {top3}")
    conn.close()

    return {"repos_found": len(repos), "new_repos": inserted, "paper_linked": linked}


def export_trending_json() -> dict:
    """
    导出最新一期 Trending 数据为前端可用的 JSON 格式。

    Returns:
        dict: 包含 snapshot_at, count, repos 列表, history_dates（最近7天快照日期）。
    """
    conn = get_db()
    ensure_table(conn)

    # 查询最新快照的 Top 30 仓库
    rows = conn.execute("""
        SELECT repo_full, description, language, stars_today, total_stars,
               url, snapshot_at, paper_linked, paper_id
        FROM github_trending
        WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM github_trending)
        ORDER BY stars_today DESC
        LIMIT 30
    """).fetchall()

    repos = []
    for r in rows:
        repos.append({
            "repo_full": r["repo_full"],
            "description": r["description"],
            "language": r["language"],
            "stars_today": r["stars_today"],
            "total_stars": r["total_stars"],
            "url": r["url"],
            "paper_linked": bool(r["paper_linked"]),
            "paper_id": r["paper_id"],
        })

    # 获取最近 7 天的快照日期（用于前端历史选择器）
    history = conn.execute("""
        SELECT DISTINCT snapshot_at
        FROM github_trending
        ORDER BY snapshot_at DESC
        LIMIT 7
    """).fetchall()

    conn.close()

    return {
        "snapshot_at": rows[0]["snapshot_at"] if rows else None,
        "count": len(repos),
        "repos": repos,
        "history_dates": [h["snapshot_at"][:10] for h in reversed(history)],
    }


if __name__ == "__main__":
    run()
