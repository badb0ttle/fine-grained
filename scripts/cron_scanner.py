#!/usr/bin/env python3
"""
Headless 快速扫描器 (Cron Scanner)
==================================
专为 cron 定时任务设计的轻量扫描脚本，跳过慢速/不稳定信源。

与 rss_scanner.py 的区别：
- 只扫描快速稳定信源（跳过量子位、TechCrunch、VentureBeat）
- HTTP 超时降至 4 秒（cron 硬限制 120 秒）
- fetch 重试次数设为 0（不再重试，减少等待）
- 执行完自动恢复全量信源列表

适用场景：cron 高频触发（如每30分钟），作为 08:00 全量 LLM 扫描的补充。
"""

import os
import sys
import time
from pathlib import Path

# ── Monkey-patch：全局 HTTP 超时缩短为 4 秒 ──
# cron 环境对单次运行有严格时间限制（120秒），必须缩短网络等待
import requests as _requests
_original_request = _requests.Session.request

def _fast_request(self, method, url, **kwargs):
    """拦截所有 requests 调用，强制注入 4 秒超时。"""
    kwargs.setdefault("timeout", 4)
    return _original_request(self, method, url, **kwargs)

_requests.Session.request = _fast_request

# ── 定位项目根目录 ──
# cron 环境下工作目录不确定，需通过环境变量或路径探测确定
_project_root = Path(os.environ.get("HERMES_CRON_WORKDIR", Path.cwd()))
if not (_project_root / "scripts" / "pipeline").exists():
    _project_root = Path("/root/fine-grained")  # ECS 标准路径
sys.path.insert(0, str(_project_root / "scripts"))

from pipeline import scanner, dedup, scorer
import pipeline  # 直接访问 pipeline.SOURCES

# ── 快速信源列表：排除慢速/不稳定信源 ──
SKIP_SOURCES = {"量子位", "TechCrunch AI", "VentureBeat AI"}
_original_sources = list(pipeline.SOURCES)  # 备份原始列表
# 原地替换：从 SOURCES 中移除跳过的信源
pipeline.SOURCES[:] = [s for s in pipeline.SOURCES if s["name"] not in SKIP_SOURCES]

# ── 覆盖 fetch：禁用重试 ──
_original_fetch = scanner.fetch_feed

def _fetch_fast(source: dict) -> list[dict]:
    """
    快速抓取：重试次数为 0，失败直接返回空列表。

    Args:
        source: 信源定义字典。

    Returns:
        list[dict]: 文章列表，失败返回 []。
    """
    return _original_fetch(source, retries=0)

t0 = time.time()

try:
    # 注入快速 fetch 函数到 scanner 模块
    scanner.fetch_feed = _fetch_fast

    # ── 顺序执行 Pipeline 前三阶段 ──
    scan_stats = scanner.run()
    dedup_stats = dedup.run()
    scorer_stats = scorer.run()

    # 计算耗时并输出统计
    elapsed = time.time() - t0
    new_count = scan_stats.get("new_articles", 0)
    success = scan_stats.get("successful_sources", 0)
    total_src = scan_stats.get("total_sources", 0)

    print(
        f"[scanner] {elapsed:.0f}s | {success}/{total_src} sources "
        f"new={new_count} "
        f"deduped={dedup_stats.get('removed', 0)} "
        f"scored={scorer_stats.get('scored', 0)}",
        file=sys.stderr,
    )

except Exception as e:
    elapsed = time.time() - t0
    print(f"❌ Scanner failed after {elapsed:.0f}s: {e}", file=sys.stderr)
    sys.exit(1)

finally:
    # ── 关键：始终恢复全量信源列表 ──
    # 即使中途异常退出，也必须还原，避免影响后续正常扫描
    pipeline.SOURCES[:] = _original_sources
