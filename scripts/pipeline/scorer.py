#!/usr/bin/env python3
"""
阶段3: Scorer — 四维加权质量评分引擎。

================================================================================
模块功能
================================================================================
Pipeline 第三阶段：对已入库的文章进行启发式质量评分。
基于四个维度计算 0-100 的综合分数，用于后续 Curator 阶段的筛选排序。

================================================================================
评分公式
================================================================================
综合分数 = 四维子分数的加权求和（每维 0-1 归一化后乘权重）:

  total = authority × 25   (权威度 25%)
        + timeliness × 20  (时效性 20%)
        + depth × 30       (技术深度 30%)
        + relevance × 25   (AI 相关性 25%)

权重设计理由:
  - 技术深度权重最高 (30%)：受众是技术读者，深度内容最有价值
  - 权威度 25%：来自顶级机构的内容通常更可靠
  - AI 相关性 25%：确保内容聚焦 AI 领域
  - 时效性 20%：新闻价值随时间衰减，但不应对评分影响过大（经典论文仍有价值）

================================================================================
四维详解
================================================================================
1. 权威度 (Authority): 基于信源声誉的静态评分，从 AUTHORITY 字典查表
   - 顶级 AI Lab / ArXiv: 90-95 分
   - 科技媒体: 65-70 分
   - 未知信源: 50 分（默认及格线）

2. 时效性 (Timeliness): 基于发布时间到当前时间的天数线性衰减
   - 0 天内: 1.0
   - 7 天后: 0.1（底线，不归零）
   - 未知时间: 0.3（中等偏下，不假设太新也不假设太旧）

3. 技术深度 (Depth): 两个子维度各 0.5 权重
   - 长度分: 摘要长度 / 300 字符封顶，越长通常信息量越大
   - 信号分: 检测技术信号词（benchmark, accuracy, SOTA, ablation 等），
     匹配 ≥5 个即满分

4. AI 相关性 (Relevance): 匹配 AI_KEYWORDS 列表中的关键词
   - 在 title + summary 中做大小写不敏感匹配
   - 匹配 ≥5 个关键词即可满分
   - 关键词涵盖中英文技术术语
"""

import re
from datetime import datetime, timedelta, timezone

from . import get_db


# ============================================================================
# 权威度权重表 (0-100 原始分)
# ============================================================================
# 基于信源声誉预设的权威度分值。未列出的信源默认 50 分。
# 分值依据: 研究机构 > 学术论文 > 开源社区 > 科技媒体
AUTHORITY = {
    # 顶级 AI 研究机构 — 最高权威
    "OpenAI Blog":      95,
    "Google DeepMind":  92,
    "Google AI":        90,
    "Anthropic":        90,     # 预留给未来可能添加的信源
    "Meta AI":          85,
    "Apple ML Research": 88,
    "NVIDIA Blog":      82,
    # ArXiv 学术论文 — 同行评审或预印本，权威度高
    "ArXiv cs.AI":      95,
    "ArXiv cs.LG":      95,
    "ArXiv cs.CL":      95,
    "ArXiv cs.CV":      92,
    "ArXiv stat.ML":    92,
    # 开源社区/平台 — 中等权威
    "HuggingFace Blog": 80,
    "PyTorch Blog":     78,
    # 科技媒体 — 信息丰富但非一手来源
    "TechCrunch AI":    70,
    "VentureBeat AI":   68,
    "雷锋网 AI":        65,
}


# ============================================================================
# AI 相关性关键词列表
# ============================================================================
# 涵盖模型类型、训练技术、推理部署、评测基准等 AI 核心领域的术语
# 同时包含中文关键词，确保中文文章也能被正确评分
AI_KEYWORDS = [
    # --- 模型与架构 ---
    "llm", "gpt", "transformer", "fine-tun", "rag", "agent",
    "diffusion", "stable diffusion", "image generat",
    "multimodal", "vision language", "vlm", "speech",
    "neural network", "deep learning", "machine learning",
    # --- 训练与对齐 ---
    "rlhf", "reinforcement learning", "dpo", "ppo",
    # --- 推理与部署 ---
    "embedding", "vector database", "semantic search",
    "quantiz", "gguf", "gptq", "awq", "lora", "qlora",
    "attention", "token", "context window", "inference",
    # --- 代码与工具 ---
    "code generat", "copilot", "codex",
    # --- 评测与基准 ---
    "benchmark", "mmlu", "humaneval", "gsm8k", "sota",
    # --- 开源 ---
    "open source", "open-source", "weights", "checkpoint",
    # --- 中文关键词 ---
    "训练", "模型", "大模型", "推理", "微调", "部署",
    "开源", "参数", "基准", "评测",
]


def score_authority(source_name: str) -> float:
    """
    计算权威度子分数（0-1 归一化）。

    从 AUTHORITY 查表获取原始分（0-100），除以 100 归一化到 [0, 1]。
    未知信源默认 50 分（及格线），不高估也不惩罚新来源。

    Args:
        source_name: 信源名称（如 "OpenAI Blog", "ArXiv cs.AI"）

    Returns:
        0-1 之间的权威度分数
    """
    return AUTHORITY.get(source_name, 50) / 100.0


def score_timeliness(published: str) -> float:
    """
    计算时效性子分数（0-1 归一化），基于发布时间的线性衰减。

    衰减曲线:
      - 0 天前（刚发布）:  1.0
      - 3.5 天前:         0.5
      - 7 天前及更早:     0.1（硬底线，不归零——经典内容仍有价值）
      - 未知时间:         0.3（中性默认值）

    时间解析容错:
      - 如果 published 格式不符合 "%Y-%m-%d %H:%M:%S"，返回默认值 0.3
      - 注意原生 datetime 对象是 naive 的（无时区），手动添加 UTC 时区

    Args:
        published: 发布时间字符串，格式 "YYYY-MM-DD HH:MM:SS" 或 "Unknown"

    Returns:
        0-1 之间的时效性分数，最低 0.1
    """
    # 未知时间：返回中性默认值 0.3，不高估也不惩罚
    if not published or published == "Unknown":
        return 0.3
    try:
        # 取前 19 个字符（"YYYY-MM-DD HH:MM:SS"），忽略可能的微秒和时区后缀
        pub_date = datetime.strptime(published[:19], "%Y-%m-%d %H:%M:%S")
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.3  # 无法解析的日期格式，返回默认值

    age = datetime.now(timezone.utc) - pub_date
    days = age.total_seconds() / 86400  # 转换为天数

    if days <= 0:
        return 1.0  # 未来时间（时区差异），按最新处理
    elif days >= 7:
        return 0.1  # 7 天及更早，硬底线
    # 线性衰减: 1.0 → 0.1 跨越 7 天
    return max(0.1, 1.0 - (days / 7))


def score_depth(title: str, summary: str) -> float:
    """
    计算技术深度子分数（0-1 归一化）。

    两个各占 50% 权重的子维度:

    【长度分 (0.5 权重)】
      假设: 摘要越长，技术内容越丰富（在去除 HTML 标签后）
      公式: min(摘要长度 / 300, 1.0) × 0.5
      300 字符为满分的阈值，大多数高质量技术文章的摘要在此之上

    【信号分 (0.5 权重)】
      检测 title + summary 中的技术信号词
      信号词包括: benchmark, accuracy, SOTA, ablation, architecture 等
      匹配 ≥5 个信号词即可满分，每个信号词计 0.1

    Args:
        title:   文章标题
        summary: 文章摘要

    Returns:
        0-1 之间的技术深度分数
    """
    if not summary:
        return 0.0  # 无摘要的文章无法评估深度

    # ---- 子维度 1: 长度分 (50%) ----
    # 300 字符封顶归一化，覆盖绝大多数摘要长度
    total_len = len(summary)
    length_score = min(total_len / 300, 1.0) * 0.5

    # ---- 子维度 2: 技术信号分 (50%) ----
    # 这些词语通常出现在有技术深度的文章中，而非 PR 通稿
    tech_signals = [
        "benchmark", "accuracy", "precision", "%", "outperform",
        "state-of-the-art", "sota", "parameter", "training",
        "dataset", "ablation", "experiment", "evaluation",
        "performance", "scale", "compute", "latency", "throughput",
        "improve", "novel", "architecture", "framework",
    ]
    text = (title + " " + summary).lower()
    signal_count = sum(1 for s in tech_signals if s in text)
    # 匹配 ≥5 个信号词即可满分
    signal_score = min(signal_count / 5, 1.0) * 0.5

    return length_score + signal_score


def score_relevance(title: str, summary: str, category: str) -> float:
    """
    计算 AI 相关性子分数（0-1 归一化）。

    在 title + summary 中做大小写不敏感的关键词匹配。
    使用 AI_KEYWORDS 列表（涵盖模型、训练、推理、评测等领域术语，含中英文）。
    匹配 ≥5 个关键词即可满分。

    注意: category 参数目前未使用，保留以便未来按类别调整阈值。
          例如 Paper 类别可以适当降低阈值（学术论文默认与 AI 相关）。

    Args:
        title:    文章标题
        summary:  文章摘要
        category: 文章类别（预留参数，当前未使用）

    Returns:
        0-1 之间的 AI 相关性分数
    """
    text = (title + " " + summary).lower()
    match_count = sum(1 for kw in AI_KEYWORDS if kw.lower() in text)
    # 5 个关键词即可满分，避免过度依赖关键词密度
    return min(match_count / 5, 1.0)


def compute_total(auth: float, time: float, depth: float, rel: float) -> float:
    """
    计算加权综合分数（0-100 分制）。

    四维加权公式:
      total = authority × 25   (权威度: 信源声誉)
            + timeliness × 20  (时效性: 发布时间衰减)
            + depth × 30       (技术深度: 摘要长度 + 技术信号词)
            + relevance × 25   (相关性: AI 关键词匹配)

    各维度已归一化到 [0, 1]，乘以权重后求和即为 0-100 分。

    权重设计考量:
      - depth 最高 (30): 面向技术受众，深度内容最有价值
      - authority (25): 信源声誉是强质量信号但不是全部
      - relevance (25): 与 AI 领域的相关程度
      - timeliness (20): 时效重要但不应主导评分（经典内容仍有价值）

    Args:
        auth:  0-1 权威度分数
        time:  0-1 时效性分数
        depth: 0-1 技术深度分数
        rel:   0-1 AI 相关性分数

    Returns:
        0-100 的综合质量分数
    """
    return (auth * 25 + time * 20 + depth * 30 + rel * 25)


def run() -> dict:
    """
    运行评分主流程：对所有未评分的文章计算四维分数。

    筛选条件:
      - score_total = 0: 尚未评分的新文章
      - 不限制日期范围：如果某天 Scanner 入库但 Scorer 未运行，后续运行会补评分

    处理流程:
      1. 查询所有 score_total=0 的文章
      2. 逐条计算四个维度的子分数
      3. UPDATE 写入 score_authority / score_timeliness / score_depth / score_relevance / score_total
      4. 输出评分分布统计

    Returns:
        { scored: int, avg_score: float } — 本次评分数量和总平均分
    """
    print("📊 Scorer — computing quality scores...")

    conn = get_db()

    # 获取所有尚未评分的文章（score_total = 0 表示未评分）
    # 注意: 不限制日期范围，确保历史遗留的未评分文章也能被处理
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
        # ---- 逐篇计算四个维度的子分数 ----
        auth = score_authority(row["source_name"])
        time_s = score_timeliness(row["published"])
        depth = score_depth(row["title"], row["summary"])
        rel = score_relevance(row["title"], row["summary"], row["category"])
        total = compute_total(auth, time_s, depth, rel)

        # ---- 写入评分结果 ----
        # 将子分数和总分一起更新，方便后续分析各维度的表现
        conn.execute("""
            UPDATE articles SET
            score_authority = ?, score_timeliness = ?, score_depth = ?,
            score_relevance = ?, score_total = ?
            WHERE id = ?
        """, (auth, time_s, depth, rel, total, row["id"]))
        scored += 1

    conn.commit()

    # ---- 评分分布统计 ----
    # 展示整体评分质量: 平均分、最高分、最低分
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
