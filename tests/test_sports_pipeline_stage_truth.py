"""Truthful, secret-safe diagnostics for the current sports sync stages."""


def _fallback_run():
    return {
        "ok": True,
        "status": "PARTIAL",
        "processed": 180,
        "external_calls": 1,
        "started_at": "2026-09-20T12:15:16+02:00",
        "finished_at": "2026-09-20T12:15:24+02:00",
        "trigger_type": "shared_telegram_cron",
        "fixtures": {
            "ok": False,
            "status": "ERROR",
            "configured": True,
            "enabled": True,
            "external_calls": 1,
            "fixtures_count": 0,
            "error": "provider-sensitive-detail-must-not-be-forwarded",
        },
        "fallback": {
            "ok": True,
            "status": "OK",
            "processed": 180,
        },
        "live": {
            "ok": True,
            "status": "SAFE_SKIP_NO_LIVE_WINDOW",
            "external_calls": 0,
            "fixtures_count": 0,
        },
        "odds": {
            "ok": True,
            "status": "OK",
            "processed": 0,
            "external_calls": 2,
        },
        "deep_enrichment": {
            "status": "SKIPPED_NO_API_FOOTBALL_FIXTURE",
            "external_calls": 0,
        },
        "deep_external_calls": 0,
    }


def test_diagnostics_identify_sportsdb_fallback_without_forwarding_provider_error(app_module):
    diagnostics = app_module._build_sports_pipeline_diagnostics(_fallback_run(), {})
    current = diagnostics["current_sync"]

    assert current["selected_source"] == "SPORTSDB_FALLBACK"
    assert current["api_football_primary"] == {
        "state": "ERROR",
        "reason_code": "PROVIDER_ERROR",
        "ok": False,
        "configured": True,
        "enabled": True,
        "external_calls": 1,
        "fixtures_count": 0,
        "error_present": True,
        "used": False,
        "data_contributed": False,
        "cache_reused": False,
    }
    assert current["sportsdb_fallback"]["ok"] is True
    assert current["sportsdb_fallback"]["used"] is True
    assert current["sportsdb_fallback"]["processed"] == 180
    assert "provider-sensitive-detail" not in str(diagnostics)


def test_diagnostics_prefer_api_football_when_primary_succeeds(app_module):
    payload = _fallback_run()
    payload["status"] = "OK"
    payload["processed"] = 12
    payload["fixtures"] = {
        "ok": True,
        "status": "OK",
        "configured": True,
        "enabled": True,
        "external_calls": 5,
        "fixtures_count": 12,
    }
    payload["fallback"] = {
        "ok": True,
        "status": "NOT_REQUIRED",
        "skipped": True,
        "processed": 0,
    }

    diagnostics = app_module._build_sports_pipeline_diagnostics(payload, {})
    current = diagnostics["current_sync"]
    assert current["selected_source"] == "API_FOOTBALL_PRIMARY"
    assert current["api_football_primary"]["fixtures_count"] == 12
    assert current["api_football_primary"]["reason_code"] == "NONE"
    assert current["sportsdb_fallback"]["used"] is False


def test_compact_cron_payload_preserves_only_stage_truth(app_module):
    diagnostics = app_module._build_sports_pipeline_diagnostics(_fallback_run(), {})
    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {
            "ok": True,
            "status": "OLD_MATCH",
            "sports_pipeline": diagnostics,
            "sent": 0,
            "processed": 0,
        },
        "2026-09-20T12:15:16+02:00",
        "2026-09-20T12:15:24+02:00",
    )
    current = compact["sports_pipeline"]["current_sync"]
    assert current["selected_source"] == "SPORTSDB_FALLBACK"
    assert current["sportsdb_fallback"]["processed"] == 180
    assert current["api_football_primary"]["error_present"] is True
    assert "provider-sensitive-detail" not in str(compact)


def test_master_cron_sanitizer_preserves_stage_truth_and_redacts_secret(app_module):
    from tools.render_cron_master_tick import sanitized_sports_pipeline

    diagnostics = app_module._build_sports_pipeline_diagnostics(_fallback_run(), {})
    sanitized = sanitized_sports_pipeline({"sports_pipeline": diagnostics}, "super-secret-value")
    current = sanitized["current_sync"]
    assert current["selected_source"] == "SPORTSDB_FALLBACK"
    assert current["sportsdb_fallback"]["processed"] == 180
    assert current["api_football_primary"]["external_calls"] == 1
    assert "provider-sensitive-detail" not in str(sanitized)
    assert "super-secret-value" not in str(sanitized)


def test_reason_code_classifies_auth_without_exposing_message(app_module):
    stage = {
        "ok": False,
        "status": "PARTIAL",
        "configured": True,
        "enabled": True,
        "errors": {"token": "Invalid API key: SECRET-CANARY"},
    }
    assert app_module._sports_stage_reason_code(stage) == "AUTH_OR_ACCESS"
    diagnostics = app_module._build_sports_pipeline_diagnostics(
        {
            **_fallback_run(),
            "fixtures": stage,
        },
        {},
    )
    text = str(diagnostics)
    assert diagnostics["current_sync"]["api_football_primary"]["reason_code"] == "AUTH_OR_ACCESS"
    assert "SECRET-CANARY" not in text


def test_reason_code_classifies_quota_and_network(app_module):
    assert app_module._sports_stage_reason_code(
        {"ok": False, "configured": True, "enabled": True, "error": "HTTP 429 rate limit"}
    ) == "RATE_OR_QUOTA"
    assert app_module._sports_stage_reason_code(
        {"ok": False, "configured": True, "enabled": True, "error": "connection timed out"}
    ) == "NETWORK_OR_TIMEOUT"


def test_diagnostics_mark_mixed_source_when_partial_primary_also_persisted(app_module):
    payload = _fallback_run()
    payload["fixtures"] = {
        "ok": False,
        "status": "PARTIAL",
        "configured": True,
        "enabled": True,
        "external_calls": 5,
        "fixtures_count": 3,
        "errors": {"provider": "partial response"},
    }
    diagnostics = app_module._build_sports_pipeline_diagnostics(payload, {})
    current = diagnostics["current_sync"]
    assert current["selected_source"] == "MIXED_PRIMARY_AND_FALLBACK"
    assert current["api_football_primary"]["fixtures_count"] == 3
    assert current["sportsdb_fallback"]["processed"] == 180


def test_current_sync_declares_match_window_scope_and_odds_calls(app_module):
    current = app_module._build_sports_pipeline_diagnostics(_fallback_run(), {})["current_sync"]
    assert current["source_scope"] == "MATCH_WINDOW_PRIMARY_FALLBACK"
    assert current["selected_source"] == "SPORTSDB_FALLBACK"
    assert current["odds_refresh"]["external_calls"] == 2

    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "OLD_MATCH", "sports_pipeline": app_module._build_sports_pipeline_diagnostics(_fallback_run(), {})},
        "2026-09-20T12:15:16+02:00",
        "2026-09-20T12:15:24+02:00",
    )["sports_pipeline"]["current_sync"]
    assert compact["source_scope"] == "MATCH_WINDOW_PRIMARY_FALLBACK"
    assert compact["odds_refresh"]["external_calls"] == 2


def test_partial_primary_with_persisted_rows_is_still_primary_source(app_module):
    payload = _fallback_run()
    payload["fixtures"] = {
        "ok": False,
        "status": "PARTIAL",
        "configured": True,
        "enabled": True,
        "external_calls": 5,
        "fixtures_count": 3,
        "errors": {"provider": "partial response"},
    }
    payload["fallback"] = {"ok": True, "status": "NOT_REQUIRED", "skipped": True, "processed": 0}
    current = app_module._build_sports_pipeline_diagnostics(payload, {})["current_sync"]
    assert current["selected_source"] == "API_FOOTBALL_PRIMARY"
    assert current["api_football_primary"]["fixtures_count"] == 3


def test_partial_fallback_with_persisted_rows_is_still_fallback_source(app_module):
    payload = _fallback_run()
    payload["fallback"] = {
        "ok": False,
        "status": "PARTIAL",
        "processed": 75,
        "errors": ["one league unavailable"],
    }
    current = app_module._build_sports_pipeline_diagnostics(payload, {})["current_sync"]
    assert current["selected_source"] == "SPORTSDB_FALLBACK"
    assert current["sportsdb_fallback"]["processed"] == 75
    assert current["sportsdb_fallback"]["error_present"] is True


def test_reason_code_distinguishes_missing_and_disabled_configuration(app_module):
    assert app_module._sports_stage_reason_code(
        {"ok": False, "sin_key": True, "errors": ["Falta THE_ODDS_API_KEY."]}
    ) == "NOT_CONFIGURED"
    assert app_module._sports_stage_reason_code(
        {"ok": False, "disabled": True, "skipped": True}
    ) == "DISABLED"


def test_api_football_cache_reuse_is_not_claimed_as_new_data(app_module):
    payload = _fallback_run()
    payload["fixtures"] = {
        "ok": True,
        "status": "cache",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
    }
    payload["fallback"] = {"ok": True, "status": "NOT_REQUIRED", "skipped": True, "processed": 0}
    current = app_module._build_sports_pipeline_diagnostics(payload, {})["current_sync"]
    primary = current["api_football_primary"]
    assert current["selected_source"] == "API_FOOTBALL_PRIMARY"
    assert primary["used"] is True
    assert primary["data_contributed"] is False
    assert primary["cache_reused"] is True
    assert primary["external_calls"] == 0


def test_fallback_contribution_survives_compact_and_sanitized_contract(app_module):
    from tools.render_cron_master_tick import sanitized_sports_pipeline
    diagnostics = app_module._build_sports_pipeline_diagnostics(_fallback_run(), {})
    assert diagnostics["current_sync"]["sportsdb_fallback"]["data_contributed"] is True

    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "OLD_MATCH", "sports_pipeline": diagnostics},
        "2026-09-20T12:15:16+02:00",
        "2026-09-20T12:15:24+02:00",
    )["sports_pipeline"]
    assert compact["current_sync"]["sportsdb_fallback"]["data_contributed"] is True

    sanitized = sanitized_sports_pipeline({"sports_pipeline": compact}, "secret-canary")
    assert sanitized["current_sync"]["sportsdb_fallback"]["data_contributed"] is True


def test_ok_true_never_erases_partial_stage_errors(app_module):
    stage = {
        "ok": True,
        "status": "partial",
        "error": "one provider subrequest failed",
    }
    assert app_module._sports_stage_reason_code(stage) == "PROVIDER_ERROR"

    payload = _fallback_run()
    payload["live"] = {
        "ok": True,
        "status": "partial",
        "external_calls": 1,
        "fixtures_count": 0,
        "errors": ["partial live response"],
    }
    payload["odds"] = {
        "ok": True,
        "status": "PARTIAL",
        "external_calls": 14,
        "processed": 0,
        "errors": ["some odds requests failed"],
    }
    current = app_module._build_sports_pipeline_diagnostics(payload, {})["current_sync"]
    assert current["live_refresh"]["ok"] is True
    assert current["live_refresh"]["error_present"] is True
    assert current["live_refresh"]["reason_code"] == "PROVIDER_ERROR"
    assert current["odds_refresh"]["ok"] is True
    assert current["odds_refresh"]["error_present"] is True
    assert current["odds_refresh"]["reason_code"] == "PROVIDER_ERROR"


def test_ok_true_with_specific_error_keeps_specific_reason(app_module):
    assert app_module._sports_stage_reason_code({
        "ok": True,
        "errors": ["HTTP 429 rate limit while partial data was retained"],
    }) == "RATE_OR_QUOTA"
    assert app_module._sports_stage_reason_code({
        "ok": True,
        "errors": ["connection timed out after partial data"],
    }) == "NETWORK_OR_TIMEOUT"
