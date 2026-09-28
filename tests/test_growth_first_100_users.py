from __future__ import annotations

import json
import uuid
from pathlib import Path

from engines.growth_revenue_os_engine import (
    GROWTH_FUNNEL_EVENT_CONTRACT,
    build_growth_funnel_event,
    normalize_growth_attribution,
)


ROOT = Path(__file__).resolve().parents[1]


def test_attribution_is_minimal_allowlisted_and_session_safe():
    attribution = normalize_growth_attribution(
        {
            "utm_source": "Instagram<script>",
            "utm_medium": "social",
            "utm_campaign": "FIRST_10_USERS/../../secret",
            "ref": "invite-01",
        }
    )

    assert attribution["channel"] == "REFERRAL"
    assert attribution["campaign_id"].startswith("FIRST_10_USERS")
    assert "/" not in attribution["campaign_id"]
    assert attribution["privacy"] == {
        "full_url_stored": False,
        "ip_stored": False,
        "user_agent_stored": False,
        "fingerprint_used": False,
        "pii_stored": False,
    }

    event = build_growth_funnel_event(
        "LANDING",
        target_id="public-home",
        attribution=attribution,
        authenticated=False,
        analytics_consent=False,
        occurred_at_madrid="2026-08-12T10:00:00+02:00",
    )
    assert event["contract"] == GROWTH_FUNNEL_EVENT_CONTRACT
    assert event["anonymous_session_only"] is True
    assert event["persistence_allowed"] is False


def test_public_landing_event_remains_session_only(client):
    response = client.get(
        "/landing?utm_source=instagram&utm_medium=social&utm_campaign=FIRST_10_USERS"
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-growth-stage="LANDING"' in html
    assert 'rel="canonical"' in html
    assert 'name="description"' in html
    assert 'application/ld+json' in html
    with client.session_transaction() as state:
        csrf = state["csrf_token"]

    event = client.post(
        "/api/growth/funnel-event",
        json={"stage": "LANDING", "target_id": "company-landing"},
        headers={"X-CSRF-Token": csrf},
    )
    payload = event.get_json()
    assert event.status_code == 202
    assert payload["persisted"] is False
    assert payload["state"] == "SESSION_ONLY"
    with client.session_transaction() as state:
        assert state["growth_attribution"]["channel"] == "INSTAGRAM"
        assert state["growth_attribution"]["campaign_id"] == "FIRST_10_USERS"
        assert state["growth_session_journey"][0]["stage"] == "LANDING"


def test_first_value_and_activation_use_authenticated_first_party_events(client, app_module):
    user_id = "qa-growth-first-100"
    cleanup = app_module.db()
    cleanup.execute("DELETE FROM user_activity WHERE user_id=?", (user_id,))
    cleanup.commit()
    cleanup.close()
    with client.session_transaction() as state:
        state["user_id"] = user_id
        state["user_name"] = "QA Growth"
        state["user_email"] = "qa-growth@example.invalid"
        state["user_role"] = "FREE"
        state["user_membership"] = "FREE"
        state["membership"] = "FREE"
        state["csrf_token"] = "csrf-growth-first-100"
    headers = {"X-CSRF-Token": "csrf-growth-first-100"}

    first = client.post(
        "/api/growth/funnel-event",
        json={"stage": "FIRST_VALUE", "target_id": "match-real-1"},
        headers=headers,
    )
    second = client.post(
        "/api/growth/funnel-event",
        json={"stage": "FIRST_VALUE", "target_id": "match-real-2"},
        headers=headers,
    )

    assert first.status_code == 200
    assert first.get_json()["activation"]["state"] == "NOT_YET_ACTIVATED"
    assert second.status_code == 200
    assert second.get_json()["activation"]["state"] == "RECORDED"

    snapshot = app_module.growth_funnel_analytics_snapshot()
    assert snapshot["simulated_stages"]["FIRST_VALUE"] >= 1
    assert snapshot["simulated_stages"]["ACTIVATED"] >= 1
    rows = app_module.rows(
        "SELECT payload_json FROM user_activity WHERE user_id=? AND target_type='growth_funnel'",
        (user_id,),
    )
    assert rows
    for row in rows:
        payload = json.loads(row["payload_json"])
        payload_text = json.dumps(payload).lower()
        assert "qa-growth@example.invalid" not in payload_text
        assert "ip_address" not in payload_text
        assert payload["privacy"]["user_agent_stored"] is False
        assert payload["privacy"]["ip_stored"] is False
        assert payload["privacy"]["pii_stored"] is False
        assert payload["evidence_origin"] == "SIMULATED_QA"

    conn = app_module.db()
    conn.execute("DELETE FROM user_activity WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def test_first_100_surfaces_and_seo_routes_are_present(client):
    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")
    assert robots.status_code == 200
    assert "Sitemap:" in robots.get_data(as_text=True)
    assert "Disallow: /admin" in robots.get_data(as_text=True)
    assert sitemap.status_code == 200
    assert "<urlset" in sitemap.get_data(as_text=True)
    assert "/landing" in sitemap.get_data(as_text=True)

    match_template = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8")
    membership_template = (ROOT / "templates" / "membership.html").read_text(encoding="utf-8")
    founder_template = (ROOT / "templates" / "admin_founder_dashboard.html").read_text(encoding="utf-8")
    assert 'data-growth-stage="FIRST_VALUE"' in match_template
    assert 'data-growth-stage="PREMIUM_INTENT"' in membership_template
    assert "Primeros " in founder_template
    assert "Que haria hoy para conseguir mas clientes" in founder_template


def test_growth_brief_is_part_of_continuous_evolution_without_mutating_actions():
    source = (ROOT / "engines" / "product_review_system_engine.py").read_text(encoding="utf-8")
    assert '"growth_revenue": growth_snapshot' in source
    assert "Growth:" in source
    assert "Revenue:" in source
    assert "build_growth_revenue_os_snapshot" in source
    assert "automatic_publication" not in source

def test_founder_surfaces_first10_next_action_before_deep_growth_detail():
    founder_template = (ROOT / "templates" / "admin_founder_dashboard.html").read_text(encoding="utf-8")
    assert 'data-first10-founder-today="true"' in founder_template
    assert "FIRST 10 · Tu siguiente acción" in founder_template
    assert "Registrados reales" in founder_template
    assert "Primer valor" in founder_template
    assert "Activados" in founder_template
    assert "Han vuelto" in founder_template
    assert "Invita a una sola persona adecuada." in founder_template
    assert "No invites a otra persona todavía." in founder_template
    assert "Pausa las invitaciones." in founder_template
    assert "SIMULATED_QA no incrementa estos contadores" in founder_template


def test_first10_cohort_is_real_campaign_only_and_links_pseudonymous_feedback(app_module):
    real_uid = "first10-real-" + uuid.uuid4().hex[:10]
    other_uid = "first10-other-" + uuid.uuid4().hex[:10]
    qa_uid = "first10-qa-" + uuid.uuid4().hex[:10]
    user_ids = (real_uid, other_uid, qa_uid)

    def record(uid, stage, *, campaign="", origin="REAL_USER"):
        payload = {
            "evidence_origin": origin,
            "campaign_id": campaign,
            "channel": "REFERRAL",
            "privacy": {"pii_stored": False},
        }
        app_module.record_user_activity(
            app_module.GROWTH_STAGE_ACTIVITY[stage],
            "growth_funnel",
            stage.lower(),
            payload,
            user_id=uid,
        )

    try:
        record(real_uid, "REGISTRATION", campaign="FIRST_10_USERS")
        record(real_uid, "FIRST_VALUE")
        record(real_uid, "ACTIVATED")
        record(real_uid, "RETURNING")

        record(other_uid, "REGISTRATION", campaign="OTHER_CAMPAIGN")
        record(other_uid, "FIRST_VALUE")

        record(qa_uid, "REGISTRATION", campaign="FIRST_10_USERS", origin="SIMULATED_QA")
        record(qa_uid, "FIRST_VALUE", origin="SIMULATED_QA")

        app_module.ensure_beta_feedback_schema()
        payload, errors = app_module.sanitize_beta_feedback_payload(
            {
                "feedback_type": "satisfaction",
                "category": "shark",
                "severity": "low",
                "device_context": "mobile",
                "title": "Primer uso",
                "message": "La experiencia fue clara.",
                "satisfaction_score": "5",
                "allow_beta_metrics": "1",
            },
            {"id": real_uid},
        )
        assert errors == []
        app_module.save_beta_feedback(payload)

        snapshot = app_module.growth_first10_cohort_snapshot(limit=10)
        assert snapshot["campaign_id"] == "FIRST_10_USERS"
        assert snapshot["evidence_origin"] == "REAL_USER_ONLY"
        assert snapshot["count"] == 1
        assert snapshot["feedback_users"] == 1
        assert snapshot["stage_counts"]["REGISTRATION"] == 1
        assert snapshot["stage_counts"]["FIRST_VALUE"] == 1
        assert snapshot["stage_counts"]["ACTIVATED"] == 1
        assert snapshot["stage_counts"]["RETURNING"] == 1
        assert snapshot["premium_access_users"] == 0
        assert snapshot["privacy"]["pii_exposed"] is False

        item = snapshot["items"][0]
        assert item["alias"] == "Beta 01"
        assert item["stage"] == "RETURNING"
        assert item["feedback_count"] == 1
        assert item["satisfaction_score"] == 5
        assert item["action_state"] == "LEARN"
        assert item["user_ref"].startswith("usr_")

        serialized = json.dumps(snapshot, ensure_ascii=False)
        assert real_uid not in serialized
        assert other_uid not in serialized
        assert qa_uid not in serialized
    finally:
        user_ref = app_module.pseudonymized_user_ref({"id": real_uid})
        conn = app_module.db()
        conn.execute(
            "DELETE FROM user_activity WHERE user_id IN (?,?,?) AND target_type='growth_funnel'",
            user_ids,
        )
        if app_module.db_table_exists("beta_feedback"):
            conn.execute("DELETE FROM beta_feedback WHERE user_ref=?", (user_ref,))
        conn.commit()
        conn.close()


def test_first10_founder_template_exposes_cohort_without_pii_columns():
    template = (ROOT / "templates" / "admin_founder_dashboard.html").read_text(encoding="utf-8")
    assert 'data-first10-cohort="true"' in template
    assert "Cohorte FIRST 10 · seguimiento sin PII" in template
    assert "Usuario beta" in template
    assert "Siguiente acción" in template
    assert "email" not in template[template.index('data-first10-cohort="true"'):template.index('data-first10-cohort="true"') + 3000].lower()


def test_first10_registration_form_defaults_to_onboarding_but_paid_checkout_wins(client):
    response = client.get(
        "/registro?utm_source=referral&utm_medium=manual&utm_campaign=FIRST_10_USERS&ref=first10-founder"
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'name="next" value="/onboarding"' in html

    paid = client.get(
        "/registro?plan=PRO&utm_source=referral&utm_medium=manual&utm_campaign=FIRST_10_USERS&ref=first10-founder"
    )
    paid_html = paid.get_data(as_text=True)
    assert paid.status_code == 200
    assert 'name="plan" value="PRO"' in paid_html
    assert "/membresias?plan=PRO" in paid_html
    assert "continuar_pago=1" in paid_html


def test_onboarding_prioritizes_first_value_before_personalization(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_favorites", lambda user_id="": [])
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda user, limit=12: [])
    monkeypatch.setattr(app_module, "build_client_alerts", lambda limit=5: [])
    monkeypatch.setattr(app_module, "telegram_user_state", lambda user: {"linked": False})

    def safe_count_before_value(table, where="", params=()):
        if table == "user_activity":
            return 0
        if table == "shark_memory":
            return 0
        return 0

    monkeypatch.setattr(app_module, "safe_count", safe_count_before_value)
    with app_module.app.test_request_context("/onboarding"):
        app_module.session["growth_attribution"] = {
            "campaign_id": "FIRST_10_USERS",
            "channel": "REFERRAL",
        }
        status = app_module.onboarding_status({"id": "real-first10-user", "membership": "FREE", "role": "FREE"})

    assert [step["key"] for step in status["steps"]] == ["account", "first_value", "shark", "favorites", "telegram"]
    assert status["next_step"]["key"] == "first_value"
    assert status["next_step"]["href"] == "/calendario"
    assert status["core_done"] == 1
    assert status["core_total"] == 2
    assert status["core_score"] == 50
    assert status["first10_beta"] is True
    assert next(step for step in status["steps"] if step["key"] == "telegram")["optional"] is True


def test_onboarding_after_first_value_moves_to_optional_value_and_feedback(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_favorites", lambda user_id="": [])
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda user, limit=12: [])
    monkeypatch.setattr(app_module, "build_client_alerts", lambda limit=5: [])
    monkeypatch.setattr(app_module, "telegram_user_state", lambda user: {"linked": False})

    def safe_count_after_value(table, where="", params=()):
        if table == "user_activity":
            return 1
        if table == "shark_memory":
            return 0
        return 0

    monkeypatch.setattr(app_module, "safe_count", safe_count_after_value)
    with app_module.app.test_request_context("/onboarding"):
        app_module.session["growth_attribution"] = {"campaign_id": "FIRST_10_USERS"}
        status = app_module.onboarding_status({"id": "real-first10-user", "membership": "FREE", "role": "FREE"})

    assert status["first_value_ready"] is True
    assert status["core_score"] == 100
    assert status["next_step"]["key"] == "shark"

    template = (ROOT / "templates" / "onboarding.html").read_text(encoding="utf-8")
    assert 'data-first-value-onboarding="true"' in template
    assert 'data-first10-feedback-prompt="true"' in template
    assert 'href="/beta#beta-feedback-form"' in template
    assert "No configures cinco cosas antes de empezar." in template
    assert "no te pide tu número de teléfono" in template


def test_first10_cohort_metrics_are_campaign_specific_not_global():
    template = (ROOT / "templates" / "admin_founder_dashboard.html").read_text(encoding="utf-8")
    assert "first10_registered = first10_cohort.get('count', 0)" in template
    assert "first10_stage_counts.get('FIRST_VALUE', 0)" in template
    assert "first10_stage_counts.get('ACTIVATED', 0)" in template
    assert "first10_stage_counts.get('RETURNING', 0)" in template
    assert "Acceso actual; no equivale a pago confirmado" in template
    assert "Pago real" not in template[template.index('id="first10-today"'):template.index('id="first10-today"') + 5000]
