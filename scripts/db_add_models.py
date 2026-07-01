#!/usr/bin/env python3
"""
模型表补充创建模块 (DB Add Models)
==================================
在已有 SQLite 数据库中新增模型追踪相关表（models + model_benchmarks）。

本脚本独立于 db_init.py，用于对已上线的数据库进行增量 DDL 变更，
无需重建整个数据库。

涉及表：
- models：模型基础信息（名称、提供方、参数规模、上下文窗口等）
- model_benchmarks：模型 Benchmark 分数记录（关联 models.id）

所有 CREATE 语句均使用 IF NOT EXISTS，安全幂等。
"""

from pathlib import Path
import sys

# 将项目根目录加入 sys.path，以便导入 pipeline 包
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.pipeline import get_db

conn = get_db()

# ── 建表 DDL ──
conn.executescript("""
-- 模型基础信息表（名称唯一约束）
CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,          -- 模型名称（唯一，如 "GPT-5.5"）
    provider    TEXT,                          -- 提供方（如 "OpenAI", "Google"）
    release_date TEXT,                         -- 发布日期
    parameters  TEXT,                          -- 参数规模（如 "1.8T", "未知"）
    context_window TEXT,                       -- 上下文窗口（如 "1M tokens"）
    modalities  TEXT,                          -- 模态能力（如 "text,image"）
    description TEXT,                          -- 描述
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Benchmark 分数记录表（关联 models 表）
CREATE TABLE IF NOT EXISTS model_benchmarks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id    INTEGER REFERENCES models(id), -- 外键关联 models 表
    benchmark   TEXT NOT NULL,                 -- Benchmark 名称（如 "MMLU", "HumanEval"）
    score       TEXT NOT NULL,                 -- 分数（如 "92.5%"）
    source_article TEXT,                       -- 来源文章
    reported_at TEXT,                          -- 报告时间
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 为高频查询建立索引
CREATE INDEX IF NOT EXISTS idx_mb_model ON model_benchmarks(model_id);
CREATE INDEX IF NOT EXISTS idx_mb_benchmark ON model_benchmarks(benchmark);
""")

conn.commit()

# 验证：查询刚创建/已存在的 model_ 前缀表
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'model%'"
).fetchall()

print(f"✅ Added: {[t[0] for t in tables]}")
conn.close()
