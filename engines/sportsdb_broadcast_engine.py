"""Automatic TheSportsDB TV/broadcast memory for upcoming matches.

This module owns provider I/O only inside scheduled automation. Product read
paths consume the persisted Sports History detail and never call TheSportsDB
while rendering a page.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from engines.sports_history_engine import ensure_schema, persist_detail

SOURCE = "thesportsdb"
DETAIL_KIND = "broadcasts"
DETAIL_EXTERNAL_ID = "event_tv"
DEFAULT_LIMIT = 6
DEFAULT_HORIZON_HOURS = 72
DEFAULT_TTL_HOURS = 12
V2_BASE = "https://www.thesportsdb.com/api/v2/json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_instant(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_text(value: Any, limit: int = 180) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def normalize_broadcast(item: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep only display-safe TV schedule fields supplied by TheSportsDB."""
    row = dict(item or {})
    return {
        "schedule_id": _safe_text(row.get("id"), 80),
        "event_id": _safe_text(row.get("idEvent") or row.get("id_event"), 80),
        "channel_id": _safe_text(row.get("idChannel") or row.get("id_channel"), 80),
        "channel": _safe_text(row.get("strChannel") or row.get("channel"), 160),
        "country": _safe_text(row.get("strCountry") or row.get("country"), 120),
        "logo": _safe_text(row.get("strLogo") or row.get("logo"), 500),
        "date": _safe_text(row.get("dateEvent") or row.get("date"), 40),
        "time": _safe_text(row.get("strTime") or row.get("time"), 40),
        "timestamp": _safe_text(
            row.get("strTimeStamp") or row.get("strTimestamp") or row.get("timestamp"),
            80,
        ),
        "source": SOURCE,
    }


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    for key in ("tvevents", "tv", "event_tv", "broadcasts", "events", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, Mapping)]
    for value in payload.values():
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def normalize_event_tv(payload: Any, event_id: str) -> list[dict[str, Any]]:
    event_id = _safe_text(event_id, 80)
    channels = []
    seen = set()
    for item in _payload_rows(payload):
        channel = normalize_broadcast(item)
        if channel["event_id"] and channel["event_id"] != event_id:
            continue
        if not channel["channel"]:
            continue
        identity = (
            channel["channel_id"],
            channel["channel"].casefold(),
            channel["country"].casefold(),
        )
        if identity in seen:
            continue
        seen.add(identity)
        channels.append(channel)
    # Spain-first is presentation ordering only; all provider-confirmed channels
    # remain available and no location-specific availability is inferred.
    channels.sort(
        key=lambda item: (
            0 if item["country"].casefold() in {"spain", "españa"} else 1,
            item["country"].casefold(),
            item["channel"].casefold(),
        )
    )
    return channels


def _provider_key(env: Mapping[str, str]) -> str:
    return str(env.get("THESPORTSDB_API_KEY") or env.get("THESPORTSDB_KEY") or "").strip()


def _fetch_event_tv(event_id: str, key: str, timeout: float = 6.0) -> Any:
    if not str(event_id).isdigit():
        raise ValueError("invalid_event_id")
    request = urllib.request.Request(
        f"{V2_BASE}/lookup/event_tv/{event_id}",
        headers={
            "X-API-KEY": key,
            "Accept": "application/json",
            "User-Agent": "NeMeSiS-SHARK-PRO/1.0",
        },
        method="GET",
    )
    try:
        from engines.cron_request_budget import request_timeout
        with urllib.request.urlopen(request, timeout=request_timeout(timeout)) as response:
            body = response.read(512_000)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError("SPORTSDB_AUTH_ERROR") from None
        if exc.code == 429:
            raise RuntimeError("SPORTSDB_RATE_LIMIT") from None
        raise RuntimeError(f"SPORTSDB_HTTP_{int(exc.code)}") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("SPORTSDB_NETWORK_ERROR") from None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("SPORTSDB_INVALID_JSON") from None


def _latest_snapshot(conn: sqlite3.Connection, match_id: str) -> tuple[dict[str, Any], str]:
    row = conn.execute(
        """SELECT payload,captured_at FROM sports_history_details
           WHERE match_id=? AND kind=? AND source=? AND external_id=?
           ORDER BY captured_at DESC LIMIT 1""",
        (match_id, DETAIL_KIND, SOURCE, DETAIL_EXTERNAL_ID),
    ).fetchone()
    if not row:
        return {}, ""
    try:
        payload = json.loads(row[0] or "{}")
    except json.JSONDecodeError:
        payload = {}
    return (payload if isinstance(payload, dict) else {}, str(row[1] or ""))


def _fresh(captured_at: str, now: datetime, ttl_hours: int) -> bool:
    captured = _parse_instant(captured_at)
    return bool(captured and timedelta(0) <= now - captured < timedelta(hours=max(1, ttl_hours)))


def _candidates(
    conn: sqlite3.Connection,
    *,
    now: datetime,
    horizon_hours: int,
    limit: int,
) -> list[dict[str, str]]:
    rows = conn.execute(
        """SELECT DISTINCT m.id,m.kickoff,m.status,i.external_id
           FROM sports_history_matches m
           JOIN sports_history_ids i
             ON i.kind='match' AND i.source='thesportsdb' AND i.canonical_id=m.id
           WHERE COALESCE(i.external_id,'')<>''
             AND julianday(m.kickoff) BETWEEN julianday(?) AND julianday(?)
           ORDER BY m.kickoff ASC,m.id ASC
           LIMIT 250""",
        ((now - timedelta(hours=3)).isoformat(), (now + timedelta(hours=max(6, horizon_hours))).isoformat()),
    ).fetchall()
    lower = now - timedelta(hours=3)
    upper = now + timedelta(hours=max(6, horizon_hours))
    result = []
    for match_id, kickoff, status, event_id in rows:
        instant = _parse_instant(kickoff)
        if not instant or instant < lower or instant > upper:
            continue
        if str(status or "").strip().lower() in {
            "ft", "finished", "final", "finalizado", "match finished",
            "archived", "aet", "pen", "cancelled", "canceled",
        }:
            continue
        event_id = str(event_id or "").strip()
        if not event_id.isdigit():
            continue
        result.append(
            {
                "match_id": str(match_id),
                "event_id": event_id,
                "kickoff": str(kickoff or ""),
            }
        )
        if len(result) >= max(1, limit):
            break
    return result


def sync_upcoming_broadcasts(
    db_path: str,
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    max_matches: int = DEFAULT_LIMIT,
    horizon_hours: int = DEFAULT_HORIZON_HOURS,
    ttl_hours: int = DEFAULT_TTL_HOURS,
    fetcher: Callable[[str, str], Any] | None = None,
) -> dict[str, Any]:
    """Refresh bounded upcoming TV listings using exact SportsDB event IDs only."""
    env = os.environ if env is None else env
    key = _provider_key(env)
    observed = (now or _utc_now()).astimezone(timezone.utc)
    max_matches = max(1, min(12, int(max_matches or DEFAULT_LIMIT)))
    if not key:
        return {
            "ok": False,
            "reason": "SPORTSDB_KEY_MISSING",
            "source": SOURCE,
            "external_calls": 0,
            "processed": 0,
            "updated": 0,
            "cached": 0,
        }
    fetcher = fetcher or _fetch_event_tv
    processed = updated = cached = calls = 0
    errors: list[dict[str, str]] = []
    with closing(sqlite3.connect(db_path, timeout=8)) as conn:
        ensure_schema(conn)
        conn.commit()
        candidates = _candidates(
            conn,
            now=observed,
            horizon_hours=horizon_hours,
            limit=max_matches,
        )
        from engines.cron_request_budget import CronRequestBudget, exhausted
        deferred = False
        with CronRequestBudget(seconds=12):
            for candidate in candidates:
                if exhausted():
                    deferred = True
                    break
                snapshot, captured_at = _latest_snapshot(conn, candidate["match_id"])
                if _fresh(str(snapshot.get('observed_at') or ''), observed, ttl_hours):
                    cached += 1
                    processed += 1
                    continue
                try:
                    calls += 1
                    payload = fetcher(candidate["event_id"], key)
                    channels = normalize_event_tv(payload, candidate["event_id"])
                    snapshot = {
                        "available": bool(channels),
                        "event_id": candidate["event_id"],
                        "channels": channels,
                        "country_priority": "Spain",
                        "source": SOURCE,
                        "observed_at": observed.isoformat(),
                        "kickoff": candidate["kickoff"],
                        "no_invented_availability": True,
                    }
                    persist_detail(
                        conn,
                        candidate["match_id"],
                        DETAIL_KIND,
                        SOURCE,
                        DETAIL_EXTERNAL_ID,
                        snapshot,
                    )
                    conn.commit()
                    updated += 1
                    processed += 1
                except (RuntimeError, ValueError, sqlite3.Error) as exc:
                    errors.append(
                        {
                            "event_id": candidate["event_id"],
                            "code": str(exc) if str(exc) in {
                                'SPORTSDB_AUTH_ERROR', 'SPORTSDB_RATE_LIMIT',
                                'SPORTSDB_NETWORK_ERROR', 'SPORTSDB_INVALID_JSON',
                                'invalid_event_id', 'TIME_BUDGET',
                            } or (str(exc).startswith('SPORTSDB_HTTP_') and str(exc)[16:].isdigit()) else 'SPORTSDB_BROADCAST_ERROR',
                        }
                    )
        return {
            "ok": not errors,
            "source": SOURCE,
            "sync_type": "event_tv",
            "result": "PARTIAL" if deferred or errors else "COMPLETE",
            "controlled_deferral": "TIME_BUDGET" if deferred else "",
            "processed": processed,
            "updated": updated,
            "cached": cached,
            "external_calls": calls,
            "candidates": len(candidates),
            "errors": errors[:6],
            "observed_at": observed.isoformat(),
            "horizon_hours": horizon_hours,
            "ttl_hours": ttl_hours,
            "no_render_calls": True,
            "exact_event_identity_only": True,
        }
