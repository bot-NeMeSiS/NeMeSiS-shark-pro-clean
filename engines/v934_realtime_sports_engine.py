"""Safe realtime sports snapshots built exclusively from local DB/cache data."""
from __future__ import annotations

import copy
import threading
import time
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from engines.madrid_time_engine import format_madrid_sync_label


MADRID_TZ = ZoneInfo("Europe/Madrid")
LIVE_POLL_SECONDS = 45
IDLE_POLL_SECONDS = 180
MATCH_CACHE_TTL_SECONDS = 15
LIVE_STALE_SECONDS = 120
ODDS_FRESH_SECONDS = 900
ODDS_STALE_SECONDS = 3600

_CACHE_LOCK = threading.RLock()
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_BUILD_LOCKS: dict[str, threading.Lock] = {}


def _now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(MADRID_TZ)
    if value.tzinfo is None:
        value = value.replace(tzinfo=MADRID_TZ)
    return value.astimezone(MADRID_TZ)


def _iso(now: datetime | None = None) -> str:
    return _now(now).isoformat(timespec="seconds")


def _text(value: Any, limit: int = 180) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _parse_time(value: Any) -> datetime | None:
    text = _text(value, 80)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=MADRID_TZ)
        return parsed.astimezone(MADRID_TZ)
    except (TypeError, ValueError):
        return None


def _age_seconds(value: Any, now: datetime | None = None) -> int | None:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    return max(0, int((_now(now) - parsed).total_seconds()))


def _number(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 999 else None


def _minute(value: Any) -> int | None:
    number = _number(value)
    return number if number is not None and number <= 130 else None


def _status(value: Any) -> dict[str, Any]:
    raw = _text(value, 50).lower()
    if raw in {"1h", "2h", "live", "in play", "en directo", "playing"}:
        return {"key": "live", "label": "En directo", "is_live": True, "is_finished": False}
    if raw in {"ht", "half time", "halftime", "break", "descanso"}:
        return {"key": "halftime", "label": "Descanso", "is_live": True, "is_finished": False}
    if raw in {"ft", "aet", "pen", "finished", "finalizado", "final"}:
        return {"key": "finished", "label": "Finalizado", "is_live": False, "is_finished": True}
    if raw in {"postponed", "cancelled", "canceled", "suspended", "aplazado", "cancelado"}:
        return {"key": "interrupted", "label": "Interrumpido", "is_live": False, "is_finished": False}
    return {"key": "scheduled", "label": "Programado", "is_live": False, "is_finished": False}


def odds_freshness(timestamp: Any, now: datetime | None = None) -> dict[str, Any]:
    age = _age_seconds(timestamp, now)
    if age is None:
        return {
            "status": "recorded_unknown_age",
            "label": "Ultima registrada",
            "age_seconds": None,
            "is_fresh": False,
            "is_stale": True,
        }
    if age <= ODDS_FRESH_SECONDS:
        status, label = "fresh", "Actualizada"
    elif age <= ODDS_STALE_SECONDS:
        status, label = "recorded", "Ultima registrada"
    else:
        status, label = "stale", "Dato retrasado"
    return {
        "status": status,
        "label": label,
        "age_seconds": age,
        "is_fresh": status == "fresh",
        "is_stale": status == "stale",
    }


def normalize_match(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    match_id = _text(item.get("id") or item.get("match_id") or item.get("external_id"), 90)
    home = _text(item.get("home_team") or item.get("client_home") or item.get("home_name"), 120)
    away = _text(item.get("away_team") or item.get("client_away") or item.get("away_name"), 120)
    competition = _text(
        item.get("competition_name")
        or item.get("league_name")
        or item.get("client_competition")
        or item.get("calendar_competition")
        or item.get("competition")
        or item.get("league"),
        140,
    )
    match_date = _text(item.get("match_date") or item.get("date"), 10)
    kickoff = _text(
        item.get("kickoff_time")
        or item.get("match_time")
        or item.get("client_time_label")
        or item.get("calendar_time"),
        24,
    )
    source = _text(item.get("source"), 80)
    if not all((match_id, home, away, competition, match_date, kickoff, source)):
        return None
    raw_status = _text(
        item.get("status")
        or item.get("match_status")
        or item.get("fixture_status")
        or item.get("calendar_status"),
        50,
    )
    status = _status(raw_status)
    updated_at = _text(
        item.get("live_updated_at")
        or item.get("provider_updated_at")
        or item.get("updated_at"),
        80,
    )
    age = _age_seconds(updated_at, now)
    minute = _minute(item.get("minute") or item.get("elapsed") or item.get("live_minute")) if status["is_live"] else None
    home_score = _number(item.get("home_score"))
    away_score = _number(item.get("away_score"))
    score_available = home_score is not None and away_score is not None and (status["is_live"] or status["is_finished"])
    phase_evidence = raw_status.lower() in {
        "1h", "2h", "ht", "half time", "halftime", "break", "descanso",
        "first half", "second half", "1st half", "2nd half",
    }
    if status["is_live"] and minute is None and not score_available and not phase_evidence:
        status = {"key": "pending", "label": "Estado pendiente", "is_live": False, "is_finished": False}
    stale = bool(status["is_live"] and (age is None or age > LIVE_STALE_SECONDS))
    return {
        "id": match_id,
        "home_team": home,
        "away_team": away,
        "competition": competition,
        "match_date": match_date,
        "kickoff_time": kickoff,
        "status": status["key"],
        "status_label": "Datos retrasados" if stale else status["label"],
        "is_live": status["is_live"],
        "is_finished": status["is_finished"],
        "minute": minute,
        "home_score": home_score if score_available else None,
        "away_score": away_score if score_available else None,
        "source": source,
        "updated_at": updated_at,
        "age_seconds": age,
        "is_stale": stale,
        "detail_url": f"/match/{match_id}",
    }


def normalize_pick(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    pick_id = _text(item.get("id"), 90)
    match_id = _text(item.get("match_id"), 90)
    home = _text(item.get("home_team") or item.get("client_home"), 120)
    away = _text(item.get("away_team") or item.get("client_away"), 120)
    market = _text(item.get("market") or item.get("market_name") or item.get("bet_type"), 140)
    selection = _text(item.get("client_selection_label") or item.get("selection_display") or item.get("selection"), 140)
    try:
        odds = float(str(item.get("client_odds_label") or item.get("odds") or item.get("price") or "").replace(",", "."))
    except (TypeError, ValueError):
        odds = 0.0
    if not all((pick_id, match_id, home, away, market, selection)) or odds <= 1.0:
        return None
    timestamp = _text(item.get("odds_updated_at") or item.get("updated_at") or item.get("created_at"), 80)
    freshness = odds_freshness(timestamp, now)
    return {
        "id": pick_id,
        "match_id": match_id,
        "match": f"{home} vs {away}",
        "market": market,
        "selection": selection,
        "odds": round(odds, 2),
        "odds_recorded_at": timestamp,
        "odds_freshness": freshness,
        "source": _text(item.get("odds_source") or item.get("source") or "published_pick", 80),
        "detail_url": f"/match/{match_id}",
    }


def build_realtime_snapshot(summary: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    summary = summary if isinstance(summary, dict) else {}
    seen: set[str] = set()
    normalized_matches: list[dict[str, Any]] = []
    for raw in list(summary.get("valid_matches_today") or []) + list(summary.get("valid_upcoming_matches") or []):
        match = normalize_match(raw, now)
        if match and match["id"] not in seen:
            seen.add(match["id"])
            normalized_matches.append(match)
    picks = [pick for pick in (normalize_pick(item, now) for item in summary.get("valid_active_picks") or []) if pick]
    all_live = [item for item in normalized_matches if item["is_live"]]
    stale_live = [item for item in all_live if item["is_stale"]]
    live = [item for item in all_live if not item["is_stale"]]
    # Stale live evidence remains available to protected diagnostics only. It must
    # not leak into public schedules, cards, counters, or polling decisions.
    matches = [item for item in normalized_matches if not item["is_stale"]]
    finished = [item for item in matches if item["is_finished"]]
    poll_after = LIVE_POLL_SECONDS if live else IDLE_POLL_SECONDS
    freshness_values = [item["odds_freshness"]["status"] for item in picks]
    odds_status = (
        "fresh"
        if freshness_values and all(value == "fresh" for value in freshness_values)
        else "recorded_or_stale"
        if freshness_values
        else "no_real_odds"
    )
    last_safe_sync = _text(summary.get("last_sync"), 80)
    return {
        "generated_at_madrid": _iso(now),
        "matches": matches,
        "live": live,
        "stale_live": stale_live,
        "finished": finished,
        "picks": picks,
        "counts": {
            "matches": len(matches),
            "live": len(live),
            "finished": len(finished),
            "picks": len(picks),
            "stale_live": len(stale_live),
            "incomplete": len(summary.get("incomplete_matches") or []),
        },
        "provider_status": _text(summary.get("provider_status") or "waiting_for_sync", 60),
        "cache_status": "available" if matches or picks else "empty_safe",
        "last_safe_sync": last_safe_sync,
        "last_safe_sync_label": format_madrid_sync_label(last_safe_sync),
        "realtime_match_status": "live_cached" if live else "schedule_cached" if matches else "waiting_for_real_data",
        "realtime_live_status": "live" if live else "stale" if stale_live else "no_live_events",
        "odds_freshness_status": odds_status,
        "poll_after_seconds": poll_after,
        "safe_message": (
            f"Datos reales actualizados; {len(stale_live)} lectura(s) retrasada(s) quedan fuera del directo."
            if live and stale_live
            else f"No hay directo confirmado; {len(stale_live)} lectura(s) retrasada(s) quedan excluidas."
            if stale_live
            else "Datos confirmados disponibles. La información se mantiene accesible entre actualizaciones."
            if matches or picks
            else "Esperando una sincronización real; no se muestran datos de ejemplo."
        ),
        "no_external_calls": True,
        "no_fake_data": True,
    }


def cached_realtime_snapshot(
    key: str,
    builder: Callable[[], dict[str, Any]],
    *,
    ttl_seconds: int = MATCH_CACHE_TTL_SECONDS,
    force: bool = False,
) -> tuple[dict[str, Any], str]:
    cache_key = _text(key, 160) or "default"
    now_mono = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached and not force and now_mono < float(cached.get("expires_at") or 0):
            return copy.deepcopy(cached["payload"]), "hit"
        build_lock = _CACHE_BUILD_LOCKS.setdefault(cache_key, threading.Lock())

    # Only one request rebuilds a missing key. Waiting requests re-check the
    # cache and reuse that result instead of repeating the CPU-heavy builder.
    with build_lock:
        now_mono = time.monotonic()
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
            if cached and not force and now_mono < float(cached.get("expires_at") or 0):
                return copy.deepcopy(cached["payload"]), "hit"
        try:
            payload = builder()
        except Exception:
            with _CACHE_LOCK:
                stale = _CACHE.get(cache_key)
                if stale:
                    fallback = copy.deepcopy(stale["payload"])
                    fallback["cache_status"] = "stale_fallback"
                    fallback["safe_message"] = "Actualización temporalmente no disponible. Se conserva la última información confirmada."
                    return fallback, "stale_fallback"
            return build_realtime_snapshot({}), "safe_empty"
        stored_at = time.monotonic()
        with _CACHE_LOCK:
            _CACHE[cache_key] = {
                "payload": copy.deepcopy(payload),
                "created_at": stored_at,
                "expires_at": stored_at + max(5, min(int(ttl_seconds), 300)),
            }
        return copy.deepcopy(payload), "refreshed"

def invalidate_realtime_cache(prefix: str = "") -> int:
    safe_prefix = _text(prefix, 160)
    with _CACHE_LOCK:
        keys = [key for key in _CACHE if not safe_prefix or key.startswith(safe_prefix)]
        for key in keys:
            _CACHE.pop(key, None)
    return len(keys)


def realtime_cache_status() -> dict[str, Any]:
    now_mono = time.monotonic()
    with _CACHE_LOCK:
        items = [
            {
                "key": key,
                "fresh": now_mono < float(value.get("expires_at") or 0),
                "age_seconds": max(0, int(now_mono - float(value.get("created_at") or now_mono))),
            }
            for key, value in _CACHE.items()
        ]
    return {"entries": len(items), "items": items[:20], "secrets_visible": False}


def apply_test_transition(match: dict[str, Any], state: str, *, minute: int | None = None, home_score: int | None = None, away_score: int | None = None) -> dict[str, Any]:
    """Pure helper for isolated transition tests; never writes DB or cache."""
    result = dict(match or {})
    allowed = {"scheduled", "live", "halftime", "finished"}
    if state not in allowed:
        raise ValueError("invalid transition state")
    result["status"] = {"scheduled": "NS", "live": "LIVE", "halftime": "HT", "finished": "FT"}[state]
    if state in {"live", "halftime"} and minute is not None:
        result["minute"] = max(0, min(int(minute), 130))
    if state in {"live", "halftime", "finished"}:
        result["home_score"] = max(0, int(home_score or 0))
        result["away_score"] = max(0, int(away_score or 0))
    return result
