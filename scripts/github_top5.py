#!/usr/bin/env python3
"""GitHub AI Top 5 — fetch top-starred AI repos + generate AI summaries via DeepSeek."""
import json, os, sys, hashlib, time
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "github_top5.json"
CACHE_FILE = DATA_DIR / ".github_top5_cache.json"

# GitHub search: top AI repos by stars (language-agnostic, filtered by AI topics)
SEARCH_URL = "https://api.github.com/search/repositories"
QUERY = "ai OR llm OR machine-learning in:name,description stars:>10000 language:python"
PARAMS = {
    "q": QUERY,
    "sort": "stars",
    "order": "desc",
    "per_page": 5,
}

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def get_github_token():
    """Try to get GitHub token from env."""
    return os.environ.get("GITHUB_TOKEN", "")


def fetch_top_repos():
    """Fetch top 5 AI repos from GitHub Search API."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(SEARCH_URL, params=PARAMS, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    repos = []
    for item in data.get("items", []):
        repos.append({
            "full_name": item["full_name"],
            "name": item["name"],
            "owner": item["owner"]["login"],
            "description": (item.get("description") or "")[:300],
            "url": item["html_url"],
            "stars": item["stargazers_count"],
            "forks": item["forks_count"],
            "language": item.get("language") or "Unknown",
            "topics": item.get("topics", []),
            "updated_at": item["updated_at"],
        })
    return repos


def load_cache():
    """Load cached results to avoid re-generating summaries."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_cache(repos, summaries):
    """Cache repo data keyed by full_name."""
    cache = {}
    for r in repos:
        name = r["full_name"]
        cache[name] = {
            "stars": r["stars"],
            "summary": summaries.get(name, ""),
            "updated_at": r["updated_at"],
        }
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def generate_summary(repo):
    """Generate a brief AI summary of a GitHub repo using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        print("  ⚠️  No DEEPSEEK_API_KEY, using description as summary", file=sys.stderr)
        return repo["description"]

    prompt = f"""You are a technical writer. Explain this open-source project in 2-3 Chinese sentences — what it does and why developers should care. Be specific, avoid buzzwords like "revolutionary" or "game-changing". No emoji.

Project: {repo['full_name']}
Description: {repo['description']}
Language: {repo['language']}
Stars: {repo['stars']:,}
Topics: {', '.join(repo.get('topics', []))}"""

    try:
        resp = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3,
            },
            timeout=20,
        )
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️  DeepSeek error for {repo['full_name']}: {e}", file=sys.stderr)
        return repo["description"]


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching GitHub AI Top 5...", file=sys.stderr)

    # Fetch repos
    repos = fetch_top_repos()
    print(f"  Found {len(repos)} repos", file=sys.stderr)

    # Load cache
    cache = load_cache()

    # Generate summaries (skip if cached and stars unchanged)
    summaries = {}
    for repo in repos:
        name = repo["full_name"]
        cached = cache.get(name, {})
        if cached and cached.get("stars") == repo["stars"] and cached.get("summary"):
            print(f"  {name} — cached (⭐ {repo['stars']:,})", file=sys.stderr)
            summaries[name] = cached["summary"]
        else:
            print(f"  {name} — generating summary (⭐ {repo['stars']:,})...", file=sys.stderr)
            summaries[name] = generate_summary(repo)
            time.sleep(0.5)  # rate limit

    # Build output
    output = {
        "generated_at": datetime.now().isoformat(),
        "repos": [
            {
                **repo,
                "summary": summaries[repo["full_name"]],
                "stars_formatted": f"{repo['stars']:,}",
            }
            for repo in repos
        ],
    }

    # Write output
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    # Update cache
    save_cache(repos, summaries)

    print(f"  ✅ Written to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
