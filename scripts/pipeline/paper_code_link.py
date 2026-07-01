#!/usr/bin/env python3
"""
论文-代码关联模块 (Paper-Code Linker)
=====================================
为 ArXiv 论文自动查找关联的 GitHub 开源仓库。

检索策略（两阶段）：
1. 用论文 ArXiv ID 精确搜索 GitHub
2. 用论文标题关键词（前5个单词）搜索 GitHub

使用 GitHub Search API（无需认证也可使用，但有频率限制）。
通过 .git_token 文件可提供 Personal Access Token 提高限额。
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

from . import get_db


def _gh_search(query: str, token: str | None = None) -> dict | None:
    """
    调用 GitHub Search API 搜索仓库。

    使用 urllib（标准库，零依赖），按 Star 数降序，每页最多 3 条结果。

    Args:
        query: GitHub 搜索查询字符串（会被 URL 编码）。
        token: GitHub Personal Access Token（可选，提高 API 限额）。

    Returns:
        dict | None: API 返回的 JSON 解析结果，失败返回 None。
    """
    # 构建搜索 URL：按 stargazers 降序，每次取 3 条
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page=3"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Intel-Scanner/2.0",
    })
    # 如有 Token 则附加 Authorization Header
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ⚠️  GitHub API: {e}")
        return None


def find_repo_for_paper(paper_id: str, title: str, token: str | None = None) -> str | None:
    """
    为单篇论文查找匹配的 GitHub 仓库。

    检索策略：
    1. 精确搜索 ArXiv ID（需 Star ≥ 2）
    2. 关键词搜索论文标题前5个单词（需 Star ≥ 5）

    Args:
        paper_id: ArXiv 论文编号（如 "2401.12345"）。
        title: 论文标题。
        token: GitHub API Token（可选）。

    Returns:
        str | None: 匹配到的 GitHub 仓库 URL，未找到返回 None。
    """
    # ---- 策略1：按 ArXiv ID 精确搜索 ----
    result = _gh_search(f'"{paper_id}"', token)
    if result and result.get("items"):
        best = result["items"][0]  # 取 Star 数最高的结果
        if best.get("stargazers_count", 0) >= 2:
            return best["html_url"]

    # ---- 策略2：按标题关键词搜索（前5个单词） ----
    keywords = " ".join(title.split()[:5])
    result = _gh_search(f'"{keywords}"', token)
    if result and result.get("items"):
        best = result["items"][0]
        if best.get("stargazers_count", 0) >= 5:
            return best["html_url"]

    return None


def run(limit: int = 5, token: str = None) -> dict:
    """
    执行论文-代码关联流程。

    查询 is_paper=1 但 github_repo 为空的文章，
    逐篇调用 find_repo_for_paper，找到后更新 articles 表。

    Args:
        limit: 单次最多处理的论文数量，默认 5 篇。
        token: GitHub API Token。

    Returns:
        dict: {"linked": int, "total": int} 关联统计。
    """
    conn = get_db()

    # 查询需要关联代码的论文（已标记为论文但尚无 GitHub 链接）
    papers = conn.execute("""
        SELECT id, title, paper_id
        FROM articles
        WHERE is_paper = 1 AND (github_repo IS NULL OR github_repo = '')
        AND paper_id IS NOT NULL
        ORDER BY score_total DESC
        LIMIT ?
    """, (limit,)).fetchall()

    if not papers:
        print("📎 Paper-Code: all papers already linked")
        conn.close()
        return {"linked": 0}

    linked = 0
    for i, p in enumerate(papers):
        print(f"  [{i+1}/{len(papers)}] {p['paper_id']}...", end=" ", flush=True)
        repo = find_repo_for_paper(p["paper_id"], p["title"], token)
        if repo:
            # 找到匹配仓库，更新 articles 表
            conn.execute(
                "UPDATE articles SET github_repo = ? WHERE id = ?",
                (repo, p["id"])
            )
            conn.commit()
            linked += 1
            print(f"✅ {repo}")
        else:
            print("❌ not found")

        # 遵守 API 频率限制：未认证 30 次/分钟，间隔 2 秒
        if i < len(papers) - 1:
            time.sleep(2)

    conn.close()
    print(f"\n📎 Paper-Code: {linked}/{len(papers)} repos linked")
    return {"linked": linked, "total": len(papers)}


if __name__ == "__main__":
    # 独立运行：尝试从 .git_token 文件读取 Token
    token_file = Path(__file__).parent.parent.parent / ".git_token"
    token = token_file.read_text().strip() if token_file.exists() else None
    run(limit=3, token=token)
