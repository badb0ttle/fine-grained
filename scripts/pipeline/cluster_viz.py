#!/usr/bin/env python3
"""Phase 5: Topic clustering — TF-IDF + SVD + KMeans → 2D scatter coordinates."""

import html as _html
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from collections import Counter


def compute_clusters() -> dict:
    """Compute article clusters and 2D coordinates. Returns data for frontend."""
    from . import get_db
    conn = get_db()

    rows = conn.execute("""
        SELECT id, title, title_cn, summary, summary_cn, source_name,
               category, published, link, score_total
        FROM articles
        WHERE score_total > 0
        ORDER BY published DESC
    """).fetchall()
    conn.close()

    if len(rows) < 10:
        return {"clusters": [], "points": []}

    # Build text corpus — prefer Chinese, fall back to English
    texts = []
    for r in rows:
        t = (r["title_cn"] or r["title"] or "")
        s = (r["summary_cn"] or r["summary"] or "")[:300]
        # Clean: HTML entities, arXiv IDs, dates, common noise tokens
        full = (t + " " + s)
        full = _html.unescape(full)
        full = re.sub(r'&\w+;', '', full)
        full = re.sub(r'arxiv:\d+\.\d+', '', full, flags=re.IGNORECASE)
        full = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', full)
        full = re.sub(r'\b\d+:\d+\b', '', full)
        full = re.sub(r'\b(at|the|and|for|this|with|that|from|its|can|has|are|was|new|more|also)\b', '', full, flags=re.IGNORECASE)
        full = re.sub(r'\s+', ' ', full).strip()
        texts.append(full)

    # TF-IDF vectorization — use token_pattern that allows CJK characters
    vec = TfidfVectorizer(
        max_features=3000, min_df=3, max_df=0.7,
        ngram_range=(1, 2), stop_words=None,
        token_pattern=r'(?u)\b\w+\b|[\u4e00-\u9fff]+'
    )
    try:
        X = vec.fit_transform(texts)
    except ValueError:
        return {"clusters": [], "points": []}

    if X.shape[1] < 2:
        return {"clusters": [], "points": []}

    # Reduce to 50D with SVD
    n_components = min(50, X.shape[1] - 1, X.shape[0] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    X_reduced = svd.fit_transform(X)

    # Reduce to 2D for display
    svd_2d = TruncatedSVD(n_components=2, random_state=42)
    coords_2d = svd_2d.fit_transform(X_reduced)

    # Normalize to [0, 1] range
    for dim in range(2):
        mn, mx = coords_2d[:, dim].min(), coords_2d[:, dim].max()
        if mx > mn:
            coords_2d[:, dim] = (coords_2d[:, dim] - mn) / (mx - mn)

    # KMeans clustering
    n_clusters = min(8, max(3, len(rows) // 50))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_reduced)
    centers = kmeans.cluster_centers_

    # Get representative titles per cluster (closest to centroid)
    cluster_titles = {}
    for i in range(n_clusters):
        mask = labels == i
        if not mask.any():
            continue
        cluster_center = centers[i]
        # Find article closest to cluster center
        distances = np.linalg.norm(X_reduced[mask] - cluster_center, axis=1)
        best_idx = np.where(mask)[0][np.argmin(distances)]
        r = rows[best_idx]
        cluster_titles[int(i)] = (r["title_cn"] or r["title"])[:60]

    # Also get top TF-IDF terms (cleaned) — must inverse_transform from SVD space
    cluster_terms = {}
    feature_names = vec.get_feature_names_out()
    centers_tfidf = svd.inverse_transform(centers)  # 50D → full TF-IDF space
    for i in range(n_clusters):
        top_idx = np.argsort(centers_tfidf[i])[::-1]
        top_terms = []
        for j in top_idx:
            term = feature_names[j]
            # Skip pure numbers, dates, very short terms
            if term.isdigit() or len(term) <= 1:
                continue
            if any(c.isdigit() for c in term) and len(term) <= 3:
                continue
            top_terms.append(term)
            if len(top_terms) >= 5:
                break
        cluster_terms[int(i)] = top_terms

    # Cluster sizes
    cluster_counts = Counter(int(l) for l in labels)

    # Build points
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
            "x": round(float(coords_2d[i, 0]), 4),
            "y": round(float(coords_2d[i, 1]), 4),
            "cluster": int(labels[i]),
        })

    # Cluster colors
    cluster_colors = [
        "#6C5CE7", "#00CEC9", "#00b894", "#f0a050",
        "#74b9ff", "#fd79a8", "#a29bfe", "#55efc4",
    ]

    clusters = []
    for i in range(n_clusters):
        clusters.append({
            "id": i,
            "title": cluster_titles.get(i, ""),
            "keywords": cluster_terms.get(i, []),
            "count": cluster_counts.get(i, 0),
            "color": cluster_colors[i % len(cluster_colors)],
        })

    return {
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "total_articles": len(points),
        "n_clusters": n_clusters,
        "clusters": clusters,
        "points": points,
    }


def export_clusters_json() -> dict:
    """Standalone export, usable from publisher."""
    return compute_clusters()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    data = compute_clusters()
    out = __import__('pathlib').Path('data/clusters.json')
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Exported {data['total_articles']} points, {data['n_clusters']} clusters → {out}")
