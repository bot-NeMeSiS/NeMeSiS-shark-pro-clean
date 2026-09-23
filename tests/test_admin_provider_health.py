"""Provider-health admin contracts: persisted evidence only, no provider calls."""
import app as app_module


def _state(key, default=None, max_bytes=64 * 1024):
    if key == "telegram_tick_last_detail":
        return {
            "compact": {
                "sports_pipeline": {
                    "status": "PARTIAL",
                    "provider_access_freshness": "LAST_OBSERVED_NOT_CURRENT",
                    "provider_access": {
                        "provider": "API-Football",
                        "state": "ACCESS_FAILED",
                        "configured": True,
                        "authenticated": False,
                        "checked_at": "2026-09-10T22:20:23+00:00",
                        "freshness": "LAST_OBSERVED_NOT_CURRENT",
                    },
                    "provider_plan_observation": {
                        "state": "UNKNOWN",
                        "value": None,
                        "observed_at": "",
                    },
                    "quota_observation": {
                        "state": "OBSERVED",
                        "observed_at": "2026-09-10T22:20:23+00:00",
                        "values": {
                            "daily_limit": 100,
                            "daily_remaining": 99,
                            "minute_limit": 10,
                            "minute_remaining": 9,
                        },
                    },
                    "job_execution": {
                        "finished_at": "2026-09-23T18:50:54+02:00",
                        "processed": 180,
                        "external_calls": 6,
                    },
                    "current_sync": {
                        "selected_source": "SPORTSDB_FALLBACK",
                        "api_football_primary": {
                            "state": "CACHE_PROVIDER_FAILURE_FREE_PLAN_RESTRICTED",
                            "reason_code": "CACHED_PROVIDER_ERROR",
                            "configured": True,
                            "enabled": True,
                            "ok": False,
                            "data_contributed": False,
                            "fixtures_count": 0,
                            "external_calls": 0,
                        },
                        "sportsdb_fallback": {
                            "state": "UNKNOWN",
                            "ok": True,
                            "data_contributed": True,
                            "processed": 180,
                            "external_calls": 6,
                        },
                        "odds_refresh": {
                            "state": "CACHE_REUSED",
                            "reason_code": "NONE",
                            "ok": True,
                            "processed": 0,
                            "external_calls": 0,
                        },
                    },
                }
            }
        }
    return default


def test_provider_health_surfaces_restricted_primary_and_real_fallback(monkeypatch):
    monkeypatch.setattr(app_module, "automation_get_bounded", _state)
    monkeypatch.setattr(
        app_module,
        "env_present",
        lambda key: key in {"API_FOOTBALL_KEY", "THE_ODDS_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"},
    )

    result = app_module.v945_provider_health_snapshot()
    providers = {item["key"]: item for item in result["providers"]}

    assert result["provider_calls_during_render"] == 0
    assert result["source"] == "PERSISTED_CRON_EVIDENCE"
    assert result["selected_source"] == "SPORTSDB_FALLBACK"

    primary = providers["api_football"]
    assert primary["configured"] is True
    assert primary["status"] == "REVISAR_PLAN_ACCESO"
    assert primary["authenticated"] is False
    assert primary["quota"]["daily_remaining"] == 99
    assert "suscripción" in primary["next_action"].lower()

    fallback = providers["sportsdb"]
    assert fallback["configured"] is False
    assert fallback["status"] == "OPERATIVA_FALLBACK"
    assert fallback["data_contributed"] is True
    assert fallback["processed"] == 180

    odds = providers["the_odds"]
    assert odds["configured"] is True
    assert odds["status"] == "CACHE"
    assert "no verificable" in odds["billing_status"].lower()


def test_provider_health_never_equates_configured_with_paid(monkeypatch):
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda *a, **kw: {})
    monkeypatch.setattr(app_module, "env_present", lambda key: key in {"THE_ODDS_API_KEY", "STRIPE_SECRET_KEY"})

    result = app_module.v945_provider_health_snapshot()
    providers = {item["key"]: item for item in result["providers"]}

    assert providers["the_odds"]["configured"] is True
    assert providers["the_odds"]["status"] == "SIN_VERIFICACION_RECIENTE"
    assert "no verificable" in providers["the_odds"]["billing_status"].lower()
    assert "Configurado no equivale a pagado" in result["external_services"]["note"]


def test_provider_health_missing_credentials_is_explicit(monkeypatch):
    monkeypatch.setattr(app_module, "automation_get_bounded", lambda *a, **kw: {})
    monkeypatch.setattr(app_module, "env_present", lambda *_a, **_kw: False)

    result = app_module.v945_provider_health_snapshot()
    providers = {item["key"]: item for item in result["providers"]}

    assert providers["api_football"]["status"] == "NO_CONFIGURADA"
    assert providers["the_odds"]["status"] == "NO_CONFIGURADA"
    assert result["has_alerts"] is True
    assert result["provider_calls_during_render"] == 0
