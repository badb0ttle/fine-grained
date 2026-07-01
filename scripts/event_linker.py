#!/usr/bin/env python3
"""
事件关联引擎 (Event Linker)
============================
基于语义相似度发现文章之间的关联关系，构建事件-文章网络。

核心算法：
- 使用 sentence-transformers/all-MiniLM-L6-v2 对文章标题+摘要编码为向量
- 余弦相似度配对计算（阈值 > 0.75 认为相关）
- 相似文章分组为事件簇（连通分量算法）
- 输出到 data/event_links.json（供前端可视化）

适用场景：
- Timeline 视图的事件时间线
- Cluster 视图的文章聚类
- 知识图谱的关系边
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

REPO_DIR = Path(__file__).resolve().parent


def load_articles() -> list:
    """
    从 raw.json 加载所有文章。

    Returns:
        list[dict]: 文章列表，含 title, summary, link 等字段。
    """
    raw_path = REPO_DIR.parent / "data" / "raw.json"
    if not raw_path.exists():
        print("❌ raw.json not found — run rss_scanner.py first")
        return []

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("articles", [])


def build_embeddings(articles: list, model) -> np.ndarray:
    """
    使用预训练的 sentence-transformer 模型编码文章文本。

    每条文章编码内容：title + summary（截断至模型 max_seq_length）

    Args:
        articles: 文章列表。
        model: sentence-transformers 模型实例。

    Returns:
        np.ndarray: (N, 384) 的归一化向量矩阵（all-MiniLM-L6-v2 输出维度 384）。
    """
    # 构造输入文本：标题 + 摘要（截断）
    texts = []
    for a in articles:
        text = a.get("title", "") + " " + a.get("summary", "")
        texts.append(text[:512])  # MiniLM 最大上下文窗口为 512 tokens 的近似

    # 批量编码（show_progress_bar 在 cron 环境输出到 stderr）
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,  # 归一化后余弦相似度 = 内积
        show_progress_bar=False,
    )
    return embeddings


def compute_links(articles: list, embeddings: np.ndarray, threshold: float = 0.75) -> list:
    """
    计算文章间的相似度并生成关联边。

    算法：
    - 计算 N×N 余弦相似度矩阵
    - 取上三角（避免重复 + 忽略自环）
    - 筛选相似度 > threshold 的配对
    - 按相似度降序排序

    Args:
        articles: 文章列表。
        embeddings: (N, 384) 归一化向量矩阵。
        threshold: 相似度阈值（0.75 实测过滤掉弱关联）。

    Returns:
        list[dict]: 关联边列表，每条含 source, target (文章标题), score。
    """
    # 余弦相似度矩阵（归一化后等价于内积）
    sim_matrix = cosine_similarity(embeddings)

    links = []
    n = len(articles)

    for i in range(n):
        for j in range(i + 1, n):  # 只遍历上三角
            score = float(sim_matrix[i][j])
            if score > threshold:
                links.append({
                    "source": articles[i].get("title", ""),
                    "source_link": articles[i].get("link", ""),
                    "target": articles[j].get("title", ""),
                    "target_link": articles[j].get("link", ""),
                    "score": round(score, 4),
                })

    # 按相似度降序（最相关的排前面）
    links.sort(key=lambda x: x["score"], reverse=True)

    return links


def build_event_groups(links: list) -> list:
    """
    基于相似边构建事件簇（连通分量）。

    使用并查集(Union-Find)算法：
    - 每篇文章初始为独立集合
    - 遍历相似边，merge 相关联的文章集合
    - 最终输出每个簇的文章标题列表

    Args:
        links: compute_links() 输出的关联边列表。

    Returns:
        list[dict]: 事件簇列表，每个含 event_id, articles, article_count。
    """
    # 收集所有不重复的文章标题
    all_titles = set()
    for link in links:
        all_titles.add(link["source"])
        all_titles.add(link["target"])
    title_list = list(all_titles)

    # 并查集：建立标题到索引的映射
    idx_map = {t: i for i, t in enumerate(title_list)}
    parent = list(range(len(title_list)))  # parent[i] = 集合的代表元素

    def find(x):
        """并查集 find：带路径压缩。"""
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        """并查集 union：合并两个集合。"""
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # 根据关联边合并集合
    for link in links:
        i = idx_map.get(link["source"])
        j = idx_map.get(link["target"])
        if i is not None and j is not None:
            union(i, j)

    # 按代表元素分组
    groups = {}
    for title, idx in idx_map.items():
        root = find(idx)
        if root not in groups:
            groups[root] = []
        groups[root].append(title)

    # 构造事件簇输出（过滤掉单篇文章 = 无关联）
    events = []
    for eid, (root, titles) in enumerate(groups.items(), 1):
        if len(titles) >= 2:  # 至少两篇才算事件
            events.append({
                "event_id": f"event_{eid:03d}",
                "articles": titles,
                "article_count": len(titles),
            })

    # 按文章数降序（大事件在前）
    events.sort(key=lambda x: x["article_count"], reverse=True)

    return events


def main():
    """
    主函数：加载文章 → 编码 → 计算关联 → 聚类 → 保存结果。

    Returns:
        int: 0 成功，1 失败。
    """
    print("🔗 AI Intel Event Linker\n")

    # Step 1: 加载文章
    articles = load_articles()
    if not articles:
        print("No articles to link.")
        return 1

    print(f"📄 {len(articles)} articles loaded")

    # Step 2: 延迟加载模型（避免不必要时消耗内存）
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        print("❌ Install sentence-transformers: pip install sentence-transformers")
        return 1

    # Step 3: 编码 + 计算相似度
    print("🧠 Encoding articles...")
    embeddings = build_embeddings(articles, model)

    print("🔍 Computing similarity links...")
    links = compute_links(articles, embeddings)
    print(f"   → {len(links)} links found (threshold=0.75)")

    # Step 4: 事件聚类
    print("📊 Building event groups...")
    events = build_event_groups(links)
    print(f"   → {len(events)} event groups")

    # Step 5: 保存关联数据
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_articles": len(articles),
        "total_links": len(links),
        "total_events": len(events),
        "links": links,
        "events": events,
    }

    out_path = REPO_DIR.parent / "data" / "event_links.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved to {out_path}")

    # 打印 Top 5 事件
    print("\n📌 Top Events:")
    for ev in events[:5]:
        print(f"  {ev['event_id']}: {ev['article_count']} articles")
        for t in ev["articles"][:3]:
            print(f"    - {t}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
