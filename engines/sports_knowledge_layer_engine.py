"""Shared read-only sports knowledge layer for NeMeSiS SHARK PRO.

This module is not a provider adapter, route, API, UI component or scheduler.
It receives canonical Sports Core snapshots already built by callers and
organizes reusable knowledge contracts with provenance, evidence, freshness,
limitations and quality. It never reads databases, calls providers, sends
messages, writes files, triggers payments or invents unavailable facts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import MATCH_INTELLIGENCE_CONTRACT
from engines.sports_domain_model_engine import (
    EVIDENCE_STATES as SPORTS_DOMAIN_EVIDENCE_STATES,
    SPORTS_DOMAIN_MODEL_CONTRACT,
)


SPORTS_KNOWLEDGE_LAYER_CONTRACT = "SPORTS-KNOWLEDGE-LAYER-V1"
TEAM_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-TEAM-V1"
COMPETITION_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-COMPETITION-V1"
MATCH_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-MATCH-V1"
SEASON_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-SEASON-V1"
RIVALRY_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-RIVALRY-V1"
CHRONOLOGICAL_KNOWLEDGE_CONTRACT = "SPORTS-KNOWLEDGE-CHRONOLOGY-V1"

SPORTS_KNOWLEDGE_EVIDENCE_STATES = tuple(SPORTS_DOMAIN_EVIDENCE_STATES)

SPORTS_KNOWLEDGE_CONSUMERS = (
    "match_center",
    "team_center",
    "competition_center",
    "player_center",
    "shark",
    "telegram",
    "picks",
    "live_center",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _state(value: Any) -> str:
    candidate = _text(value, 80).upper()
    return candidate if candidate in SPORTS_KNOWLEDGE_EVIDENCE_STATES else "REQUIRES_REVIEW"


def _first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _freshness(match: Mapping[str, Any] | None = None) -> dict[str, Any]:
    fresh = _mapping(_mapping(match).get("freshness"))
    if fresh:
        return fresh
    return {
        "state": "unknown",
        "usable_for_intelligence": False,
        "limitations": ["Freshness was not supplied by the canonical snapshot."],
    }


def _quality_from_evidence(
    evidence: Iterable[Mapping[str, Any]],
    *,
    required: Iterable[str] = (),
    fallback_state: str = "INSUFFICIENT_DATA",
) -> dict[str, Any]:
    items = _items(list(evidence))
    missing = [_text(item, 80) for item in required if _text(item, 80)]
    states = {_state(item.get("state") or item.get("evidence_state")) for item in items}
    if not items:
        state = fallback_state
    elif "STALE" in states:
        state = "STALE"
    elif "REQUIRES_REVIEW" in states:
        state = "REQUIRES_REVIEW"
    elif "INSUFFICIENT_DATA" in states:
        state = "PARTIALLY_VERIFIED"
    elif missing:
        state = "PARTIALLY_VERIFIED"
    else:
        state = "VERIFIED"
    return {
        "state": _state(state),
        "evidence_count": len(items),
        "required_missing": missing,
        "numeric_confidence_score": None,
        "quality_is_not_probability": True,
    }


def _evidence_item(
    evidence_id: str,
    *,
    kind: str,
    source: Any,
    state: str,
    value: Any = None,
    limitations: Iterable[Any] = (),
) -> dict[str, Any]:
    return {
        "id": _text(evidence_id, 160),
        "kind": _text(kind, 80),
        "source": _text(source, 120) or "canonical_snapshot",
        "state": _state(state),
        "value": value,
        "limitations": [_text(item, 180) for item in limitations if _text(item, 180)],
    }


def _contract(
    *,
    contract: str,
    subject_type: str,
    subject_id: Any = "",
    source: Any = "",
    evidence: Iterable[Mapping[str, Any]] = (),
    freshness: Mapping[str, Any] | None = None,
    limitations: Iterable[Any] = (),
    quality_state: str = "",
    facts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_items = _items(list(evidence))
    fresh = _mapping(freshness)
    limit_items = [_text(item, 200) for item in limitations if _text(item, 200)]
    quality = _quality_from_evidence(
        evidence_items,
        fallback_state=quality_state or "INSUFFICIENT_DATA",
    )
    if quality_state:
        quality["state"] = _state(quality_state)
    return {
        "contract": contract,
        "subject_type": _text(subject_type, 80),
        "subject_id": _text(subject_id, 160) or None,
        "source": _text(source, 120) or "canonical_snapshot",
        "evidence": evidence_items,
        "freshness": fresh,
        "limitations": limit_items,
        "quality": quality,
        "certification_state": quality["state"],
        "facts": _mapping(facts),
        "read_only": True,
        "database_write_authorized": False,
        "external_action_authorized": False,
        "telegram_send_authorized": False,
        "stripe_action_authorized": False,
    }


def build_team_knowledge(
    team_entity: Mapping[str, Any] | None,
    *,
    role: str = "",
    match_entity: Mapping[str, Any] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    picks: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build read-only knowledge for one team from canonical inputs."""

    team = _mapping(team_entity)
    match = _mapping(match_entity)
    events = _items(timeline_events)
    team_name = _text(team.get("display_name"), 160)
    canonical_id = team.get("canonical_team_id")
    side = _text(role or team.get("side"), 40)
    team_events = [
        item
        for item in events
        if _text(item.get("team_side"), 40) == side
        or (team_name and _text(item.get("team_name"), 160) == team_name)
    ]
    related_picks = [
        item
        for item in _items(picks)
        if _text(item.get("team") or item.get("selection"), 160) == team_name
    ]
    evidence = []
    if canonical_id or team_name:
        evidence.append(
            _evidence_item(
                f"team:{canonical_id or team_name}",
                kind="canonical_team_identity",
                source=team.get("source") or match.get("source"),
                state=team.get("data_quality") or "PARTIALLY_VERIFIED",
                value={"name": team_name, "role": side},
                limitations=team.get("limitations") or (),
            )
        )
    if team_events:
        evidence.append(
            _evidence_item(
                f"team-events:{canonical_id or team_name}",
                kind="canonical_timeline_events_for_team",
                source=match.get("source"),
                state="VERIFIED",
                value={"count": len(team_events)},
            )
        )
    limitations = list(team.get("limitations") or [])
    if not team_events:
        limitations.append("No hay eventos específicos del equipo confirmados en la cronología disponible.")
    if not related_picks:
        limitations.append("No hay conocimiento de picks relacionado disponible para este equipo.")
    return _contract(
        contract=TEAM_KNOWLEDGE_CONTRACT,
        subject_type="team",
        subject_id=canonical_id,
        source=team.get("source") or match.get("source"),
        evidence=evidence,
        freshness=_freshness(match),
        limitations=limitations,
        quality_state=team.get("data_quality") or ("PARTIALLY_VERIFIED" if evidence else "INSUFFICIENT_DATA"),
        facts={
            "display_name": team_name or None,
            "role": side or None,
            "country": team.get("country"),
            "logo": team.get("logo"),
            "competition_ids": team.get("competition_ids") or [],
            "timeline_event_count": len(team_events),
            "related_pick_count": len(related_picks),
        },
    )


def build_competition_knowledge(
    competition_entity: Mapping[str, Any] | None,
    *,
    match_entity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    competition = _mapping(competition_entity)
    match = _mapping(match_entity)
    competition_id = competition.get("canonical_competition_id")
    evidence = []
    if competition_id or competition.get("display_name"):
        evidence.append(
            _evidence_item(
                f"competition:{competition_id or competition.get('display_name')}",
                kind="canonical_competition_identity",
                source=competition.get("source") or match.get("source"),
                state=competition.get("data_quality") or "PARTIALLY_VERIFIED",
                value={
                    "name": competition.get("display_name"),
                    "country": competition.get("country"),
                    "season": competition.get("season") or match.get("season"),
                },
                limitations=competition.get("limitations") or (),
            )
        )
    limitations = list(competition.get("limitations") or [])
    if not competition.get("season") and not match.get("season"):
        limitations.append("Season is not confirmed for this competition.")
    return _contract(
        contract=COMPETITION_KNOWLEDGE_CONTRACT,
        subject_type="competition",
        subject_id=competition_id,
        source=competition.get("source") or match.get("source"),
        evidence=evidence,
        freshness=_freshness(match),
        limitations=limitations,
        quality_state=competition.get("data_quality") or ("PARTIALLY_VERIFIED" if evidence else "INSUFFICIENT_DATA"),
        facts={
            "display_name": competition.get("display_name"),
            "country": competition.get("country"),
            "season": competition.get("season") or match.get("season"),
            "round": match.get("round"),
            "stage": competition.get("stage") or match.get("stage"),
            "competition_type": competition.get("competition_type"),
        },
    )


def build_match_knowledge(
    match_entity: Mapping[str, Any] | None,
    *,
    match_intelligence: Mapping[str, Any] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    related_picks: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    match = _mapping(match_entity)
    intelligence = _mapping(match_intelligence)
    events = _items(timeline_events if timeline_events is not None else match.get("events"))
    picks = _items(related_picks)
    evidence = []
    if match.get("canonical_match_id"):
        evidence.append(
            _evidence_item(
                f"match:{match.get('canonical_match_id')}",
                kind="canonical_match_identity",
                source=match.get("source"),
                state=match.get("data_quality") or "PARTIALLY_VERIFIED",
                value={
                    "status": match.get("status"),
                    "phase": match.get("phase"),
                    "score": match.get("score"),
                },
                limitations=match.get("limitations") or (),
            )
        )
    if intelligence.get("contract") == MATCH_INTELLIGENCE_CONTRACT:
        evidence.append(
            _evidence_item(
                f"match-intelligence:{match.get('canonical_match_id') or 'unknown'}",
                kind="match_intelligence_contract",
                source=match.get("source"),
                state=intelligence.get("certification_state") or "PARTIALLY_VERIFIED",
                value={
                    "supported_conclusions": _mapping(intelligence.get("quality")).get("supported_conclusions"),
                    "total_conclusions": _mapping(intelligence.get("quality")).get("total_conclusions"),
                },
                limitations=intelligence.get("limitations") or (),
            )
        )
    if events:
        evidence.append(
            _evidence_item(
                f"timeline:{match.get('canonical_match_id') or 'unknown'}",
                kind="canonical_timeline",
                source=match.get("source"),
                state="VERIFIED",
                value={"count": len(events)},
            )
        )
    limitations = list(match.get("limitations") or [])
    if not events:
        limitations.append("No confirmed timeline events are available.")
    if not picks:
        limitations.append("No hay picks relacionados disponibles en el snapshot suministrado.")
    return _contract(
        contract=MATCH_KNOWLEDGE_CONTRACT,
        subject_type="match",
        subject_id=match.get("canonical_match_id"),
        source=match.get("source"),
        evidence=evidence,
        freshness=_freshness(match),
        limitations=limitations,
        quality_state=match.get("data_quality") or ("PARTIALLY_VERIFIED" if evidence else "INSUFFICIENT_DATA"),
        facts={
            "status": match.get("status"),
            "phase": match.get("phase"),
            "minute": match.get("minute"),
            "score": match.get("score"),
            "venue": match.get("venue"),
            "officials": match.get("officials") or [],
            "timeline_event_count": len(events),
            "related_pick_count": len(picks),
        },
    )


def build_season_knowledge(match_entity: Mapping[str, Any] | None) -> dict[str, Any]:
    match = _mapping(match_entity)
    competition = _mapping(match.get("competition"))
    season = _first_present(match.get("season"), competition.get("season"))
    evidence = []
    if season:
        evidence.append(
            _evidence_item(
                f"season:{season}",
                kind="season_from_canonical_match",
                source=match.get("source") or competition.get("source"),
                state="PARTIALLY_VERIFIED",
                value={"season": season, "round": match.get("round"), "stage": match.get("stage")},
                limitations=("Season context is limited to the supplied match snapshot.",),
            )
        )
    limitations = []
    if not season:
        limitations.append("Season is not confirmed.")
    if not match.get("round"):
        limitations.append("Round is not confirmed.")
    return _contract(
        contract=SEASON_KNOWLEDGE_CONTRACT,
        subject_type="season",
        subject_id=season,
        source=match.get("source") or competition.get("source"),
        evidence=evidence,
        freshness=_freshness(match),
        limitations=limitations,
        quality_state="PARTIALLY_VERIFIED" if season else "INSUFFICIENT_DATA",
        facts={
            "season": season,
            "round": match.get("round"),
            "stage": match.get("stage"),
            "competition_id": competition.get("canonical_competition_id"),
        },
    )


def build_rivalry_knowledge(
    match_entity: Mapping[str, Any] | None,
    *,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    match = _mapping(match_entity)
    home = _mapping(match.get("home_team"))
    away = _mapping(match.get("away_team"))
    events = _items(timeline_events if timeline_events is not None else match.get("events"))
    subject_id = " vs ".join(
        item
        for item in (
            _text(home.get("canonical_team_id") or home.get("display_name"), 120),
            _text(away.get("canonical_team_id") or away.get("display_name"), 120),
        )
        if item
    )
    evidence = []
    if home or away:
        evidence.append(
            _evidence_item(
                f"rivalry:{subject_id or 'unknown'}",
                kind="match_participants",
                source=match.get("source"),
                state="PARTIALLY_VERIFIED" if home and away else "INSUFFICIENT_DATA",
                value={
                    "home": home.get("display_name"),
                    "away": away.get("display_name"),
                    "event_count": len(events),
                },
                limitations=("No historical rivalry claim is inferred from one match snapshot.",),
            )
        )
    limitations = ["Head-to-head history is not supplied to this layer."]
    if not (home and away):
        limitations.append("Both teams are required to describe rivalry context.")
    return _contract(
        contract=RIVALRY_KNOWLEDGE_CONTRACT,
        subject_type="rivalry",
        subject_id=subject_id,
        source=match.get("source"),
        evidence=evidence,
        freshness=_freshness(match),
        limitations=limitations,
        quality_state="PARTIALLY_VERIFIED" if home and away else "INSUFFICIENT_DATA",
        facts={
            "home_team": home.get("display_name"),
            "away_team": away.get("display_name"),
            "timeline_event_count": len(events),
            "head_to_head_available": False,
        },
    )


def build_chronological_knowledge(
    match_entity: Mapping[str, Any] | None,
    *,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    now_madrid: Any = "",
) -> dict[str, Any]:
    match = _mapping(match_entity)
    events = _items(timeline_events if timeline_events is not None else match.get("events"))
    kickoff = match.get("kickoff_at")
    evidence = []
    if kickoff or match.get("status"):
        evidence.append(
            _evidence_item(
                f"chronology:{match.get('canonical_match_id') or kickoff or 'unknown'}",
                kind="match_time_status",
                source=match.get("source"),
                state=match.get("data_quality") or "PARTIALLY_VERIFIED",
                value={
                    "kickoff_at": kickoff,
                    "timezone": match.get("timezone"),
                    "status": match.get("status"),
                    "phase": match.get("phase"),
                    "minute": match.get("minute"),
                    "observed_at_madrid": _text(now_madrid, 80) or None,
                },
            )
        )
    if events:
        evidence.append(
            _evidence_item(
                f"chronology-events:{match.get('canonical_match_id') or 'unknown'}",
                kind="ordered_timeline_events",
                source=match.get("source"),
                state="VERIFIED",
                value={
                    "first_event": events[0].get("canonical_event_id"),
                    "last_event": events[-1].get("canonical_event_id"),
                    "count": len(events),
                },
            )
        )
    limitations = []
    if not kickoff:
        limitations.append("Kickoff time is not confirmed.")
    if not events:
        limitations.append("No ordered timeline events are available.")
    return _contract(
        contract=CHRONOLOGICAL_KNOWLEDGE_CONTRACT,
        subject_type="chronology",
        subject_id=match.get("canonical_match_id"),
        source=match.get("source"),
        evidence=evidence,
        freshness=_freshness(match),
        limitations=limitations,
        quality_state=match.get("data_quality") or ("PARTIALLY_VERIFIED" if evidence else "INSUFFICIENT_DATA"),
        facts={
            "kickoff_at": kickoff,
            "timezone": match.get("timezone"),
            "status": match.get("status"),
            "phase": match.get("phase"),
            "minute": match.get("minute"),
            "timeline_event_count": len(events),
            "observed_at_madrid": _text(now_madrid, 80) or None,
        },
    )


def build_future_consumer_contracts() -> dict[str, dict[str, Any]]:
    return {
        consumer: {
            "consumer": consumer,
            "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            "read_only": True,
            "database_write_authorized": False,
            "external_action_authorized": False,
            "telegram_send_authorized": False,
            "implementation_state": "prepared_not_enabled",
        }
        for consumer in SPORTS_KNOWLEDGE_CONSUMERS
    }


def build_sports_knowledge_snapshot(
    *,
    match_entity: Mapping[str, Any] | None = None,
    domain_model: Mapping[str, Any] | None = None,
    match_intelligence: Mapping[str, Any] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    related_picks: Iterable[Mapping[str, Any]] | None = None,
    now_madrid: Any = "",
) -> dict[str, Any]:
    """Create one shared knowledge snapshot from canonical Sports Core input."""

    domain = _mapping(domain_model)
    match = _mapping(match_entity or domain.get("match"))
    timeline = _items(timeline_events if timeline_events is not None else domain.get("timeline_events") or match.get("events"))
    teams = _items(domain.get("teams"))
    home = _mapping(match.get("home_team") or (teams[0] if len(teams) > 0 else {}))
    away = _mapping(match.get("away_team") or (teams[1] if len(teams) > 1 else {}))
    competition = _mapping(domain.get("competition") or match.get("competition"))
    picks = _items(related_picks)
    source_contract = domain.get("contract") or SPORTS_DOMAIN_MODEL_CONTRACT

    team_knowledge = {
        "home": build_team_knowledge(
            home,
            role="home",
            match_entity=match,
            timeline_events=timeline,
            picks=picks,
        ),
        "away": build_team_knowledge(
            away,
            role="away",
            match_entity=match,
            timeline_events=timeline,
            picks=picks,
        ),
    }
    competition_knowledge = build_competition_knowledge(competition, match_entity=match)
    match_knowledge = build_match_knowledge(
        match,
        match_intelligence=match_intelligence,
        timeline_events=timeline,
        related_picks=picks,
    )
    season_knowledge = build_season_knowledge(match)
    rivalry_knowledge = build_rivalry_knowledge(match, timeline_events=timeline)
    chronological_knowledge = build_chronological_knowledge(
        match,
        timeline_events=timeline,
        now_madrid=now_madrid,
    )
    all_contracts = [
        match_knowledge,
        competition_knowledge,
        season_knowledge,
        rivalry_knowledge,
        chronological_knowledge,
        *team_knowledge.values(),
    ]
    limitations = sorted({
        _text(item, 220)
        for contract in all_contracts
        for item in contract.get("limitations") or []
        if _text(item, 220)
    })
    verified_count = sum(
        contract.get("certification_state") in {"VERIFIED", "PARTIALLY_VERIFIED"}
        for contract in all_contracts
    )
    if any(contract.get("certification_state") == "STALE" for contract in all_contracts):
        state = "STALE"
    elif verified_count == len(all_contracts):
        state = "VERIFIED"
    elif verified_count:
        state = "PARTIALLY_VERIFIED"
    else:
        state = "INSUFFICIENT_DATA"
    return {
        "ok": True,
        "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "source_domain_contract": source_contract,
        "source_intelligence_contract": _mapping(match_intelligence).get("contract"),
        "match_id": match.get("canonical_match_id"),
        "observed_at_madrid": _text(now_madrid, 80) or match.get("source_timestamp"),
        "certification_state": state,
        "team_knowledge": team_knowledge,
        "competition_knowledge": competition_knowledge,
        "match_knowledge": match_knowledge,
        "season_knowledge": season_knowledge,
        "rivalry_knowledge": rivalry_knowledge,
        "chronological_knowledge": chronological_knowledge,
        "future_consumers": build_future_consumer_contracts(),
        "evidence_graph": {
            "source": "sports_core_snapshot",
            "domain_contract": source_contract,
            "sports_graph_contract": _mapping(domain.get("sports_graph")).get("contract"),
            "edge_count": len(_items(_mapping(domain.get("sports_graph")).get("edges"))),
            "persistence_authorized": False,
        },
        "limitations": limitations,
        "quality": {
            "contract_count": len(all_contracts),
            "verified_or_partial_contracts": verified_count,
            "numeric_confidence_score": None,
            "quality_is_not_sport_probability": True,
        },
        "diagnostics": {
            "database_queries": 0,
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "fake_data_created": 0,
            "single_domain_snapshot": True,
            "new_provider_calls": 0,
            "new_cache_writes": 0,
        },
        "read_only": True,
        "no_fake_data": True,
    }


def sports_knowledge_layer_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "source_contracts": [
            SPORTS_DOMAIN_MODEL_CONTRACT,
            MATCH_INTELLIGENCE_CONTRACT,
        ],
        "knowledge_contracts": [
            TEAM_KNOWLEDGE_CONTRACT,
            COMPETITION_KNOWLEDGE_CONTRACT,
            MATCH_KNOWLEDGE_CONTRACT,
            SEASON_KNOWLEDGE_CONTRACT,
            RIVALRY_KNOWLEDGE_CONTRACT,
            CHRONOLOGICAL_KNOWLEDGE_CONTRACT,
        ],
        "consumers_prepared": list(SPORTS_KNOWLEDGE_CONSUMERS),
        "states": list(SPORTS_KNOWLEDGE_EVIDENCE_STATES),
        "guardrails": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "automatic_actions": 0,
        },
    }
