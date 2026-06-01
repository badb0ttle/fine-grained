# 🤖 AI Intelligence

每日 AI 技术情报 — 自动采集最新 AI 动态、论文、博客和技术讨论。

🌐 **https://ai.hjhai.xyz**

## 架构

```
scripts/
├── rss_scanner.py   # RSS 多源扫描器
├── deploy.py        # 一键采集+部署
data/
├── latest.json      # 最新数据
├── history/         # 历史快照
index.html           # GitHub Pages 前端
assets/style.css     # 样式
CNAME                # 自定义域名
```

## 数据源

- **AI Lab**: OpenAI, Google AI, DeepMind, Meta AI, Anthropic, Mistral, Stability AI, Cohere
- **Paper**: ArXiv (cs.AI, cs.LG, cs.CL, stat.ML)
- **Community**: HuggingFace Blog, Hacker News
- **Blog**: The Gradient, Lil'Log

## 本地运行

```bash
pip install feedparser requests beautifulsoup4
python scripts/rss_scanner.py
```

## 自动更新

由 Hermes Agent Cron 每日自动执行扫描并推送。
