"""Canonical Match Center context for MATCH-CENTER-LIFECYCLE-STORY-V1.

The builder is deliberately pure: callers provide data already loaded from the
local store and this module performs no database, network, session or provider
work. That keeps every Match Center component on one factual snapshot.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping
from urllib.parse import quote

from engines.match_intelligence_engine import (
    build_match_intelligence,
    build_shark_match_intelligence_state,
)
from engines.match_live_story_engine import build_match_live_story
from engines.sports_domain_model_engine import (
    build_telegram_readonly_contract,
    build_unified_domain_snapshot,
    legacy_event_from_entity,
    legacy_match_from_entity,
)
from engines.sports_knowledge_layer_engine import build_sports_knowledge_snapshot
from engines.v935_launch_trust_engine import match_status_truth


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
    "LineupsPanel",
    "Timeline",
    "StatsPanel",
    "HeadToHeadPanel",
    "StandingsPanel",
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


def _public_entity_route_id(entity_type: str, identifier: str) -> str:
    marker = f":{entity_type}:"
    if entity_type in {"competition", "player"} and marker in identifier:
        return identifier.rsplit(marker, 1)[-1] or identifier
    return identifier


def _entity_href(entity_type: str, entity_id: Any, label: Any = "") -> str:
    identifier = _text(entity_id)
    display = _text(label)
    if entity_type == "team" and display:
        return f"/team/{quote(display, safe='')}"
    if entity_type == "competition" and identifier:
        return f"/competition/{quote(_public_entity_route_id(entity_type, identifier), safe='')}"
    if entity_type == "player" and identifier:
        return f"/player/{quote(_public_entity_route_id(entity_type, identifier), safe='')}"
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


def _stat_label(value: Any) -> str:
    raw = _text(value)
    labels = {
        "ball possession": "Posesión",
        "total shots": "Tiros",
        "shots on goal": "Tiros a puerta",
        "shots off goal": "Tiros fuera",
        "blocked shots": "Tiros bloqueados",
        "corner kicks": "Córners",
        "fouls": "Faltas",
        "yellow cards": "Tarjetas amarillas",
        "red cards": "Tarjetas rojas",
        "goalkeeper saves": "Paradas",
        "total passes": "Pases",
        "passes accurate": "Pases precisos",
        "expected goals": "Goles esperados",
    }
    return labels.get(raw.casefold(), raw)


def _real_statistics(
    live: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    cached: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    provider = _text(live.get("provider"))
    stale = bool(lifecycle.get("is_stale") or live.get("is_stale"))
    live_rows: list[dict[str, Any]] = []
    for raw in _items(live.get("stat_cards")):
        label = _stat_label(raw.get("label"))
        home = _stat_value(raw.get("home"))
        away = _stat_value(raw.get("away"))
        if not label or (home is None and away is None):
            continue
        live_rows.append({
            "key": _text(raw.get("key")) or label.lower().replace(" ", "_"),
            "label": label,
            "home": home or "No disponible",
            "away": away or "No disponible",
            "leader": _text(raw.get("leader")) or "even",
        })
    if provider and live_rows and not stale:
        return {
            "available": True,
            "item_count": len(live_rows),
            "items": live_rows,
            "status": "available",
            "source": provider,
            "updated_at": live.get("updated_at"),
            "snapshot_kind": "live",
        }

    cached_data = _mapping(cached)
    cached_rows: list[dict[str, Any]] = []
    for raw in _items(cached_data.get("items")):
        label = _stat_label(raw.get("label"))
        home = _stat_value(raw.get("home"))
        away = _stat_value(raw.get("away"))
        if not label or (home is None and away is None):
            continue
        cached_rows.append({
            "key": _text(raw.get("key")) or label.lower().replace(" ", "_"),
            "label": label,
            "home": home or "No disponible",
            "away": away or "No disponible",
            "leader": _text(raw.get("leader")) or "even",
        })
    available = bool(cached_data.get("available") and cached_rows)
    return {
        "available": available,
        "item_count": len(cached_rows) if available else 0,
        "items": cached_rows if available else [],
        "status": (
            "available"
            if available
            else "stale"
            if stale and live_rows
            else "not_available"
        ),
        "source": cached_data.get("source") if available else None,
        "updated_at": cached_data.get("updated_at") if available else None,
        "snapshot_kind": "persisted" if available else None,
    }


def _head_to_head_context(raw_value: Any) -> dict[str, Any]:
    raw = _mapping(raw_value)
    items = _items(raw.get("items") if raw else raw_value)
    normalized = []
    for item in items:
        home = _text(item.get("home_team"))
        away = _text(item.get("away_team"))
        kickoff_iso = _text(item.get("kickoff_iso"))
        status = _text(item.get("status")).upper()
        if (
            not home
            or not away
            or not kickoff_iso
            or status not in {"FT", "FINISHED", "FINAL", "AET", "PEN"}
        ):
            continue
        home_score = item.get("home_score")
        away_score = item.get("away_score")
        score = (
            _text(item.get("score"))
            if item.get("score") not in (None, "")
            else (
                f"{home_score}-{away_score}"
                if home_score is not None and away_score is not None
                else None
            )
        )
        normalized.append({
            "match_id": _text(item.get("match_id")) or None,
            "fixture_id": _text(item.get("fixture_id")) or None,
            "home_team": home,
            "away_team": away,
            "score": score,
            "competition": _text(item.get("competition")) or None,
            "kickoff_iso": kickoff_iso,
            "date_label": _text(item.get("date_label")) or None,
            "status": "FT",
            "href": _text(item.get("href")) or None,
            "source": _text(item.get("source")) or _text(raw.get("source")) or None,
        })
    return {
        "contract": "NEMESIS-MATCH-H2H-CACHE-V1",
        "available": bool(normalized),
        "count": len(normalized),
        "items": normalized,
        "source": _text(raw.get("source")) or (
            normalized[0].get("source") if normalized else None
        ),
        "updated_at": raw.get("updated_at"),
        "external_calls": 0,
        "fake_matches_created": 0,
    }


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _standings_context(raw_value: Any) -> dict[str, Any]:
    raw = _mapping(raw_value)
    rows = _items(raw.get("rows") if raw else raw_value)
    normalized = []
    for item in rows:
        team_name = _text(item.get("team_name") or item.get("name"))
        position = _optional_int(item.get("rank") or item.get("position"))
        if not team_name or position is None:
            continue
        normalized.append({
            "position": position,
            "team_id": _text(item.get("team_id")) or None,
            "team_name": team_name,
            "href": _entity_href("team", item.get("team_id"), team_name),
            "played": _optional_int(item.get("played")),
            "wins": _optional_int(item.get("wins")),
            "draws": _optional_int(item.get("draws")),
            "losses": _optional_int(item.get("losses")),
            "goals_for": _optional_int(item.get("goals_for")),
            "goals_against": _optional_int(item.get("goals_against")),
            "points": _optional_int(item.get("points")),
            "form": _text(item.get("form")) or None,
            "description": _text(item.get("description")) or None,
        })
    normalized.sort(key=lambda item: item["position"])
    return {
        "contract": "NEMESIS-MATCH-STANDINGS-CACHE-V1",
        "available": bool(normalized),
        "count": len(normalized),
        "rows": normalized[:24],
        "source": _text(raw.get("source")) or None,
        "updated_at": raw.get("updated_at"),
        "external_calls": 0,
        "fake_rows_created": 0,
    }


def _lineup_position_band(value: Any) -> str:
    key = _text(value).upper().replace(" ", "_")
    if key in {"G", "GK", "GOALKEEPER", "PORTERO"}:
        return "GK"
    if key in {"D", "DEF", "CB", "LB", "RB", "LWB", "RWB", "DEFENDER", "DEFENSA"}:
        return "DEF"
    if key in {"M", "MID", "CM", "DM", "AM", "LM", "RM", "MIDFIELDER", "MEDIO"}:
        return "MID"
    if key in {"F", "FW", "FWD", "ST", "CF", "LW", "RW", "ATTACKER", "DELANTERO"}:
        return "FWD"
    return "UNKNOWN"


def _lineups_context(raw_lineups: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    seen: set[tuple[str, str, bool]] = set()
    sources: list[str] = []
    captured: list[str] = []
    for raw in _items(raw_lineups):
        player_id = _text(raw.get("player_id"))
        player_name = _text(raw.get("player_name") or raw.get("name"))
        team_id = _text(raw.get("team_id"))
        team_name = _text(raw.get("team_name")) or "Equipo no identificado"
        if not player_id or not player_name:
            continue
        is_starting = str(raw.get("is_starting") or "").strip().lower() in {"1", "true", "yes", "si", "sí"}
        identity = (team_id or team_name.casefold(), player_id, is_starting)
        if identity in seen:
            continue
        seen.add(identity)
        source = _text(raw.get("source")) or "lineup_cache"
        observed_at = _text(raw.get("captured_at") or raw.get("updated_at"))
        if source not in sources:
            sources.append(source)
        if observed_at:
            captured.append(observed_at)
        team_key = team_id or team_name.casefold()
        group = groups.setdefault(team_key, {
            "team_id": team_id,
            "team_name": team_name,
            "formation": _text(raw.get("formation")) or None,
            "coach": None,
            "starters": [],
            "substitutes": [],
        })
        if not group.get("formation") and _text(raw.get("formation")):
            group["formation"] = _text(raw.get("formation"))
        player = {
            "player_id": player_id,
            "name": player_name,
            "number": _text(raw.get("number") or raw.get("shirt_number")) or None,
            "position": _text(raw.get("position")) or None,
            "position_band": _lineup_position_band(raw.get("position")),
            "href": _entity_href("player", player_id, player_name),
            "source": source,
        }
        group["starters" if is_starting else "substitutes"].append(player)
    teams = list(groups.values())
    starters = [player for team in teams for player in team["starters"]]
    substitutes = [player for team in teams for player in team["substitutes"]]
    pitch_available = bool(
        len(starters) >= 8
        and all(player.get("position_band") != "UNKNOWN" for player in starters)
        and len({player.get("position_band") for player in starters}) >= 3
    )
    confirmed = bool(teams and starters + substitutes)
    return {
        "contract": "SPORTS-KNOWLEDGE-LINEUPS-V1",
        "confirmed": confirmed,
        "state": "CONFIRMED" if confirmed else "NOT_CONFIRMED",
        "message": "Alineación confirmada." if confirmed else "Alineación todavía no confirmada.",
        "teams": teams,
        "team_count": len(teams),
        "player_count": len(starters) + len(substitutes),
        "starters_count": len(starters),
        "substitutes_count": len(substitutes),
        "pitch_available": pitch_available,
        "source": ", ".join(sources) if sources else None,
        "updated_at": max(captured) if captured else None,
        "external_calls": 0,
        "fake_players_created": 0,
    }


def _factual_summaries(
    match: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    score: Mapping[str, Any],
    event_summary: Mapping[str, Any],
    statistics: Mapping[str, Any],
    lineups: Mapping[str, Any],
    shark_context: Mapping[str, Any],
) -> dict[str, Any]:
    home = _text(match.get("home_team")) or "Equipo local"
    away = _text(match.get("away_team")) or "Equipo visitante"
    key = _text(lifecycle.get("key")).upper()
    items: list[dict[str, Any]] = []
    evidence = ["match_status"]
    if lifecycle.get("is_finished"):
        summary_type = "FULLTIME_SUMMARY"
        text = f"{home} y {away} finalizaron"
        if score.get("confirmed"):
            text += f" {score.get('label')}"
            evidence.append("score")
        text += "."
    elif key in {"HT", "HALFTIME", "DESCANSO"}:
        summary_type = "HALFTIME_SUMMARY"
        text = f"{home} y {away} están al descanso"
        if score.get("confirmed"):
            text += f" con marcador {score.get('label')}"
            evidence.append("score")
        text += "."
    elif lifecycle.get("is_live"):
        summary_type = "LIVE_SUMMARY"
        text = f"{home} y {away} están disputando el partido"
        if score.get("confirmed"):
            text += f" con marcador {score.get('label')}"
            evidence.append("score")
        text += "."
    else:
        summary_type = "PREMATCH_SUMMARY"
        text = f"{home} y {away} tienen un partido programado."
    items.append({"type": summary_type, "text": text, "evidence": evidence})
    if lineups.get("confirmed"):
        items.append({
            "type": "LINEUP_SUMMARY",
            "text": f"Hay {lineups.get('player_count')} jugadores confirmados en las alineaciones disponibles.",
            "evidence": ["confirmed_lineup_cache"],
        })
    if event_summary.get("available"):
        items.append({
            "type": "EVENTS_SUMMARY",
            "text": f"La cronología contiene {event_summary.get('count')} eventos confirmados.",
            "evidence": ["canonical_timeline"],
        })
    if statistics.get("available"):
        items.append({
            "type": "STATS_SUMMARY",
            "text": f"Hay {statistics.get('item_count')} métricas comparables confirmadas.",
            "evidence": ["provider_stats_cache"],
        })
    if lifecycle.get("is_finished") and shark_context.get("available"):
        items.append({
            "type": "POSTMATCH_SHARK_REVIEW",
            "text": _text(shark_context.get("headline")) or "SHARK dispone de evidencia postpartido.",
            "evidence": list(shark_context.get("evidence") or []),
        })
    return {
        "contract": "NEMESIS-FACTUAL-MATCH-SUMMARIES-V1",
        "available": bool(items),
        "current_type": summary_type,
        "items": items,
        "generative_ai_calls": 0,
        "unsupported_claims": 0,
    }




def _lifecycle_from_domain(
    canonical_match: Mapping[str, Any],
    *,
    raw_match: Mapping[str, Any] | None = None,
    live: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    match = _mapping(canonical_match)
    raw = _mapping(raw_match)
    tracker = _mapping(live)
    truth_source = dict(raw)
    if tracker.get("available"):
        tracker_status = tracker.get("status") or tracker.get("status_short") or tracker.get("phase")
        if tracker_status:
            truth_source["provider_status"] = tracker_status
        tracker_updated = tracker.get("updated_at") or tracker.get("last_synced_at")
        if tracker_updated:
            truth_source["live_updated_at"] = tracker_updated
    truth = match_status_truth(truth_source)
    lifecycle = _text(truth.get("lifecycle") or "INCOMPLETE").upper()
    labels = {
        "UPCOMING": "Programado",
        "LIVE": "En directo",
        "HALFTIME": "Descanso",
        "FINISHED": "Finalizado",
        "RESULT_PENDING": "Resultado pendiente",
        "POSTPONED": "Aplazado",
        "SUSPENDED": "Suspendido",
        "CANCELLED": "Cancelado",
        "ABANDONED": "Abandonado",
        "STALE": "Actualización pendiente",
        "ARCHIVED": "Finalizado",
        "INCOMPLETE": "Estado pendiente",
    }
    return {
        "key": lifecycle,
        "label": labels.get(lifecycle, "Estado pendiente"),
        "is_finished": bool(truth.get("is_finished")),
        "is_live": bool(truth.get("is_live")),
        "is_stale": bool(truth.get("is_stale")),
        "stale_reason": truth.get("stale_reason") or "",
        "minute": match.get("minute") if truth.get("is_live") else None,
        "phase": lifecycle.lower(),
        "source": match.get("source") or raw.get("source"),
        "evidence_state": match.get("data_quality") or "INSUFFICIENT_DATA",
        "status_contract": truth.get("contract"),
    }

def _score_from_domain(canonical_match: Mapping[str, Any], display: Mapping[str, Any]) -> dict[str, Any]:
    score = _mapping(_mapping(canonical_match).get("score"))
    if score.get("confirmed"):
        return {
            "home": score.get("home"),
            "away": score.get("away"),
            "label": score.get("label") or f"{score.get('home')}-{score.get('away')}",
            "confirmed": True,
        }
    label = _text(display.get("client_score_label"))
    if label.lower() in {"", "-", "vs", "pendiente"}:
        label = "VS"
    return {"home": None, "away": None, "label": label or "VS", "confirmed": False}


def _team_view_from_domain(entity: Mapping[str, Any], *, side: str) -> dict[str, Any]:
    team = _mapping(entity)
    name = _text(team.get("display_name") or team.get("official_name")) or (
        "Equipo local pendiente" if side == "home" else "Equipo visitante pendiente"
    )
    return {
        "id": team.get("canonical_team_id"),
        "name": name,
        "logo": team.get("crest"),
        "flag": team.get("country_flag") or team.get("flag"),
        "href": _entity_href("team", team.get("canonical_team_id"), name),
        "source": team.get("source"),
        "data_quality": team.get("data_quality"),
        "limitations": list(team.get("limitations") or []),
    }


def _teams_from_domain(canonical_match: Mapping[str, Any]) -> dict[str, Any]:
    match = _mapping(canonical_match)
    return {
        "home": _team_view_from_domain(_mapping(match.get("home_team")), side="home"),
        "away": _team_view_from_domain(_mapping(match.get("away_team")), side="away"),
    }


def _competition_from_domain(canonical_match: Mapping[str, Any]) -> dict[str, Any]:
    competition = _mapping(_mapping(canonical_match).get("competition"))
    name = _text(competition.get("display_name") or competition.get("official_name"))
    identifier = competition.get("canonical_competition_id")
    available = bool(name and competition.get("data_quality") != "INSUFFICIENT_DATA")
    return {
        "id": identifier,
        "name": name or "Competición pendiente",
        "round": _text(_mapping(canonical_match).get("round") or competition.get("stage")),
        "country": _text(competition.get("country")),
        "flag": competition.get("logo"),
        "href": _entity_href("competition", identifier, name) if identifier else "",
        "available": available,
        "source": competition.get("source"),
        "data_quality": competition.get("data_quality"),
        "limitations": list(competition.get("limitations") or []),
    }


def _timeline_from_domain(canonical_events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for event in canonical_events or []:
        item = legacy_event_from_entity(event)
        if not item:
            continue
        entity = _mapping(event)
        if entity.get("provider_event_id"):
            item["id"] = entity.get("provider_event_id")
        item["canonical_event_id"] = entity.get("canonical_event_id")
        item["timeline_event_contract"] = entity.get("contract")
        item["canonical_event"] = dict(event)
        timeline.append(item)
    return timeline


def _freshness_label(freshness: Mapping[str, Any]) -> str:
    state = _text(_mapping(freshness).get("state")).lower()
    return {
        "fresh": "Fresco",
        "aging": "Válido con antigüedad",
        "stale": "Desactualizado",
        "unknown": "Frescura desconocida",
        "unavailable": "No disponible",
    }.get(state, "No disponible")


def _evidence_label(value: Any) -> str:
    key = _text(value).upper()
    return {
        "VERIFIED": "Confirmado",
        "PARTIALLY_VERIFIED": "Parcial",
        "NOT_CERTIFIED": "No certificado",
        "NOT_CONFIGURED": "No configurado",
        "STALE": "Desactualizado",
        "BLOCKED_BY_ACCESS": "Bloqueado por acceso",
        "HYPOTHESIS": "Hipótesis",
        "INSUFFICIENT_DATA": "Datos insuficientes",
        "REQUIRES_REVIEW": "Requiere revisión",
        "AVAILABLE": "Disponible",
        "PARTIAL": "Parcial",
    }.get(key, "No certificado")



def _public_limitation(value: Any) -> str:
    text = _text(value)[:180]
    lower = text.lower()
    if not text:
        return "Información pendiente."
    if "source timestamp" in lower or "marca temporal" in lower:
        return "No hay marca temporal confirmada."
    if "outside the freshness" in lower or "stale" in lower:
        return "La información está fuera de la ventana de frescura."
    if "team crest" in lower or "crest" in lower:
        return "Escudo no disponible."
    if "competition logo" in lower or "logo" in lower:
        return "Logo no disponible."
    if "team name" in lower:
        return "Nombre de equipo pendiente."
    if "competition name" in lower:
        return "Nombre de competición pendiente."
    if "player photo" in lower:
        return "Foto de jugador no disponible."
    if "player name" in lower:
        return "Nombre de jugador pendiente."
    if "fallback id" in lower or "stable visible facts" in lower:
        return "Identificador derivado de datos visibles, pendiente de confirmación oficial."
    if "multiple provider" in lower or "explicit mapping" in lower:
        return "Hay identificadores de proveedor que requieren revisión."
    if "no safe identifier" in lower:
        return "No existe identificador seguro confirmado."
    if "fresh_provider_statistics" in lower:
        return "Faltan estadísticas frescas del proveedor."
    if "canonical_match_status" in lower or "match_status" in lower:
        return "Estado del partido pendiente."
    return text

def _source_label(value: Any) -> str:
    source = _text(value).replace("_", " ")
    return source.title() if source else "Fuente no identificada"


def _transparency_block(
    *,
    source: Any,
    evidence_state: Any,
    freshness: Mapping[str, Any] | None,
    limitations: Iterable[Any] = (),
    confidence: Any = None,
) -> dict[str, Any]:
    fresh = _mapping(freshness)
    clean_limitations = [_public_limitation(item) for item in limitations if _text(item)]
    return {
        "source": _source_label(source),
        "evidence": _evidence_label(evidence_state),
        "freshness": _freshness_label(fresh),
        "confidence": confidence if confidence not in (None, "") else "No probabilística",
        "limitations": clean_limitations[:3],
    }

def _navigation(
    teams: Mapping[str, Any],
    competition: Mapping[str, Any],
    timeline: list[dict[str, Any]],
    lineups: Mapping[str, Any] | None = None,
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
    for team in _items(_mapping(lineups).get("teams")):
        for player in _items(team.get("starters")) + _items(team.get("substitutes")):
            player_id = _text(player.get("player_id"))
            if not player_id or player_id in seen_players:
                continue
            seen_players.add(player_id)
            players.append({
                "id": player_id,
                "name": _text(player.get("name")) or "Jugador confirmado",
                "href": _entity_href("player", player_id, player.get("name")),
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
    lineups: dict[str, Any]
    head_to_head: dict[str, Any]
    standings: dict[str, Any]
    summaries: dict[str, Any]
    media: dict[str, Any]
    facts: dict[str, Any]
    intelligence: dict[str, Any]
    shark_context: dict[str, Any]
    navigation: dict[str, Any]
    story: dict[str, Any]
    live_story: dict[str, Any]
    domain_model: dict[str, Any]
    sports_graph: dict[str, Any]
    sports_knowledge: dict[str, Any]
    telegram_readonly_contract: dict[str, Any]
    transparency: dict[str, dict[str, Any]]
    experience_blocks: list[dict[str, Any]]
    absent_information: list[str]
    prepared_integrations: list[dict[str, Any]]
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
    lineups = _lineups_context(detail_data.get("lineups") or [])
    media = _mapping(detail_data.get("media"))
    live_events = _items(live.get("events"))
    raw_timeline_total = len(live_events)
    if live_events:
        provider = _text(live.get("provider"))
        raw_timeline = [
            {**event, "source": _text(event.get("source")) or provider}
            for event in live_events
        ]
    else:
        raw_timeline_source = _items(detail_data.get("timeline") or detail_data.get("events"))
        raw_timeline_total = len(raw_timeline_source)
        raw_timeline = [
            event
            for event in raw_timeline_source
            if _text(event.get("source") or event.get("provider"))
        ]

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
    canonical_timeline = _items(
        domain_model.get("timeline_events") or canonical_match.get("events")
    )
    timeline = _timeline_from_domain(canonical_timeline)
    live_story = build_match_live_story(match, raw_timeline)
    latest_event = timeline[-1] if timeline else {}
    event_summary = {
        "contract": "SPORTS-CORE-TIMELINE-EVENT-V1",
        "available": bool(timeline),
        "count": len(timeline),
        "latest": latest_event,
        "items": timeline,
        "raw_count": raw_timeline_total,
        "excluded_without_evidence": max(0, raw_timeline_total - len(canonical_timeline)),
        "source": _text(canonical_match.get("source") or live.get("provider")) or None,
    }

    lifecycle = _lifecycle_from_domain(canonical_match, raw_match=match, live=live)
    score = _score_from_domain(canonical_match, display)
    shell_identity = {
        "id": canonical_match.get("canonical_match_id") or match.get("id"),
        "home_team": _mapping(canonical_match.get("home_team")).get("display_name") or match.get("home_team"),
        "away_team": _mapping(canonical_match.get("away_team")).get("display_name") or match.get("away_team"),
    }
    shell_state = _shell_state(shell_identity, lifecycle, offline=offline)
    statistics = _real_statistics(
        live,
        lifecycle,
        _mapping(detail_data.get("cached_statistics")),
    )
    head_to_head = _head_to_head_context(detail_data.get("head_to_head"))
    standings = _standings_context(detail_data.get("standings"))
    picks = {
        "available": bool(related_picks),
        "count": len(related_picks),
        "items": related_picks,
    }

    teams = _teams_from_domain(canonical_match)
    facts = _match_facts(match)
    competition = _competition_from_domain(canonical_match)
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

    navigation = _navigation(teams, competition, timeline, lineups)
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
        historical=head_to_head.get("items"),
        observed_at_madrid=(
            madrid_time.get("iso")
            or live.get("updated_at")
            or match.get("updated_at")
        ),
    )
    shark_context = build_shark_match_intelligence_state(intelligence)
    summaries = _factual_summaries(
        match,
        lifecycle,
        score,
        event_summary,
        statistics,
        lineups,
        shark_context,
    )
    telegram_readonly_contract = build_telegram_readonly_contract(
        match_entity=canonical_match,
        match_intelligence=intelligence,
        timeline_events=canonical_timeline,
        evidence=intelligence.get("evidence"),
        freshness=canonical_match.get("freshness"),
    )
    sports_knowledge = build_sports_knowledge_snapshot(
        domain_model=domain_model,
        match_intelligence=intelligence,
        timeline_events=canonical_timeline,
        related_picks=related_picks,
        now_madrid=(
            madrid_time.get("iso")
            or live.get("updated_at")
            or match.get("updated_at")
        ),
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
    if not lineups["confirmed"]:
        limitations.append("Alineación todavía no confirmada.")
    if not head_to_head["available"]:
        limitations.append("Sin enfrentamientos directos confirmados.")
    if not standings["available"]:
        limitations.append("Sin clasificación confirmada.")
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
        "LineupsPanel": _component(
            "ready" if lineups["confirmed"] else "partial",
            lineups["message"],
            available=lineups["confirmed"],
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
        "HeadToHeadPanel": _component(
            "ready" if head_to_head["available"] else "partial",
            "Enfrentamientos directos confirmados."
            if head_to_head["available"]
            else "No hay enfrentamientos directos confirmados.",
            available=head_to_head["available"],
        ),
        "StandingsPanel": _component(
            "ready" if standings["available"] else "partial",
            "Clasificación confirmada."
            if standings["available"]
            else "No hay clasificación confirmada.",
            available=standings["available"],
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

    freshness = _mapping(canonical_match.get("freshness"))
    intelligence_quality = _mapping(intelligence.get("quality"))
    intelligence_state = intelligence.get("certification_state") or canonical_match.get("data_quality")
    match_limitations = list(canonical_match.get("limitations") or [])
    missing_from_conclusions = sorted({
        _text(item)
        for conclusion in _mapping(intelligence.get("conclusions")).values()
        if isinstance(conclusion, Mapping)
        for item in (conclusion.get("missing_information") or [])
        if _text(item)
    })
    absent_information = sorted({
        item
        for item in (limitations + match_limitations + missing_from_conclusions)
        if _text(item)
    })
    risk_conclusion = _mapping(_mapping(intelligence.get("conclusions")).get("riesgo"))
    risk_value = _mapping(risk_conclusion.get("value"))
    risk_flags = _items(risk_value.get("flags"))
    risk_limitations = list(risk_conclusion.get("limitations") or [])
    if not risk_flags and not risk_limitations:
        risk_limitations = ["No hay riesgos deportivos confirmados con la evidencia actual."]

    transparency = {
        "summary": _transparency_block(
            source=canonical_match.get("source"),
            evidence_state=canonical_match.get("data_quality"),
            freshness=freshness,
            limitations=match_limitations,
        ),
        "status": _transparency_block(
            source=lifecycle.get("source") or canonical_match.get("source"),
            evidence_state=lifecycle.get("evidence_state"),
            freshness=freshness,
            limitations=match_limitations,
        ),
        "score": _transparency_block(
            source=canonical_match.get("source"),
            evidence_state="VERIFIED" if score.get("confirmed") else "INSUFFICIENT_DATA",
            freshness=freshness,
            limitations=[] if score.get("confirmed") else ["Marcador no confirmado."],
        ),
        "timeline": _transparency_block(
            source=event_summary.get("source"),
            evidence_state="VERIFIED" if event_summary.get("available") else "INSUFFICIENT_DATA",
            freshness=freshness,
            limitations=[] if event_summary.get("available") else ["Sin eventos confirmados."],
        ),
        "intelligence": _transparency_block(
            source=canonical_match.get("source"),
            evidence_state=intelligence_state,
            freshness=freshness,
            confidence=intelligence_quality.get("quality_label") or intelligence_quality.get("numeric_confidence_score"),
            limitations=intelligence.get("limitations") or missing_from_conclusions,
        ),
        "statistics": _transparency_block(
            source=statistics.get("source"),
            evidence_state="VERIFIED" if statistics.get("available") else "INSUFFICIENT_DATA",
            freshness=freshness,
            limitations=[] if statistics.get("available") else ["Sin estadísticas confirmadas."],
        ),
        "lineups": _transparency_block(
            source=lineups.get("source"),
            evidence_state="VERIFIED" if lineups.get("confirmed") else "INSUFFICIENT_DATA",
            freshness={"state": "fresh" if lineups.get("updated_at") else "unknown"},
            limitations=[] if lineups.get("confirmed") else ["Alineación todavía no confirmada."],
        ),
        "head_to_head": _transparency_block(
            source=head_to_head.get("source"),
            evidence_state="VERIFIED" if head_to_head.get("available") else "INSUFFICIENT_DATA",
            freshness={"state": "persisted" if head_to_head.get("updated_at") else "unknown"},
            limitations=[] if head_to_head.get("available") else ["Sin enfrentamientos directos confirmados."],
        ),
        "standings": _transparency_block(
            source=standings.get("source"),
            evidence_state="VERIFIED" if standings.get("available") else "INSUFFICIENT_DATA",
            freshness={"state": "persisted" if standings.get("updated_at") else "unknown"},
            limitations=[] if standings.get("available") else ["Sin clasificación confirmada."],
        ),
        "data_quality": _transparency_block(
            source=canonical_match.get("source"),
            evidence_state=canonical_match.get("data_quality"),
            freshness=freshness,
            limitations=absent_information,
        ),
    }
    experience_blocks = [
        {"id": "summary", "label": "Resumen del partido", "available": True},
        {"id": "status", "label": "Estado actual", "available": lifecycle.get("key") != "UNKNOWN"},
        {"id": "score", "label": "Marcador", "available": score.get("confirmed")},
        {"id": "timeline", "label": "Cronología", "available": event_summary.get("available")},
        {"id": "intelligence", "label": "Inteligencia", "available": shark_context.get("available")},
        {"id": "evidence", "label": "Evidencia", "available": bool(intelligence.get("evidence"))},
        {"id": "context", "label": "Contexto", "available": competition.get("available")},
        {"id": "teams", "label": "Equipos", "available": bool(teams.get("home") and teams.get("away"))},
        {"id": "competition", "label": "Competición", "available": competition.get("available")},
        {"id": "statistics", "label": "Estadísticas disponibles", "available": statistics.get("available")},
        {"id": "lineups", "label": "Alineaciones", "available": lineups.get("confirmed")},
        {"id": "head_to_head", "label": "Enfrentamientos directos", "available": head_to_head.get("available")},
        {"id": "standings", "label": "Clasificación", "available": standings.get("available")},
        {"id": "video", "label": "Vídeo autorizado", "available": bool(media.get("visible_count"))},
        {"id": "risks", "label": "Riesgos", "available": bool(risk_flags)},
        {"id": "data_quality", "label": "Calidad de datos", "available": True},
        {"id": "freshness", "label": "Frescura", "available": bool(freshness)},
        {"id": "missing", "label": "Información ausente", "available": bool(absent_information)},
    ]
    prepared_integrations = [
        {"name": "Team Center", "state": "Preparado", "contract": navigation.get("contract"), "write_authorized": False},
        {"name": "Competition Center", "state": "Preparado", "contract": navigation.get("contract"), "write_authorized": False},
        {"name": "Player Center", "state": "Conectado" if navigation.get("players") else "Preparado", "contract": navigation.get("contract"), "write_authorized": False},
        {"name": "Sports Graph", "state": "Preparado", "contract": _mapping(domain_model.get("sports_graph")).get("contract"), "write_authorized": False},
        {"name": "Sports Knowledge", "state": "Preparado", "contract": sports_knowledge.get("contract"), "write_authorized": False},
        {"name": "SHARK", "state": "Conectado", "contract": intelligence.get("contract"), "write_authorized": False},
        {"name": "Telegram", "state": "Solo lectura", "contract": telegram_readonly_contract.get("contract"), "write_authorized": False},
        {"name": "Video", "state": "Disponible" if media.get("visible_count") else "Bloqueado o no disponible", "contract": "NEMESIS-MEDIA-RIGHTS-GUARD-V1", "write_authorized": False},
    ]
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
        lineups=lineups,
        head_to_head=head_to_head,
        standings=standings,
        summaries=summaries,
        media=media,
        facts=facts,
        intelligence=intelligence,
        shark_context=shark_context,
        navigation=navigation,
        story=story,
        live_story=live_story,
        domain_model=domain_model,
        sports_graph=_mapping(domain_model.get("sports_graph")),
        sports_knowledge=sports_knowledge,
        telegram_readonly_contract=telegram_readonly_contract,
        transparency=transparency,
        experience_blocks=experience_blocks,
        absent_information=absent_information,
        prepared_integrations=prepared_integrations,
        components=components,
        evidence={
            "source": _source_label(canonical_match.get("source") or match.get("source") or match.get("v935_source")),
            "updated_at": canonical_match.get("source_timestamp") or match.get("updated_at"),
            "certification_state": _evidence_label(canonical_match.get("data_quality") or ("PARTIAL" if limitations else "AVAILABLE")),
            "match_id": canonical_match.get("canonical_match_id") or match.get("id") or detail_data.get("id"),
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
            "sports_knowledge_contract": sports_knowledge.get("contract"),
            "sports_knowledge_single_domain_snapshot": _mapping(sports_knowledge.get("diagnostics")).get("single_domain_snapshot"),
            "sports_knowledge_database_writes": _mapping(sports_knowledge.get("diagnostics")).get("database_writes"),
            "sports_knowledge_external_calls": _mapping(sports_knowledge.get("diagnostics")).get("external_calls"),
            "head_to_head_external_calls": head_to_head.get("external_calls"),
            "standings_external_calls": standings.get("external_calls"),
            "statistics_snapshot_kind": statistics.get("snapshot_kind"),
            "telegram_readonly_contract": telegram_readonly_contract.get("contract"),
            "component_contracts": list(MATCH_CENTER_COMPONENTS),
            "canonical_states": list(CANONICAL_COMPONENT_STATES),
            "timeline_event_contract": event_summary.get("contract"),
            "lineups_contract": lineups.get("contract"),
            "lineup_players": lineups.get("player_count"),
            "factual_summary_contract": summaries.get("contract"),
            "media_visible": media.get("visible_count", 0),
            "match_center_2_transparency": True,
            "experience_blocks": [item["id"] for item in experience_blocks],
        },
    )
    return context.to_dict()
