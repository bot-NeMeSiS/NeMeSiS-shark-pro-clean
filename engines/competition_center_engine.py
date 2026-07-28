"""Premium Competition Center context built on Sports Core contracts.

The builder receives already loaded local/cache data and organizes it through
the Unified Sports Domain Model, Sports Knowledge Layer and Sports Graph. It
does not read databases, call providers, send Telegram, touch Stripe, write
files or invent unavailable sports facts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import build_match_intelligence
from engines.sports_domain_model_engine import (
    SPORTS_DOMAIN_MODEL_CONTRACT,
    build_unified_domain_snapshot,
    normalize_competition_entity,
    normalize_team_entity,
)
from engines.sports_graph_foundation_engine import (
    SPORTS_GRAPH_FOUNDATION_CONTRACT,
    build_sports_graph_relationships,
)
from engines.sports_knowledge_layer_engine import (
    COMPETITION_KNOWLEDGE_CONTRACT,
    SEASON_KNOWLEDGE_CONTRACT,
    SPORTS_KNOWLEDGE_LAYER_CONTRACT,
    build_competition_knowledge,
    build_season_knowledge,
    build_sports_knowledge_snapshot,
)


COMPETITION_CENTER_CONTRACT = "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _score_number(value: Any) -> int | None:
    return _as_int(value)


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


def _result_for_team(match: Mapping[str, Any], team_name: str) -> str:
    home = _text(match.get("home_team") or match.get("safe_home"), 160).casefold()
    away = _text(match.get("away_team") or match.get("safe_away"), 160).casefold()
    target = _text(team_name, 160).casefold()
    home_score = _score_number(match.get("home_score"))
    away_score = _score_number(match.get("away_score"))
    if not target or target not in {home, away} or home_score is None or away_score is None:
        return ""
    goals_for = home_score if target == home else away_score
    goals_against = away_score if target == home else home_score
    if goals_for > goals_against:
        return "V"
    if goals_for == goals_against:
        return "E"
    return "D"


def _team_recent_form(matches: Iterable[Mapping[str, Any]], team_name: str) -> dict[str, Any]:
    sequence: list[str] = []
    for match in _items(matches):
        result = _result_for_team(match, team_name)
        if result:
            sequence.append(result)
        if len(sequence) >= 5:
            break
    wins = sequence.count("V")
    draws = sequence.count("E")
    losses = sequence.count("D")
    if len(sequence) >= 3 and wins > losses:
        trend = "Sube"
    elif len(sequence) >= 3 and losses > wins:
        trend = "Baja"
    elif len(sequence) >= 3:
        trend = "Estable"
    else:
        trend = "No disponible"
    return {
        "sequence": sequence,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "trend": trend,
        "available": bool(sequence),
        "limitations": [] if len(sequence) >= 3 else ["Muestra insuficiente para tendencia fiable."],
    }


def _team_catalog_from_matches(matches: Iterable[Mapping[str, Any]], teams: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for raw in _items(teams):
        canonical = normalize_team_entity(raw, provider=raw.get("source") or "local_cache")
        key = canonical.get("canonical_team_id") or canonical.get("display_name")
        if key:
            catalog[str(key)] = {"canonical": canonical, "matches": []}
    for match in _items(matches):
        for side in ("home", "away"):
            name = match.get(f"{side}_team") or match.get(f"safe_{side}")
            if not name:
                continue
            raw_team = {
                "team_id": match.get(f"{side}_team_id"),
                "name": name,
                "display_name": name,
                "country": match.get("country"),
                "competition_id": match.get("competition_id"),
                "logo": match.get(f"{side}_logo"),
                "source": match.get("source") or "matches",
            }
            canonical = normalize_team_entity(raw_team, provider=raw_team.get("source"))
            key = canonical.get("canonical_team_id") or canonical.get("display_name")
            if not key:
                continue
            catalog.setdefault(str(key), {"canonical": canonical, "matches": []})["matches"].append(match)
    result: list[dict[str, Any]] = []
    for item in catalog.values():
        canonical = item["canonical"]
        related_matches = item.get("matches") or []
        form = _team_recent_form(
            sorted(
                related_matches,
                key=lambda match: (match.get("match_date") or "", match.get("kickoff_time") or ""),
                reverse=True,
            ),
            canonical.get("display_name") or canonical.get("official_name") or "",
        )
        result.append({
            "canonical": canonical,
            "name": canonical.get("display_name") or canonical.get("official_name") or "Equipo no disponible",
            "country": canonical.get("country") or "No disponible",
            "crest": canonical.get("crest"),
            "route_id": _team_route_id(canonical),
            "matches": len(related_matches),
            "form": form,
            "data_quality": canonical.get("data_quality") or "PARTIALLY_VERIFIED",
            "limitations": canonical.get("limitations") or [],
        })
    return sorted(result, key=lambda item: item["name"])


def _standings_rows(
    standings: Iterable[Mapping[str, Any]],
    *,
    fallback_teams: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw in _items(standings):
        team_name = _text(raw.get("team_name") or raw.get("name"), 160)
        if not team_name:
            continue
        goals_for = _as_int(raw.get("goals_for"))
        goals_against = _as_int(raw.get("goals_against"))
        goal_difference = None
        if goals_for is not None and goals_against is not None:
            goal_difference = goals_for - goals_against
        description = _text(raw.get("description"), 160)
        state = "Confirmado"
        lowered = description.casefold()
        if "champion" in lowered or "campe" in lowered:
            state = "Campeon"
        elif "europa" in lowered or "champions" in lowered:
            state = "Europa"
        elif "play" in lowered:
            state = "Playoff"
        elif "descenso" in lowered or "releg" in lowered:
            state = "Descenso"
        rows.append({
            "position": _as_int(raw.get("rank") or raw.get("position")),
            "team_name": team_name,
            "team_route_id": _text(raw.get("team_id"), 160) or team_name,
            "points": _as_int(raw.get("points")),
            "played": _as_int(raw.get("played")),
            "wins": _as_int(raw.get("wins")),
            "draws": _as_int(raw.get("draws")),
            "losses": _as_int(raw.get("losses")),
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goal_difference,
            "form": _text(raw.get("form"), 12) or "No disponible",
            "trend": "No disponible",
            "state": state,
            "source": raw.get("source") or "api_football_standings_deep",
            "evidence": "standings_row",
            "limitations": [] if raw.get("rank") or raw.get("points") else ["Clasificacion parcial sin posicion o puntos confirmados."],
        })
    rows = sorted(rows, key=lambda item: item.get("position") or 999)
    return {
        "available": bool(rows),
        "rows": rows[:24],
        "source": "api_football_standings_deep" if rows else "No disponible",
        "limitations": [] if rows else ["No hay clasificacion oficial sincronizada para esta competicion."],
        "fallback_team_count": len(_items(fallback_teams)),
    }


def _calendar(matches: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = _items(matches)
    upcoming = [
        item for item in items
        if _text(_mapping(item.get("status_info")).get("label") or item.get("status"), 60).casefold() not in {"finalizado", "ft", "finished", "final"}
    ]
    recent = [
        item for item in items
        if item not in upcoming
    ]
    rounds: dict[str, int] = {}
    for item in items:
        label = _text(item.get("round") or item.get("round_name"), 120)
        if label:
            rounds[label] = rounds.get(label, 0) + 1
    current_round = next(iter(sorted(rounds, key=lambda key: (-rounds[key], key))), "")
    return {
        "current_round": current_round or "No disponible",
        "upcoming": sorted(upcoming, key=lambda item: (item.get("match_date") or "", item.get("kickoff_time") or ""))[:12],
        "recent": sorted(recent, key=lambda item: (item.get("match_date") or "", item.get("kickoff_time") or ""), reverse=True)[:12],
        "rounds": [{"label": key, "matches": value} for key, value in sorted(rounds.items())[:12]],
        "limitations": [] if items else ["No hay partidos reales asociados a esta competicion."],
    }


def _competition_state(matches: Iterable[Mapping[str, Any]], competition: Mapping[str, Any]) -> str:
    items = _items(matches)
    live = [item for item in items if _mapping(item.get("status_info")).get("is_live")]
    upcoming = [item for item in items if _mapping(item.get("status_info")).get("is_upcoming")]
    recent = [item for item in items if _mapping(item.get("status_info")).get("is_finished")]
    if live:
        return "Con partidos en directo"
    if upcoming and recent:
        return "Temporada en curso"
    if upcoming:
        return "Calendario preparado"
    if recent:
        return "Resultados disponibles"
    if competition:
        return "Informacion parcial"
    return "No disponible"


def _shark_competition_context(
    *,
    matches: Iterable[Mapping[str, Any]],
    standings: Mapping[str, Any],
    season: Any = "",
    round_label: Any = "",
) -> dict[str, Any]:
    items = _items(matches)
    live_count = sum(1 for item in items if _mapping(item.get("status_info")).get("is_live"))
    upcoming_count = sum(1 for item in items if _mapping(item.get("status_info")).get("is_upcoming"))
    recent_count = sum(1 for item in items if _mapping(item.get("status_info")).get("is_finished"))
    signals: list[str] = []
    if live_count:
        signals.append(f"{live_count} partidos en directo confirmados en la muestra local.")
    if upcoming_count and recent_count:
        signals.append("La competicion tiene calendario y resultados disponibles.")
    elif upcoming_count:
        signals.append("La competicion tiene proximos partidos disponibles.")
    elif recent_count:
        signals.append("La competicion solo tiene resultados recientes en la muestra disponible.")
    if standings.get("available"):
        signals.append("Existe clasificacion sincronizada para contextualizar objetivos.")
    if season:
        signals.append(f"Temporada confirmada: {season}.")
    if round_label and round_label != "No disponible":
        signals.append(f"Jornada o fase visible: {round_label}.")
    return {
        "available": bool(signals),
        "state": "PARTIALLY_VERIFIED" if signals else "INSUFFICIENT_DATA",
        "summary": " ".join(signals) if signals else "No hay suficiente informacion para construir contexto SHARK de competicion.",
        "limitations": [] if signals else ["SHARK no genera predicciones ni contexto sin evidencia real."],
        "source": "competition_center_context",
        "evidence": signals,
    }


def build_competition_center_context(
    detail: Mapping[str, Any] | None,
    *,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build the visible Competition Center context from already loaded facts."""

    data = _mapping(detail)
    raw_competition = _mapping(data.get("competition"))
    matches = _items(data.get("matches"))
    standings_input = _items(data.get("standings"))
    picks = _items(data.get("picks"))
    teams_input = _items(data.get("teams"))
    competition = normalize_competition_entity(
        {
            "canonical_competition_id": raw_competition.get("canonical_competition_id"),
            "competition_id": raw_competition.get("external_id") or raw_competition.get("competition_id") or raw_competition.get("id"),
            "competition_name": raw_competition.get("name") or raw_competition.get("competition_name"),
            "display_name": raw_competition.get("display_name") or raw_competition.get("name"),
            "country": raw_competition.get("country"),
            "season": raw_competition.get("season"),
            "stage": raw_competition.get("stage") or raw_competition.get("round"),
            "competition_type": raw_competition.get("scope") or raw_competition.get("competition_type"),
            "logo": raw_competition.get("logo") or raw_competition.get("logo_url"),
            "source": raw_competition.get("source") or "local_cache",
        },
        provider=raw_competition.get("source") or "local_cache",
    )
    domain_snapshots = [_domain_for_match(match, now_madrid=observed_at_madrid) for match in matches[:80]]
    canonical_matches = [_mapping(snapshot.get("match")) for snapshot in domain_snapshots]
    canonical_events = [
        event
        for snapshot in domain_snapshots
        for event in _items(snapshot.get("timeline_events"))
    ]
    teams = _team_catalog_from_matches(matches, teams_input)
    canonical_teams = [item["canonical"] for item in teams]
    anchor_domain = domain_snapshots[0] if domain_snapshots else {}
    anchor_match = _mapping(anchor_domain.get("match"))
    anchor_competition = _mapping(anchor_domain.get("competition")) or competition
    if anchor_competition.get("canonical_competition_id"):
        competition.update({
            key: anchor_competition.get(key)
            for key in (
                "canonical_competition_id",
                "provider_competition_ids",
                "season",
                "stage",
                "data_quality",
                "source",
            )
            if anchor_competition.get(key)
        })
    intelligence = (
        build_match_intelligence(
            canonical_match=anchor_match,
            canonical_timeline=_items(anchor_domain.get("timeline_events")),
            observed_at_madrid=observed_at_madrid,
        )
        if anchor_match
        else {}
    )
    competition_knowledge = build_competition_knowledge(
        competition,
        match_entity=anchor_match,
    )
    season_knowledge = build_season_knowledge(anchor_match)
    sports_knowledge = build_sports_knowledge_snapshot(
        domain_model=anchor_domain,
        match_intelligence=intelligence,
        timeline_events=_items(anchor_domain.get("timeline_events")),
        related_picks=picks,
        now_madrid=observed_at_madrid,
    ) if anchor_domain else {
        "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "certification_state": competition_knowledge.get("certification_state"),
        "limitations": ["Sports Knowledge completo requiere al menos un partido canonico asociado."],
        "diagnostics": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
        },
    }
    standings = _standings_rows(standings_input, fallback_teams=teams)
    calendar = _calendar(matches)
    graph = build_sports_graph_relationships(
        team_entities=canonical_teams,
        match_entities=canonical_matches,
        competition_entities=[competition],
        timeline_events=canonical_events,
        evidence_items=competition_knowledge.get("evidence") or [],
        match_intelligence=intelligence,
        picks=picks,
        telegram_context={"id": f"telegram:{competition.get('canonical_competition_id')}", "certification_state": "NOT_CONFIGURED"} if matches else {},
        shark_context={"id": f"shark:{competition.get('canonical_competition_id')}", "certification_state": intelligence.get("certification_state") or "INSUFFICIENT_DATA"} if intelligence else {},
        observed_at_madrid=observed_at_madrid,
        center="competition_center",
    )
    season = competition.get("season") or _mapping(season_knowledge.get("facts")).get("season")
    round_label = calendar.get("current_round") or competition.get("stage")
    shark = _shark_competition_context(
        matches=matches,
        standings=standings,
        season=season,
        round_label=round_label,
    )
    missing = []
    if not competition.get("logo"):
        missing.append("Logo no disponible: ninguna fuente lo confirma.")
    if not season:
        missing.append("Temporada no disponible.")
    if not competition.get("competition_type"):
        missing.append("Tipo de competicion no disponible.")
    if not standings.get("available"):
        missing.extend(standings.get("limitations") or [])
    if not matches:
        missing.append("No hay partidos asociados a esta competicion.")
    state = _competition_state(matches, competition)
    return {
        "ok": True,
        "contract": COMPETITION_CENTER_CONTRACT,
        "source_domain_contract": SPORTS_DOMAIN_MODEL_CONTRACT,
        "sports_knowledge_contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "competition_knowledge_contract": COMPETITION_KNOWLEDGE_CONTRACT,
        "season_knowledge_contract": SEASON_KNOWLEDGE_CONTRACT,
        "sports_graph_contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "competition": {
            "name": competition.get("display_name") or raw_competition.get("name") or "Competicion",
            "official_name": competition.get("official_name") or competition.get("display_name") or raw_competition.get("name") or "Competicion",
            "country": competition.get("country") or raw_competition.get("country") or "No disponible",
            "season": season or "No disponible",
            "type": competition.get("competition_type") or "No disponible",
            "stage": competition.get("stage") or round_label or "No disponible",
            "state": state,
            "logo": competition.get("logo"),
            "logo_source": competition.get("logo_source") or "No disponible",
            "canonical": competition,
            "route_id": _competition_route_id(competition),
        },
        "metrics": {
            "teams": len(teams),
            "matches": len(matches),
            "upcoming": len(calendar.get("upcoming") or []),
            "recent": len(calendar.get("recent") or []),
            "standings": len(standings.get("rows") or []),
            "picks": len(picks),
            "graph_edges": graph.get("edge_count", 0),
        },
        "standings": standings,
        "calendar": calendar,
        "teams": teams,
        "matches": matches,
        "picks": picks,
        "competition_knowledge": competition_knowledge,
        "season_knowledge": season_knowledge,
        "sports_knowledge": sports_knowledge,
        "sports_graph": graph,
        "shark_context": shark,
        "available_information": [
            item
            for item, available in (
                ("Identidad de competicion", bool(competition.get("display_name"))),
                ("Equipos relacionados", bool(teams)),
                ("Partidos relacionados", bool(matches)),
                ("Calendario", bool(calendar.get("upcoming") or calendar.get("recent"))),
                ("Clasificacion", bool(standings.get("available"))),
                ("Sports Graph", bool(graph.get("edge_count"))),
            )
            if available
        ],
        "missing_information": sorted(set(item for item in missing if item)),
        "data_quality": {
            "source": competition.get("source") or raw_competition.get("source") or "local_cache",
            "freshness": _mapping(anchor_match.get("freshness")),
            "certification_state": competition_knowledge.get("certification_state") or "PARTIALLY_VERIFIED",
            "limitations": sorted(set((competition_knowledge.get("limitations") or []) + missing)),
        },
        "links": {
            "calendar": "/calendar",
            "match_center": "/match/" + _text(matches[0].get("id"), 160) if matches else "",
            "team_center": "/team/" + _text(teams[0].get("route_id"), 160) if teams else "",
            "sports_graph": "",
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


def competition_center_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": COMPETITION_CENTER_CONTRACT,
        "requires": [
            SPORTS_DOMAIN_MODEL_CONTRACT,
            SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            SPORTS_GRAPH_FOUNDATION_CONTRACT,
        ],
        "guardrails": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "fake_data_created": 0,
        },
    }
