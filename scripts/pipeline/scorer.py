#!/usr/bin/env python3
"""Stage 3: Scorer — heuristic quality scoring for articles."""

import re
from datetime import datetime, timedelta, timezone

from . import get_db


# Source authority weights (0-100)
AUTHORITY = {
    "OpenAI Blog":      95,
    "Google AI":        90,
    "Google DeepMind":  92,
    "Anthropic":        90,     # not currently in SOURCES but future-proof
    "Meta AI":          85,
    "Apple ML Research": 88,
    "NVIDIA Blog":      82,
    "HuggingFace Blog": 80,
    "PyTorch Blog":     78,
    "ArXiv cs.AI":      95,
    "ArXiv cs.LG":      95,
    "ArXiv cs.CL":      95,
    "ArXiv cs.CV":      92,
    "ArXiv stat.ML":    92,
    "雷锋网 AI":        65,
    "TechCrunch AI":    70,
    "VentureBeat AI":   68,
}

# AI-related keywords for relevance scoring
AI_KEYWORDS = [
    "llm", "gpt", "transformer", "fine-tun", "rag", "agent",
    "benchmark", "mmlu", "humaneval", "gsm8k", "sota",
    "diffusion", "stable diffusion", "image generat",
    "rlhf", "reinforcement learning", "dpo", "ppo",
    "embedding", "vector database", "semantic search",
    "open source", "open-source", "weights", "checkpoint",
    "quantiz", "gguf", "gptq", "awq", "lora", "qlora",
    "multimodal", "vision language", "vlm", "speech",
    "code generat", "copilot", "codex",
    "neural network", "deep learning", "machine learning",
    "attention", "token", "context window", "inference",
    "训练", "模型", "大模型", "推理", "微调", "部署",
    "开源", "参数", "基准", "评测",
]


def score_authority(source_name: str) -> float:
    """Return 0-1 authority score based on source reputation."""
    return AUTHORITY.get(source_name, 50) / 100.0


def score_timeliness(published: str) -> float:
    """Return 0-1 freshness score. Newer = higher, decays over 7 days."""
    if not published or published == "Unknown":
        return 0.3
    try:
        pub_date = datetime.strptime(published[:19], "%Y-%m-%d %H:%M:%S")
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.3

    age = datetime.now(timezone.utc) - pub_date
    days = age.total_seconds() / 86400
    if days <= 0:
        return 1.0
    elif days >= 7:
        return 0.1
    return max(0.1, 1.0 - (days / 7))


def score_depth(title: str, summary: str) -> float:
    """Return 0-1 technical depth score based on length and signal words."""
    if not summary:
        return 0.0

    # Length component
    total_len = len(summary)
    length_score = min(total_len / 300, 1.0) * 0.5

    # Technical signal words
    tech_signals = [
        "benchmark", "accuracy", "precision", "%", "outperform",
        "state-of-the-art", "sota", "parameter", "training",
        "dataset", "ablation", "experiment", "evaluation",
        "performance", "scale", "compute", "latency", "throughput",
        "improve", "novel", "architecture", "framework",
    ]
    text = (title + " " + summary).lower()
    signal_count = sum(1 for s in tech_signals if s in text)
    signal_score = min(signal_count / 5, 1.0) * 0.5

    return length_score + signal_score


def score_relevance(title: str, summary: str, category: str) -> float:
    """Return 0-1 AI relevance score."""
    text = (title + " " + summary).lower()
    match_count = sum(1 for kw in AI_KEYWORDS if kw.lower() in text)
    return min(match_count / 5, 1.0)


def compute_total(auth: float, time: float, depth: float, rel: float) -> float:
    """Weighted total score 0-100."""
    return (auth * 25 + time * 20 + depth * 30 + rel * 25)


def run() -> dict:
    """Score all unscored articles."""
    print("📊 Scorer — computing quality scores...")

    conn = get_db()

    # Get articles scanned today that haven't been scored yet
    rows = conn.execute("""
        SELECT id, title, summary, published, source_name, category
        FROM articles
        WHERE score_total = 0
    """).fetchall()

    if not rows:
        print("   All articles already scored")
        conn.close()
        return {"scored": 0}

    scored = 0
    for row in rows:
        auth = score_authority(row["source_name"])
        time_s = score_timeliness(row["published"])
        depth = score_depth(row["title"], row["summary"])
        rel = score_relevance(row["title"], row["summary"], row["category"])
        total = compute_total(auth, time_s, depth, rel)

        conn.execute("""
            UPDATE articles SET
            score_authority = ?, score_timeliness = ?, score_depth = ?,
            score_relevance = ?, score_total = ?
            WHERE id = ?
        """, (auth, time_s, depth, rel, total, row["id"]))
        scored += 1

    conn.commit()

    # Show score distribution
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            ROUND(AVG(score_total), 1) as avg_score,
            ROUND(MAX(score_total), 1) as max_score,
            ROUND(MIN(score_total), 1) as min_score
        FROM articles
        WHERE score_total > 0
    """).fetchone()

    conn.close()

    print(f"   Scored {scored} articles")
    print(f"   Score range: {stats['min_score']} – {stats['max_score']} (avg {stats['avg_score']})")
    return {"scored": scored, "avg_score": stats["avg_score"]}


if __name__ == "__main__":
    run()
