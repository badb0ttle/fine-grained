#!/usr/bin/env python3
"""
RSS 2.0 Feed 生成器 (RSS Feed)
===============================
从 latest.json（精选文章数据）生成标准 RSS 2.0 XML Feed。

输出位置：
- docs/rss.xml：部署到 GitHub Pages 供 RSS 阅读器订阅
- data/rss.xml：本地备份

站点配置：
- 站点名：AllOfAI — 每日 AI 技术动态
- 站点地址：https://ai.hjhai.xyz
- 语言：zh-CN
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from html import escape

# 项目根目录
REPO_DIR = Path(__file__).resolve().parent.parent

# ── 站点元信息 ──
SITE_URL = "https://ai.hjhai.xyz"
SITE_TITLE = "AllOfAI — 每日 AI 技术动态"
SITE_DESC = "每日自动扫描全球 AI 信源，由 LLM 精选并深度解读的 AI 技术情报"


def rfc822_date(iso_str: str) -> str:
    """
    将 ISO 8601 日期字符串转换为 RSS 要求的 RFC 822 格式。

    RSS 2.0 规范要求 <pubDate> 使用 RFC 822 格式：
    例："Mon, 01 Jul 2026 12:00:00 +0000"

    Args:
        iso_str: ISO 格式日期字符串（如 "2026-07-01T12:00:00+00:00"）。

    Returns:
        str: RFC 822 格式的日期字符串。解析失败时返回当前 UTC 时间。
    """
    try:
        # 处理 Z 后缀 → +00:00 时区格式
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        # 解析失败：fallback 到当前 UTC 时间
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")


def generate() -> str:
    """
    生成完整的 RSS 2.0 XML 字符串。

    数据源：data/latest.json（经 LLM 精选和翻译的文章）
    仅取前 30 篇文章（RSS 阅读器通常显示最近条目）。

    Returns:
        str: 完整的 RSS XML 字符串。如果 latest.json 不存在返回空字符串。
    """
    data_path = REPO_DIR / "data" / "latest.json"
    if not data_path.exists():
        print(f"⚠️  {data_path} not found", file=sys.stderr)
        return ""

    data = json.loads(data_path.read_text())
    articles = data.get("articles", [])[:30]  # RSS 取最近 30 篇
    now = rfc822_date(data.get("curated_at", datetime.utcnow().isoformat()))

    # 逐篇构造 <item> XML 片段
    items = []
    for i, a in enumerate(articles):
        title = a.get("title_cn") or a.get("title", "")  # 优先中文标题
        link = a.get("link", "")
        summary = (a.get("summary_cn") or a.get("summary", ""))[:500]  # 截断至500字
        pub_date = rfc822_date(a.get("published", ""))
        source = a.get("source", "")
        category = a.get("category", "")
        why = a.get("why_it_matters", "")

        # 构造 <description>：摘要 + 重要性 + 来源信息
        desc_parts = [f"<p>{escape(summary)}</p>"]
        if why:
            desc_parts.append(f"<p><strong>重要性：</strong>{escape(why)}</p>")
        desc_parts.append(f"<p>来源：{escape(source)} · 分类：{escape(category)}</p>")

        # 构造 GUID：使用链接的最后一段作为稳定标识
        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <link>{escape(link)}</link>
      <guid isPermaLink="false">ai-intel-{a.get('link','').split('/')[-1] or i}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{"".join(desc_parts)}</description>
      <category>{escape(category)}</category>
      <source url="{SITE_URL}">{escape(source)}</source>
    </item>""")

    # 组装完整的 RSS XML（含 Atom 命名空间以支持自引用）
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_TITLE}</title>
    <link>{SITE_URL}</link>
    <description>{SITE_DESC}</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/rss.xml" rel="self" type="application/rss+xml"/>
    <generator>AllOfAI Pipeline</generator>
{chr(10).join(items)}
  </channel>
</rss>"""
    return rss


def main():
    """
    主函数：生成 RSS 并写入输出文件。

    输出两个副本：
    1. docs/rss.xml — 部署到 GitHub Pages
    2. data/rss.xml — 本地存档

    Returns:
        int: 0 成功，1 失败（数据不存在）。
    """
    rss = generate()
    if not rss:
        return 1

    # 写入部署目录（docs/ 用于 GitHub Pages）
    out_dir = REPO_DIR / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rss.xml"
    out_path.write_text(rss)
    print(f"✅ RSS: {out_path} ({len(rss)} bytes)")

    # 写入数据目录（本地备份）
    data_out = REPO_DIR / "data" / "rss.xml"
    data_out.write_text(rss)

    return 0


if __name__ == "__main__":
    sys.exit(main())
