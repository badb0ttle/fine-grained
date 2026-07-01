#!/usr/bin/env python3
"""
站点地图生成器 (Sitemap Generator)
==================================
为 ai.hjhai.xyz 生成标准 sitemap.xml，帮助搜索引擎（Google/Bing/Baidu）发现和索引页面。

输出位置：docs/sitemap.xml（随 GitHub Pages 一起部署）

包含页面：
- 静态页面：首页 /, Leaderboard, Timeline, Clusters, Weekly, About
- 动态页面：周报详情页（从 data/weekly/index.json 读取最近12期）
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 项目根目录和站点 URL
REPO_DIR = Path(__file__).resolve().parent.parent
SITE_URL = "https://ai.hjhai.xyz"


def generate() -> str:
    """
    生成完整的 sitemap.xml 内容。

    包含：
    - 静态页面（固定路径 + 优先级 + 更新频率）
    - 动态周报页面（从 weekly index.json 读取）

    Returns:
        str: 完整的 XML sitemap 字符串。
    """
    # ── 静态页面定义：(路径, 更新频率, 优先级) ──
    urls = [
        ("/", "daily", "1.0"),          # 首页 — 最高优先级
        ("/leaderboard", "daily", "0.9"),
        ("/timeline", "daily", "0.8"),
        ("/clusters", "weekly", "0.7"),
        ("/weekly", "daily", "0.9"),    # 周报列表 — 高频更新
        ("/about", "monthly", "0.8"),
    ]

    # ── 动态添加周报详情页 ──
    weekly_index = REPO_DIR / "data" / "weekly" / "index.json"
    if weekly_index.exists():
        index_data = json.loads(weekly_index.read_text())
        weeks = index_data.get("reports", [])
        for w in weeks[:12]:  # 最近 12 期周报
            date = w.get("date", "")
            if date:
                urls.append((f"/weekly/{date}", "weekly", "0.7"))

    # 使用当前日期作为 lastmod（Google 偏好准确的最后修改时间）
    now = datetime.utcnow().strftime("%Y-%m-%d")

    # 逐条构造 <url> XML 片段
    entries = []
    for path, freq, pri in urls:
        entries.append(f"""  <url>
    <loc>{SITE_URL}{path}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{pri}</priority>
  </url>""")

    # 组装完整 sitemap
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(entries)}
</urlset>"""


def main():
    """
    主函数：生成 sitemap 并写入 docs/ 目录。

    Returns:
        int: 0 成功。
    """
    sitemap = generate()
    out_path = REPO_DIR / "docs" / "sitemap.xml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(sitemap)
    print(f"✅ Sitemap: {out_path} ({len(sitemap)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
