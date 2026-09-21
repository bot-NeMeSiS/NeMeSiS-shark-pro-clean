"""API usage guard for NeMeSiS SHARK PRO V818 daily automation."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
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


def api_usage_snapshot(db_path: str, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if env is None else env
    today = madrid_now().date().isoformat()
    budgets = {
        "api_football": _budget("API_FOOTBALL_DAILY_CALL_BUDGET", 120, env),
        "odds_api": _budget("ODDS_API_DAILY_CALL_BUDGET", 40, env),
    }
    used = {"api_football": 0, "odds_api": 0}
    try:
        with closing(sqlite3.connect(db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            ensure_api_usage_guard_schema(conn)
            for provider in used:
                row = conn.execute(
                    "SELECT COALESCE(SUM(CASE WHEN status='ALLOWED' AND estimated_calls>0 THEN estimated_calls ELSE 0 END),0) AS calls FROM api_usage_guard WHERE provider=? AND window_key=?",
                    (provider, today),
                ).fetchone()
                used[provider] = int(row["calls"] if row else 0)
    except Exception:
        pass
    return {
        "madrid_date": today,
        "budgets": budgets,
        "used_estimated": used,
        "remaining_estimated": {key: max(0, budgets[key] - used.get(key, 0)) for key in budgets},
        "configured": {
            "api_football": bool(env.get("API_FOOTBALL_KEY") or env.get("API_FOOTBALL_API_KEY")),
            "odds_api": bool(env.get("ODDS_API_KEY") or env.get("THE_ODDS_API_KEY")),
        },
        "policy": "cache first, top leagues first, no rare leagues for Telegram",
    }


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
                used = conn.execute(
                    """SELECT COALESCE(SUM(CASE WHEN status='ALLOWED' AND estimated_calls>0
                               THEN estimated_calls ELSE 0 END),0)
                       FROM api_usage_guard WHERE provider=? AND window_key=?""",
                    (provider, today),
                ).fetchone()[0]
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
    try:
        with closing(sqlite3.connect(db_path)) as conn, conn:
            conn.row_factory = sqlite3.Row
            ensure_api_usage_guard_schema(conn)
            row = conn.execute("SELECT value_json, expires_at FROM api_response_cache WHERE provider=? AND cache_key=?", (provider, cache_key)).fetchone()
            if not row:
                return None
            expires = row["expires_at"] or ""
            if expires and datetime.fromisoformat(expires) < madrid_now():
                return None
            return json.loads(row["value_json"] or "null")
    except Exception:
        return None


def cache_set(db_path: str, provider: str, cache_key: str, value: Any, ttl_seconds: int = 900) -> None:
    try:
        now = madrid_now()
        with closing(sqlite3.connect(db_path)) as conn, conn:
            ensure_api_usage_guard_schema(conn)
            conn.execute(
                """INSERT OR REPLACE INTO api_response_cache(cache_key, provider, value_json, expires_at, updated_at)
                   VALUES (?,?,?,?,?)""",
                (cache_key, provider, _json(value), (now + timedelta(seconds=max(30, int(ttl_seconds)))).isoformat(timespec="seconds"), now.isoformat(timespec="seconds")),
            )
            conn.commit()
    except Exception:
        pass
