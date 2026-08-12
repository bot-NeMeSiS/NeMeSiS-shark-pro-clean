from __future__ import annotations

import json
import uuid

from engines.growth_revenue_os_engine import (
    build_first100_attribution_links,
    build_first_10_launch_kit,
    build_first_7_day_organic_schedule,
    build_first_paid_customer_path,
)


def _csrf(client, value="csrf-growth-live"):
    with client.session_transaction() as state:
        state["csrf_token"] = value
    return value


def test_first100_links_kits_and_week_are_ready_without_external_actions():
    links = build_first100_attribution_links("https://example.invalid")
    assert len(links) == 9
    assert {item["channel"] for item in links} == {
        "DIRECT", "INSTAGRAM", "TIKTOK", "YOUTUBE", "X", "FACEBOOK", "TELEGRAM", "REFERRAL", "ORGANIC_SEARCH"
    }
    assert all(item["contains_pii"] is False for item in links)
    assert all(item["url"].startswith("https://example.invalid/landing") for item in links)
    assert next(item for item in links if item["channel"] == "DIRECT")["campaign_id"] == "DIRECT_NO_UTM"
    assert "utm_campaign=FIRST100_ORGANIC" in next(item for item in links if item["channel"] == "INSTAGRAM")["url"]

    kit = build_first_10_launch_kit(links)
    week = build_first_7_day_organic_schedule(links)
    assert len(kit) == 3
    assert len(week) == 7
    assert {item["day"] for item in week} == set(range(1, 8))
    assert all(item["publication_state"] == "NOT_PUBLISHED" for item in week)
    assert all(item["status"] == "READY_FOR_REVIEW" for item in week)
    assert build_first_paid_customer_path()["charging_allowed"] is False


def test_full_first_user_funnel_is_simulated_qa_and_never_real_business(client, app_module, monkeypatch):
    token = uuid.uuid4().hex[:10]
    username = f"growth{token}"
    email = f"growth-{token}@example.invalid"
    password = "Growth-qa-Password-2026"

    landing = client.get("/landing?utm_source=instagram&utm_medium=social&utm_campaign=FIRST100_ORGANIC")
    assert landing.status_code == 200
    csrf = _csrf(client)
    session_event = client.post(
        "/api/growth/funnel-event",
        json={"stage": "LANDING", "target_id": "company-landing"},
        headers={"X-CSRF-Token": csrf},
    )
    assert session_event.status_code == 202
    assert session_event.get_json()["persisted"] is False

    registration = client.post(
        "/registro",
        data={"name": "Growth QA", "username": username, "email": email, "password": password, "csrf_token": csrf},
        follow_redirects=False,
    )
    assert registration.status_code in {302, 303}
    user = app_module.get_user_by_email(email)
    assert user

    client.get("/logout")
    client.get("/cliente-login")
    csrf = _csrf(client, "csrf-growth-live-login")
    login = client.post(
        "/cliente-login",
        data={"login": email, "password": password, "csrf_token": csrf},
        follow_redirects=False,
    )
    assert login.status_code in {302, 303}

    match_ids = ["v944-match-1", "v944-match-2"]

    def qa_match_detail(match_id, *, include_depth=True):
        assert include_depth is False
        return {
            "id": match_id,
            "match": {
                "id": match_id,
                "home_team": "Real Club Deportivo Local",
                "away_team": "Union Deportiva Visitante",
                "competition_name": "Competicion de prueba local",
                "competition_key": "test-local",
                "match_date": "2026-08-12",
                "kickoff_time": "20:30",
                "status": "upcoming",
                "source": "fixture-local-v944",
                "status_info": {"key": "UPCOMING", "label": "Proximo", "is_upcoming": True, "is_live": False, "is_finished": False},
                "live_depth": {"state": "UPCOMING", "label": "Proximo", "minute": "20:30"},
            },
            "timeline": [],
            "events": [],
            "related_picks": [],
            "favorite": False,
            "state": {"state": "UPCOMING", "shark_momentum": {"stats_available": False}},
            "statistics": {"items": []},
        }

    monkeypatch.setattr(app_module, "match_detail", qa_match_detail)
    monkeypatch.setattr(app_module, "live_tracker_for_match", lambda *_args, **_kwargs: {})
    csrf = _csrf(client, "csrf-growth-live-value")
    for match_id in match_ids:
        page = client.get(f"/match/{match_id}")
        assert page.status_code == 200
        event = client.post(
            "/api/growth/funnel-event",
            json={"stage": "FIRST_VALUE", "target_id": match_id},
            headers={"X-CSRF-Token": csrf},
        )
        assert event.status_code == 200
    assert event.get_json()["activation"]["state"] in {"RECORDED", "ALREADY_ACTIVATED"}

    event_rows = app_module.rows(
        "SELECT payload_json FROM user_activity WHERE user_id=? AND target_type='growth_funnel'",
        (user["id"],),
    )
    assert event_rows
    assert all(json.loads(item["payload_json"])["evidence_origin"] == "SIMULATED_QA" for item in event_rows)
    snapshot = app_module.growth_funnel_analytics_snapshot()
    assert snapshot["simulated_stages"]["REGISTRATION"] >= 1
    assert snapshot["simulated_stages"]["FIRST_VALUE"] >= 1
    assert snapshot["simulated_stages"]["ACTIVATED"] >= 1

    conn = app_module.db()
    conn.execute("DELETE FROM favorites WHERE user_id=?", (user["id"],))
    conn.execute("DELETE FROM user_activity WHERE user_id=?", (user["id"],))
    conn.execute("DELETE FROM users WHERE id=?", (user["id"],))
    conn.commit()
    conn.close()


def test_founder_can_review_content_but_cannot_publish(client, app_module):
    app_module.ensure_growth_content_review_schema()
    conn = app_module.db()
    conn.execute("DELETE FROM growth_content_reviews WHERE content_id='POST-10'")
    conn.commit()
    conn.close()

    with client.session_transaction() as state:
        state["user_id"] = "qa-founder-growth"
        state["user_name"] = "Founder QA"
        state["user_email"] = "founder@example.invalid"
        state["user_role"] = "ADMIN"
        state["user_membership"] = "ADMIN"
        state["membership"] = "ADMIN"
        state["csrf_token"] = "csrf-founder-growth"

    response = client.post(
        "/admin/founder-dashboard/growth-content-review",
        data={"content_id": "POST-10", "action": "APPROVE", "csrf_token": "csrf-founder-growth"},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}
    review = app_module.growth_content_review_snapshot()["items"]["POST-10"]
    assert review["state"] == "APPROVED"
    assert review["publication_state"] == "NOT_PUBLISHED"

    response = client.post(
        "/admin/founder-dashboard/growth-content-review",
        data={
            "content_id": "POST-10",
            "action": "EDIT",
            "edited_hook": "Beta clara para diez personas",
            "edited_content": "Prueba un partido real y cuentanos que falta.",
            "csrf_token": "csrf-founder-growth",
        },
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}
    review = app_module.growth_content_review_snapshot()["items"]["POST-10"]
    assert review["state"] == "EDITED"
    assert review["publication_state"] == "NOT_PUBLISHED"

    conn = app_module.db()
    conn.execute("DELETE FROM growth_content_reviews WHERE content_id='POST-10'")
    conn.commit()
    conn.close()