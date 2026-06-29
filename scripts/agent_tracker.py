#!/usr/bin/env python3
"""
Agent & MCP 工具周榜 — 三路 GitHub Search → DeepSeek 中文摘要 → JSON。
每周追踪 MCP 服务器、AI Agent 工具、Agent Skill 三个维度的 GitHub 新星项目。
输出: data/agent_tools.json
"""
import json, os, sys, time
from datetime import datetime
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "agent_tools.json"
CACHE_FILE = DATA_DIR / ".agent_tools_cache.json"

# Three search dimensions: MCP servers, Agent tools, Agent skills
SEARCH_URL = "https://api.github.com/search/repositories"

SEARCHES = [
    {
        "id": "mcp-server",
        "label": "MCP 服务器",
        "query": "mcp-server in:name,description stars:>50",
        "sort": "stars",
        "per_page": 8,
    },
    {
        "id": "agent-tool",
        "label": "Agent 工具",
        "query": "ai-agent OR agent-framework in:name,description stars:>500",
        "sort": "stars",
        "per_page": 8,
    },
    {
        "id": "agent-skill",
        "label": "Agent 技能",
        "query": "agent-skill OR mcp-tool in:name,description stars:>30",
        "sort": "stars",
        "per_page": 5,
    },
]

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def get_github_token():
    """Try to get GitHub token from env."""
    return os.environ.get("GITHUB_TOKEN", "")


def fetch_search(searcher):
    """Fetch repos from a single GitHub search query."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": searcher["query"],
        "sort": searcher["sort"],
        "order": "desc",
        "per_page": searcher["per_page"],
    }

    try:
        resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️  Search failed for {searcher['id']}: {e}", file=sys.stderr)
        return []

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
            "type": searcher["id"],
            "type_label": searcher["label"],
        })
    return repos


def merge_deduplicate(all_repos, top_n=10):
    """Merge results from multiple searches, deduplicate by full_name, pick top N by stars."""
    seen = set()
    unique = []
    for repo in all_repos:
        if repo["full_name"] in seen:
            continue
        seen.add(repo["full_name"])
        unique.append(repo)

    unique.sort(key=lambda r: r["stars"], reverse=True)
    return unique[:top_n]


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
            "type": r["type"],
        }
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def generate_summary(repo):
    """Generate a brief AI summary of an agent/MCP tool using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        print("  ⚠️  No DEEPSEEK_API_KEY, using description as summary", file=sys.stderr)
        return repo["description"]

    type_hint = {
        "mcp-server": "这是一个 MCP (Model Context Protocol) 服务器",
        "agent-tool": "这是一个 AI Agent 工具或框架",
        "agent-skill": "这是一个 Agent Skill 或 MCP 工具包",
    }.get(repo["type"], "这是一个 AI 相关工具")

    prompt = f"""你是一名技术写作者。用 2-3 句中文字介绍这个开源项目——它是什么、怎么用、为什么 AI 开发者应当关注。具体、不空洞。禁止使用 emoji，禁止使用「革命性」「游戏规则改变者」等 buzzwords。

{type_hint}。
项目: {repo['full_name']}
描述: {repo['description']}
语言: {repo['language']}
Star: {repo['stars']:,}
类型标签: {', '.join(repo.get('topics', []))}"""

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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Agent & MCP Tools...", file=sys.stderr)

    # Fetch from all three search dimensions
    all_repos = []
    for searcher in SEARCHES:
        print(f"  Searching: {searcher['label']}...", file=sys.stderr)
        repos = fetch_search(searcher)
        print(f"    Found {len(repos)} repos", file=sys.stderr)
        all_repos.extend(repos)

    # Merge, deduplicate, pick top 10
    top_repos = merge_deduplicate(all_repos, top_n=10)
    print(f"  Merged to {len(top_repos)} unique repos", file=sys.stderr)

    # Load cache
    cache = load_cache()

    # Generate summaries (skip if cached and stars unchanged)
    summaries = {}
    for repo in top_repos:
        name = repo["full_name"]
        cached = cache.get(name, {})
        if cached and cached.get("stars") == repo["stars"] and cached.get("summary"):
            print(f"  {name} — cached (⭐ {repo['stars']:,}) [{repo['type_label']}]", file=sys.stderr)
            summaries[name] = cached["summary"]
        else:
            print(f"  {name} — generating summary (⭐ {repo['stars']:,}) [{repo['type_label']}]...", file=sys.stderr)
            summaries[name] = generate_summary(repo)
            time.sleep(0.5)  # rate limit

    # Build output
    output = {
        "generated_at": datetime.now().isoformat(),
        "generated_week": datetime.now().strftime("%Y-W%W"),
        "tools": [
            {
                **repo,
                "summary": summaries[repo["full_name"]],
                "stars_formatted": f"{repo['stars']:,}",
            }
            for repo in top_repos
        ],
        "stats": {
            "total_mcp": sum(1 for r in top_repos if r["type"] == "mcp-server"),
            "total_agent": sum(1 for r in top_repos if r["type"] == "agent-tool"),
            "total_skill": sum(1 for r in top_repos if r["type"] == "agent-skill"),
        },
    }

    # Write output
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))

    # Update cache
    save_cache(top_repos, summaries)

    print(f"  ✅ Written to {OUTPUT_FILE}", file=sys.stderr)
    print(f"     MCP: {output['stats']['total_mcp']} | Agent: {output['stats']['total_agent']} | Skill: {output['stats']['total_skill']}", file=sys.stderr)


if __name__ == "__main__":
    main()
