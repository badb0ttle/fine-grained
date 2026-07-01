#!/usr/bin/env python3
"""
AI Agent 追踪器 (Agent Tracker)
================================
监控和追踪 AI Agent 领域的新闻动态，从多信源自动识别 Agent 相关文章。

功能：
1. 从 raw.json 中筛选标题含 Agent 关键词的文章
2. 调用 DeepSeek API 对候选文章进行摘要和分类
3. 生成 data/agent_articles.json 供前端 Agent Tracker 页面渲染

Agent 关键词匹配（不区分大小写）：
- Agent / AI Agent / 智能体
- Agentic / Agentic AI / Agentic Workflow
- Multi-agent / Agent Framework / Agent Platform
- LangChain / AutoGPT / CrewAI / MetaGPT（Agent 框架）

技术栈：
- DeepSeek API (deepseek-chat) 用于智能筛选
- api_client 模块用于幂等 API 调用
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

# ── 项目路径设置 ──
REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

from scripts.pipeline.api_client import call_llm, get_api_key

# ── Agent 关键词列表 ──
# 两阶段筛选：
#   第一阶段（快速）：正则匹配关键词，快速过滤 >90% 不相关文章
#   第二阶段（LLM）：DeepSeek 确认是否为 Agent 领域文章
AGENT_KEYWORDS = [
    r"\bagent\b", r"\bAgent\b", r"\bagents\b", r"\bAgents\b",
    r"\bagentic\b", r"\bAgentic\b",
    r"multi.agent", r"Multi.Agent",
    r"\bLangChain\b", r"\bLangGraph\b",
    r"\bAutoGPT\b", r"\bCrewAI\b",
    r"\bMetaGPT\b", r"\bTaskWeaver\b",
    r"智能体",  # 中文
    r"agent.framework", r"Agent.Framework",
    r"agent.platform", r"Agent.Platform",
    r"\bAutoGen\b",
]


def load_articles() -> list:
    """
    从 raw.json 加载当天所有文章。

    Returns:
        list[dict]: 文章列表。
    """
    raw_path = REPO_DIR.parent / "data" / "raw.json"
    if not raw_path.exists():
        print("❌ raw.json not found — run rss_scanner.py first")
        return []

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("articles", [])


def keyword_filter(articles: list) -> list:
    """
    第一阶段过滤：用正则关键词快速筛选 Agent 相关文章。

    对每篇文章，将 title + summary 拼接后，检查是否匹配任一 Agent 关键词。

    Args:
        articles: 全量文章列表。

    Returns:
        list[dict]: 通过关键词筛选的候选文章。
    """
    candidates = []
    for a in articles:
        text = a.get("title", "") + " " + a.get("summary", "")
        # 遍历关键词列表，任一匹配即可
        for pattern in AGENT_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                candidates.append(a)
                break  # 匹配到一个就停止，避免重复添加

    return candidates


def llm_filter(candidates: list) -> list:
    """
    第二阶段过滤：调用 DeepSeek API 判断文章是否为 Agent 领域。

    使用批量判断 prompt，一次 API 调用处理多篇文章，节省 token。

    Args:
        candidates: 关键词过滤后的候选文章列表。

    Returns:
        list[dict]: 被 LLM 确认为 Agent 领域的文章（附带 AI 摘要）。
    """
    if not candidates:
        return []

    api_key = get_api_key()
    if not api_key:
        print("⚠️  No API key — using keyword-only mode")
        # 无 API key 时：为每篇文章添加默认摘要
        for a in candidates:
            a["agent_summary"] = a.get("summary", "")[:200]
            a["agent_category"] = "Agent News"
        return candidates

    results = []
    # 每次处理最多 10 篇文章（API 上下文窗口限制）
    batch_size = 10
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]

        # 构造判断 prompt
        articles_text = ""
        for j, a in enumerate(batch):
            articles_text += (
                f"[{j+1}] Title: {a.get('title', 'N/A')}\n"
                f"    Summary: {a.get('summary', 'N/A')[:200]}\n\n"
            )

        prompt = f"""你是一个 AI Agent 领域专家。请判断以下文章是否与 AI Agent（智能体）相关。

相关定义：文章讨论 AI Agent、Agentic AI、多智能体系统、Agent 框架、自主决策系统、
Agent 工具使用、Agent 规划/推理等话题。

请为每篇文章输出 JSON 格式：
[
  {{"index": 1, "is_agent": true/false, "summary_cn": "中文摘要（50字以内）", "category": "分类"}},
  ...
]

分类可选：Agent Framework, Agent Research, Agent Application, Agent News

{articles_text}"""

        try:
            resp = call_llm(
                prompt=prompt,
                system_prompt="你是 AI Agent 领域专家。请严格按照 JSON 格式回复，不要添加任何额外内容。",
                max_tokens=2000,
            )

            # 解析 LLM 返回的 JSON
            response_text = resp.get("content", "[]")
            # 提取 JSON 数组（LLM 可能在前后加额外文字）
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                for item in parsed:
                    idx = item.get("index", 0) - 1
                    if 0 <= idx < len(batch) and item.get("is_agent", False):
                        article = batch[idx].copy()
                        article["agent_summary"] = item.get("summary_cn", "")
                        article["agent_category"] = item.get("category", "Agent News")
                        results.append(article)

        except Exception as e:
            print(f"  ⚠️ LLM filter error for batch {i//batch_size + 1}: {e}")
            # 失败回退：将这批全部纳入结果
            for a in batch:
                a.setdefault("agent_summary", a.get("summary", "")[:200])
                a.setdefault("agent_category", "Agent News")
            results.extend(batch)

    return results


def main():
    """
    主函数：加载 → 关键词过滤 → LLM 过滤 → 保存结果。

    Returns:
        int: 0 成功，1 失败。
    """
    print("🤖 AI Agent Tracker\n")

    # Step 1: 加载全量文章
    articles = load_articles()
    if not articles:
        print("No articles to process.")
        return 1

    print(f"📄 {len(articles)} articles loaded")

    # Step 2: 第一阶段 — 关键词快速过滤
    candidates = keyword_filter(articles)
    print(f"🔑 {len(candidates)} candidates after keyword filter")

    # Step 3: 第二阶段 — LLM 深度判断
    agent_articles = llm_filter(candidates)
    print(f"🤖 {len(agent_articles)} confirmed Agent articles via LLM")

    # Step 4: 保存结果
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(articles),
        "candidates": len(candidates),
        "agent_articles": len(agent_articles),
        "articles": agent_articles,
    }

    out_path = REPO_DIR.parent / "data" / "agent_articles.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved to {out_path}")

    # 简要预览
    for a in agent_articles[:5]:
        print(f"  • [{a.get('agent_category', 'N/A')}] {a.get('title', '')}")
        print(f"    {a.get('agent_summary', '')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
