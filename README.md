# 🤖 AI Intelligence

每日 AI 技术情报 — 自动采集最新 AI 动态、论文、博客和技术讨论。

🌐 **https://ai.hjhai.xyz** | 📊 [仪表盘](https://ai.hjhai.xyz/dashboard.html)

## 架构

```
scripts/
├── db_init.py           # 初始化 SQLite 数据库
├── db_migrate.py        # 从 JSON 迁移数据
├── pipeline_run.py      # Pipeline 主入口
├── pipeline/
│   ├── __init__.py      # 共享配置 + DB 连接
│   ├── scanner.py       # Stage 1: RSS 多源采集
│   ├── dedup.py         # Stage 2: 跨源去重
│   ├── scorer.py        # Stage 3: 质量评分
│   ├── curator.py       # Stage 4: LLM 精选 + 翻译
│   └── publisher.py     # Stage 5: 导出 + Git Push
data/
├── ai_intel.db          # SQLite 主存储 (FTS5 全文索引)
├── latest.json          # 前端消费的精选数据
├── stats.json           # 仪表盘统计数据
├── raw.json             # (deprecated) 原始 JSON 备份
├── history/             # 每日历史快照
index.html               # GitHub Pages 前端
dashboard.html           # Pipeline 仪表盘
CNAME                    # 自定义域名
```

## 数据流

```
采集(scanner) → 去重(dedup) → 打分(scorer) → LLM精选翻译(curator) → 发布(publisher)
     │              │              │                    │                   │
     ▼              ▼              ▼                    ▼                   ▼
  SQLite DB ←── articles 表 (266+ articles, FTS5 索引, 质量评分)
     │
     ├── latest.json  (精选 Top 10 → 前端展示)
     ├── stats.json   (仪表盘数据)
     └── GitHub Pages (自动推送)
```

## 数据源

- **AI Lab**: OpenAI, Google AI, DeepMind, Meta AI, Anthropic, Mistral, Stability AI, Cohere
- **Paper**: ArXiv (cs.AI, cs.LG, cs.CL, cs.CV, stat.ML)
- **Community**: HuggingFace Blog, Hacker News
- **Blog**: The Gradient, Lil'Log, TechCrunch AI, VentureBeat AI
- **中文**: 雷锋网 AI

## 本地运行

```bash
pip install feedparser requests beautifulsoup4 sqlite-utils sqlite-vec

# 首次：初始化数据库 + 迁移现有数据
python scripts/db_init.py
python scripts/db_migrate.py

# 运行完整 Pipeline
python scripts/pipeline_run.py

# 或单独运行某个阶段
python -m scripts.pipeline.scanner
python -m scripts.pipeline.scorer
```

## 自动更新

由 Hermes Agent Cron 每日 8:00 自动执行 Pipeline 并推送。

## 路线图

详见 [ROADMAP.md](ROADMAP.md) — 6 阶段 18 项升级计划。
