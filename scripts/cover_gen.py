#!/usr/bin/env python3
"""
封面图生成器 (Cover Gen)
=========================
为周报和文章自动生成社交媒体封面图（Open Graph / Twitter Card）。

功能：
1. 读取 weekly index.json 获取最新周报信息
2. 使用 Pillow 渲染模板（渐变背景 + 标题文字 + 日期 + Logo）
3. 输出 1200×630 PNG 图片到 docs/covers/ 目录

模板设计：
- 渐变背景：深蓝 (#1a1a2e) → 深紫 (#16213e)
- 标题：白色，PingFang SC / Noto Sans 字体，居中
- 日期：灰色小字
- Logo 区：左下角 "AllOfAI" 品牌标识

技术栈：Pillow（Python Imaging Library）
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

# ── 路径常量 ──
REPO_DIR = Path(__file__).resolve().parent
COVERS_DIR = REPO_DIR.parent / "docs" / "covers"
WEEKLY_INDEX = REPO_DIR.parent / "data" / "weekly" / "index.json"

# ── 封面尺寸（Open Graph 标准） ──
WIDTH, HEIGHT = 1200, 630

# ── 配色方案 ──
BG_TOP = (26, 26, 46)        # 深蓝
BG_BOTTOM = (22, 33, 62)     # 深紫
TEXT_COLOR = (255, 255, 255)  # 白色
SUB_TEXT_COLOR = (180, 180, 200)  # 灰紫色


def load_weekly_data() -> dict:
    """
    加载周报索引信息。

    Returns:
        dict: 周报索引数据，含 reports 列表。无数据时返回空 dict。
    """
    if not WEEKLY_INDEX.exists():
        return {}
    with open(WEEKLY_INDEX, "r", encoding="utf-8") as f:
        return json.load(f)


def draw_gradient_background(draw, width, height):
    """
    绘制从上到下的双色渐变背景。

    算法：逐行插值 BG_TOP → BG_BOTTOM。

    Args:
        draw: PIL ImageDraw 对象。
        width: 图片宽度。
        height: 图片高度。
    """
    for y in range(height):
        # 线性插值：t = 0（顶部）→ 1（底部）
        t = y / height
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        # 逐行绘制（高效替代：ImageDraw.rectangle 批量绘制）
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def create_cover(title: str, date_str: str, issue_num: int) -> Image.Image:
    """
    生成单张封面图。

    布局（从上到下）：
    - ~30% 空白留白
    - 大号标题（自动换行，最多3行）
    - 日期 + 期号
    - ~20% 底部品牌标识

    Args:
        title: 封面标题文本。
        date_str: 日期字符串（如 "2025-01-15 ~ 2025-01-21"）。
        issue_num: 周报期号。

    Returns:
        PIL.Image: 生成的封面图像。
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(img)

    # ── 绘制渐变背景 ──
    draw_gradient_background(draw, WIDTH, HEIGHT)

    # ── 加载字体（PingFang SC 是 macOS 默认中文字体） ──
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 56)
        font_date = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 28)
        font_brand = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
    except (OSError, IOError):
        # fallback：使用 Pillow 默认字体（可能不支持中文）
        font_title = ImageFont.load_default()
        font_date = ImageFont.load_default()
        font_brand = ImageFont.load_default()

    # ── 标题文字：居中，自动换行 ──
    title_lines = []
    max_chars_per_line = 22  # 1200px 宽度大约 22 个中文字符
    words = list(title)
    current_line = ""
    for word in words:
        if len(current_line) + 1 <= max_chars_per_line:
            current_line += word
        else:
            title_lines.append(current_line)
            current_line = word
    if current_line:
        title_lines.append(current_line)

    # 限制最多 3 行
    title_lines = title_lines[:3]

    line_height = 70  # 行间距
    total_title_height = len(title_lines) * line_height
    title_start_y = 180  # 标题区域起始 Y 坐标

    for idx, line in enumerate(title_lines):
        # 使用 textbbox 计算文字宽度，实现精确居中
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (WIDTH - text_width) / 2
        y = title_start_y + idx * line_height
        draw.text((x, y), line, fill=TEXT_COLOR, font=font_title)

    # ── 日期 + 期号 ──
    date_text = f"📅 {date_str}  ·  第 {issue_num} 期"
    date_y = title_start_y + total_title_height + 40
    bbox = draw.textbbox((0, 0), date_text, font=font_date)
    date_width = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - date_width) / 2, date_y),
        date_text,
        fill=SUB_TEXT_COLOR,
        font=font_date,
    )

    # ── 底部品牌标识 ──
    brand_text = "AllOfAI  ·  ai.hjhai.xyz"
    draw.text((40, HEIGHT - 60), brand_text, fill=SUB_TEXT_COLOR, font=font_brand)

    return img


def main():
    """
    主函数：从周报索引读取最新一期信息并生成封面图。

    Returns:
        int: 0 成功，1 没有周报数据，2 其他错误。
    """
    print("🎨 Cover Generator\n")

    data = load_weekly_data()
    reports = data.get("reports", [])

    if not reports:
        print("⚠️  No weekly reports found")
        return 1

    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 为最近一期生成封面 ──
    latest = reports[0]
    date_str = latest.get("date", datetime.now().strftime("%Y-%m-%d"))
    title = latest.get("title", "AI 技术周报")
    issue_num = latest.get("issue", len(reports))

    print(f"  标题: {title}")
    print(f"  日期: {date_str}")
    print(f"  期号: 第 {issue_num} 期")

    # 生成封面图
    img = create_cover(title, date_str, issue_num)

    # 保存到 docs/covers/ 目录
    filename = f"weekly-{date_str}.png"
    out_path = COVERS_DIR / filename
    img.save(out_path, "PNG", optimize=True)
    print(f"\n✅ Cover saved: {out_path} ({out_path.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
