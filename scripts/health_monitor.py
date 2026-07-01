#!/usr/bin/env python3
"""
信源健康监控模块 (Health Monitor)
==================================
检查所有 RSS 信源的扫描健康状态，生成分级告警信息。

告警等级（基于连续失败次数）：
- warning（1-2次）：轻微异常，可能是临时网络波动
- critical（3-5次）：严重异常，需要关注
- down（>5次）：信源已失效，需要人工介入（更换 URL 或移除）

输出：
- 控制台打印告警信息
- data/health_alert.txt：告警文本文件（供 cron 邮件/消息推送）

用法：
  python health_monitor.py
  返回 0 = 全部健康，1 = 存在告警
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_DIR = Path(__file__).resolve().parent


def check_health() -> dict:
    """
    从数据库查询信源健康状态并生成告警信息。

    查询 sources 表中 consecutive_failures > 0 的记录，
    根据连续失败次数分级。

    Returns:
        dict: {
            "checked_at": ISO时间,
            "total_alerts": 告警信源总数,
            "down": 已失效信源数,
            "critical": 严重告警数,
            "alerts": [{name, category, consecutive_failures, last_success, level}, ...]
        }
    """
    # 动态导入 pipeline 包（避免循环依赖）
    sys.path.insert(0, str(REPO_DIR))
    from scripts.pipeline import get_db

    conn = get_db()
    # 查询所有存在失败记录的信源
    rows = conn.execute("""
        SELECT name, category, consecutive_failures, last_failure, last_success
        FROM sources
        WHERE consecutive_failures > 0
        ORDER BY consecutive_failures DESC
    """).fetchall()
    conn.close()

    alerts = []
    for r in rows:
        # 分级判定：1-2 = warning, 3-5 = critical, >5 = down
        level = "warning" if r["consecutive_failures"] <= 2 else \
                "critical" if r["consecutive_failures"] <= 5 else "down"

        alerts.append({
            "name": r["name"],
            "category": r["category"],
            "consecutive_failures": r["consecutive_failures"],
            "last_success": r["last_success"],
            "level": level,
        })

    # 统计各级别数量
    down_count = sum(1 for a in alerts if a["level"] == "down")
    critical_count = sum(1 for a in alerts if a["level"] == "critical")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_alerts": len(alerts),
        "down": down_count,
        "critical": critical_count,
        "alerts": alerts,
    }


def format_alert_message(result: dict) -> str:
    """
    将健康检查结果格式化为人类可读的告警消息。

    输出格式：
    [Pipeline 健康告警]
    严重: N 个信源异常
      CRITICAL — 信源名 (分类) 连续失败 X 次
      警告 — 信源名 (分类) 失败 X 次
    检测时间: YYYY-MM-DD HH:MM:SS

    Args:
        result: check_health() 返回的结果字典。

    Returns:
        str: 格式化的告警文本。无告警时返回空字符串。
    """
    if not result["alerts"]:
        return ""

    lines = ["[Pipeline 健康告警]", ""]

    # 按级别分组：严重告警（critical + down）和警告（warning）
    critical = [a for a in result["alerts"] if a["level"] in ("critical", "down")]
    warnings = [a for a in result["alerts"] if a["level"] == "warning"]

    if critical:
        lines.append(f"严重: {len(critical)} 个信源异常")
        for a in critical:
            lines.append(f"  {a['level'].upper()} — {a['name']} ({a['category']}) 连续失败 {a['consecutive_failures']} 次")
        lines.append("")

    if warnings:
        for a in warnings:
            lines.append(f"  警告 — {a['name']} ({a['category']}) 失败 {a['consecutive_failures']} 次")

    lines.append(f"检测时间: {result['checked_at'][:19]}")  # 截断毫秒

    return "\n".join(lines)


def main():
    """
    主函数：执行健康检查并输出结果。

    Returns:
        int: 0 = 无告警（全部健康），1 = 存在告警（用于 cron 判断是否发送通知）。
    """
    result = check_health()
    msg = format_alert_message(result)

    if msg:
        print(msg)
        # 将告警文本写入文件，供 cron 或其他监控系统读取
        alert_file = REPO_DIR.parent / "data" / "health_alert.txt"
        alert_file.write_text(msg)
        return 1  # 非零退出码 = 有告警
    else:
        print(f"✅ All {result['total_alerts']} monitored sources healthy")
        return 0


if __name__ == "__main__":
    sys.exit(main())
