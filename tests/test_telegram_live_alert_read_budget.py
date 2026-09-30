"""Regression coverage for Telegram live-alert worker-timeout budget."""

from pathlib import Path


def test_live_alert_loader_uses_bounded_live_only_query(app_module, monkeypatch):
    seen = {"rows": []}

    sample = [
        {
            "id": "live-1",
            "match_date": app_module.today_iso(),
            "status": "LIVE",
            "priority": 95,
            "kickoff_time": "20:00",
            "competition_name": "Liga QA",
            "home_team": "Local",
            "away_team": "Visitante",
        },
        {
            "id": "not-live",
            "match_date": app_module.today_iso(),
            "status": "LIVE",
            "priority": 90,
            "kickoff_time": "20:10",
            "competition_name": "Liga QA",
            "home_team": "Otro",
            "away_team": "Rival",
        },
    ]

    def fake_rows(query, params=()):
        seen["rows"].append((query, params))
        return sample[: int(params[-1])]

    monkeypatch.setattr(app_module, "rows", fake_rows)
    monkeypatch.setattr(app_module, "is_fake_match", lambda _item: False)
    monkeypatch.setattr(
        app_module,
        "canonical_match_status",
        lambda item: {
            "is_live": item.get("id") == "live-1",
            "is_finished": False,
            "is_upcoming": False,
        },
    )
    monkeypatch.setattr(app_module, "canonical_live_minute", lambda _item: "12")
    monkeypatch.setattr(app_module, "telegram_enrich_match_for_message", lambda item: dict(item))
    monkeypatch.setenv("TELEGRAM_LIVE_ALERT_SCAN_LIMIT", "16")

    items = app_module.telegram_live_alert_matches()

    assert [item["id"] for item in items] == ["live-1"]
    query, params = seen["rows"][0]
    assert "match_date=?" in query
    assert "lower(status) LIKE '%live%'" in query
    assert "'et','p','bt'" in query
    assert "LIMIT ?" in query
    assert params[-1] == 16
    assert items[0]["client_live_minute"] == "12"


def test_live_alert_loader_has_hard_max(app_module, monkeypatch):
    captured = {}

    def fake_rows(_query, params=()):
        captured["limit"] = params[-1]
        return []

    monkeypatch.setattr(app_module, "rows", fake_rows)
    monkeypatch.setenv("TELEGRAM_LIVE_ALERT_SCAN_LIMIT", "999")

    assert app_module.telegram_live_alert_matches() == []
    assert captured["limit"] == 24


def test_live_alert_delivery_never_builds_full_match_hub():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")

    loader_start = source.index("def telegram_live_alert_matches")
    loader_end = source.index("\n\ndef enqueue_live_alerts", loader_start)
    loader = source[loader_start:loader_end]

    delivery_start = source.index("def enqueue_live_alerts")
    delivery_end = source.index("\n\ndef telegram_plain_text_from_html", delivery_start)
    delivery = source[delivery_start:delivery_end]

    assert "match_hub(" not in loader
    assert "get_results_matches(" not in loader
    assert "get_upcoming_matches(" not in loader
    assert "TELEGRAM_LIVE_ALERT_SCAN_LIMIT" in loader
    assert "min(requested, 24)" in loader

    assert "telegram_live_alert_matches()" in delivery
    assert "match_hub(" not in delivery
    assert "get_results_matches(" not in delivery


def test_scheduler_live_alert_path_is_still_enabled(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_telegram_settings",
        lambda: {
            "enabled": True,
            "auto_daily_matches": False,
            "auto_daily_picks": False,
            "auto_live_alerts": True,
        },
    )
    monkeypatch.setattr(app_module, "telegram_env_auto_enabled", lambda: False)
    monkeypatch.setattr(app_module, "telegram_env_should_enable", lambda: True)
    monkeypatch.setattr(
        app_module,
        "telegram_pro_calibration",
        lambda: {"max_queue_per_tick": 5, "max_auto_picks_per_tick": 2},
    )
    monkeypatch.setattr(
        app_module,
        "enqueue_live_alerts",
        lambda force=False: {
            "ok": True,
            "status": "NO_LIVE_ALERTS",
            "processed": 0,
            "inserted": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "discard_reasons": ["NO_LIVE_ALERTS"],
        },
    )
    monkeypatch.setattr(
        app_module,
        "enqueue_v771_telegram_activity",
        lambda **_kwargs: {
            "ok": True,
            "status": "NO_ACTIVITY_CANDIDATES",
            "processed": 0,
            "inserted": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "discard_reasons": [],
        },
    )
    monkeypatch.setattr(
        app_module,
        "process_premium_telegram_queue",
        lambda **_kwargs: {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "sent_items": [],
        },
    )

    result = app_module.telegram_scheduler_delivery(force=False)

    assert result["modules"]["live_alerts"]["status"] == "NO_LIVE_ALERTS"
    assert result["ok"] is True
