"""API usage guard for NeMeSiS SHARK PRO V818 daily automation."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")


def madrid_now() -> datetime:
    return datetime.now(TZ)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _budget(name: str, default: int, env: Mapping[str, str] | None = None) -> int:
    source = os.environ if env is None else env
    raw = str(source.get(name, "auto") or "auto").strip().lower()
    if raw in {"auto", ""}:
        return default
    return max(0, _int(raw, default))


def ensure_api_usage_guard_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS api_usage_guard(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            window_key TEXT NOT NULL,
            job_key TEXT,
            estimated_calls INTEGER DEFAULT 0,
            actual_calls INTEGER DEFAULT 0,
            status TEXT,
            details_json TEXT,
            created_at TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_guard_provider_window ON api_usage_guard(provider, window_key)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS api_response_cache(
            cache_key TEXT PRIMARY KEY,
            provider TEXT,
            value_json TEXT,
            expires_at TEXT,
            updated_at TEXT
        )"""
    )


@contextmanager
def _read_connection(db_path: str):
    """Existing file only; reading a budget/cache must never initialize storage."""
    path = Path(db_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError("budget_store_not_initialized")
    if not path.is_file():
        raise OSError("budget_store_unavailable")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.3)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        yield conn


def _table_present(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _recorded_estimate(conn: sqlite3.Connection, provider: str, today: str) -> int:
    """Use the same validated ledger for display and authorization.

    SQLite can store text or fractions in an INTEGER-affinity column. Do not
    truncate these values into permission to make another provider request.
    Historical negative integer rows remain ignored, never credits.
    """
    row = conn.execute(
        """SELECT COALESCE(SUM(CASE WHEN status='ALLOWED'
                 AND typeof(estimated_calls)='integer' AND estimated_calls>0
                 THEN estimated_calls ELSE 0 END),0),
                 COALESCE(SUM(CASE WHEN status='ALLOWED'
                 AND typeof(estimated_calls)!='integer' THEN 1 ELSE 0 END),0)
           FROM api_usage_guard WHERE provider=? AND window_key=?""",
        (provider, today),
    ).fetchone()
    if row is None or row[1] or type(row[0]) is not int or row[0] < 0:
        raise ValueError("invalid_recorded_usage")
    return row[0]


def api_usage_snapshot(db_path: str, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Read recorded estimates, not the provider quota. Unknown is never zero.

    All provider counters belong to one read transaction. If either read fails,
    no partial balances escape. Initializing this ledger belongs to a write.
    """
    env = os.environ if env is None else env
    now = madrid_now()
    today = now.date().isoformat()
    budgets = {
        "api_football": _budget("API_FOOTBALL_DAILY_CALL_BUDGET", 120, env),
        "odds_api": _budget("ODDS_API_DAILY_CALL_BUDGET", 40, env),
    }
    result = {
        "ok": False,
        "state": "NOT_INITIALIZED",
        "madrid_date": today,
        "checked_at": now.isoformat(timespec="seconds"),
        "budgets": budgets,
        "used_estimated": {provider: None for provider in budgets},
        "remaining_estimated": {provider: None for provider in budgets},
        "configured": {
            "api_football": bool(env.get("API_FOOTBALL_KEY") or env.get("API_FOOTBALL_API_KEY")),
            "odds_api": bool(env.get("ODDS_API_KEY") or env.get("THE_ODDS_API_KEY")),
        },
        "usage_scope": "LOCAL_GUARD_RESERVATIONS_NOT_PROVIDER_QUOTA",
        "provider_quota_verified": False,
        "policy": "cache first, top leagues first, no rare leagues for Telegram",
    }
    try:
        with _read_connection(db_path) as conn:
            if not _table_present(conn, "api_usage_guard"):
                return result
            used = {}
            for provider in budgets:
                used[provider] = _recorded_estimate(conn, provider, today)
        result.update(ok=True, state="READY", used_estimated=used,
                      remaining_estimated={provider: max(0, budgets[provider] - used[provider]) for provider in budgets})
    except FileNotFoundError:
        pass
    except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
        result["state"] = "READ_UNAVAILABLE"
    return result


def allow_api_job(db_path: str, provider: str, job_key: str, estimated_calls: int, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Atomically reserve an estimate before authorizing work; never call a provider.

    A stored estimate is not the provider's measured quota. A failed reservation
    must not authorize work. Approved reservations remain consumed if a callback
    subsequently fails: this guard cannot prove that the provider was not called.
    """
    env = os.environ if env is None else env
    now = madrid_now()
    today = now.date().isoformat()
    budgets = {
        "api_football": _budget("API_FOOTBALL_DAILY_CALL_BUDGET", 120, env),
        "odds_api": _budget("ODDS_API_DAILY_CALL_BUDGET", 40, env),
    }
    valid_estimate = type(estimated_calls) is int and estimated_calls >= 0
    result = {
        "ok": False,
        "provider": provider,
        "job_key": job_key,
        "estimated_calls": estimated_calls if valid_estimate else 0,
        "remaining_before": None,
        "budget": budgets.get(provider, 0),
        "reason": "invalid_api_estimate" if not valid_estimate else "unknown_api_provider",
    }
    if not valid_estimate or provider not in budgets:
        return result
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            with conn:
                ensure_api_usage_guard_schema(conn)
            # Read + decide + reserve share one write transaction. Other callers
            # cannot all approve against the same stale remaining budget.
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                used = _recorded_estimate(conn, provider, today)
                remaining = max(0, budgets[provider] - int(used))
                allowed = estimated_calls <= remaining
                result.update(ok=allowed, remaining_before=remaining,
                              reason="" if allowed else "api_budget_exceeded")
                conn.execute(
                    """INSERT INTO api_usage_guard(provider, window_key, job_key,
                           estimated_calls, actual_calls, status, details_json, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (provider, today, job_key, estimated_calls if allowed else 0, 0,
                     "ALLOWED" if allowed else "BLOCKED", _json(result), now.isoformat(timespec="seconds")),
                )
            # Success is returned only after COMMIT, not merely after INSERT.
        return result
    except (sqlite3.Error, OSError, ValueError, OverflowError):
        # Do not echo DB paths, SQL or secrets from exception messages.
        result.update(ok=False, remaining_before=None, reason="api_budget_storage_unavailable")
        return result


def cache_get(db_path: str, provider: str, cache_key: str) -> Any:
    """Cache miss on missing/unreadable/expired data; no schema writes or HTTP."""
    try:
        with _read_connection(db_path) as conn:
            if not _table_present(conn, "api_response_cache"):
                return None
            row = conn.execute("SELECT value_json, expires_at FROM api_response_cache WHERE provider=? AND cache_key=?", (provider, cache_key)).fetchone()
            if not row or not row["expires_at"]:
                return None
            expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            now = madrid_now()
            if expires.tzinfo is None or expires.utcoffset() is None or now.tzinfo is None:
                return None
            if expires.astimezone(timezone.utc) <= now.astimezone(timezone.utc):
                return None
            return json.loads(row["value_json"] or "null")
    except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError, RecursionError):
        return None


def cache_set(db_path: str, provider: str, cache_key: str, value: Any, ttl_seconds: int = 900) -> None:
    try:
        now = madrid_now()
        with closing(sqlite3.connect(db_path)) as conn, conn:
            ensure_api_usage_guard_schema(conn)
            conn.execute(
                """INSERT OR REPLACE INTO api_response_cache(cache_key, provider, value_json, expires_at, updated_at)
                   VALUES (?,?,?,?,?)""",
                (cache_key, provider, _json(value), (now.astimezone(timezone.utc) + timedelta(seconds=max(30, int(ttl_seconds)))).isoformat(timespec="seconds"), now.isoformat(timespec="seconds")),
            )
            conn.commit()
    except Exception:
        pass
