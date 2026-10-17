"""Bounded statistics ingestion, independent of the slow multi-capability sample.

Only the sports writer calls refresh_api_football_statistics_if_due. Page reads
use statistics_refresh_state_for_match, which never initializes storage or HTTP.
Provider receipts do not change the fixture's lifecycle or provider clocks.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import uuid

from engines import api_usage_guard_engine as usage_guard
from engines.api_football_live_tracker_engine import (
    _api_get,
    _provider_failure_labels,
    _safe_provider_error_shape,
)
from engines.cron_request_budget import CronTimeBudget, exhausted, sqlite_busy_timeout
from engines.match_record_archive import record_observation, utc_stamp
from engines.provider_access_evidence import FAILURE_PRIORITY, safe_failure_categories
from engines.v935_launch_trust_engine import (
    _FINISHED_STATUS_KEYS, _HALFTIME_STATUS_KEYS, _LIVE_STATUS_KEYS,
)

STATE_TABLE = "api_football_statistics_refresh_state"
PROVIDER = "api_football"
LIVE = frozenset(value.upper() for value in _LIVE_STATUS_KEYS | _HALFTIME_STATUS_KEYS) | {"DIRECTO"}
FINISHED = frozenset(value.upper() for value in _FINISHED_STATUS_KEYS)
SOURCES = frozenset({"api_football", "api_football_live", "api_sports", "api_sports_api_football"})
GLOBAL_FAILURES = frozenset({
    "AUTH_OR_ACCESS", "ACCESS_RESTRICTED", "ACCOUNT_SUSPENDED", "RATE_OR_QUOTA",
    "FREE_PLAN_RESTRICTED", "ENDPOINT_RESTRICTED", "SUBSCRIPTION_RESTRICTED",
})
_ID = re.compile(r"[0-9]{1,24}\Z")
_NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)%?\Z")


def _now():
    return datetime.now(timezone.utc)


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _date(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def _flag(env, name, default=True):
    return str(env.get(name, str(default))).strip().lower() in {"true", "1", "yes", "on", "si", "sí"}


def _integer(env, suffix, default, low, high):
    try:
        value = int(env.get("API_FOOTBALL_STATISTICS_" + suffix, default))
    except (ValueError, TypeError, OverflowError):
        value = default
    return max(low, min(high, value))


def _settings(env, limit):
    transport = str(env.get("API_FOOTBALL_STATISTICS_TRANSPORT", "batch")).lower().strip()
    cap = _integer(env, "BATCH_SIZE", 20, 0, 20)
    if transport == "individual":
        cap = min(cap, _integer(env, "INDIVIDUAL_LIMIT", 2, 0, 4))
    if limit is not None:
        cap = min(cap, max(0, int(limit)))
    return {
        "transport": transport, "limit": cap,
        "live_ttl": _integer(env, "LIVE_TTL_SECONDS", 300, 60, 3600),
        "final_ttl": _integer(env, "FINAL_TTL_SECONDS", 21600, 3600, 86400),
        "empty_ttl": _integer(env, "EMPTY_TTL_SECONDS", 1800, 300, 21600),
        "failure_ttl": _integer(env, "FAILURE_BACKOFF_SECONDS", 21600, 300, 86400),
    }


def _connect(db_path):
    conn = sqlite3.connect(db_path, timeout=sqlite_busy_timeout(500) / 1000)
    conn.row_factory = sqlite3.Row
    return conn


def _exists(conn, table):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def _ensure_schema(conn):
    usage_guard.ensure_api_usage_guard_schema(conn)
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {STATE_TABLE}(
        fixture_id TEXT PRIMARY KEY, status TEXT NOT NULL, phase TEXT,
        last_attempt_at TEXT, next_due_at TEXT, last_success_at TEXT,
        provider_observed_at TEXT, failure_category TEXT,
        lease_token TEXT, lease_until TEXT)""")
    # Same caches consumed by the existing tracker and Match Center. This writer
    # does not initialize unrelated enrichment tables or alter the matches table.
    conn.execute("""CREATE TABLE IF NOT EXISTS api_football_live_stats(
        id TEXT PRIMARY KEY, fixture_id TEXT, team_id TEXT, team_name TEXT,
        stat_name TEXT, stat_value TEXT, numeric_value REAL DEFAULT 0,
        payload_json TEXT, captured_at TEXT, UNIQUE(fixture_id,team_id,stat_name))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS api_football_match_stats_history(
        id TEXT PRIMARY KEY, fixture_id TEXT, team_id TEXT, team_name TEXT,
        stat_name TEXT, stat_value TEXT, numeric_value REAL,
        payload_json TEXT, captured_at TEXT, UNIQUE(fixture_id,team_id,stat_name,captured_at))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_af_statistics_history_fixture_time ON api_football_match_stats_history(fixture_id,captured_at)")


def _identity(match):
    match = dict(match or {})
    source = str(match.get("source") or match.get("provider") or "").lower().replace("-", "_")
    internal = str(match.get("id") or match.get("match_id") or "")
    if internal.startswith("af-") and _ID.fullmatch(internal[3:]) and (not source or source in SOURCES):
        return internal[3:]
    if source in SOURCES:
        value = str(match.get("fixture_id") or match.get("external_id") or "")
        if _ID.fullmatch(value):
            return value
    return ""


def _candidates(conn, now):
    """Use proven provider identities, newest evidence first, with bounded reads."""
    found, sources, identities = {}, [], set()
    for table, identity, clock in (
        ("api_football_live_snapshots", "fixture_id", "last_synced_at"),
        ("api_football_fixture_index", "fixture_id", "last_seen_at"),
        ("matches", "external_id", "updated_at"),
    ):
        if not _exists(conn, table):
            continue
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if identity not in columns:
            continue
        selected = [key for key in (identity, "status_short", "status", "kickoff_iso", "match_date", "source", clock,
                                    "home_team_id", "away_team_id") if key in columns]
        order = clock if clock in columns else "kickoff_iso" if "kickoff_iso" in columns else identity
        if table == "matches" and "source" not in columns:
            continue
        predicate = ("lower(replace(COALESCE(source,''),'-','_')) IN "
                     "('api_football','api_football_live','api_sports','api_sports_api_football') AND ") if table == "matches" else ""
        status_columns = [f"NULLIF({key},'')" for key in ("status_short", "status") if key in columns]
        date_columns = [f"NULLIF({key},'')" for key in ("kickoff_iso", "match_date") if key in columns]
        if not status_columns or not date_columns:
            continue
        status_expr = "upper(replace(COALESCE(" + ",".join(status_columns + ["''"]) + "),'_', ' '))"
        date_expr = "substr(COALESCE(" + ",".join(date_columns + ["''"]) + "),1,10)"
        statuses = sorted(LIVE | FINISHED)
        placeholders = ",".join("?" for _ in statuses)
        # Filter before LIMIT: a large future calendar must not hide live games.
        records = conn.execute(
            f"SELECT {identity} FROM {table} WHERE {predicate}{status_expr} IN ({placeholders}) "
            f"AND {date_expr} BETWEEN ? AND ? ORDER BY {order} DESC LIMIT 600",
            # Text dates may carry Madrid/other offsets. Keep the coarse SQL
            # window wide; the aware UTC age check below enforces 12h/48h exactly.
            (*statuses, (now - timedelta(days=3)).date().isoformat(), (now + timedelta(days=1)).date().isoformat()),
        ).fetchall()
        identities.update(str(row[0]) for row in records if _ID.fullmatch(str(row[0] or "")))
        sources.append((table, identity, clock, ",".join(dict.fromkeys(selected)), predicate, order))
    identifiers = sorted(identities)
    for table, identity, clock, selected, predicate, order in sources:
        for offset in range(0, len(identifiers), 400):
            if exhausted():
                raise CronTimeBudget()
            subset = identifiers[offset:offset + 400]
            placeholders = ",".join("?" for _ in subset)
            # Re-read these identities without the status filter. A newer NS,
            # cancelled or postponed observation must supersede an older live row.
            records = conn.execute(
                f"SELECT {selected} FROM {table} WHERE {predicate}{identity} IN ({placeholders}) "
                f"ORDER BY {order} DESC LIMIT 1200", subset,
            ).fetchall()
            for row in records:
                item = dict(row)
                fid = str(item.get(identity) or "")
                status = str(item.get("status_short") or item.get("status") or "").strip().upper().replace("_", " ")
                observed = _date(item.get(clock)) or datetime.min.replace(tzinfo=timezone.utc)
                if fid in found and found[fid]["observed"] >= observed:
                    continue
                kickoff = _date(item.get("kickoff_iso"))
                if kickoff is not None:
                    age = (now - kickoff).total_seconds()
                    recent = 0 <= age <= (12 * 3600 if status in LIVE else 48 * 3600)
                else:
                    day = str(item.get("match_date") or "")[:10]
                    recent = (now - timedelta(days=2)).date().isoformat() <= day <= now.date().isoformat()
                found[fid] = {"fixture_id": fid, "phase": "live" if status in LIVE else "final",
                              "team_ids": {str(item[key]) for key in ("home_team_id", "away_team_id") if item.get(key)},
                              "eligible": recent and status in LIVE | FINISHED, "observed": observed}
    return [item for item in found.values() if item["eligible"]]


def _claim(conn, candidates, cfg, env, now):
    """Claim due fixtures and reserve the shared ledger in one short transaction."""
    conn.execute("BEGIN IMMEDIATE")
    global_row = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id='*'").fetchone()
    if global_row and (_date(global_row["next_due_at"]) or now) > now:
        conn.rollback()
        return [], None, dict(global_row), 0
    due = []
    for item in candidates:
        row = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id=?", (item["fixture_id"],)).fetchone()
        state = dict(row) if row else {}
        if (_date(state.get("lease_until")) or now) > now:
            continue
        phase_changed = state.get("phase") == "live" and item["phase"] == "final"
        if (_date(state.get("next_due_at")) or now) > now and not phase_changed:
            continue
        due.append({**item, "last_attempt_at": state.get("last_attempt_at") or ""})
    due.sort(key=lambda row: (row["last_attempt_at"], row["fixture_id"]))
    live = [item for item in due if item["phase"] == "live"]
    final = [item for item in due if item["phase"] == "final"]
    # Give live games most slots without starving recent finals behind every tick.
    live_slots = cfg["limit"] if not final else max(1, cfg["limit"] * 3 // 4)
    selected_live = live[:live_slots]
    selected = list(selected_live)
    selected += final[:max(0, cfg["limit"] - len(selected))]
    selected += live[len(selected_live):][:max(0, cfg["limit"] - len(selected))]
    selected = selected[:cfg["limit"]]
    if not selected:
        conn.rollback()
        return [], None, None, len(due)
    calls = 1 if cfg["transport"] == "batch" else len(selected)
    today = now.astimezone(usage_guard.TZ).date().isoformat()
    budget = usage_guard._budget("API_FOOTBALL_DAILY_CALL_BUDGET", 120, env)
    used = usage_guard._recorded_estimate(conn, PROVIDER, today)
    remaining = max(0, budget - used)
    if cfg["transport"] == "individual" and remaining:
        selected = selected[:remaining]
        calls = len(selected)
    if calls > remaining:
        conn.rollback()
        return [], None, {"status": "DAILY_BUDGET", "failure_category": "", "next_due_at": ""}, len(due)
    reservation = conn.execute("""INSERT INTO api_usage_guard
        (provider,window_key,job_key,estimated_calls,actual_calls,status,details_json,created_at)
        VALUES (?,?,?,?,0,'ALLOWED',?,?)""", (PROVIDER, today, "api_football_statistics_" + cfg["transport"],
        calls, json.dumps({"fixture_count": len(selected), "usage_scope": "LOCAL_GUARD_RESERVATIONS_NOT_PROVIDER_QUOTA"}), _stamp(now))).lastrowid
    token = uuid.uuid4().hex
    for item in selected:
        item["lease_token"] = token
        conn.execute(f"""INSERT INTO {STATE_TABLE}
            (fixture_id,status,phase,last_attempt_at,lease_token,lease_until)
            VALUES (?,'FETCHING',?,?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET
            status='FETCHING',phase=excluded.phase,last_attempt_at=excluded.last_attempt_at,
            lease_token=excluded.lease_token,lease_until=excluded.lease_until""",
            (item["fixture_id"], item["phase"], _stamp(now), token, _stamp(now + timedelta(seconds=60))))
    conn.commit()
    return selected, reservation, None, len(due)


def _stat_value(value):
    if value is None:
        return None
    if type(value) in (int, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str) and _NUMBER.fullmatch(value.strip()):
        return value.strip()
    return None


def _valid_statistics(payload):
    if not isinstance(payload, list) or len(payload) > 2:
        return False
    teams = set()
    for block in payload:
        if not isinstance(block, dict) or not isinstance(block.get("team"), dict):
            return False
        team_id = str(block["team"].get("id") or "")
        if not _ID.fullmatch(team_id) or team_id in teams:
            return False
        teams.add(team_id)
        stats = block.get("statistics")
        if not isinstance(stats, list) or len(stats) > 100:
            return False
        if any(not isinstance(stat, dict) or not isinstance(stat.get("type"), str) or not stat["type"].strip()
               or (stat.get("value") is not None and _stat_value(stat.get("value")) is None) for stat in stats):
            return False
    return True


def _persist(conn, fid, payload, received):
    """One append-only receipt and both current consumers, in the caller's commit."""
    record_observation(conn, fid, "statistics", payload, received_at=received)
    usable = any(_stat_value(stat.get("value")) is not None for block in payload for stat in block["statistics"])
    if not usable:
        return 0  # Preserve the previous usable snapshot on an empty/null receipt.
    captured = utc_stamp(received)
    # A new usable receipt replaces the current set atomically. Omitted metrics
    # or teams must not survive as though they belonged to this fresh snapshot.
    conn.execute("DELETE FROM api_football_live_stats WHERE fixture_id=?", (fid,))
    count = 0
    for block in payload:
        team = block["team"]
        for stat in block["statistics"]:
            name, value = stat["type"].strip(), _stat_value(stat.get("value"))
            text_value = "" if value is None else str(value)
            numeric = None if value is None else float(str(value).rstrip("%"))
            identity = (fid, str(team["id"]), str(team.get("name") or ""), name, text_value, numeric)
            row_id = hashlib.sha256(json.dumps([fid, team["id"], name]).encode()).hexdigest()
            conn.execute("""INSERT INTO api_football_live_stats
                (id,fixture_id,team_id,team_name,stat_name,stat_value,numeric_value,payload_json,captured_at)
                VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(fixture_id,team_id,stat_name) DO UPDATE SET
                team_name=excluded.team_name,stat_value=excluded.stat_value,numeric_value=excluded.numeric_value,
                payload_json=excluded.payload_json,captured_at=excluded.captured_at""",
                (row_id, *identity, json.dumps(stat, ensure_ascii=False), captured))
            history_id = hashlib.sha256((row_id + captured).encode()).hexdigest()
            conn.execute("""INSERT OR IGNORE INTO api_football_match_stats_history
                (id,fixture_id,team_id,team_name,stat_name,stat_value,numeric_value,payload_json,captured_at)
                VALUES (?,?,?,?,?,?,?,?,?)""", (history_id, *identity, json.dumps(block, ensure_ascii=False), captured))
            count += 1
    return count


def _failure(payload):
    categories = _provider_failure_labels(payload)
    if _safe_provider_error_shape(payload) == "ERROR_KEY_ACCESS" and not categories:
        categories = ["ACCESS_RESTRICTED"]
    elif _safe_provider_error_shape(payload) == "ERROR_KEY_ACCESS" and categories == ["PROVIDER_RESPONSE"]:
        categories = ["ACCESS_RESTRICTED"]
    return categories[0] if categories else "PROVIDER_RESPONSE"


def _finish(conn, item, status, cfg, now, *, failure="", count=0, observed=True):
    ttl = (cfg["live_ttl"] if item["phase"] == "live" else cfg["final_ttl"]) if status == "AVAILABLE" else cfg["empty_ttl"]
    if failure:
        ttl = 900 if failure == "RATE_OR_QUOTA" else 300 if failure in {"NETWORK_OR_TIMEOUT", "PROVIDER_RESPONSE"} else cfg["failure_ttl"]
    if status == "TIME_BUDGET":
        ttl = 30
    due = _stamp(now + timedelta(seconds=ttl))
    conn.execute(f"""UPDATE {STATE_TABLE} SET status=?,next_due_at=?,
        last_success_at=CASE WHEN ?='AVAILABLE' THEN ? ELSE last_success_at END,
        provider_observed_at=CASE WHEN ? THEN ? ELSE provider_observed_at END,
        failure_category=?,lease_token='',lease_until='' WHERE fixture_id=? AND lease_token=?""",
        (status, due, status, _stamp(now), int(observed), _stamp(now), failure, item["fixture_id"], item["lease_token"]))
    if failure in GLOBAL_FAILURES:
        conn.execute(f"""INSERT INTO {STATE_TABLE}
            (fixture_id,status,last_attempt_at,next_due_at,provider_observed_at,failure_category)
            VALUES ('*',?,?,?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET
            status=excluded.status,last_attempt_at=excluded.last_attempt_at,next_due_at=excluded.next_due_at,
            provider_observed_at=excluded.provider_observed_at,failure_category=excluded.failure_category""",
            (status, _stamp(now), due, _stamp(now), failure))
    return {"fixture_id": item["fixture_id"], "status": status, "stats_inserted": count,
            "failure_category": failure, "next_due_at": due}


def refresh_api_football_statistics_if_due(db_path, *, limit=None, env=None):
    """Refresh one rotating batch. No forced bypass of claims, TTL or daily budget."""
    env = os.environ if env is None else env
    cfg = _settings(env, limit)
    configured = any(bool(str(env.get(key) or "").strip()) for key in (
        "API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY", "API_SPORTS_KEY", "APISPORTS_KEY"))
    enabled = configured and all(_flag(env, name) for name in (
        "ENABLE_API_FOOTBALL_PROVIDER", "ENABLE_API_FOOTBALL_STATISTICS_SYNC", "ENABLE_API_SPORTS_NETWORK_CALLS"))
    result = {"ok": True, "status": "NO_DUE_STATISTICS", "configured": configured, "enabled": enabled,
              "transport": cfg["transport"], "external_calls": 0, "selected_fixture_ids": [],
              "fixtures_count": 0, "refreshed_fixtures": 0, "stats_inserted": 0,
              "no_data_count": 0, "failed_count": 0, "eligible_count": 0, "due_count": 0,
              "skipped": True, "data_contributed": False, "items": [], "failure_categories": [],
              "provider_observation_current": False, "provider_observed_at": "", "errors": []}
    if not configured or not enabled or not cfg["limit"]:
        result.update(status="NOT_CONFIGURED" if not configured else "DISABLED", disabled=not enabled or not cfg["limit"])
        return result
    local_safe = _flag(env, "NEMESIS_LOCAL_SAFE_MODE", False)
    local_offline = (str(env.get("NEMESIS_LOCAL_MODE", "OFFLINE_SAFE")).upper() != "INTEGRATION_TEST"
                     or _flag(env, "NEMESIS_OFFLINE_MODE", True)
                     or not _flag(env, "NEMESIS_LOCAL_EXTERNAL_AUTHORIZED", False))
    if (local_safe and local_offline) or _flag(env, "NEMESIS_OFFLINE_MODE", False):
        return {**result, "status": "OFFLINE_SAFE", "enabled": False}
    if cfg["transport"] not in {"batch", "individual"}:
        return {**result, "ok": False, "status": "INVALID_CONFIGURATION", "errors": ["INVALID_STATISTICS_TRANSPORT"]}
    if exhausted():
        return {**result, "status": "TIME_BUDGET"}
    try:
        with closing(_connect(db_path)) as conn:
            candidates = _candidates(conn, _now())
            result["eligible_count"] = len(candidates)
            if not candidates:
                return {**result, "status": "SKIPPED_NO_API_FOOTBALL_FIXTURE"}
            with conn:
                _ensure_schema(conn)
            selected, reservation, blocked, due_count = _claim(conn, candidates, cfg, env, _now())
            result["due_count"] = due_count
            if blocked:
                labels = safe_failure_categories(blocked.get("failure_category"))
                failure = labels[0] if labels else ""
                return {**result, "ok": not bool(failure), "status": "PROVIDER_FAILURE_BACKOFF_" + failure if failure else "DAILY_BUDGET" if blocked.get("status") == "DAILY_BUDGET" else "SOURCE_COOLDOWN",
                        "failure_category": failure, "failure_categories": [failure] if failure else [],
                        "provider_failure_backoff": bool(failure), "next_due_at": blocked.get("next_due_at"),
                        "provider_observed_at": blocked.get("provider_observed_at") or ""}
            if not selected:
                return result
            result.update(skipped=False, selected_fixture_ids=[item["fixture_id"] for item in selected])
            groups = [selected] if cfg["transport"] == "batch" else [[item] for item in selected]
            stop = False
            for group in groups:
                if exhausted() or stop:
                    with conn:
                        for item in group:
                            result["items"].append(_finish(conn, item, "TIME_BUDGET" if not stop else "DEFERRED_PROVIDER_FAILURE", cfg, _now(), observed=False))
                    continue
                path = "fixtures" if cfg["transport"] == "batch" else "fixtures/statistics"
                params = {"ids": "-".join(item["fixture_id"] for item in group)} if cfg["transport"] == "batch" else {"fixture": group[0]["fixture_id"]}
                try:
                    # Claim and reservation have committed: no write lock spans HTTP.
                    payload = _api_get(path, params, timeout=4)
                    if (isinstance(payload, dict) and type(payload.get("external_calls")) is int
                            and payload["external_calls"] == 0):
                        with conn:
                            for item in group:
                                result["items"].append(_finish(conn, item, "OFFLINE_SAFE", cfg, _now(), observed=False))
                        continue
                    result["external_calls"] += 1
                except CronTimeBudget as exc:
                    result["external_calls"] += exc.external_calls
                    with conn:
                        for item in group:
                            result["items"].append(_finish(conn, item, "TIME_BUDGET", cfg, _now(), observed=False))
                    continue
                except Exception:
                    result["external_calls"] += 1
                    payload = {"ok": False, "error": "PROVIDER_RESPONSE"}
                now = _now()
                result.update(provider_observation_current=True, provider_observed_at=_stamp(now))
                if not isinstance(payload, dict) or (payload.get("ok") and not isinstance(payload.get("response"), list)):
                    payload = {"ok": False, "errors": {"response": "INVALID_RESPONSE_SHAPE"}}
                if not payload.get("ok"):
                    failure = _failure(payload)
                    with conn:
                        for item in group:
                            result["items"].append(_finish(conn, item, "PROVIDER_FAILURE_" + failure, cfg, now, failure=failure))
                    stop = failure in GLOBAL_FAILURES
                    continue
                expected = {item["fixture_id"] for item in group}
                by_id, duplicate_ids = {}, set()
                if cfg["transport"] == "batch":
                    for received in payload["response"]:
                        if not isinstance(received, dict) or not isinstance(received.get("fixture"), dict):
                            continue
                        fid = str(received["fixture"].get("id") or "")
                        if fid not in expected:
                            continue
                        if fid in by_id:
                            duplicate_ids.add(fid)
                        by_id[fid] = received.get("statistics")
                else:
                    by_id[group[0]["fixture_id"]] = payload["response"]
                with conn:
                    conn.execute("BEGIN IMMEDIATE")
                    for item in group:
                        fid = item["fixture_id"]
                        owned = conn.execute(f"SELECT 1 FROM {STATE_TABLE} WHERE fixture_id=? AND lease_token=?",
                                             (fid, item["lease_token"])).fetchone()
                        if not owned:
                            continue
                        stats = by_id.get(fid)
                        if fid not in by_id or stats is None:
                            result["items"].append(_finish(conn, item, "NO_DATA", cfg, now))
                        elif (fid in duplicate_ids or not _valid_statistics(stats)
                              or (item["team_ids"] and any(str(block["team"]["id"]) not in item["team_ids"] for block in stats))):
                            result["items"].append(_finish(conn, item, "PROVIDER_FAILURE_INVALID_RESPONSE", cfg, now, failure="PROVIDER_RESPONSE"))
                        else:
                            count = _persist(conn, fid, stats, now)
                            result["items"].append(_finish(conn, item, "AVAILABLE" if count else "NO_DATA", cfg, now, count=count))
            with conn:
                conn.execute("UPDATE api_usage_guard SET actual_calls=? WHERE id=?", (result["external_calls"], reservation))
    except CronTimeBudget:
        result["status"] = "TIME_BUDGET"
    except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
        result.update(ok=False, status="LOCAL_STORAGE_UNAVAILABLE", errors=["STATISTICS_LOCAL_STORAGE_UNAVAILABLE"])
    items = result["items"]
    result["refreshed_fixtures"] = sum(item["status"] == "AVAILABLE" for item in items)
    result["fixtures_count"] = result["refreshed_fixtures"]
    result["stats_inserted"] = sum(item["stats_inserted"] for item in items)
    result["no_data_count"] = sum(item["status"] == "NO_DATA" for item in items)
    result["failed_count"] = sum(item["status"].startswith("PROVIDER_FAILURE_") for item in items)
    result["failure_categories"] = sorted({item["failure_category"] for item in items if item["failure_category"]})
    result["data_contributed"] = result["refreshed_fixtures"] > 0
    if result["failed_count"]:
        result.update(ok=False, status="PARTIAL" if result["data_contributed"] else "PROVIDER_FAILURE",
                      failure_category=result["failure_categories"][0], errors=result["failure_categories"])
    elif result["ok"] and items:
        result["status"] = "TIME_BUDGET" if any(item["status"] == "TIME_BUDGET" for item in items) else "OFFLINE_SAFE" if any(item["status"] == "OFFLINE_SAFE" for item in items) else "OK" if result["data_contributed"] else "NO_DATA"
    return result


def statistics_refresh_state_for_match(db_path, match):
    """Read only stored collection evidence. Never equate it with a current probe."""
    fid = _identity(match)
    result = {"status": "PENDING", "fixture_id": fid or None, "last_attempt_at": "", "last_success_at": "",
              "next_due_at": "", "failure_category": "", "provider_observed_at": "",
              "provider_observation_current": False, "read_only": True, "external_calls": 0}
    try:
        path = Path(db_path).expanduser().resolve()
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=.1)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            if not fid:
                internal_id = str((match or {}).get("id") or (match or {}).get("match_id") or "").strip()
                if internal_id and _exists(conn, "api_football_fixture_index"):
                    mapped = conn.execute("SELECT fixture_id FROM api_football_fixture_index WHERE internal_match_id=? LIMIT 2", (internal_id,)).fetchall()
                    if len(mapped) == 1 and _ID.fullmatch(str(mapped[0][0] or "")):
                        fid = str(mapped[0][0])
                        result["fixture_id"] = fid
                if not fid:
                    return {**result, "status": "IDENTITY_UNAVAILABLE"}
            if not _exists(conn, STATE_TABLE):
                return result
            row = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id=?", (fid,)).fetchone()
            fixture_success = _date(row["last_success_at"]) if row else None
            now = _now()
            blocked = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id='*'").fetchone()
            if blocked and (_date(blocked["next_due_at"]) or now) > now and (not row or row["status"] != "AVAILABLE"):
                row = blocked
            if row:
                for field in ("last_attempt_at", "last_success_at", "next_due_at", "provider_observed_at"):
                    parsed = _date(row[field])
                    result[field] = _stamp(parsed) if parsed else ""
                known_states = {"PENDING", "AVAILABLE", "NO_DATA", "FETCHING", "STALE", "TIME_BUDGET", "OFFLINE_SAFE", "DEFERRED_PROVIDER_FAILURE",
                                "PROVIDER_FAILURE_INVALID_RESPONSE"} | {"PROVIDER_FAILURE_" + category for category in FAILURE_PRIORITY}
                result["status"] = row["status"] if row["status"] in known_states else "UNKNOWN"
                labels = safe_failure_categories(row["failure_category"])
                result["failure_category"] = labels[0] if labels else ""
                # Global access evidence does not erase the fixture's last good
                # receipt or move its statistics onto the scoreboard's clock.
                result["last_success_at"] = _stamp(fixture_success) if fixture_success else ""
                if result["status"] == "AVAILABLE" and (_date(result["next_due_at"]) or now) <= now:
                    result["status"] = "STALE"
                if result["status"] == "FETCHING" and (_date(row["lease_until"]) or now) <= now:
                    result["status"] = "PENDING"
                result["has_previous_data"] = bool(result["last_success_at"])
    except (sqlite3.Error, OSError, ValueError, TypeError):
        result["status"] = "READ_UNAVAILABLE"
    return result
