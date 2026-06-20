# Phase 7: Post-Migration Cleanup

After the API backend is live and stable (≥1 week), remove the JSON dual-write and related legacy code.

## 1. publisher.py — Remove JSON export

In `scripts/pipeline/publisher.py`, remove lines inside `run()`:
- `data = export_latest_json()`
- `stats = export_stats_json()`
- `files = export_files(data)`
- The entire API sync block from Phase 4

Replace the full `run()` body with just:
```python
def run() -> dict:
    """Publish: RSS + sitemap + git push."""
    # Keep RSS + sitemap for SEO
    import scripts.rss_feed as rf
    import scripts.sitemap_gen as sg
    rss = rf.generate()
    if rss:
        (REPO_DIR / "docs" / "rss.xml").write_text(rss)
    sitemap = sg.generate()
    (REPO_DIR / "docs" / "sitemap.xml").write_text(sitemap)
    return git_push()
```

## 2. Stale JSON files — Remove from git

```bash
git rm -r data/latest.json data/stats.json data/trending.json data/clusters.json
git rm -r data/github_top5.json data/model_leaderboard.json
# Add to .gitignore
echo "data/*.json" >> .gitignore
git commit -m "Remove stale JSON exports (API now serves live data)"
```

## 3. ECS Cron — Update P3 job

Change the publisher cron job from:
```
python3 scripts/pipeline/publisher.py  (full export + push)
```
to just:
```
python3 scripts/pipeline/publisher.py  (RSS + sitemap + push only, after cleanup)
```

The article data no longer needs to be pushed — API reads directly from DB.

## 4. Remove postbuild step

If there was a postbuild hook copying JSON to `docs/data/`, remove it. 
(Currently not in vite.config.ts — no action needed.)

## 5. Verify

```bash
# Frontend in API mode should still work
cd frontend && VITE_API_MODE=true npx vite build

# API should serve all endpoints
curl https://ai.hjhai.xyz/api/health
curl https://ai.hjhai.xyz/api/latest | jq '.curated_count'
```
