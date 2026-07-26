"""Build an honest Match Center story from provider-confirmed events only.

The engine is independent from Flask and the database. Callers pass a
normalized match plus provider/cache events and receive a deterministic story.
No event, score, momentum, probability, or sporting consequence is invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


_EVENT_TYPES = {
    "goal": ("Gol", 100),
    "penalty_goal": ("Gol de penalti", 100),
    "own_goal": ("Gol en propia puerta", 100),
    "red_card": ("Tarjeta roja", 90),
    "var": ("Revisión VAR", 85),
    "missed_penalty": ("Penalti fallado", 85),
    "yellow_red_card": ("Segunda amarilla", 80),
    "period_start": ("Comienza el periodo", 75),
    "period_end": ("Final del periodo", 75),
    "substitution": ("Cambio", 45),
    "yellow_card": ("Tarjeta amarilla", 40),
    "unknown": ("Evento confirmado", 20),
}

_TYPE_ALIASES = {
    "gol": "goal",
    "goal": "goal",
    "penalty goal": "penalty_goal",
    "gol de penalti": "penalty_goal",
    "own goal": "own_goal",
    "autogol": "own_goal",
    "red": "red_card",
    "red card": "red_card",
    "tarjeta roja": "red_card",
    "var": "var",
    "missed penalty": "missed_penalty",
    "penalti fallado": "missed_penalty",
    "yellow red": "yellow_red_card",
    "second yellow": "yellow_red_card",
    "segunda amarilla": "yellow_red_card",
    "substitution": "substitution",
    "cambio": "substitution",
    "yellow": "yellow_card",
    "yellow card": "yellow_card",
    "tarjeta amarilla": "yellow_card",
    "kickoff": "period_start",
    "period start": "period_start",
    "half start": "period_start",
    "period end": "period_end",
    "half time": "period_end",
    "full time": "period_end",
}


@dataclass(frozen=True)
class EventMinute:
    base: int | None
    added: int
    label: str
    sort_value: int


def _text(value: Any, limit: int = 180) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _event_minute(value: Any) -> EventMinute:
    raw = _text(value, 20).replace("’", "").replace("'", "")
    if not raw:
        return EventMinute(None, 0, "Minuto no disponible", 99_999)
    try:
        if "+" in raw:
            base_raw, added_raw = raw.split("+", 1)
            base = int(base_raw)
            added = max(0, int(added_raw))
        else:
            base = int(raw)
            added = 0
    except (TypeError, ValueError):
        return EventMinute(None, 0, "Minuto no disponible", 99_999)
    if base < 0 or base > 130 or added > 30:
        return EventMinute(None, 0, "Minuto no disponible", 99_999)
    label = f"{base}+{added}'" if added else f"{base}'"
    return EventMinute(base, added, label, base * 100 + added)


def _canonical_type(value: Any) -> str:
    raw = _text(value, 80).lower().replace("_", "-").replace("-", " ")
    candidate = raw.replace(" ", "_")
    return _TYPE_ALIASES.get(
        raw,
        candidate if candidate in _EVENT_TYPES else "unknown",
    )


def _safe_team(value: Any, match: dict[str, Any]) -> str:
    team = _text(value, 120)
    if not team:
        return ""
    known = {_text(match.get("home_team"), 120), _text(match.get("away_team"), 120)}
    return team if team in known else ""


def normalize_story_event(
    raw: dict[str, Any],
    match: dict[str, Any],
) -> dict[str, Any] | None:
    """Normalize one event without manufacturing its identity or source."""

    if not isinstance(raw, dict):
        return None
    event_type = _canonical_type(
        raw.get("type") or raw.get("event_type") or raw.get("kind")
    )
    minute = _event_minute(
        raw.get("minute") or raw.get("elapsed") or raw.get("time")
    )
    event_id = _text(
        raw.get("id") or raw.get("event_id") or raw.get("external_id"),
        100,
    )
    provider = _text(raw.get("source") or raw.get("provider"), 80)
    if not event_id or not provider:
        return None

    label, importance = _EVENT_TYPES[event_type]
    team = _safe_team(raw.get("team") or raw.get("team_name"), match)
    player = _text(raw.get("player") or raw.get("player_name"), 120)
    related_player = _text(
        raw.get("related_player") or raw.get("assist") or raw.get("player_out"),
        120,
    )
    detail = _text(
        raw.get("detail") or raw.get("description") or raw.get("reason"),
        220,
    )
    headline_parts = [label]
    if player:
        headline_parts.append(player)
    if team:
        headline_parts.append(team)

    return {
        "id": event_id,
        "type": event_type,
        "label": label,
        "headline": " · ".join(headline_parts),
        "minute": minute.base,
        "added_time": minute.added,
        "minute_label": minute.label,
        "sort_value": minute.sort_value,
        "team": team,
        "player": player,
        "related_player": related_player,
        "detail": detail,
        "importance": importance,
        "is_key_event": importance >= 80,
        "source": provider,
    }


def normalize_story_events(
    events: Iterable[dict[str, Any]] | None,
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return unique, provider-confirmed events in chronological order."""

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in events or []:
        event = normalize_story_event(raw, match)
        if event and event["id"] not in seen:
            seen.add(event["id"])
            normalized.append(event)
    return sorted(
        normalized,
        key=lambda item: (item["sort_value"], item["id"]),
    )


def _phase_for_minute(minute: int | None, match_status: Any) -> str:
    status = _text(match_status, 40).lower()
    if status in {"finished", "finalizado", "ft", "aet", "pen"}:
        return "finished"
    if status in {"halftime", "descanso", "ht"}:
        return "halftime"
    if minute is None:
        return "unknown"
    if minute <= 45:
        return "first_half"
    if minute <= 90:
        return "second_half"
    return "extra_time"


def _build_cycles(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cycles: list[list[dict[str, Any]]] = []
    for event in events:
        if not cycles:
            cycles.append([event])
            continue
        previous = cycles[-1][-1]
        same_known_window = (
            event["minute"] is not None
            and previous["minute"] is not None
            and event["minute"] - previous["minute"] <= 4
        )
        if same_known_window:
            cycles[-1].append(event)
        else:
            cycles.append([event])

    payload: list[dict[str, Any]] = []
    for index, items in enumerate(cycles, start=1):
        key_event = max(
            items,
            key=lambda item: (item["importance"], -item["sort_value"]),
        )
        minute_label = items[0]["minute_label"]
        if len(items) > 1:
            minute_label = f"{items[0]['minute_label']}–{items[-1]['minute_label']}"
        payload.append(
            {
                "id": f"cycle-{index}",
                "start_minute": items[0]["minute"],
                "end_minute": items[-1]["minute"],
                "minute_label": minute_label,
                "headline": key_event["headline"],
                "importance": key_event["importance"],
                "event_count": len(items),
                "events": items,
            }
        )
    return payload


def build_match_live_story(
    match: dict[str, Any],
    events: Iterable[dict[str, Any]] | None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a complete safe story payload for one Match Center."""

    match = match if isinstance(match, dict) else {}
    match_id = _text(match.get("id") or match.get("match_id"), 100)
    home = _text(match.get("home_team"), 120)
    away = _text(match.get("away_team"), 120)
    normalized = normalize_story_events(events, match)
    cycles = _build_cycles(normalized)
    latest = normalized[-1] if normalized else None
    key_events = [item for item in normalized if item["is_key_event"]]
    minute = match.get("minute") or (latest or {}).get("minute")
    phase = _phase_for_minute(minute, match.get("status"))

    valid_match = bool(match_id and home and away)
    if not valid_match:
        state = "invalid_match_context"
        message = "No hay contexto de partido suficiente para construir la historia."
    elif not normalized:
        state = "waiting_for_confirmed_events"
        message = "Aún no hay eventos confirmados para construir la historia del partido."
    else:
        state = "story_available"
        message = f"Historia construida con {len(normalized)} evento(s) confirmado(s)."

    return {
        "contract": "MATCH-CENTER-LIFECYCLE-STORY-V1",
        "match_id": match_id,
        "match_label": f"{home} vs {away}" if home and away else "Partido pendiente",
        "state": state,
        "safe_message": message,
        "phase": phase,
        "latest_event": latest,
        "timeline": normalized,
        "cycles": cycles,
        "key_events": key_events,
        "counts": {
            "events": len(normalized),
            "cycles": len(cycles),
            "key_events": len(key_events),
        },
        "generated_at": (
            generated_at.isoformat(timespec="seconds") if generated_at else ""
        ),
        "no_external_calls": True,
        "no_database_writes": True,
        "no_fake_data": True,
        "momentum_available": False,
        "sporting_consequences_available": False,
    }
