"""Unified Sports Core domain model for NeMeSiS SHARK PRO.

This module is the canonical, read-only language for sports entities. It does
not query databases, call providers, send Telegram messages, write files, or
invent unavailable facts. Callers pass already available provider/cache rows and
receive normalized entities with provenance, freshness and limitations.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


SPORTS_DOMAIN_MODEL_CONTRACT = "SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1"
TIMELINE_EVENT_CONTRACT = "SPORTS-CORE-TIMELINE-EVENT-V1"
EVIDENCE_CONTRACT = "SPORTS-CORE-EVIDENCE-V1"
FRESHNESS_CONTRACT = "SPORTS-CORE-FRESHNESS-V1"
SPORTS_GRAPH_CONTRACT = "SPORTS-CORE-GRAPH-FOUNDATION-V1"
TELEGRAM_READONLY_CONTRACT = "SPORTS-CORE-TELEGRAM-READONLY-V1"
ENTITY_CENTER_CONTRACT = "SPORTS-ENTITY-CENTER-CONTEXT-V1"

EVIDENCE_STATES = (
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "NOT_CERTIFIED",
    "NOT_CONFIGURED",
    "STALE",
    "BLOCKED_BY_ACCESS",
    "HYPOTHESIS",
    "INSUFFICIENT_DATA",
    "REQUIRES_REVIEW",
)

FRESHNESS_STATES = ("fresh", "aging", "stale", "unknown", "unavailable")

MATCH_PHASES = (
    "scheduled",
    "pre_match",
    "live",
    "halftime",
    "second_half",
    "extra_time",
    "penalties",
    "postponed",
    "suspended",
    "cancelled",
    "finished",
    "unknown",
)

EVENT_TYPE_ALIASES = {
    "goal": "goal",
    "gol": "goal",
    "normal goal": "goal",
    "own goal": "own_goal",
    "autogol": "own_goal",
    "penalty": "penalty_goal",
    "penalty goal": "penalty_goal",
    "missed penalty": "missed_penalty",
    "penalti fallado": "missed_penalty",
    "var": "var",
    "yellow card": "yellow_card",
    "yellow": "yellow_card",
    "tarjeta amarilla": "yellow_card",
    "second yellow": "second_yellow",
    "yellow red": "second_yellow",
    "red card": "red_card",
    "red": "red_card",
    "tarjeta roja": "red_card",
    "substitution": "substitution",
    "subst": "substitution",
    "cambio": "substitution",
    "injury": "injury",
    "period start": "period_start",
    "kickoff": "period_start",
    "period end": "period_end",
    "full time": "period_end",
    "added time": "added_time",
    "score change": "score_change",
    "suspension": "suspension",
    "restart": "restart",
}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _state(value: Any) -> str:
    candidate = _text(value, 40).upper()
    return candidate if candidate in EVIDENCE_STATES else "REQUIRES_REVIEW"


def _provider(value: Any) -> str:
    provider = _text(value, 80).lower().replace("-", "_").replace(" ", "_")
    return provider or "source_not_identified"


def _slug(value: Any, limit: int = 120) -> str:
    text = unicodedata.normalize("NFKD", _text(value, limit))
    ascii_text = text.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:limit] or "unresolved"


def _hash(parts: Iterable[Any], limit: int = 24) -> str:
    raw = "|".join(_text(part, 160).casefold() for part in parts)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:limit]


def _parse_datetime(value: Any) -> datetime | None:
    text = _text(value, 80)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_minutes(source_timestamp: Any, now_value: Any = None) -> int | None:
    source = _parse_datetime(source_timestamp)
    if source is None:
        return None
    now = _parse_datetime(now_value) if now_value else datetime.now(timezone.utc)
    if now is None:
        now = datetime.now(timezone.utc)
    return max(0, int((now - source).total_seconds() // 60))


def _number(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace("%", "").strip()))
    except (TypeError, ValueError):
        return None


def provider_identifier(namespace: Any, entity_type: Any, value: Any) -> str:
    provider = _provider(namespace)
    kind = _slug(entity_type, 40)
    identifier = _text(value, 120)
    if not identifier:
        return ""
    return f"{provider}:{kind}:{identifier}"


def canonical_identifier(
    entity_type: Any,
    *,
    explicit_id: Any = "",
    provider_ids: Mapping[str, Any] | None = None,
    fallback_parts: Iterable[Any] = (),
) -> dict[str, Any]:
    """Resolve a safe canonical id without merging ambiguous entities."""

    kind = _slug(entity_type, 40)
    explicit = _text(explicit_id, 160)
    ids = {
        _provider(source): _text(value, 160)
        for source, value in _mapping(provider_ids).items()
        if _text(value, 160)
    }
    namespaced = {
        source: provider_identifier(source, kind, value)
        for source, value in ids.items()
    }
    limitations: list[str] = []
    if explicit:
        return {
            "canonical_id": explicit,
            "provider_ids": namespaced,
            "identity_state": "VERIFIED",
            "identity_method": "explicit_existing_identifier",
            "collision_risk": "low",
            "limitations": limitations,
        }
    if len(set(namespaced.values())) == 1 and namespaced:
        return {
            "canonical_id": next(iter(namespaced.values())),
            "provider_ids": namespaced,
            "identity_state": "VERIFIED",
            "identity_method": "single_provider_identifier",
            "collision_risk": "low",
            "limitations": limitations,
        }
    if namespaced:
        canonical = f"{kind}:mapped:{_hash(sorted(namespaced.values()))}"
        limitations.append("Multiple provider identifiers require explicit mapping before automatic merge.")
        return {
            "canonical_id": canonical,
            "provider_ids": namespaced,
            "identity_state": "REQUIRES_REVIEW",
            "identity_method": "namespaced_provider_identifiers",
            "collision_risk": "medium",
            "limitations": limitations,
        }
    fallback = [_text(part, 120) for part in fallback_parts if _text(part, 120)]
    if fallback:
        limitations.append("Fallback id is derived from stable visible facts; it is not an official identifier.")
        return {
            "canonical_id": f"{kind}:fallback:{_hash(fallback)}",
            "provider_ids": {},
            "identity_state": "PARTIALLY_VERIFIED",
            "identity_method": "stable_fallback_key",
            "collision_risk": "medium",
            "limitations": limitations,
        }
    return {
        "canonical_id": "",
        "provider_ids": {},
        "identity_state": "INSUFFICIENT_DATA",
        "identity_method": "unresolved",
        "collision_risk": "unknown",
        "limitations": ["No safe identifier is available."],
    }


def normalize_status(raw_status: Any, minute: Any = None) -> dict[str, Any]:
    key = _text(raw_status, 40).upper()
    elapsed = _number(minute)
    phase = "unknown"
    status = "unknown"
    method = "insufficient_status"
    if key in {"NS", "TBD", "SCHEDULED", "PROGRAMADO"}:
        status = "scheduled"
        phase = "pre_match"
        method = "status_taxonomy"
    elif key in {"1H", "FIRST_HALF"}:
        status = "live"
        phase = "live"
        method = "status_taxonomy"
    elif key in {"2H", "SECOND_HALF"}:
        status = "live"
        phase = "second_half"
        method = "status_taxonomy"
    elif key in {"LIVE", "EN DIRECTO"}:
        status = "live"
        if elapsed is None:
            phase = "live"
            method = "generic_live_status"
        elif elapsed <= 45:
            phase = "live"
            method = "confirmed_match_minute"
        elif elapsed <= 90:
            phase = "second_half"
            method = "confirmed_match_minute"
        else:
            phase = "extra_time"
            method = "confirmed_match_minute"
    elif key in {"HT", "HALFTIME", "DESCANSO"}:
        status = "halftime"
        phase = "halftime"
        method = "status_taxonomy"
    elif key in {"ET", "AET", "BT"}:
        status = "live" if key != "AET" else "finished"
        phase = "extra_time"
        method = "status_taxonomy"
    elif key in {"P", "PEN", "PENALTIES"}:
        status = "live" if key == "P" else "finished"
        phase = "penalties"
        method = "status_taxonomy"
    elif key in {"FT", "FINISHED", "FINAL", "FINALIZADO"}:
        status = "finished"
        phase = "finished"
        method = "status_taxonomy"
    elif key in {"POSTP", "POSTPONED", "APL"}:
        status = "postponed"
        phase = "postponed"
        method = "status_taxonomy"
    elif key in {"SUSP", "SUSPENDED", "INT"}:
        status = "suspended"
        phase = "suspended"
        method = "status_taxonomy"
    elif key in {"CANC", "CANCELLED", "CANCELED"}:
        status = "cancelled"
        phase = "cancelled"
        method = "status_taxonomy"
    return {
        "raw": key,
        "status": status if status in MATCH_PHASES else "unknown",
        "phase": phase if phase in MATCH_PHASES else "unknown",
        "minute": elapsed,
        "method": method,
        "evidence_state": "VERIFIED" if method != "insufficient_status" else "INSUFFICIENT_DATA",
        "limitations": [] if method != "generic_live_status" else ["Generic live status lacks a precise provider phase."],
    }


def build_freshness_entity(
    *,
    source_timestamp: Any = "",
    received_at: Any = "",
    now_madrid: Any = "",
    match_status: Any = "",
    data_type: Any = "match",
    fresh_minutes: int | None = None,
    stale_minutes: int | None = None,
) -> dict[str, Any]:
    kind = _slug(data_type, 40)
    status_key = _text(match_status, 40).upper()
    if fresh_minutes is None:
        fresh_minutes = 3 if status_key in {"LIVE", "1H", "2H", "HT", "ET", "P"} else 180
    if stale_minutes is None:
        stale_minutes = 15 if status_key in {"LIVE", "1H", "2H", "HT", "ET", "P"} else 1440
    timestamp = source_timestamp or received_at
    age = _age_minutes(timestamp, now_madrid)
    if not timestamp:
        state = "unknown"
        limitations = ["No source timestamp is available."]
    elif age is None:
        state = "unknown"
        limitations = ["Source timestamp could not be parsed."]
    elif age <= fresh_minutes:
        state = "fresh"
        limitations = []
    elif age <= stale_minutes:
        state = "aging"
        limitations = []
    else:
        state = "stale"
        limitations = ["Data is outside the freshness tolerance for this state and type."]
    return {
        "contract": FRESHNESS_CONTRACT,
        "state": state,
        "data_type": kind,
        "source_timestamp": _text(source_timestamp, 80) or None,
        "received_at": _text(received_at, 80) or None,
        "now_madrid": _text(now_madrid, 80) or None,
        "age_minutes": age,
        "fresh_minutes": fresh_minutes,
        "stale_minutes": stale_minutes,
        "usable_for_live": state in {"fresh", "aging"} and status_key in {"LIVE", "1H", "2H", "HT", "ET", "P"},
        "usable_for_intelligence": state in {"fresh", "aging"},
        "limitations": limitations,
    }


def normalize_team_entity(
    row: Mapping[str, Any] | None,
    *,
    side: str = "",
    provider: Any = "",
) -> dict[str, Any]:
    data = _mapping(row)
    prefix = f"{side}_" if side else ""
    provider_name = _provider(provider or data.get("source") or data.get("provider"))
    official = _text(data.get("official_name") or data.get(f"{prefix}team") or data.get(f"{prefix}team_name") or data.get("name"), 160)
    display = _text(data.get("display_name") or official, 140)
    provider_id = data.get("provider_team_id") or data.get(f"{prefix}team_id") or data.get("team_id") or data.get("id")
    identity = canonical_identifier(
        "team",
        explicit_id=data.get("canonical_team_id"),
        provider_ids={provider_name: provider_id} if provider_id else {},
        fallback_parts=(official, data.get("country"), data.get("competition_id")),
    )
    crest = _text(data.get("crest") or data.get("crest_url") or data.get(f"{prefix}logo") or data.get(f"{prefix}crest"), 400)
    limitations = list(identity["limitations"])
    if not official:
        limitations.append("Team name is not available.")
    if not crest:
        limitations.append("Team crest is not available.")
    return {
        "contract": "SPORTS-CORE-TEAM-ENTITY-V1",
        "canonical_team_id": identity["canonical_id"],
        "provider_team_ids": identity["provider_ids"],
        "official_name": official or None,
        "display_name": display or "Equipo no disponible",
        "short_name": _text(data.get("short_name"), 60) or None,
        "aliases": [item for item in (data.get("aliases") or []) if _text(item, 80)] if isinstance(data.get("aliases"), list) else [],
        "slug": _slug(display or official),
        "country": _text(data.get("country"), 100) or None,
        "city": _text(data.get("city"), 100) or None,
        "competition_ids": [str(data.get("competition_id"))] if data.get("competition_id") else [],
        "crest": crest or None,
        "crest_source": _text(data.get("crest_source") or "provider_url" if crest else "", 80) or None,
        "venue": _text(data.get("venue"), 160) or None,
        "founded": _text(data.get("founded"), 20) or None,
        "gender": _text(data.get("gender"), 40) or None,
        "category": _text(data.get("category"), 60) or None,
        "data_quality": identity["identity_state"] if official else "INSUFFICIENT_DATA",
        "source": provider_name,
        "limitations": limitations,
    }


def normalize_competition_entity(
    row: Mapping[str, Any] | None,
    *,
    provider: Any = "",
) -> dict[str, Any]:
    data = _mapping(row)
    provider_name = _provider(provider or data.get("source") or data.get("provider"))
    official = _text(data.get("official_name") or data.get("competition_name") or data.get("league_name") or data.get("name"), 180)
    display = _text(data.get("display_name") or official, 160)
    provider_id = data.get("provider_competition_id") or data.get("competition_id") or data.get("league_id") or data.get("id")
    identity = canonical_identifier(
        "competition",
        explicit_id=data.get("canonical_competition_id"),
        provider_ids={provider_name: provider_id} if provider_id else {},
        fallback_parts=(official, data.get("country"), data.get("season"), data.get("competition_type")),
    )
    logo = _text(data.get("logo") or data.get("league_logo") or data.get("competition_logo"), 400)
    limitations = list(identity["limitations"])
    if not official:
        limitations.append("Competition name is not available.")
    if not logo:
        limitations.append("Competition logo is not available.")
    return {
        "contract": "SPORTS-CORE-COMPETITION-ENTITY-V1",
        "canonical_competition_id": identity["canonical_id"],
        "provider_competition_ids": identity["provider_ids"],
        "official_name": official or None,
        "display_name": display or "Competicion no disponible",
        "aliases": [item for item in (data.get("aliases") or []) if _text(item, 80)] if isinstance(data.get("aliases"), list) else [],
        "country": _text(data.get("country"), 100) or None,
        "level": _text(data.get("level"), 40) or None,
        "competition_type": _text(data.get("competition_type") or data.get("type"), 80) or None,
        "season": _text(data.get("season"), 40) or None,
        "stage": _text(data.get("stage") or data.get("round"), 120) or None,
        "logo": logo or None,
        "logo_source": _text(data.get("logo_source") or "provider_url" if logo else "", 80) or None,
        "standings_available": bool(data.get("standings_available")),
        "fixtures_available": bool(data.get("fixtures_available")),
        "data_quality": identity["identity_state"] if official else "INSUFFICIENT_DATA",
        "source": provider_name,
        "limitations": limitations,
    }


def normalize_player_entity(
    row: Mapping[str, Any] | None,
    *,
    provider: Any = "",
) -> dict[str, Any]:
    data = _mapping(row)
    provider_name = _provider(provider or data.get("source") or data.get("provider"))
    official = _text(data.get("official_name") or data.get("player_name") or data.get("name") or data.get("player"), 160)
    provider_id = data.get("provider_player_id") or data.get("player_id") or data.get("id")
    identity = canonical_identifier(
        "player",
        explicit_id=data.get("canonical_player_id"),
        provider_ids={provider_name: provider_id} if provider_id else {},
        fallback_parts=(official, data.get("team_id"), data.get("birth_date")),
    )
    photo = _text(data.get("photo") or data.get("photo_url"), 400)
    limitations = list(identity["limitations"])
    if not official:
        limitations.append("Player name is not available.")
    if not photo:
        limitations.append("Player photo is not available.")
    return {
        "contract": "SPORTS-CORE-PLAYER-ENTITY-V1",
        "canonical_player_id": identity["canonical_id"],
        "provider_player_ids": identity["provider_ids"],
        "official_name": official or None,
        "display_name": _text(data.get("display_name") or official, 140) or "Jugador no disponible",
        "aliases": [item for item in (data.get("aliases") or []) if _text(item, 80)] if isinstance(data.get("aliases"), list) else [],
        "team_id": _text(data.get("team_id"), 120) or None,
        "position": _text(data.get("position"), 40) or None,
        "shirt_number": _text(data.get("shirt_number") or data.get("number"), 20) or None,
        "nationality": _text(data.get("nationality"), 80) or None,
        "birth_date": _text(data.get("birth_date"), 40) or None,
        "status": _text(data.get("status"), 60) or None,
        "injury_status": _text(data.get("injury_status"), 120) or None,
        "photo": photo or None,
        "photo_source": _text(data.get("photo_source") or "provider_url" if photo else "", 80) or None,
        "data_quality": identity["identity_state"] if official else "INSUFFICIENT_DATA",
        "source": provider_name,
        "limitations": limitations,
    }


def normalize_score(row: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(row)
    home = data.get("home_score")
    away = data.get("away_score")
    confirmed = home not in (None, "") and away not in (None, "")
    return {
        "home": home if confirmed else None,
        "away": away if confirmed else None,
        "label": f"{home}-{away}" if confirmed else _text(data.get("score"), 40) or None,
        "confirmed": confirmed,
    }


def normalize_timeline_event_entity(
    raw: Mapping[str, Any] | None,
    *,
    match_id: Any = "",
    home_team: Any = "",
    away_team: Any = "",
    provider: Any = "",
) -> dict[str, Any] | None:
    data = _mapping(raw)
    provider_name = _provider(provider or data.get("source") or data.get("provider"))
    provider_event_id = _text(data.get("provider_event_id") or data.get("event_id") or data.get("id") or data.get("external_id"), 140)
    raw_type = _text(data.get("event_type") or data.get("type") or data.get("kind"), 80)
    subtype = _text(data.get("subtype") or data.get("detail") or data.get("description"), 120)
    normalized_raw = raw_type.lower().replace("_", " ").replace("-", " ")
    normalized_subtype = subtype.lower().replace("_", " ").replace("-", " ")
    combined = f"{normalized_raw} {normalized_subtype}".strip()
    if normalized_raw in {"card", "tarjeta"}:
        if "second yellow" in normalized_subtype or "yellow red" in normalized_subtype:
            event_type = "second_yellow"
        elif "red" in normalized_subtype or "roja" in normalized_subtype:
            event_type = "red_card"
        elif "yellow" in normalized_subtype or "amarilla" in normalized_subtype:
            event_type = "yellow_card"
        else:
            event_type = "unknown"
    else:
        event_type = EVENT_TYPE_ALIASES.get(combined) or EVENT_TYPE_ALIASES.get(normalized_raw, "unknown")
    minute = _number(data.get("minute") or data.get("elapsed") or data.get("time"))
    added = _number(data.get("added_time") or data.get("extra")) or 0
    team_name = _text(data.get("team") or data.get("team_name"), 140)
    team_side = "home" if team_name and team_name == _text(home_team, 140) else "away" if team_name and team_name == _text(away_team, 140) else ""
    event_key = provider_event_id or _hash((match_id, event_type, minute, added, team_name, data.get("player_id"), data.get("player") or data.get("player_name"), subtype), 20)
    if not match_id or not event_key:
        return None
    canonical_event_id = provider_identifier(provider_name, "event", event_key)
    limitations = []
    if not provider_event_id:
        limitations.append("Provider event id missing; stable event key derived from event facts.")
    if minute is None:
        limitations.append("Event minute is not available.")
    if event_type == "unknown":
        limitations.append("Event type is unknown.")
    player = normalize_player_entity(
        {
            "player_id": data.get("player_id"),
            "player_name": data.get("player") or data.get("player_name"),
            "team_id": data.get("team_id"),
        },
        provider=provider_name,
    )
    related_player = normalize_player_entity(
        {
            "player_id": data.get("related_player_id") or data.get("assist_id"),
            "player_name": data.get("related_player") or data.get("assist") or data.get("assist_name"),
            "team_id": data.get("team_id"),
        },
        provider=provider_name,
    )
    return {
        "contract": TIMELINE_EVENT_CONTRACT,
        "canonical_event_id": canonical_event_id,
        "provider_event_id": provider_event_id or None,
        "match_id": _text(match_id, 160),
        "event_type": event_type,
        "subtype": subtype or None,
        "period": _text(data.get("period"), 40) or None,
        "minute": minute,
        "added_time": added,
        "timestamp": _text(data.get("timestamp") or data.get("captured_at"), 80) or None,
        "team_id": _text(data.get("team_id"), 120) or None,
        "team_name": team_name or None,
        "team_side": team_side or None,
        "player_id": player["canonical_player_id"] or None,
        "player_name": player["display_name"] if player["data_quality"] != "INSUFFICIENT_DATA" else None,
        "related_player_id": related_player["canonical_player_id"] or None,
        "related_player_name": related_player["display_name"] if related_player["data_quality"] != "INSUFFICIENT_DATA" else None,
        "score_after": data.get("score_after"),
        "description": _text(data.get("description") or data.get("detail") or data.get("comments"), 220) or None,
        "source": provider_name,
        "source_timestamp": _text(data.get("source_timestamp") or data.get("captured_at"), 80) or None,
        "confidence": None,
        "data_quality": "VERIFIED" if provider_event_id else "PARTIALLY_VERIFIED",
        "limitations": limitations,
    }


def normalize_timeline_events(
    events: Iterable[Mapping[str, Any]] | None,
    *,
    match_id: Any = "",
    home_team: Any = "",
    away_team: Any = "",
    provider: Any = "",
) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    seen_facts: set[tuple[Any, ...]] = set()
    normalized: list[dict[str, Any]] = []
    for raw in events or []:
        event = normalize_timeline_event_entity(
            raw,
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            provider=provider,
        )
        if not event:
            continue
        fact_key = (
            event["event_type"],
            event["minute"],
            event["added_time"],
            event.get("team_name") or "",
            event.get("player_name") or "",
            event.get("related_player_name") or "",
            event.get("description") or "",
        )
        if event["canonical_event_id"] in seen_ids or fact_key in seen_facts:
            continue
        seen_ids.add(event["canonical_event_id"])
        seen_facts.add(fact_key)
        normalized.append(event)
    return sorted(normalized, key=lambda item: ((item.get("minute") or 99999), item.get("added_time") or 0, item["canonical_event_id"]))


def normalize_evidence_entity(
    *,
    evidence_id: Any = "",
    match_id: Any = "",
    category: Any,
    claim: Any,
    raw_value: Any = None,
    normalized_value: Any = None,
    source: Any = "",
    method: Any = "",
    observed_at: Any = "",
    freshness: Mapping[str, Any] | None = None,
    confidence: Any = None,
    limitations: Iterable[Any] = (),
    missing_information: Iterable[Any] = (),
) -> dict[str, Any]:
    fresh = _mapping(freshness)
    stale = fresh.get("state") == "stale"
    usable = bool(fresh.get("usable_for_intelligence", True)) and not stale
    return {
        "contract": EVIDENCE_CONTRACT,
        "evidence_id": _text(evidence_id, 160) or f"evidence:{_hash((match_id, category, claim, source), 20)}",
        "match_id": _text(match_id, 160) or None,
        "category": _text(category, 80),
        "claim": _text(claim, 240),
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "source": _provider(source),
        "method": _text(method, 160) or "direct_provider_fact",
        "observed_at": _text(observed_at, 80) or None,
        "freshness": fresh,
        "confidence": confidence,
        "limitations": [_text(item, 180) for item in limitations if _text(item, 180)],
        "missing_information": [_text(item, 120) for item in missing_information if _text(item, 120)],
        "stale": stale,
        "usable_for_intelligence": usable,
    }


def normalize_match_entity(
    row: Mapping[str, Any] | None,
    *,
    live_context: Mapping[str, Any] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    provider: Any = "",
    now_madrid: Any = "",
) -> dict[str, Any]:
    data = _mapping(row)
    live = _mapping(live_context)
    provider_name = _provider(provider or live.get("provider") or data.get("source") or data.get("provider"))
    provider_id = data.get("external_id") or data.get("fixture_id") or data.get("id")
    match_id = data.get("id") or data.get("match_id")
    home = normalize_team_entity(data, side="home", provider=provider_name)
    away = normalize_team_entity(data, side="away", provider=provider_name)
    competition = normalize_competition_entity(data, provider=provider_name)
    kickoff = data.get("kickoff_at") or data.get("kickoff_iso") or data.get("commence_time") or data.get("match_date")
    status = normalize_status(data.get("status") or live.get("status"), data.get("minute") or live.get("minute"))
    freshness = build_freshness_entity(
        source_timestamp=live.get("updated_at") or data.get("updated_at") or data.get("source_timestamp"),
        received_at=data.get("updated_at"),
        now_madrid=now_madrid,
        match_status=status.get("raw"),
        data_type="match",
    )
    identity = canonical_identifier(
        "match",
        explicit_id=match_id if str(match_id or "").startswith("match:") else "",
        provider_ids={provider_name: provider_id} if provider_id else {},
        fallback_parts=(
            competition.get("canonical_competition_id"),
            kickoff,
            home.get("canonical_team_id"),
            away.get("canonical_team_id"),
        ),
    )
    events = normalize_timeline_events(
        timeline_events if timeline_events is not None else live.get("events"),
        match_id=identity["canonical_id"],
        home_team=home.get("display_name"),
        away_team=away.get("display_name"),
        provider=provider_name,
    )
    score = normalize_score(data)
    limitations = list(identity["limitations"])
    for key, entity in (("home_team", home), ("away_team", away), ("competition", competition)):
        if entity.get("data_quality") == "INSUFFICIENT_DATA":
            limitations.append(f"{key} is incomplete.")
    if freshness.get("state") in {"stale", "unknown"}:
        limitations.extend(freshness.get("limitations") or [])
    return {
        "contract": "SPORTS-CORE-MATCH-ENTITY-V1",
        "canonical_match_id": identity["canonical_id"],
        "provider_match_ids": identity["provider_ids"],
        "sport": _text(data.get("sport") or data.get("sport_key") or "soccer", 40),
        "competition": competition,
        "season": _text(data.get("season"), 40) or competition.get("season"),
        "round": _text(data.get("round") or data.get("round_name"), 120) or None,
        "stage": _text(data.get("stage"), 120) or competition.get("stage"),
        "home_team": home,
        "away_team": away,
        "kickoff_at": _text(kickoff, 80) or None,
        "timezone": _text(data.get("timezone") or "Europe/Madrid", 80),
        "status": status["status"],
        "phase": status["phase"],
        "minute": status["minute"],
        "added_time": _number(data.get("added_time") or data.get("extra")),
        "score": score,
        "period_scores": data.get("period_scores") if isinstance(data.get("period_scores"), Mapping) else {},
        "venue": _text(data.get("venue"), 160) or None,
        "officials": [_text(data.get("referee"), 120)] if data.get("referee") else [],
        "events": events,
        "freshness": freshness,
        "source": provider_name,
        "source_timestamp": freshness.get("source_timestamp"),
        "data_quality": "STALE" if freshness.get("state") == "stale" else identity["identity_state"],
        "limitations": sorted(set(item for item in limitations if item)),
    }


def legacy_match_from_entity(match_entity: Mapping[str, Any] | None) -> dict[str, Any]:
    entity = _mapping(match_entity)
    home = _mapping(entity.get("home_team"))
    away = _mapping(entity.get("away_team"))
    competition = _mapping(entity.get("competition"))
    score = _mapping(entity.get("score"))
    provider_ids = _mapping(entity.get("provider_match_ids"))
    external = next(iter(provider_ids.values()), "") if provider_ids else ""
    return {
        "id": entity.get("canonical_match_id"),
        "match_id": entity.get("canonical_match_id"),
        "external_id": external,
        "sport_key": entity.get("sport"),
        "competition_id": competition.get("canonical_competition_id"),
        "competition_name": competition.get("display_name"),
        "league_name": competition.get("display_name"),
        "country": competition.get("country"),
        "season": entity.get("season"),
        "round": entity.get("round"),
        "home_team": home.get("display_name"),
        "away_team": away.get("display_name"),
        "home_team_id": home.get("canonical_team_id"),
        "away_team_id": away.get("canonical_team_id"),
        "home_logo": home.get("crest"),
        "away_logo": away.get("crest"),
        "kickoff_iso": entity.get("kickoff_at"),
        "status": entity.get("status"),
        "minute": entity.get("minute"),
        "score": score.get("label"),
        "home_score": score.get("home"),
        "away_score": score.get("away"),
        "venue": entity.get("venue"),
        "source": entity.get("source"),
        "updated_at": entity.get("source_timestamp"),
        "canonical": entity,
    }


def legacy_event_from_entity(event: Mapping[str, Any] | None) -> dict[str, Any]:
    item = _mapping(event)
    minute = item.get("minute")
    added = item.get("added_time") or 0
    minute_label = "Minuto no disponible" if minute is None else f"{minute}+{added}'" if added else f"{minute}'"
    return {
        "id": item.get("canonical_event_id"),
        "type": item.get("event_type"),
        "event_type": item.get("event_type"),
        "label": item.get("event_type", "unknown").replace("_", " ").title(),
        "headline": item.get("description") or item.get("event_type", "Evento confirmado").replace("_", " ").title(),
        "minute": minute,
        "added_time": added,
        "minute_label": minute_label,
        "team": item.get("team_name") or "",
        "side": item.get("team_side") or "",
        "player_id": item.get("player_id") or "",
        "player": item.get("player_name") or "",
        "related_player_id": item.get("related_player_id") or "",
        "related_player": item.get("related_player_name") or "",
        "detail": item.get("description") or "",
        "source": item.get("source") or "",
        "canonical_event": item,
    }


def build_sports_graph_foundation(
    match_entity: Mapping[str, Any] | None,
    *,
    picks: Iterable[Mapping[str, Any]] | None = None,
    odds: Iterable[Mapping[str, Any]] | None = None,
    telegram: Iterable[Mapping[str, Any]] | None = None,
    shark: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    match = _mapping(match_entity)
    match_id = _text(match.get("canonical_match_id"), 160)
    home = _mapping(match.get("home_team"))
    away = _mapping(match.get("away_team"))
    competition = _mapping(match.get("competition"))
    edges: list[dict[str, Any]] = []

    def add(source_id: Any, relationship: str, target_id: Any, evidence: str) -> None:
        if not _text(source_id, 160) or not _text(target_id, 160):
            return
        edges.append({
            "source_id": _text(source_id, 160),
            "relationship": relationship,
            "target_id": _text(target_id, 160),
            "evidence": evidence,
            "persistence_authorized": False,
        })

    add(match_id, "has_home_team", home.get("canonical_team_id"), "match_entity")
    add(match_id, "has_away_team", away.get("canonical_team_id"), "match_entity")
    add(match_id, "belongs_to_competition", competition.get("canonical_competition_id"), "match_entity")
    for event in _items(match.get("events")):
        add(match_id, "has_timeline_event", event.get("canonical_event_id"), "timeline_event_entity")
        add(event.get("canonical_event_id"), "belongs_to_match", match_id, "timeline_event_entity")
        add(event.get("player_id"), "appears_in_event", event.get("canonical_event_id"), "timeline_event_entity")
    for pick in picks or []:
        pick_id = _text(pick.get("id") or pick.get("pick_id"), 120)
        add(pick_id, "references_match", match_id, "pick_contract")
    for market in odds or []:
        market_id = _text(market.get("id") or market.get("market_id"), 120)
        add(market_id, "prices_match", match_id, "odds_contract")
    for delivery in telegram or []:
        delivery_id = _text(delivery.get("id") or delivery.get("dedupe_key"), 120)
        add(delivery_id, "mentions_match", match_id, "telegram_contract")
    shark_data = _mapping(shark)
    if shark_data:
        add(_text(shark_data.get("id") or "shark-analysis", 120), "uses_match_evidence", match_id, "shark_contract")
    return {
        "contract": SPORTS_GRAPH_CONTRACT,
        "entities": {
            "match": match,
            "home_team": home,
            "away_team": away,
            "competition": competition,
            "events": _items(match.get("events")),
        },
        "edges": edges,
        "edge_count": len(edges),
        "database_written": False,
        "external_calls": 0,
        "persistence_authorized": False,
    }


def build_telegram_readonly_contract(
    *,
    match_entity: Mapping[str, Any] | None = None,
    match_intelligence: Mapping[str, Any] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    evidence: Iterable[Mapping[str, Any]] | None = None,
    freshness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    match = _mapping(match_entity)
    events = _items(timeline_events if timeline_events is not None else match.get("events"))
    return {
        "contract": TELEGRAM_READONLY_CONTRACT,
        "match": match,
        "match_intelligence_contract": _mapping(match_intelligence).get("contract"),
        "timeline_events": events,
        "evidence": _items(evidence),
        "freshness": _mapping(freshness or match.get("freshness")),
        "send_executed": False,
        "telegram_api_called": False,
        "database_written": False,
        "external_action_authorized": False,
        "limitations": ["Contrato preparado para lectura; no autoriza nuevos mensajes ni cambios de dedupe."],
    }


def build_entity_center_contract(
    entity_type: Any,
    entity: Mapping[str, Any] | None = None,
    *,
    provider_configured: bool | None = None,
) -> dict[str, Any]:
    kind = _slug(entity_type, 40)
    data = _mapping(entity)
    state = "entity_available" if data else "entity_not_resolved"
    if provider_configured is False:
        state = "provider_not_configured"
    elif data and data.get("data_quality") == "STALE":
        state = "data_stale"
    elif data and data.get("data_quality") in {"PARTIALLY_VERIFIED", "REQUIRES_REVIEW"}:
        state = "entity_partial"
    return {
        "contract": ENTITY_CENTER_CONTRACT,
        "entity_type": kind,
        "state": state,
        "entity": data,
        "data_available": bool(data),
        "safe_message": {
            "entity_available": "Entidad disponible con datos confirmados.",
            "entity_partial": "Entidad parcial: se muestran solo datos confirmados.",
            "entity_not_resolved": "Entidad no resuelta con seguridad.",
            "provider_not_configured": "Proveedor no configurado para esta entidad.",
            "data_stale": "Datos desactualizados; no se presentan como actuales.",
        }.get(state, "Estado seguro."),
        "database_written": False,
        "external_calls": 0,
    }


def build_unified_domain_snapshot(
    match: Mapping[str, Any] | None = None,
    *,
    live_context: Mapping[str, Any] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    picks: Iterable[Mapping[str, Any]] | None = None,
    odds: Iterable[Mapping[str, Any]] | None = None,
    telegram: Iterable[Mapping[str, Any]] | None = None,
    shark: Mapping[str, Any] | None = None,
    now_madrid: Any = "",
) -> dict[str, Any]:
    match_entity = normalize_match_entity(
        match,
        live_context=live_context,
        timeline_events=timeline_events,
        now_madrid=now_madrid,
    )
    graph = build_sports_graph_foundation(
        match_entity,
        picks=picks,
        odds=odds,
        telegram=telegram,
        shark=shark,
    )
    return {
        "contract": SPORTS_DOMAIN_MODEL_CONTRACT,
        "match": match_entity,
        "teams": [match_entity["home_team"], match_entity["away_team"]],
        "competition": match_entity["competition"],
        "players": [
            player
            for event in match_entity.get("events") or []
            for player in (
                {
                    "canonical_player_id": event.get("player_id"),
                    "display_name": event.get("player_name"),
                },
                {
                    "canonical_player_id": event.get("related_player_id"),
                    "display_name": event.get("related_player_name"),
                },
            )
            if player.get("canonical_player_id")
        ],
        "timeline_events": match_entity.get("events") or [],
        "freshness": match_entity.get("freshness"),
        "sports_graph": graph,
        "diagnostics": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "generative_ai_calls": 0,
            "fake_data_created": 0,
        },
    }


def sports_domain_model_snapshot() -> dict[str, Any]:
    return {
        "ok": True,
        "contract": SPORTS_DOMAIN_MODEL_CONTRACT,
        "entities": [
            "match",
            "team",
            "competition",
            "player",
            "timeline_event",
            "evidence",
            "freshness",
        ],
        "relationships": [
            "Match -> Home Team",
            "Match -> Away Team",
            "Match -> Competition",
            "Match -> Timeline Events",
            "Match -> Evidence",
            "Pick -> Match",
            "Odds Market -> Match",
            "Telegram Delivery -> Match or Pick",
            "SHARK Analysis -> Match + Evidence",
        ],
        "future_centers": ["Team Center", "Competition Center", "Player Center"],
        "guardrails": {
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "automatic_merges": False,
        },
        "states": {
            "evidence": list(EVIDENCE_STATES),
            "freshness": list(FRESHNESS_STATES),
            "match_phases": list(MATCH_PHASES),
        },
    }

