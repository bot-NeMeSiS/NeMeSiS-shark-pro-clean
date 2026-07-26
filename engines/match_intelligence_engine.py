"""Canonical evidence-backed intelligence for one sports match.

The engine is pure and deterministic. It receives facts already loaded by the
caller and never reads a database, calls a provider, sends a message, or
generates a sporting claim. Every derived value keeps its evidence and limits.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


MATCH_INTELLIGENCE_CONTRACT = "MATCH-INTELLIGENCE-EVIDENCE-V1"
MATCH_INTELLIGENCE_CONSUMERS = (
    "match_center",
    "team_center",
    "competition_center",
    "player_center",
    "shark",
    "telegram",
    "sports_graph",
)
EVIDENCE_STATES = (
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "NOT_CERTIFIED",
    "STALE",
    "INSUFFICIENT_DATA",
    "REQUIRES_REVIEW",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _minute(value: Any) -> int | None:
    candidate = _text(value, 16).replace("'", "")
    if not candidate:
        return None
    try:
        return int(float(candidate.split("+", 1)[0]))
    except (TypeError, ValueError):
        return None


def _state(value: Any) -> str:
    candidate = _text(value, 40).upper()
    return candidate if candidate in EVIDENCE_STATES else "REQUIRES_REVIEW"


def _evidence(
    evidence_id: str,
    *,
    kind: str,
    source: str,
    state: str,
    data: Mapping[str, Any] | None = None,
    observed_at: Any = "",
    limitations: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "kind": kind,
        "source": source or "source_not_identified",
        "state": _state(state),
        "observed_at_madrid": _text(observed_at, 80) or None,
        "data": _mapping(data),
        "limitations": [_text(item) for item in limitations if _text(item)],
    }


def _conclusion(
    key: str,
    *,
    state: str,
    value: Any = None,
    evidence_ids: Iterable[str] = (),
    supporting_data: Mapping[str, Any] | None = None,
    missing: Iterable[str] = (),
    method: str,
    limitations: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "key": key,
        "state": _state(state),
        "value": value,
        "evidence_ids": [item for item in evidence_ids if item],
        "supporting_data": _mapping(supporting_data),
        "missing_information": [_text(item) for item in missing if _text(item)],
        "method": method,
        "limitations": [_text(item) for item in limitations if _text(item)],
    }


def _canonical_phase(lifecycle: Mapping[str, Any]) -> tuple[str | None, str]:
    key = _text(lifecycle.get("key") or lifecycle.get("status"), 40).upper()
    if key in {"LIVE", "EN DIRECTO"}:
        minute = _minute(lifecycle.get("minute"))
        if minute is None:
            return "live_unspecified", "generic_live_status"
        if minute <= 45:
            return "first_half", "confirmed_match_minute"
        if minute <= 90:
            return "second_half", "confirmed_match_minute"
        return "live_unspecified", "generic_live_status_unclassified_minute"
    groups = (
        ({"FT", "FINISHED", "FINAL", "FINALIZADO", "AET", "PEN"}, "finished"),
        ({"HT", "HALFTIME", "DESCANSO"}, "halftime"),
        ({"2H", "SECOND_HALF"}, "second_half"),
        ({"1H", "FIRST_HALF"}, "first_half"),
        ({"ET", "EXTRA_TIME", "BT"}, "extra_time"),
        ({"P", "PENALTIES", "PENALTY_SHOOTOUT"}, "penalty_shootout"),
        ({"SUSP", "SUSPENDED", "INT", "POSTP", "POSTPONED"}, "interrupted"),
        ({"NS", "UPCOMING", "SCHEDULED", "PROGRAMADO"}, "pre_match"),
    )
    for statuses, phase in groups:
        if key in statuses:
            return phase, "status_taxonomy"
    return None, "insufficient_status"


def _key_event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _text(event.get("id"), 100),
        "type": _text(event.get("type") or event.get("event_type"), 60),
        "label": _text(event.get("label") or event.get("headline"), 160),
        "minute": event.get("minute"),
        "minute_label": _text(event.get("minute_label"), 24),
        "team": _text(event.get("team") or event.get("team_name"), 120),
        "player_id": _text(event.get("player_id"), 100),
        "player": _text(event.get("player") or event.get("player_name"), 120),
        "source": _text(event.get("source") or event.get("provider"), 80),
    }


def _legacy_event_from_canonical(event: Mapping[str, Any]) -> dict[str, Any]:
    item = _mapping(event)
    minute = item.get("minute")
    added = item.get("added_time") or 0
    minute_label = ""
    if minute is not None:
        minute_label = f"{minute}+{added}'" if added else f"{minute}'"
    return {
        "id": _text(item.get("canonical_event_id"), 120),
        "type": _text(item.get("event_type"), 60),
        "label": _text(item.get("event_type"), 60).replace("_", " ").title(),
        "minute": minute,
        "minute_label": minute_label,
        "team": _text(item.get("team_name"), 120),
        "player_id": _text(item.get("player_id"), 120),
        "player": _text(item.get("player_name"), 120),
        "related_player_id": _text(item.get("related_player_id"), 120),
        "related_player": _text(item.get("related_player_name"), 120),
        "source": _text(item.get("source"), 80),
        "is_key_event": item.get("event_type") in {"goal", "own_goal", "penalty_goal", "missed_penalty", "var", "red_card", "second_yellow"},
        "canonical_event": item,
    }


def _legacy_match_from_canonical(match: Mapping[str, Any]) -> dict[str, Any]:
    item = _mapping(match)
    home = _mapping(item.get("home_team"))
    away = _mapping(item.get("away_team"))
    competition = _mapping(item.get("competition"))
    score = _mapping(item.get("score"))
    return {
        "id": item.get("canonical_match_id"),
        "match_id": item.get("canonical_match_id"),
        "home_team_id": home.get("canonical_team_id"),
        "away_team_id": away.get("canonical_team_id"),
        "home_team": home.get("display_name"),
        "away_team": away.get("display_name"),
        "competition_id": competition.get("canonical_competition_id"),
        "competition_name": competition.get("display_name"),
        "status": item.get("phase") or item.get("status"),
        "minute": item.get("minute"),
        "home_score": score.get("home"),
        "away_score": score.get("away"),
        "score": score.get("label"),
        "source": item.get("source"),
        "updated_at": _mapping(item.get("freshness")).get("source_timestamp"),
        "is_stale": _mapping(item.get("freshness")).get("state") == "stale",
        "canonical": item,
    }

def _entity_context(
    match: Mapping[str, Any],
    competition: Mapping[str, Any],
    source: str,
    evidence_state: str,
) -> dict[str, Any]:
    match_id = _text(match.get("id") or match.get("match_id"), 120)
    entities = {
        "match": {
            "type": "match",
            "id": match_id,
            "label": " vs ".join(
                item
                for item in (
                    _text(match.get("home_team"), 120),
                    _text(match.get("away_team"), 120),
                )
                if item
            ),
        },
        "home_team": {
            "type": "team",
            "id": _text(match.get("home_team_id"), 120),
            "label": _text(match.get("home_team"), 120),
        },
        "away_team": {
            "type": "team",
            "id": _text(match.get("away_team_id"), 120),
            "label": _text(match.get("away_team"), 120),
        },
        "competition": {
            "type": "competition",
            "id": _text(
                competition.get("id")
                or match.get("competition_id")
                or match.get("competition_key"),
                120,
            ),
            "label": _text(
                competition.get("name") or match.get("competition_name"),
                160,
            ),
        },
    }
    for entity in entities.values():
        entity["source"] = source or "source_not_identified"
        entity["evidence_state"] = (
            evidence_state if entity["id"] else "INSUFFICIENT_DATA"
        )
    relationships = []
    for target, relationship in (
        ("home_team", "has_home_team"),
        ("away_team", "has_away_team"),
        ("competition", "belongs_to_competition"),
    ):
        if match_id and entities[target]["id"]:
            relationships.append({
                "source": "match",
                "relationship": relationship,
                "target": target,
                "evidence_state": evidence_state,
                "persistence_authorized": False,
            })
    return {
        "contract": "SPORTS-ENTITY-CENTER-CONTEXT-V1",
        "entities": entities,
        "relationships": relationships,
        "sports_graph_write_authorized": False,
    }


def build_match_intelligence_consumer_view(
    intelligence: Mapping[str, Any] | None,
    consumer: str,
) -> dict[str, Any]:
    """Return a read-only view of the same snapshot for one approved consumer."""

    snapshot = _mapping(intelligence)
    normalized_consumer = _text(consumer, 40).lower()
    if normalized_consumer not in MATCH_INTELLIGENCE_CONSUMERS:
        raise ValueError("unsupported_match_intelligence_consumer")
    conclusions = _mapping(snapshot.get("conclusions"))
    allowed = {
        "match_center": tuple(conclusions),
        "team_center": ("estado_partido", "fase", "eventos_clave", "tendencias"),
        "competition_center": (
            "estado_partido",
            "fase",
            "eventos_clave",
            "tendencias",
        ),
        "player_center": ("estado_partido", "fase", "eventos_clave"),
        "shark": (
            "estado_partido",
            "fase",
            "ritmo",
            "presion",
            "dominador",
            "equilibrio",
            "riesgo",
            "eventos_clave",
            "tendencias",
            "cambios_recientes",
        ),
        "telegram": (
            "estado_partido",
            "fase",
            "riesgo",
            "eventos_clave",
            "cambios_recientes",
        ),
        "sports_graph": ("estado_partido", "fase", "eventos_clave"),
    }[normalized_consumer]
    selected = {key: conclusions[key] for key in allowed if key in conclusions}
    referenced = {
        evidence_id
        for conclusion in selected.values()
        for evidence_id in conclusion.get("evidence_ids") or []
    }
    evidence = [
        dict(item)
        for item in snapshot.get("evidence") or []
        if isinstance(item, Mapping) and item.get("id") in referenced
    ]
    return {
        "contract": MATCH_INTELLIGENCE_CONTRACT,
        "consumer": normalized_consumer,
        "match_id": snapshot.get("match_id"),
        "certification_state": snapshot.get("certification_state")
        or "INSUFFICIENT_DATA",
        "conclusions": selected,
        "evidence": evidence,
        "entity_context": _mapping(snapshot.get("entity_context")),
        "limitations": list(snapshot.get("limitations") or []),
        "external_action_authorized": False,
        "database_write_authorized": False,
    }


def build_shark_match_intelligence_state(
    intelligence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build deterministic Match Center SHARK copy from the canonical snapshot."""

    view = build_match_intelligence_consumer_view(intelligence, "shark")
    conclusions = _mapping(view.get("conclusions"))
    pressure = _mapping(conclusions.get("presion"))
    dominant = _mapping(conclusions.get("dominador"))
    phase = _mapping(conclusions.get("fase"))
    changes = _mapping(conclusions.get("cambios_recientes"))
    pressure_value = _mapping(pressure.get("value"))
    dominant_value = _mapping(dominant.get("value"))
    phase_value = _mapping(phase.get("value"))
    recent_value = _mapping(changes.get("value"))
    interpretive_keys = (
        "ritmo",
        "presion",
        "dominador",
        "equilibrio",
        "eventos_clave",
        "cambios_recientes",
    )

    def has_interpretive_value(key: str) -> bool:
        conclusion = _mapping(conclusions.get(key))
        if conclusion.get("state") not in {"VERIFIED", "PARTIALLY_VERIFIED"}:
            return False
        value = conclusion.get("value")
        if value in (None, {}, []):
            return False
        if key in {"eventos_clave", "cambios_recientes"}:
            return bool(_mapping(value).get("count"))
        return True

    available = (
        view.get("certification_state") != "STALE"
        and any(has_interpretive_value(key) for key in interpretive_keys)
    )
    evidence_kind_labels = {
        "match_status": "Estado",
        "score": "Marcador",
        "derived_pressure": "Presion",
        "statistics_snapshot": "Estadisticas",
        "match_event": "Evento",
    }
    evidence_labels = []
    for item in view.get("evidence") or []:
        data = _mapping(item.get("data"))
        label = _text(
            data.get("label")
            or evidence_kind_labels.get(_text(item.get("kind"), 80))
            or "Evidencia deportiva",
            100,
        )
        if label and label not in evidence_labels:
            evidence_labels.append(label)
    signals = []
    if pressure_value.get("label"):
        signals.append(_text(pressure_value.get("label"), 140))
    recent_count = recent_value.get("count")
    if isinstance(recent_count, int) and recent_count > 0:
        noun = "cambio confirmado" if recent_count == 1 else "cambios confirmados"
        signals.append(f"{recent_count} {noun} en la ventana reciente")
    return {
        "contract": MATCH_INTELLIGENCE_CONTRACT,
        "available": available,
        "headline": (
            _text(dominant_value.get("headline"), 180)
            or _text(pressure_value.get("label"), 180)
            or "Contexto estructurado disponible"
        )
        if available
        else "",
        "phase": _text(
            phase_value.get("label") or phase_value.get("key"),
            120,
        )
        if available
        else "",
        "dominant_team": _text(dominant_value.get("team"), 120)
        if dominant.get("state") == "PARTIALLY_VERIFIED"
        else "",
        "signals": signals,
        "evidence": evidence_labels,
        "quality_label": {
            "VERIFIED": "Evidencia confirmada",
            "PARTIALLY_VERIFIED": "Evidencia parcial",
            "STALE": "Evidencia desactualizada",
        }.get(view.get("certification_state"), "Evidencia insuficiente"),
        "certification_state": view.get("certification_state"),
        "source": ",".join(
            sorted(
                {
                    _text(item.get("source"), 80)
                    for item in view.get("evidence") or []
                    if _text(item.get("source"), 80)
                }
            )
        ),
        "message": (
            "Lectura construida por el contrato unico con evidencia trazable."
            if available
            else "No disponible: faltan senales deportivas suficientes o frescas."
        ),
        "consumer_view": view,
    }


def build_match_intelligence(
    match: Mapping[str, Any] | None = None,
    picks: list[dict[str, Any]] | None = None,
    *,
    lifecycle: Mapping[str, Any] | None = None,
    score: Mapping[str, Any] | None = None,
    timeline: Iterable[Mapping[str, Any]] | None = None,
    statistics: Mapping[str, Any] | None = None,
    tracker: Mapping[str, Any] | None = None,
    historical: Iterable[Mapping[str, Any]] | None = None,
    competition: Mapping[str, Any] | None = None,
    canonical_match: Mapping[str, Any] | None = None,
    canonical_timeline: Iterable[Mapping[str, Any]] | None = None,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build one reusable structured snapshot from supplied factual inputs."""

    match_data = _mapping(match)
    canonical_match_data = _mapping(canonical_match)
    canonical_timeline_data = _items(canonical_timeline)
    if canonical_match_data and not match_data:
        match_data = _legacy_match_from_canonical(canonical_match_data)
    elif canonical_match_data:
        match_data.setdefault("canonical", canonical_match_data)
        match_data.setdefault("id", canonical_match_data.get("canonical_match_id"))
        match_data.setdefault("match_id", canonical_match_data.get("canonical_match_id"))
    picks_data = _items(picks)
    lifecycle_data = _mapping(lifecycle)
    score_data = _mapping(score)
    tracker_data = _mapping(tracker)
    statistics_data = _mapping(statistics)
    competition_data = _mapping(competition)
    timeline_data = [
        dict(item) for item in (timeline or []) if isinstance(item, Mapping)
    ]
    historical_data = [
        dict(item) for item in (historical or []) if isinstance(item, Mapping)
    ]
    if canonical_timeline_data and not timeline_data:
        timeline_data = [_legacy_event_from_canonical(item) for item in canonical_timeline_data]

    if not lifecycle_data:
        lifecycle_data = {
            "key": match_data.get("status"),
            "label": match_data.get("client_status_label") or match_data.get("status"),
            "minute": match_data.get("minute"),
            "is_stale": bool(match_data.get("is_stale") or match_data.get("stale")),
        }
    if not score_data:
        score_data = {
            "home": match_data.get("home_score"),
            "away": match_data.get("away_score"),
            "label": match_data.get("score") or match_data.get("client_score_label"),
            "confirmed": (
                match_data.get("home_score") is not None
                and match_data.get("away_score") is not None
            ),
        }
    if not timeline_data:
        timeline_data = _items(tracker_data.get("events"))
    if not statistics_data:
        tracker_cards = _items(tracker_data.get("stat_cards"))
        statistics_data = {
            "available": bool(tracker_cards),
            "items": tracker_cards,
            "source": tracker_data.get("provider"),
            "updated_at": tracker_data.get("updated_at"),
        }

    source = _text(
        tracker_data.get("provider")
        or match_data.get("source")
        or match_data.get("v935_source"),
        100,
    )
    observed_at = (
        _text(observed_at_madrid, 80)
        or _text(tracker_data.get("updated_at"), 80)
        or _text(match_data.get("updated_at"), 80)
    )
    stale = bool(
        lifecycle_data.get("is_stale")
        or tracker_data.get("is_stale")
        or match_data.get("is_stale")
        or match_data.get("stale")
    )
    current_state = "STALE" if stale else "VERIFIED"
    evidence: list[dict[str, Any]] = []

    status_key = _text(
        lifecycle_data.get("key") or match_data.get("status"),
        40,
    ).upper()
    status_label = _text(
        lifecycle_data.get("label")
        or match_data.get("client_status_label")
        or match_data.get("status"),
        100,
    )
    status_evidence_id = ""
    if status_key or status_label:
        status_evidence_id = "match-status"
        evidence.append(
            _evidence(
                status_evidence_id,
                kind="match_status",
                source=source,
                state=current_state,
                observed_at=observed_at,
                data={
                    "key": status_key,
                    "label": status_label,
                    "minute": lifecycle_data.get("minute") or match_data.get("minute"),
                },
            )
        )
    score_evidence_id = ""
    if score_data.get("confirmed") or _text(score_data.get("label"), 40):
        score_evidence_id = "match-score"
        evidence.append(
            _evidence(
                score_evidence_id,
                kind="score",
                source=source,
                state=current_state,
                observed_at=observed_at,
                data={
                    "home": score_data.get("home"),
                    "away": score_data.get("away"),
                    "label": _text(score_data.get("label"), 40),
                    "confirmed": bool(score_data.get("confirmed")),
                },
            )
        )

    quality = _mapping(tracker_data.get("quality"))
    pressure = _mapping(tracker_data.get("pressure"))
    field_state = _mapping(tracker_data.get("field_state"))
    game_flow = _mapping(tracker_data.get("game_flow"))
    pressure_evidence_id = ""
    if pressure.get("available") and not stale:
        pressure_evidence_id = "provider-pressure"
        evidence.append(
            _evidence(
                pressure_evidence_id,
                kind="derived_pressure",
                source=_text(pressure.get("source"), 100) or source,
                state="PARTIALLY_VERIFIED",
                observed_at=observed_at,
                data={
                    "label": _text(pressure.get("label"), 160),
                    "home_pct": pressure.get("home_pct"),
                    "away_pct": pressure.get("away_pct"),
                    "input_evidence": list(quality.get("evidence") or []),
                },
                limitations=(
                    "Derived from available provider statistics; it is not ball location or a probability.",
                ),
            )
        )

    statistics_evidence_id = ""
    statistic_items = _items(statistics_data.get("items"))
    if statistics_data.get("available") and statistic_items and not stale:
        statistics_evidence_id = "provider-statistics"
        evidence.append(
            _evidence(
                statistics_evidence_id,
                kind="statistics_snapshot",
                source=_text(statistics_data.get("source"), 100) or source,
                state="VERIFIED",
                observed_at=statistics_data.get("updated_at") or observed_at,
                data={
                    "count": len(statistic_items),
                    "keys": [
                        _text(item.get("key") or item.get("label"), 80)
                        for item in statistic_items
                    ],
                },
            )
        )

    event_evidence_ids: list[str] = []
    normalized_events: list[dict[str, Any]] = []
    for index, event in enumerate(timeline_data):
        payload = _key_event_payload(event)
        event_id = payload["id"] or f"event-{index + 1}"
        evidence_id = f"event:{event_id}"
        event_evidence_ids.append(evidence_id)
        normalized_events.append(payload)
        evidence.append(
            _evidence(
                evidence_id,
                kind="match_event",
                source=payload["source"] or source,
                state="VERIFIED",
                observed_at=observed_at,
                data=payload,
                limitations=(
                    "A confirmed event remains historical evidence even when the live snapshot later becomes stale.",
                ),
            )
        )

    phase_key, phase_method = _canonical_phase(lifecycle_data)
    upstream_phase = _text(game_flow.get("phase"), 120)
    phase_value = (
        {
            "key": phase_key,
            "label": status_label or phase_key,
            "provider_reading": upstream_phase or None,
        }
        if phase_key or upstream_phase
        else None
    )
    current_minute = _minute(
        lifecycle_data.get("minute")
        or match_data.get("minute")
        or game_flow.get("latest_minute")
    )
    recent_events = []
    if current_minute is not None:
        for event in normalized_events:
            event_minute = _minute(event.get("minute"))
            if event_minute is not None and event_minute >= max(0, current_minute - 15):
                recent_events.append(event)
    recent_ids = [
        f"event:{item['id']}" for item in recent_events if item.get("id")
    ]
    important_types = {
        "goal",
        "penalty_goal",
        "penalty_shootout_goal",
        "own_goal",
        "red_card",
        "yellow_red_card",
        "var",
        "missed_penalty",
        "penalty_shootout_miss",
        "period_start",
        "halftime",
        "extra_time_start",
        "penalty_shootout_start",
        "period_end",
    }
    key_events = [
        event
        for raw, event in zip(timeline_data, normalized_events)
        if bool(raw.get("is_key_event")) or event.get("type") in important_types
    ]
    key_event_ids = [
        f"event:{item['id']}" for item in key_events if item.get("id")
    ]

    direct_risk_types = {
        "red_card": "red_card_observed",
        "yellow_red_card": "dismissal_observed",
        "penalty_goal": "penalty_observed",
        "missed_penalty": "penalty_observed",
        "var": "var_review_observed",
        "penalty_shootout_start": "shootout_observed",
    }
    risk_flags = [
        {
            "kind": direct_risk_types[event["type"]],
            "event_id": event["id"],
            "minute_label": event["minute_label"],
            "team": event["team"],
        }
        for event in normalized_events
        if event.get("type") in direct_risk_types
    ]
    if phase_key == "interrupted":
        risk_flags.append(
            {
                "kind": "match_interrupted",
                "event_id": "",
                "minute_label": "",
                "team": "",
            }
        )

    pressure_value = (
        {
            "label": _text(pressure.get("label"), 160),
            "home_pct": pressure.get("home_pct"),
            "away_pct": pressure.get("away_pct"),
            "kind": "derived_from_provider_statistics",
        }
        if pressure_evidence_id
        else None
    )
    dominant_value = None
    if (
        pressure_evidence_id
        and field_state.get("available")
        and _text(field_state.get("dominant_team"), 120)
    ):
        dominant_value = {
            "team": _text(field_state.get("dominant_team"), 120),
            "side": _text(field_state.get("dominant_side"), 20),
            "headline": _text(field_state.get("headline"), 180),
            "kind": "upstream_evidence_interpretation",
        }
    balance_value = None
    if pressure_evidence_id:
        home_pressure = _number(pressure.get("home_pct"))
        away_pressure = _number(pressure.get("away_pct"))
        if home_pressure is not None and away_pressure is not None:
            balance_value = {
                "provider_label": _text(pressure.get("label"), 160),
                "absolute_gap": abs(home_pressure - away_pressure),
                "kind": "pressure_gap_observation",
            }
    rhythm_value = None
    if game_flow.get("available") and not stale:
        rhythm_value = {
            "event_count": int(
                game_flow.get("event_count") or len(normalized_events)
            ),
            "recent_event_count": int(
                game_flow.get("recent_event_count") or len(recent_events)
            ),
            "window_minutes": 15,
            "kind": "observed_event_activity",
        }
    trend_value = (
        {
            "observations": historical_data,
            "sample_size": len(historical_data),
            "kind": "caller_supplied_historical_observations",
        }
        if historical_data
        else None
    )

    conclusions = {
        "estado_partido": _conclusion(
            "estado_partido",
            state=current_state if status_evidence_id else "INSUFFICIENT_DATA",
            value={
                "key": status_key,
                "label": status_label,
                "minute": lifecycle_data.get("minute") or match_data.get("minute"),
                "score": score_data.get("label") if score_evidence_id else None,
            }
            if status_evidence_id
            else None,
            evidence_ids=(status_evidence_id, score_evidence_id),
            missing=() if status_evidence_id else ("match_status",),
            method="direct_match_state",
        ),
        "ritmo": _conclusion(
            "ritmo",
            state="PARTIALLY_VERIFIED" if rhythm_value else "INSUFFICIENT_DATA",
            value=rhythm_value,
            evidence_ids=event_evidence_ids,
            missing=() if rhythm_value else ("event_activity_window",),
            method="count_confirmed_events_in_fixed_window",
            limitations=(
                "Activity count is not momentum, pressure, dominance, or a prediction.",
            ),
        ),
        "presion": _conclusion(
            "presion",
            state=(
                "PARTIALLY_VERIFIED"
                if pressure_value
                else "STALE"
                if stale and pressure.get("available")
                else "INSUFFICIENT_DATA"
            ),
            value=pressure_value,
            evidence_ids=(pressure_evidence_id, statistics_evidence_id),
            missing=() if pressure_value else ("fresh_provider_statistics",),
            method="reuse_upstream_pressure_from_real_statistics",
            limitations=(
                "No exact ball coordinates are available.",
                "This is not a win probability.",
            ),
        ),
        "dominador": _conclusion(
            "dominador",
            state="PARTIALLY_VERIFIED" if dominant_value else "INSUFFICIENT_DATA",
            value=dominant_value,
            evidence_ids=(pressure_evidence_id, statistics_evidence_id),
            missing=() if dominant_value else ("supported_dominant_team",),
            method="reuse_upstream_field_state",
            limitations=(
                "Dominance is a provider-stat interpretation, not a factual possession claim or prediction.",
            ),
        ),
        "equilibrio": _conclusion(
            "equilibrio",
            state="PARTIALLY_VERIFIED" if balance_value else "INSUFFICIENT_DATA",
            value=balance_value,
            evidence_ids=(pressure_evidence_id,),
            missing=() if balance_value else ("comparable_pressure_values",),
            method="report_pressure_gap_without_new_threshold",
        ),
        "fase": _conclusion(
            "fase",
            state=current_state if phase_value else "INSUFFICIENT_DATA",
            value=phase_value,
            evidence_ids=(status_evidence_id,),
            missing=() if phase_value else ("canonical_match_status",),
            method=phase_method,
        ),
        "riesgo": _conclusion(
            "riesgo",
            state=(
                "VERIFIED"
                if status_evidence_id or event_evidence_ids
                else "INSUFFICIENT_DATA"
            ),
            value={
                "kind": "observed_match_incidents_not_betting_risk",
                "flags": risk_flags,
                "flag_count": len(risk_flags),
            }
            if status_evidence_id or event_evidence_ids
            else None,
            evidence_ids=(
                event_evidence_ids
                + ([status_evidence_id] if phase_key == "interrupted" else [])
            ),
            missing=()
            if status_evidence_id or event_evidence_ids
            else ("match_events",),
            method="direct_incident_flags_only",
            limitations=(
                "No betting, injury, result, or financial risk is inferred.",
            ),
        ),
        "eventos_clave": _conclusion(
            "eventos_clave",
            state="VERIFIED" if timeline_data else "INSUFFICIENT_DATA",
            value={"items": key_events, "count": len(key_events)}
            if timeline_data
            else None,
            evidence_ids=key_event_ids,
            missing=() if timeline_data else ("confirmed_timeline",),
            method="canonical_event_importance_contract",
        ),
        "tendencias": _conclusion(
            "tendencias",
            state="PARTIALLY_VERIFIED" if trend_value else "INSUFFICIENT_DATA",
            value=trend_value,
            evidence_ids=(),
            missing=()
            if trend_value
            else ("comparable_historical_snapshots",),
            method="caller_supplied_history_only",
            limitations=("A single live snapshot never becomes a trend.",),
        ),
        "cambios_recientes": _conclusion(
            "cambios_recientes",
            state=(
                "PARTIALLY_VERIFIED"
                if current_minute is not None and timeline_data
                else "INSUFFICIENT_DATA"
            ),
            value={
                "window_minutes": 15,
                "current_minute": current_minute,
                "count": len(recent_events),
                "items": recent_events,
            }
            if current_minute is not None and timeline_data
            else None,
            evidence_ids=recent_ids,
            missing=()
            if current_minute is not None and timeline_data
            else ("current_minute", "confirmed_timeline"),
            method="fixed_recent_event_window",
            limitations=(
                "Only confirmed events in the supplied timeline are considered.",
            ),
        ),
    }

    missing_information = sorted(
        {
            item
            for conclusion in conclusions.values()
            for item in conclusion.get("missing_information") or []
        }
    )
    related = [
        item
        for item in picks_data
        if _text(item.get("match_id"), 120)
        == _text(match_data.get("id") or match_data.get("match_id"), 120)
    ]
    verified_count = sum(
        conclusion["state"] in {"VERIFIED", "PARTIALLY_VERIFIED"}
        for conclusion in conclusions.values()
    )
    certification_state = (
        "STALE"
        if stale
        else "VERIFIED"
        if verified_count >= 7
        else "PARTIALLY_VERIFIED"
        if verified_count
        else "INSUFFICIENT_DATA"
    )
    limitations = [
        "No external providers are called by this engine.",
        "No missing event, statistic, trend, probability, or sporting consequence is inferred.",
        "Upstream derived pressure remains explicitly marked as partially verified.",
    ]
    entity_context = _entity_context(
        match_data,
        competition_data,
        source,
        certification_state,
    )
    snapshot = {
        "ok": True,
        "contract": MATCH_INTELLIGENCE_CONTRACT,
        "match_id": match_data.get("id") or match_data.get("match_id"),
        "title": " vs ".join(
            item
            for item in (
                _text(match_data.get("home_team"), 120),
                _text(match_data.get("away_team"), 120),
            )
            if item
        )
        or "Partido pendiente",
        "certification_state": certification_state,
        "observed_at_madrid": observed_at or None,
        "freshness": "STALE" if stale else "CURRENT_INPUT",
        "conclusions": conclusions,
        "evidence": evidence,
        "missing_information": missing_information,
        "limitations": limitations,
        "entity_context": entity_context,
        "domain_model": {
            "contract": (canonical_match_data or {}).get("contract"),
            "canonical_match": canonical_match_data,
            "canonical_timeline_count": len(canonical_timeline_data),
            "single_domain_entity_source": bool(canonical_match_data),
        },
        "consumer_contracts": {
            consumer: {
                "contract": MATCH_INTELLIGENCE_CONTRACT,
                "read_only": True,
                "external_action_authorized": False,
            }
            for consumer in MATCH_INTELLIGENCE_CONSUMERS
        },
        "quality": {
            "supported_conclusions": verified_count,
            "total_conclusions": len(conclusions),
            "evidence_items": len(evidence),
            "numeric_confidence_score": None,
            "quality_is_not_sport_probability": True,
        },
        "cache": {
            "policy": "reuse_caller_snapshot",
            "provider_cache_reused": bool(tracker_data),
            "new_cache_write": False,
        },
        "diagnostics": {
            "database_queries": 0,
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "generative_ai_calls": 0,
            "automatic_actions": 0,
        },
        "related_picks": related[:5],
        "no_fake_data": True,
    }
    snapshot["consumer_views"] = {
        consumer: build_match_intelligence_consumer_view(snapshot, consumer)
        for consumer in MATCH_INTELLIGENCE_CONSUMERS
    }
    shark_state = build_shark_match_intelligence_state(snapshot)
    snapshot["shark_context"] = shark_state

    # V745 compatibility is deterministic and is not a second intelligence path.
    snapshot["summary"] = (
        status_label or "Contexto pendiente de datos sincronizados."
    )
    snapshot["signals"] = shark_state.get("signals") or []
    snapshot["risks"] = [
        item["kind"]
        for item in _mapping(conclusions["riesgo"].get("value")).get("flags") or []
    ] or missing_information[:3]
    snapshot["missing_data"] = missing_information
    return snapshot


def match_intelligence_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "MATCH_INTELLIGENCE_ENGINE_READY",
        "contract": MATCH_INTELLIGENCE_CONTRACT,
        "consumers": list(MATCH_INTELLIGENCE_CONSUMERS),
        "output_keys": [
            "estado_partido",
            "ritmo",
            "presion",
            "dominador",
            "equilibrio",
            "fase",
            "riesgo",
            "eventos_clave",
            "tendencias",
            "cambios_recientes",
        ],
        "rules": [
            "Every conclusion carries evidence, missing information, method, and limitations.",
            "A single snapshot never becomes a trend.",
            "No external call, database write, Telegram send, or generative AI call is allowed.",
            "Missing evidence produces INSUFFICIENT_DATA instead of a fabricated conclusion.",
        ],
        "diagnostics": {
            "external_calls": 0,
            "database_writes": 0,
            "generative_ai_calls": 0,
        },
    }
