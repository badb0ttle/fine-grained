# AllOfAI — AI Intelligence Aggregator / AI 情报聚合站

Multilingual AI news & paper aggregator. 15+ sources, automated curation, bilingual (zh/en) weekly briefings.

多语言 AI 资讯与论文聚合站。15+ 信源、自动精选、中英双语周报。

🌐 **https://ai.hjhai.xyz** | 📊 [Dashboard / 仪表盘](https://ai.hjhai.xyz/dashboard.html)

---

## Architecture / 架构

```
scripts/
├── db_init.py              # Init SQLite database / 初始化数据库
├── db_migrate.py           # Migrate from JSON / JSON 数据迁移
├── pipeline_run.py         # Pipeline entry / Pipeline 主入口
├── pipeline/
│   ├── __init__.py         # Shared config + DB connection
│   ├── scanner.py          # Stage 1: Multi-source RSS fetch
│   ├── dedup.py            # Stage 2: Cross-source dedup
│   ├── scorer.py           # Stage 3: Quality scoring
│   ├── curator.py          # Stage 4: LLM curation + translation
│   ├── weekly_report.py    # Weekly briefing prompt (zh + en)
│   ├── cluster_viz.py      # TF-IDF clustering
│   ├── trends.py           # Keyword trend analysis
│   ├── model_tracker.py    # Model mention extraction
│   ├── model_leaderboard.py # OpenRouter leaderboard
│   ├── github_trending.py  # GitHub trending repos
│   ├── paper_analyzer.py   # Paper deep-dive
│   ├── paper_code_link.py  # Paper ↔ GitHub code linking
│   ├── telegram_digest.py  # Telegram daily/weekly digest
│   └── publisher.py        # Stage 5: Export + Git push
├── rss_feed.py             # RSS feed generator
├── sitemap_gen.py          # Sitemap generator
├── health_monitor.py       # Source health alerts
├── github_top5.py          # GitHub AI repo top 5 (DeepSeek summary)
└── deploy.py               # Legacy deploy script
frontend/                   # React + Vite + Tailwind CSS v4
├── src/
│   ├── pages/              # HomePage, WeeklyPage, WeeklyDetailPage, ClustersPage, ModelLeaderboard, TimelinePage, AboutPage
│   ├── components/         # Layout, ArticleCard, ParticleBackground, AdminGate, Animations, Skeleton
│   └── context/            # LocaleContext (zh/en)
└── ... 
docs/                       # GitHub Pages build output
data/
├── ai_intel.db             # SQLite (FTS5 full-text index)
├── latest.json             # Curated articles for frontend
├── stats.json              # Dashboard stats
├── search_index.json       # Full-text search index
├── model_leaderboard.json  # Model rankings
├── clusters.json           # Cluster viz data
├── weekly/                 # Weekly HTML reports (zh + en)
└── history/                # Daily snapshots
```

## Data Flow / 数据流

```
15 RSS Sources → scanner.py → articles table (SQLite)
                       ↓
                  dedup.py (cross-source hash dedup)
                       ↓
                  scorer.py (4-dim quality score)
                       ↓
                  curator.py (LLM curation + CN translation)
                       ↓
                  publisher.py (JSON export + git push)
                       ↓
                  GitHub Pages → ai.hjhai.xyz
```

Weekly: `weekly_report.py` → LLM generates zh+en HTML → saved to `data/weekly/` → frontend loads by locale.

每周：`weekly_report.py` → LLM 生成中英 HTML → 存到 `data/weekly/` → 前端按语言加载。

## Data Sources / 数据源

| Category | Sources |
|----------|---------|
| AI Lab | OpenAI, Google AI, Google DeepMind, Apple ML Research, NVIDIA |
| Papers | ArXiv (cs.AI, cs.LG, cs.CL, cs.CV, stat.ML) |
| Community | HuggingFace Blog, PyTorch Blog |
| Blogs | TechCrunch AI, VentureBeat AI |
| 中文媒体 | 雷锋网 AI, 量子位 |

## Features / 功能

- **Bilingual UI** / 中英双语界面 — URL path-based locale switching (`/` zh, `/en/*` en)
- **Weekly Briefings** / 每周深度简报 — LLM-generated analysis with KPI dashboard, category charts, model rankings
- **Topic Clusters** / 聚类分析 — TF-IDF semantic clustering, 8 clusters, 900+ articles
- **Model Leaderboard** / 模型排行榜 — 300+ models via OpenRouter API, scored by Artificial Analysis + Design Arena
- **Full-text Search** / 全文搜索 — FTS5-powered, client-side search index
- **RSS + Sitemap** / RSS + 站点地图 — Auto-generated for SEO
- **GitHub Top 5** / GitHub AI 热门 — Weekly top AI repos with DeepSeek summaries
- **Telegram Digest** / Telegram 推送 — Daily + weekly digests auto-delivered
- **Admin Dashboard** / 管理后台 — Password-gated pipeline stats & health monitor
- **Dark/Light Theme** / 暗色/亮色主题 — OLED-optimized dark + light mode with dynamic particle background

## Local Setup / 本地运行

```bash
pip install feedparser requests beautifulsoup4 sqlite-utils

# First run: init + migrate
python scripts/db_init.py
python scripts/db_migrate.py

# Run full pipeline
python scripts/pipeline_run.py

# Frontend dev
cd frontend && pnpm install && pnpm dev

# Frontend build
cd frontend && pnpm build   # outputs to ../docs/
```

## Automation / 自动化

Powered by Hermes Agent Cron / 由 Hermes Agent Cron 驱动：

| Job | Schedule | Description |
|-----|----------|-------------|
| AI Intel Daily Scan | Daily 8:00 | Full pipeline + Telegram digest |
| AI Intel Weekly Briefing | Sunday 10:00 | Zh+en weekly HTML + Telegram weekly digest |
| AI Intel Daily Telegram Digest | Daily 8:15 | Telegram daily digest delivery |
| AI Intel Weekly Telegram Digest | Sunday 10:15 | Telegram weekly digest delivery |

## Roadmap / 路线图

See / 详见 [ROADMAP.md](ROADMAP.md) — 6 phases, 18 features.
