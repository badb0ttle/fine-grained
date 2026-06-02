#!/usr/bin/env python3
"""Model Tracker — extract model info and benchmark scores from articles."""

from datetime import datetime, timezone

from . import get_db


def get_candidate_articles(limit: int = 20) -> list[dict]:
    """Get recent curated/high-score articles that might mention models."""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, title_cn, summary, summary_cn, link, source_name, published
        FROM articles
        WHERE (curated = 1 OR score_total >= 70)
        ORDER BY score_total DESC, published DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_extraction_prompt(articles: list[dict]) -> str:
    """Generate prompt for LLM to extract model info."""
    article_texts = []
    for i, a in enumerate(articles, 1):
        title = a["title_cn"] or a["title"]
        summary = (a["summary_cn"] or a["summary"] or "")[:300]
        article_texts.append(f"[{i}] {title}\n    {summary}\n")

    prompt = f"""从以下 AI 相关文章中提取大模型信息。对于每篇提到的模型，提取：

- name: 模型名称（如 "GPT-5.5", "Gemini 3.1 Pro", "MiniMax-M3"）
- provider: 模型提供方（如 "OpenAI", "Google", "MiniMax"）
- benchmarks: 文章中提到的 Benchmark 分数列表，每项含 {{"name": "MMLU", "score": "92.5%"}}
- parameters: 参数规模（如 "未知", "1.8T"）
- context_window: 上下文窗口（如 "1M tokens", "128K"）

返回严格 JSON 数组：
[
  {{"name": "模型名", "provider": "提供方", "benchmarks": [{{"name":"...","score":"..."}}], "parameters": "..."}},
  ...
]
如果一篇文章没有提到具体模型，跳过它。

文章列表：
{chr(10).join(article_texts)}"""
    return prompt


def apply_models(models_data: list[dict]) -> dict:
    """Apply extracted model data to DB. Returns stats."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    new_models = 0
    new_benchmarks = 0

    for m in models_data:
        name = m.get("name", "").strip()
        if not name:
            continue

        # Upsert model
        conn.execute("""
            INSERT INTO models (name, provider, parameters, context_window, description)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
            provider = COALESCE(NULLIF(excluded.provider, ''), provider),
            parameters = COALESCE(NULLIF(excluded.parameters, ''), parameters),
            context_window = COALESCE(NULLIF(excluded.context_window, ''), context_window),
            description = COALESCE(NULLIF(excluded.description, ''), description)
        """, (
            name,
            m.get("provider", ""),
            m.get("parameters", ""),
            m.get("context_window", ""),
            m.get("description", ""),
        ))
        if conn.total_changes > 0:
            new_models += 1

        # Get model_id
        model_row = conn.execute("SELECT id FROM models WHERE name = ?", (name,)).fetchone()
        if not model_row:
            continue
        model_id = model_row["id"]

        # Insert benchmarks
        for b in m.get("benchmarks", []):
            bname = b.get("name", "").strip()
            bscore = b.get("score", "").strip()
            if not bname or not bscore:
                continue
            # Avoid duplicates: same model + benchmark + score
            existing = conn.execute("""
                SELECT id FROM model_benchmarks
                WHERE model_id = ? AND benchmark = ? AND score = ?
            """, (model_id, bname, bscore)).fetchone()
            if not existing:
                conn.execute("""
                    INSERT INTO model_benchmarks (model_id, benchmark, score, reported_at)
                    VALUES (?, ?, ?, ?)
                """, (model_id, bname, bscore, now))
                new_benchmarks += 1

    conn.commit()
    conn.close()

    print(f"🤖 Model Tracker: {new_models} models, {new_benchmarks} benchmark scores")
    return {"new_models": new_models, "new_benchmarks": new_benchmarks}


def get_leaderboard() -> list[dict]:
    """Get all models with their benchmarks, sorted."""
    conn = get_db()
    models = conn.execute("""
        SELECT id, name, provider, parameters, context_window, release_date
        FROM models ORDER BY name
    """).fetchall()

    result = []
    for m in models:
        benchmarks = conn.execute("""
            SELECT benchmark, score, reported_at
            FROM model_benchmarks WHERE model_id = ?
            ORDER BY reported_at DESC
        """, (m["id"],)).fetchall()

        result.append({
            "name": m["name"],
            "provider": m["provider"],
            "parameters": m["parameters"],
            "context_window": m["context_window"],
            "release_date": m["release_date"],
            "benchmarks": [{"benchmark": b["benchmark"], "score": b["score"]} for b in benchmarks],
        })

    conn.close()
    return result


def export_leaderboard_json() -> dict:
    """Export leaderboard data for frontend."""
    models = get_leaderboard()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
    }


if __name__ == "__main__":
    import json
    articles = get_candidate_articles(10)
    print(f"📋 {len(articles)} candidate articles for model extraction")
    if articles:
        print(f"   Top: {articles[0]['title_cn'] or articles[0]['title'][:60]}")
        prompt = get_extraction_prompt(articles[:5])
        print(f"\n--- Prompt (first 500 chars) ---")
        print(prompt[:500])
