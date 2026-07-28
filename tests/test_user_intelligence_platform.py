from __future__ import annotations

import ast
import inspect
from pathlib import Path

import engines.user_intelligence_platform_engine as user_platform_module
from engines.sentinel_autopilot_engine import build_user_intelligence_platform_contract_snapshot
from engines.user_intelligence_platform_engine import (
    USER_INTELLIGENCE_PLATFORM_CONTRACT,
    USER_INTELLIGENCE_PRIVACY_CONTRACT,
    build_user_intelligence_platform_snapshot,
    default_user_intelligence_preferences,
    sanitize_user_intelligence_preferences,
    user_intelligence_platform_snapshot,
)
from engines.sports_platform_contracts import build_sports_platform_contract_registry

ROOT = Path(__file__).resolve().parents[1]


def _activity() -> list[dict]:
    return [
        {
            "activity_type": "view",
            "target_type": "match",
            "target_id": "match-1",
            "payload": {
                "match_title": "Club Norte vs Club Sur",
                "home_team": "Club Norte",
                "away_team": "Club Sur",
                "competition_name": "Liga Real",
                "lane": "today",
            },
            "created_at": "2026-07-28T21:00:00+02:00",
        },
        {
            "activity_type": "view",
            "target_type": "team",
            "target_id": "club-norte",
            "payload": {"team_name": "Club Norte"},
            "created_at": "2026-07-28T21:04:00+02:00",
        },
        {
            "activity_type": "view",
            "target_type": "competition",
            "target_id": "liga-real",
            "payload": {"competition_name": "Liga Real"},
            "created_at": "2026-07-28T21:06:00+02:00",
        },
    ]


def _favorites() -> list[dict]:
    return [
        {"kind": "team", "value": "club-norte", "label": "Club Norte", "created_at": "2026-07-28T20:00:00+02:00"},
        {"kind": "league", "value": "liga-real", "label": "Liga Real", "created_at": "2026-07-28T20:01:00+02:00"},
    ]


def test_user_intelligence_builds_transparent_first_party_profile():
    preferences = sanitize_user_intelligence_preferences(
        default_user_intelligence_preferences(),
        {"remember_filters": True},
        action="enable",
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )
    snapshot = build_user_intelligence_platform_snapshot(
        user={"id": "usr-test", "membership": "PRO", "email": "hidden@example.invalid", "name": "Hidden"},
        activity=_activity(),
        favorites=_favorites(),
        preferences=preferences,
        shark_intelligence={"contract": "SHARK-INTELLIGENCE-PLATFORM-V1"},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )

    assert snapshot["contract"] == USER_INTELLIGENCE_PLATFORM_CONTRACT
    assert snapshot["privacy_contract"] == USER_INTELLIGENCE_PRIVACY_CONTRACT
    assert snapshot["transparent"] is True
    assert snapshot["user_controlled"] is True
    assert snapshot["no_generative_ai"] is True
    assert snapshot["no_fake_data"] is True
    assert snapshot["diagnostics"]["external_calls"] == 0
    assert snapshot["diagnostics"]["telegram_sends"] == 0
    assert snapshot["diagnostics"]["stripe_calls"] == 0
    assert snapshot["diagnostics"]["database_writes_by_get"] == 0
    assert snapshot["privacy"]["data_leaves_nemesis"] is False
    assert snapshot["privacy"]["third_party_sale"] is False
    assert snapshot["privacy"]["controls"]["delete_profile"] is True
    assert snapshot["personalization"]["automatic_home_personalization"] is False
    assert snapshot["user_context"]["email_included"] is False
    assert snapshot["user_context"]["name_included"] is False
    assert snapshot["signals"]["teams"][0]["label"] == "Club Norte"
    assert snapshot["signals"]["competitions"][0]["label"] == "Liga Real"
    assert snapshot["recommendations"]


def test_user_intelligence_requires_consent_before_personalization():
    snapshot = build_user_intelligence_platform_snapshot(
        user={"id": "usr-test", "membership": "FREE"},
        activity=_activity(),
        favorites=_favorites(),
        preferences=default_user_intelligence_preferences(),
        shark_intelligence={"contract": "SHARK-INTELLIGENCE-PLATFORM-V1"},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )

    assert snapshot["certification_state"] == "NOT_CONFIGURED"
    assert snapshot["personalization"]["enabled"] is False
    assert snapshot["personalization"]["blocked_without_consent"] is True
    assert "La personalizacion no esta activada por consentimiento." in snapshot["missing_information"]


def test_user_intelligence_registry_template_and_sentinel_pass():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "user_intelligence_center.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    sentinel = build_user_intelligence_platform_contract_snapshot(ROOT, "TEST")

    assert capabilities["user_intelligence_platform"]["state"] == "INTEGRATED"
    assert capabilities["user_intelligence_platform"]["contract"] == USER_INTELLIGENCE_PLATFORM_CONTRACT
    assert "data-user-intelligence-contract" in template
    assert "data-user-privacy-contract" in template
    assert "data-user-intelligence-section=\"privacy\"" in template
    assert "Borrar perfil" in template
    assert "USER INTELLIGENCE PLATFORM V1" in css
    assert sentinel["validation_result"] == "PASS"
    assert sentinel["evidence"]["violations"] == []


def test_user_intelligence_engine_is_pure_and_guarded():
    source = inspect.getsource(user_platform_module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert {"sqlite3", "requests", "urllib", "flask", "stripe", "openai"} & imported_roots == set()
    assert "TELEGRAM_BOT_TOKEN" not in source
    assert "STRIPE_SECRET_KEY" not in source
    assert "OPENAI_API_KEY" not in source
    metadata = user_intelligence_platform_snapshot()
    assert metadata["guardrails"]["external_calls"] == 0
    assert metadata["guardrails"]["telegram_sends"] == 0
    assert metadata["guardrails"]["stripe_calls"] == 0
    assert metadata["guardrails"]["generative_ai_calls"] == 0
    assert metadata["privacy_controls"]["delete_profile"] is True


def test_user_intelligence_routes_are_session_protected(client, app_module, monkeypatch):
    assert client.get("/api/user-intelligence/summary").status_code == 401
    assert client.get("/api/user-intelligence/export").status_code == 401
    assert client.get("/user-intelligence").status_code == 302

    snapshot = build_user_intelligence_platform_snapshot(
        user={"id": "qa-user", "membership": "PRO"},
        activity=_activity(),
        favorites=_favorites(),
        preferences=sanitize_user_intelligence_preferences(action="enable"),
        shark_intelligence={"contract": "SHARK-INTELLIGENCE-PLATFORM-V1"},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )
    monkeypatch.setattr(app_module, "build_user_intelligence_page_context", lambda user=None: snapshot)
    monkeypatch.setattr(app_module, "_user_intelligence_export_payload", lambda user: {"contract": USER_INTELLIGENCE_PLATFORM_CONTRACT})
    saved_actions: list[str] = []
    monkeypatch.setattr(app_module, "_load_user_intelligence_preferences", lambda _user_id: {})
    monkeypatch.setattr(
        app_module,
        "_save_user_intelligence_preferences",
        lambda _user, prefs, action="update": saved_actions.append(action) or {"ok": True, "preferences": prefs},
    )
    monkeypatch.setattr(app_module, "_delete_user_intelligence_profile", lambda _user_id, clear_history=False: {"ok": True, "history_deleted": clear_history})

    with client.session_transaction() as session:
        session["user_id"] = "qa-user"
        session["user_name"] = "Cliente QA"
        session["user_email"] = "qa@example.invalid"
        session["user_role"] = "PRO"
        session["user_membership"] = "PRO"
        session["membership"] = "PRO"
        session["csrf_token"] = "csrf-user-intelligence-test"

    headers = {"X-CSRF-Token": "csrf-user-intelligence-test"}
    summary = client.get("/api/user-intelligence/summary")
    export = client.get("/api/user-intelligence/export")
    enable = client.post("/api/user-intelligence/preferences", json={"action": "enable"}, headers=headers)
    delete = client.delete("/api/user-intelligence/profile", json={"clear_history": True}, headers=headers)

    assert summary.status_code == 200
    assert summary.get_json()["user_intelligence"]["contract"] == USER_INTELLIGENCE_PLATFORM_CONTRACT
    assert export.status_code == 200
    assert export.get_json()["export"]["contract"] == USER_INTELLIGENCE_PLATFORM_CONTRACT
    assert enable.status_code == 200
    assert saved_actions == ["enable"]
    assert delete.status_code == 200
    assert delete.get_json()["history_deleted"] is True
