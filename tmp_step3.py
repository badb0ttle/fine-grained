import json

curated = [
    {
        "id": 1459,
        "title_cn": "Transformer 深层 Value 向量可脱离上下文？",
        "summary_cn": "研究者发现 Transformer 深层注意力中的 value 向量对残差流上下文的依赖明显弱于浅层，这一发现挑战了注意力层必须依赖上下文的传统认知，为简化深层计算、降低推理开销提供了理论基础。",
        "why_it_matters": "深入理解注意力机制可指导 LLM 架构简化，降低推理成本"
    },
    {
        "id": 1484,
        "title_cn": "自动化肿瘤 VQA：3D 医学影像评估新基准",
        "summary_cn": "提出自动化 Agent pipeline 从临床报告生成肿瘤学 VQA 基准，解决了医学影像评估数据稀缺、人工标注昂贵且易泄露的问题，为 VLM 在 3D 医学影像上的评测提供了可扩展方案。",
        "why_it_matters": "自动化 benchmark 生成是医学 AI 迈向临床落地的关键一步"
    },
    {
        "id": 59,
        "title_cn": "蒸馏 LLM 反馈提升 Lean 定理证明",
        "summary_cn": "在 Lean 定理证明任务中，用 LLM 生成反馈信号蒸馏为小模型训练数据，替代传统基于可验证奖励的强化学习，在保持证明质量的同时大幅提升训练效率，为数学推理模型训练开辟新路径。",
        "why_it_matters": "LLM 反馈蒸馏为数学推理模型的高效训练提供可行方案"
    },
    {
        "id": 1461,
        "title_cn": "FOLIO+MALLS 标注审计：LLM 辅助修复逻辑基准",
        "summary_cn": "首次系统性审计两个主流 NL-to-FOL 数据集的标注质量，发现大量错误标注。提出 LLM 辅助框架聚焦人工重标注，显著提升逻辑推理 benchmark 的可靠性，对神经符号 AI 研究有重要意义。",
        "why_it_matters": "基础 benchmark 的标注质量直接决定 AI 逻辑推理研究的可信度"
    },
    {
        "id": 632,
        "title_cn": "CardioLens：揭示多模态大模型临床真实差距",
        "summary_cn": "通过多序列心脏 MRI 评估发现当前多模态大模型在公开医学 benchmark 上的高分存在虚高，在真实临床场景下准确率大幅下降，暴露了从 benchmark 到 clinical deployment 的巨大鸿沟。",
        "why_it_matters": "临床部署前的真实场景验证至关重要，benchmark 高分不等于可用"
    },
    {
        "id": 620,
        "title_cn": "显式建模数据流形几何的图像扩散生成",
        "summary_cn": "提出显式建模数据流形几何结构的扩散模型新方法，通过理解数据在低维流形上的分布特征改进生成质量，克服现有扩散模型对流形结构学习不足的根本限制。",
        "why_it_matters": "从流形几何角度理解生成模型，有望提升图像生成的真实性"
    },
    {
        "id": 1434,
        "title_cn": "ToolGate：VLM Agent 工具调用预筛选",
        "summary_cn": "提出 ToolGate 机制，在多模态 Agent 执行工具调用前判断是否必要，跳过不必要的 OCR、检测等调用，以极低计算开销减少无效工具调用，显著降低 Agent 运行 token 消耗。",
        "why_it_matters": "工具调用预筛选是降低 AI Agent 运行成本的关键优化"
    },
    {
        "id": 1447,
        "title_cn": "量化 LLM 的幻觉信号可在中间层线性解码",
        "summary_cn": "在三款 7B-8B 开源模型（Llama-3.1、Mistral、Qwen2.5）4-bit 量化版本中发现：LLM 的幻觉倾向在中间层隐藏状态中存在线性可分离信号，可在生成前通过简单线性探针检测。",
        "why_it_matters": "幻觉检测可在输出前完成，为安全部署 LLM 提供低成本方案"
    },
    {
        "id": 597,
        "title_cn": "CSRP：思维链+强化学习的中文纠错新范式",
        "summary_cn": "将思维链推理与效率感知奖励的强化学习结合用于中文语法纠错，解决通用大模型缺乏专用纠错知识和传统系统依赖大量标注数据的问题，在 CGEC 任务上取得 SOTA 效果。",
        "why_it_matters": "CoT+RL 组合为中文 NLP 任务提供了高效的微调范式"
    },
    {
        "id": 1444,
        "title_cn": "几何感知表格扩散模型",
        "summary_cn": "引入列间 pairwise 角度和长度作为几何先验注入表格扩散模型的去噪过程，使其显式建模列依赖关系，克服传统方法依赖隐式学习列间联系的局限，在隐私保护的表格数据合成任务中取得突破。",
        "why_it_matters": "几何先验注入扩散模型可提升隐私保护表格数据合成质量"
    }
]

with open('data/curated.json', 'w') as f:
    json.dump(curated, f, ensure_ascii=False, indent=2)

print(f"Curated {len(curated)} articles to data/curated.json")
