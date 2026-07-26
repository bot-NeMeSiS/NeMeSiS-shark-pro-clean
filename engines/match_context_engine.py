"""Canonical Match Center context for MATCH-CENTER-LIFECYCLE-STORY-V1.

The builder is deliberately pure: callers provide data already loaded from the
local store and this module performs no database, network, session or provider
work. That keeps every Match Center component on one factual snapshot.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.parse import quote

from engines.match_intelligence_engine import (
    build_match_intelligence,
    build_shark_match_intelligence_state,
)
from engines.match_live_story_engine import build_match_live_story
from engines.sports_domain_model_engine import (
    build_telegram_readonly_contract,
    build_unified_domain_snapshot,
)


MATCH_CENTER_CONTRACT = "MATCH-CENTER-LIFECYCLE-STORY-V1"
MATCH_CENTER_FOUNDATION = "V944_MATCH_CENTER_FOUNDATION_PHASE_1_FINAL"

CANONICAL_COMPONENT_STATES = (
    "loading",
    "ready",
    "partial",
    "finished",
    "error",
    "offline",
    "unknown",
)

MATCH_CENTER_COMPONENTS = (
    "MatchHeader",
    "ScoreWidget",
    "MatchStory",
    "Timeline",
    "StatsPanel",
    "SharkPanel",
    "TelegramPanel",
    "BankrollPanel",
    "CompetitionPanel",
    "QuickActions",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _present(value: Any) -> bool:
    return value not in (None, "")


def _json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _first_text(*values: Any) -> str:
    for value in values:
        candidate = _text(value)
        if candidate:
            return candidate
    return ""


def _entity_href(entity_type: str, entity_id: Any, label: Any = "") -> str:
    identifier = _text(entity_id)
    display = _text(label)
    if entity_type == "team" and display:
        return f"/team/{quote(display, safe='')}"
    if entity_type == "competition" and identifier:
        return f"/competition/{quote(identifier, safe='')}"
    if entity_type == "player" and identifier:
        return f"/player/{quote(identifier, safe='')}"
    return ""


def _match_facts(match: Mapping[str, Any]) -> dict[str, Any]:
    payload = _json_mapping(match.get("raw_json") or match.get("payload_json"))
    fixture = _mapping(payload.get("fixture"))
    venue = _mapping(fixture.get("venue"))
    league = _mapping(payload.get("league"))
    stadium = _first_text(
        match.get("venue"),
        venue.get("name"),
        payload.get("strVenue"),
        payload.get("stadium"),
    )
    referee = _first_text(
        match.get("referee"),
        fixture.get("referee"),
        payload.get("strReferee"),
    )
    city = _first_text(venue.get("city"), payload.get("strCity"))
    season = _first_text(
        match.get("season"),
        league.get("season"),
        payload.get("strSeason"),
    )
    competition_flag = _first_text(
        league.get("flag"),
        payload.get("strCountryBadge"),
    )
    available_count = sum(bool(item) for item in (stadium, referee, city, season))
    return {
        "stadium": stadium or None,
        "referee": referee or None,
        "city": city or None,
        "season": season or None,
        "competition_flag": competition_flag or None,
        "available": bool(available_count),
        "available_count": available_count,
    }


def _stat_value(value: Any) -> str | None:
    candidate = _text(value)
    if candidate in {"", "-", "—", "None", "null"}:
        return None
    return candidate


def _real_statistics(
    live: Mapping[str, Any], lifecycle: Mapping[str, Any]
) -> dict[str, Any]:
    provider = _text(live.get("provider"))
    stale = bool(lifecycle.get("is_stale") or live.get("is_stale"))
    rows: list[dict[str, Any]] = []
    for raw in _items(live.get("stat_cards")):
        label = _text(raw.get("label"))
        home = _stat_value(raw.get("home"))
        away = _stat_value(raw.get("away"))
        if not label or (home is None and away is None):
            continue
        rows.append({
            "key": _text(raw.get("key")) or label.lower().replace(" ", "_"),
            "label": label,
            "home": home or "No disponible",
            "away": away or "No disponible",
            "leader": _text(raw.get("leader")) or "even",
        })
    available = bool(provider and rows and not stale)
    return {
        "available": available,
        "item_count": len(rows) if available else 0,
        "items": rows if available else [],
        "status": "available" if available else "stale" if stale and rows else "not_available",
        "source": provider or None,
        "updated_at": live.get("updated_at"),
    }



def _navigation(
    teams: Mapping[str, Any],
    competition: Mapping[str, Any],
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    players: list[dict[str, Any]] = []
    seen_players: set[str] = set()
    for event in timeline:
        for id_key, name_key, href_key in (
            ("player_id", "player", "player_href"),
            ("related_player_id", "related_player", "related_player_href"),
        ):
            player_id = _text(event.get(id_key))
            player_name = _text(event.get(name_key))
            href = _entity_href("player", player_id, player_name)
            event[href_key] = href
            if player_id and player_id not in seen_players:
                seen_players.add(player_id)
                players.append({
                    "id": player_id,
                    "name": player_name or "Jugador confirmado",
                    "href": href,
                })
    return {
        "contract": "SPORTS-ENTITY-CENTER-CONTEXT-V1",
        "teams": [
            dict(teams.get("home") or {}),
            dict(teams.get("away") or {}),
        ],
        "competition": dict(competition),
        "players": players,
        "broken_links_allowed": False,
    }


def _score(match: Mapping[str, Any], display: Mapping[str, Any]) -> dict[str, Any]:
    home = match.get("home_score")
    away = match.get("away_score")
    confirmed = _present(home) and _present(away)
    label = _text(display.get("client_score_label"))
    if confirmed:
        label = f"{home}-{away}"
    elif label.lower() in {"", "-", "vs", "pendiente"}:
        label = "VS"
    return {
        "home": home if confirmed else None,
        "away": away if confirmed else None,
        "label": label,
        "confirmed": confirmed,
    }


def _lifecycle(match: Mapping[str, Any], detail: Mapping[str, Any]) -> dict[str, Any]:
    status_info = _mapping(match.get("status_info"))
    live_depth = _mapping(match.get("live_depth") or detail.get("state"))
    key = _text(
        match.get("v935_lifecycle")
        or status_info.get("key")
        or live_depth.get("state")
        or match.get("status")
    ).upper()
    label = _text(
        status_info.get("label")
        or live_depth.get("label")
        or match.get("client_status_label")
        or match.get("status")
    )
    is_finished = bool(status_info.get("is_finished")) or key in {
        "FT",
        "FINISHED",
        "FINAL",
        "FINALIZADO",
    }
    is_live = bool(status_info.get("is_live")) or key in {
        "LIVE",
        "HT",
        "1H",
        "2H",
        "EN DIRECTO",
    }
    is_stale = bool(
        match.get("is_stale")
        or match.get("stale")
        or _mapping(match.get("v935_freshness")).get("is_stale")
    )
    return {
        "key": key or "UNKNOWN",
        "label": label or "Estado pendiente",
        "is_finished": is_finished,
        "is_live": is_live and not is_finished,
        "is_stale": is_stale,
        "minute": match.get("minute") or live_depth.get("minute"),
    }


def _shell_state(
    match: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    *,
    offline: bool,
) -> str:
    if offline:
        return "offline"
    if lifecycle.get("is_finished"):
        return "finished"
    if lifecycle.get("is_stale"):
        return "partial"
    identity_complete = all(
        _text(value)
        for value in (
            match.get("id"),
            match.get("home_team"),
            match.get("away_team"),
        )
    )
    if identity_complete and lifecycle.get("key") != "UNKNOWN":
        return "ready"
    if identity_complete:
        return "partial"
    return "unknown"


def _component(state: str, message: str, *, available: bool) -> dict[str, Any]:
    canonical = state if state in CANONICAL_COMPONENT_STATES else "unknown"
    return {
        "state": canonical,
        "message": message,
        "available": bool(available),
    }


def _story(
    match: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    score: Mapping[str, Any],
    event_summary: Mapping[str, Any],
) -> dict[str, str]:
    home = _text(match.get("home_team")) or "Equipo local"
    away = _text(match.get("away_team")) or "Equipo visitante"
    latest = _mapping(event_summary.get("latest"))
    latest_title = _text(latest.get("title") or latest.get("detail"))

    if lifecycle.get("is_finished"):
        if score.get("confirmed"):
            summary = f"{home} y {away} finalizaron con marcador {score.get('label')}."
        else:
            summary = (
                "El partido figura como finalizado, pero el resultado confirmado "
                "todavía no está disponible."
            )
        phase = "Cierre del partido"
    elif lifecycle.get("is_live"):
        summary = f"{home} y {away} están disputando el partido."
        if latest_title:
            summary += f" Ultimo hecho disponible: {latest_title}."
        phase = "Partido en curso"
    elif lifecycle.get("is_stale"):
        summary = (
            "La ultima lectura se conserva como contexto, pero no se presenta "
            "como informacion actual."
        )
        phase = "Actualizacion pendiente"
    elif lifecycle.get("key") != "UNKNOWN":
        summary = f"{home} y {away} tienen un encuentro programado."
        phase = "Antes del partido"
    else:
        summary = (
            "Se muestran unicamente los datos confirmados mientras se completa "
            "el estado del partido."
        )
        phase = "Cobertura parcial"
    return {"phase": phase, "summary": summary}


@dataclass(frozen=True)
class MatchContext:
    contract: str
    foundation: str
    state: str
    match: dict[str, Any]
    lifecycle: dict[str, Any]
    competition: dict[str, Any]
    teams: dict[str, Any]
    score: dict[str, Any]
    madrid_time: dict[str, Any]
    favorite: bool
    picks: dict[str, Any]
    event_summary: dict[str, Any]
    statistics: dict[str, Any]
    facts: dict[str, Any]
    intelligence: dict[str, Any]
    shark_context: dict[str, Any]
    navigation: dict[str, Any]
    story: dict[str, Any]
    live_story: dict[str, Any]
    domain_model: dict[str, Any]
    sports_graph: dict[str, Any]
    telegram_readonly_contract: dict[str, Any]
    components: dict[str, dict[str, Any]]
    evidence: dict[str, Any]
    limitations: list[str]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_match_context(
    detail: Mapping[str, Any] | None,
    *,
    madrid_context: Mapping[str, Any] | None = None,
    live_context: Mapping[str, Any] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Build one immutable factual snapshot for every Match Center component."""

    detail_data = _mapping(detail)
    match = _mapping(detail_data.get("match"))
    display = _mapping(madrid_context)
    live = _mapping(live_context or detail_data.get("api_football_live_tracker"))
    lifecycle = _lifecycle(match, detail_data)
    score = _score(match, display)
    shell_state = _shell_state(match, lifecycle, offline=offline)

    live_events = _items(live.get("events"))
    if live_events:
        provider = _text(live.get("provider"))
        raw_timeline = [
            {**event, "source": _text(event.get("source")) or provider}
            for event in live_events
        ]
    else:
        raw_timeline = _items(detail_data.get("timeline") or detail_data.get("events"))
    live_story = build_match_live_story(match, raw_timeline)
    timeline = _items(live_story.get("timeline"))
    latest_event = _mapping(live_story.get("latest_event"))
    event_summary = {
        "available": bool(timeline),
        "count": len(timeline),
        "latest": latest_event,
        "items": timeline,
        "raw_count": len(raw_timeline),
        "excluded_without_evidence": max(0, len(raw_timeline) - len(timeline)),
        "source": _text(live.get("provider")) or None,
    }

    statistics = _real_statistics(live, lifecycle)

    related_picks = _items(detail_data.get("related_picks"))
    domain_model = build_unified_domain_snapshot(
        match,
        live_context=live,
        timeline_events=raw_timeline,
        picks=related_picks,
        now_madrid=(
            display.get("client_full_datetime_label")
            or live.get("updated_at")
            or match.get("updated_at")
        ),
    )
    canonical_match = _mapping(domain_model.get("match"))
    canonical_timeline = _items(canonical_match.get("events"))
    picks = {
        "available": bool(related_picks),
        "count": len(related_picks),
        "items": related_picks,
    }

    home_identity = _mapping(match.get("home_identity"))
    away_identity = _mapping(match.get("away_identity"))
    home_name = _text(match.get("home_team")) or "Equipo local pendiente"
    away_name = _text(match.get("away_team")) or "Equipo visitante pendiente"
    teams = {
        "home": {
            "id": match.get("home_team_id"),
            "name": home_name,
            "logo": home_identity.get("logo")
            or home_identity.get("crest_url")
            or match.get("home_logo")
            or match.get("home_crest"),
            "flag": home_identity.get("country_flag")
            or home_identity.get("flag_emoji"),
            "href": _entity_href("team", match.get("home_team_id"), home_name),
        },
        "away": {
            "id": match.get("away_team_id"),
            "name": away_name,
            "logo": away_identity.get("logo")
            or away_identity.get("crest_url")
            or match.get("away_logo")
            or match.get("away_crest"),
            "flag": away_identity.get("country_flag")
            or away_identity.get("flag_emoji"),
            "href": _entity_href("team", match.get("away_team_id"), away_name),
        },
    }

    facts = _match_facts(match)
    competition_name = _text(
        display.get("client_competition")
        or match.get("competition_name")
        or match.get("league_name")
    )
    competition_id = match.get("competition_id") or match.get("competition_key")
    competition = {
        "id": competition_id,
        "name": competition_name or "Competición pendiente",
        "round": _text(match.get("round") or match.get("stage")),
        "country": _text(match.get("country")),
        "flag": facts.get("competition_flag"),
        "href": _entity_href("competition", competition_id, competition_name),
        "available": bool(competition_name),
    }

    madrid_time = {
        "label": _text(
            display.get("client_full_datetime_label")
            or display.get("client_datetime_label")
            or display.get("client_time_label")
        )
        or "Hora Madrid pendiente",
        "date": _text(display.get("client_date_label") or match.get("match_date")),
        "time": _text(display.get("client_time_label") or match.get("kickoff_time")),
        "iso": match.get("kickoff_iso") or match.get("commence_time"),
    }

    navigation = _navigation(teams, competition, timeline)
    event_summary["items"] = timeline
    intelligence = build_match_intelligence(
        match,
        related_picks,
        lifecycle=lifecycle,
        score=score,
        timeline=timeline,
        statistics=statistics,
        tracker=live,
        competition=competition,
        canonical_match=canonical_match,
        canonical_timeline=canonical_timeline,
        observed_at_madrid=(
            madrid_time.get("iso")
            or live.get("updated_at")
            or match.get("updated_at")
        ),
    )
    shark_context = build_shark_match_intelligence_state(intelligence)
    telegram_readonly_contract = build_telegram_readonly_contract(
        match_entity=canonical_match,
        match_intelligence=intelligence,
        timeline_events=canonical_timeline,
        evidence=intelligence.get("evidence"),
        freshness=canonical_match.get("freshness"),
    )

    limitations: list[str] = []
    if not competition["available"]:
        limitations.append("Competición no confirmada.")
    if madrid_time["label"] == "Hora Madrid pendiente":
        limitations.append("Hora Madrid no confirmada.")
    if not event_summary["available"]:
        limitations.append("Sin eventos confirmados.")
    if not statistics["available"]:
        limitations.append("Sin estadísticas confirmadas.")
    if lifecycle.get("is_stale"):
        limitations.append("La última lectura deportiva está desactualizada.")

    story = _story(match, lifecycle, score, event_summary)
    header_state = shell_state if shell_state in {"ready", "finished"} else "partial"
    score_state = (
        "finished"
        if lifecycle.get("is_finished")
        else "ready"
        if score.get("confirmed") or lifecycle.get("key") != "UNKNOWN"
        else "unknown"
    )
    timeline_state = "ready" if event_summary["available"] else "partial"
    stats_state = "ready" if statistics["available"] else "partial"

    components = {
        "MatchHeader": _component(
            header_state,
            "Identidad y contexto confirmados."
            if header_state in {"ready", "finished"}
            else "Se muestran los datos de identidad disponibles.",
            available=bool(match),
        ),
        "ScoreWidget": _component(
            score_state,
            "Marcador confirmado."
            if score.get("confirmed")
            else "El marcador no está disponible todavía.",
            available=True,
        ),
        "MatchStory": _component(
            shell_state,
            "Historia construida solo con el estado disponible.",
            available=True,
        ),
        "Timeline": _component(
            timeline_state,
            "Cronología disponible."
            if event_summary["available"]
            else "No disponible todavía.",
            available=event_summary["available"],
        ),
        "StatsPanel": _component(
            stats_state,
            "Estadísticas reales del proveedor disponibles."
            if statistics["available"]
            else "No disponible: la última instantánea está fuera de la ventana de frescura."
            if statistics["status"] == "stale"
            else "No disponible.",
            available=statistics["available"],
        ),
        "SharkPanel": _component(
            "ready" if shark_context["available"] else "partial",
            shark_context["message"],
            available=shark_context["available"],
        ),
        "TelegramPanel": _component(
            "partial",
            "No disponible todavía.",
            available=False,
        ),
        "BankrollPanel": _component(
            "partial",
            "No disponible todavía.",
            available=False,
        ),
        "CompetitionPanel": _component(
            "ready" if competition["available"] else "partial",
            "Contexto de competición disponible."
            if competition["available"]
            else "Competición pendiente de confirmar.",
            available=competition["available"],
        ),
        "QuickActions": _component(
            "ready",
            "Acciones seguras de continuidad.",
            available=True,
        ),
    }

    context = MatchContext(
        contract=MATCH_CENTER_CONTRACT,
        foundation=MATCH_CENTER_FOUNDATION,
        state=shell_state,
        match=match,
        lifecycle=lifecycle,
        competition=competition,
        teams=teams,
        score=score,
        madrid_time=madrid_time,
        favorite=bool(detail_data.get("favorite") or match.get("is_favorite")),
        picks=picks,
        event_summary=event_summary,
        statistics=statistics,
        facts=facts,
        intelligence=intelligence,
        shark_context=shark_context,
        navigation=navigation,
        story=story,
        live_story=live_story,
        domain_model=domain_model,
        sports_graph=_mapping(domain_model.get("sports_graph")),
        telegram_readonly_contract=telegram_readonly_contract,
        components=components,
        evidence={
            "source": _text(match.get("source") or match.get("v935_source"))
            or "Fuente no identificada",
            "updated_at": match.get("updated_at"),
            "certification_state": _text(match.get("certification_state"))
            or ("PARTIAL" if limitations else "AVAILABLE"),
            "match_id": match.get("id") or detail_data.get("id"),
        },
        limitations=limitations,
        diagnostics={
            "builder_database_queries": 0,
            "builder_database_writes": 0,
            "external_calls": 0,
            "single_snapshot": True,
            "match_intelligence_contract": intelligence.get("contract"),
            "match_intelligence_reused_by_shark": True,
            "sports_domain_model_contract": domain_model.get("contract"),
            "sports_graph_write_authorized": False,
            "telegram_readonly_contract": telegram_readonly_contract.get("contract"),
            "component_contracts": list(MATCH_CENTER_COMPONENTS),
            "canonical_states": list(CANONICAL_COMPONENT_STATES),
        },
    )
    return context.to_dict()
