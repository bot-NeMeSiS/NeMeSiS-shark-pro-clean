"""Canonical read-only lifecycle and data-trust rules for V935.

The module never opens a database, calls a provider, or mutates input records.
It is deliberately pure so page rendering, workers, and checks share one policy.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")

MATCH_LIFECYCLES = (
    "UPCOMING", "LIVE", "HALFTIME", "FINISHED", "RESULT_PENDING",
    "POSTPONED", "CANCELLED", "ABANDONED", "STALE", "INCOMPLETE", "ARCHIVED",
)
PICK_LIFECYCLES = (
    "DRAFT", "INCOMPLETE", "REVIEW", "APPROVED", "PUBLISHED", "LIVE",
    "WON", "LOST", "VOID", "CANCELLED", "EXPIRED", "ARCHIVED",
)
ODDS_STATES = ("FRESH", "RECORDED", "STALE", "EXPIRED", "INVALID")

_PLACEHOLDERS = {
    "", "none", "null", "undefined", "pending", "pendiente", "por confirmar",
    "sin dato", "sin datos", "unknown", "n/a", "na", "tbd", "placeholder",
    "esperar cuota disponible", "cuota pendiente", "mercado pendiente",
    "seleccion pendiente", "selección pendiente", "competicion pendiente",
    "competición pendiente", "hora pendiente",
}


def madrid_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(MADRID_TZ)
    if value.tzinfo is None:
        value = value.replace(tzinfo=MADRID_TZ)
    return value.astimezone(MADRID_TZ)


def _text(value: Any, limit: int = 180) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _key(value: Any) -> str:
    return _text(value).casefold()


def _present(value: Any) -> bool:
    return _key(value) not in _PLACEHOLDERS


def _float(value: Any) -> float | None:
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number


def _parse_iso(value: Any) -> datetime | None:
    text = _text(value, 100)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=MADRID_TZ)
    return parsed.astimezone(MADRID_TZ)


def match_kickoff_madrid(item: dict[str, Any]) -> datetime | None:
    for key in ("kickoff_iso", "commence_time", "start_time", "datetime", "date_time"):
        parsed = _parse_iso(item.get(key))
        if parsed:
            return parsed
    date_text = _text(item.get("match_date") or item.get("date"), 10)
    time_text = _text(
        item.get("kickoff_time") or item.get("match_time")
        or item.get("calendar_time") or item.get("client_time_label"),
        16,
    )
    if not date_text or not time_text:
        return None
    time_text = time_text[:5]
    try:
        return datetime.fromisoformat(f"{date_text}T{time_text}:00").replace(tzinfo=MADRID_TZ)
    except ValueError:
        return None


def get_match_source(item: dict[str, Any]) -> str:
    source = _text(
        item.get("source") or item.get("provider") or item.get("data_source")
        or item.get("source_name"),
        80,
    )
    if not _present(source) or any(token in _key(source) for token in ("fake", "demo", "fixture_test", "placeholder")):
        return ""
    return source


def _match_identity(item: dict[str, Any]) -> tuple[str, str, str, str]:
    match_id = _text(item.get("id") or item.get("match_id") or item.get("external_id"), 90)
    home = _text(item.get("home_team") or item.get("client_home") or item.get("home_name"), 120)
    away = _text(item.get("away_team") or item.get("client_away") or item.get("away_name"), 120)
    competition = _text(
        item.get("competition_name") or item.get("league_name") or item.get("client_competition")
        or item.get("calendar_competition") or item.get("competition") or item.get("league"),
        140,
    )
    return match_id, home, away, competition


def is_match_complete(item: dict[str, Any]) -> bool:
    if not isinstance(item, dict):
        return False
    match_id, home, away, competition = _match_identity(item)
    return bool(
        _present(match_id) and _present(home) and _present(away)
        and home.casefold() != away.casefold() and _present(competition)
        and match_kickoff_madrid(item) is not None and get_match_source(item)
    )


def _score_confirmed(item: dict[str, Any]) -> bool:
    home = _float(item.get("home_score"))
    away = _float(item.get("away_score"))
    if home is not None and away is not None and home >= 0 and away >= 0:
        return True
    score = _text(item.get("score") or item.get("result"), 40)
    if not score:
        return False
    for separator in ("-", ":", "â€“"):
        if separator in score:
            left, right = score.split(separator, 1)
            return _float(left) is not None and _float(right) is not None
    return False


_FINISHED_STATUS_KEYS = {
    "ft", "final", "finalizado", "finished", "match finished", "full time",
    "aet", "pen", "after penalties", "terminado",
}
_POSTPONED_STATUS_KEYS = {
    "postponed", "post", "pst", "ppd", "aplazado", "aplazada", "suspended", "suspendido",
}
_CANCELLED_STATUS_KEYS = {"cancelled", "canceled", "canc", "cancelado", "cancelada"}
_ABANDONED_STATUS_KEYS = {"abandoned", "abd", "abandono", "abandonado", "interrupted"}
_HALFTIME_STATUS_KEYS = {"ht", "bt", "halftime", "half time", "break", "descanso"}
_LIVE_STATUS_KEYS = {
    "live", "1h", "2h", "in play", "inplay", "in progress", "playing",
    "en directo", "first half", "second half", "1st half", "2nd half",
    "et", "p", "extra time", "penalties", "penalty shootout",
}
_UPCOMING_STATUS_KEYS = {
    "ns", "not started", "scheduled", "programado", "fixture", "upcoming", "proximo", "próximo",
}
LIVE_STALE_SECONDS = 120


def _status_key(value: Any) -> str:
    text = _text(value, 180).casefold().replace("_", " ").replace("-", " ")
    text = "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"\s+", " ", text).strip()


def _status_values(item: dict[str, Any]) -> list[tuple[str, str]]:
    """Collect only status-shaped fields; minute, score and kickoff are not status."""
    values: list[tuple[str, str]] = []

    def add(source: str, value: Any) -> None:
        if isinstance(value, dict):
            for key in ("key", "short", "long", "status", "state", "label", "lifecycle"):
                if value.get(key) not in (None, ""):
                    add(f"{source}.{key}", value.get(key))
            return
        key = _status_key(value)
        if key and not key.isdigit():
            values.append((source, key))

    for field in (
        "lifecycle", "v935_lifecycle", "v935_raw_lifecycle", "match_status", "fixture_status", "sports_status",
        "provider_status", "status_short", "short_status", "status_code", "status",
        "safe_status", "client_status_label", "live_status_label", "calendar_status",
    ):
        add(field, item.get(field))

    status_info = item.get("status_info")
    if isinstance(status_info, dict):
        add("status_info", status_info)
        if status_info.get("is_finished") is True:
            add("status_info.is_finished", "ft")
        if status_info.get("is_live") is True:
            add("status_info.is_live", "live")
    if item.get("is_finished") is True:
        add("is_finished", "ft")
    if item.get("is_live") is True:
        add("is_live", "live")

    fixture = item.get("fixture")
    if isinstance(fixture, dict):
        add("fixture.status", fixture.get("status"))

    for payload_field in ("raw_json", "payload_json"):
        raw = item.get(payload_field)
        payload = raw if isinstance(raw, dict) else None
        if payload is None and isinstance(raw, str) and 1 < len(raw) <= 200_000:
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                payload = None
        if not isinstance(payload, dict):
            continue
        for key in ("status", "strStatus", "match_status", "fixture_status"):
            add(f"{payload_field}.{key}", payload.get(key))
        nested_fixture = payload.get("fixture")
        if isinstance(nested_fixture, dict):
            add(f"{payload_field}.fixture.status", nested_fixture.get("status"))

    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source, key in values:
        marker = (source, key)
        if marker not in seen:
            seen.add(marker)
            deduped.append(marker)
    return deduped


def _status_kind(key: str) -> str:
    if key in _FINISHED_STATUS_KEYS or key.startswith("finalizado") or key.startswith("finished"):
        return "FINISHED"
    if key in _POSTPONED_STATUS_KEYS or key.startswith("postpon") or key.startswith("aplaz"):
        return "POSTPONED"
    if key in _CANCELLED_STATUS_KEYS or key.startswith("cancel"):
        return "CANCELLED"
    if key in _ABANDONED_STATUS_KEYS or key.startswith("abandon"):
        return "ABANDONED"
    if key in _HALFTIME_STATUS_KEYS:
        return "HALFTIME"
    if key in _LIVE_STATUS_KEYS or key.startswith("en directo"):
        return "LIVE"
    if key in _UPCOMING_STATUS_KEYS or key.startswith("proximo"):
        return "UPCOMING"
    if key in {"archived", "archive", "historical", "historico"}:
        return "ARCHIVED"
    return "UNKNOWN"


def _live_freshness_truth(
    item: dict[str, Any],
    raw_lifecycle: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return the freshness decision used by every client-facing LIVE surface."""
    source = dict(item or {})
    nested = [
        value for value in (
            source.get("v935_freshness"),
            source.get("freshness"),
            source.get("live_depth"),
            source.get("status_info"),
        )
        if isinstance(value, dict)
    ]
    explicit_stale = bool(
        source.get("is_stale")
        or source.get("stale")
        or any(value.get("is_stale") or value.get("stale") for value in nested)
    )
    timestamp = (
        source.get("live_updated_at")
        or source.get("provider_updated_at")
        or source.get("updated_at")
    )
    parsed = _parse_iso(timestamp)
    age = None if parsed is None else max(0, int((madrid_now(now) - parsed).total_seconds()))
    raw_is_live = raw_lifecycle in {"LIVE", "HALFTIME"}
    match_shaped = bool(
        source.get("id")
        or source.get("match_id")
        or source.get("external_id")
        or match_kickoff_madrid(source)
    )
    freshness_required = bool(timestamp or nested or explicit_stale or match_shaped)
    stale = bool(
        raw_is_live
        and freshness_required
        and (explicit_stale or age is None or age > LIVE_STALE_SECONDS)
    )
    if not stale:
        stale_reason = ""
    elif explicit_stale:
        stale_reason = "EXPLICIT_STALE_EVIDENCE"
    elif age is None:
        stale_reason = "LIVE_TIMESTAMP_MISSING"
    else:
        stale_reason = "LIVE_EVIDENCE_TOO_OLD"
    return {
        "status": "STALE" if stale else "FRESH" if age is not None else "UNKNOWN",
        "age_seconds": age,
        "is_stale": stale,
        "stale_reason": stale_reason,
        "timestamp_present": parsed is not None,
        "freshness_required": freshness_required,
    }

def match_status_truth(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Fail-closed status and freshness truth shared by every sports surface."""
    source = dict(item or {})
    signals = _status_values(source)
    kinds = [_status_kind(key) for _source, key in signals]
    terminal_kinds = {
        kind for kind in kinds
        if kind in {"FINISHED", "POSTPONED", "CANCELLED", "ABANDONED", "ARCHIVED"}
    }
    live_kinds = {kind for kind in kinds if kind in {"LIVE", "HALFTIME"}}
    conflict = bool(terminal_kinds and live_kinds)

    raw_lifecycle = ""
    for terminal in ("ABANDONED", "CANCELLED", "POSTPONED", "ARCHIVED", "FINISHED"):
        if terminal in terminal_kinds:
            raw_lifecycle = terminal
            break
    if raw_lifecycle == "FINISHED" and not _score_confirmed(source):
        raw_lifecycle = "RESULT_PENDING"
    if not raw_lifecycle and "HALFTIME" in live_kinds:
        raw_lifecycle = "HALFTIME"
    if not raw_lifecycle and "LIVE" in live_kinds:
        raw_lifecycle = "LIVE"

    if not raw_lifecycle:
        kickoff = match_kickoff_madrid(source)
        if kickoff is None:
            raw_lifecycle = "INCOMPLETE"
        elif kickoff < madrid_now(now):
            raw_lifecycle = "FINISHED" if _score_confirmed(source) else "RESULT_PENDING"
        else:
            raw_lifecycle = "UPCOMING"

    freshness = _live_freshness_truth(source, raw_lifecycle, now)
    lifecycle = "STALE" if freshness["is_stale"] else raw_lifecycle
    return {
        "contract": "MATCH-STATUS-TRUTH-V2",
        "lifecycle": lifecycle,
        "raw_lifecycle": raw_lifecycle,
        "is_live": raw_lifecycle in {"LIVE", "HALFTIME"} and not conflict and not freshness["is_stale"],
        "is_finished": lifecycle in {"FINISHED", "ARCHIVED"},
        "is_stale": bool(freshness["is_stale"]),
        "stale_reason": freshness["stale_reason"],
        "live_age_seconds": freshness["age_seconds"],
        "live_timestamp_present": freshness["timestamp_present"],
        "status_conflict": conflict,
        "conflict_type": "LIVE_TERMINAL" if conflict else "",
        "signal_kinds": sorted({kind for kind in kinds if kind != "UNKNOWN"}),
        "signal_count": len(signals),
        "live_inferred_from_time": False,
        "live_inferred_from_score": False,
        "live_inferred_from_minute": False,
    }

def _live_evidence_confirmed(item: dict[str, Any], raw_status: str) -> bool:
    truth = match_status_truth({**dict(item or {}), "status": raw_status or item.get("status")})
    return bool(truth.get("is_live") and not truth.get("status_conflict"))


def normalize_match_lifecycle(item: dict[str, Any], now: datetime | None = None) -> str:
    if not is_match_complete(item):
        return "INCOMPLETE"
    truth = match_status_truth(item, now)
    if item.get("archived_at"):
        return "ARCHIVED"
    return str(truth.get("lifecycle") or "INCOMPLETE")


def get_match_freshness(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    truth = match_status_truth(item, now)
    age = truth.get("live_age_seconds")
    stale = bool(truth.get("is_stale"))
    return {
        "status": "STALE" if stale else "FRESH" if age is not None else "UNKNOWN",
        "age_seconds": age,
        "is_stale": stale,
        "stale_reason": truth.get("stale_reason") or "",
        "label": "Datos retrasados" if stale else "Actualizado" if age is not None else "Sin marca temporal",
    }


def classify_match_for_surface(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    truth = match_status_truth(item, now)
    lifecycle = str(truth.get("lifecycle") or "INCOMPLETE")
    kickoff = match_kickoff_madrid(item)
    today = madrid_now(now).date()
    is_today = bool(kickoff and kickoff.date() == today)
    return {
        "lifecycle": lifecycle,
        "home": is_today and lifecycle in {"UPCOMING", "LIVE", "HALFTIME"},
        "calendar": lifecycle == "UPCOMING",
        "live": bool(truth.get("is_live")),
        "results": lifecycle in {"FINISHED", "ARCHIVED"},
        "incidents": lifecycle in {"RESULT_PENDING", "POSTPONED", "CANCELLED", "ABANDONED", "STALE", "INCOMPLETE"},
        "admin": True,
    }


def is_match_publicly_visible(item: dict[str, Any], surface: str = "calendar", now: datetime | None = None) -> bool:
    return bool(classify_match_for_surface(item, now).get(surface))


def enrich_match_lifecycle(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    result = dict(item or {})
    truth = match_status_truth(result, now)
    result["v935_status_truth"] = truth
    result["v935_lifecycle"] = str(truth.get("lifecycle") or "INCOMPLETE")
    result["v935_raw_lifecycle"] = str(truth.get("raw_lifecycle") or result["v935_lifecycle"])
    result["v935_surface"] = classify_match_for_surface(result, now)
    result["v935_freshness"] = {
        "status": "STALE" if truth.get("is_stale") else "FRESH" if truth.get("live_age_seconds") is not None else "UNKNOWN",
        "age_seconds": truth.get("live_age_seconds"),
        "is_stale": bool(truth.get("is_stale")),
        "stale_reason": truth.get("stale_reason") or "",
        "label": "Datos retrasados" if truth.get("is_stale") else "Actualizado" if truth.get("live_age_seconds") is not None else "Sin marca temporal",
    }
    result["v935_source"] = get_match_source(result)
    result["v935_complete"] = is_match_complete(result)
    return result

def archive_expired_match_safely(item: dict[str, Any], now: datetime | None = None, after_days: int = 30) -> dict[str, Any]:
    result = enrich_match_lifecycle(item, now)
    kickoff = match_kickoff_madrid(result)
    if result["v935_lifecycle"] == "FINISHED" and kickoff and kickoff < madrid_now(now) - timedelta(days=max(1, after_days)):
        result["v935_lifecycle"] = "ARCHIVED"
        result["v935_archive_candidate"] = True
    else:
        result["v935_archive_candidate"] = False
    return result


def get_odds_freshness(
    timestamp: Any,
    now: datetime | None = None,
    *,
    odds: Any = None,
    source: Any = None,
    match_lifecycle: str = "UPCOMING",
    market_open: bool = True,
) -> dict[str, Any]:
    value = _float(odds)
    source_text = _text(source, 80)
    if value is None or value <= 1.0 or not _present(source_text):
        status = "INVALID"
        age = None
    elif not market_open or match_lifecycle in {"LIVE", "HALFTIME", "FINISHED", "RESULT_PENDING", "CANCELLED", "ABANDONED", "ARCHIVED"}:
        status = "EXPIRED"
        age = None
    else:
        parsed = _parse_iso(timestamp)
        age = None if parsed is None else max(0, int((madrid_now(now) - parsed).total_seconds()))
        if age is None:
            status = "INVALID"
        elif age <= 15 * 60:
            status = "FRESH"
        elif age <= 60 * 60:
            status = "RECORDED"
        else:
            status = "STALE"
    labels = {
        "FRESH": "Cuota actual",
        "RECORDED": "Ultima cuota registrada",
        "STALE": "Cuota retrasada",
        "EXPIRED": "Mercado cerrado",
        "INVALID": "Cuota no disponible",
    }
    return {
        "status": status,
        "label": labels[status],
        "age_seconds": age,
        "is_fresh": status == "FRESH",
        "is_usable": status in {"FRESH", "RECORDED"},
        "is_publishable": status == "FRESH",
    }


def is_odds_valid(odds: Any, source: Any) -> bool:
    value = _float(odds)
    return bool(value is not None and value > 1.0 and _present(source))


def is_odds_usable(item: dict[str, Any], now: datetime | None = None) -> bool:
    return bool(_pick_odds_state(item, now).get("is_usable"))


def is_odds_publishable(item: dict[str, Any], now: datetime | None = None) -> bool:
    return bool(_pick_odds_state(item, now).get("is_publishable"))


def get_odds_display_label(item: dict[str, Any], now: datetime | None = None) -> str:
    return str(_pick_odds_state(item, now).get("label") or "Cuota no disponible")


def _pick_match_view(item: dict[str, Any]) -> dict[str, Any]:
    match = dict(item)
    match["id"] = item.get("match_id") or item.get("id")
    match["status"] = item.get("match_status") or item.get("fixture_status") or item.get("sports_status") or "NS"
    return match


def _pick_odds_state(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    match_lifecycle = str(item.get("v935_match_lifecycle") or normalize_match_lifecycle(_pick_match_view(item), now))
    return get_odds_freshness(
        item.get("odds_updated_at") or item.get("updated_at") or item.get("published_at") or item.get("created_at"),
        now,
        odds=item.get("client_odds_label") or item.get("odds") or item.get("price"),
        source=item.get("odds_source") or item.get("source"),
        match_lifecycle=match_lifecycle,
        market_open=not bool(item.get("market_closed")),
    )


def is_pick_complete(item: dict[str, Any], now: datetime | None = None) -> bool:
    if not isinstance(item, dict):
        return False
    pick_id = item.get("id") or item.get("pick_id")
    match_id = item.get("match_id")
    market = item.get("market") or item.get("market_name") or item.get("pick_type")
    selection = item.get("client_selection_label") or item.get("selection_display") or item.get("selection")
    timestamp = item.get("odds_updated_at") or item.get("published_at") or item.get("updated_at") or item.get("created_at")
    source = item.get("odds_source") or item.get("source")
    return bool(
        _present(pick_id) and _present(match_id) and _present(market) and _present(selection)
        and _present(timestamp) and is_odds_valid(item.get("client_odds_label") or item.get("odds") or item.get("price"), source)
        and is_match_complete(_pick_match_view(item))
    )


def normalize_pick_lifecycle(item: dict[str, Any], now: datetime | None = None) -> str:
    if not is_pick_complete(item, now):
        return "INCOMPLETE"
    raw = _key(item.get("lifecycle") or item.get("pick_status") or item.get("status"))
    result = _key(item.get("result_status") or item.get("result") or item.get("grading_status"))
    if raw in {"archived", "archive", "historical", "historico", "histórico"}:
        return "ARCHIVED"
    if result in {"won", "win", "ganado", "acertado"}:
        return "WON"
    if result in {"lost", "loss", "perdido", "fallado"}:
        return "LOST"
    if result in {"void", "push", "nulo"}:
        return "VOID"
    if raw in {"cancelled", "canceled", "cancelado"}:
        return "CANCELLED"
    match_lifecycle = normalize_match_lifecycle(_pick_match_view(item), now)
    if match_lifecycle in {"FINISHED", "RESULT_PENDING", "POSTPONED", "CANCELLED", "ABANDONED", "ARCHIVED"}:
        return "EXPIRED"
    if raw in {"draft", "borrador"}:
        return "DRAFT"
    if raw in {"review", "pending_review", "revision", "revisión"}:
        return "REVIEW"
    if raw in {"approved", "aprobado"}:
        return "APPROVED"
    if raw in {"live", "in_play"} or match_lifecycle in {"LIVE", "HALFTIME"}:
        return "LIVE"
    if raw in {"published", "active", "publicado"}:
        return "PUBLISHED"
    return "DRAFT"


def is_pick_publishable(item: dict[str, Any], now: datetime | None = None) -> bool:
    lifecycle = normalize_pick_lifecycle(item, now)
    return lifecycle in {"PUBLISHED", "LIVE"} and is_pick_complete(item, now) and is_odds_usable(item, now)


def is_pick_evaluable(item: dict[str, Any], now: datetime | None = None) -> bool:
    lifecycle = normalize_pick_lifecycle(item, now)
    stake = _float(item.get("stake") or item.get("stake_units"))
    return bool(lifecycle in {"WON", "LOST", "VOID"} and stake is not None and stake > 0 and is_pick_complete(item, now))


def get_pick_data_quality(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    if not is_pick_complete(item, now):
        reasons.append("missing_match_market_selection_odds_timestamp_or_source")
    lifecycle = normalize_pick_lifecycle(item, now)
    odds = _pick_odds_state(item, now)
    if odds["status"] in {"STALE", "EXPIRED", "INVALID"}:
        reasons.append(f"odds_{odds['status'].lower()}")
    if lifecycle in {"EXPIRED", "CANCELLED", "ARCHIVED"}:
        reasons.append(f"pick_{lifecycle.lower()}")
    reasons = list(dict.fromkeys(reasons))
    return {
        "status": "PASS" if not reasons else "BLOCKED",
        "reasons": reasons,
        "publishable": is_pick_publishable(item, now),
        "evaluable": is_pick_evaluable(item, now),
        "lifecycle": lifecycle,
        "odds": odds,
    }


def enrich_pick_lifecycle(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    result = dict(item or {})
    result["v935_match_lifecycle"] = normalize_match_lifecycle(_pick_match_view(result), now)
    result["v935_lifecycle"] = normalize_pick_lifecycle(result, now)
    result["v935_odds"] = _pick_odds_state(result, now)
    result["v935_quality"] = get_pick_data_quality(result, now)
    result["v935_publishable"] = is_pick_publishable(result, now)
    result["v935_evaluable"] = is_pick_evaluable(result, now)
    return result


def archive_pick_safely(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    result = enrich_pick_lifecycle(item, now)
    result["v935_archive_candidate"] = result["v935_lifecycle"] in {"WON", "LOST", "VOID", "CANCELLED", "EXPIRED"}
    return result


def _dedupe(items: Iterable[dict[str, Any]], key_name: str = "id") -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        key = _text(item.get(key_name) or item.get("match_id") or item.get("pick_id"), 100)
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def build_data_trust_snapshot(
    matches: Iterable[dict[str, Any]],
    picks: Iterable[dict[str, Any]],
    *,
    provider_status: str = "waiting_for_sync",
    last_sync: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    match_items = _dedupe(enrich_match_lifecycle(item, now) for item in matches if isinstance(item, dict))
    pick_items = _dedupe((enrich_pick_lifecycle(item, now) for item in picks if isinstance(item, dict)), "id")
    match_counts = {state: 0 for state in MATCH_LIFECYCLES}
    pick_counts = {state: 0 for state in PICK_LIFECYCLES}
    odds_counts = {state: 0 for state in ODDS_STATES}
    for item in match_items:
        match_counts[item["v935_lifecycle"]] += 1
    for item in pick_items:
        pick_counts[item["v935_lifecycle"]] += 1
        odds_counts[item["v935_odds"]["status"]] += 1
    issues: list[dict[str, Any]] = []
    issue_specs = (
        ("incomplete_matches", match_counts["INCOMPLETE"], "P1", "Complete or quarantine missing match fields."),
        ("result_pending_matches", match_counts["RESULT_PENDING"], "P1", "Run the authorized result sync and grade safely."),
        ("incomplete_picks", pick_counts["INCOMPLETE"], "P1", "Keep incomplete picks outside client surfaces."),
        ("stale_odds", odds_counts["STALE"], "P1", "Refresh odds through the protected sync job."),
        ("invalid_odds", odds_counts["INVALID"], "P1", "Keep invalid odds blocked and repair source data."),
    )
    for issue_type, count, priority, action in issue_specs:
        if count:
            issues.append({"type": issue_type, "count": count, "priority": priority, "next_action": action})
    publicable = sum(1 for item in pick_items if item["v935_publishable"])
    evaluable = sum(1 for item in pick_items if item["v935_evaluable"])
    non_evaluable = max(0, len(pick_items) - evaluable)
    has_data = bool(match_items or pick_items)
    status = "BLOCKED" if any(item["priority"] == "P0" for item in issues) else "ATTENTION" if issues else "READY" if has_data else "WAITING_FOR_REAL_DATA"
    return {
        "status": status,
        "provider_status": _text(provider_status, 80) or "waiting_for_sync",
        "last_safe_sync": _text(last_sync, 100),
        "match_counts": match_counts,
        "pick_counts": pick_counts,
        "odds_counts": odds_counts,
        "publicable_picks": publicable,
        "evaluable_picks": evaluable,
        "non_evaluable_picks": non_evaluable,
        "issues": issues,
        "blockers": [item for item in issues if item["priority"] == "P0"],
        "next_action": issues[0]["next_action"] if issues else "review_launch_readiness" if has_data else "run_authorized_sports_sync",
        "no_external_calls": True,
        "database_writes": 0,
        "no_fake_data": True,
        "generated_at_madrid": madrid_now(now).isoformat(timespec="seconds"),
    }
