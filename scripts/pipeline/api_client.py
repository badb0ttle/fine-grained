"""
API 客户端模块 (API Client)
===========================
AllOfAI 后端 API 调用封装，供 cron Pipeline 使用。

功能：
- 将扫描/精选结果 POST 到 FastAPI 后端（本地 127.0.0.1:8001）
- 前端通过 API 获取实时数据，替代静态 JSON 文件方案
- 支持幂等键（Idempotency Key）保证重试安全

配置：
- AI_INTEL_API_BASE：API 地址（默认 http://127.0.0.1:8001）
- AI_INTEL_API_KEY：Bearer Token 认证密钥
- AI_INTEL_API_ENABLED：是否启用 API 推送（默认 1=启用）

注意：cron 环境不自动加载 .env，模块内置了 fallback 读取逻辑。
"""

import json
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ── 配置区 ──

# 默认地址：ECS 上用 OpenResty 反向代理到本地 8001 端口
API_BASE = os.getenv("AI_INTEL_API_BASE", "http://127.0.0.1:8001")
API_KEY = os.getenv("AI_INTEL_API_KEY", "")

# Cron / 非登录 shell 环境不会自动加载 .env 文件
# 这里做 fallback：直接读取文件解析 API_KEY
if not API_KEY:
    from pathlib import Path as _P
    # 尝试多个可能的 .env 路径
    _envf = _P(os.getenv("HERMES_HOME", "/root/.hermes")) / ".env"
    if not _envf.exists():
        _envf = _P("/root/fine-grained/.env")
    if _envf.exists():
        for _l in _envf.read_text().splitlines():
            _l = _l.strip()
            if _l.startswith("AI_INTEL_API_KEY="):
                # 去除引号（支持单引号和双引号）
                API_KEY = _l.split("=", 1)[1].strip().strip('"').strip("'")
                break

# 通过环境变量控制是否启用 API 推送
API_ENABLED = os.getenv("AI_INTEL_API_ENABLED", "1") == "1"


def _request(method: str, path: str, body: dict) -> dict:
    """
    发送带认证的 HTTP 请求到 API。

    自动附加：
    - Authorization: Bearer Token
    - X-Idempotency-Key：基于 scan_id + 时间戳的幂等键（防重复提交）

    Args:
        method: HTTP 方法（POST/PUT/GET）。
        path: API 路径（如 "/api/admin/batch"）。
        body: 请求体 dict，会被 JSON 序列化。

    Returns:
        dict: API 返回的 JSON 响应，失败时含 status: "error" 和错误详情。
    """
    if not API_ENABLED:
        return {"status": "disabled", "reason": "AI_INTEL_API_ENABLED=0"}

    url = f"{API_BASE}{path}"
    # JSON 序列化请求体，确保中文字符不被转义
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    # 构造幂等键：scan_id + UTC 时间戳（精确到秒）
    # 确保同一批数据不会因网络重试被重复处理
    scan_id = body.get("scan_id", "unknown")
    idempotency_key = f"{scan_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "X-Idempotency-Key": idempotency_key,
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # HTTP 4xx/5xx 错误：读取响应体作为错误详情
        body = e.read().decode("utf-8", errors="replace")
        return {"status": "error", "http_status": e.code, "detail": body}
    except urllib.error.URLError as e:
        # 网络层错误（DNS、连接超时等）
        return {"status": "error", "reason": str(e.reason)}


def post_batch(articles: list, stats: dict = None, scan_id: str = "") -> dict:
    """
    批量提交文章和每日统计到 API。

    将 DB 行格式的文章转换为 API 兼容格式（字段映射），
    可选附带 daily_stats 统计信息。

    Args:
        articles: 文章字典列表（与 DB 行结构一致）。
        stats: 可选的每日统计字典（daily_stats 表数据）。
        scan_id: 扫描批次标识符（如 "2026-W25"）。

    Returns:
        dict: API 响应。
    """
    if not API_ENABLED:
        return {"status": "disabled"}

    # 构造 API 兼容的文章列表（字段白名单 + 类型转换）
    api_articles = []
    for a in articles:
        api_articles.append({
            "title": a.get("title", ""),
            "link": a.get("link", ""),
            "summary": a.get("summary", ""),
            "published": a.get("published", ""),
            "source_name": a.get("source_name", "unknown"),
            "category": a.get("category", "general"),
            "score_total": a.get("score_total", 0),
            "score_authority": a.get("score_authority", 0),
            "score_timeliness": a.get("score_timeliness", 0),
            "score_depth": a.get("score_depth", 0),
            "score_relevance": a.get("score_relevance", 0),
            "content_hash": a.get("content_hash", ""),
            "is_paper": bool(a.get("is_paper", False)),
            "paper_id": a.get("paper_id", ""),
        })

    payload = {
        "scan_id": scan_id,
        "articles": api_articles,
    }
    if stats:
        payload["stats"] = stats

    return _request("POST", "/api/admin/batch", payload)


def post_curation(curated: list, scan_id: str = "") -> dict:
    """
    提交精选结果到 API。

    Args:
        curated: 精选文章列表，每项含 id, title_cn, summary_cn, why_it_matters。
        scan_id: 批次标识符。

    Returns:
        dict: API 响应。
    """
    return _request("POST", "/api/admin/curation", {
        "scan_id": scan_id,
        "curated": curated,
    })


def health_check() -> dict:
    """
    检查 API 是否可达。

    调用 /health 端点，5 秒超时。

    Returns:
        dict: API 健康状态，失败时含 status: "error"。
    """
    try:
        url = f"{API_BASE}/health"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "error", "reason": str(e)}
