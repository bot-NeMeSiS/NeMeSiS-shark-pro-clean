from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1"


def _sample_snapshot() -> dict:
    meta = {
        "provenance": "test",
        "source": "test",
        "evidence": ["evidence"],
        "freshness": "2026-07-28T12:00:00+02:00",
        "quality": "VERIFIED",
        "limitations": ["No predicciones."],
    }
    sections = {}
    for key in [
        "smart_home",
        "smart_favorites",
        "watchlist",
        "alert_center",
        "daily_briefing",
        "evening_recap",
        "activity_center",
        "decision_history",
    ]:
        sections[key] = {
            "items": [
                {
                    "title": key,
                    "body": "Dato con evidencia.",
                    "href": "/calendar",
                    "badge": "QA",
                    "value": 1,
                    "meta": dict(meta),
                }
            ],
            "meta": dict(meta),
        }
    return {
        "contract": CONTRACT,
        "version": "TEST",
        "observed_at_madrid": "2026-07-28T12:00:00+02:00",
        "certification_state": "PARTIALLY_VERIFIED",
        "membership": "PRO",
        "user_present": True,
        "sections": sections,
        "section_nav": {
            "smart_home": {"title": "Smart Home", "route": "/smart-home", "goal": "Inicio personal."},
            "smart_favorites": {"title": "Smart Favorites", "route": "/smart-favorites", "goal": "Favoritos."},
            "watchlist": {"title": "Watchlist", "route": "/watchlist", "goal": "Seguimiento."},
            "alert_center": {"title": "Alert Center", "route": "/alert-center", "goal": "Alertas."},
            "daily_briefing": {"title": "Daily Briefing", "route": "/daily-briefing", "goal": "Briefing."},
            "evening_recap": {"title": "Evening Recap", "route": "/evening-recap", "goal": "Recap."},
            "activity_center": {"title": "Activity Center", "route": "/activity-center", "goal": "Actividad."},
            "decision_history": {"title": "Decision History", "route": "/decision-history", "goal": "Decision."},
        },
        "next_action": {"title": "Continuar", "body": "Abrir calendario.", "href": "/calendar", "meta": dict(meta)},
        "summary": {"body": "Resumen", "sections": 8, "favorites": 1, "watchlist": 1, "alerts": 1, "activity": 1},
        "source_contracts": {
            "sports_core": "sports-metrics-v1",
            "decision_engine": "NEMESIS-DECISION-ENGINE-EVIDENCE-FIRST-V1",
            "shark": "SHARK-INTELLIGENCE-PLATFORM-V1",
            "user_intelligence": "USER-INTELLIGENCE-PLATFORM-V1",
            "gateway": "SPORTS-INTELLIGENCE-GATEWAY-V1",
        },
        "transparency": {"all_sections_have_metadata": True},
        "guardrails": {
            "external_calls": 0,
            "database_writes_by_get": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "predictions_created": 0,
            "picks_created": 0,
            "betting_recommendations_created": 0,
            "automatic_user_decisions": 0,
        },
        "privacy": {"first_party_only": True, "user_control": True},
        "limitaciones": ["Produccion no certificada."],
    }


def _patch_read_only_inputs(monkeypatch, app_module):
    user = {"id": "qa-user", "membership": "PRO", "role": "PRO"}
    monkeypatch.setattr(app_module, "now_iso", lambda: "2026-07-28T12:00:00+02:00")
    monkeypatch.setattr(app_module, "today_iso", lambda: "2026-07-28")
    monkeypatch.setattr(app_module, "_load_user_intelligence_preferences", lambda _user_id: {"personalization_enabled": True, "consent_state": "GRANTED"})
    monkeypatch.setattr(app_module, "get_favorites", lambda user_id=None, kind=None: [{"kind": "team", "value": "club-norte", "label": "Club Norte"}])
    monkeypatch.setattr(app_module, "favorite_feed_full", lambda limit=40, user_id=None: {"matches": [], "live": [], "picks": [], "priority": [{"id": "m1", "home_team": "Club Norte", "away_team": "Club Sur", "competition_name": "Liga Real", "match_date": "2026-07-28"}]})
    monkeypatch.setattr(app_module, "favorite_insights", lambda user_id=None: {"favorites": [{"kind": "team"}], "by_kind": {"team": [{"label": "Club Norte"}], "league": [], "match": []}, "summary": "1 equipo", "total": 1})
    monkeypatch.setattr(app_module, "client_activity_feed", lambda limit=40, user_id=None: [{"activity_type": "view", "target_type": "match", "target_id": "m1", "created_at": "2026-07-28T11:00:00+02:00", "label": "Partido consultado."}])
    monkeypatch.setattr(app_module, "build_client_alerts", lambda limit=10, user_id=None: [{"type": "match", "priority": 70, "href": "/match/m1", "badge": "MATCH"}])
    monkeypatch.setattr(app_module, "build_daily_briefing", lambda user=None, favorites=None: {"counts": {"today": 1, "upcoming": 1, "live": 0, "favorites": 1, "picks": 0}, "upcoming": [{"id": "m1", "home_team": "Club Norte", "away_team": "Club Sur", "competition_name": "Liga Real"}], "today_matches": [], "live": [], "picks": []})
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: {"source": "qa", "last_sync": "2026-07-28T11:50:00+02:00"})
    monkeypatch.setattr(app_module, "get_sports_metrics_contract", lambda summary: {"contract": "sports-metrics-v1", "matches_available": 1, "live_confirmed": 0, "picks_ready": 0, "last_sync": summary.get("last_sync")})
    return user


def test_action_platform_snapshot_reuses_existing_engines_without_side_effects(app_module, monkeypatch):
    user = _patch_read_only_inputs(monkeypatch, app_module)
    snapshot = app_module.build_action_platform_snapshot(user)

    assert snapshot["contract"] == CONTRACT
    assert set(snapshot["sections"]) == {
        "smart_home",
        "smart_favorites",
        "watchlist",
        "alert_center",
        "daily_briefing",
        "evening_recap",
        "activity_center",
        "decision_history",
    }
    for section in snapshot["sections"].values():
        assert section["meta"]["provenance"]
        assert section["meta"]["evidence"]
        assert section["meta"]["freshness"]
        assert section["meta"]["quality"]
        assert section["meta"]["limitations"]
    assert snapshot["guardrails"]["external_calls"] == 0
    assert snapshot["guardrails"]["database_writes_by_get"] == 0
    assert snapshot["guardrails"]["telegram_sends"] == 0
    assert snapshot["guardrails"]["stripe_calls"] == 0
    assert snapshot["guardrails"]["generative_ai_calls"] == 0
    assert snapshot["guardrails"]["predictions_created"] == 0
    assert snapshot["guardrails"]["betting_recommendations_created"] == 0
    assert snapshot["privacy"]["first_party_only"] is True
    assert snapshot["source_contracts"]["decision_engine"] == "NEMESIS-DECISION-ENGINE-EVIDENCE-FIRST-V1"


def test_action_platform_routes_are_session_protected(client, app_module, monkeypatch):
    assert client.get("/smart-home").status_code == 302
    assert client.get("/api/action-platform/summary").status_code == 401

    user = {"id": "qa-user", "membership": "PRO", "role": "PRO"}
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(app_module, "build_action_platform_snapshot", lambda user=None: _sample_snapshot())

    page = client.get("/smart-home")
    api = client.get("/api/action-platform/summary")

    assert page.status_code == 200
    assert "Plataforma de acciones".encode("utf-8") in page.data
    assert b"Procedencia" in page.data
    assert b"Evidencia" in page.data
    assert api.status_code == 200
    assert api.get_json()["action_platform"]["contract"] == CONTRACT


def test_action_platform_registry_roadmap_sentinel_and_files_are_canonical():
    import engines.project_operating_system_engine as os_engine
    from engines.sentinel_autopilot_engine import build_action_platform_contract_snapshot
    from engines.sports_platform_contracts import build_sports_platform_contract_registry

    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    roadmap = {item["name"]: item for item in os_engine.build_product_roadmap(ROOT)["modules"]}
    sentinel = build_action_platform_contract_snapshot(ROOT, "TEST")
    template = (ROOT / "templates" / "action_platform.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")

    assert not (ROOT / "engines" / "action_platform_engine.py").exists()
    assert capabilities["action_platform"]["state"] == "INTEGRATED"
    assert capabilities["action_platform"]["implementation"] == "app.py + templates/action_platform.html + tools/check_action_platform.py"
    assert roadmap["Action Platform"]["state"] == "COMPLETED"
    assert sentinel["validation_result"] == "PASS"
    assert sentinel["evidence"]["violations"] == []
    assert "data-action-platform-contract" in template
    assert "No hay recomendaciones de apuestas ni predicciones nuevas." in template
    assert "ACTION PLATFORM V1" in css