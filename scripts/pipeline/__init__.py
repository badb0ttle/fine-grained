#!/usr/bin/env python3
"""
AI情报聚合站 (AllOfAI) Pipeline — 共享配置与数据库访问模块。

================================================================================
模块功能
================================================================================
本模块是 Pipeline 各阶段的公共基础设施，提供：
  1. 项目根目录路径 (REPO_DIR) 和 SQLite 数据库路径 (DB_PATH)
  2. 16个 RSS/API 信源定义 (SOURCES 列表)
  3. 统一的 WAL 模式数据库连接工厂函数 (get_db)

================================================================================
项目架构概述
================================================================================
项目名: AI情报聚合站 (ai.hjhai.xyz)
运行环境: 阿里云 ECS 服务器
技术栈: Python 3.11+, SQLite FTS5, feedparser, requests, DeepSeek API

5阶段 Pipeline:
  阶段1: Scanner  (scanner.py)     — RSS/API 采集，去重入库
  阶段2: Dedup    (dedup.py)       — 跨源重复检测
  阶段3: Scorer   (scorer.py)      — 四维加权质量评分
  阶段4: Curator  (curator.py)     — DeepSeek 精选翻译
  阶段5: Publisher(publisher.py)   — JSON/RSS/Sitemap 导出 + Telegram 推送

================================================================================
信源配置说明
================================================================================
SOURCES 列表每个元素包含:
  - name:     信源显示名称（中文/英文）
  - url:      RSS feed URL 或 WordPress REST API 端点
  - category: 信源分类（AI Lab / Paper / Community / Blog / 中文媒体）
  - type:     可选，默认为 "rss"；设为 "wp_api" 表示 WordPress REST API 格式

分类说明:
  - AI Lab:    顶级 AI 研究机构的官方博客（OpenAI, Google, DeepMind, Apple, NVIDIA）
  - Paper:     ArXiv 学术论文聚合（cs.AI, cs.LG, cs.CL, cs.CV, stat.ML）
  - Community: 社区/开源平台博客（HuggingFace, PyTorch）
  - Blog:      科技媒体报道（TechCrunch, VentureBeat）
  - 中文媒体:   中文科技媒体（雷锋网, 量子位）
"""

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
# REPO_DIR: 项目仓库根目录（scripts/pipeline/__init__.py → 上溯三级到项目根）
REPO_DIR = Path(__file__).parent.parent.parent

# DB_PATH: SQLite 数据库文件路径，存储在 data/ 目录下
DB_PATH = REPO_DIR / "data" / "ai_intel.db"

# ---------------------------------------------------------------------------
# 信源定义 — 16 个 RSS/API 数据源
# ---------------------------------------------------------------------------
# 每个信源的 category 用于前端分类展示和评分权重计算
# type="wp_api" 表示该源使用 WordPress REST API JSON 格式，而非标准 RSS XML
SOURCES = [
    # --- AI 顶级实验室官方博客 (AI Lab) ---
    {"name": "OpenAI Blog",          "url": "https://openai.com/blog/rss.xml",                    "category": "AI Lab"},
    {"name": "Google AI",            "url": "https://blog.research.google/feeds/posts/default",   "category": "AI Lab"},
    {"name": "Google DeepMind",      "url": "https://blog.google/technology/ai/rss/",             "category": "AI Lab"},
    {"name": "Apple ML Research",    "url": "https://machinelearning.apple.com/rss.xml",           "category": "AI Lab"},
    {"name": "NVIDIA Blog",          "url": "https://developer.nvidia.com/blog/feed",              "category": "AI Lab"},

    # --- ArXiv 学术论文聚合 (Paper) ---
    # 覆盖 AI 核心子领域：人工智能、机器学习、计算语言学、计算机视觉、统计机器学习
    {"name": "ArXiv cs.AI",          "url": "https://rss.arxiv.org/rss/cs.AI",                    "category": "Paper"},
    {"name": "ArXiv cs.LG",          "url": "https://rss.arxiv.org/rss/cs.LG",                    "category": "Paper"},
    {"name": "ArXiv cs.CL",          "url": "https://rss.arxiv.org/rss/cs.CL",                    "category": "Paper"},
    {"name": "ArXiv cs.CV",          "url": "https://rss.arxiv.org/rss/cs.CV",                    "category": "Paper"},
    {"name": "ArXiv stat.ML",        "url": "https://rss.arxiv.org/rss/stat.ML",                  "category": "Paper"},

    # --- 社区/开源平台 (Community) ---
    {"name": "HuggingFace Blog",     "url": "https://huggingface.co/blog/feed.xml",               "category": "Community"},
    {"name": "PyTorch Blog",         "url": "https://pytorch.org/blog/feed.xml",                  "category": "Community"},

    # --- 中文科技媒体 ---
    # 雷锋网: 标准 RSS feed
    {"name": "雷锋网 AI",         "url": "https://www.leiphone.com/feed",                        "category": "中文媒体"},
    # 量子位: WordPress REST API，返回 JSON 数组而非 XML，per_page=20 限制每页条数
    {"name": "量子位",           "url": "https://www.qbitai.com/wp-json/wp/v2/posts?per_page=20", "category": "中文媒体", "type": "wp_api"},

    # --- 英文科技媒体 (Blog) ---
    {"name": "TechCrunch AI",        "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Blog"},
    {"name": "VentureBeat AI",       "url": "https://feeds.feedburner.com/venturebeat/SZYF",       "category": "Blog"},
]


def get_db() -> sqlite3.Connection:
    """
    获取 WAL 模式的 SQLite 数据库连接。

    返回的 Connection 对象配置了:
      - WAL 日志模式:  提高并发读写性能，避免写入时阻塞读取
      - 外键约束开启:  保证数据引用完整性
      - Row 工厂:      查询结果以 sqlite3.Row 对象返回，支持列名索引

    Returns:
        sqlite3.Connection: 已配置的数据库连接对象（调用方负责 conn.close()）

    注意事项:
      - WAL 模式在大多数现代文件系统上性能优异，但数据目录需可写
      - 如果 DB_PATH 对应的文件不存在，SQLite 会自动创建空数据库
    """
    conn = sqlite3.connect(str(DB_PATH))
    # WAL (Write-Ahead Logging): 写操作不阻塞读操作，适合多进程/多线程场景
    conn.execute("PRAGMA journal_mode=WAL")
    # 开启外键约束（SQLite 默认关闭），确保 REFERENCES 声明生效
    conn.execute("PRAGMA foreign_keys=ON")
    # 使用 Row 工厂，查询结果支持按列名访问：row["column_name"]
    conn.row_factory = sqlite3.Row
    return conn
