#!/usr/bin/env python3
"""
阶段5: 语义聚类可视化 — TF-IDF + SVD降维 + KMeans聚类 → 2D散点坐标。

================================================================================
模块功能
================================================================================
为前端交互式文章地图提供数据：将文章文本转换为 2D 坐标和聚类标签。
  1. 从数据库获取所有已评分文章
  2. 构建文本语料（优先中文，回退英文）
  3. TF-IDF 向量化 → SVD 降维到 50D → SVD 再降维到 2D
  4. KMeans 聚类 → 提取每个聚类的代表文章和关键词
  5. 输出 clusters.json 供前端 2D 散点图渲染

================================================================================
核心算法流程
================================================================================
文本预处理:
  - 拼接 title_cn/summary_cn（优先中文）或 title/summary（英文回退）
  - 清洗: HTML 实体解码、arXiv ID 移除、日期/时间移除、常见停用词过滤

TF-IDF 向量化:
  - max_features=3000: 限制特征词数，控制稀疏矩阵规模
  - min_df=3, max_df=0.7: 过滤罕见词（噪声）和超高频词（无区分度）
  - ngram_range=(1,2): 同时使用单词和双词组合
  - token_pattern: 特殊设计的正则，同时匹配英文单词和 CJK 字符

降维 (Two-stage SVD):
  - Stage 1: TF-IDF → 50D（保留主要语义结构）
  - Stage 2: 50D → 2D（用于可视化）
  - 两阶段降维而非一步到位，保留中间维度的语义信息用于 KMeans

KMeans 聚类:
  - n_clusters = min(8, max(3, n_articles // 50)): 动态聚类数，50篇/类
  - 在 50D 语义空间聚类，而非 2D 坐标空间（保留更多信息）

后处理:
  - 坐标归一化到 [0, 1]: 方便前端 Canvas/SVG 渲染
  - 提取聚类关键词: 通过 inverse_transform 将聚类中心映射回 TF-IDF 空间
  - 提取聚类代表文章: 距离聚类中心最近的 article

================================================================================
边界条件
================================================================================
- 文章数 <10: 返回空结果（数据太少无法有效聚类）
- TF-IDF 特征数 <2: 返回空结果（文本多样性不足）
- sklearn ValueError: 捕获并返回空结果（如空文本导致的异常）
"""

import html as _html
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from collections import Counter


def compute_clusters() -> dict:
    """
    计算文章语义聚类和 2D 坐标。

    完整算法流程:
      1. 从 DB 获取所有已评分文章
      2. 文本预处理: 拼接标题+摘要、HTML 清洗、停用词过滤
      3. TF-IDF 向量化: 英文单词 + 中文 CJK 字符
      4. SVD 降维: 高维 TF-IDF → 50D → 2D 坐标
      5. KMeans 聚类: 在 50D 语义空间分组
      6. 后处理: 坐标归一化、提取聚类关键词和代表文章

    Returns:
        {
          generated_at: str (ISO 时间戳),
          total_articles: int,
          n_clusters: int,
          clusters: [{ id, title, keywords, count, color }],
          points: [{ id, title, source, category, published, link, score, x, y, cluster }],
        }
        如果文章数不足或向量化失败，返回 { clusters: [], points: [] }
    """
    from . import get_db
    conn = get_db()

    # ---- 第一步: 获取所有已评分文章 ----
    rows = conn.execute("""
        SELECT id, title, title_cn, summary, summary_cn, source_name,
               category, published, link, score_total
        FROM articles
        WHERE score_total > 0
        ORDER BY published DESC
    """).fetchall()
    conn.close()

    # 数据不足: 少于 10 篇文章无法做有意义的聚类
    if len(rows) < 10:
        return {"clusters": [], "points": []}

    # ---- 第二步: 构建文本语料 + 清洗 ----
    # 优先使用中文标题/摘要，回退到英文原文
    texts = []
    for r in rows:
        t = (r["title_cn"] or r["title"] or "")
        s = (r["summary_cn"] or r["summary"] or "")[:300]  # 截断到 300 字符
        full = (t + " " + s)
        # 清洗管道
        full = _html.unescape(full)                         # HTML 实体解码 (&amp; → &)
        full = re.sub(r'&\w+;', '', full)                   # 移除残留 HTML 实体
        full = re.sub(r'arxiv:\d+\.\d+', '', full, flags=re.IGNORECASE)  # 移除 arXiv ID
        full = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', full)  # 移除日期 (2024-01-15)
        full = re.sub(r'\b\d+:\d+\b', '', full)             # 移除时间 (15:30)
        # 过滤英文常见停用词（高频无意义词会引入噪声）
        full = re.sub(r'\b(at|the|and|for|this|with|that|from|its|can|has|are|was|new|more|also)\b', '', full, flags=re.IGNORECASE)
        full = re.sub(r'\s+', ' ', full).strip()            # 合并多余空白
        texts.append(full)

    # ---- 第三步: TF-IDF 向量化 ----
    # token_pattern: (?u) Unicode模式, \b\w+\b 英文单词, [\u4e00-\u9fff]+ CJK中文字符
    vec = TfidfVectorizer(
        max_features=3000,        # 最多保留 3000 个特征词，控制维度
        min_df=3,                 # 至少在 3 篇文章中出现，过滤罕见词（噪声）
        max_df=0.7,               # 出现在超过 70% 文章中的词忽略（无区分度）
        ngram_range=(1, 2),       # 同时使用 unigrams 和 bigrams（如 "machine learning"）
        stop_words=None,          # 不额外去停用词（已在清洗管道中手动处理）
        token_pattern=r'(?u)\b\w+\b|[\u4e00-\u9fff]+'  # 关键: 同时匹配英文和中文
    )
    try:
        X = vec.fit_transform(texts)  # 稀疏矩阵，shape: (n_articles, n_features)
    except ValueError:
        # 所有文本为空或特征提取失败
        return {"clusters": [], "points": []}

    # 特征数不足: 文本向量维度 <2，无法降维到 2D
    if X.shape[1] < 2:
        return {"clusters": [], "points": []}

    # ---- 第四步: 第一阶段 SVD 降维 (TF-IDF 空间 → 50D) ----
    # 降到 50 维保留主要语义结构，供 KMeans 使用
    n_components = min(50, X.shape[1] - 1, X.shape[0] - 1)  # 不超过特征数或样本数
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    X_reduced = svd.fit_transform(X)  # shape: (n_articles, 50)

    # ---- 第五步: 第二阶段 SVD 降维 (50D → 2D) ----
    # 从 50D 语义空间降到 2D 用于可视化散点图
    svd_2d = TruncatedSVD(n_components=2, random_state=42)
    coords_2d = svd_2d.fit_transform(X_reduced)  # shape: (n_articles, 2)

    # ---- 第六步: 坐标归一化到 [0, 1] ----
    # 归一化使得前端 Canvas/SVG 渲染时坐标落在可见区域内
    for dim in range(2):
        mn, mx = coords_2d[:, dim].min(), coords_2d[:, dim].max()
        if mx > mn:
            coords_2d[:, dim] = (coords_2d[:, dim] - mn) / (mx - mn)

    # ---- 第七步: KMeans 聚类 (在 50D 语义空间) ----
    # 动态聚类数: 每约 50 篇文章一个聚类，最少 3 个，最多 8 个
    # 在 50D 空间聚类而非 2D 空间，因为 50D 保留了更多语义信息
    n_clusters = min(8, max(3, len(rows) // 50))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_reduced)  # 每篇文章的聚类标签
    centers = kmeans.cluster_centers_       # 聚类中心在 50D 空间

    # ---- 第八步: 提取每个聚类的代表文章 ----
    # 代表文章 = 距离聚类中心最近的 article（在 50D 语义空间中）
    cluster_titles = {}
    for i in range(n_clusters):
        mask = labels == i
        if not mask.any():
            continue  # 空聚类（理论上不应出现，但防御性检查）
        cluster_center = centers[i]
        # 计算该聚类中所有文章到聚类中心的欧氏距离
        distances = np.linalg.norm(X_reduced[mask] - cluster_center, axis=1)
        best_idx = np.where(mask)[0][np.argmin(distances)]  # 最近文章的索引
        r = rows[best_idx]
        cluster_titles[int(i)] = (r["title_cn"] or r["title"])[:60]

    # ---- 第九步: 提取每个聚类的 Top-5 TF-IDF 关键词 ----
    # 通过 SVD inverse_transform 将 50D 聚类中心映射回完整 TF-IDF 空间
    cluster_terms = {}
    feature_names = vec.get_feature_names_out()
    centers_tfidf = svd.inverse_transform(centers)  # 50D → 完整 TF-IDF 空间
    for i in range(n_clusters):
        top_idx = np.argsort(centers_tfidf[i])[::-1]  # 按 TF-IDF 值降序
        top_terms = []
        for j in top_idx:
            term = feature_names[j]
            # 过滤无意义术语: 纯数字、单字符、含数字的短字符串
            if term.isdigit() or len(term) <= 1:
                continue
            if any(c.isdigit() for c in term) and len(term) <= 3:
                continue
            top_terms.append(term)
            if len(top_terms) >= 5:  # 每个聚类取 top-5 关键词
                break
        cluster_terms[int(i)] = top_terms

    # ---- 第十步: 构建输出数据结构 ----
    # 聚类大小统计
    cluster_counts = Counter(int(l) for l in labels)

    # 构建 points 数组（每个点对应一篇文章）
    points = []
    for i, r in enumerate(rows):
        points.append({
            "id": r["id"],
            "title": r["title_cn"] or r["title"],
            "source": r["source_name"],
            "category": r["category"],
            "published": r["published"],
            "link": r["link"],
            "score": round(r["score_total"], 1) if r["score_total"] else 0,
            "x": round(float(coords_2d[i, 0]), 4),   # 2D 横坐标 [0,1]
            "y": round(float(coords_2d[i, 1]), 4),   # 2D 纵坐标 [0,1]
            "cluster": int(labels[i]),                # 聚类标签
        })

    # 聚类颜色方案（8 色，覆盖最大聚类数）
    cluster_colors = [
        "#6C5CE7", "#00CEC9", "#00b894", "#f0a050",
        "#74b9ff", "#fd79a8", "#a29bfe", "#55efc4",
    ]

    # 构建 clusters 数组（每个聚类一个元素）
    clusters = []
    for i in range(n_clusters):
        clusters.append({
            "id": i,
            "title": cluster_titles.get(i, ""),           # 代表文章标题
            "keywords": cluster_terms.get(i, []),          # Top-5 TF-IDF 关键词
            "count": cluster_counts.get(i, 0),             # 该聚类的文章数
            "color": cluster_colors[i % len(cluster_colors)],  # 循环使用颜色
        })

    return {
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "total_articles": len(points),
        "n_clusters": n_clusters,
        "clusters": clusters,
        "points": points,
    }


def export_clusters_json() -> dict:
    """
    独立导出版本，供 publisher.py 调用。

    Returns:
        compute_clusters() 的返回值（同上）
    """
    return compute_clusters()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    data = compute_clusters()
    out = __import__('pathlib').Path('data/clusters.json')
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Exported {data['total_articles']} points, {data['n_clusters']} clusters → {out}")
