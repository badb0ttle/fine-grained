#!/usr/bin/env python3
"""Pipeline health monitor — check source health and generate alerts."""

import sys
from pathlib import Path
from datetime import datetime, timezone

REPO_DIR = Path(__file__).resolve().parent

def check_health() -> dict:
    """Check source health from DB and return alert info."""
    sys.path.insert(0, str(REPO_DIR))
    from scripts.pipeline import get_db

    conn = get_db()
    rows = conn.execute("""
        SELECT name, category, consecutive_failures, last_failure, last_success
        FROM sources
        WHERE consecutive_failures > 0
        ORDER BY consecutive_failures DESC
    """).fetchall()
    conn.close()

    alerts = []
    for r in rows:
        level = "warning" if r["consecutive_failures"] <= 2 else \
                "critical" if r["consecutive_failures"] <= 5 else "down"

        alerts.append({
            "name": r["name"],
            "category": r["category"],
            "consecutive_failures": r["consecutive_failures"],
            "last_success": r["last_success"],
            "level": level,
        })

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
    """Format health check result as a human-readable message."""
    if not result["alerts"]:
        return ""

    lines = ["[Pipeline 健康告警]", ""]

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

    lines.append(f"检测时间: {result['checked_at'][:19]}")

    return "\n".join(lines)

def main():
    result = check_health()
    msg = format_alert_message(result)

    if msg:
        print(msg)
        # Write alert to file for cron delivery
        alert_file = REPO_DIR.parent / "data" / "health_alert.txt"
        alert_file.write_text(msg)
        return 1  # non-zero = has alerts
    else:
        print(f"✅ All {result['total_alerts']} monitored sources healthy")
        return 0

if __name__ == "__main__":
    sys.exit(main())
