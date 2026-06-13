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
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "meta-llama": "Meta",
    "mistralai": "Mistral AI",
    "mistral": "Mistral AI",
    "deepseek": "DeepSeek",
    "qwen": "Alibaba",
    "alibaba": "Alibaba",
    "01-ai": "01.AI",
    "x-ai": "xAI",
    "nvidia": "NVIDIA",
    "moonshotai": "Moonshot AI",
    "cohere": "Cohere",
    "amazon": "Amazon",
    "microsoft": "Microsoft",
    "ai21": "AI21 Labs",
    "minimax": "MiniMax",
    "stepfun": "StepFun",
    "zhipuai": "Zhipu AI",
    "baichuan": "Baichuan",
    "bytedance": "ByteDance",
    "nex-agi": "Nex AGI",
    "liquid": "Liquid AI",
    "sao10k": "Sao10K",
    "nousresearch": "Nous Research",
    "perplexity": "Perplexity",
    "phind": "Phind",
    "recursal": "Recursal",
    "targon": "Targon",
    "featherless": "Featherless",
    "infermatic": "Infermatic",
    "kluster": "Kluster",
    "hyperbolic": "Hyperbolic",
    "together": "Together AI",
    "fireworks": "Fireworks",
    "groq": "Groq",
    "cerebras": "Cerebras",
    "sambanova": "SambaNova",
    "z-ai": "Z.ai",
}


def extract_provider(model_id: str) -> str:
    """Extract friendly provider name from model ID."""
    # Remove leading ~ (private), trailing :free/:beta etc.
    clean = model_id.lstrip("~")
    if "/" in clean:
        prefix = clean.split("/")[0].lower()
    else:
        prefix = clean.lower()
    return PROVIDER_MAP.get(prefix, prefix.replace("-", " ").title())


def should_include(model: dict) -> bool:
    """Filter out deprecated, test, and very niche models."""
    mid = model["id"]
    name = model.get("name", "")

    # Skip private betas (~ prefix)
    if mid.startswith("~"):
        return False
    # Skip free/test variants (:free, :beta, :experimental)
    if ":free" in mid or ":beta" in mid or ":experimental" in mid:
        return False
    # Skip if no pricing
    pricing = model.get("pricing", {})
    if not pricing.get("prompt") or float(pricing["prompt"]) == 0:
        return False
    # Skip tiny/specialized models (context < 2048)
    if model.get("context_length", 0) < 2048:
        return False
    # Skip specific test/demo patterns
    skip_patterns = ["test", "demo", "deprecated", "debug", "echo"]
    if any(p in mid.lower() for p in skip_patterns):
        return False

    return True


def format_price(price_str: str) -> str:
    """Convert per-token price to $/1M tokens. e.g. '0.00000095' → '$0.95'"""
    try:
        p = float(price_str) * 1_000_000
        if p < 0.01:
            return f"${p:.3f}"
        elif p < 1:
            return f"${p:.2f}"
        else:
            return f"${p:.1f}"
    except (ValueError, TypeError):
        return "?"


def format_context(n: int) -> str:
    """Format context length to human readable."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n//1_000}K"
    return str(n)


def get_tags(model: dict) -> list[str]:
    """Extract capability tags from model data."""
    tags = []
    arch = model.get("architecture", {})
    modality = arch.get("modality", "")

    if "image" in modality:
        tags.append("vision")
    if "video" in modality:
        tags.append("video")
    if "audio" in modality:
        tags.append("audio")
    if "file" in modality:
        tags.append("file")

    ctx = model.get("context_length", 0)
    if ctx >= 1_000_000:
        tags.append("1M+ctx")

    tp = model.get("top_provider", {})
    if tp.get("is_moderated"):
        tags.append("moderated")

    return tags


def fetch_and_export() -> dict:
    """Fetch OpenRouter models, filter, rank, export to JSON."""
    print("[Leaderboard] Fetching from OpenRouter API...")
    req = urllib.request.Request(API_URL, headers={"User-Agent": "AllOfAI/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())

    all_models = data.get("data", [])
    print(f"  Raw: {len(all_models)} models")

    # Filter
    filtered = [m for m in all_models if should_include(m)]
    print(f"  After filter: {len(filtered)} models")

    # Build leaderboard entries
    entries = []
    for m in filtered:
        pricing = m.get("pricing", {})
        tp = m.get("top_provider", {})
        max_out = tp.get("max_completion_tokens") if tp else None

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
        }
        entries.append(entry)

    # Sort by created (newest first)
    entries.sort(key=lambda e: e.get("created", 0), reverse=True)

    # Add rank
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_models": len(entries),
        "source": "OpenRouter API",
        "models": entries,
    }

    # Write JSON
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"  Exported: {OUTPUT_FILE} ({len(entries)} models)")

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
    print(f"\nTop 5:")
    for m in result["models"][:5]:
        print(f"  #{m['rank']} {m['name']}")
        print(f"     {m['provider']} | ctx={m['context_display']} | "
              f"{m['price_input']}/M in, {m['price_output']}/M out | "
              f"tags={m['tags']}")
