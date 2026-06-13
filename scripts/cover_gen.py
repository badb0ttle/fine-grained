"""Generate Zhihu cover image for weekly AI briefing."""
import sys, os, json, re, textwrap
from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 675  # 16:9

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def make_cover(date_str, keywords, out_path):
    """Generate cover with dark theme + purple gradient + keywords."""
    bg = Image.new('RGBA', (W, H), hex_to_rgb('#0a0a0f'))
    draw = ImageDraw.Draw(bg)

    # Gradient overlay (top-left purple to bottom-right cyan)
    for y in range(H):
        t = y / H
        r = int(108 * (1 - t) + 0 * t)    # #6C5CE7 → #00cec9
        g = int(92 * (1 - t) + 206 * t)
        b = int(231 * (1 - t) + 201 * t)
        for x in range(0, W, 4):
            alpha = int(20 * (1 - abs(x/W - 0.5) * 1.5))
            alpha = max(0, min(30, alpha))
            color = (r, g, b)
            bg.putpixel((x, y), color + (alpha,))

    # Convert back to RGB for JPEG compatibility
    bg_rgb = Image.new('RGB', (W, H), (10, 10, 15))
    bg_rgb.paste(bg, (0, 0), bg)
    draw = ImageDraw.Draw(bg_rgb)

    # Try to load system fonts
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/Helvetica.ttc',
    ]
    title_font = None
    body_font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                if title_font is None:
                    title_font = ImageFont.truetype(fp, 48)
                elif body_font is None:
                    body_font = ImageFont.truetype(fp, 22)
            except:
                pass
        if title_font and body_font:
            break

    if title_font is None:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    # Draw decorative line (top)
    for x in range(80, W - 80):
        alpha = int(40 * (1 - abs(x/W - 0.5) * 2))
        if alpha > 0:
            draw.point((x, 60), fill=(108, 92, 231))

    # Title: 本周 AI 大事记
    title = "本周 AI 大事记"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 120), title, fill=(232, 233, 240), font=title_font)

    # Date
    date_display = date_str
    bbox = draw.textbbox((0, 0), date_display, font=ImageFont.truetype(font_paths[0], 28) if os.path.exists(font_paths[0]) else body_font)
    dw = bbox[2] - bbox[0]
    date_color = (0, 206, 201)  # cyan
    try:
        date_font = ImageFont.truetype(font_paths[0], 28)
    except:
        date_font = body_font
    draw.text(((W - dw) // 2, 195), date_display, fill=date_color, font=date_font)

    # Keywords (2-3 lines max)
    keyword_font = body_font
    if keywords:
        # Wrap keywords to fit
        max_line_w = W - 200
        lines = []
        current = ''
        for kw in keywords.replace('·', '·').split('·'):
            kw = kw.strip()
            if not kw:
                continue
            test = (current + ' · ' + kw) if current else kw
            bbox = draw.textbbox((0, 0), test, font=keyword_font)
            if bbox[2] - bbox[0] > max_line_w and current:
                lines.append(current)
                current = kw
            else:
                current = test
        if current:
            lines.append(current)

        y_start = 280
        for i, line in enumerate(lines[:3]):
            bbox = draw.textbbox((0, 0), line, font=keyword_font)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, y_start + i * 38), line, fill=(196, 196, 212), font=keyword_font)

    # Bottom: website URL + decorative line
    for x in range(80, W - 80):
        alpha = int(40 * (1 - abs(x/W - 0.5) * 2))
        if alpha > 0:
            draw.point((x, H - 60), fill=(0, 206, 201))

    url = "ai.hjhai.xyz"
    try:
        url_font = ImageFont.truetype(font_paths[0], 18) if os.path.exists(font_paths[0]) else body_font
    except:
        url_font = body_font
    bbox = draw.textbbox((0, 0), url, font=url_font)
    uw = bbox[2] - bbox[0]
    draw.text(((W - uw) // 2, H - 45), url, fill=(108, 92, 231), font=url_font)

    # Subtle branding top-left
    try:
        brand_font = ImageFont.truetype(font_paths[0], 14) if os.path.exists(font_paths[0]) else body_font
    except:
        brand_font = body_font
    draw.text((80, 32), "AllOfAI", fill=(108, 92, 231, 128), font=brand_font)

    bg_rgb.save(out_path, 'PNG', quality=95)
    print(f"Cover saved: {out_path}")


if __name__ == '__main__':
    if len(sys.argv) >= 4:
        date_str = sys.argv[1]
        keywords = sys.argv[2]
        out_path = sys.argv[3]
    else:
        # Default: use latest week
        date_str = date.today().strftime('%Y-%m-%d')
        # Try to read keywords from index.json
        idx_path = Path('/Users/mac/Desktop/Projects/ai-intel/data/weekly/index.json')
        keywords = "AI Agent · LLM · 模型效率"
        if idx_path.exists():
            data = json.loads(idx_path.read_text())
            if data.get('reports'):
                kw = data['reports'][0].get('summary', keywords)
                if kw:
                    keywords = kw
        out_path = f'/Users/mac/Desktop/ZhiHu/cover_{date_str}.png'

    make_cover(date_str, keywords, out_path)
