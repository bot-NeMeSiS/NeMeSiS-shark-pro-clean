"""Bounded API-Football pre-match 1X2 odds ingestion.

Uses existing API-Football fixture identities and the canonical ``odds_snapshots``
store. It never creates fixtures, invents prices, calls from page renders, or
claims to know the provider's remaining quota. A local UTC-day feature cap and
the shared application guard reserve calls before the request.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
import re
import sqlite3
import unicodedata
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

from engines import api_usage_guard_engine as usage_guard
from engines.api_football_live_tracker_engine import (
    _api_get,
    _provider_failure_labels,
    _safe_provider_error_shape,
)
from engines.cron_request_budget import CronTimeBudget, exhausted, sqlite_busy_timeout
from engines.provider_access_evidence import safe_failure_categories

STATE_TABLE = "api_football_odds_refresh_state"
DAILY_TABLE = "api_football_odds_daily_usage"
PROVIDER = "api_football"
UTC = timezone.utc
MADRID = ZoneInfo("Europe/Madrid")
SOURCE_ALIASES = frozenset({"api_football", "api_football_live", "api_sports", "api_sports_api_football"})
GLOBAL_FAILURES = frozenset({
    "AUTH_OR_ACCESS", "ACCESS_RESTRICTED", "ACCOUNT_SUSPENDED", "RATE_OR_QUOTA",
    "FREE_PLAN_RESTRICTED", "ENDPOINT_RESTRICTED", "SUBSCRIPTION_RESTRICTED",
})
FIXTURE_ID = re.compile(r"[0-9]{1,24}\Z")
MATCH_WINNER_MARKETS = frozenset({"match winner", "fulltime result", "full time result", "1x2"})


def _now():
    return datetime.now(UTC)


def _stamp(value):
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_stamp(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(UTC)
    except (ValueError, TypeError, OverflowError):
        return None


def _flag(env, name, default):
    return str(env.get(name, str(default))).strip().lower() in {"true", "1", "yes", "on", "si", "sí"}


def _int_setting(env, name, default, low, high):
    try:
        parsed = int(str(env.get(name, default)).strip())
    except (ValueError, TypeError, OverflowError):
        parsed = default
    return max(low, min(high, parsed))


def _settings(env, limit):
    configured_limit = _int_setting(env, "API_FOOTBALL_ODDS_FIXTURES_PER_TICK", 2, 0, 5)
    if limit is not None:
        try:
            configured_limit = min(configured_limit, max(0, int(limit)))
        except (TypeError, ValueError, OverflowError):
            configured_limit = 0
    return {
        "limit": configured_limit,
        "daily_budget": _int_setting(env, "API_FOOTBALL_ODDS_DAILY_CALL_BUDGET", 60, 0, 500),
        "refresh_seconds": _int_setting(env, "API_FOOTBALL_ODDS_REFRESH_SECONDS", 10800, 600, 86400),
        "empty_backoff_seconds": _int_setting(env, "API_FOOTBALL_ODDS_EMPTY_BACKOFF_SECONDS", 10800, 600, 86400),
        "failure_backoff_seconds": _int_setting(env, "API_FOOTBALL_ODDS_FAILURE_BACKOFF_SECONDS", 900, 60, 21600),
        "global_backoff_seconds": _int_setting(env, "API_FOOTBALL_ODDS_GLOBAL_FAILURE_BACKOFF_SECONDS", 21600, 300, 86400),
        "days_ahead": _int_setting(env, "API_FOOTBALL_ODDS_MAX_DAYS_AHEAD", 14, 1, 14),
    }


def _configured(env):
    return any(bool(str(env.get(name) or "").strip()) for name in (
        "API_FOOTBALL_KEY", "API_FOOTBALL_API_KEY", "API_SPORTS_KEY", "APISPORTS_KEY"))


def _enabled(env):
    return _configured(env) and all(_flag(env, name, True) for name in (
        "ENABLE_API_FOOTBALL_PROVIDER", "ENABLE_API_FOOTBALL_ODDS_SYNC", "ENABLE_API_SPORTS_NETWORK_CALLS"))


def _offline_safe(env):
    local_safe = _flag(env, "NEMESIS_LOCAL_SAFE_MODE", False)
    local_offline = (str(env.get("NEMESIS_LOCAL_MODE", "OFFLINE_SAFE")).upper() != "INTEGRATION_TEST"
                     or _flag(env, "NEMESIS_OFFLINE_MODE", True)
                     or not _flag(env, "NEMESIS_LOCAL_EXTERNAL_AUTHORIZED", False))
    return (local_safe and local_offline) or _flag(env, "NEMESIS_OFFLINE_MODE", False)


def _connect(db_path):
    conn = sqlite3.connect(db_path, timeout=sqlite_busy_timeout(500) / 1000)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, table):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def _ensure_schema(conn):
    usage_guard.ensure_api_usage_guard_schema(conn)
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {STATE_TABLE}(
        fixture_id TEXT PRIMARY KEY, status TEXT NOT NULL, last_attempt_at TEXT,
        next_due_at TEXT, last_success_at TEXT, provider_observed_at TEXT,
        failure_category TEXT, lease_token TEXT, lease_until TEXT)""")
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {DAILY_TABLE}(
        day_utc TEXT PRIMARY KEY, estimated_calls INTEGER NOT NULL DEFAULT 0,
        actual_calls INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)""")


def _normalized(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _fixture_clock(row):
    kickoff = _parse_stamp(row.get("kickoff_iso"))
    if kickoff:
        return kickoff
    day = str(row.get("match_date") or "")[:10]
    time = str(row.get("kickoff_time") or row.get("match_time") or "").strip()
    if not day or not time:
        return None
    try:
        local = datetime.fromisoformat(f"{day}T{time[:8]}")
        if local.tzinfo is None:
            local = local.replace(tzinfo=MADRID)
        return local.astimezone(UTC)
    except (ValueError, TypeError, OverflowError):
        return None


def _fixture_id(row):
    external = str(row.get("external_id") or "").strip()
    if FIXTURE_ID.fullmatch(external):
        return external
    internal = str(row.get("id") or "").strip()
    if internal.startswith("af-") and FIXTURE_ID.fullmatch(internal[3:]):
        return internal[3:]
    return ""


def _candidates(conn, now, days_ahead):
    if not _table_exists(conn, "matches"):
        raise sqlite3.OperationalError("matches table unavailable")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
    required = {"id", "source"}
    if not required.issubset(columns) or not ({"external_id", "id"} & columns) or not ({"kickoff_iso", "match_date"} & columns):
        raise sqlite3.OperationalError("fixture identity columns unavailable")
    selected = [name for name in (
        "id", "external_id", "source", "match_date", "kickoff_iso", "kickoff_time", "match_time",
        "status", "home_team", "away_team", "league_name", "competition_name") if name in columns]
    source_clause = "lower(replace(COALESCE(source,''),'-','_')) IN (" + ",".join("?" for _ in SOURCE_ALIASES) + ")"
    date_columns = [name for name in ("kickoff_iso", "match_date") if name in columns]
    order_expr = "COALESCE(" + ",".join(date_columns) + ")"
    upper = now + timedelta(days=days_ahead)
    # Bound the SQL result by a broad calendar window before applying LIMIT.
    # Limiting all historical provider rows first can hide upcoming fixtures
    # once a long-running database has more than 3,000 older API-Football rows.
    date_floor = (now - timedelta(days=1)).date().isoformat()
    date_ceiling = (upper + timedelta(days=1)).date().isoformat()
    date_predicates = []
    date_params = []
    if "kickoff_iso" in columns:
        date_predicates.append("substr(COALESCE(kickoff_iso,''),1,10) BETWEEN ? AND ?")
        date_params.extend((date_floor, date_ceiling))
    if "match_date" in columns:
        date_predicates.append("substr(COALESCE(match_date,''),1,10) BETWEEN ? AND ?")
        date_params.extend((date_floor, date_ceiling))
    date_clause = " AND (" + " OR ".join(date_predicates) + ")" if date_predicates else ""
    sql = (f"SELECT {','.join(selected)} FROM matches WHERE {source_clause}{date_clause} "
           f"ORDER BY {order_expr} LIMIT 3000")
    rows = [dict(row) for row in conn.execute(sql, [*sorted(SOURCE_ALIASES), *date_params])]
    found = {}
    for row in rows:
        fid = _fixture_id(row)
        kickoff = _fixture_clock(row)
        if not fid or not kickoff or kickoff <= now or kickoff > upper:
            continue
        status = _normalized(row.get("status"))
        if status in {"ft", "aet", "pen", "finished", "finalizado", "postponed", "suspended", "cancelled", "canceled", "abandoned"}:
            continue
        item = {**row, "fixture_id": fid, "kickoff_at": kickoff}
        current = found.get(fid)
        if current is None or (not current.get("home_team") and item.get("home_team")):
            found[fid] = item
    return sorted(found.values(), key=lambda item: (item["kickoff_at"], item["fixture_id"]))


def _is_1x2_market(name):
    return _normalized(name) in MATCH_WINNER_MARKETS


def _price(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 1 else None


def _outcome_key(label, home, away):
    value = _normalized(label)
    if value in {"home", "local", "1"} or (home and value == _normalized(home)):
        return "home"
    if value in {"draw", "tie", "empate", "x"}:
        return "draw"
    if value in {"away", "visitor", "visiting", "visitante", "2"} or (away and value == _normalized(away)):
        return "away"
    return ""


def _prices_from_bet(bet, home, away):
    values = bet.get("values") if isinstance(bet, dict) else None
    if not isinstance(values, list) or len(values) > 30:
        return None
    prices = {}
    for item in values:
        if not isinstance(item, dict):
            return None
        key = _outcome_key(item.get("value") or item.get("name"), home, away)
        if not key:
            continue
        odd = _price(item.get("odd"))
        if odd is None or (key in prices and not math.isclose(prices[key], odd, rel_tol=1e-9, abs_tol=1e-9)):
            return None
        prices[key] = odd
    return prices if set(prices) == {"home", "draw", "away"} else None


def _provider_time(event):
    return _parse_stamp(event.get("update") or event.get("updated_at"))


def _market_prices(event, match):
    bets = event.get("bets")
    if not isinstance(bets, list) or len(bets) > 100:
        return None
    markets = [bet for bet in bets if isinstance(bet, dict) and _is_1x2_market(bet.get("name"))]
    complete = []
    for bet in markets:
        prices = _prices_from_bet(bet, match.get("home_team"), match.get("away_team"))
        if prices:
            complete.append((bet, prices))
    if not complete:
        return None
    signatures = {tuple(sorted(prices.items())) for _bet, prices in complete}
    if len(signatures) != 1:
        return None
    return complete[0]


def _failure(payload):
    labels = _provider_failure_labels(payload if isinstance(payload, dict) else {})
    shape = _safe_provider_error_shape(payload if isinstance(payload, dict) else {})
    if shape == "ERROR_KEY_ACCESS" and not labels:
        labels = ["ACCESS_RESTRICTED"]
    elif shape == "ERROR_KEY_ACCESS" and labels == ["PROVIDER_RESPONSE"]:
        labels = ["ACCESS_RESTRICTED"]
    safe = safe_failure_categories(labels)
    return safe[0] if safe else "PROVIDER_RESPONSE"


def _ttl(status, failure, cfg):
    if status == "TIME_BUDGET":
        return 30
    if failure:
        if failure == "NETWORK_OR_TIMEOUT":
            return cfg["failure_backoff_seconds"]
        if failure == "RATE_OR_QUOTA":
            return cfg["global_backoff_seconds"]
        return cfg["global_backoff_seconds"] if failure in GLOBAL_FAILURES else cfg["failure_backoff_seconds"]
    return cfg["empty_backoff_seconds"] if status == "NO_DATA" else cfg["refresh_seconds"]


def _finish(conn, item, status, cfg, now, *, failure="", observed=False, inserted=0):
    due = _stamp(now + timedelta(seconds=_ttl(status, failure, cfg)))
    conn.execute(f"""UPDATE {STATE_TABLE} SET status=?,next_due_at=?,
        last_success_at=CASE WHEN ?='AVAILABLE' THEN ? ELSE last_success_at END,
        provider_observed_at=CASE WHEN ? THEN ? ELSE provider_observed_at END,
        failure_category=?,lease_token='',lease_until=''
        WHERE fixture_id=? AND lease_token=?""",
        (status, due, status, _stamp(now), int(observed), _stamp(now), failure,
         item["fixture_id"], item["lease_token"]))
    if failure in GLOBAL_FAILURES:
        conn.execute(f"""INSERT INTO {STATE_TABLE}
            (fixture_id,status,last_attempt_at,next_due_at,provider_observed_at,failure_category)
            VALUES ('*',?,?,?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET
            status=excluded.status,last_attempt_at=excluded.last_attempt_at,next_due_at=excluded.next_due_at,
            provider_observed_at=excluded.provider_observed_at,failure_category=excluded.failure_category""",
            (status, _stamp(now), due, _stamp(now), failure))
    return {"fixture_id": item["fixture_id"], "status": status, "snapshots_inserted": inserted,
            "failure_category": failure, "next_due_at": due}


def _claim(conn, candidates, cfg, env, now):
    conn.execute("BEGIN IMMEDIATE")
    global_row = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id='*'").fetchone()
    global_due = _parse_stamp(global_row["next_due_at"]) if global_row else None
    if global_due and global_due > now and global_row["failure_category"]:
        conn.rollback()
        return [], None, {"status": "PROVIDER_FAILURE_BACKOFF", "failure_category": global_row["failure_category"],
                          "next_due_at": global_row["next_due_at"]}, 0, 0, ""

    due = []
    for item in candidates:
        row = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id=?", (item["fixture_id"],)).fetchone()
        state = dict(row) if row else {}
        lease = _parse_stamp(state.get("lease_until"))
        next_due = _parse_stamp(state.get("next_due_at"))
        if lease and lease > now:
            continue
        if next_due and next_due > now:
            continue
        due.append({**item, "last_attempt_at": state.get("last_attempt_at") or ""})
    due.sort(key=lambda item: (item["last_attempt_at"], item["kickoff_at"], item["fixture_id"]))
    if not due:
        conn.rollback()
        return [], None, None, 0, 0, ""

    feature_row = conn.execute(f"SELECT estimated_calls FROM {DAILY_TABLE} WHERE day_utc=?", (now.date().isoformat(),)).fetchone()
    feature_used = 0
    if feature_row:
        stored_estimate = feature_row[0]
        if type(stored_estimate) is not int or stored_estimate < 0:
            raise ValueError("invalid_odds_daily_estimate")
        feature_used = stored_estimate
    feature_remaining = max(0, cfg["daily_budget"] - feature_used)
    madrid_day = now.astimezone(MADRID).date().isoformat()
    shared_budget = usage_guard._budget("API_FOOTBALL_DAILY_CALL_BUDGET", usage_guard.DEFAULT_API_FOOTBALL_DAILY_CALL_BUDGET, env)
    shared_used = usage_guard._recorded_estimate(conn, PROVIDER, madrid_day)
    shared_remaining = max(0, shared_budget - shared_used)
    count = min(cfg["limit"], len(due), feature_remaining, shared_remaining)
    if count <= 0:
        conn.rollback()
        scope = "LOCAL_FEATURE_GUARD" if feature_remaining <= 0 else "LOCAL_APPLICATION_GUARD"
        return [], None, {"status": "DAILY_BUDGET", "budget_scope": scope,
                          "budget_limit": cfg["daily_budget"] if scope == "LOCAL_FEATURE_GUARD" else shared_budget,
                          "budget_used": feature_used if scope == "LOCAL_FEATURE_GUARD" else shared_used,
                          "budget_remaining": 0, "provider_quota_consulted": False}, len(due), 0, ""

    selected = due[:count]
    lease_until = _stamp(now + timedelta(seconds=90))
    for item in selected:
        item["lease_token"] = uuid.uuid4().hex
        conn.execute(f"""INSERT INTO {STATE_TABLE}
            (fixture_id,status,last_attempt_at,lease_token,lease_until)
            VALUES (?,'FETCHING',?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET
            status='FETCHING',last_attempt_at=excluded.last_attempt_at,
            lease_token=excluded.lease_token,lease_until=excluded.lease_until""",
            (item["fixture_id"], _stamp(now), item["lease_token"], lease_until))
    conn.execute(f"""INSERT INTO {DAILY_TABLE}(day_utc,estimated_calls,actual_calls,updated_at)
        VALUES (?,?,0,?) ON CONFLICT(day_utc) DO UPDATE SET
        estimated_calls=estimated_calls+excluded.estimated_calls,updated_at=excluded.updated_at""",
        (now.date().isoformat(), count, _stamp(now)))
    reservation = conn.execute("""INSERT INTO api_usage_guard
        (provider,window_key,job_key,estimated_calls,actual_calls,status,details_json,created_at)
        VALUES (?,?,?,?,0,'ALLOWED',?,?)""", (PROVIDER, madrid_day, "api_football_odds_fixture",
        count, json.dumps({"usage_scope": "LOCAL_GUARD_RESERVATIONS_NOT_PROVIDER_QUOTA", "utc_feature_cap": cfg["daily_budget"]}), _stamp(now))).lastrowid
    conn.commit()
    return selected, reservation, None, len(due), count, now.date().isoformat()


def _persist_fixture(conn, item, event, observed_at, snapshot_callback=None):
    bookmakers = event.get("bookmakers")
    if not isinstance(bookmakers, list) or len(bookmakers) > 60:
        return {"status": "NO_DATA", "inserted": 0, "valid": 0, "skipped": 0, "callback_errors": 0}
    fixture = event.get("fixture") if isinstance(event.get("fixture"), dict) else {}
    if str(fixture.get("id") or "") != item["fixture_id"]:
        return {"status": "INVALID_RESPONSE", "inserted": 0, "valid": 0, "skipped": 0, "callback_errors": 0}
    update = _provider_time(event)
    if not update:
        return {"status": "INVALID_RESPONSE", "inserted": 0, "valid": 0, "skipped": 0, "callback_errors": 0}
    update_text = _stamp(update)
    inserted = valid = skipped = callback_errors = 0
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            skipped += 1
            continue
        name = str(bookmaker.get("name") or "").strip()[:160]
        if not name:
            skipped += 1
            continue
        selected = _market_prices(bookmaker, item)
        if not selected:
            skipped += 1
            continue
        bet, prices = selected
        valid += 1
        book_id = str(bookmaker.get("id") or name)[:80]
        market_id = str(bet.get("id") or "")[:80]
        outcome_rows = [
            {"name": item.get("home_team") or "Home", "price": prices["home"]},
            {"name": "Draw", "price": prices["draw"]},
            {"name": item.get("away_team") or "Away", "price": prices["away"]},
        ]
        snapshot = {
            "provider": "API-Football", "source": "API-Football", "bookmaker": name,
            "bookmaker_id": book_id, "market": "1X2", "market_id": market_id,
            "home": prices["home"], "draw": prices["draw"], "away": prices["away"],
            "outcomes": outcome_rows, "odds_updated_at": update_text, "last_update": update_text,
        }
        identity_material = json.dumps([item["fixture_id"], book_id, market_id, update_text,
                                        prices["home"], prices["draw"], prices["away"]],
                                       ensure_ascii=False, separators=(",", ":"))
        snapshot_id = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()[:40]
        existed = conn.execute("SELECT 1 FROM odds_snapshots WHERE id=?", (snapshot_id,)).fetchone()
        conn.execute("""INSERT OR IGNORE INTO odds_snapshots
            (id,match_id,external_id,source,sport_key,league_name,bookmaker,market,
             home_team,away_team,home_price,draw_price,away_price,commence_time,payload_json,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (snapshot_id, item["id"], item["fixture_id"], "API-Football", "soccer",
             str(item.get("league_name") or item.get("competition_name") or "")[:160], name, "1x2",
             str(item.get("home_team") or "")[:160], str(item.get("away_team") or "")[:160],
             format(prices["home"], ".12g"), format(prices["draw"], ".12g"), format(prices["away"], ".12g"),
             str(item.get("kickoff_iso") or item.get("match_date") or "")[:80],
             json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))[:5000], _stamp(observed_at)))
        if not existed:
            inserted += 1
        old = conn.execute("SELECT odds_updated_at FROM matches WHERE id=?", (item["id"],)).fetchone()
        old_time = _parse_stamp(old[0]) if old and old[0] else None
        if old_time is None or update >= old_time:
            conn.execute("UPDATE matches SET bookmaker=?,odds_h2h_json=?,odds_updated_at=? WHERE id=?",
                         (name, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))[:5000], update_text, item["id"]))
            if snapshot_callback is not None:
                try:
                    snapshot_callback(conn.cursor(), item["id"], snapshot_id)
                except Exception:
                    callback_errors += 1
    status = "AVAILABLE" if valid else "NO_DATA"
    return {"status": status, "inserted": inserted, "valid": valid, "skipped": skipped,
            "callback_errors": callback_errors}


def refresh_api_football_odds_if_due(db_path, *, limit=None, env=None, transport=None, snapshot_callback=None):
    """Refresh only due, upcoming API-Football fixtures; never force-bypass cache or caps."""
    env = os.environ if env is None else env
    cfg = _settings(env, limit)
    configured, enabled = _configured(env), _enabled(env)
    result = {"ok": True, "status": "NO_DUE_ODDS", "configured": configured, "enabled": enabled,
              "skipped": True, "external_calls": 0, "processed": 0, "fixtures_count": 0,
              "snapshots_inserted": 0, "eligible_count": 0, "due_count": 0,
              "selected_fixture_ids": [], "provider_observation_current": False,
              "provider_observed_at": "", "provider_quota_consulted": False,
              "budget_scope": "LOCAL_GUARD_RESERVATIONS_NOT_PROVIDER_QUOTA", "items": [], "errors": []}
    if not configured:
        return {**result, "status": "NOT_CONFIGURED", "disabled": True}
    if not enabled or not cfg["limit"]:
        return {**result, "status": "DISABLED", "disabled": True}
    if _offline_safe(env):
        return {**result, "status": "OFFLINE_SAFE", "enabled": False, "disabled": True}
    if exhausted():
        return {**result, "status": "TIME_BUDGET"}

    try:
        with closing(_connect(db_path)) as conn:
            if not _table_exists(conn, "odds_snapshots"):
                raise sqlite3.OperationalError("odds snapshot store unavailable")
            with conn:
                _ensure_schema(conn)
            now = _now()
            candidates = _candidates(conn, now, cfg["days_ahead"])
            result["eligible_count"] = len(candidates)
            if not candidates:
                return {**result, "status": "SKIPPED_NO_API_FOOTBALL_FIXTURE"}
            selected, reservation, blocked, due_count, reserved, feature_day = _claim(conn, candidates, cfg, env, now)
            result["due_count"] = due_count
            if blocked:
                failure = str(blocked.get("failure_category") or "")
                return {**result, "ok": not bool(failure), "status": blocked.get("status") or "DAILY_BUDGET",
                        "skipped": True, "provider_failure_backoff": bool(failure),
                        "failure_category": failure, "failure_categories": [failure] if failure else [],
                        "reason_code": "LOCAL_APPLICATION_BUDGET_EXHAUSTED" if blocked.get("status") == "DAILY_BUDGET" else "",
                        "budget_scope": blocked.get("budget_scope") or "PROVIDER_FAILURE_BACKOFF",
                        "budget_limit": blocked.get("budget_limit"), "budget_used": blocked.get("budget_used"),
                        "budget_remaining": blocked.get("budget_remaining"),
                        "provider_quota_consulted": False,
                        "retry_after": blocked.get("next_due_at") or ""}
            if not selected:
                return {**result, "status": "NO_DUE_ODDS"}

            result.update(skipped=False, selected_fixture_ids=[item["fixture_id"] for item in selected])
            caller = transport or _api_get
            stop = False
            for item in selected:
                if exhausted() or stop:
                    with conn:
                        result["items"].append(_finish(conn, item, "TIME_BUDGET" if not stop else "DEFERRED_PROVIDER_FAILURE",
                                                        cfg, _now(), observed=False))
                    continue
                try:
                    payload = caller("odds", {"fixture": item["fixture_id"]}, timeout=4)
                    if isinstance(payload, dict) and type(payload.get("external_calls")) is int and payload["external_calls"] == 0:
                        with conn:
                            result["items"].append(_finish(conn, item, "OFFLINE_SAFE", cfg, _now(), observed=False))
                        continue
                    result["external_calls"] += 1
                except CronTimeBudget as exc:
                    result["external_calls"] += max(0, int(getattr(exc, "external_calls", 0) or 0))
                    with conn:
                        result["items"].append(_finish(conn, item, "TIME_BUDGET", cfg, _now(), observed=False))
                    continue
                except Exception:
                    # _api_get returns transport failures as closed error labels;
                    # an unexpected transport exception is conservatively charged.
                    result["external_calls"] += 1
                    payload = {"ok": False, "error": "PROVIDER_RESPONSE"}

                observed_at = _now()
                result.update(provider_observation_current=True, provider_observed_at=_stamp(observed_at))
                if not isinstance(payload, dict) or (payload.get("ok") and not isinstance(payload.get("response"), list)):
                    payload = {"ok": False, "errors": {"response": "INVALID_RESPONSE_SHAPE"}}
                if not payload.get("ok"):
                    failure = _failure(payload)
                    with conn:
                        result["items"].append(_finish(conn, item, "PROVIDER_FAILURE_" + failure, cfg,
                                                        observed_at, failure=failure, observed=True))
                    result["failure_categories"] = sorted(set(result.get("failure_categories", []) + [failure]))
                    stop = failure in GLOBAL_FAILURES
                    continue

                responses = payload.get("response")
                if len(responses) > 20 or any(not isinstance(row, dict) for row in responses):
                    with conn:
                        result["items"].append(_finish(conn, item, "PROVIDER_FAILURE_INVALID_RESPONSE", cfg,
                                                        observed_at, failure="PROVIDER_RESPONSE", observed=True))
                    result["failure_categories"] = sorted(set(result.get("failure_categories", []) + ["PROVIDER_RESPONSE"]))
                    continue
                matches = [row for row in responses if isinstance(row.get("fixture"), dict)
                           and str(row["fixture"].get("id") or "") == item["fixture_id"]]
                if len(matches) > 1:
                    outcome = {"status": "INVALID_RESPONSE", "inserted": 0, "valid": 0, "skipped": 0, "callback_errors": 0}
                elif not matches:
                    outcome = {"status": "NO_DATA", "inserted": 0, "valid": 0, "skipped": 0, "callback_errors": 0}
                else:
                    with conn:
                        outcome = _persist_fixture(conn, item, matches[0], observed_at, snapshot_callback)
                if outcome["status"] == "INVALID_RESPONSE":
                    with conn:
                        result["items"].append(_finish(conn, item, "PROVIDER_FAILURE_INVALID_RESPONSE", cfg,
                                                        observed_at, failure="PROVIDER_RESPONSE", observed=True))
                    result["failure_categories"] = sorted(set(result.get("failure_categories", []) + ["PROVIDER_RESPONSE"]))
                else:
                    with conn:
                        finished = _finish(conn, item, outcome["status"], cfg, observed_at,
                                           observed=True, inserted=outcome["inserted"])
                        finished.update({"bookmakers_received": len(matches[0].get("bookmakers") or []) if matches else 0,
                                         "bookmakers_with_1x2": outcome["valid"],
                                         "market_forecast_snapshot_errors": outcome["callback_errors"]})
                        result["items"].append(finished)
                    result["snapshots_inserted"] += outcome["inserted"]
                    result["bookmakers_with_1x2"] = result.get("bookmakers_with_1x2", 0) + outcome["valid"]

            with conn:
                conn.execute("UPDATE api_usage_guard SET actual_calls=? WHERE id=?", (result["external_calls"], reservation))
                conn.execute(f"UPDATE {DAILY_TABLE} SET actual_calls=actual_calls+?,updated_at=? WHERE day_utc=?",
                             (result["external_calls"], _stamp(_now()), feature_day))
                if result["external_calls"] < reserved:
                    delta = reserved - result["external_calls"]
                    conn.execute("UPDATE api_usage_guard SET estimated_calls=? WHERE id=?", (result["external_calls"], reservation))
                    conn.execute(f"UPDATE {DAILY_TABLE} SET estimated_calls=MAX(0,estimated_calls-?),updated_at=? WHERE day_utc=?",
                                 (delta, _stamp(_now()), feature_day))
    except CronTimeBudget as exc:
        result["external_calls"] += max(0, int(getattr(exc, "external_calls", 0) or 0))
        result["status"] = "TIME_BUDGET"
    except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
        result.update(ok=False, status="LOCAL_STORAGE_UNAVAILABLE", errors=["API_FOOTBALL_ODDS_LOCAL_STORAGE_UNAVAILABLE"])

    items = result["items"]
    result["processed"] = sum(item["status"] in {"AVAILABLE", "NO_DATA"} for item in items)
    result["fixtures_count"] = sum(item["status"] == "AVAILABLE" for item in items)
    result["failed_count"] = sum(item["status"].startswith("PROVIDER_FAILURE_") for item in items)
    result["data_contributed"] = result["snapshots_inserted"] > 0
    if result["failed_count"]:
        result.update(ok=result["data_contributed"], status="PARTIAL" if result["data_contributed"] else "PROVIDER_FAILURE",
                      errors=result.get("failure_categories") or ["PROVIDER_RESPONSE"])
    elif result["data_contributed"]:
        result["status"] = "OK"
    elif any(item["status"] == "NO_DATA" for item in items):
        result["status"] = "NO_DATA"
    elif any(item["status"] == "TIME_BUDGET" for item in items):
        result["status"] = "TIME_BUDGET"
    elif items:
        result["status"] = "PARTIAL"
    return result


def odds_runtime_status(db_path, env=None):
    """Read stored odds-sync evidence and local reservations without making requests."""
    env = os.environ if env is None else env
    cfg = _settings(env, None)
    result = {"configured": _configured(env), "enabled": _enabled(env),
              "last_status": "NOT_OBSERVED", "last_attempt_at": "", "last_success_at": "",
              "provider_observed_at": "", "failure_category": "", "fixtures_seen": 0,
              "snapshots_inserted": 0, "utc_day": _now().date().isoformat(),
              "local_daily_budget": cfg["daily_budget"], "local_daily_estimated_calls": None,
              "local_daily_actual_calls": None, "local_daily_remaining_estimate": None,
              "snapshots_total": 0,
              "usage_scope": "LOCAL_APPLICATION_GUARD_NOT_PROVIDER_QUOTA",
              "provider_quota_consulted": False, "read_only": True}
    try:
        path = Path(db_path).expanduser().resolve()
        if not path.is_file():
            return result
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.3)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            if _table_exists(conn, STATE_TABLE):
                row = conn.execute(f"SELECT * FROM {STATE_TABLE} WHERE fixture_id!='*' ORDER BY last_attempt_at DESC LIMIT 1").fetchone()
                if row:
                    item = dict(row)
                    result.update(last_status=item.get("status") or "NOT_OBSERVED",
                                  last_attempt_at=item.get("last_attempt_at") or "",
                                  last_success_at=item.get("last_success_at") or "",
                                  provider_observed_at=item.get("provider_observed_at") or "",
                                  failure_category=(safe_failure_categories(item.get("failure_category")) or [""])[0])
                result["fixtures_seen"] = max(0, int(conn.execute(f"SELECT COUNT(*) FROM {STATE_TABLE} WHERE fixture_id!='*'").fetchone()[0]))
            if _table_exists(conn, DAILY_TABLE):
                row = conn.execute(f"SELECT estimated_calls,actual_calls FROM {DAILY_TABLE} WHERE day_utc=?",
                                   (result["utc_day"],)).fetchone()
                if row:
                    estimated = max(0, int(row[0]))
                    actual = max(0, int(row[1]))
                    result.update(local_daily_estimated_calls=estimated,
                                  local_daily_actual_calls=actual,
                                  local_daily_remaining_estimate=max(0, cfg["daily_budget"] - estimated))
            if _table_exists(conn, "odds_snapshots"):
                row = conn.execute("SELECT COUNT(*) FROM odds_snapshots WHERE source='API-Football'").fetchone()
                result["snapshots_total"] = max(0, int(row[0] or 0))
                result["snapshots_inserted"] = result["snapshots_total"]
    except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
        result["last_status"] = "READ_UNAVAILABLE"
    return result

