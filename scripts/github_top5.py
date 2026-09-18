#!/usr/bin/env python3
"""独立抓取 GitHub AI 开源项目总 Star Top5，生成前端统一数据结构。

不依赖 Trending 或 LLM；简介来自 GitHub 原文。发布失败保留上次有效快照。
运行方式：python -m scripts.github_top5
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "github_top5.json"
TOPICS = ("artificial-intelligence", "machine-learning", "deep-learning", "llm", "ai")


def fetch_top5() -> dict:
    """通过 GitHub 多主题并集搜索获取总 Star 最高的五个 AI 项目。"""
    # 同一请求中的多个 topic 是交集；逐主题查询后去重才能得到并集。
    unique = {}
    for topic in TOPICS:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": f"topic:{topic} fork:false archived:false", "sort": "stars", "order": "desc", "per_page": 5},
            headers={"Accept": "application/vnd.github+json", "User-Agent": "AllOfAI-Top5"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", [])
        if payload.get("incomplete_results") or len(items) < 5:
            raise ValueError("GitHub Top5 search is incomplete; keeping previous snapshot")
        for item in items:
            unique[item["full_name"]] = item
    items = list(unique.values())
    if len(items) < 5:
        raise ValueError("GitHub returned fewer than five unique repositories")
    repos = []
    for item in sorted(items, key=lambda item: item["stargazers_count"], reverse=True)[:5]:
        stars = item["stargazers_count"]
        repos.append({
            "full_name": item["full_name"],
            "name": item["name"],
            "owner": item["owner"]["login"],
            "description": item.get("description") or "",
            "url": item["html_url"],
            "stars": stars,
            "stars_formatted": f"{stars:,}",
            "forks": item["forks_count"],
            "language": item.get("language") or "",
            "topics": item.get("topics", []),
            "summary": item.get("description") or "",
            "updated_at": item["updated_at"],
        })
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "github_search_stars", "repos": repos}


def refresh(output: Path = OUTPUT) -> dict:
    """完整抓取成功后原子替换快照，失败不改旧文件。"""
    data = fetch_top5()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return data


if __name__ == "__main__":
    result = refresh()
    print(f"Saved {len(result['repos'])} repositories to {OUTPUT}")
