"""Premium Team Center context built on Sports Core contracts.

The builder receives data already loaded by Flask. It only normalizes and
organizes that data through the Unified Sports Domain Model, Sports Knowledge
Layer and Sports Graph relationships. It performs no IO or external action.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import build_match_intelligence
from engines.sports_domain_model_engine import (
    SPORTS_DOMAIN_MODEL_CONTRACT,
    build_unified_domain_snapshot,
    normalize_team_entity,
)
from engines.sports_graph_foundation_engine import (
    SPORTS_GRAPH_FOUNDATION_CONTRACT,
    build_sports_graph_relationships,
)
from engines.sports_knowledge_layer_engine import (
    SPORTS_KNOWLEDGE_LAYER_CONTRACT,
    build_sports_knowledge_snapshot,
    build_team_knowledge,
)


TEAM_CENTER_CONTRACT = "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _score_number(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


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


def _team_side(match: Mapping[str, Any], team_name: str) -> str:
    name = team_name.lower()
    if _text(match.get("home_team"), 160).lower() == name or _text(match.get("safe_home"), 160).lower() == name:
        return "home"
    if _text(match.get("away_team"), 160).lower() == name or _text(match.get("safe_away"), 160).lower() == name:
        return "away"
    return ""


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


def _result_for_team(match: Mapping[str, Any], team_name: str) -> dict[str, Any]:
    side = _team_side(match, team_name)
    home = _score_number(match.get("home_score"))
    away = _score_number(match.get("away_score"))
    if side not in {"home", "away"} or home is None or away is None:
        return {
            "available": False,
            "outcome": "No disponible",
            "goals_for": None,
            "goals_against": None,
            "limitation": "El marcador o el lado del equipo no estan confirmados.",
        }
    goals_for = home if side == "home" else away
    goals_against = away if side == "home" else home
    if goals_for > goals_against:
        outcome = "Victoria"
    elif goals_for == goals_against:
        outcome = "Empate"
    else:
        outcome = "Derrota"
    return {
        "available": True,
        "outcome": outcome,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "side": side,
    }


def _form_summary(matches: Iterable[Mapping[str, Any]], team_name: str) -> dict[str, Any]:
    items = []
    wins = draws = losses = goals_for = goals_against = 0
    for match in _items(matches):
        result = _result_for_team(match, team_name)
        if not result["available"]:
            continue
        if result["outcome"] == "Victoria":
            wins += 1
        elif result["outcome"] == "Empate":
            draws += 1
        elif result["outcome"] == "Derrota":
            losses += 1
        goals_for += int(result["goals_for"] or 0)
        goals_against += int(result["goals_against"] or 0)
        items.append({"match": match, **result})
        if len(items) >= 5:
            break
    sample = len(items)
    if sample >= 3 and wins > losses:
        trend = "Tendencia favorable en la muestra confirmada"
    elif sample >= 3 and losses > wins:
        trend = "Tendencia exigente en la muestra confirmada"
    elif sample >= 3:
        trend = "Tendencia equilibrada en la muestra confirmada"
    else:
        trend = "No disponible"
    return {
        "available": bool(items),
        "sample_size": sample,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "trend": trend,
        "items": items,
        "limitations": []
        if sample >= 3
        else ["Muestra insuficiente para declarar una tendencia deportiva."],
    }


def _strengths_and_weaknesses(form: Mapping[str, Any]) -> dict[str, Any]:
    sample = int(form.get("sample_size") or 0)
    strengths: list[str] = []
    weaknesses: list[str] = []
    limitations: list[str] = []
    if sample < 3:
        limitations.append("No hay muestra suficiente para detectar fortalezas o debilidades.")
    else:
        goals_for = int(form.get("goals_for") or 0)
        goals_against = int(form.get("goals_against") or 0)
        wins = int(form.get("wins") or 0)
        losses = int(form.get("losses") or 0)
        if wins > losses:
            strengths.append("Resultados recientes favorables en la muestra disponible.")
        if goals_for >= sample:
            strengths.append("Ha marcado en promedio al menos un gol por partido en la muestra.")
        if losses > wins:
            weaknesses.append("Resultados recientes desfavorables en la muestra disponible.")
        if goals_against >= sample:
            weaknesses.append("Ha encajado en promedio al menos un gol por partido en la muestra.")
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "limitations": limitations,
        "available": bool(strengths or weaknesses),
    }


def _timeline(matches: Iterable[Mapping[str, Any]], team_name: str) -> list[dict[str, Any]]:
    timeline = []
    for match in _items(matches)[:12]:
        result = _result_for_team(match, team_name)
        label = result["outcome"] if result.get("available") else _text(_mapping(match.get("live_depth")).get("label") or match.get("status"), 80) or "No disponible"
        timeline.append({
            "match_id": match.get("id") or match.get("match_id"),
            "label": label,
            "home": match.get("safe_home") or match.get("home_team"),
            "away": match.get("safe_away") or match.get("away_team"),
            "date": match.get("match_date") or match.get("kickoff_iso"),
            "score": _mapping(match.get("live_depth")).get("score") or match.get("score") or "No disponible",
            "source": match.get("source") or match.get("v935_source") or "local_cache",
        })
    return timeline


def build_team_center_context(
    detail: Mapping[str, Any] | None,
    *,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build the visible Team Center context from already loaded facts."""

    data = _mapping(detail)
    team = _mapping(data.get("team"))
    identity = _mapping(data.get("identity"))
    name = _text(data.get("name") or team.get("name") or identity.get("display_name"), 160) or "Equipo"
    upcoming = _items(data.get("upcoming"))
    recent = _items(data.get("recent"))
    live = _items(data.get("live"))
    picks = _items(data.get("picks"))
    matches = upcoming + recent
    source = team.get("source") or identity.get("crest_source") or "local_cache"
    canonical_team = normalize_team_entity(
        {
            "canonical_team_id": team.get("canonical_team_id"),
            "team_id": team.get("id") or team.get("key") or data.get("key"),
            "name": name,
            "official_name": team.get("official_name") or name,
            "country": team.get("country") or identity.get("country"),
            "logo": team.get("logo_url") or identity.get("logo_url") or identity.get("crest_url"),
            "competition_id": team.get("competition_id"),
            "source": source,
        },
        provider=source,
    )
    domain_snapshots = [_domain_for_match(match, now_madrid=observed_at_madrid) for match in matches[:24]]
    canonical_matches = [_mapping(snapshot.get("match")) for snapshot in domain_snapshots]
    canonical_events = [
        event
        for snapshot in domain_snapshots
        for event in _items(snapshot.get("timeline_events"))
    ]
    competitions = []
    seen_competitions = set()
    for snapshot in domain_snapshots:
        competition = _mapping(snapshot.get("competition"))
        comp_id = competition.get("canonical_competition_id") or competition.get("display_name")
        if comp_id and comp_id not in seen_competitions:
            seen_competitions.add(comp_id)
            competitions.append(competition)
    anchor_domain = domain_snapshots[0] if domain_snapshots else {}
    anchor_match = _mapping(anchor_domain.get("match"))
    intelligence = (
        build_match_intelligence(
            canonical_match=anchor_match,
            canonical_timeline=_items(anchor_domain.get("timeline_events")),
            observed_at_madrid=observed_at_madrid,
        )
        if anchor_match
        else {}
    )
    knowledge = build_team_knowledge(
        canonical_team,
        role="team_center",
        match_entity=anchor_match,
        timeline_events=canonical_events,
        picks=picks,
    )
    sports_knowledge = build_sports_knowledge_snapshot(
        domain_model=anchor_domain,
        match_intelligence=intelligence,
        timeline_events=_items(anchor_domain.get("timeline_events")),
        related_picks=picks,
        now_madrid=observed_at_madrid,
    )
    form = _form_summary(recent, name)
    traits = _strengths_and_weaknesses(form)
    graph = build_sports_graph_relationships(
        team_entity=canonical_team,
        match_entities=canonical_matches,
        competition_entities=competitions,
        timeline_events=canonical_events,
        evidence_items=knowledge.get("evidence") or [],
        match_intelligence=intelligence,
        picks=picks,
        telegram_context={"id": f"telegram:{canonical_team.get('canonical_team_id')}", "certification_state": "NOT_CONFIGURED"} if matches else {},
        shark_context={"id": f"shark:{canonical_team.get('canonical_team_id')}", "certification_state": intelligence.get("certification_state") or "INSUFFICIENT_DATA"} if intelligence else {},
        observed_at_madrid=observed_at_madrid,
    )
    missing = []
    if not team.get("stadium") and not team.get("venue"):
        missing.append("Estadio no disponible: ninguna fuente lo confirma.")
    if not team.get("founded") and not team.get("foundation_year"):
        missing.append("Fundación no disponible: ninguna fuente lo confirma.")
    if not form.get("available"):
        missing.append("Forma reciente pendiente de resultados confirmados.")
    if not traits.get("available"):
        missing.extend(traits.get("limitations") or [])
    state = "En directo" if live else "Con calendario" if upcoming else "Información parcial"
    return {
        "ok": True,
        "contract": TEAM_CENTER_CONTRACT,
        "source_domain_contract": SPORTS_DOMAIN_MODEL_CONTRACT,
        "sports_knowledge_contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "sports_graph_contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "team": {
            "name": name,
            "official_name": team.get("official_name") or name,
            "country": team.get("country") or identity.get("country") or "No disponible",
            "competition": team.get("league") or team.get("competition_name") or (competitions[0].get("display_name") if competitions else "No disponible"),
            "stadium": team.get("stadium") or team.get("venue") or "No disponible",
            "founded": team.get("founded") or team.get("foundation_year") or "No disponible",
            "state": state,
            "canonical": canonical_team,
            "identity": identity,
        },
        "metrics": {
            "upcoming": len(upcoming),
            "recent": len(recent),
            "live": len(live),
            "picks": len(picks),
            "competitions": len(competitions),
            "graph_edges": graph.get("edge_count", 0),
        },
        "form": form,
        "streak": {
            "label": form.get("trend") or "No disponible",
            "sample_size": form.get("sample_size") or 0,
            "limitations": form.get("limitations") or [],
        },
        "strengths": traits.get("strengths") or [],
        "weaknesses": traits.get("weaknesses") or [],
        "available_information": [
            item
            for item, available in (
                ("Identidad del equipo", bool(canonical_team.get("display_name"))),
                ("Partidos relacionados", bool(matches)),
                ("Competiciones relacionadas", bool(competitions)),
                ("Picks relacionados", bool(picks)),
                ("Sports Graph", bool(graph.get("edge_count"))),
            )
            if available
        ],
        "missing_information": sorted(set(item for item in missing if item)),
        "upcoming": upcoming,
        "recent": recent,
        "live": live,
        "picks": picks,
        "timeline": _timeline(matches, name),
        "competitions": competitions,
        "knowledge": knowledge,
        "sports_knowledge": sports_knowledge,
        "sports_graph": graph,
        "shark_context": {
            "available": bool(intelligence),
            "contract": intelligence.get("contract"),
            "state": intelligence.get("certification_state") or "INSUFFICIENT_DATA",
            "summary": data.get("shark_context") or "Contexto SHARK no disponible.",
            "limitations": intelligence.get("limitations") or ["No se crea IA nueva en Team Center."],
        },
        "data_quality": {
            "source": source,
            "freshness": anchor_match.get("freshness") or {},
            "certification_state": knowledge.get("certification_state") or "PARTIALLY_VERIFIED",
            "limitations": sorted(set((knowledge.get("limitations") or []) + missing)),
        },
        "links": {
            "competition_center": "/competition/" + _competition_route_id(competitions[0]) if competitions and _competition_route_id(competitions[0]) else "",
            "player_center": "",
            "match_center": "/match/" + _text(matches[0].get("id"), 160) if matches else "",
            "sports_graph": "",
        },
        "diagnostics": {
            "database_queries": 0,
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "new_dependencies": 0,
            "domain_snapshots": len(domain_snapshots),
            "single_domain_model_per_match": True,
        },
        "no_fake_data": True,
    }


def team_center_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": TEAM_CENTER_CONTRACT,
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
            "fake_data_created": 0,
        },
    }
