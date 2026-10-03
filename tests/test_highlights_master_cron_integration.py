"""Highlights run as an isolated master-cron step, never inside the core sports request."""
import time

import app as app_module


def _ok(status="OK", external_calls=0, **extra):
    return {"ok": True, "status": status, "external_calls": external_calls, **extra}


def test_sports_cycle_does_not_run_highlights_inline(monkeypatch):
    labels = []
    stages = {
        "api_football_match_window": _ok("CACHE", fixtures_count=2),
        "api_football_deep_enrichment": _ok("SKIPPED_NOT_DUE"),
        "odds": _ok("CACHE_REUSED"),
        "pick_grading": _ok("OK", picks_checked=0),
    }

    def safe_call(label, *_args, **_kwargs):
        labels.append(label)
        return dict(stages[label])

    monkeypatch.setattr(app_module, "_safe_sports_sync_call", safe_call)
    monkeypatch.setattr(app_module, "sports_sync_window_state", lambda: {"live_refresh_required": False})
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda limit=1: [])
    monkeypatch.setattr(app_module, "invalidate_v934_realtime_cache", lambda *_a, **_k: None)
    monkeypatch.setattr(app_module, "automation_safe_set", lambda *_a, **_k: {"ok": True})
    monkeypatch.setattr(app_module, "has_request_context", lambda: False)
    monkeypatch.setattr(
        app_module,
        "v766_sync_highlights_daily",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("highlights must not run inline")),
    )

    result = app_module.run_sports_sync_cycle(force=False, trigger_type="shared_telegram_cron")

    assert result["ok"] is True
    assert "highlights" not in labels
    assert "highlights" not in result
    assert result["external_calls"] == 0


def test_highlights_fresh_six_hour_window_skips_provider(monkeypatch):
    now = 10_000.0
    monkeypatch.setenv("HIGHLIGHTS_SYNC_INTERVAL_MINUTES", "360")
    monkeypatch.setattr(time, "time", lambda: now)
    monkeypatch.setattr(
        app_module,
        "automation_get",
        lambda key, default=None: {
            "ok": True,
            "status": "OK",
            "errors": [],
            "attempt_finished_epoch": now - (60 * 60),
        } if key == "sportsdb_highlights_last_sync" else default,
    )
    monkeypatch.setattr(
        app_module,
        "sync_sportsdb_highlights",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("provider must stay cached")),
    )

    result = app_module.v766_sync_highlights_daily(force=False, days_back=2, limit=250)

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["reason"] == "fresh_sync_window"
    assert result["external_calls"] == 0
    assert 0 < result["next_check_seconds"] <= 5 * 60 * 60


def test_highlights_after_six_hours_runs_and_persists(monkeypatch):
    now = 50_000.0
    written = []
    calls = []
    monkeypatch.setenv("HIGHLIGHTS_SYNC_INTERVAL_MINUTES", "360")
    monkeypatch.setattr(time, "time", lambda: now)
    monkeypatch.setattr(
        app_module,
        "automation_get",
        lambda key, default=None: {
            "ok": True,
            "status": "OK",
            "errors": [],
            "attempt_finished_epoch": now - (361 * 60),
        } if key == "sportsdb_highlights_last_sync" else default,
    )
    monkeypatch.setattr(
        app_module,
        "sync_sportsdb_highlights",
        lambda *args, **kwargs: calls.append((args, kwargs)) or {
            "ok": True,
            "status": "OK",
            "external_calls": 2,
            "highlights_found": 1,
            "linked_matches": 1,
            "errors": [],
        },
    )
    monkeypatch.setattr(app_module, "automation_set", lambda key, value: written.append((key, value)))

    result = app_module.v766_sync_highlights_daily(force=False, days_back=2, limit=250)

    assert result["ok"] is True
    assert result["external_calls"] == 2
    assert calls and calls[0][1] == {"days_back": 2, "limit": 250, "force": False}
    assert written and written[-1][0] == "sportsdb_highlights_last_sync"
    assert written[-1][1]["attempt_finished_epoch"] == now
