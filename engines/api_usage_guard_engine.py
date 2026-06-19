"""API usage guard for NeMeSiS SHARK PRO V818 daily automation."""
from __future__ import annotations

import json
import os
import sqlite3
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


def _budget(name: str, default: int) -> int:
    raw = str(os.getenv(name, "auto") or "auto").strip().lower()
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
    env = env or os.environ
    today = madrid_now().date().isoformat()
    budgets = {
        "api_football": _budget("API_FOOTBALL_DAILY_CALL_BUDGET", 120),
        "odds_api": _budget("ODDS_API_DAILY_CALL_BUDGET", 40),
    }
    used = {"api_football": 0, "odds_api": 0}
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            ensure_api_usage_guard_schema(conn)
            for provider in used:
                row = conn.execute(
                    "SELECT COALESCE(SUM(estimated_calls),0) AS calls FROM api_usage_guard WHERE provider=? AND window_key=?",
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
    env = env or os.environ
    today = madrid_now().date().isoformat()
    snapshot = api_usage_snapshot(db_path, env=env)
    budget = int((snapshot.get("budgets") or {}).get(provider, 0))
    used = int((snapshot.get("used_estimated") or {}).get(provider, 0))
    remaining = max(0, budget - used)
    allowed = estimated_calls <= remaining
    result = {
        "ok": allowed,
        "provider": provider,
        "job_key": job_key,
        "estimated_calls": int(estimated_calls or 0),
        "remaining_before": remaining,
        "budget": budget,
        "reason": "" if allowed else "api_budget_exceeded",
    }
    try:
        with sqlite3.connect(db_path) as conn:
            ensure_api_usage_guard_schema(conn)
            conn.execute(
                """INSERT INTO api_usage_guard(provider, window_key, job_key, estimated_calls, actual_calls, status, details_json, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (provider, today, job_key, int(estimated_calls or 0), 0, "ALLOWED" if allowed else "BLOCKED", _json(result), madrid_now().isoformat(timespec="seconds")),
            )
            conn.commit()
    except Exception:
        pass
    return result


def cache_get(db_path: str, provider: str, cache_key: str) -> Any:
    try:
        with sqlite3.connect(db_path) as conn:
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
        with sqlite3.connect(db_path) as conn:
            ensure_api_usage_guard_schema(conn)
            conn.execute(
                """INSERT OR REPLACE INTO api_response_cache(cache_key, provider, value_json, expires_at, updated_at)
                   VALUES (?,?,?,?,?)""",
                (cache_key, provider, _json(value), (now + timedelta(seconds=max(30, int(ttl_seconds)))).isoformat(timespec="seconds"), now.isoformat(timespec="seconds")),
            )
            conn.commit()
    except Exception:
        pass
