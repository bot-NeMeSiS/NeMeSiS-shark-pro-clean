from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from engines.api_football_live_tracker_engine import (
    ensure_live_tracker_schema,
    live_tracker_for_match,
)
from engines.match_context_engine import build_match_context
from engines.match_live_story_engine import normalize_story_events
from engines.sentinel_autopilot_engine import (
    build_v944_match_center_foundation_contract_snapshot,
    create_autopilot_task,
    detect_product_quality_contract_issues,
)


def _detail() -> dict:
    match = {
        "id": "af-4242",
        "external_id": "4242",
        "home_team": "Club Local",
        "away_team": "Union Visitante",
        "home_team_id": "10",
        "away_team_id": "20",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "competition_key": "liga-real",
        "country": "Spain",
        "round": "Jornada 8",
        "match_date": "2026-07-26",
        "kickoff_time": "20:30",
        "kickoff_iso": "2026-07-26T20:30:00+02:00",
        "status": "2H",
        "minute": "68",
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "source": "api_football_live",
        "last_synced_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds"),
        "updated_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds"),
        "status_info": {
            "key": "2H",
            "label": "En directo",
            "is_live": True,
            "is_finished": False,
            "is_upcoming": False,
        },
        "home_identity": {
            "crest_url": "/team-crest.svg?name=Club+Local",
            "country_flag": "ES",
        },
        "away_identity": {
            "crest_url": "/team-crest.svg?name=Union+Visitante",
        },
        "raw_json": json.dumps({
            "fixture": {
                "referee": "Arbitro Confirmado",
                "venue": {"name": "Estadio Central", "city": "Madrid"},
            },
            "league": {"season": 2026, "flag": "https://example.invalid/flag.svg"},
        }),
    }
    return {
        "id": match["id"],
        "match": match,
        "favorite": True,
        "related_picks": [],
        "statistics": {
            "items": [{"label": "Synthetic momentum", "home": 99, "away": 1}],
        },
        "state": {"shark_momentum": {"stats_available": True}},
    }


def _live_context() -> dict:
    return {
        "available": True,
        "read_only": True,
        "provider": "api_football",
        "last_synced_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds"),
        "updated_at": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds"),
        "events": [
            {
                "id": "goal-1",
                "elapsed": 12,
                "event_type": "Goal",
                "detail": "Normal Goal",
                "team_name": "Club Local",
                "player_id": "101",
                "player_name": "Jugador Uno",
            },
            {
                "id": "card-1",
                "elapsed": 45,
                "extra": 2,
                "event_type": "Card",
                "detail": "Yellow Card",
                "team_name": "Union Visitante",
                "player_id": "202",
                "player_name": "Jugador Dos",
            },
            {
                "id": "card-duplicate-provider-id",
                "elapsed": 45,
                "extra": 2,
                "event_type": "Card",
                "detail": "Yellow Card",
                "team_name": "Union Visitante",
                "player_id": "202",
                "player_name": "Jugador Dos",
            },
            {
                "id": "sub-1",
                "elapsed": 62,
                "event_type": "subst",
                "detail": "Substitution 1",
                "team_name": "Club Local",
                "player_id": "303",
                "player_name": "Jugador Tres",
                "assist_id": "304",
                "assist_name": "Jugador Cuatro",
            },
        ],
        "stat_cards": [
            {"key": "possession", "label": "Posesion", "home": "58%", "away": "42%", "leader": "home"},
            {"key": "shots_on_goal", "label": "Tiros a puerta", "home": "6", "away": "2", "leader": "home"},
        ],
        "quality": {
            "label": "Live avanzado",
            "evidence": ["estadisticas", "eventos", "tiros"],
        },
        "game_flow": {
            "available": True,
            "title": "Lectura real disponible",
            "phase": "Dominio claro",
        },
        "field_state": {
            "available": True,
            "headline": "Presion de Club Local",
            "dominant_team": "Club Local",
            "chips": ["Tiros 6-2", "Posesion 58-42"],
        },
        "pressure": {"available": True, "home_pct": 64, "away_pct": 36},
    }


def test_match_context_uses_only_persisted_provider_facts():
    context = build_match_context(
        _detail(),
        madrid_context={
            "client_full_datetime_label": "domingo, 26 de julio - 20:30",
            "client_competition": "Liga Real",
            "client_score_label": "1-0",
        },
        live_context=_live_context(),
    )

    assert context["statistics"]["source"] == "api_football"
    assert context["statistics"]["item_count"] == 2
    assert all(item["label"] != "Synthetic momentum" for item in context["statistics"]["items"])
    assert context["event_summary"]["raw_count"] == 4
    assert context["event_summary"]["count"] == 3
    assert context["event_summary"]["excluded_without_evidence"] == 1
    assert [item["type"] for item in context["event_summary"]["items"]] == [
        "goal",
        "yellow_card",
        "substitution",
    ]
    assert context["event_summary"]["items"][1]["minute_label"] == "45+2'"
    assert context["event_summary"]["items"][0]["player_href"] == "/player/101"
    assert context["facts"] == {
        "stadium": "Estadio Central",
        "referee": "Arbitro Confirmado",
        "city": "Madrid",
        "season": "2026",
        "competition_flag": "https://example.invalid/flag.svg",
        "available": True,
        "available_count": 4,
    }
    assert context["teams"]["home"]["href"] == "/team/Club%20Local"
    assert context["competition"]["href"] == "/competition/140"
    assert context["navigation"]["broken_links_allowed"] is False
    assert context["shark_context"]["available"] is True
    assert context["shark_context"]["dominant_team"] == "Club Local"
    assert context["diagnostics"]["builder_database_writes"] == 0
    assert context["diagnostics"]["external_calls"] == 0


def test_match_context_hides_stale_live_statistics_and_shark():
    detail = _detail()
    detail["match"]["v935_freshness"] = {"is_stale": True}
    context = build_match_context(detail, live_context=_live_context())

    assert context["state"] == "partial"
    assert context["statistics"]["status"] == "stale"
    assert context["statistics"]["available"] is False
    assert context["statistics"]["items"] == []
    assert context["shark_context"]["available"] is False


def test_timeline_dedupes_provider_facts_even_when_ids_change():
    match = _detail()["match"]
    events = _live_context()["events"]
    for event in events:
        event["source"] = "api_football"
    events[2]["source"] = "secondary_confirmed_cache"
    normalized = normalize_story_events(events, match)
    assert len(normalized) == 3
    assert normalized[1]["type"] == "yellow_card"
    assert normalized[2]["type"] == "substitution"


def test_live_tracker_match_read_is_byte_for_byte_read_only(tmp_path, monkeypatch):
    db_path = tmp_path / "tracker.sqlite"
    ensure_live_tracker_schema(str(db_path))
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO api_football_live_snapshots(fixture_id,match_id,status_short,elapsed,home_team,away_team,last_synced_at) VALUES (?,?,?,?,?,?,?)",
        ("4242", "af-4242", "2H", 68, "Club Local", "Union Visitante", "2026-07-26T19:58:00Z"),
    )
    conn.execute(
        "INSERT INTO api_football_live_events(id,fixture_id,elapsed,team_name,player_name,event_type,detail,captured_at) VALUES (?,?,?,?,?,?,?,?)",
        ("event-1", "4242", 12, "Club Local", "Jugador Uno", "Goal", "Normal Goal", "2026-07-26T19:58:00Z"),
    )
    conn.execute(
        "INSERT INTO api_football_live_stats(id,fixture_id,team_id,team_name,stat_name,stat_value,numeric_value,captured_at) VALUES (?,?,?,?,?,?,?,?)",
        ("stat-1", "4242", "10", "Club Local", "Ball Possession", "58%", 58, "2026-07-26T19:58:00Z"),
    )
    conn.commit()
    conn.close()

    before = hashlib.sha256(db_path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        "engines.api_football_live_tracker_engine.ensure_live_tracker_schema",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("schema write from GET")),
    )
    tracker = live_tracker_for_match(str(db_path), "af-4242")
    after = hashlib.sha256(db_path.read_bytes()).hexdigest()

    assert tracker["available"] is True
    assert tracker["read_only"] is True
    assert tracker["events_count"] == 1
    assert tracker["field_state"]["available"] is True
    assert before == after


def test_match_api_get_has_no_persistence_side_effect(client, app_module, monkeypatch):
    detail = _detail()
    monkeypatch.setattr(app_module, "match_detail", lambda _match_id: detail)
    monkeypatch.setattr(app_module, "get_favorites", lambda: [])
    monkeypatch.setattr(app_module, "default_profile", lambda: {})
    monkeypatch.setattr(app_module, "build_shark_context", lambda **_kwargs: {"state": "safe"})
    monkeypatch.setattr(
        app_module,
        "save_shark_context",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("GET write")),
    )

    response = client.get("/api/matches/af-4242/detail")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["side_effects"] == {"database_writes": 0, "external_calls": 0}


def test_future_entity_contract_routes_are_safe_and_not_broken(client):
    for route in ("/competition/140", "/player/101"):
        response = client.get(route)
        assert response.status_code == 200
        assert "No disponible" in response.get_data(as_text=True)


def test_sentinel_and_autopilot_detect_match_intelligence_regression(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "app.py",
        "engines/match_context_engine.py",
        "engines/sports_domain_model_engine.py",
        "engines/api_football_live_tracker_engine.py",
        "engines/match_intelligence_engine.py",
        "engines/shark_context_presentation_engine.py",
        "engines/sports_platform_contracts.py",
        "engines/telegram_intelligence_engine.py",
        "templates/match_detail.html",
        "templates/components/v944_match_center.html",
        "static/v933-product.css",
    ):
        source = root / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    components = tmp_path / "templates/components/v944_match_center.html"
    source = components.read_text(encoding="utf-8")
    components.write_text(
        source.replace("data-stat-source=", "data-stat-source-removed="),
        encoding="utf-8",
    )

    snapshot = build_v944_match_center_foundation_contract_snapshot(
        tmp_path,
        "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL",
    )
    assert snapshot["validation_result"] == "REGRESSION"
    assert "intelligence_contract" in snapshot["evidence"]["violations"]

    issues = detect_product_quality_contract_issues(
        tmp_path,
        "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL",
    )
    issue = next(item for item in issues if item["id"] == "V944-MATCH-CENTER-FOUNDATION-CONTRACT")
    task = create_autopilot_task(issue)
    assert issue["priority"] == "P1"
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True
