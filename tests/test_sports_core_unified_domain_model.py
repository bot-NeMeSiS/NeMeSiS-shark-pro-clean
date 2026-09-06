from __future__ import annotations

import ast
import inspect
from datetime import datetime
from zoneinfo import ZoneInfo

import engines.sports_domain_model_engine as domain_module
from engines.match_context_engine import build_match_context
from engines.match_intelligence_engine import build_match_intelligence
from engines.sports_domain_model_engine import (
    SPORTS_DOMAIN_MODEL_CONTRACT,
    TELEGRAM_READONLY_CONTRACT,
    TIMELINE_EVENT_CONTRACT,
    build_entity_center_contract,
    build_freshness_entity,
    build_sports_graph_foundation,
    build_telegram_readonly_contract,
    build_unified_domain_snapshot,
    canonical_identifier,
    normalize_competition_entity,
    normalize_evidence_entity,
    normalize_match_entity,
    normalize_player_entity,
    normalize_status,
    normalize_team_entity,
    normalize_timeline_events,
    sports_domain_model_snapshot,
)


def _match_row() -> dict:
    return {
        "id": "af-4242",
        "external_id": "4242",
        "sport_key": "soccer",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada 8",
        "home_team_id": "10",
        "away_team_id": "20",
        "home_team": "Club Local",
        "away_team": "Union Visitante",
        "home_logo": "https://example.invalid/home.svg",
        "away_logo": "https://example.invalid/away.svg",
        "kickoff_iso": "2026-07-26T20:30:00+02:00",
        "status": "LIVE",
        "minute": 68,
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "venue": "Estadio Central",
        "source": "api_football",
        "updated_at": "2026-07-26T21:58:00+02:00",
    }


def _events() -> list[dict]:
    return [
        {
            "id": "goal-1",
            "elapsed": 12,
            "event_type": "Goal",
            "detail": "Normal Goal",
            "team_name": "Club Local",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "source": "api_football",
            "captured_at": "2026-07-26T21:58:00+02:00",
        },
        {
            "id": "goal-duplicate-provider-id-changed",
            "elapsed": 12,
            "event_type": "Goal",
            "detail": "Normal Goal",
            "team_name": "Club Local",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "source": "api_football",
            "captured_at": "2026-07-26T21:58:00+02:00",
        },
        {
            "id": "red-1",
            "elapsed": 64,
            "event_type": "Card",
            "detail": "Red Card",
            "team_name": "Union Visitante",
            "player_id": "202",
            "player_name": "Jugador Dos",
            "source": "api_football",
            "captured_at": "2026-07-26T21:58:00+02:00",
        },
    ]


def test_match_team_competition_player_entities_are_canonical_and_honest():
    match = normalize_match_entity(
        _match_row(),
        live_context={"provider": "api_football", "last_synced_at": "2026-07-26T21:58:00+02:00"},
        timeline_events=_events(),
        now_madrid="2026-07-26T22:00:00+02:00",
    )

    assert match["contract"] == "SPORTS-CORE-MATCH-ENTITY-V1"
    assert match["status"] == "live"
    assert match["phase"] == "second_half"
    assert match["minute"] == 68
    assert match["freshness"]["state"] == "fresh"
    assert match["freshness"]["usable_for_intelligence"] is True
    assert match["home_team"]["canonical_team_id"].startswith("api_football:team:")
    assert match["away_team"]["display_name"] == "Union Visitante"
    assert match["competition"]["canonical_competition_id"].startswith("api_football:competition:")
    assert match["score"] == {"home": 1, "away": 0, "label": "1-0", "confirmed": True}
    assert len(match["events"]) == 2
    assert {item["event_type"] for item in match["events"]} == {"goal", "red_card"}

    partial_player = normalize_player_entity({"player_name": "Jugador Sin Foto"}, provider="api_football")
    assert partial_player["display_name"] == "Jugador Sin Foto"
    assert partial_player["photo"] is None
    assert "Player photo is not available." in partial_player["limitations"]


def test_canonical_identifiers_do_not_auto_merge_ambiguous_entities():
    ambiguous = canonical_identifier(
        "team",
        provider_ids={"api_football": "10", "odds_api": "team-10-alt"},
        fallback_parts=("Club Local", "Spain"),
    )
    assert ambiguous["identity_state"] == "REQUIRES_REVIEW"
    assert ambiguous["collision_risk"] == "medium"

    competition_a = normalize_competition_entity({"league_name": "La Liga", "country": "Spain"}, provider="api_football")
    competition_b = normalize_competition_entity({"league_name": "Liga", "country": "Spain"}, provider="odds_api")
    assert competition_a["canonical_competition_id"] != competition_b["canonical_competition_id"]


def test_freshness_and_evidence_keep_stale_and_missing_states_visible():
    fresh = build_freshness_entity(
        source_timestamp="2026-07-26T19:58:00Z",
        now_madrid="2026-07-26T22:00:00+02:00",
        match_status="LIVE",
        data_type="statistics",
    )
    stale = build_freshness_entity(
        source_timestamp="2026-07-26T19:20:00Z",
        now_madrid="2026-07-26T22:00:00+02:00",
        match_status="LIVE",
        data_type="statistics",
    )
    unknown = build_freshness_entity(match_status="LIVE", data_type="statistics")

    assert fresh["state"] == "fresh"
    assert stale["state"] == "stale"
    assert stale["usable_for_intelligence"] is False
    assert unknown["state"] == "unknown"

    evidence = normalize_evidence_entity(
        match_id="af-4242",
        category="status",
        claim="minute_68_is_second_half",
        raw_value="LIVE 68",
        normalized_value={"phase": "second_half"},
        source="api_football",
        method="confirmed_match_minute",
        observed_at="2026-07-26T22:00:00+02:00",
        freshness=stale,
        missing_information=("provider_phase",),
    )
    assert evidence["contract"] == "SPORTS-CORE-EVIDENCE-V1"
    assert evidence["stale"] is True
    assert evidence["usable_for_intelligence"] is False
    assert evidence["missing_information"] == ["provider_phase"]


def test_domain_snapshot_graph_and_telegram_contract_are_read_only():
    snapshot = build_unified_domain_snapshot(
        _match_row(),
        live_context={"provider": "api_football", "updated_at": "2026-07-26T21:58:00+02:00", "events": _events()},
        timeline_events=_events(),
        picks=({"id": "pick-1", "match_id": "af-4242"},),
        now_madrid="2026-07-26T22:00:00+02:00",
    )
    graph = build_sports_graph_foundation(snapshot["match"], picks=({"id": "pick-1"},), shark={"id": "shark-1"})
    telegram = build_telegram_readonly_contract(match_entity=snapshot["match"], timeline_events=snapshot["timeline_events"])

    assert snapshot["contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert snapshot["diagnostics"] == {
        "database_writes": 0,
        "external_calls": 0,
        "telegram_sends": 0,
        "generative_ai_calls": 0,
        "fake_data_created": 0,
    }
    assert graph["database_written"] is False
    assert graph["persistence_authorized"] is False
    assert any(edge["relationship"] == "has_home_team" for edge in graph["edges"])
    assert telegram["contract"] == TELEGRAM_READONLY_CONTRACT
    assert telegram["send_executed"] is False
    assert telegram["telegram_api_called"] is False
    assert telegram["database_written"] is False


def test_match_context_and_match_intelligence_reuse_domain_entities():
    live_updated_at = datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds")
    match = _match_row()
    match["updated_at"] = live_updated_at
    match["last_synced_at"] = live_updated_at
    context = build_match_context(
        {"match": match, "related_picks": []},
        madrid_context={"client_full_datetime_label": "domingo, 26 de julio - 20:30"},
        live_context={"available": True, "provider": "api_football", "last_synced_at": live_updated_at, "events": _events()},
    )
    intelligence = context["intelligence"]

    assert context["domain_model"]["contract"] == SPORTS_DOMAIN_MODEL_CONTRACT
    assert context["sports_graph"]["database_written"] is False
    assert context["telegram_readonly_contract"]["send_executed"] is False
    assert intelligence["domain_model"]["single_domain_entity_source"] is True
    assert intelligence["conclusions"]["fase"]["value"]["key"] == "second_half"
    assert intelligence["diagnostics"]["database_writes"] == 0
    assert intelligence["diagnostics"]["external_calls"] == 0

    canonical_only = build_match_intelligence(
        canonical_match=context["domain_model"]["match"],
        canonical_timeline=context["domain_model"]["timeline_events"],
    )
    assert canonical_only["domain_model"]["single_domain_entity_source"] is True
    assert canonical_only["conclusions"]["fase"]["value"]["key"] == "second_half"


def test_future_entity_center_contracts_are_safe_states():
    unresolved = build_entity_center_contract("player")
    configured = build_entity_center_contract("team", normalize_team_entity(_match_row(), side="home", provider="api_football"))
    provider_missing = build_entity_center_contract("competition", provider_configured=False)

    assert unresolved["state"] == "entity_not_resolved"
    assert configured["state"] in {"entity_available", "entity_partial"}
    assert provider_missing["state"] == "provider_not_configured"
    assert unresolved["external_calls"] == 0


def test_status_and_timeline_edge_cases_cover_required_states():
    assert normalize_status("NS")["phase"] == "pre_match"
    assert normalize_status("1H", 12)["phase"] == "live"
    assert normalize_status("HT")["phase"] == "halftime"
    assert normalize_status("LIVE", 68)["phase"] == "second_half"
    assert normalize_status("ET", 101)["phase"] == "extra_time"
    assert normalize_status("P", 121)["phase"] == "penalties"
    assert normalize_status("POSTP")["phase"] == "postponed"
    assert normalize_status("SUSP")["phase"] == "suspended"
    assert normalize_status("FT")["phase"] == "finished"
    assert normalize_status("??")["phase"] == "unknown"

    events = normalize_timeline_events(_events(), match_id="af-4242", home_team="Club Local", away_team="Union Visitante", provider="api_football")
    assert len(events) == 2
    assert events[0]["contract"] == TIMELINE_EVENT_CONTRACT


def test_module_has_no_io_network_or_generative_dependencies():
    source = inspect.getsource(domain_module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert imported_roots <= {"__future__", "hashlib", "re", "unicodedata", "datetime", "typing", "engines"}
    engine_imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("engines.")
    ]
    assert engine_imports == ["engines.v935_launch_trust_engine"]
    lowered = source.lower()
    assert "sqlite3" not in lowered
    assert "urlopen" not in lowered
    assert "requests" not in lowered
    assert "openai" not in lowered
    assert sports_domain_model_snapshot()["guardrails"] == {
        "database_writes": 0,
        "external_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "generative_ai_calls": 0,
        "automatic_merges": False,
    }

