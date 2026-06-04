import json, sys
sys.path.insert(0, '/Users/mac/Desktop/Projects/ai-intel')
from scripts.pipeline.model_tracker import apply_models

models = [
    {
        "name": "MiniMax-M3",
        "provider": "MiniMax",
        "benchmarks": [
            {"name": "Key Benchmarks (vs GPT-5.5)", "score": "超越"},
            {"name": "Key Benchmarks (vs Gemini 3.1 Pro)", "score": "超越"}
        ],
        "parameters": "未知",
        "context_window": "1M tokens",
        "description": "前沿编码和Agent能力，原生多模态，定价$20/月，综合性能超越GPT-5.5和Gemini 3.1 Pro，成本仅为竞品的5-10%"
    },
    {
        "name": "GPT-5.5",
        "provider": "OpenAI",
        "benchmarks": [
            {"name": "被MiniMax-M3超越", "score": "见MiniMax-M3"}
        ],
        "parameters": "未知",
        "context_window": "未知"
    },
    {
        "name": "Gemini 3.1 Pro",
        "provider": "Google",
        "benchmarks": [
            {"name": "被MiniMax-M3超越", "score": "见MiniMax-M3"}
        ],
        "parameters": "未知",
        "context_window": "未知"
    },
    {
        "name": "Llama-3.1-8B",
        "provider": "Meta",
        "benchmarks": [
            {"name": "4-bit NF4量化幻觉检测", "score": "线性可解码"}
        ],
        "parameters": "8B",
        "context_window": "未知"
    },
    {
        "name": "Mistral-7B",
        "provider": "Mistral",
        "benchmarks": [
            {"name": "4-bit NF4量化幻觉检测", "score": "线性可解码"}
        ],
        "parameters": "7B",
        "context_window": "未知"
    },
    {
        "name": "Qwen2.5-7B",
        "provider": "Alibaba",
        "benchmarks": [
            {"name": "4-bit NF4量化幻觉检测", "score": "线性可解码"}
        ],
        "parameters": "7B",
        "context_window": "未知"
    }
]

with open('data/model_extraction_results.json', 'w') as f:
    json.dump(models, f, ensure_ascii=False, indent=2)

result = apply_models(models)
print(f"Model extraction applied: {result}")
