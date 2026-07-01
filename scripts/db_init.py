#!/usr/bin/env python3
"""
SQLite 数据库初始化模块 (DB Init)
=================================
创建 AI 情报聚合站的核心数据库及所有表结构。

数据库位置：项目根目录下 data/ai_intel.db

包含以下表：
- articles：文章主表（含评分、论文、精选等字段）
- sources：信源健康监控表
- daily_stats：每日统计表
- articles_fts：FTS5 全文搜索虚拟表（含同步触发器）

索引：覆盖 source_name、category、published、scanned_at、curated、score_total、is_paper、content_hash。

技术栈：SQLite 3 + FTS5（全文搜索），无需外部依赖。
"""

import sqlite3
from pathlib import Path

# 数据库文件路径：项目根目录/data/ai_intel.db
DB_PATH = Path(__file__).parent.parent / "data" / "ai_intel.db"


# ── 完整建表 SQL ──
SCHEMA = """
-- ========== Articles (主表) ==========
-- 存储所有采集的文章，是系统的核心数据表
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,                    -- 原始标题
    link            TEXT    NOT NULL UNIQUE,             -- 原文链接（唯一约束，防重）
    summary         TEXT,                                -- 原始摘要
    published       TEXT,                                -- 发布时间（ISO 格式）
    source_name     TEXT    NOT NULL,                    -- 信源名称
    category        TEXT,                                -- 分类（如 AI Lab, Paper, 中文媒体）
    content_hash    TEXT    NOT NULL,                    -- SHA256(title+link) 去重哈希
    -- LLM 处理字段 (Phase 2)
    title_cn        TEXT,                                -- 中文标题翻译
    summary_cn      TEXT,                                -- 中文摘要翻译
    why_it_matters  TEXT,                                -- 重要性解读（LLM 生成）
    -- 质量评分 (Phase 2)
    score_authority    REAL DEFAULT 0,                   -- 权威性评分
    score_timeliness   REAL DEFAULT 0,                   -- 时效性评分
    score_depth        REAL DEFAULT 0,                   -- 深度评分
    score_relevance    REAL DEFAULT 0,                   -- 相关性评分
    score_total        REAL DEFAULT 0,                   -- 综合评分（四维加权）
    -- 论文专属字段 (Phase 2)
    is_paper        INTEGER DEFAULT 0,                   -- 是否为 ArXiv 论文
    paper_id        TEXT,                                -- ArXiv 论文 ID（如 2401.12345）
    paper_authors   TEXT,                                -- 作者列表
    paper_method    TEXT,                                -- 核心方法（LLM 分析）
    paper_benchmark TEXT,                                -- Benchmark 结果（LLM 分析）
    paper_takeaway  TEXT,                                -- 一句话启发（LLM 分析）
    github_repo     TEXT,                                -- 关联的 GitHub 仓库 URL
    -- 精选
    curated         INTEGER DEFAULT 0,                   -- 是否入选每日精选（1=是）
    curated_at      TEXT,                                -- 精选时间
    -- 元数据
    scanned_at      TEXT,                                -- 扫描批次时间
    created_at      TEXT DEFAULT (datetime('now'))       -- 记录创建时间
);

-- ========== Sources (信源健康监控) ==========
-- 记录每个 RSS 信源的扫描状态和健康度
CREATE TABLE IF NOT EXISTS sources (
    name                 TEXT PRIMARY KEY,               -- 信源名称（主键）
    url                  TEXT,                           -- RSS/API 地址
    category             TEXT,                           -- 分类
    last_success         TEXT,                           -- 最近成功时间
    last_failure         TEXT,                           -- 最近失败时间
    consecutive_failures INTEGER DEFAULT 0,              -- 连续失败次数（0=健康）
    article_count_last   INTEGER DEFAULT 0,              -- 上次扫描文章数
    avg_response_ms      REAL                            -- 平均响应时间（毫秒）
);

-- ========== Daily Stats (每日统计) ==========
-- 每日 Pipeline 运行统计，支撑运营看板
CREATE TABLE IF NOT EXISTS daily_stats (
    date               TEXT PRIMARY KEY,                 -- YYYY-MM-DD（主键）
    total_sources      INTEGER,                          -- 信源总数
    successful_sources INTEGER,                          -- 成功扫描的信源数
    total_articles     INTEGER,                          -- 采集文章总数
    new_articles       INTEGER,                          -- 新增文章数
    curated_count      INTEGER,                          -- 当日精选数
    pipeline_duration_ms INTEGER,                        -- Pipeline 总耗时（毫秒）
    top_categories     TEXT                              -- 热门分类 Top N（JSON 格式）
);

-- ========== Indexes ==========
-- 覆盖高频查询字段，加速前端页面加载
CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source_name);
CREATE INDEX IF NOT EXISTS idx_articles_category  ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_published  ON articles(published);
CREATE INDEX IF NOT EXISTS idx_articles_scanned    ON articles(scanned_at);
CREATE INDEX IF NOT EXISTS idx_articles_curated    ON articles(curated);
CREATE INDEX IF NOT EXISTS idx_articles_score      ON articles(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_articles_is_paper   ON articles(is_paper);
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_hash ON articles(content_hash);

-- ========== FTS5 全文搜索 ==========
-- 内容同步自 articles 表的虚拟表，支持中英文混合搜索
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title,
    summary,
    title_cn,
    summary_cn,
    source_name,
    category,
    content='articles',       -- 外部内容表
    content_rowid='id'        -- 外部表的主键列
);

-- FTS5 同步触发器：INSERT 时自动更新搜索索引
CREATE TRIGGER IF NOT EXISTS trg_articles_ai AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES (new.id, new.title, new.summary, new.title_cn, new.summary_cn, new.source_name, new.category);
END;

-- FTS5 同步触发器：DELETE 时从搜索索引中移除
CREATE TRIGGER IF NOT EXISTS trg_articles_ad AFTER DELETE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES ('delete', old.id, old.title, old.summary, old.title_cn, old.summary_cn, old.source_name, old.category);
END;

-- FTS5 同步触发器：UPDATE 时先删旧记录再插新记录
CREATE TRIGGER IF NOT EXISTS trg_articles_au AFTER UPDATE ON articles BEGIN
    INSERT INTO articles_fts(articles_fts, rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES ('delete', old.id, old.title, old.summary, old.title_cn, old.summary_cn, old.source_name, old.category);
    INSERT INTO articles_fts(rowid, title, summary, title_cn, summary_cn, source_name, category)
    VALUES (new.id, new.title, new.summary, new.title_cn, new.summary_cn, new.source_name, new.category);
END;
"""


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    初始化数据库：创建目录、连接、执行建表脚本。

    所有 CREATE 语句使用 IF NOT EXISTS，可安全重复调用。

    Args:
        db_path: 数据库文件路径，默认为 data/ai_intel.db。

    Returns:
        sqlite3.Connection: 已初始化并提交的数据库连接。
    """
    # 确保 data 目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    # executescript 一次性执行所有 DDL 语句（多条 SQL 分号分隔）
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


if __name__ == "__main__":
    # 独立运行：初始化数据库并打印已创建的表清单
    conn = init_db()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"✅ Database initialized at {DB_PATH}")
    print(f"📊 Tables: {', '.join(t[0] for t in tables)}")
    conn.close()
