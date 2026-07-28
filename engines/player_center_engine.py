"""Premium Player Center context built on Sports Core contracts.

The builder receives already loaded local/cache data and organizes it through
the Unified Sports Domain Model, Sports Knowledge Layer and Sports Graph. It
does not read databases, call providers, send Telegram, touch Stripe, write
files, call generative AI or invent unavailable sports facts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import build_match_intelligence
from engines.shark_intelligence_platform_engine import SHARK_INTELLIGENCE_PLATFORM_CONTRACT
from engines.sports_domain_model_engine import (
    SPORTS_DOMAIN_MODEL_CONTRACT,
    build_unified_domain_snapshot,
    normalize_competition_entity,
    normalize_player_entity,
    normalize_team_entity,
)
from engines.sports_graph_foundation_engine import (
    SPORTS_GRAPH_FOUNDATION_CONTRACT,
    build_sports_graph_relationships,
)
from engines.sports_knowledge_layer_engine import (
    PLAYER_KNOWLEDGE_CONTRACT,
    SPORTS_KNOWLEDGE_LAYER_CONTRACT,
    build_player_knowledge,
    build_sports_knowledge_snapshot,
)
from engines.user_intelligence_platform_engine import USER_INTELLIGENCE_PLATFORM_CONTRACT


PLAYER_CENTER_CONTRACT = "PLAYER-CENTER-PREMIUM-SPORTS-IDENTITY-PLATFORM-V1"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _event_minute(event: Mapping[str, Any]) -> str:
    minute = event.get("minute") if event.get("minute") not in (None, "") else event.get("elapsed")
    extra = event.get("added_time") if event.get("added_time") not in (None, "") else event.get("extra")
    if minute in (None, ""):
        return "No disponible"
    return f"{minute}+{extra}'" if extra not in (None, "", 0, "0") else f"{minute}'"


def _is_upcoming_match(match: Mapping[str, Any]) -> bool:
    status_info = _mapping(match.get("status_info"))
    if status_info.get("is_upcoming") is True:
        return True
    status = _text(status_info.get("label") or match.get("status"), 80).casefold()
    return status in {
        "ns",
        "tbd",
        "scheduled",
        "not started",
        "programado",
        "por jugar",
        "pendiente",
    }

def _domain_for_match(match: Mapping[str, Any], *, now_madrid: Any = "") -> dict[str, Any]:
    item = _mapping(match)
    timeline = _items(item.get("timeline") or item.get("events"))
    return build_unified_domain_snapshot(
        item,
        live_context={
            "provider": item.get("source") or item.get("v935_source") or "local_cache",
            "updated_at": item.get("updated_at") or item.get("source_timestamp"),
            "events": timeline,
            "status": item.get("status"),
            "minute": item.get("minute"),
        },
        timeline_events=timeline,
        now_madrid=now_madrid or item.get("updated_at") or item.get("kickoff_iso"),
    )


def _team_route_id(team: Mapping[str, Any]) -> str:
    return _text(
        team.get("display_name")
        or team.get("official_name")
        or team.get("name")
        or team.get("canonical_team_id"),
        160,
    )


def _competition_route_id(competition: Mapping[str, Any]) -> str:
    providers = _mapping(competition.get("provider_competition_ids"))
    for value in providers.values():
        if _text(value, 160):
            return _text(value, 160)
    return _text(
        competition.get("display_name")
        or competition.get("official_name")
        or competition.get("name")
        or competition.get("canonical_competition_id"),
        160,
    )


def _player_matches_events(
    matches: Iterable[Mapping[str, Any]],
    *,
    player_id: Any = "",
    player_name: Any = "",
) -> list[dict[str, Any]]:
    pid = _text(player_id, 180)
    pname = _text(player_name, 180).casefold()
    items: list[dict[str, Any]] = []
    for match in _items(matches):
        events = []
        for event in _items(match.get("timeline") or match.get("events")):
            event_player_id = _text(event.get("player_id"), 180)
            event_player_name = _text(event.get("player_name") or event.get("player"), 180).casefold()
            related_player_id = _text(event.get("related_player_id") or event.get("assist_id"), 180)
            related_player_name = _text(event.get("related_player_name") or event.get("assist"), 180).casefold()
            if (pid and pid in {event_player_id, related_player_id}) or (
                pname and pname in {event_player_name, related_player_name}
            ):
                events.append(event)
        if events:
            items.append({"match": dict(match), "events": events})
    return items


def _participation_summary(
    *,
    matches: Iterable[Mapping[str, Any]],
    events: Iterable[Mapping[str, Any]],
    lineups: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    event_items = _items(events)
    lineup_items = _items(lineups)
    match_ids = {
        _text(item.get("match_id") or item.get("fixture_id"), 160)
        for item in event_items + lineup_items
        if _text(item.get("match_id") or item.get("fixture_id"), 160)
    }
    match_count = len(match_ids) or len(_items(matches))
    goals = sum(1 for item in event_items if _text(item.get("event_type") or item.get("type"), 80).casefold() in {"goal", "gol"})
    cards = sum(1 for item in event_items if "card" in _text(item.get("event_type") or item.get("type"), 80).casefold() or "tarjeta" in _text(item.get("event_type") or item.get("type"), 80).casefold())
    substitutions = sum(1 for item in event_items if "subst" in _text(item.get("event_type") or item.get("type"), 80).casefold() or "cambio" in _text(item.get("event_type") or item.get("type"), 80).casefold())
    starts = sum(1 for item in lineup_items if str(item.get("is_starting") or "").lower() in {"1", "true", "yes", "si"})
    return {
        "available": bool(event_items or lineup_items or match_count),
        "matches": match_count,
        "events": len(event_items),
        "lineups": len(lineup_items),
        "goals": goals,
        "cards": cards,
        "substitutions": substitutions,
        "starts": starts,
        "limitations": []
        if event_items or lineup_items
        else ["No hay participacion confirmada para este jugador en la muestra local."],
    }


def _player_timeline(events: Iterable[Mapping[str, Any]], matches: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    matches_by_id = {
        _text(match.get("id") or match.get("match_id") or match.get("external_id"), 160): match
        for match in _items(matches)
    }
    timeline = []
    for event in sorted(
        _items(events),
        key=lambda item: (
            _text(item.get("match_date") or item.get("captured_at") or item.get("timestamp"), 80),
            int(item.get("minute") or item.get("elapsed") or 0),
        ),
        reverse=True,
    )[:14]:
        match_id = _text(event.get("match_id") or event.get("fixture_id"), 160)
        match = _mapping(matches_by_id.get(match_id))
        timeline.append({
            "match_id": match_id,
            "minute": _event_minute(event),
            "event_type": _text(event.get("event_type") or event.get("type"), 80) or "No disponible",
            "detail": _text(event.get("detail") or event.get("comments") or event.get("description"), 160) or "No disponible",
            "team": _text(event.get("team_name") or match.get("home_team") or match.get("safe_home"), 160) or "No disponible",
            "match_label": " vs ".join(
                item for item in (
                    _text(match.get("safe_home") or match.get("home_team"), 80),
                    _text(match.get("safe_away") or match.get("away_team"), 80),
                )
                if item
            ) or "No disponible",
            "source": _text(event.get("source") or match.get("source"), 120) or "local_cache",
        })
    return timeline


def _shark_player_context(
    *,
    participation: Mapping[str, Any],
    intelligence: Mapping[str, Any],
    player_name: Any,
) -> dict[str, Any]:
    evidence: list[str] = []
    event_count = int(participation.get("events") or 0)
    match_count = int(participation.get("matches") or 0)
    if event_count:
        evidence.append(f"{event_count} eventos registrados para el jugador en la muestra local.")
    if match_count:
        evidence.append(f"{match_count} partidos relacionados con participacion o contexto disponible.")
    if intelligence.get("contract"):
        evidence.append("Match Intelligence disponible para el partido ancla.")
    if evidence:
        summary = " ".join(evidence)
        state = "PARTIALLY_VERIFIED"
    else:
        summary = "No hay suficiente informacion para construir contexto SHARK del jugador."
        state = "INSUFFICIENT_DATA"
    return {
        "available": bool(evidence),
        "contract": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "state": state,
        "summary": summary,
        "evidence": evidence,
        "source": "player_center_context",
        "limitations": [] if evidence else ["SHARK no genera interpretaciones del jugador sin evidencia real."],
        "subject": _text(player_name, 160) or "No disponible",
    }


def build_player_center_context(
    detail: Mapping[str, Any] | None,
    *,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build the visible Player Center context from already loaded facts."""

    data = _mapping(detail)
    raw_player = _mapping(data.get("player"))
    matches = _items(data.get("matches"))
    raw_events = _items(data.get("events"))
    lineups = _items(data.get("lineups"))
    injuries = _items(data.get("injuries"))
    picks = _items(data.get("picks"))
    raw_team = _mapping(data.get("team"))
    raw_competition = _mapping(data.get("competition"))
    source = raw_player.get("source") or raw_team.get("source") or raw_competition.get("source") or "local_cache"
    player = normalize_player_entity(raw_player, provider=source)
    player_name = player.get("display_name") or raw_player.get("player_name") or "Jugador no disponible"
    team = normalize_team_entity(raw_team, provider=raw_team.get("source") or source) if raw_team else {}
    competition = normalize_competition_entity(raw_competition, provider=raw_competition.get("source") or source) if raw_competition else {}
    domain_snapshots = [_domain_for_match(match, now_madrid=observed_at_madrid) for match in matches[:40]]
    canonical_matches = [_mapping(snapshot.get("match")) for snapshot in domain_snapshots]
    canonical_events = [
        event
        for snapshot in domain_snapshots
        for event in _items(snapshot.get("timeline_events"))
    ]
    if not canonical_events and raw_events:
        canonical_events = raw_events
    anchor_domain = domain_snapshots[0] if domain_snapshots else {}
    anchor_match = _mapping(anchor_domain.get("match"))
    anchor_timeline = _items(anchor_domain.get("timeline_events"))
    intelligence = (
        build_match_intelligence(
            canonical_match=anchor_match,
            canonical_timeline=anchor_timeline,
            observed_at_madrid=observed_at_madrid,
        )
        if anchor_match
        else {}
    )
    player_knowledge = build_player_knowledge(
        player,
        match_entity=anchor_match,
        timeline_events=canonical_events,
        picks=picks,
        lineups=lineups,
        injuries=injuries,
    )
    sports_knowledge = (
        build_sports_knowledge_snapshot(
            domain_model=anchor_domain,
            match_intelligence=intelligence,
            timeline_events=anchor_timeline,
            related_picks=picks,
            now_madrid=observed_at_madrid,
        )
        if anchor_domain
        else {
            "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            "certification_state": player_knowledge.get("certification_state"),
            "limitations": ["Sports Knowledge completo requiere al menos un partido canonico asociado."],
            "diagnostics": {
                "database_writes": 0,
                "external_calls": 0,
                "telegram_sends": 0,
                "stripe_calls": 0,
            },
        }
    )
    participation = _participation_summary(matches=matches, events=canonical_events or raw_events, lineups=lineups)
    player_event_pairs = _player_matches_events(
        matches,
        player_id=player.get("canonical_player_id") or raw_player.get("player_id"),
        player_name=player_name,
    )
    graph = build_sports_graph_relationships(
        player_entity=player,
        team_entities=[team] if team else [],
        match_entities=canonical_matches,
        competition_entities=[competition] if competition else [],
        timeline_events=canonical_events,
        evidence_items=player_knowledge.get("evidence") or [],
        match_intelligence=intelligence,
        picks=picks,
        telegram_context={"id": f"telegram:{player.get('canonical_player_id')}", "certification_state": "NOT_CONFIGURED"} if canonical_matches else {},
        shark_context={"id": f"shark:{player.get('canonical_player_id')}", "certification_state": intelligence.get("certification_state") or "INSUFFICIENT_DATA"} if intelligence else {},
        user_intelligence_context={"id": f"user-intelligence:{player.get('canonical_player_id')}", "certification_state": "NOT_CONFIGURED"},
        observed_at_madrid=observed_at_madrid,
        center="player_center",
    )
    shark_context = _shark_player_context(
        participation=participation,
        intelligence=intelligence,
        player_name=player_name,
    )
    missing = list(player.get("limitations") or [])
    if not player.get("photo"):
        missing.append("Fotografia no disponible: ninguna fuente legal lo confirma.")
    if not player.get("position"):
        missing.append("Posicion no disponible.")
    if not player.get("shirt_number"):
        missing.append("Dorsal no disponible.")
    if not team:
        missing.append("Equipo actual no disponible.")
    if not competition:
        missing.append("Competicion no disponible.")
    if not participation.get("available"):
        missing.extend(participation.get("limitations") or [])
    if not raw_events and not canonical_events:
        missing.append("Eventos personales no disponibles.")
    if not lineups:
        missing.append("Alineaciones o participacion oficial no disponibles.")
    if not injuries:
        missing.append("Estado fisico no disponible o no confirmado.")
    state = player.get("status") or ("Con eventos" if participation.get("events") else "Informacion parcial")
    available_information = [
        item
        for item, available in (
            ("Identidad del jugador", bool(player.get("official_name") or raw_player.get("player_name"))),
            ("Equipo relacionado", bool(team)),
            ("Competicion relacionada", bool(competition)),
            ("Partidos relacionados", bool(matches)),
            ("Eventos registrados", bool(canonical_events or raw_events)),
            ("Sports Graph", bool(graph.get("edge_count"))),
            ("User Intelligence preparado", True),
        )
        if available
    ]
    return {
        "ok": True,
        "contract": PLAYER_CENTER_CONTRACT,
        "source_domain_contract": SPORTS_DOMAIN_MODEL_CONTRACT,
        "sports_knowledge_contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "player_knowledge_contract": PLAYER_KNOWLEDGE_CONTRACT,
        "sports_graph_contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "shark_intelligence_contract": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "user_intelligence_contract": USER_INTELLIGENCE_PLATFORM_CONTRACT,
        "player": {
            "name": player_name,
            "official_name": player.get("official_name") or "No disponible",
            "display_name": player.get("display_name") or "No disponible",
            "team": team.get("display_name") or raw_team.get("name") or "No disponible",
            "competition": competition.get("display_name") or raw_competition.get("name") or "No disponible",
            "country": player.get("nationality") or raw_player.get("country") or "No disponible",
            "position": player.get("position") or "No disponible",
            "shirt_number": player.get("shirt_number") or "No disponible",
            "state": state,
            "photo": player.get("photo"),
            "photo_source": player.get("photo_source") or "No disponible",
            "canonical": player,
        },
        "team": team,
        "competition": competition,
        "metrics": {
            "matches": len(matches),
            "upcoming": sum(1 for match in matches if _is_upcoming_match(match)),
            "events": participation.get("events") or 0,
            "lineups": participation.get("lineups") or 0,
            "picks": len(picks),
            "graph_edges": graph.get("edge_count", 0),
        },
        "participation": participation,
        "player_matches": player_event_pairs,
        "timeline": _player_timeline(canonical_events or raw_events, matches),
        "matches": matches,
        "events": canonical_events or raw_events,
        "lineups": lineups,
        "injuries": injuries,
        "picks": picks,
        "player_knowledge": player_knowledge,
        "sports_knowledge": sports_knowledge,
        "sports_graph": graph,
        "shark_context": shark_context,
        "user_intelligence": {
            "contract": USER_INTELLIGENCE_PLATFORM_CONTRACT,
            "state": "PREPARED_NOT_APPLIED",
            "summary": "Preparado para jugadores consultados, favoritos e historial interno si el usuario lo autoriza.",
            "home_modified": False,
            "privacy_contract": "USER-PRIVACY-CONTROLS-V1",
            "limitations": ["No modifica la Home automaticamente.", "No crea perfiles invasivos."],
        },
        "available_information": available_information,
        "missing_information": sorted(set(item for item in missing if item)),
        "data_quality": {
            "source": source,
            "freshness": _mapping(anchor_match.get("freshness")),
            "certification_state": player_knowledge.get("certification_state") or player.get("data_quality") or "PARTIALLY_VERIFIED",
            "limitations": sorted(set((player_knowledge.get("limitations") or []) + missing)),
        },
        "links": {
            "team_center": "/team/" + _team_route_id(team) if team and _team_route_id(team) else "",
            "competition_center": "/competition/" + _competition_route_id(competition) if competition and _competition_route_id(competition) else "",
            "match_center": "/match/" + _text(matches[0].get("id") or matches[0].get("match_id"), 160) if matches else "",
            "sports_graph": "",
            "user_intelligence": "/user-intelligence",
        },
        "diagnostics": {
            "database_queries": 0,
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "new_dependencies": 0,
            "domain_snapshots": len(domain_snapshots),
            "single_domain_model_per_match": True,
        },
        "no_fake_data": True,
    }


def player_center_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": PLAYER_CENTER_CONTRACT,
        "requires": [
            SPORTS_DOMAIN_MODEL_CONTRACT,
            SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            SPORTS_GRAPH_FOUNDATION_CONTRACT,
            SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
            USER_INTELLIGENCE_PLATFORM_CONTRACT,
        ],
        "guardrails": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "fake_data_created": 0,
            "automatic_home_personalization": False,
        },
    }

