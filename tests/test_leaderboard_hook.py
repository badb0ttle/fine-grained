from pathlib import Path


def test_leaderboard_uses_canonical_site_snapshot_in_all_modes():
    """排行榜必须像 stats 一样始终读取本站快照，避免 API 数据停更。"""
    source = Path(__file__).parents[1] / "frontend/src/hooks/useData.ts"
    text = source.read_text(encoding="utf-8")

    start = text.index("export function useLeaderboard()")
    end = text.index("// ── API-only hooks ──", start)
    hook = text[start:end]

    assert "fetch(`${DATA_BASE}data/model_leaderboard.json`)" in hook
    assert "API_BASE" not in hook
    assert "/model-leaderboard" not in hook