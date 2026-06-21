#!/usr/bin/env python3
"""GitHub Trending scraper — daily snapshot of AI/ML repositories.

Uses pure regex parsing (no BeautifulSoup dependency) to scrape
github.com/trending and extract AI/ML repos with star counts.
"""

import json
import re
import time
from datetime import datetime, timezone

import requests

from . import get_db

# AI/ML related topics and keywords to filter
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
    """Check if repo description/handle hints at AI/ML."""
    text_lower = text.lower()
    for kw in AI_KEYWORDS:
        if re.search(kw, text_lower):
            return True
    return False


def fetch_trending() -> list[dict]:
    """Scrape GitHub Trending page for AI/ML repos.

    Returns list of repo dicts sorted by stars_today descending.
    """
    html = None
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
    seen = set()

    # Find all article blocks — each is a repo card
    # Pattern: <article class="Box-row"> ... </article>
    articles = re.findall(
        r'<article\s+class="Box-row"[^>]*>(.*?)</article>\s*(?=<article|$|</div>\s*</div>\s*$)',
        html, re.DOTALL
    )

    for block in articles:
        # Extract repo_full: /owner/repo
        repo_match = re.search(r'href="(/([^/"]+)/([^/"]+))"', block)
        if not repo_match:
            continue
        repo_full = repo_match.group(1).strip("/")
        if repo_full in seen:
            continue

        # Skip if not AI-related (check description + repo name)
        desc_match = re.search(
            r'<p\s+class="(?:col-9\s+)?(?:color-fg-muted\s+)?(?:my-1\s+)?pr-4"[^>]*>\s*(.*?)\s*</p>',
            block, re.DOTALL
        )
        description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else ""

        if not _is_ai_repo(f"{repo_full} {description}"):
            continue
        seen.add(repo_full)

        # Language
        lang_match = re.search(
            r'itemprop="programmingLanguage"[^>]*>\s*([^<]+)\s*<',
            block
        )
        language = lang_match.group(1).strip() if lang_match else ""

        # Stars today
        stars_today = 0
        star_texts = re.findall(
            r'<span[^>]*float-sm-right[^>]*>\s*([\d,]+)\s+stars?\s+today\s*</span>',
            block, re.IGNORECASE
        )
        if star_texts:
            stars_today = int(star_texts[0].replace(",", ""))
        else:
            # Fallback: any span with "stars today"
            alt = re.findall(
                r'([\d,]+)\s+stars?\s+today',
                block, re.IGNORECASE
            )
            if alt:
                stars_today = int(alt[0].replace(",", ""))

        # Total stars
        total_stars = 0
        ts_match = re.findall(
            r'([\d,]+)\s*</a>\s*$',
            block, re.MULTILINE
        )
        for m in ts_match:
            val = m.replace(",", "").strip()
            if val.isdigit():
                total_stars = max(total_stars, int(val))

        # Fallback: find any number preceding </a> that could be total stars
        if total_stars == 0:
            all_nums = re.findall(r'>\s*([\d,]+)\s*<', block)
            # The largest number is likely total stars
            for n in sorted([int(x.replace(",", "")) for x in all_nums], reverse=True):
                if n > stars_today and n > 10:
                    total_stars = n
                    break

        repos.append({
            "repo_full": repo_full,
            "description": description[:500],
            "language": language,
            "stars_today": stars_today,
            "total_stars": total_stars,
            "url": f"https://github.com/{repo_full}",
        })

    repos.sort(key=lambda r: r["stars_today"], reverse=True)
    return repos[:30]


def ensure_table(conn):
    """Create github_trending table if not exists."""
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
    """Link trending repos to ArXiv papers in our DB. Returns count linked."""
    rows = conn.execute("""
        SELECT id, repo_full FROM github_trending
        WHERE paper_linked = 0 AND snapshot_at = (
            SELECT MAX(snapshot_at) FROM github_trending
        )
    """).fetchall()

    linked = 0
    for row in rows:
        repo_name = row["repo_full"].split("/")[-1].lower()

        # Strategy 1: exact github_repo match
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

        # Strategy 2: fuzzy — check if any paper title contains repo name words
        words = repo_name.replace("-", " ").replace("_", " ").split()
        if len(words) >= 2:
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
    """Run GitHub Trending scraper. Returns stats dict."""
    print(f"\n🔥 GitHub Trending — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    repos = fetch_trending()
    if not repos:
        print("   No AI/ML repos found on trending today")
        return {"repos_found": 0, "new_repos": 0, "paper_linked": 0}

    conn = get_db()
    ensure_table(conn)
    snapshot_at = datetime.now(timezone.utc).isoformat()
    inserted = 0

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
            pass

    conn.commit()

    linked = cross_link_papers(conn)
    conn.commit()

    top3 = ", ".join(r["repo_full"].split("/")[-1] for r in repos[:3])
    print(f"   ✅ {len(repos)} AI/ML repos ({inserted} new, {linked} paper-linked)")
    print(f"   🔝 {top3}")
    conn.close()

    return {"repos_found": len(repos), "new_repos": inserted, "paper_linked": linked}


def export_trending_json() -> dict:
    """Export latest trending data for frontend display."""
    conn = get_db()
    ensure_table(conn)

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
