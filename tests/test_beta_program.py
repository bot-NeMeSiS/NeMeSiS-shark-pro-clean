from __future__ import annotations

import re
import sqlite3

from engines.beta_program_engine import (
    BETA_METRICS_CONTRACT,
    BETA_PROGRAM_CONTRACT,
    FEEDBACK_PLATFORM_CONTRACT,
    build_beta_program_snapshot,
    sanitize_beta_feedback_payload,
)


def test_beta_snapshot_contracts_and_metric_transparency():
    snapshot = build_beta_program_snapshot(
        counts={
            "feedback_total": 3,
            "bug_total": 1,
            "feature_total": 1,
            "satisfaction_count": 1,
            "metrics_enabled": 2,
            "metrics_disabled": 1,
            "open_items": 1,
            "satisfaction_average": 4.0,
        },
        source_contracts={"user_intelligence": "USER-INTELLIGENCE-PLATFORM-V1"},
    )

    assert snapshot["contract"] == BETA_PROGRAM_CONTRACT
    assert snapshot["feedback_contract"] == FEEDBACK_PLATFORM_CONTRACT
    assert snapshot["metrics_contract"] == BETA_METRICS_CONTRACT
    assert snapshot["privacy_controls"]["stores_sensitive_information"] is False
    assert snapshot["privacy_controls"]["metrics_can_be_disabled_per_submission"] is True
    assert snapshot["privacy_controls"]["external_calls"] == 0
    assert all(metric["source"] and metric["definition"] and metric["limitation"] for metric in snapshot["metrics"])
    assert all(metric["user_disable_supported"] is True for metric in snapshot["metrics"])


def test_beta_sanitizer_rejects_sensitive_text_and_keeps_user_pseudonymous():
    payload, errors = sanitize_beta_feedback_payload(
        {
            "feedback_type": "general",
            "category": "home",
            "severity": "medium",
            "title": "Necesito ayuda",
            "message": "Mi correo es tester@example.com",
        },
        {"id": "real-user-id", "email": "person@example.invalid"},
    )

    assert errors
    assert payload["user_ref"].startswith("usr_")
    assert "real-user-id" not in payload["user_ref"]
    assert "person" not in payload["user_ref"]


def test_beta_bug_report_requires_reproduction_fields():
    payload, errors = sanitize_beta_feedback_payload(
        {
            "feedback_type": "bug",
            "category": "match_center",
            "severity": "high",
            "title": "Pantalla bloqueada",
            "message": "No puedo continuar.",
        },
        {"id": "user-qa"},
    )

    assert payload["feedback_type"] == "bug"
    joined = " ".join(errors).lower()
    assert "pasos" in joined
    assert "esperado" in joined
    assert "real" in joined


def test_beta_satisfaction_score_and_metric_consent():
    payload, errors = sanitize_beta_feedback_payload(
        {
            "feedback_type": "satisfaction",
            "category": "home",
            "severity": "low",
            "title": "Me queda claro",
            "message": "La experiencia se entiende mejor.",
            "satisfaction_score": "5",
            "allow_beta_metrics": "on",
        },
        {"id": "user-qa"},
    )

    assert errors == []
    assert payload["satisfaction_score"] == 5
    assert payload["allow_beta_metrics"] is True


def test_beta_public_page_renders_without_sensitive_inputs(client):
    response = client.get("/beta")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "data-beta-program-contract" in html
    assert "name=\"email\"" not in html.lower()
    assert "name=\"phone\"" not in html.lower()
    assert "allow_beta_metrics" in html


def test_beta_submit_valid_bug_writes_only_beta_feedback(app_module, client):
    app_module.ensure_beta_feedback_schema()
    conn = sqlite3.connect(app_module.DB_PATH)
    try:
        conn.execute("DELETE FROM beta_feedback")
        conn.commit()
    finally:
        conn.close()

    page = client.get("/beta")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)).group(1)
    response = client.post(
        "/beta/feedback",
        data={
            "csrf_token": token,
            "feedback_type": "bug",
            "category": "calendar",
            "severity": "medium",
            "device_context": "mobile",
            "route": "/calendar?x=1",
            "title": "No encuentro un partido",
            "message": "La lista es larga y pierdo el contexto.",
            "steps_to_reproduce": "Abrir calendario y bajar hasta el final.",
            "expected_result": "Mantener contexto visible.",
            "actual_result": "Pierdo el filtro al hacer scroll.",
            "allow_beta_metrics": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/beta?sent=1")
    conn = sqlite3.connect(app_module.DB_PATH)
    try:
        row = conn.execute("SELECT feedback_type, category, allow_beta_metrics, route FROM beta_feedback").fetchone()
    finally:
        conn.close()
    assert row == ("bug", "calendar", 1, "/calendar")


def test_admin_beta_center_is_protected_and_renders_for_admin(client):
    blocked = client.get("/admin/beta-center")
    assert blocked.status_code == 302
    assert "/admin-login" in blocked.headers["Location"]

    with client.session_transaction() as sess:
        sess["user_role"] = "ADMIN"
        sess["user_id"] = "admin-qa"
        sess["user_name"] = "Admin QA"
        sess["membership"] = "ADMIN"

    response = client.get("/admin/beta-center")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "data-beta-program-contract" in html
    assert "Beta Metrics" in html
