#!/usr/bin/env python3
"""Model Leaderboard — fetch from OpenRouter API, export ranked JSON."""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = REPO_DIR / "data" / "model_leaderboard.json"
API_URL = "https://openrouter.ai/api/v1/models"

# Map model ID prefix → friendly provider name
PROVIDER_MAP = {
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google",
    "meta-llama": "Meta", "mistralai": "Mistral AI", "mistral": "Mistral AI",
    "deepseek": "DeepSeek", "qwen": "Alibaba", "alibaba": "Alibaba",
    "01-ai": "01.AI", "x-ai": "xAI", "nvidia": "NVIDIA",
    "moonshotai": "Moonshot AI", "cohere": "Cohere", "amazon": "Amazon",
    "microsoft": "Microsoft", "ai21": "AI21 Labs", "minimax": "MiniMax",
    "stepfun": "StepFun", "zhipuai": "Zhipu AI", "baichuan": "Baichuan",
    "bytedance": "ByteDance", "nex-agi": "Nex AGI", "liquid": "Liquid AI",
    "sao10k": "Sao10K", "nousresearch": "Nous Research", "perplexity": "Perplexity",
    "phind": "Phind", "recursal": "Recursal", "targon": "Targon",
    "featherless": "Featherless", "infermatic": "Infermatic", "kluster": "Kluster",
    "hyperbolic": "Hyperbolic", "together": "Together AI", "fireworks": "Fireworks",
    "groq": "Groq", "cerebras": "Cerebras", "sambanova": "SambaNova", "z-ai": "Z.ai",
}


def extract_provider(model_id: str) -> str:
    clean = model_id.lstrip("~")
    if "/" in clean:
        prefix = clean.split("/")[0].lower()
    else:
        prefix = clean.lower()
    return PROVIDER_MAP.get(prefix, prefix.replace("-", " ").title())


def should_include(model: dict) -> bool:
    mid = model["id"]
    if mid.startswith("~"):
        return False
    if ":free" in mid or ":beta" in mid or ":experimental" in mid:
        return False
    pricing = model.get("pricing", {})
    if not pricing.get("prompt") or float(pricing["prompt"]) == 0:
        return False
    if model.get("context_length", 0) < 2048:
        return False
    skip_patterns = ["test", "demo", "deprecated", "debug", "echo"]
    if any(p in mid.lower() for p in skip_patterns):
        return False
    return True


def format_price(price_str: str) -> str:
    try:
        p = float(price_str) * 1_000_000
        if p < 0.01: return f"${p:.3f}"
        elif p < 1: return f"${p:.2f}"
        else: return f"${p:.1f}"
    except (ValueError, TypeError):
        return "?"


def format_context(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    elif n >= 1_000: return f"{n//1_000}K"
    return str(n)


def get_tags(model: dict) -> list[str]:
    tags = []
    arch = model.get("architecture", {})
    modality = arch.get("modality", "")
    if "image" in modality: tags.append("vision")
    if "video" in modality: tags.append("video")
    if "audio" in modality: tags.append("audio")
    if "file" in modality: tags.append("file")
    if model.get("context_length", 0) >= 1_000_000: tags.append("1M+ctx")
    tp = model.get("top_provider", {})
    if tp.get("is_moderated"): tags.append("moderated")
    return tags


def extract_scores(model: dict) -> dict | None:
    """Extract benchmark scores from OpenRouter model data.

    Returns dict with:
      - intelligence: 0-100 (Artificial Analysis)
      - coding: 0-100
      - agentic: 0-100
      - best_elo: max ELO from Design Arena
      - best_elo_category: which category got the best ELO
      - elo_categories: list of {category, elo, win_rate, rank}
    Returns None if no benchmarks available.
    """
    benchmarks = model.get("benchmarks", {})
    if not benchmarks:
        return None

    scores = {}

    # Artificial Analysis: numeric indices 0-100
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

    # Design Arena: ELO scores per category
    da = benchmarks.get("design_arena", [])
    if isinstance(da, list) and da:
        best = max(da, key=lambda e: e.get("elo", 0) if isinstance(e, dict) else 0)
        if isinstance(best, dict) and "elo" in best:
            scores["best_elo"] = best["elo"]
            scores["best_elo_category"] = best.get("category", "?")
            scores["elo_categories"] = [
                {"category": e.get("category", "?"), "elo": e.get("elo"),
                 "win_rate": e.get("win_rate"), "rank": e.get("rank")}
                for e in da if isinstance(e, dict) and e.get("elo")
            ]
            scores["elo_categories"].sort(key=lambda x: -(x["elo"] or 0))

    return scores if scores else None


def fetch_and_export() -> dict:
    print("[Leaderboard] Fetching from OpenRouter API...")
    req = urllib.request.Request(API_URL, headers={"User-Agent": "AllOfAI/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())

    all_models = data.get("data", [])
    print(f"  Raw: {len(all_models)} models")

    filtered = [m for m in all_models if should_include(m)]
    print(f"  After filter: {len(filtered)} models")

    # Stats
    with_scores = 0

    entries = []
    for m in filtered:
        pricing = m.get("pricing", {})
        tp = m.get("top_provider", {})
        max_out = tp.get("max_completion_tokens") if tp else None
        scores = extract_scores(m)
        if scores:
            with_scores += 1

        entry = {
            "id": m["id"],
            "name": m.get("name", m["id"]),
            "provider": extract_provider(m["id"]),
            "description": (m.get("description", "") or "")[:200],
            "created": m.get("created"),
            "context_length": m.get("context_length"),
            "context_display": format_context(m.get("context_length", 0)),
            "max_output": format_context(max_out) if max_out else None,
            "max_output_raw": max_out,
            "price_input": format_price(pricing.get("prompt", "0")),
            "price_output": format_price(pricing.get("completion", "0")),
            "price_input_raw": float(pricing.get("prompt", 0)),
            "price_output_raw": float(pricing.get("completion", 0)),
            "tags": get_tags(m),
            "modality": m.get("architecture", {}).get("modality", "text"),
            "knowledge_cutoff": m.get("knowledge_cutoff"),
            "scores": scores,
        }
        entries.append(entry)

    # Sort by benchmark strength: scored models first, then by best_elo → intelligence → coding
    entries.sort(key=lambda e: (
        e.get("scores") is not None,                                              # scored first
        e["scores"].get("best_elo", 0) if e.get("scores") else 0,                 # ELO (Design Arena)
        e["scores"].get("intelligence", 0) if e.get("scores") else 0,             # AA intelligence
        e["scores"].get("coding", 0) if e.get("scores") else 0,                   # AA coding
        e.get("created", 0),                                                      # tiebreaker: newest
    ), reverse=True)
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_models": len(entries),
        "source": "OpenRouter API",
        "models": entries,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"  Exported: {OUTPUT_FILE} ({len(entries)} models, {with_scores} with scores)")

    # Quick stats
    providers = {}
    for e in entries:
        p = e["provider"]
        providers[p] = providers.get(p, 0) + 1
    top_providers = sorted(providers.items(), key=lambda x: -x[1])[:10]
    print(f"  Top providers: {', '.join(f'{p}({c})' for p,c in top_providers)}")

    return result


if __name__ == "__main__":
    result = fetch_and_export()
    # Show top with scores
    scored = [m for m in result["models"] if m.get("scores")]
    print(f"\nTop 5 (with scores):")
    for m in scored[:5]:
        s = m["scores"]
        parts = [f"int={s.get('intelligence','?')}", f"code={s.get('coding','?')}", f"agent={s.get('agentic','?')}"]
        if s.get("best_elo"):
            parts.append(f"ELO={s['best_elo']}({s.get('best_elo_category','?')})")
        print(f"  #{m['rank']} {m['name']} — {', '.join(parts)}")


def export_top_json(top_n: int = 20) -> dict:
    """Export a streamlined top-N leaderboard for weekly/detail pages.
    
    Only includes fields the weekly detail sidebar needs (name, provider, scores),
    keeping the payload under ~5KB instead of the full ~200KB leaderboard.
    """
    path = REPO_DIR / "data" / "model_leaderboard.json"
    if not path.exists():
        fetch_and_export()
    
    data = json.loads(path.read_text())
    all_models = data.get("models", [])
    
    # Pick top scored models (already sorted by rank)
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
        "source": "OpenRouter API (top {} by benchmark)".format(top_n),
        "models": top,
    }
    
    top_path = REPO_DIR / "data" / "model_leaderboard_top.json"
    top_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"[Leaderboard] Exported top {len(top)} to {top_path}")
    return result
