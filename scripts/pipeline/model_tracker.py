#!/usr/bin/env python3
"""
模型追踪模块 (Model Tracker)
=============================
从已收录文章中自动提取大模型信息（名称、提供方、Benchmark分数、参数规模等），
并存入 models / model_benchmarks 表，支撑前端 Leaderboard 展示。

技术栈：SQLite + LLM（由调用方传入提取结果）。
职责边界：本模块只负责 DB 读写和 Prompt 构造，不直接调用 LLM API。
"""

from datetime import datetime, timezone

from . import get_db


def get_candidate_articles(limit: int = 20) -> list[dict]:
    """
    获取可能需要提取模型信息的候选文章列表。

    筛选条件：
    - curated=1（已入选精选）或 score_total >= 70（高质量文章）
    - 按综合评分降序、发布时间降序排序

    Args:
        limit: 最大返回数量，默认 20 篇。

    Returns:
        list[dict]: 文章字典列表，包含 id, title, title_cn, summary, summary_cn,
                    link, source_name, published 等字段。
    """
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
    """
    生成用于 LLM 的模型信息提取 Prompt。

    将文章列表（含标题 + 前300字摘要）拼接为结构化 Prompt，
    要求 LLM 返回严格 JSON 数组格式的模型信息。

    Args:
        articles: 候选文章列表，每篇需包含 title_cn/title 和 summary_cn/summary。

    Returns:
        str: 发送给 LLM 的完整 Prompt 文本。
    """
    # 构造每篇文章的文本块：编号 + 中文标题 + 摘要（截断至300字）
    article_texts = []
    for i, a in enumerate(articles, 1):
        title = a["title_cn"] or a["title"]  # 优先使用中文标题
        summary = (a["summary_cn"] or a["summary"] or "")[:300]  # 截断避免超长
        article_texts.append(f"[{i}] {title}\n    {summary}\n")

    # 组装 Prompt：要求提取模型名称、提供方、Benchmark、参数规模、上下文窗口
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
    """
    将 LLM 提取的模型数据写入数据库。

    执行逻辑：
    1. 遍历每个模型，执行 UPSERT（INSERT OR REPLACE 语义）
    2. 对已有字段，只在非空时覆盖（COALESCE 保护）
    3. 为每个模型写入 Benchmark 分数，跳过重复记录
    4. 统计新增模型数和新增 Benchmark 数

    Args:
        models_data: LLM 返回的模型数据列表，每项含 name, provider, benchmarks 等。

    Returns:
        dict: {"new_models": int, "new_benchmarks": int} 统计信息。
    """
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()  # UTC 时间戳
    new_models = 0
    new_benchmarks = 0

    for m in models_data:
        name = m.get("name", "").strip()
        if not name:
            continue  # 跳过无名称的无效数据

        # ---- Upsert 模型 ----
        # ON CONFLICT(name) DO UPDATE：名称重复时更新字段
        # COALESCE(NULLIF(excluded.xxx, ''), provider)：新值为空则不覆盖旧值
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
        # 通过 changes() 判断是否实际插入了新行（非仅更新）
        if conn.execute("SELECT changes()").fetchone()[0]:
            new_models += 1

        # ---- 获取 model_id 用于后续 Benchmark 关联 ----
        model_row = conn.execute("SELECT id FROM models WHERE name = ?", (name,)).fetchone()
        if not model_row:
            continue
        model_id = model_row["id"]

        # ---- 插入 Benchmark 分数 ----
        for b in m.get("benchmarks", []):
            bname = b.get("name", "").strip()
            bscore = b.get("score", "").strip()
            if not bname or not bscore:
                continue  # 无效 Benchmark 跳过

            # 去重检查：同一模型 + 同一基准 + 同一分数不重复插入
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
    """
    获取完整的模型排行榜数据（含所有 Benchmark 分数）。

    从 models 和 model_benchmarks 两表联查，按模型名称排序。

    Returns:
        list[dict]: 每个模型含 name, provider, parameters, context_window,
                    release_date, benchmarks 列表。
    """
    conn = get_db()
    # 查询所有模型基础信息
    models = conn.execute("""
        SELECT id, name, provider, parameters, context_window, release_date
        FROM models ORDER BY name
    """).fetchall()

    result = []
    for m in models:
        # 查询该模型的所有 Benchmark 记录，按报告时间倒序
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
    """
    导出排行榜数据为前端可用的 JSON 格式。

    Returns:
        dict: {"generated_at": ISO时间, "models": [...]}
    """
    models = get_leaderboard()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
    }


if __name__ == "__main__":
    # 独立运行时的快速测试：获取候选文章并打印 Prompt 预览
    import json
    articles = get_candidate_articles(10)
    print(f"📋 {len(articles)} candidate articles for model extraction")
    if articles:
        print(f"   Top: {articles[0]['title_cn'] or articles[0]['title'][:60]}")
        prompt = get_extraction_prompt(articles[:5])
        print(f"\n--- Prompt (first 500 chars) ---")
        print(prompt[:500])
