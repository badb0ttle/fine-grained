#!/usr/bin/env python3
"""Trend Analyzer — keyword frequency tracking and trend detection."""

from datetime import datetime, timedelta

from . import get_db

# Key AI trends to track
TREND_KEYWORDS = [
    # Model types
    "LLM", "GPT", "Claude", "Gemini", "Mistral", "Llama", "DeepSeek",
    "多模态", "multimodal", "VLM", "视觉语言",
    # Techniques
    "RLHF", "DPO", "强化学习", "fine-tun", "微调", "LoRA", "QLoRA",
    "RAG", "检索增强", "Agent", "智能体", "function calling",
    "量化", "quantiz", "GGUF", "GPTQ", "AWQ",
    # Domains
    "代码生成", "code", "Codex", "Copilot",
    "推理", "reasoning", "chain-of-thought", "CoT",
    "embeddings", "向量", "vector",
    "开源", "open-source", "open source", "weights",
    # Infrastructure
    "GPU", "算力", "inference", "推理加速", "deploy", "部署",
    "benchmark", "MMLU", "HumanEval", "GSM8K",
    # Applications
    "机器人", "robotics", "自动驾驶", "autonomous",
    "医疗", "medical", "蛋白质", "protein",
    "安全", "safety", "alignment", "对齐",
]


def compute_trends(days: int = 7) -> dict:
    """Compute keyword trends: current period vs previous period.

    Returns dict with:
    - keywords: list of {keyword, current_count, previous_count, change_pct, direction}
    - period: {current_start, current_end, previous_start, previous_end}
    """
    conn = get_db()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")

    current_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    previous_start = (now - timedelta(days=days*2)).strftime("%Y-%m-%d")
    previous_end = current_start

    def count_keywords(start_date: str, end_date: str) -> dict[str, int]:
        """Count keyword occurrences in articles within date range."""
        counts = {}
        for kw in TREND_KEYWORDS:
            # Search title + summary for keyword (case-insensitive)
            rows = conn.execute("""
                SELECT COUNT(*) FROM articles
                WHERE published >= ? AND published < ?
                AND (LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)
            """, (start_date, end_date, f"%{kw.lower()}%", f"%{kw.lower()}%")).fetchone()
            counts[kw] = rows[0]
        return counts

    # But published dates are in format "2026-06-02 HH:MM:SS" — let's use scanned_at instead
    def count_by_scanned(start_date: str, end_date: str) -> dict[str, int]:
        counts = {}
        for kw in TREND_KEYWORDS:
            rows = conn.execute("""
                SELECT COUNT(*) FROM articles
                WHERE scanned_at >= ? AND scanned_at < ?
                AND (LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)
            """, (start_date, end_date, f"%{kw.lower()}%", f"%{kw.lower()}%")).fetchone()
            counts[kw] = rows[0]
        return counts

    # Use daily_stats dates to get the right windows
    # Simpler: just count articles scanned in the two windows
    current = count_by_scanned(current_start, today + "T23:59:59")
    previous = count_by_scanned(previous_start, previous_end)

    conn.close()

    # Build trend results
    keywords = []
    for kw in TREND_KEYWORDS:
        curr = current.get(kw, 0)
        prev = previous.get(kw, 0)

        if curr == 0 and prev == 0:
            continue

        if prev > 0:
            change_pct = round((curr - prev) / prev * 100, 1)
        elif curr > 0:
            change_pct = 100  # New keyword
        else:
            change_pct = 0

        if change_pct >= 50:
            direction = "surging"
        elif change_pct >= 10:
            direction = "rising"
        elif change_pct <= -30:
            direction = "falling"
        elif change_pct <= -10:
            direction = "declining"
        else:
            direction = "stable"

        keywords.append({
            "keyword": kw,
            "current_count": curr,
            "previous_count": prev,
            "change_pct": change_pct,
            "direction": direction,
        })

    # Sort by absolute momentum (change_pct magnitude)
    keywords.sort(key=lambda k: abs(k["change_pct"]), reverse=True)

    return {
        "keywords": keywords[:20],  # Top 20 most dynamic
        "period": {
            "current_start": current_start,
            "current_end": today,
            "previous_start": previous_start,
            "previous_end": previous_end,
            "window_days": days,
        }
    }


if __name__ == "__main__":
    import json
    trends = compute_trends(7)
    print(f"📈 Trend Analysis ({trends['period']['window_days']}d window)")
    print(f"   Current: {trends['period']['current_start']} → {trends['period']['current_end']}")
    print(f"   Previous: {trends['period']['previous_start']} → {trends['period']['previous_end']}")
    print(f"\n   Top trends:")
    for k in trends["keywords"][:10]:
        arrow = {"surging": "🚀", "rising": "📈", "falling": "📉", "declining": "🔻", "stable": "➡️", "new": "🆕"}[k["direction"]]
        print(f"   {arrow} {k['keyword']}: {k['previous_count']}→{k['current_count']} ({k['change_pct']:+.1f}%) [{k['direction']}]")
