#!/usr/bin/env python3
"""
量子位独立采集器 (Fetch QbitAI)
================================
独立抓取量子位 (www.qbitai.com) 的最新 AI 资讯。

为什么独立采集：
- 量子位无 RSS feed，需从 HTML 页面抓取
- 网站反爬（Cloudflare），需要特殊 User-Agent 和请求头
- 内容量大，单独采集避免影响 Pipeline 主流程的稳定性

抓取源：
- 首页：www.qbitai.com（最新文章列表）
- 分类页：www.qbitai.com/category/xxx

关键点：
- 使用 requests + BeautifulSoup4 解析 HTML
- 模拟 Chrome 浏览器 User-Agent 绕过基础反爬
- 提取标题、摘要、发布时间、封面图
- 输出到 data/qbitai.json

局限性：
- Cloudflare Turnstile 可能阻断（必要时回退到 Selenium/Playwright）
- 页面布局可能变更，使用 fallback 选择器
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

REPO_DIR = Path(__file__).resolve().parent

# ── 量子位 URL 列表 ──
# 首页 + 各分类频道
QBITAI_URLS = [
    ("首页", "https://www.qbitai.com"),
    ("AI", "https://www.qbitai.com/category/人工智能"),
    ("大模型", "https://www.qbitai.com/tag/大模型"),
]


def fetch_page(url: str) -> str:
    """
    HTTP GET 请求，返回 HTML 内容。

    使用 Chrome User-Agent 模拟浏览器，设置较长超时。

    Args:
        url: 目标页面 URL。

    Returns:
        str: HTML 内容。失败返回空字符串。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.qbitai.com/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        # 检测是否被 Cloudflare 拦截（页面内容极少 + 含 "challenge" 字样）
        if len(resp.text) < 500 and "challenge" in resp.text.lower():
            print(f"  ⚠️  Blocked by Cloudflare: {url}")
            return ""
        return resp.text
    except Exception as e:
        print(f"  ⚠️  Error fetching {url}: {e}")
        return ""


def parse_articles(html: str, source_name: str) -> list:
    """
    从 HTML 中提取文章列表。

    量子位文章卡片常见选择器（页面结构经常变化，使用多级 fallback）：
    1. article 标签（标准 HTML5 语义）
    2. div.post-item / div.article-item（常见 CMS 模板）
    3. 任意含标题链接的 div + h3 组合

    每篇文章提取：title, link, summary, time, image

    Args:
        html: 页面 HTML 内容。
        source_name: 抓取来源名称（用于标记）。

    Returns:
        list[dict]: 文章列表。
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # ── 策略 1：查找 article 标签 ──
    for article_tag in soup.find_all("article"):
        try:
            title_tag = article_tag.find(["h2", "h3", "h4"])
            if not title_tag:
                continue

            link_tag = title_tag.find("a")
            title = (link_tag.get_text(strip=True) if link_tag else title_tag.get_text(strip=True))
            link = link_tag.get("href", "") if link_tag else ""

            # 补全相对链接
            if link and not link.startswith("http"):
                link = f"https://www.qbitai.com{link}"

            # 摘要：优先取 p 标签，其次取 article 内容的前 200 字符
            summary_tag = article_tag.find("p")
            summary = summary_tag.get_text(strip=True) if summary_tag else ""

            # 时间：查找 time 标签或 class 含 "time" 的 span
            time_tag = article_tag.find("time")
            if not time_tag:
                time_tag = article_tag.find("span", class_=re.compile(r"time|date", re.I))
            pub_time = time_tag.get_text(strip=True) if time_tag else ""

            # 封面图
            img_tag = article_tag.find("img")
            image = img_tag.get("src", "") if img_tag else ""

            articles.append({
                "title": title,
                "link": link,
                "summary": summary[:200],
                "time": pub_time,
                "image": image,
                "source": f"量子位-{source_name}",
            })
        except Exception:
            continue

    # ── 策略 2：fallback — 查找任何含 h3 + a 的 div ──
    if not articles:
        for div in soup.find_all("div"):
            h3 = div.find("h3")
            if not h3:
                continue
            link_tag = h3.find("a")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            link = link_tag.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.qbitai.com{link}"

            summary_tag = div.find("p")
            summary = summary_tag.get_text(strip=True) if summary_tag else ""

            articles.append({
                "title": title,
                "link": link,
                "summary": summary[:200],
                "time": "",
                "image": "",
                "source": f"量子位-{source_name}",
            })
            if len(articles) >= 20:  # 上限，避免页面杂讯
                break

    return articles


def main():
    """
    主函数：遍历量子位各频道 → 抓取 → 去重 → 保存。

    去重策略：按标题前 80 字符。

    Returns:
        int: 0 成功。
    """
    print("📰 QuantumBit (量子位) AI News Fetcher\n")

    all_articles = []

    # 逐频道抓取
    for name, url in QBITAI_URLS:
        print(f"  [{name}] {url}...", end=" ", flush=True)
        html = fetch_page(url)
        if not html:
            print("❌ failed")
            continue

        articles = parse_articles(html, name)
        print(f"✅ {len(articles)} articles")
        all_articles.extend(articles)

    # ── 去重：按标题前 80 字符 ──
    seen = set()
    unique = []
    for a in all_articles:
        key = a["title"].strip().lower()[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(a)

    print(f"\n📊 Total: {len(unique)} unique articles")

    # ── 保存结果 ──
    if unique:
        output = {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "source": "qbitai.com",
            "article_count": len(unique),
            "articles": unique,
        }

        out_path = REPO_DIR.parent / "data" / "qbitai.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved to {out_path}")

        # 简要预览
        for a in unique[:5]:
            print(f"  • {a['title']}")
    else:
        print("⚠️  No articles found — site may have changed structure")

    return 0


if __name__ == "__main__":
    sys.exit(main())
