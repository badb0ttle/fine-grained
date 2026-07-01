#!/usr/bin/env python3
"""
阶段5: Publisher — 导出、部署与推送模块。

================================================================================
模块功能
================================================================================
Pipeline 最终阶段：将精选文章和衍生数据导出为静态文件，并推送到生产环境。
  1. export_stats_json:     生成运维仪表盘统计数据（信源健康、评分分布、趋势）
  2. export_search_index:   导出全量文章索引用于前端全文搜索
  3. export_files:          写入 latest.json / stats.json / 历史快照 / 聚类数据等
  4. run:                   主编排函数 — 协调所有导出 + API 同步 + RSS + Sitemap + 健康检查

================================================================================
导出文件清单
================================================================================
data/
  ├── latest.json            # 当日精选文章（前端主数据源）
  ├── stats.json             # 仪表盘统计数据
  ├── leaderboard.json       # 模型排行榜（由 model_tracker 生成）
  ├── trending.json          # GitHub Trending 数据
  ├── search_index.json      # 全文搜索索引
  ├── clusters.json          # 语义聚类可视化数据
  ├── health_alert.txt       # 健康监控告警信息
  └── history/
      └── YYYY-MM-DD.json    # 每日历史快照

docs/data/                   # GitHub Pages 同步副本（与 data/ 保持同步）
"""

import json
from pathlib import Path

from . import REPO_DIR
from .curator import export_latest_json


def export_stats_json() -> dict:
    """
    导出运维仪表盘统计数据。

    包含五个维度的数据:
      1. source_health:      每个信源的健康状态（成功/失败次数、文章数）
      2. score_distribution: 评分分布（按 80-100 / 60-79 / 40-59 / 20-39 / 0-19 分桶）
      3. category_distribution: 文章分类分布
      4. daily_trends:       最近 14 天的每日趋势（来源数、文章数、精选数）
      5. top_articles:       Top-10 最高评分文章

    用途: 前端 dashboard.html 的数据源

    Returns:
        包含上述五个维度的统计字典
    """
    from . import get_db
    conn = get_db()

    # ---- 1. 信源健康状态 ----
    # 按连续失败次数降序排列，优先展示问题信源
    # status 判定: consecutive_failures==0→healthy, 1-3→degraded, ≥4→down
    sources = conn.execute("""
        SELECT name, category, last_success, consecutive_failures,
               article_count_last
        FROM sources
        ORDER BY consecutive_failures DESC, name
    """).fetchall()

    source_health = []
    for s in sources:
        source_health.append({
            "name": s["name"],
            "category": s["category"],
            "last_success": s["last_success"],
            "consecutive_failures": s["consecutive_failures"],
            "article_count_last": s["article_count_last"],
            "status": "healthy" if s["consecutive_failures"] == 0 else
                      ("degraded" if s["consecutive_failures"] <= 3 else "down")
        })

    # ---- 2. 评分分布 (0-100 五个分桶) ----
    # 使用 CASE WHEN 做分桶，前端可据此绘制直方图
    score_rows = conn.execute("""
        SELECT
            CASE
                WHEN score_total >= 80 THEN '80-100'
                WHEN score_total >= 60 THEN '60-79'
                WHEN score_total >= 40 THEN '40-59'
                WHEN score_total >= 20 THEN '20-39'
                ELSE '0-19'
            END as bucket,
            COUNT(*) as cnt
        FROM articles
        WHERE score_total > 0
        GROUP BY bucket
        ORDER BY bucket DESC
    """).fetchall()

    score_distribution = {r["bucket"]: r["cnt"] for r in score_rows}

    # ---- 3. 分类分布 ----
    # 按 category 聚合已评分文章数量
    cat_rows = conn.execute("""
        SELECT category, COUNT(*) as cnt
        FROM articles
        WHERE score_total > 0
        GROUP BY category
        ORDER BY cnt DESC
    """).fetchall()

    category_distribution = {r["category"]: r["cnt"] for r in cat_rows}

    # ---- 4. 最近 14 天趋势 ----
    # 按日期倒序取最近 14 条记录，再反转呈时间升序（方便前端绘制折线图）
    daily_rows = conn.execute("""
        SELECT date, total_sources, successful_sources,
               total_articles, new_articles, curated_count
        FROM daily_stats
        ORDER BY date DESC
        LIMIT 14
    """).fetchall()

    daily_trends = []
    for r in reversed(daily_rows):
        daily_trends.append({
            "date": r["date"],
            "total_sources": r["total_sources"],
            "successful_sources": r["successful_sources"],
            "total_articles": r["total_articles"],
            "new_articles": r["new_articles"],
            "curated_count": r["curated_count"],
        })

    # ---- 5. Top-10 最高分文章 ----
    top_rows = conn.execute("""
        SELECT title, source_name, category, score_total, published
        FROM articles
        WHERE score_total > 0
        ORDER BY score_total DESC
        LIMIT 10
    """).fetchall()

    top_articles = []
    for r in top_rows:
        top_articles.append({
            "title": r["title"],
            "source": r["source_name"],
            "category": r["category"],
            "score": round(r["score_total"], 1),
            "published": r["published"],
        })

    conn.close()

    # 动态导入 trends 模块计算关键词趋势（避免循环导入）
    return {
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "source_health": source_health,
        "score_distribution": score_distribution,
        "category_distribution": category_distribution,
        "daily_trends": daily_trends,
        "top_articles": top_articles,
        "keyword_trends": __import__('scripts.pipeline.trends', fromlist=['compute_trends']).compute_trends(7),
    }


def export_search_index() -> list:
    """
    导出全量文章搜索索引，用于前端客户端全文搜索 (Phase 5)。

    索引包含所有已评分文章的:
      - 标题和摘要（中英文双份）
      - 信源和分类
      - 论文标记和 ID
      - 评分

    注意: 摘要截断到 300 字符以控制 JSON 体积，前端搜索在 title + title_cn + summary + summary_cn 中匹配

    Returns:
        文章字典列表，每项为可序列化的扁平结构
    """
    from . import get_db
    conn = get_db()
    rows = conn.execute("""
        SELECT id, title, title_cn, summary, summary_cn, source_name,
               category, published, link, is_paper, paper_id, score_total
        FROM articles
        WHERE score_total > 0
        ORDER BY published DESC
    """).fetchall()
    conn.close()
    return [{
        "id": r["id"],
        "title": r["title"],
        "title_cn": r["title_cn"],
        "summary": (r["summary"] or "")[:300],
        "summary_cn": (r["summary_cn"] or "")[:300],
        "source": r["source_name"],
        "category": r["category"],
        "published": r["published"],
        "link": r["link"],
        "is_paper": bool(r["is_paper"]),
        "paper_id": r["paper_id"],
        "score": round(r["score_total"], 1) if r["score_total"] else 0,
    } for r in rows]


def export_files(data: dict) -> dict:
    """
    写入所有导出文件并同步到 docs/data/ 目录。

    写入的文件:
      1. data/latest.json            — 当日精选文章
      2. data/stats.json             — 仪表盘统计
      3. data/leaderboard.json       — 模型排行榜（调用 model_tracker）
      4. data/trending.json          — GitHub Trending（调用 github_trending）
      5. data/search_index.json      — 搜索索引
      6. data/clusters.json          — 语义聚类数据
      7. data/history/YYYY-MM-DD.json — 每日历史快照
      8. docs/data/*                 — GitHub Pages 同步副本

    docs/data/ 同步策略:
      - data/ 目录下的所有 .json 文件 → docs/data/
      - data/history/ 目录下的所有 .json 文件 → docs/data/history/
      - data/weekly/ 目录下的所有文件 → docs/data/weekly/
      - 使用 shutil.copy2 保留文件元数据（修改时间等）

    Args:
        data: export_latest_json() 的返回值（精选文章数据）

    Returns:
        { latest: str, history: str } — 主文件和快照文件的路径
    """
    data_dir = REPO_DIR / "data"
    latest_path = data_dir / "latest.json"
    history_dir = data_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    # ---- 写入 latest.json (前端主数据源) ----
    # ensure_ascii=False 保留中文不转义，indent=2 提高可读性
    latest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"💾 latest.json: {len(data['articles'])} articles")

    # ---- 写入 stats.json (仪表盘数据) ----
    stats_data = export_stats_json()
    stats_path = data_dir / "stats.json"
    stats_path.write_text(json.dumps(stats_data, ensure_ascii=False, indent=2))
    print(f"💾 stats.json: dashboard data exported")

    # ---- 写入 leaderboard.json (模型追踪) ----
    leaderboard_data = __import__('scripts.pipeline.model_tracker', fromlist=['export_leaderboard_json']).export_leaderboard_json()
    lb_path = data_dir / "leaderboard.json"
    lb_path.write_text(json.dumps(leaderboard_data, ensure_ascii=False, indent=2))
    print(f"💾 leaderboard.json: {len(leaderboard_data.get('models',[]))} models")

    # ---- 写入 trending.json (GitHub Trending) ----
    trending_data = __import__('scripts.pipeline.github_trending', fromlist=['export_trending_json']).export_trending_json()
    trending_path = data_dir / "trending.json"
    trending_path.write_text(json.dumps(trending_data, ensure_ascii=False, indent=2))
    print(f"💾 trending.json: {trending_data.get('count',0)} repos")

    # ---- 写入 search_index.json (全文搜索索引) ----
    search_data = export_search_index()
    search_path = data_dir / "search_index.json"
    search_path.write_text(json.dumps(search_data, ensure_ascii=False, indent=2))
    print(f"💾 search_index.json: {len(search_data)} articles")

    # ---- 写入 clusters.json (语义聚类可视化) ----
    cluster_data = __import__('scripts.pipeline.cluster_viz', fromlist=['compute_clusters']).compute_clusters()
    cluster_path = data_dir / "clusters.json"
    cluster_path.write_text(json.dumps(cluster_data, ensure_ascii=False, indent=2))
    print(f"💾 clusters.json: {cluster_data.get('total_articles',0)} points, {cluster_data.get('n_clusters',0)} clusters")

    # ---- 写入历史快照 (按日期归档) ----
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    history_path = history_dir / f"{date_str}.json"
    history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"💾 History: {history_path.name}")

    # ---- 同步到 docs/data/ 供 GitHub Pages 使用 ----
    # docs/data/ 是 GitHub Pages 的部署目录，不需要 Node.js 构建
    docs_data = REPO_DIR / "docs" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    (docs_data / "history").mkdir(parents=True, exist_ok=True)
    import shutil
    # 同步所有 .json 文件
    for f in data_dir.glob("*.json"):
        shutil.copy2(f, docs_data / f.name)
    # 同步历史快照
    for f in (data_dir / "history").glob("*.json"):
        shutil.copy2(f, docs_data / "history" / f.name)
    # 同步周报（如果存在）
    for f in (data_dir / "weekly").glob("*"):
        if f.is_file():
            dest = docs_data / "weekly" / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
    print(f"💾 Synced to docs/data/ for GitHub Pages")

    return {"latest": str(latest_path), "history": str(history_path)}


def run() -> dict:
    """
    主编排函数 — 执行完整的发布流程。

    发布流程分为三个阶段:

    【Phase 1: 生成衍生数据】
      - 拉取并导出模型排行榜 (model_leaderboard.fetch_and_export)
      - 导出 top-20 精简版排行榜 (model_leaderboard.export_top_json)
      这些必须在 export_files 之前运行，以确保它们被同步到 docs/data/

    【Phase 2: 导出静态文件】
      - 生成 latest.json（精选文章）
      - 生成 stats.json（仪表盘数据）
      - 调用 export_files 写入所有文件 + 同步 docs/data/

    【Phase 3: API 同步与部署】
      - 向 API 后端 POST 精选文章 (post_batch)
      - 向 API 后端 POST 精选元数据 (post_curation)
      - 生成 RSS feed (rss_feed.generate)
      - 生成 Sitemap (sitemap_gen.generate)
      - 运行健康检查 (health_monitor.check_health)

    Returns:
        包含导出文件路径的字典
    """
    print("📦 Publisher — exporting and deploying...\n")

    # ── Phase 1: 生成所有衍生数据（leaderboard, clusters）──
    # 这些必须在 export_files 之前运行，以便被同步到 docs/data/
    lb = __import__('scripts.pipeline.model_leaderboard', fromlist=['fetch_and_export', 'export_top_json'])
    leaderboard_data = lb.fetch_and_export()
    print(f"    leaderboard: {leaderboard_data['total_models']} models")
    lb.export_top_json(20)
    print(f"    leaderboard top20 exported")

    data = export_latest_json()
    stats = export_stats_json()
    files = export_files(data)

    # ── Phase 3: 同步到 API 后端 ──
    from .api_client import post_batch, post_curation
    from datetime import datetime

    scan_id = f"publish-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    api_result = {"status": "skipped"}

    # POST 精选文章到 API 后端
    curated = data.get("articles", [])
    if curated:
        api_result = post_batch(articles=curated, stats=stats, scan_id=scan_id)
        api_status = api_result.get("status", "error")
        print(f"📡 API batch: {api_status} — {api_result.get('inserted', 0)} inserted, {api_result.get('skipped', 0)} skipped")

        # POST 精选元数据（中文标题/摘要/重要性）
        # 只发送有中文翻译的文章
        curation_items = []
        for a in curated:
            if a.get("title_cn") or a.get("why_it_matters"):
                curation_items.append({
                    "id": a.get("id", 0),
                    "title_cn": a.get("title_cn", ""),
                    "summary_cn": a.get("summary_cn", ""),
                    "why_it_matters": a.get("why_it_matters", ""),
                })
        if curation_items:
            cr = post_curation(curated=curation_items, scan_id=scan_id)
            print(f"📡 API curation: {cr.get('status', 'error')} — {cr.get('curated', 0)} updated")

    # ---- 生成 RSS + Sitemap ----
    # RSS: 供 RSS 阅读器订阅，写入 docs/rss.xml
    import scripts.rss_feed as rf
    import scripts.sitemap_gen as sg
    rss = rf.generate()
    if rss:
        (REPO_DIR / "docs" / "rss.xml").write_text(rss)
        print(f"✅ RSS feed generated")
    sitemap = sg.generate()
    (REPO_DIR / "docs" / "sitemap.xml").write_text(sitemap)
    print(f"✅ Sitemap generated")

    # ---- 健康检查 ----
    # 输出告警信息到 data/health_alert.txt，供运维监控
    import scripts.health_monitor as hm
    health = hm.check_health()
    if health["alerts"]:
        msg = hm.format_alert_message(health)
        (REPO_DIR / "data" / "health_alert.txt").write_text(msg)
        print(f"⚠️  Health: {health['critical']} critical, {len(health['alerts'])} total alerts")
    else:
        print(f"✅ Health: all sources OK")

    return {**files}


if __name__ == "__main__":
    run()
