#!/usr/bin/env python3
"""Stage 5: Publisher — export JSON, commit, push to GitHub Pages."""

import json
import subprocess
import sys
from pathlib import Path

from . import REPO_DIR
from .curator import export_latest_json


def export_stats_json() -> dict:
    """Export dashboard stats (source health, score distribution, daily trends)."""
    from . import get_db
    conn = get_db()

    # Source health
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

    # Score distribution
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

    # Category distribution
    cat_rows = conn.execute("""
        SELECT category, COUNT(*) as cnt
        FROM articles
        WHERE score_total > 0
        GROUP BY category
        ORDER BY cnt DESC
    """).fetchall()

    category_distribution = {r["category"]: r["cnt"] for r in cat_rows}

    # Daily trends (last 14 days)
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

    # Top scored articles
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

    return {
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "source_health": source_health,
        "score_distribution": score_distribution,
        "category_distribution": category_distribution,
        "daily_trends": daily_trends,
        "top_articles": top_articles,
        "keyword_trends": __import__('scripts.pipeline.trends', fromlist=['compute_trends']).compute_trends(7),
    }


def export_files(data: dict) -> dict:
    """Write latest.json and history snapshot."""
    data_dir = REPO_DIR / "data"
    latest_path = data_dir / "latest.json"
    history_dir = data_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    # Write latest.json
    latest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"💾 latest.json: {len(data['articles'])} articles")

    # Write stats.json for dashboard
    stats_data = export_stats_json()
    stats_path = data_dir / "stats.json"
    stats_path.write_text(json.dumps(stats_data, ensure_ascii=False, indent=2))
    print(f"💾 stats.json: dashboard data exported")

    # Write leaderboard.json for model tracker
    leaderboard_data = __import__('scripts.pipeline.model_tracker', fromlist=['export_leaderboard_json']).export_leaderboard_json()
    lb_path = data_dir / "leaderboard.json"
    lb_path.write_text(json.dumps(leaderboard_data, ensure_ascii=False, indent=2))
    print(f"💾 leaderboard.json: {len(leaderboard_data.get('models',[]))} models")

    # Write trending.json for GitHub Trending
    trending_data = __import__('scripts.pipeline.github_trending', fromlist=['export_trending_json']).export_trending_json()
    trending_path = data_dir / "trending.json"
    trending_path.write_text(json.dumps(trending_data, ensure_ascii=False, indent=2))
    print(f"💾 trending.json: {trending_data.get('count',0)} repos")

    # Write history snapshot
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    history_path = history_dir / f"{date_str}.json"
    history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"💾 History: {history_path.name}")

    return {"latest": str(latest_path), "history": str(history_path)}


def git_push() -> dict:
    """Commit and push to GitHub Pages."""
    token_file = REPO_DIR / ".git_token"
    if not token_file.exists():
        print("⚠️  .git_token not found — skipping git push")
        return {"pushed": False, "reason": "no token"}

    token = token_file.read_text().strip()
    branch = "main"

    def run(cmd, check=True):
        result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"  ⚠️  {' '.join(cmd)}: {result.stderr.strip()[:200]}")
        return result

    print("\n📤 Publishing to GitHub Pages...")

    # Pull first
    run(["git", "pull", "origin", branch, "--rebase"], check=False)

    # Stage
    run(["git", "add", "data/latest.json", "data/stats.json", "data/leaderboard.json", "data/trending.json", "data/history/", "data/ai_intel.db"], check=False)

    # Check if anything to commit
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_DIR, capture_output=True, text=True
    )
    if not status.stdout.strip():
        print("   Nothing to commit — already up to date")
        return {"pushed": False, "reason": "no changes"}

    # Commit
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    run(["git", "commit", "-m", f"📡 AI intel scan + curated — {date_str}"])

    # Push
    push_url = f"https://oauth2:{token}@github.com/badb0ttle/fine-grained.git"
    result = subprocess.run(
        ["git", "push", push_url, branch],
        cwd=REPO_DIR, capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ Pushed! → https://ai.hjhai.xyz")
        return {"pushed": True}
    else:
        if "everything up-to-date" in result.stderr:
            print("✅ Already up to date")
            return {"pushed": False, "reason": "up to date"}
        print(f"⚠️  Push issue: {result.stderr[:200]}")
        return {"pushed": False, "reason": result.stderr[:100]}


def run() -> dict:
    """Full publish: export JSON + git push."""
    print("📦 Publisher — exporting and deploying...\n")

    data = export_latest_json()
    stats = export_stats_json()
    files = export_files(data)
    result = git_push()

    return {**files, **result}


if __name__ == "__main__":
    run()
