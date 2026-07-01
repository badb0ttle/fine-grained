#!/usr/bin/env python3
"""
GitHub AI 项目 Top5 抓取器 + DeepSeek 摘要
===========================================
从 GitHub Trending 中筛选 AI/ML/LLM 相关的热门仓库，并调用 DeepSeek API 生成中文摘要。

工作流程：
1. 抓取 GitHub Trending 页面（weekly 时间跨度），解析 HTML 提取仓库卡片
2. 按关键词过滤（AI/ML/LLM/Deep Learning 等），选择前 5 个
3. 对每个仓库抓取 README（1000 字截断）
4. 调用 DeepSeek API 生成中文摘要（100字以内）
5. 保存到 data/github_top5.json

输出数据：
{
  "scanned_at": "ISO时间",
  "repos": [
    {
      "name": "user/repo",
      "url": "https://github.com/user/repo",
      "description": "GitHub 原文描述",
      "stars": 1234,
      "language": "Python",
      "summary_cn": "DeepSeek 生成的中文摘要"
    },
    ...
  ]
}

局限：
- GitHub Trending 页面是动态渲染的，纯 requests 可能无法获取完整数据
- 作为 fallback，也尝试使用非官方 trending API
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

from scripts.pipeline.api_client import call_llm

# ── AI 项目关键词（用于二级筛选） ──
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "large language model", "gpt", "transformer", "diffusion",
    "neural network", "nlp", "natural language", "computer vision",
    "reinforcement learning", "generative", "stable diffusion", "langchain",
    "agent", "rag", "vector database", "embedding", "fine-tuning",
    "open source ai", "llama", "mistral", "mixture of experts",
]


def fetch_trending() -> list:
    """
    抓取 GitHub Trending 页面（weekly 时间范围）。

    解析 HTML：
    - 每个仓库在 <article class="Box-row"> 中
    - 仓库名：h2 > a 的 href（如 "/user/repo"）
    - 描述：p 标签（class 含 "col-9"）
    - Stars：最后一个 svg 后的 span（class 含 "d-inline-block"）
    - 语言：span[itemprop="programmingLanguage"]

    Returns:
        list[dict]: 仓库信息列表，字段含 name, url, description, stars, language, description_lower。
    """
    url = "https://github.com/trending?since=weekly"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AI-Intel-Bot/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch trending: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    repos = []
    # 找到所有仓库卡片（article 标签）
    articles = soup.find_all("article", class_="Box-row")
    for article in articles:
        # 提取仓库名和链接
        h2 = article.find("h2")
        if not h2:
            continue

        link_tag = h2.find("a")
        if not link_tag:
            continue

        repo_path = link_tag.get("href", "").strip()
        if not repo_path or not repo_path.startswith("/"):
            continue

        repo_name = repo_path.strip("/")
        # 跳过镜像/归档仓库（通常含 "mirror" 或 "archive" 标签）
        if "mirror" in repo_name.lower() or "awesome" in repo_name.lower():
            continue

        repo_url = f"https://github.com{repo_path}"

        # 提取描述
        desc_tag = article.find("p", class_=lambda c: c and "col-9" in c)
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 提取 Stars 数量
        stars = 0
        star_spans = article.find_all("span", class_=lambda c: c and "d-inline-block" in c)
        for span in star_spans:
            text = span.get_text(strip=True).replace(",", "")
            try:
                stars = int(text)
                break  # 第一个数字通常是 stars
            except ValueError:
                continue

        # 提取编程语言
        lang_tag = article.find("span", itemprop="programmingLanguage")
        language = lang_tag.get_text(strip=True) if lang_tag else "Unknown"

        repos.append({
            "name": repo_name,
            "url": repo_url,
            "description": description,
            "stars": stars,
            "language": language,
            "description_lower": description.lower() + " " + repo_name.lower(),
        })

    return repos


def filter_ai_repos(repos: list) -> list:
    """
    按 AI 关键词过滤仓库。

    匹配范围：仓库名 + 描述（小写后匹配）。

    Args:
        repos: 全量 trending 仓库列表。

    Returns:
        list[dict]: AI 相关仓库，取前 5 个（按 stars 降序）。
    """
    ai_repos = []
    for repo in repos:
        text = repo["description_lower"]
        if any(keyword in text for keyword in AI_KEYWORDS):
            ai_repos.append(repo)

    # 按 stars 降序，取前 5
    ai_repos.sort(key=lambda r: r["stars"], reverse=True)
    top5 = ai_repos[:5]

    return top5


def fetch_readme(repo_name: str) -> str:
    """
    从 raw.githubusercontent.com 抓取仓库 README.md（前 1000 字符）。

    尝试顺序：README.md → readme.md → 带下划线的变体

    Args:
        repo_name: 仓库全名（如 "user/repo"）。

    Returns:
        str: README 内容（截断至 1000 字符）。失败返回空字符串。
    """
    filenames = ["README.md", "readme.md", "Readme.md", "README.rst"]
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AI-Intel-Bot/1.0)",
    }
    for fname in filenames:
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/main/{fname}"
        try:
            resp = requests.get(raw_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.text[:1000]  # 截断以控制 prompt 长度
            # 也尝试 master 分支
            raw_url = f"https://raw.githubusercontent.com/{repo_name}/master/{fname}"
            resp = requests.get(raw_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.text[:1000]
        except Exception:
            continue

    return ""


def generate_summary_cn(repo: dict, readme: str) -> str:
    """
    调用 DeepSeek API 生成中文摘要。

    摘要要求（在 prompt 中指定）：
    - 100 字以内
    - 突出核心功能和用途
    - 中文输出

    Args:
        repo: 仓库信息字典（含 name, description, stars 等）。
        readme: README 文件内容（已截断）。

    Returns:
        str: 中文摘要。API 失败返回 repo description 原文。
    """
    if not readme and not repo.get("description"):
        return "暂无描述"

    prompt = f"""你是 GitHub 项目分析专家。请为以下 AI 项目生成中文摘要，要求如下：
- 100 字以内
- 突出核心功能和用途
- 简洁明了

项目名：{repo['name']}
描述：{repo.get('description', '无')}

README 片段：
{readme[:800]}

请直接输出中文摘要："""

    try:
        resp = call_llm(
            prompt=prompt,
            system_prompt="你是开源 AI 项目分析专家。请提供简洁准确的项目摘要。",
            max_tokens=200,
        )
        summary = resp.get("content", "").strip().strip('"').strip("'")
        return summary[:120]  # 兜底截断
    except Exception as e:
        print(f"  ⚠️  LLM summary failed for {repo['name']}: {e}")
        return repo.get("description", "暂无描述")


def main():
    """
    主函数：抓取 → 过滤 → 摘要 → 保存。

    Returns:
        int: 0 成功。
    """
    print("🌟 GitHub AI Top5 with DeepSeek Summary\n")

    # Step 1: 抓取 GitHub Trending
    print("📡 Fetching GitHub Trending...")
    repos = fetch_trending()
    print(f"   → {len(repos)} total trending repos")

    # Step 2: 按 AI 关键词过滤
    print("🔍 Filtering AI-related repos...")
    top5 = filter_ai_repos(repos)
    print(f"   → {len(top5)} AI repos selected")

    if not top5:
        print("⚠️  No AI repos found in trending")
        return 0

    # Step 3: 抓取 README + 生成摘要
    print("\n📝 Generating summaries via DeepSeek...")
    for repo in top5:
        print(f"   [{repo['language']}] {repo['name']} ⭐{repo['stars']}")
        readme = fetch_readme(repo["name"])
        repo["summary_cn"] = generate_summary_cn(repo, readme)
        print(f"     → {repo['summary_cn'][:80]}...")

    # Step 4: 保存结果
    output = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "source": "github_trending_weekly",
        "repo_count": len(top5),
        "repos": top5,
    }

    out_path = REPO_DIR.parent / "data" / "github_top5.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved to {out_path}")

    # 简要预览
    print("\n🌟 Top 5 AI Repos on GitHub:")
    for i, repo in enumerate(top5, 1):
        print(f"  {i}. {repo['name']} ⭐{repo['stars']}")
        print(f"     {repo['summary_cn'][:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
