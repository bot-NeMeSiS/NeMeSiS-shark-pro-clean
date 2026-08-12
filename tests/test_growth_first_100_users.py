from __future__ import annotations

import json
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