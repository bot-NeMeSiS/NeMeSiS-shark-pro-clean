"""Highlights must run inside the existing master sports cron without becoming a core-data blocker."""
from tools.render_cron_master_tick import sanitized_sports_pipeline
import app as app_module


def _ok(status="OK", external_calls=0, **extra):
    return {"ok": True, "status": status, "external_calls": external_calls, **extra}


def _stub_core(monkeypatch, highlight_result):
    monkeypatch.setattr(app_module, "sports_sync_window_state", lambda: {"live_refresh_required": False})
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda limit=1: [])
    monkeypatch.setattr(app_module, "sync_api_football_match_window", lambda *a, **k: _ok("CACHE", fixtures_count=2))
    monkeypatch.setattr(app_module, "sync_sportsdb_calendar", lambda *a, **k: _ok("NOT_REQUIRED", processed=0))
    monkeypatch.setattr(app_module, "run_api_exploitation_if_due", lambda *a, **k: _ok("SKIPPED_NOT_DUE"))
    monkeypatch.setattr(app_module, "sync_odds_events", lambda *a, **k: _ok("CACHE_REUSED"))
    monkeypatch.setattr(app_module, "run_pick_grading", lambda *a, **k: _ok("OK", picks_checked=0))
    monkeypatch.setattr(app_module, "v766_sync_highlights_daily", lambda *a, **k: dict(highlight_result))
    monkeypatch.setattr(app_module, "invalidate_v934_realtime_cache", lambda *_a, **_k: None)
    writes = []
    monkeypatch.setattr(app_module, "automation_safe_set", lambda key, value: writes.append((key, value)) or {"ok": True})
    return writes


def test_master_sports_sync_runs_bounded_highlights_and_counts_provider_calls(monkeypatch):
    calls = []

    def highlights(*args, **kwargs):
        calls.append((args, kwargs))
        return {
            "ok": True,
            "status": "OK",
            "highlights_found": 3,
            "linked_matches": 2,
            "external_calls": 2,
            "persistent_cache_hits": 1,
            "profile_links_reused": 1,
            "v2_event_lookups": 1,
            "v2_cache_hits": 0,
            "v2_highlights_found": 1,
            "errors": [],
        }

    writes = _stub_core(monkeypatch, highlights())
    monkeypatch.setattr(app_module, "v766_sync_highlights_daily", highlights)

    result = app_module.run_sports_sync_cycle(force=False, trigger_type="shared_telegram_cron")

    assert len(calls) == 1
    assert calls[0][1] == {"force": False, "days_back": 5, "limit": 250}
    assert result["ok"] is True
    assert result["status"] == "OK"
    assert result["highlights_synced"] == 3
    assert result["highlight_external_calls"] == 2
    assert result["external_calls"] == 2
    assert result["media_errors"] == []
    state = next(value for key, value in writes if key == "sports_sync_operational_state")
    assert state["highlight_status"] == "OK"
    assert state["highlights_synced"] == 3
    assert state["highlight_external_calls"] == 2


def test_highlight_failure_is_visible_but_does_not_break_core_sports_sync(monkeypatch):
    writes = _stub_core(monkeypatch, {
        "ok": False,
        "status": "FAILED",
        "external_calls": 1,
        "errors": ["PROVIDER_MEDIA_FAILURE"],
    })

    result = app_module.run_sports_sync_cycle(force=False, trigger_type="shared_telegram_cron")

    assert result["ok"] is True
    assert result["status"] == "OK"
    assert result["errors"] == []
    assert result["media_errors"] == ["PROVIDER_MEDIA_FAILURE"]
    assert result["highlight_external_calls"] == 1
    state = next(value for key, value in writes if key == "sports_sync_operational_state")
    assert state["highlight_status"] == "FAILED"
    assert state["highlight_errors_count"] == 1


def test_highlight_stage_survives_compact_and_master_sanitizer():
    sports_result = {
        "ok": True,
        "status": "OK",
        "fixtures": {"ok": True, "status": "CACHE", "fixtures_count": 1, "external_calls": 0},
        "fallback": {"ok": True, "status": "NOT_REQUIRED", "processed": 0, "external_calls": 0},
        "live": {"ok": True, "status": "SAFE_SKIP_NO_LIVE_WINDOW", "external_calls": 0},
        "odds": {"ok": True, "status": "CACHE_REUSED", "external_calls": 0},
        "highlights": {
            "ok": True,
            "status": "OK",
            "highlights_found": 4,
            "linked_matches": 3,
            "external_calls": 2,
            "persistent_cache_hits": 2,
            "profile_links_reused": 1,
            "v2_event_lookups": 1,
            "v2_cache_hits": 1,
            "v2_highlights_found": 1,
        },
        "deep_enrichment": {"status": "SKIPPED_NOT_DUE"},
        "deep_status": "SKIPPED_NOT_DUE",
        "deep_external_calls": 0,
        "external_calls": 2,
        "processed": 1,
    }

    diagnostics = app_module._build_sports_pipeline_diagnostics(sports_result, {})
    stage = diagnostics["current_sync"]["highlights_refresh"]
    assert stage["state"] == "OK"
    assert stage["highlights_found"] == 4
    assert stage["linked_matches"] == 3
    assert stage["v2_event_lookups"] == 1
    assert stage["v2_cache_hits"] == 1

    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "PASS", "sports_pipeline": diagnostics},
        "2026-10-03T01:20:00+02:00",
        "2026-10-03T01:20:05+02:00",
    )["sports_pipeline"]
    assert compact["current_sync"]["highlights_refresh"]["highlights_found"] == 4

    sanitized = sanitized_sports_pipeline({"sports_pipeline": compact}, "secret-canary")
    media = sanitized["current_sync"]["highlights_refresh"]
    assert media["state"] == "OK"
    assert media["external_calls"] == 2
    assert media["profile_links_reused"] == 1
    assert media["v2_highlights_found"] == 1
    assert "secret-canary" not in str(sanitized)
