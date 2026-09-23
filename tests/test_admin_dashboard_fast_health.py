"""Regression coverage for the request-time admin dashboard health hotfix."""
import json

import app as app_module


def test_automation_get_bounded_rejects_large_state_before_json_parse(monkeypatch):
    captured = {}

    def fake_one(query, params=()):
        captured["query"] = query
        captured["params"] = params
        return {"value_json": None, "value_bytes": 999999}

    monkeypatch.setattr(app_module, "one", fake_one)
    marker = {"safe": True}
    assert app_module.automation_get_bounded("telegram_last_dispatch", marker, max_bytes=4096) is marker
    assert "CASE WHEN length(CAST(value_json AS BLOB))<=?" in captured["query"]
    assert captured["params"] == (4096, "telegram_last_dispatch")


def test_automation_get_bounded_parses_small_valid_json(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "one",
        lambda *_a, **_kw: {"value_json": json.dumps({"status": "PASS"}), "value_bytes": 18},
    )
    assert app_module.automation_get_bounded("qa", {}) == {"status": "PASS"}


def test_fast_telegram_overview_does_not_invoke_full_diagnostics(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "telegram_diagnostics_safe",
        lambda: (_ for _ in ()).throw(AssertionError("full diagnostics must not run")),
    )
    monkeypatch.setattr(app_module, "env_present", lambda key: key in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"})
    monkeypatch.setattr(app_module, "env_bool", lambda *_a, **_kw: True)
    monkeypatch.setattr(app_module, "safe_count", lambda *_a, **_kw: 2)

    def fake_one(query, params=()):
        if "telegram_settings" in query:
            return {"enabled": 1}
        if "telegram_queue" in query:
            return {"status": "sent", "error_message": "", "sent_at_madrid": "2026-09-23T18:30:00+02:00"}
        return None

    monkeypatch.setattr(app_module, "one", fake_one)

    def fake_state(key, default=None, max_bytes=64 * 1024):
        values = {
            "last_cron_telegram_call": {"time": "2026-09-23T18:30:00+02:00"},
            "last_cron_http_status": 200,
            "last_cron_result": "QUEUED",
        }
        return values.get(key, default)

    monkeypatch.setattr(app_module, "automation_get_bounded", fake_state)
    result = app_module.v928_telegram_overview_fast()
    assert result["automatic_status"] == "Cron activo"
    assert result["pending"] == 2
    assert result["summary_mode"] == "BOUNDED_READ_ONLY"
    assert result["no_provider_call"] is True


def test_admin_overview_uses_fast_summaries_only(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "telegram_diagnostics_safe",
        lambda: (_ for _ in ()).throw(AssertionError("dashboard must not run deep Telegram diagnostics")),
    )
    monkeypatch.setattr(
        app_module,
        "v773_automation_center_context",
        lambda: (_ for _ in ()).throw(AssertionError("dashboard must not load full automation context")),
    )
    monkeypatch.setattr(
        app_module,
        "v928_telegram_overview_fast",
        lambda: {"automatic_status": "Cron activo", "pending": 0},
    )
    monkeypatch.setattr(
        app_module,
        "v928_automation_overview_fast",
        lambda: {"jobs_ready": 5, "jobs_total": 5, "generated_at_madrid": "qa"},
    )
    monkeypatch.setattr(app_module, "latest_observability_errors", lambda *_a, **_kw: [])
    monkeypatch.setattr(app_module, "safe_count", lambda *_a, **_kw: 0)

    result = app_module.v928_admin_overview({"match_hub": {"counts": {"today": 3, "live": 1}}})
    assert result["telegram"]["automatic_status"] == "Cron activo"
    assert result["automation"]["jobs_ready"] == 5
    assert result["matches_today"] == 3
    assert result["live_now"] == 1
    assert result["no_render_api_call"] is True
