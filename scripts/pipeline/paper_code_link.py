#!/usr/bin/env python3
"""Paper-Code Linker — find GitHub repos associated with ArXiv papers."""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

from . import get_db


def _gh_search(query: str, token: str | None = None) -> dict | None:
    """Search GitHub repositories API. Returns parsed JSON or None."""
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page=3"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Intel-Scanner/2.0",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ⚠️  GitHub API: {e}")
        return None


def find_repo_for_paper(paper_id: str, title: str, token: str | None = None) -> str | None:
    """Search GitHub for a repo matching an ArXiv paper. Returns repo URL or None."""
    # Strategy 1: search by ArXiv ID
    result = _gh_search(f'"{paper_id}"', token)
    if result and result.get("items"):
        best = result["items"][0]
        if best.get("stargazers_count", 0) >= 2:
            return best["html_url"]

    # Strategy 2: search by paper title keywords (first 5 words)
    keywords = " ".join(title.split()[:5])
    result = _gh_search(f'"{keywords}"', token)
    if result and result.get("items"):
        best = result["items"][0]
        if best.get("stargazers_count", 0) >= 5:
            return best["html_url"]

    return None


def run(limit: int = 5, token: str = None) -> dict:
    """Find GitHub repos for unlinked ArXiv papers."""
    conn = get_db()

    # Get papers that need linking (is_paper but no github_repo)
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
            conn.execute(
                "UPDATE articles SET github_repo = ? WHERE id = ?",
                (repo, p["id"])
            )
            conn.commit()
            linked += 1
            print(f"✅ {repo}")
        else:
            print("❌ not found")

        if i < len(papers) - 1:
            time.sleep(2)  # Rate limit: 30 req/min for unauthenticated

    conn.close()
    print(f"\n📎 Paper-Code: {linked}/{len(papers)} repos linked")
    return {"linked": linked, "total": len(papers)}


if __name__ == "__main__":
    # Read token from .git_token if available
    token_file = Path(__file__).parent.parent.parent / ".git_token"
    token = token_file.read_text().strip() if token_file.exists() else None
    run(limit=3, token=token)
