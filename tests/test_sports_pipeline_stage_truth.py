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
        "failure_class": "",
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
    payload = _fallback_run()
    payload["fallback"].update({
        "external_calls": 2,
        "stale_reconciliation_candidates": 3,
        "stale_reconciliation_observed": 2,
    })
    diagnostics = app_module._build_sports_pipeline_diagnostics(payload, {})
    fallback = diagnostics["current_sync"]["sportsdb_fallback"]
    assert fallback["data_contributed"] is True
    assert fallback["external_calls"] == 2
    assert fallback["stale_reconciliation_candidates"] == 3
    assert fallback["stale_reconciliation_observed"] == 2

    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "OLD_MATCH", "sports_pipeline": diagnostics},
        "2026-09-20T12:15:16+02:00",
        "2026-09-20T12:15:24+02:00",
    )["sports_pipeline"]
    compact_fallback = compact["current_sync"]["sportsdb_fallback"]
    assert compact_fallback["data_contributed"] is True
    assert compact_fallback["external_calls"] == 2
    assert compact_fallback["stale_reconciliation_candidates"] == 3
    assert compact_fallback["stale_reconciliation_observed"] == 2

    sanitized = sanitized_sports_pipeline({"sports_pipeline": compact}, "secret-canary")
    sanitized_fallback = sanitized["current_sync"]["sportsdb_fallback"]
    assert sanitized_fallback["data_contributed"] is True
    assert sanitized_fallback["external_calls"] == 2
    assert sanitized_fallback["stale_reconciliation_candidates"] == 3
    assert sanitized_fallback["stale_reconciliation_observed"] == 2


def test_ok_true_with_errors_keeps_specific_stage_reason(app_module):
    assert app_module._sports_stage_reason_code({
        "ok": True,
        "status": "partial",
        "errors": ["HTTP 429 rate limit after partial data"],
    }) == "RATE_OR_QUOTA"
    assert app_module._sports_stage_reason_code({
        "ok": True,
        "status": "partial",
        "error": "connection timed out after partial data",
    }) == "NETWORK_OR_TIMEOUT"
    assert app_module._sports_stage_reason_code({
        "ok": True,
        "status": "partial",
        "errors": ["one provider subrequest failed"],
    }) == "PROVIDER_ERROR"
    assert app_module._sports_stage_reason_code({
        "ok": True,
        "status": "OK",
        "errors": [],
    }) == "NONE"


def test_sports_cycle_totals_all_external_provider_calls(app_module, monkeypatch):
    stages = {
        "api_football_match_window": {
            "ok": False,
            "status": "ERROR",
            "external_calls": 2,
            "processed": 0,
        },
        "sportsdb_calendar": {
            "ok": True,
            "status": "OK",
            "external_calls": 1,
            "processed": 180,
        },
        "api_football_live_tracker": {
            "ok": True,
            "status": "partial",
            "external_calls": 1,
            "fixtures_count": 0,
            "errors": ["partial live response"],
        },
        "api_football_deep_enrichment": {
            "ok": True,
            "status": "OK",
            "external_calls": 3,
            "processed": 1,
        },
        "odds": {
            "ok": True,
            "status": "PARTIAL",
            "external_calls": 14,
            "processed": 0,
            "errors": ["some odds requests failed"],
        },
        "pick_grading": {
            "ok": True,
            "status": "OK",
            "processed": 0,
        },
    }

    monkeypatch.setattr(
        app_module,
        "_safe_sports_sync_call",
        lambda label, *_args, **_kwargs: dict(stages[label]),
    )
    monkeypatch.setattr(
        app_module,
        "sports_sync_window_state",
        lambda: {"live_refresh_required": True},
    )
    monkeypatch.setattr(app_module, "_api_football_deep_enrichment_candidates", lambda limit=1: [])
    monkeypatch.setattr(app_module, "invalidate_v934_realtime_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module, "automation_safe_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module, "has_request_context", lambda: False)

    result = app_module.run_sports_sync_cycle(force=False, trigger_type="pytest")

    assert result["ok"] is True
    assert result["status"] == "PARTIAL"
    assert result["external_calls"] == 21
    assert any(str(item).startswith("odds_PARTIAL") for item in result["errors"])
    assert any(str(item).startswith("live_partial") for item in result["errors"])


def test_zero_call_configured_failure_is_local_not_provider(app_module):
    stage = {
        "ok": False,
        "status": "ERROR",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
        "error": "api_football_match_window_OperationalError",
    }
    assert app_module._sports_stage_reason_code(stage) == "LOCAL_DB_OR_SCHEMA"


def test_zero_call_unknown_failure_is_pre_call_runtime(app_module):
    stage = {
        "ok": False,
        "status": "ERROR",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
        "error": "api_football_match_window_RuntimeError",
    }
    assert app_module._sports_stage_reason_code(stage) == "LOCAL_PRECALL_ERROR"


def test_provider_failure_after_real_call_keeps_provider_reason(app_module):
    stage = {
        "ok": False,
        "status": "PARTIAL",
        "configured": True,
        "enabled": True,
        "external_calls": 1,
        "errors": ["provider response rejected"],
    }
    assert app_module._sports_stage_reason_code(stage) == "PROVIDER_ERROR"


def test_pre_call_failure_class_exposes_only_internal_exception_label(app_module):
    stage = {
        "ok": False,
        "status": "ERROR",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
        "error": "api_football_match_window_RuntimeError",
    }
    diagnostics = app_module._build_sports_pipeline_diagnostics({"fixtures": stage}, {})
    primary = diagnostics["current_sync"]["api_football_primary"]
    assert primary["reason_code"] == "LOCAL_PRECALL_ERROR"
    assert primary["failure_class"] == "RuntimeError"


def test_provider_error_text_is_never_exposed_as_failure_class(app_module):
    stage = {
        "ok": False,
        "status": "PARTIAL",
        "configured": True,
        "enabled": True,
        "external_calls": 1,
        "error": "provider says secret=CANARY",
    }
    diagnostics = app_module._build_sports_pipeline_diagnostics({"fixtures": stage}, {})
    primary = diagnostics["current_sync"]["api_football_primary"]
    assert primary["reason_code"] == "PROVIDER_ERROR"
    assert primary["failure_class"] == ""


def test_wrong_internal_prefix_is_not_exposed(app_module):
    stage = {
        "ok": False,
        "status": "ERROR",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
        "error": "different_stage_RuntimeError",
    }
    diagnostics = app_module._build_sports_pipeline_diagnostics({"fixtures": stage}, {})
    primary = diagnostics["current_sync"]["api_football_primary"]
    assert primary["failure_class"] == ""


def test_safe_failure_class_survives_compact_and_master_cron_sanitizer(app_module):
    from tools.render_cron_master_tick import sanitized_sports_pipeline

    payload = _fallback_run()
    payload["fixtures"] = {
        "ok": False,
        "status": "ERROR",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
        "fixtures_count": 0,
        "error": "api_football_match_window_RuntimeError",
    }
    diagnostics = app_module._build_sports_pipeline_diagnostics(payload, {})
    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "OLD_MATCH", "sports_pipeline": diagnostics},
        "2026-09-20T14:55:21+02:00",
        "2026-09-20T14:55:27+02:00",
    )["sports_pipeline"]
    assert compact["current_sync"]["api_football_primary"]["reason_code"] == "LOCAL_PRECALL_ERROR"
    assert compact["current_sync"]["api_football_primary"]["failure_class"] == "RuntimeError"

    sanitized = sanitized_sports_pipeline({"sports_pipeline": compact}, "secret-canary")
    primary = sanitized["current_sync"]["api_football_primary"]
    assert primary["reason_code"] == "LOCAL_PRECALL_ERROR"
    assert primary["failure_class"] == "RuntimeError"
    assert "api_football_match_window_RuntimeError" not in str(sanitized)
    assert "secret-canary" not in str(sanitized)

def test_cached_provider_failure_is_not_reclassified_as_local_precall(app_module):
    stage = {
        "ok": False,
        "status": "CACHE_PROVIDER_FAILURE",
        "configured": True,
        "enabled": True,
        "external_calls": 0,
        "cached_provider_failure": True,
        "cached_from_status": "PARTIAL",
        "error": "cached_provider_failure",
    }
    assert app_module._sports_stage_reason_code(stage) == "CACHED_PROVIDER_ERROR"
    diagnostics = app_module._build_sports_pipeline_diagnostics({"fixtures": stage}, {})
    primary = diagnostics["current_sync"]["api_football_primary"]
    assert primary["reason_code"] == "CACHED_PROVIDER_ERROR"
    assert primary["failure_class"] == ""

