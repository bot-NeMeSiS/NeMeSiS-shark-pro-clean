"""Client picks must be truthful, membership-scoped, and non-mutating.

All rows in this module are synthetic and remain inside the local test client.
"""
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo


MADRID = ZoneInfo("Europe/Madrid")


def _pick(*, identifier="pick-free", membership="FREE", match_date=None, selection="Gana el local", odds=1.95):
    now = datetime.now(MADRID)
    kickoff = now + timedelta(days=1)
    return {
        "id": identifier,
        "match_id": f"api-fixture-{identifier}",
        "match_date": match_date or kickoff.date().isoformat(),
        "kickoff_time": "18:00",
        "kickoff_iso": (kickoff.replace(hour=18, minute=0, second=0, microsecond=0)).isoformat(),
        "competition_name": "Liga QA",
        "home_team": "Equipo local QA",
        "away_team": "Equipo visitante QA",
        "market": "1X2",
        "selection": selection,
        "odds": odds,
        "odds_source": "The Odds API",
        "odds_updated_at": now.isoformat(),
        "source": "The Odds API",
        "status": "published",
        "result_status": "pending",
        "membership_required": membership,
        "risk_level": "BAJO",
        "updated_at": now.isoformat(),
        "published_at": now.isoformat(),
        "reasoning": "Explicación editorial QA.",
        "raw_json": "INTERNAL-RAW-PAYLOAD-MUST-NOT-LEAK",
        "internal_secret_marker": "INTERNAL-ONLY",
    }


def test_public_picks_api_returns_only_current_membership_safe_allowlisted_records(client, app_module, monkeypatch):
    free = _pick()
    premium = _pick(identifier="pick-pro", membership="PRO", selection="SELECCION-PREMIUM")
    upcoming = {
        "id": "fixture-public-api-qa",
        "home_team": "Granada QA",
        "away_team": "Visitante QA",
        "competition_name": "Liga QA",
        "match_date": (datetime.now(MADRID).date() + timedelta(days=1)).isoformat(),
        "kickoff_time": "20:00",
        "status": "NS",
        "source": "API-Football cache",
    }
    summary = {"valid_active_picks": [free, premium], "valid_upcoming_matches": [upcoming], "storage_status": "ok"}
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)

    response = client.get("/api/picks?limit=999999")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["id"] for item in payload["picks"]] == ["pick-free"]
    assert payload["stats"]["scope"] == "current_membership_visible"
    assert payload["stats"]["total"] == 1
    assert payload["readiness"]["count"] == 1
    assert payload["readiness"]["state"] == "available"
    assert payload["readiness"]["no_provider_call"] is True
    assert payload["readiness"]["upcoming_count"] == 1
    assert payload["watchlist"][0]["home_team"] == "Granada QA"
    assert payload["watchlist"][0]["odds_label"] == "Sin cuota observada"
    assert all("selection" not in item and "odds" not in item for item in payload["watchlist"])
    encoded = response.get_data(as_text=True)
    assert "INTERNAL-RAW-PAYLOAD-MUST-NOT-LEAK" not in encoded
    assert "INTERNAL-ONLY" not in encoded
    assert "SELECCION-PREMIUM" not in encoded
    assert "confidence" not in payload["picks"][0]


def test_public_picks_api_does_not_serve_expired_or_incomplete_published_rows(client, app_module, monkeypatch):
    yesterday = (datetime.now(MADRID).date() - timedelta(days=1)).isoformat()
    expired = _pick(identifier="old", match_date=yesterday)
    incomplete = _pick(identifier="missing-odds", odds=0, selection="")
    monkeypatch.setattr(
        app_module,
        "get_public_home_sports_summary",
        lambda: {"valid_active_picks": [expired, incomplete], "storage_status": "ok"},
    )

    response = client.get("/api/picks")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["picks"] == []
    assert payload["readiness"]["state"] == "waiting_for_matches"
    assert payload["stats"]["published"] == 0
    assert payload["stats"]["avg_odds"] == 0


def test_unknown_membership_tier_fails_closed_on_page_api_and_stats(client, app_module, monkeypatch):
    legacy = _pick(identifier="legacy-vip", membership="VIP", selection="LEGACY-LOCKED-SELECTION")
    summary = {"valid_active_picks": [legacy], "valid_upcoming_matches": [], "storage_status": "ok"}
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_a, **_k: ({}, summary))
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda *_a, **_k: [])
    monkeypatch.setattr(app_module, "get_realtime_safe_picks_context", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "get_realtime_safe_odds_context", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "get_v935_customer_trust_context", lambda *_a, **_k: {})

    api = client.get("/api/picks")
    stats = client.get("/api/picks/stats")
    page = client.get("/picks")

    assert api.status_code == stats.status_code == page.status_code == 200
    assert api.get_json()["picks"] == []
    assert api.get_json()["readiness"]["locked_count"] == 1
    assert stats.get_json()["stats"]["total"] == 0
    assert "LEGACY-LOCKED-SELECTION" not in api.get_data(as_text=True)
    assert "LEGACY-LOCKED-SELECTION" not in page.get_data(as_text=True)


def test_public_stats_endpoint_uses_only_current_membership_visible_picks(client, app_module, monkeypatch):
    free = _pick()
    premium = _pick(identifier="stats-premium", membership="PRO", odds=4.5)
    monkeypatch.setattr(
        app_module,
        "get_public_home_sports_summary",
        lambda: {"valid_active_picks": [free, premium], "storage_status": "ok"},
    )

    response = client.get("/api/picks/stats")

    assert response.status_code == 200
    stats = response.get_json()["stats"]
    assert stats["scope"] == "current_membership_visible"
    assert stats["total"] == 1
    assert stats["avg_odds"] == 1.95
    assert stats["avg_confidence"] is None
    assert stats["winrate"] is None


def test_public_admin_query_parameter_does_not_grant_raw_pick_access(client, app_module, monkeypatch):
    free = _pick()
    monkeypatch.setattr(
        app_module,
        "get_public_home_sports_summary",
        lambda: {"valid_active_picks": [free], "storage_status": "ok"},
    )

    response = client.get("/api/picks?admin=1")

    assert response.status_code == 200
    encoded = response.get_data(as_text=True)
    assert "INTERNAL-RAW-PAYLOAD-MUST-NOT-LEAK" not in encoded
    assert "INTERNAL-ONLY" not in encoded
    assert response.get_json()["stats"]["scope"] == "current_membership_visible"


def test_client_pick_readiness_shows_real_watchlist_without_fabricating_a_bet(app_module):
    match = {
        "id": "fixture-real-qa-1",
        "home_team": "Granada QA",
        "away_team": "Visitante QA",
        "competition_name": "Competición QA",
        "match_date": (datetime.now(MADRID).date() + timedelta(days=1)).isoformat(),
        "kickoff_time": "20:00",
        "status": "NS",
        "source": "API-Football cache",
    }

    readiness, watchlist = app_module.client_pick_readiness(
        {"valid_upcoming_matches": [match]}, active_count=0,
    )

    assert readiness["state"] == "waiting_for_odds"
    assert readiness["upcoming_count"] == 1
    assert readiness["fresh_odds_match_count"] == 0
    assert readiness["no_provider_call"] is True
    assert "cuotas actuales verificables" in readiness["message"]
    assert watchlist[0]["home_team"] == "Granada QA"
    assert watchlist[0]["schedule_label"]
    assert watchlist[0]["decision_label"] == "En observación"
    assert watchlist[0]["odds_label"] == "Sin cuota observada"
    assert "selection" not in watchlist[0]
    assert "odds" not in watchlist[0]


def test_recent_provider_quote_is_reported_but_never_turns_into_a_pick(app_module):
    now = datetime.now(MADRID)
    match = {
        "id": "fixture-with-real-quote-qa",
        "home_team": "Granada QA",
        "away_team": "Visitante QA",
        "competition_name": "Liga QA",
        "match_date": (now.date() + timedelta(days=1)).isoformat(),
        "kickoff_time": "20:00",
        "status": "NS",
        "odds_h2h_json": json.dumps({
            "home": 2.1, "draw": 3.2, "away": 4.0, "source": "The Odds API",
        }),
        "odds_source": "The Odds API",
        "odds_updated_at": now.isoformat(),
    }

    readiness, watchlist = app_module.client_pick_readiness(
        {"valid_upcoming_matches": [match]}, active_count=0,
    )

    assert readiness["state"] == "waiting_for_review"
    assert readiness["fresh_odds_match_count"] == 1
    assert watchlist[0]["odds_label"] == "Cuota actual verificada"
    assert watchlist[0]["decision_label"] == "En observación"
    assert "selection" not in watchlist[0]
    assert "odds" not in watchlist[0]


def test_picks_page_hides_locked_selection_details_and_shows_safe_watchlist(client, app_module, monkeypatch):
    premium = _pick(identifier="locked", membership="PRO", selection="PREMIUM-LOCKED-OUTCOME")
    match = {
        "id": "fixture-real-page-qa",
        "home_team": "Granada de prueba",
        "away_team": "Rival de prueba",
        "competition_name": "Liga de prueba",
        "match_date": (datetime.now(MADRID).date() + timedelta(days=1)).isoformat(),
        "kickoff_time": "20:00",
        "status": "NS",
        "source": "API-Football cache",
    }
    summary = {"valid_active_picks": [premium], "valid_upcoming_matches": [match], "storage_status": "ok"}
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_a, **_k: ({}, summary))
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda *_a, **_k: [])
    monkeypatch.setattr(app_module, "get_realtime_safe_picks_context", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "get_realtime_safe_odds_context", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "get_v935_customer_trust_context", lambda *_a, **_k: {})

    response = client.get("/picks")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Granada de prueba" in html
    assert "En observación" in html
    assert "Sin cuota observada" in html
    assert "PREMIUM-LOCKED-OUTCOME" not in html
    assert 'href="/membresias"' in html


def test_picks_readiness_does_not_count_an_incomplete_stored_pick(client, app_module, monkeypatch):
    incomplete = _pick(identifier="incomplete", membership="FREE", selection="")
    summary = {"valid_active_picks": [incomplete], "valid_upcoming_matches": [], "storage_status": "ok"}
    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", lambda *_a, **_k: ({}, summary))
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda *_a, **_k: [])
    monkeypatch.setattr(app_module, "get_realtime_safe_picks_context", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "get_realtime_safe_odds_context", lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, "get_v935_customer_trust_context", lambda *_a, **_k: {})

    response = client.get("/picks")

    assert response.status_code == 200
    assert 'data-pick-readiness="waiting_for_matches"' in response.get_data(as_text=True)
