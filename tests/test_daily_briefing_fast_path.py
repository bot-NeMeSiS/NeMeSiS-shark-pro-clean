"""Performance contracts for Mi dia / briefing.

The route must reuse one compact sports snapshot and pass already loaded
personal data into the briefing helpers instead of re-reading it.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app.py").read_text(encoding="utf-8")


def _function_source(name):
    node = next(
        node for node in ast.parse(SOURCE).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    return ast.get_source_segment(SOURCE, node) or ""


def test_daily_briefing_route_uses_compact_context_only():
    route = _function_source("daily_briefing_page")
    assert "v932_safe_dashboard_data(request.path, compact=True)" in route
    assert "dashboard_data(" not in route
    assert "client_command_center_data(" not in route
    assert "briefing_cutoff" in route
    assert "timedelta(days=7)" in route


def test_daily_briefing_route_reuses_personal_reads():
    route = _function_source("daily_briefing_page")
    for marker in (
        "get_favorites(user_id=user_id)",
        "published_picks_for_user(user, limit=8)",
        "client_activity_feed(limit=6, user_id=user_id)",
        "telegram_config()",
        "build_client_alerts(",
        "build_daily_briefing(",
    ):
        assert marker in route


def _forbid(name):
    def forbidden(*args, **kwargs):
        raise AssertionError(f"{name} fallback reader must not run when data is supplied")
    return forbidden


def test_alert_builder_accepts_reused_inputs(app_module, monkeypatch):
    for name in ("match_hub", "get_favorites", "published_picks_for_user", "get_upcoming_matches", "telegram_config"):
        monkeypatch.setattr(app_module, name, _forbid(name))
    alerts = app_module.build_client_alerts(
        limit=6,
        user_id="u1",
        hub={"counts": {"live": 0}},
        favorites=[],
        picks=[],
        upcoming=[],
        telegram={"configured": True},
    )
    assert isinstance(alerts, list)


def test_progress_score_accepts_reused_inputs(app_module, monkeypatch):
    for name in ("get_favorites", "published_picks_for_user", "get_upcoming_matches", "client_activity_feed", "telegram_config"):
        monkeypatch.setattr(app_module, name, _forbid(name))
    score = app_module.client_progress_score(
        {"id": "u1", "membership": "PRO"},
        favorites=[{"id": "f1"}],
        picks=[{"id": "p1"}],
        upcoming=[{"id": "m1"}],
        activity=[{"id": "a1"}],
        telegram={"configured": True},
    )
    assert score == 100


def test_briefing_accepts_complete_preloaded_context(app_module, monkeypatch):
    for name in (
        "match_hub",
        "get_upcoming_matches",
        "get_matches",
        "get_favorites",
        "published_picks_for_user",
        "smart_pick_board",
        "build_client_alerts",
        "client_activity_feed",
        "client_progress_score",
        "telegram_config",
    ):
        monkeypatch.setattr(app_module, name, _forbid(name))
    briefing = app_module.build_daily_briefing(
        {"id": "u1", "membership": "PRO"},
        favorites=[{"id": "f1"}],
        picks=[{"id": "p1"}],
        live_matches=[],
        upcoming=[{"id": "m1"}],
        smart=[],
        alerts=[],
        activity=[{"id": "a1"}],
        hub={"counts": {"live": 0}, "live": []},
        today_matches=[{"id": "today"}],
        progress_score=85,
        telegram={"configured": True},
    )
    assert briefing["score"] == 85
    assert briefing["counts"]["today"] == 1
    assert briefing["counts"]["favorites"] == 1
    assert briefing["counts"]["picks"] == 1
