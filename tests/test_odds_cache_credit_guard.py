from __future__ import annotations

from datetime import datetime, timedelta


def _iso(app_module, delta=timedelta()):
    return (datetime.now(app_module.TZ) + delta).isoformat(timespec="seconds")


def test_odds_cache_guard_reads_current_last_sync_field(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {"ok": True, "last_sync": _iso(app_module)},
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_recently_synced() is True


def test_odds_cache_guard_keeps_legacy_time_compatibility(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {"ok": True, "time": _iso(app_module)},
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_recently_synced() is True


def test_odds_cache_guard_expires_old_sync(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {"ok": True, "last_sync": _iso(app_module, timedelta(hours=-2))},
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_recently_synced() is False


def test_recent_provider_failure_uses_short_backoff_not_success_cache(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "ok": False,
        "status": "PROVIDER_FAILURE",
        "last_sync": _iso(app_module),
        "last_attempt_at": _iso(app_module),
        "errors": ["Liga: HTTPError"],
        "quota": {"error_type": "HTTPError"},
    })
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 360)
    monkeypatch.setattr(app_module, "odds_failure_cooldown_minutes", lambda: 10)

    assert app_module.odds_recently_synced() is False
    assert app_module.odds_sync_skip_reason() == "failure_backoff"


def test_old_failed_attempt_does_not_extend_success_cache(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "ok": False,
        "status": "PROVIDER_FAILURE_STOPPED_EARLY",
        "last_sync": _iso(app_module, timedelta(minutes=-20)),
        "last_attempt_at": _iso(app_module, timedelta(minutes=-20)),
        "last_success_at": _iso(app_module, timedelta(hours=-2)),
        "errors": ["Liga: HTTPError"],
    })
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)
    monkeypatch.setattr(app_module, "odds_failure_cooldown_minutes", lambda: 10)

    assert app_module.odds_sync_skip_reason() == ""
    assert app_module.odds_recently_synced() is False


def test_malformed_quota_metadata_does_not_break_cache_classification(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "ok": True,
        "status": "OK",
        "last_success_at": _iso(app_module),
        "quota": ["unexpected legacy shape"],
        "errors": [],
    })
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_sync_skip_reason() == "success_cache"


def test_malformed_quota_metadata_does_not_break_failure_backoff(app_module, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "qa-placeholder-not-a-real-key")
    monkeypatch.setenv("THE_ODDS_API_FUNDED", "true")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    monkeypatch.setattr(app_module, "odds_failure_cooldown_minutes", lambda: 10)
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "ok": False,
        "status": "PROVIDER_FAILURE",
        "last_attempt_at": _iso(app_module),
        "errors": ["provider failure"],
        "quota": ["unexpected legacy shape"],
    })
    monkeypatch.setattr(app_module, "fetch_odds_events", lambda **_kwargs: pytest.fail("backoff must not call provider"))

    result = app_module.sync_odds_events(force=False)

    assert result["provider_failure_backoff"] is True
    assert result["external_calls"] == 0
    assert result["quota"]["error_type"] == ""


def test_error_result_never_becomes_last_success_even_with_ok_status(app_module):
    assert app_module._odds_sync_is_success({
        "ok": True,
        "status": "OK",
        "errors": ["provider failure"],
        "quota": {},
    }) is False


def test_failure_backoff_is_a_transparent_zero_call_deferral(app_module, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "qa-placeholder-not-a-real-key")
    monkeypatch.setenv("THE_ODDS_API_FUNDED", "true")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    monkeypatch.setattr(app_module, "odds_last_sync", lambda: {
        "ok": False,
        "status": "PROVIDER_FAILURE",
        "last_sync": _iso(app_module),
        "last_attempt_at": _iso(app_module),
        "last_success_at": "",
        "errors": ["Liga: HTTPError"],
        "quota": {"error_type": "HTTPError", "error_code": "EXCEEDED_FREQ_LIMIT"},
    })
    monkeypatch.setattr(app_module, "fetch_odds_events", lambda **_kwargs: pytest.fail("cooldown must not call provider"))

    result = app_module.sync_odds_events(force=False)

    assert result["status"] == "PARTIAL"
    assert result["reason"] == "provider_failure_cooldown"
    assert result["controlled_deferrals"] == ["PROVIDER_FAILURE_COOLDOWN"]
    assert result["external_calls"] == 0
    assert result["provider_observation_current"] is False
    assert result["quota"]["error_code"] == "EXCEEDED_FREQ_LIMIT"


def test_cached_odds_sync_makes_zero_provider_calls(app_module, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "qa-placeholder-not-a-real-key")
    monkeypatch.setenv("THE_ODDS_API_FUNDED", "true")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    monkeypatch.setattr(app_module, "odds_sync_skip_reason", lambda: "success_cache")
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {
            "ok": True,
            "skipped": False,
            "processed": 7,
            "last_sync": _iso(app_module),
            "external_calls": 14,
            "errors": ["historical provider error"],
        },
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)
    monkeypatch.setattr(
        app_module,
        "fetch_odds_events",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("paid provider must not be called while cache is fresh")
        ),
    )

    result = app_module.sync_odds_events(limit=80, force=False)

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["reason"] == "cache_activa"
    assert result["status"] == "CACHE_REUSED"
    assert result["external_calls"] == 0
    assert result["processed"] == 0
    assert result["errors"] == []
    assert result["cached_processed"] == 7
    assert result["cached_external_calls"] == 14



def test_odds_systemic_failure_stops_after_first_competition(app_module, monkeypatch):
    sports = [
        {"odds_key": "soccer_a", "name": "Liga A"},
        {"odds_key": "soccer_b", "name": "Liga B"},
        {"odds_key": "soccer_c", "name": "Liga C"},
    ]
    calls = []
    monkeypatch.setattr(app_module, "odds_competitions", lambda: list(sports))

    def fake_request(path, params=None):
        calls.append(path)
        return {
            "ok": False,
            "payload": {},
            "http_status": 429,
            "quota": {},
            "error": "HTTPError",
        }

    monkeypatch.setattr(app_module, "odds_api_request", fake_request)

    events, errors, quota = app_module.fetch_odds_events(limit=80)

    assert events == []
    assert len(errors) == 1
    assert calls == ["sports/soccer_a/odds"]
    assert quota["observed_calls"] == 1
    assert quota["systemic_failure"] is True
    assert quota["systemic_http_status"] == 429
    assert quota["stopped_early"] is True


def test_odds_sport_specific_not_found_does_not_stop_other_competitions(
    app_module,
    monkeypatch,
):
    sports = [
        {"odds_key": "soccer_old", "name": "Liga antigua"},
        {"odds_key": "soccer_live", "name": "Liga válida"},
    ]
    calls = []
    monkeypatch.setattr(app_module, "odds_competitions", lambda: list(sports))

    responses = [
        {
            "ok": False,
            "payload": {},
            "http_status": 404,
            "quota": {},
            "error": "HTTPError",
        },
        {
            "ok": True,
            "payload": [
                {
                    "id": "event-1",
                    "home_team": "A",
                    "away_team": "B",
                }
            ],
            "http_status": 200,
            "quota": {},
            "error": "",
        },
    ]

    def fake_request(path, params=None):
        calls.append(path)
        return responses.pop(0)

    monkeypatch.setattr(app_module, "odds_api_request", fake_request)

    events, errors, quota = app_module.fetch_odds_events(limit=80)

    assert len(errors) == 1
    assert len(events) == 1
    assert len(calls) == 2
    assert quota["observed_calls"] == 2
    assert quota["systemic_failure"] is False
    assert quota["systemic_http_status"] == 0
    assert quota["stopped_early"] is False


def test_odds_systemic_failure_classifier_is_conservative(app_module):
    for status in (0, 400, 401, 402, 403, 429, 500, 503):
        assert app_module._odds_systemic_failure_response({"http_status": status}) is True
    for status in (200, 404, 409, 422):
        assert app_module._odds_systemic_failure_response({"http_status": status}) is False


def test_odds_empty_competition_set_returns_complete_zero_call_quota(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "odds_competitions", lambda: [])

    events, errors, quota = app_module.fetch_odds_events(limit=80)

    assert events == []
    assert errors == []
    assert quota == {
        "observed_calls": 0,
        "requests_last_total": 0,
        "requests_used": None,
        "requests_remaining": None,
        "requests_last": None,
        "http_status": 0,
        "systemic_failure": False,
        "systemic_http_status": 0,
        "stopped_early": False,
        "events_received": 0,
        "events_with_bookmakers": 0,
        "bookmakers_received": 0,
        "markets_received": 0,
        "events_with_h2h": 0,
    }
