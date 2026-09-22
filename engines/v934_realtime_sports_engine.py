"""Safe realtime sports snapshots built exclusively from local DB/cache data."""
from __future__ import annotations

from engines.snapshot_copy_engine import clone_snapshot
import threading
import time
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from engines.madrid_time_engine import format_madrid_sync_label
from engines.v935_launch_trust_engine import match_status_truth
from engines.realtime_state_engine import build_realtime_match_evidence


MADRID_TZ = ZoneInfo("Europe/Madrid")
LIVE_POLL_SECONDS = 45
IDLE_POLL_SECONDS = 180
MATCH_CACHE_TTL_SECONDS = 15
ODDS_FRESH_SECONDS = 900
ODDS_STALE_SECONDS = 3600

_CACHE_LOCK = threading.RLock()
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_BUILD_LOCKS: dict[str, threading.Lock] = {}
_CACHE_GENERATIONS: dict[str, object] = {}


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


def _status_from_truth(item: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    return _status_presentation(match_status_truth(item, now))


def _status_presentation(truth: dict[str, Any]) -> dict[str, Any]:
    """Format an already-computed local decision, not a second lifecycle engine."""
    lifecycle = str(truth.get("lifecycle") or "INCOMPLETE")
    raw_lifecycle = str(truth.get("raw_lifecycle") or lifecycle)
    keys = {
        "LIVE": "live",
        "HALFTIME": "halftime",
        "FINISHED": "finished",
        "ARCHIVED": "finished",
        "RESULT_PENDING": "pending",
        "POSTPONED": "postponed",
        "SUSPENDED": "suspended",
        "CANCELLED": "cancelled",
        "ABANDONED": "abandoned",
        "STALE": "stale",
        "UPCOMING": "scheduled",
        "INCOMPLETE": "pending",
    }
    labels = {
        "LIVE": "En directo",
        "HALFTIME": "Descanso",
        "FINISHED": "Finalizado",
        "ARCHIVED": "Finalizado",
        "RESULT_PENDING": "Resultado pendiente",
        "POSTPONED": "Aplazado",
        "SUSPENDED": "Suspendido",
        "CANCELLED": "Cancelado",
        "ABANDONED": "Abandonado",
        "STALE": "Datos retrasados",
        "UPCOMING": "Programado",
        "INCOMPLETE": "Estado pendiente",
    }
    return {
        "key": keys.get(lifecycle, "pending"),
        "label": labels.get(lifecycle, "Estado pendiente"),
        "is_live": bool(truth.get("is_live")),
        "was_live_signal": raw_lifecycle in {"LIVE", "HALFTIME"},
        "is_finished": bool(truth.get("is_finished")),
        "is_stale": bool(truth.get("is_stale")),
        "truth": truth,
    }


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
    # One evaluation for the existing snapshot and its additive UI projection.
    # Sports Truth still owns lifecycle; this is not another classifier.
    evaluated_at = _now(now)
    state, truth = build_realtime_match_evidence(item, now=evaluated_at)
    status = _status_presentation(truth)
    # Invalid priority timestamps do not fall back to a newer generic clock.
    updated_at = state["provider_observed_at"]
    age = state["freshness_seconds"]
    raw_minute = state["minute"]
    # Keep numeric legacy minutes while retaining observed added time (90+4).
    minute = int(raw_minute) if raw_minute is not None and raw_minute.isdigit() else raw_minute
    home_score = state["score_home"]
    away_score = state["score_away"]
    score_available = home_score is not None and away_score is not None and (
        status["is_live"] or status["was_live_signal"] or status["is_finished"]
    )
    stale = status["is_stale"]
    return {
        "id": match_id,
        "home_team": home,
        "away_team": away,
        "competition": competition,
        "match_date": match_date,
        "kickoff_time": kickoff,
        "status": status["key"],
        "status_label": state.get("period_label") or status["label"],
        "is_live": status["is_live"],
        "was_live_signal": status["was_live_signal"],
        "is_finished": status["is_finished"],
        "minute": minute,
        "home_score": home_score if score_available else None,
        "away_score": away_score if score_available else None,
        "source": source,
        "updated_at": updated_at,
        # Preserve the original provider clock fields for downstream re-evaluation.
        # updated_at is a compatibility/display alias, not freshness provenance.
        # Keep invalid priority clocks too: a newer lower-priority timestamp must
        # not turn rejected evidence into fresh LIVE on a second projection.
        **{field: _text(item.get(field), 100)
           for field in ("live_updated_at", "provider_updated_at", "last_synced_at")
           if field in item},
        "age_seconds": age,
        "is_stale": stale,
        "status_truth": status["truth"],
        "realtime_state": state,
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
    evaluated_at = _now(now)
    seen: set[str] = set()
    normalized_matches: list[dict[str, Any]] = []
    # A match leaving LIVE must still reach open consumers as a final update.
    for raw in (list(summary.get("valid_matches_today") or [])
                + list(summary.get("valid_upcoming_matches") or [])
                + list(summary.get("finished_matches") or [])):
        # Keep the same first-valid-record policy, but do not normalize a match
        # again just because it is also present in another summary section.
        raw_id = _text(raw.get("id") or raw.get("match_id") or raw.get("external_id"), 90) if isinstance(raw, dict) else ""
        if raw_id and raw_id in seen:
            continue
        match = normalize_match(raw, evaluated_at)
        if match and match["id"] not in seen:
            seen.add(match["id"])
            normalized_matches.append(match)
    picks = [pick for pick in (normalize_pick(item, evaluated_at) for item in summary.get("valid_active_picks") or []) if pick]
    stale_live = [item for item in normalized_matches if item["was_live_signal"] and item["is_stale"]]
    live = [item for item in normalized_matches if item["is_live"]]
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
        "generated_at_madrid": _iso(evaluated_at),
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
        hit = bool(cached and not force and now_mono < float(cached.get("expires_at") or 0))
        if not hit:
            build_lock = _CACHE_BUILD_LOCKS.setdefault(cache_key, threading.Lock())
    if hit:
        # Cache payloads are private and replaced, never mutated in place.
        # Copying outside the index lock lets independent keys keep progressing.
        return clone_snapshot(cached["payload"]), "hit"

    # Keep one builder per key and recheck after waiting for it. Force still
    # requests a rebuild; it does not bypass copy isolation or invalidation.
    with build_lock:
        now_mono = time.monotonic()
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
            hit = bool(cached and not force and now_mono < float(cached.get("expires_at") or 0))
            generation = _CACHE_GENERATIONS.setdefault(cache_key, object())
        if hit:
            return clone_snapshot(cached["payload"]), "hit"
        try:
            payload = builder()
        except Exception:
            with _CACHE_LOCK:
                stale = _CACHE.get(cache_key)
            if stale:
                fallback = clone_snapshot(stale["payload"])
                fallback["cache_status"] = "stale_fallback"
                fallback["safe_message"] = "Actualización temporalmente no disponible. Se conserva la última información confirmada."
                return fallback, "stale_fallback"
            return build_realtime_snapshot({}), "safe_empty"
        stored_payload = clone_snapshot(payload)
        stored_at = time.monotonic()
        with _CACHE_LOCK:
            # A sync may invalidate this key while its old builder is running.
            # That in-flight caller keeps its isolated view, but no later request
            # may hit a value built before the invalidation. No clock is renewed.
            if _CACHE_GENERATIONS.get(cache_key) is generation:
                _CACHE[cache_key] = {
                    "payload": stored_payload,
                    "created_at": stored_at,
                    "expires_at": stored_at + max(5, min(int(ttl_seconds), 300)),
                }
        return clone_snapshot(payload), "refreshed"


def invalidate_realtime_cache(prefix: str = "") -> int:
    safe_prefix = _text(prefix, 160)
    with _CACHE_LOCK:
        keys = [key for key in _CACHE if not safe_prefix or key.startswith(safe_prefix)]
        for key in keys:
            _CACHE.pop(key, None)
        # Include builds that have not published an entry yet. Retain per-key
        # build locks so invalidation cannot create a second concurrent builder.
        for key in _CACHE_BUILD_LOCKS:
            if not safe_prefix or key.startswith(safe_prefix):
                _CACHE_GENERATIONS[key] = object()
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
