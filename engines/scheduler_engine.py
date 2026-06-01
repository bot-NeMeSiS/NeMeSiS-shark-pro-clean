"""Safe internal scheduler helpers for NeMeSiS SHARK PRO.

This module is pure logic. Flask, SQLite writes and API calls stay in app.py.
"""

from datetime import datetime, timedelta


TASKS = [
    {"name": "calendar", "label": "Calendario SportsDB", "kind": "sportsdb", "env": "SPORTSDB_SYNC_HOURS", "unit": "hours", "default": 6},
    {"name": "crests", "label": "Equipos y escudos", "kind": "crests", "env": "CREST_SYNC_HOURS", "unit": "hours", "default": 24},
    {"name": "odds", "label": "Cuotas Odds", "kind": "odds", "env": "ODDS_CACHE_MINUTES", "unit": "minutes", "default": 20},
    {"name": "live", "label": "Live basico", "kind": "live", "env": "LIVE_CACHE_MINUTES", "unit": "minutes", "default": 2},
    {"name": "recommendations", "label": "Recomendaciones SHARK", "kind": "intelligence", "env": "RECOMMENDATIONS_REFRESH_MINUTES", "unit": "minutes", "default": 30},
    {"name": "auto_picks", "label": "Auto Picks Engine", "kind": "picks", "env": "AUTO_PICKS_REFRESH_MINUTES", "unit": "minutes", "default": 45},
    {"name": "live_alerts", "label": "Alertas Live SHARK", "kind": "telegram", "env": "LIVE_ALERTS_REFRESH_MINUTES", "unit": "minutes", "default": 5},
    {"name": "warehouse", "label": "Warehouse historico", "kind": "maintenance", "env": "WAREHOUSE_REFRESH_HOURS", "unit": "hours", "default": 12},
    {"name": "cleanup", "label": "Limpieza logs", "kind": "maintenance", "env": "SCHEDULER_LOG_CLEANUP_HOURS", "unit": "hours", "default": 24},
    {"name": "telegram", "label": "Telegram Premium", "kind": "telegram", "env": "TELEGRAM_PREPARE_HOURS", "unit": "hours", "default": 6},
]


def env_bool(env, key, default=False):
    value = str(env.get(key, "")).strip().lower()
    if not value:
        return bool(default)
    return value in {"1", "true", "yes", "on"}


def env_int(env, key, default, minimum=1):
    try:
        value = int(float(str(env.get(key, default)).replace(",", ".")))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def task_definition(task_name):
    for task in TASKS:
        if task["name"] == task_name:
            return dict(task)
    return {"name": task_name, "label": task_name, "kind": "custom", "env": "", "unit": "minutes", "default": 30}


def interval_seconds(task_name, env):
    task = task_definition(task_name)
    value = env_int(env, task.get("env"), task.get("default", 30), 1)
    if task.get("unit") == "hours":
        return value * 3600
    return value * 60


def scheduler_config(env):
    return {
        "enabled": env_bool(env, "ENABLE_AUTO_SYNC", True),
        "startup": env_bool(env, "AUTO_SYNC_ON_STARTUP", True),
        "tasks": [
            {
                **task,
                "interval_seconds": interval_seconds(task["name"], env),
            }
            for task in TASKS
        ],
    }


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def seconds_until_due(row, task_name, env, now_iso):
    last_run = parse_iso((row or {}).get("last_run") or (row or {}).get("locked_at"))
    if not last_run:
        return 0
    now = parse_iso(now_iso) or datetime.utcnow()
    due_at = last_run + timedelta(seconds=interval_seconds(task_name, env))
    return int((due_at - now).total_seconds())


def is_due(row, task_name, env, now_iso, force=False):
    if force:
        return True
    return seconds_until_due(row, task_name, env, now_iso) <= 0


def is_stale_running(row, now_iso, stale_minutes=12):
    if not row or str(row.get("status") or "").upper() != "RUNNING":
        return False
    locked_at = parse_iso(row.get("locked_at"))
    now = parse_iso(now_iso) or datetime.utcnow()
    if not locked_at:
        return True
    return now - locked_at > timedelta(minutes=max(1, int(stale_minutes)))


def next_run_iso(now_iso, task_name, env):
    now = parse_iso(now_iso) or datetime.utcnow()
    return (now + timedelta(seconds=interval_seconds(task_name, env))).isoformat(timespec="seconds")


def normalize_result(task_name, result, started_at="", finished_at=""):
    result = dict(result or {})
    return {
        "ok": bool(result.get("ok", True)) and not bool(result.get("sin_key")),
        "task": task_name,
        "started_at": started_at,
        "finished_at": finished_at,
        "processed": int(result.get("processed") or result.get("total_items") or 0),
        "inserted": int(result.get("inserted") or result.get("imported") or 0),
        "updated": int(result.get("updated") or 0),
        "skipped": int(result.get("skipped") or result.get("failed") or 0),
        "errors": result.get("errors") or ([] if not result.get("error") else [result.get("error")]),
        "raw": result,
    }
