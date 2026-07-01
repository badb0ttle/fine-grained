#!/usr/bin/env python3
"""
趋势分析器 — 关键词频率追踪与趋势检测。

================================================================================
模块功能
================================================================================
独立于主 Pipeline 的趋势分析模块，用于追踪 AI 领域关键词的热度变化。
  1. 从数据库统计当前周期和上一周期的关键词出现频率
  2. 计算环比变化百分比，判断趋势方向（surging/rising/stable/declining/falling）
  3. 输出 Top-20 最动态关键词，供 publisher.py 的 export_stats_json 调用

================================================================================
核心算法
================================================================================
时间窗口设计:
  - 当前周期: [now - days, now]
  - 上一周期: [now - days×2, now - days]
  - days 默认为 7，即可比较"本周 vs 上周"

趋势方向判定:
  - change_pct ≥ +50%:  surging  (飙升)
  - change_pct ≥ +10%:  rising   (上升)
  - change_pct ≤ -30%:  falling  (暴跌)
  - change_pct ≤ -10%:  declining(下降)
  - 其他:               stable   (稳定)

特殊情况:
  - 上周期为 0 当前有数据: change_pct = 100 (视为新出现，标记为 new)
  - 两个周期都为 0: 跳过该关键词（无意义）
  - 使用 scanned_at 而非 published 做时间窗口筛选（published 格式不统一）

================================================================================
TREND_KEYWORDS 设计
================================================================================
关键词列表涵盖六大 AI 领域:
  1. 模型类型:   LLM, GPT, Claude, Gemini, Mistral, Llama, DeepSeek
  2. 技术方法:   RLHF, DPO, LoRA, RAG, Agent, 微调
  3. 推理部署:   量化, GGUF, 推理加速, deploy
  4. 代码领域:   代码生成, Codex, Copilot
  5. 基础设施:   GPU, 算力, benchmark, MMLU
  6. 应用领域:   机器人, 医疗, 自动驾驶, 安全对齐
"""

from datetime import datetime, timedelta

from . import get_db

# ============================================================================
# 趋势追踪关键词列表
# ============================================================================
# 涵盖模型类型、技术方法、推理部署、代码、基础设施、应用六大领域
# 中英双语混合，确保覆盖中文和英文文章
TREND_KEYWORDS = [
    # --- 模型类型 (Model Types) ---
    "LLM", "GPT", "Claude", "Gemini", "Mistral", "Llama", "DeepSeek",
    "多模态", "multimodal", "VLM", "视觉语言",

    # --- 训练技术 (Training Techniques) ---
    "RLHF", "DPO", "强化学习", "fine-tun", "微调", "LoRA", "QLoRA",
    "RAG", "检索增强", "Agent", "智能体", "function calling",

    # --- 推理与量化 (Inference & Quantization) ---
    "量化", "quantiz", "GGUF", "GPTQ", "AWQ",

    # --- 代码领域 (Code) ---
    "代码生成", "code", "Codex", "Copilot",
    "推理", "reasoning", "chain-of-thought", "CoT",
    "embeddings", "向量", "vector",

    # --- 开源 (Open Source) ---
    "开源", "open-source", "open source", "weights",

    # --- 基础设施 (Infrastructure) ---
    "GPU", "算力", "inference", "推理加速", "deploy", "部署",
    "benchmark", "MMLU", "HumanEval", "GSM8K",

    # --- 应用 (Applications) ---
    "机器人", "robotics", "自动驾驶", "autonomous",
    "医疗", "medical", "蛋白质", "protein",
    "安全", "safety", "alignment", "对齐",
]


def compute_trends(days: int = 7) -> dict:
    """
    计算关键词趋势：当前周期 vs 上一周期的频率对比。

    算法步骤:
      1. 定义两个时间窗口: 当前周期 [now-days, now], 上一周期 [now-2*days, now-days]
      2. 使用内嵌函数 count_by_scanned 统计每个关键词在两个窗口中的出现次数
      3. 逐关键词计算环比变化百分比
      4. 根据变化幅度判定趋势方向
      5. 按变化幅度的绝对值降序排列，返回 Top-20

    使用 scanned_at 而非 published 做时间筛选的原因:
      - published 字段格式不统一（有的带时区，有的不带）
      - scanned_at 格式统一且始终为 ISO 格式，WHERE 条件更可靠

    Args:
        days: 时间窗口天数，默认 7（一周）

    Returns:
        {
          keywords: [
            { keyword, current_count, previous_count, change_pct, direction },
          ] (Top-20, 按 |change_pct| 降序),
          period: { current_start, current_end, previous_start, previous_end, window_days }
        }
    """
    conn = get_db()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")

    # 计算时间窗口边界
    current_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    previous_start = (now - timedelta(days=days*2)).strftime("%Y-%m-%d")
    previous_end = current_start  # 上一周期结束 = 当前周期开始

    def count_by_scanned(start_date: str, end_date: str) -> dict[str, int]:
        """
        通过 scanned_at 字段统计指定时间窗口内各关键词的出现次数。

        使用 LIKE '%keyword%' 做大小写不敏感匹配。
        每个关键词做一次独立查询，复杂度 O(N×M)（N=关键词数, M=数据库行数），
        但对于数千篇文章和数十个关键词的规模足够高效。

        Args:
            start_date: 起始日期（含），格式 "YYYY-MM-DD"
            end_date:   结束日期（不含），格式 "YYYY-MM-DDTHH:MM:SS"

        Returns:
            { 关键词: 出现次数 } 的计数字典
        """
        counts = {}
        for kw in TREND_KEYWORDS:
            rows = conn.execute("""
                SELECT COUNT(*) FROM articles
                WHERE scanned_at >= ? AND scanned_at < ?
                AND (LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)
            """, (start_date, end_date, f"%{kw.lower()}%", f"%{kw.lower()}%")).fetchone()
            counts[kw] = rows[0]
        return counts

    # 统计两个时间窗口的关键词频率
    current = count_by_scanned(current_start, today + "T23:59:59")
    previous = count_by_scanned(previous_start, previous_end)

    conn.close()

    # ---- 构建趋势结果 ----
    keywords = []
    for kw in TREND_KEYWORDS:
        curr = current.get(kw, 0)
        prev = previous.get(kw, 0)

        # 两个周期都为 0: 无趋势，跳过
        if curr == 0 and prev == 0:
            continue

        # 计算环比变化百分比
        if prev > 0:
            # 正常情况: 有上一周期数据，计算环比
            change_pct = round((curr - prev) / prev * 100, 1)
        elif curr > 0:
            # 新出现的关键词: 上周期为 0，当前有数据
            change_pct = 100  # 视为 100% 增长
        else:
            change_pct = 0

        # ---- 判定趋势方向 ----
        # 阈值设计:
        #   surging ≥50%: 显著增长，可能是重要趋势
        #   rising ≥10%:  温和增长
        #   falling ≤-30%: 显著下降（阈值高于 rising 是因为下降通常更剧烈且信息价值更高）
        #   declining ≤-10%: 温和下降
        #   其他: stable
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

    # 按变化幅度的绝对值降序排列（最动态的排在前面）
    keywords.sort(key=lambda k: abs(k["change_pct"]), reverse=True)

    return {
        "keywords": keywords[:20],  # 只返回 Top-20 最动态关键词
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
        # 方向对应的箭头符号
        arrow = {"surging": "🚀", "rising": "📈", "falling": "📉", "declining": "🔻", "stable": "➡️", "new": "🆕"}[k["direction"]]
        print(f"   {arrow} {k['keyword']}: {k['previous_count']}→{k['current_count']} ({k['change_pct']:+.1f}%) [{k['direction']}]")
