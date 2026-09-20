"""Provider access freshness must distinguish current checks from persisted history."""

from tools.render_cron_master_tick import sanitized_sports_pipeline


def _historical():
    return {
        "ok": True,
        "status": "PARTIAL",
        "processed": 180,
        "deep_status": "SKIPPED_NO_API_FOOTBALL_FIXTURE",
        "deep_external_calls": 0,
        "deep_enrichment": {"status": "SKIPPED_NO_API_FOOTBALL_FIXTURE"},
    }


def _history():
    return {
        "latest_account": {
            "ok": False,
            "configured": True,
            "plan": "INACCESSIBLE",
            "quota": {"daily_limit": 100, "daily_remaining": 99},
            "http_status": 401,
            "error": "historical unauthorized detail",
        },
        "latest_run": {
            "status": "PARTIAL",
            "finished_at": "2026-09-10T22:20:23+00:00",
            "external_calls": 1,
            "payload_json": "{}",
        },
        "continuity": [],
    }


def test_historical_access_is_explicitly_not_current(app_module):
    pipeline = app_module._build_sports_pipeline_diagnostics(_historical(), _history())

    # Legacy compatibility remains, but the truth contract makes its age explicit.
    assert pipeline["provider_authenticated"] is False
    assert pipeline["provider_access_is_current"] is False
    assert pipeline["provider_access_freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert pipeline["provider_access"]["state"] == "ACCESS_FAILED"
    assert pipeline["provider_access"]["source"] == "LAST_PERSISTED_DEEP_SAMPLE"
    assert pipeline["provider_access"]["checked_at"] == "2026-09-10T22:20:23+00:00"
    assert pipeline["provider_access"]["is_current"] is False
    assert pipeline["provider_access"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert pipeline["quota_observation"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"


def test_current_access_is_explicitly_current(app_module):
    pipeline = app_module._build_sports_pipeline_diagnostics(
        {
            "ok": True,
            "status": "OK",
            "processed": 10,
            "deep_status": "OK",
            "deep_external_calls": 1,
            "finished_at": "2026-09-20T10:20:00+00:00",
            "deep_enrichment": {
                "status": "OK",
                "finished_at": "2026-09-20T10:20:00+00:00",
                "account": {
                    "ok": True,
                    "configured": True,
                    "plan": "Free",
                    "quota": {"daily_remaining": 90},
                    "http_status": 200,
                },
                "capabilities": {"account": {"requested": True, "http_status": 200}},
            },
        },
        {},
    )
    assert pipeline["provider_access_is_current"] is True
    assert pipeline["provider_access_freshness"] == "CURRENT_DEEP_RUN"
    assert pipeline["provider_access"]["is_current"] is True
    assert pipeline["provider_access"]["freshness"] == "CURRENT_DEEP_RUN"


def test_freshness_survives_compact_endpoint_and_master_sanitizer(app_module):
    entity_freshness = {
        "state": "PARTIAL",
        "entity_timestamps_evaluated": True,
        "scope": "MATCH_ROWS_CANONICAL_PROVIDER_CLOCKS",
        "total": 2,
        "fresh": 0,
        "observed": 1,
        "stale": 1,
        "not_established": 0,
        "reason": "Existe una fila stale.",
        "stale_samples": [{
            "fixture_id": "fixture-stale-1",
            "home_team": "Local",
            "away_team": "Visitante",
            "competition": "Liga QA",
            "provider": "SportsDB",
            "provider_observed_at": "2026-09-20T09:00:00+00:00",
            "freshness_seconds": 7200,
            "stale_reason": "LIVE_OBSERVATION_TOO_OLD",
            "status_canonical": "LIVE",
        }],
    }
    pipeline = app_module._build_sports_pipeline_diagnostics(
        _historical(), _history(), entity_freshness
    )
    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "OLD_MATCH", "sports_pipeline": pipeline},
        "2026-09-20T10:20:00+00:00",
        "2026-09-20T10:20:05+00:00",
    )["sports_pipeline"]

    assert compact["provider_access_is_current"] is False
    assert compact["provider_access_freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert compact["provider_access"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert compact["data_freshness"]["state"] == "PARTIAL"
    assert compact["data_freshness"]["stale_samples"][0]["fixture_id"] == "fixture-stale-1"
    assert compact["data_freshness"]["stale_samples"][0]["stale_reason"] == "LIVE_OBSERVATION_TOO_OLD"

    sanitized = sanitized_sports_pipeline({"sports_pipeline": compact}, "secret-canary")
    assert sanitized["provider_access_is_current"] is False
    assert sanitized["provider_access_freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert sanitized["provider_access"]["is_current"] is False
    assert sanitized["provider_access"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert sanitized["data_freshness"]["stale_samples"][0]["fixture_id"] == "fixture-stale-1"
    assert sanitized["data_freshness"]["stale_samples"][0]["freshness_seconds"] == 7200
    assert "historical unauthorized detail" not in str(sanitized)


def test_entity_freshness_exposes_only_bounded_canonical_stale_samples(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: [{"id": "seed"}])
    stale = [
        {
            "fixture_id": f"stale-{index}",
            "home_team": f"Local {index}",
            "away_team": f"Visitante {index}",
            "competition": "Liga QA",
            "provider": "SportsDB",
            "provider_observed_at": "2026-09-20T09:00:00+00:00",
            "freshness_seconds": 3600 + index,
            "freshness_state": "STALE",
            "stale_reason": "LIVE_OBSERVATION_TOO_OLD",
            "status_canonical": "LIVE",
        }
        for index in range(7)
    ]
    monkeypatch.setattr(
        app_module,
        "build_realtime_state_snapshot",
        lambda _sample: {"matches": stale + [{
            "fixture_id": "observed-ok",
            "freshness_state": "OBSERVED",
            "is_stale": False,
        }]},
    )

    snapshot = app_module._sports_entity_freshness_snapshot(limit=200)

    assert snapshot["state"] == "PARTIAL"
    assert snapshot["stale"] == 7
    assert len(snapshot["stale_samples"]) == 5
    assert [item["fixture_id"] for item in snapshot["stale_samples"]] == [
        "stale-0", "stale-1", "stale-2", "stale-3", "stale-4"
    ]
    assert all(item["stale_reason"] == "LIVE_OBSERVATION_TOO_OLD" for item in snapshot["stale_samples"])
