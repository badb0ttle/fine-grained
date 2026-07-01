#!/usr/bin/env python3
"""
模型排行榜 — 从 OpenRouter API 拉取模型数据，导出排名 JSON。

================================================================================
模块功能
================================================================================
独立数据源模块，从 OpenRouter API (https://openrouter.ai/api/v1/models) 获取
所有可用模型的元数据、定价和基准评测分数，处理后导出为排行榜 JSON。
  1. fetch_and_export: 主函数 — 拉取、过滤、排序、导出完整排行榜
  2. export_top_json:   导出精简版 Top-N 排行榜（供周报/详情页使用）

================================================================================
数据来源
================================================================================
OpenRouter API (https://openrouter.ai/api/v1/models):
  - 返回所有可用模型的 JSON 数据
  - 每个模型包含: id, name, pricing, context_length, architecture, benchmarks
  - benchmarks 子对象包含 Artificial Analysis 和 Design Arena 的评测分数

================================================================================
模型过滤规则 (should_include)
================================================================================
从原始 API 返回中过滤掉不合适的模型:
  1. ID 以 "~" 开头:  社区/实验模型（非官方）
  2. 包含 :free/:beta/:experimental: 免费/测试/实验版本
  3. 无定价或价格为 0: 未正式上线的模型
  4. context_length < 2048: 上下文太短的模型（无法处理有意义的任务）
  5. ID 含 test/demo/deprecated/debug/echo: 非生产用途模型

================================================================================
排序策略
================================================================================
多级排序（全部降序）:
  1. 有 benchmark 分数的优先（scores is not None → True > False）
  2. Design Arena ELO 最高优先（竞技场对战得分）
  3. Artificial Analysis intelligence_index（综合智能指数）
  4. Artificial Analysis coding_index（编程能力指数）
  5. created 时间戳（最新发布的排前面，作为 tiebreaker）

================================================================================
输出文件
================================================================================
  data/model_leaderboard.json      — 完整排行榜 (~200KB)
  data/model_leaderboard_top.json  — Top-N 精简版 (~5KB，供周报 sidebar)
"""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = REPO_DIR / "data" / "model_leaderboard.json"
API_URL = "https://openrouter.ai/api/v1/models"

# ============================================================================
# 提供商名称映射
# ============================================================================
# 将模型 ID 前缀映射为友好的提供商名称
# 如 "openai/gpt-4o" → "OpenAI", "anthropic/claude-3.5-sonnet" → "Anthropic"
PROVIDER_MAP = {
    # 国际主流
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google",
    "meta-llama": "Meta", "mistralai": "Mistral AI", "mistral": "Mistral AI",
    "deepseek": "DeepSeek", "qwen": "Alibaba", "alibaba": "Alibaba",
    "01-ai": "01.AI", "x-ai": "xAI", "nvidia": "NVIDIA",
    "moonshotai": "Moonshot AI", "cohere": "Cohere", "amazon": "Amazon",
    "microsoft": "Microsoft", "ai21": "AI21 Labs", "minimax": "MiniMax",
    # 中国厂商
    "stepfun": "StepFun", "zhipuai": "Zhipu AI", "baichuan": "Baichuan",
    "bytedance": "ByteDance", "nex-agi": "Nex AGI",
    # 开源/社区
    "liquid": "Liquid AI", "sao10k": "Sao10K", "nousresearch": "Nous Research",
    "perplexity": "Perplexity", "phind": "Phind", "recursal": "Recursal",
    "targon": "Targon", "featherless": "Featherless", "infermatic": "Infermatic",
    "kluster": "Kluster", "hyperbolic": "Hyperbolic",
    # 基础设施提供商
    "together": "Together AI", "fireworks": "Fireworks", "groq": "Groq",
    "cerebras": "Cerebras", "sambanova": "SambaNova", "z-ai": "Z.ai",
}


def extract_provider(model_id: str) -> str:
    """
    从模型 ID 中提取并映射提供商名称。

    解析逻辑:
      1. 去除前导 "~"（社区标记）
      2. 如果包含 "/"，取第一个 "/" 之前的部分作为前缀
      3. 在 PROVIDER_MAP 中查找映射
      4. 未命中时使用备选: 将前缀的 "-" 替换为空格并做 Title Case

    Args:
        model_id: 模型 ID，如 "openai/gpt-4o" 或 "~sao10k/l3-stheno"

    Returns:
        友好的提供商名称，如 "OpenAI", "Sao10K"
    """
    clean = model_id.lstrip("~")
    if "/" in clean:
        prefix = clean.split("/")[0].lower()
    else:
        prefix = clean.lower()
    return PROVIDER_MAP.get(prefix, prefix.replace("-", " ").title())


def should_include(model: dict) -> bool:
    """
    判断一个模型是否应该包含在排行榜中。

    过滤掉以下几类模型:
      - 社区/实验模型: ID 以 "~" 开头
      - 非正式版本: 包含 :free, :beta, :experimental 等
      - 未定价: pricing.prompt 为 0 或不存在
      - 上下文过短: context_length < 2048（无法处理有意义的任务）
      - 测试/废弃模型: ID 含 test, demo, deprecated, debug, echo

    Args:
        model: OpenRouter API 返回的模型字典

    Returns:
        True 表示应保留，False 表示应过滤
    """
    mid = model["id"]
    # "~" 前缀表示社区/实验模型，非官方发布
    if mid.startswith("~"):
        return False
    # 免费/测试/实验版本 — 非稳定正式版
    if ":free" in mid or ":beta" in mid or ":experimental" in mid:
        return False
    # 无定价信息或价格为 0 — 未正式上线
    pricing = model.get("pricing", {})
    if not pricing.get("prompt") or float(pricing["prompt"]) == 0:
        return False
    # 上下文窗口过小 — 不适合实际使用
    if model.get("context_length", 0) < 2048:
        return False
    # 测试/废弃/调试模型 — 非生产用途
    skip_patterns = ["test", "demo", "deprecated", "debug", "echo"]
    if any(p in mid.lower() for p in skip_patterns):
        return False
    return True


def format_price(price_str: str) -> str:
    """
    格式化每百万 token 价格。

    OpenRouter API 返回的 price 是每 token 价格，需乘以 1,000,000 转为常用单位。
    显示规则:
      - < $0.01: 3 位小数显示 (如 "$0.005")
      - $0.01-$1: 2 位小数显示 (如 "$0.15")
      - ≥ $1: 1 位小数显示 (如 "$2.5")

    Args:
        price_str: API 返回的价格字符串（每 token 美元价格）

    Returns:
        格式化后的价格字符串，如 "$0.15"；解析失败返回 "?"
    """
    try:
        p = float(price_str) * 1_000_000   # 转为每百万 token 价格
        if p < 0.01: return f"${p:.3f}"
        elif p < 1: return f"${p:.2f}"
        else: return f"${p:.1f}"
    except (ValueError, TypeError):
        return "?"


def format_context(n: int) -> str:
    """
    格式化上下文窗口大小。

    规则:
      - ≥1,000,000: 显示为 "1.0M" 格式
      - ≥1,000:     显示为 "128K" 格式
      - 其他:        原样显示

    Args:
        n: 上下文窗口大小（token 数）

    Returns:
        格式化后的字符串，如 "128K", "1.0M"
    """
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    elif n >= 1_000: return f"{n//1_000}K"
    return str(n)


def get_tags(model: dict) -> list[str]:
    """
    提取模型的标签/能力标签。

    从 architecture.modality 提取多模态标签:
      - image → "vision"
      - video → "video"
      - audio → "audio"
      - file  → "file"

    额外标签:
      - context_length ≥ 1,000,000 → "1M+ctx" (超长上下文)
      - top_provider.is_moderated → "moderated" (内容审核)

    Args:
        model: OpenRouter API 返回的模型字典

    Returns:
        标签字符串列表，如 ["vision", "1M+ctx"]
    """
    tags = []
    arch = model.get("architecture", {})
    modality = arch.get("modality", "")
    if "image" in modality: tags.append("vision")
    if "video" in modality: tags.append("video")
    if "audio" in modality: tags.append("audio")
    if "file" in modality: tags.append("file")
    # 百万级上下文标记
    if model.get("context_length", 0) >= 1_000_000: tags.append("1M+ctx")
    tp = model.get("top_provider", {})
    if tp.get("is_moderated"): tags.append("moderated")
    return tags


def extract_scores(model: dict) -> dict | None:
    """
    从模型数据中提取基准评测分数。

    数据来源:
      【Artificial Analysis (AA)】 — 综合智能/编程/Agent 三大指数 (0-100)
        - intelligence_index: 综合智能指数
        - coding_index:       编程能力指数
        - agentic_index:      Agent 能力指数

      【Design Arena (DA)】 — 竞技场 ELO 分（按类别）
        - best_elo:                   所有类别中的最高 ELO 分
        - best_elo_category:          取得最高 ELO 的类别名称
        - elo_categories:            各分类的详细战绩 [{category, elo, win_rate, rank}]

    Args:
        model: OpenRouter API 返回的模型字典

    Returns:
        评分字典，如果无评测数据则返回 None
    """
    benchmarks = model.get("benchmarks", {})
    if not benchmarks:
        return None

    scores = {}

    # ---- Artificial Analysis: 数值型指数 (0-100) ----
    aa = benchmarks.get("artificial_analysis", {})
    if isinstance(aa, dict):
        ii = aa.get("intelligence_index")
        if ii is not None:
            scores["intelligence"] = round(float(ii), 1)
        ci = aa.get("coding_index")
        if ci is not None:
            scores["coding"] = round(float(ci), 1)
        ai = aa.get("agentic_index")
        if ai is not None:
            scores["agentic"] = round(float(ai), 1)

    # ---- Design Arena: ELO 竞技分数 ----
    da = benchmarks.get("design_arena", [])
    if isinstance(da, list) and da:
        # 找出所有类别中 ELO 最高的
        best = max(da, key=lambda e: e.get("elo", 0) if isinstance(e, dict) else 0)
        if isinstance(best, dict) and "elo" in best:
            scores["best_elo"] = best["elo"]
            scores["best_elo_category"] = best.get("category", "?")
            # 各分类的详细战绩
            scores["elo_categories"] = [
                {"category": e.get("category", "?"), "elo": e.get("elo"),
                 "win_rate": e.get("win_rate"), "rank": e.get("rank")}
                for e in da if isinstance(e, dict) and e.get("elo")
            ]
            # 按 ELO 降序排列，方便前端展示最强领域
            scores["elo_categories"].sort(key=lambda x: -(x["elo"] or 0))

    return scores if scores else None


def fetch_and_export() -> dict:
    """
    主函数: 从 OpenRouter API 拉取、过滤、排序并导出模型排行榜。

    完整流程:
      1. HTTP GET 请求 OpenRouter API（带 User-Agent）
      2. 解析 JSON 响应，提取 data[ ] 数组
      3. should_include 过滤: 排除社区/测试/实验/免费模型
      4. 提取每个模型: 提供商、定价、上下文、标签、评测分数
      5. 多级排序: 有分数优先 > ELO 降序 > AA 智能降序 > AA 编程降序 > 最新优先
      6. 写入 data/model_leaderboard.json
      7. 输出 Top 供应商统计

    Returns:
        {
          updated_at: str (ISO 时间戳),
          total_models: int,
          source: "OpenRouter API",
          models: [{ rank, id, name, provider, description, created, context_length,
                     context_display, max_output, price_input, price_output,
                     price_input_raw, price_output_raw, tags, modality,
                     knowledge_cutoff, scores }]
        }
    """
    print("[Leaderboard] Fetching from OpenRouter API...")
    req = urllib.request.Request(API_URL, headers={"User-Agent": "AllOfAI/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())

    all_models = data.get("data", [])
    print(f"  Raw: {len(all_models)} models")

    # ---- 过滤非正式/测试模型 ----
    filtered = [m for m in all_models if should_include(m)]
    print(f"  After filter: {len(filtered)} models")

    with_scores = 0  # 有 benchmark 分数的模型计数

    entries = []
    for m in filtered:
        pricing = m.get("pricing", {})
        tp = m.get("top_provider", {})
        max_out = tp.get("max_completion_tokens") if tp else None
        scores = extract_scores(m)
        if scores:
            with_scores += 1

        # 构建模型条目
        entry = {
            "id": m["id"],
            "name": m.get("name", m["id"]),  # display name，回退到 ID
            "provider": extract_provider(m["id"]),
            "description": (m.get("description", "") or "")[:200],  # 截断长描述
            "created": m.get("created"),                             # Unix 时间戳
            "context_length": m.get("context_length"),
            "context_display": format_context(m.get("context_length", 0)),
            "max_output": format_context(max_out) if max_out else None,  # 最大输出 token 数
            "max_output_raw": max_out,
            # 价格: 每百万 token 的美元价格（格式化显示 + 原始值）
            "price_input": format_price(pricing.get("prompt", "0")),
            "price_output": format_price(pricing.get("completion", "0")),
            "price_input_raw": float(pricing.get("prompt", 0)),
            "price_output_raw": float(pricing.get("completion", 0)),
            "tags": get_tags(m),
            "modality": m.get("architecture", {}).get("modality", "text"),
            "knowledge_cutoff": m.get("knowledge_cutoff"),  # 知识截止日期
            "scores": scores,
        }
        entries.append(entry)

    # ---- 多级排序 ----
    # 排序优先级（全部降序):
    #   1. 有 benchmark 分数 > 无分数
    #   2. Design Arena ELO 降序
    #   3. Artificial Analysis intelligence 降序
    #   4. Artificial Analysis coding 降序
    #   5. created 时间戳降序（最新发布排前面）
    entries.sort(key=lambda e: (
        e.get("scores") is not None,                                              # 有分数的排前面
        e["scores"].get("best_elo", 0) if e.get("scores") else 0,                 # ELO 竞技分
        e["scores"].get("intelligence", 0) if e.get("scores") else 0,             # AA 综合智能
        e["scores"].get("coding", 0) if e.get("scores") else 0,                   # AA 编程能力
        e.get("created", 0),                                                      # 发布时间（tiebreaker）
    ), reverse=True)

    # 添加排名序号
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_models": len(entries),
        "source": "OpenRouter API",
        "models": entries,
    }

    # ---- 导出 JSON ----
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"  Exported: {OUTPUT_FILE} ({len(entries)} models, {with_scores} with scores)")

    # ---- Top 供应商统计 ----
    providers = {}
    for e in entries:
        p = e["provider"]
        providers[p] = providers.get(p, 0) + 1
    top_providers = sorted(providers.items(), key=lambda x: -x[1])[:10]
    print(f"  Top providers: {', '.join(f'{p}({c})' for p,c in top_providers)}")

    return result


def export_top_json(top_n: int = 20) -> dict:
    """
    导出精简版 Top-N 排行榜，供周报/详情页侧边栏使用。

    与完整榜相比，精简版只包含:
      - name:        模型名称
      - provider:    提供商
      - rank:        排名
      - scores.intelligence: AI 智能指数（仅保留最关键的维度）

    这样 payload 从 ~200KB 降到 ~5KB，大幅减少周报页面的加载体积。

    注意: 如果 model_leaderboard.json 不存在（首次运行），会先调用 fetch_and_export 生成。

    Args:
        top_n: 导出前 N 个模型，默认 20

    Returns:
        {
          updated_at: str,
          source: "OpenRouter API (top N by benchmark)",
          models: [{ name, provider, rank, scores: { intelligence } }]
        }
    """
    path = REPO_DIR / "data" / "model_leaderboard.json"
    if not path.exists():
        fetch_and_export()  # 首次运行先生成完整排行榜

    data = json.loads(path.read_text())
    all_models = data.get("models", [])

    # 按排名顺序取有 intelligence 分数的模型
    top = []
    for m in all_models:
        scores = m.get("scores")
        if scores and scores.get("intelligence") is not None:
            top.append({
                "name": m["name"],
                "provider": m.get("provider", ""),
                "rank": m.get("rank"),
                "scores": {
                    "intelligence": scores.get("intelligence"),
                },
            })
            if len(top) >= top_n:
                break

    result = {
        "updated_at": data.get("updated_at"),
        "source": f"OpenRouter API (top {top_n} by benchmark)",
        "models": top,
    }

    top_path = REPO_DIR / "data" / "model_leaderboard_top.json"
    top_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[Leaderboard] Exported top {len(top)} to {top_path}")
    return result


if __name__ == "__main__":
    result = fetch_and_export()
    # 展示 Top 5 有 benchmark 分数的模型
    scored = [m for m in result["models"] if m.get("scores")]
    print(f"\nTop 5 (with scores):")
    for m in scored[:5]:
        s = m["scores"]
        parts = [f"int={s.get('intelligence','?')}", f"code={s.get('coding','?')}", f"agent={s.get('agentic','?')}"]
        if s.get("best_elo"):
            parts.append(f"ELO={s['best_elo']}({s.get('best_elo_category','?')})")
        print(f"  #{m['rank']} {m['name']} — {', '.join(parts)}")
