"""V818 daily automation operating system for NeMeSiS SHARK PRO."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

from engines.api_usage_guard_engine import allow_api_job, api_usage_snapshot, ensure_api_usage_guard_schema
from engines.telegram_professional_scheduler import professional_telegram_summary

TZ = ZoneInfo("Europe/Madrid")

JOB_WINDOWS = {
    "daily_close_previous_day": "00:10",
    "daily_data_backup_maintenance": "02:30",
    "morning_fixtures_sync": "07:00",
    "morning_odds_and_pick_candidates": "09:00",
    "telegram_daily_top_agenda": "11:30",
    "daily_evening_recap": "22:45",
}

ALWAYS_JOBS = [
    "match_lifecycle_reconciler",
    "live_tracker_smart_sync",
    "telegram_prematch_top_alerts",
    "telegram_live_top_alerts",
    "results_sync_and_telegram_top_results",
    "system_health_daily_check",
]

JOB_NAMES = {
    "daily_close_previous_day": "Cierre de dia anterior",
    "daily_data_backup_maintenance": "Backup y mantenimiento",
    "morning_fixtures_sync": "Agenda del dia",
    "morning_odds_and_pick_candidates": "Cuotas y picks candidatos",
    "telegram_daily_top_agenda": "Telegram agenda TOP",
    "match_lifecycle_reconciler": "Ciclo de vida de partidos",
    "live_tracker_smart_sync": "Live tracker inteligente",
    "telegram_prematch_top_alerts": "Recordatorios prepartido TOP",
    "telegram_live_top_alerts": "Alertas live TOP",
    "results_sync_and_telegram_top_results": "Resultados y Telegram TOP",
    "daily_evening_recap": "Resumen cierre del dia",
    "system_health_daily_check": "Salud del sistema",
}

API_ESTIMATES = {
    "morning_fixtures_sync": ("api_football", 6),
    "morning_odds_and_pick_candidates": ("odds_api", 5),
    "live_tracker_smart_sync": ("api_football", 1),
    "results_sync_and_telegram_top_results": ("api_football", 2),
    "daily_close_previous_day": ("api_football", 2),
}


def madrid_now() -> datetime:
    return datetime.now(TZ)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _load_json(value: str | None, default: Any = None) -> Any:
    try:
        return json.loads(value or "null")
    except Exception:
        return default


def _dict_row(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row else {}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return bool(row)


def ensure_automation_schema(db_path: str) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        ensure_automation_schema_conn(conn)
        conn.commit()
    return {"ok": True, "schema": "v818_daily_automation_ready"}


def ensure_automation_schema_conn(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS automation_jobs_state(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_key TEXT UNIQUE NOT NULL,
            job_name TEXT,
            last_run_at TEXT,
            last_run_madrid TEXT,
            last_status TEXT,
            last_error TEXT,
            last_duration_ms INTEGER DEFAULT 0,
            run_count INTEGER DEFAULT 0,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS automation_job_runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_key TEXT NOT NULL,
            trigger_type TEXT,
            status TEXT,
            started_at TEXT,
            finished_at TEXT,
            duration_ms INTEGER DEFAULT 0,
            madrid_date TEXT,
            summary_json TEXT,
            error_summary TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS automation_dedupe(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedupe_key TEXT UNIQUE NOT NULL,
            job_key TEXT,
            created_at TEXT,
            expires_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS automation_health_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            area TEXT,
            message TEXT,
            details_json TEXT,
            created_at TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_automation_runs_job_date ON automation_job_runs(job_key, madrid_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_automation_dedupe_expires ON automation_dedupe(expires_at)")
    ensure_api_usage_guard_schema(conn)


def _cleanup_dedupe(conn: sqlite3.Connection, now: datetime) -> None:
    conn.execute("DELETE FROM automation_dedupe WHERE expires_at IS NOT NULL AND expires_at!='' AND expires_at < ?", (now.isoformat(timespec="seconds"),))


def claim_dedupe(conn: sqlite3.Connection, job_key: str, dedupe_key: str, ttl_hours: int = 36) -> bool:
    now = madrid_now()
    _cleanup_dedupe(conn, now)
    try:
        conn.execute(
            "INSERT INTO automation_dedupe(dedupe_key, job_key, created_at, expires_at) VALUES (?,?,?,?)",
            (dedupe_key, job_key, now.isoformat(timespec="seconds"), (now + timedelta(hours=ttl_hours)).isoformat(timespec="seconds")),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def _mark_job_state(conn: sqlite3.Connection, job_key: str, status: str, duration_ms: int, error: str = "") -> None:
    now = madrid_now()
    conn.execute(
        """INSERT INTO automation_jobs_state(job_key, job_name, last_run_at, last_run_madrid, last_status, last_error, last_duration_ms, run_count, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(job_key) DO UPDATE SET
             job_name=excluded.job_name,
             last_run_at=excluded.last_run_at,
             last_run_madrid=excluded.last_run_madrid,
             last_status=excluded.last_status,
             last_error=excluded.last_error,
             last_duration_ms=excluded.last_duration_ms,
             run_count=automation_jobs_state.run_count + 1,
             updated_at=excluded.updated_at""",
        (job_key, JOB_NAMES.get(job_key, job_key), now.isoformat(timespec="seconds"), now.strftime("%Y-%m-%d %H:%M"), status, error[:900], duration_ms, 1, now.isoformat(timespec="seconds")),
    )


def _record_run(conn: sqlite3.Connection, job_key: str, trigger_type: str, status: str, started: datetime, summary: Mapping[str, Any], error: str = "") -> None:
    finished = madrid_now()
    duration_ms = int((finished - started).total_seconds() * 1000)
    conn.execute(
        """INSERT INTO automation_job_runs(job_key, trigger_type, status, started_at, finished_at, duration_ms, madrid_date, summary_json, error_summary)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (job_key, trigger_type, status, started.isoformat(timespec="seconds"), finished.isoformat(timespec="seconds"), duration_ms, started.date().isoformat(), _json(summary), error[:900]),
    )
    _mark_job_state(conn, job_key, status, duration_ms, error)


def jobs_due(now: datetime | None = None, force: bool = False) -> list[str]:
    now = now or madrid_now()
    if force:
        return list(JOB_WINDOWS) + list(ALWAYS_JOBS)
    due = list(ALWAYS_JOBS)
    minutes_now = now.hour * 60 + now.minute
    for key, hhmm in JOB_WINDOWS.items():
        hour, minute = [int(part) for part in hhmm.split(":")]
        target = hour * 60 + minute
        if target <= minutes_now < target + 15:
            due.append(key)
    return due


def next_recommended_run(now: datetime | None = None) -> str:
    now = now or madrid_now()
    return (now + timedelta(minutes=15)).replace(second=0, microsecond=0).isoformat(timespec="minutes")


def _count(conn: sqlite3.Connection, table: str, where: str = "1=1", params: tuple[Any, ...] = ()) -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS total FROM {table} WHERE {where}", params).fetchone()
    return int(row["total"] if row else 0)


def reconcile_match_lifecycle(db_path: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or madrid_now()
    updated = {"past_pending": 0, "future_upcoming": 0, "finalized": 0}
    today = now.date().isoformat()
    current_time = now.strftime("%H:%M")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_automation_schema_conn(conn)
        if not _table_exists(conn, "matches"):
            return {"ok": True, "skipped": True, "reason": "matches_table_missing", "updated": updated}
        cur = conn.cursor()
        cur.execute(
            """UPDATE matches
               SET status='Resultado pendiente', updated_at=?
               WHERE COALESCE(score,'')='' AND COALESCE(home_score,'')='' AND COALESCE(away_score,'')=''
                 AND (match_date < ? OR (match_date=? AND COALESCE(kickoff_time, match_time, '')!='' AND COALESCE(kickoff_time, match_time, '') < ?))
                 AND lower(COALESCE(status,'')) NOT LIKE '%final%'
                 AND lower(COALESCE(status,'')) NOT LIKE '%live%'
                 AND lower(COALESCE(status,'')) NOT LIKE '%directo%'
                 AND lower(COALESCE(status,'')) NOT LIKE '%pendiente%'""",
            (now.isoformat(timespec="seconds"), today, today, current_time),
        )
        updated["past_pending"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        cur.execute(
            """UPDATE matches
               SET status='Proximo', updated_at=?
               WHERE match_date >= ?
                 AND COALESCE(score,'')='' AND COALESCE(home_score,'')='' AND COALESCE(away_score,'')=''
                 AND lower(COALESCE(status,'')) IN ('', 'scheduled', 'programado', 'next', 'upcoming', 'proximo', 'próximo')""",
            (now.isoformat(timespec="seconds"), today),
        )
        updated["future_upcoming"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        cur.execute(
            """UPDATE matches
               SET status='Finalizado', updated_at=?
               WHERE (COALESCE(score,'')!='' OR COALESCE(home_score,'')!='' OR COALESCE(away_score,'')!='')
                 AND lower(COALESCE(status,'')) NOT LIKE '%live%'
                 AND lower(COALESCE(status,'')) NOT LIKE '%directo%'
                 AND lower(COALESCE(status,'')) NOT LIKE '%final%'""",
            (now.isoformat(timespec="seconds"),),
        )
        updated["finalized"] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
    return {"ok": True, "updated": updated, "no_invented_results": True, "madrid_date": today}


def system_health(db_path: str, app_version: str, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = env or os.environ
    checks: dict[str, Any] = {
        "db_path": db_path,
        "db_accessible": False,
        "critical_tables": {},
        "api_football_configured": bool(env.get("API_FOOTBALL_KEY") or env.get("API_FOOTBALL_API_KEY")),
        "odds_api_configured": bool(env.get("ODDS_API_KEY") or env.get("THE_ODDS_API_KEY")),
        "telegram_configured": bool(env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID")),
        "automation_secret_configured": bool(env.get("AUTOMATION_SECRET")),
        "version": app_version,
        "madrid_now": madrid_now().isoformat(timespec="seconds"),
    }
    warnings = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            ensure_automation_schema_conn(conn)
            checks["db_accessible"] = True
            for table in ["users", "matches", "picks", "telegram_queue", "automation_jobs_state", "automation_dedupe"]:
                checks["critical_tables"][table] = _table_exists(conn, table)
            checks["recent_failed_runs"] = _count(conn, "automation_job_runs", "status='FAILED' AND madrid_date=?", (madrid_now().date().isoformat(),))
            checks["telegram_sent_today"] = _count(conn, "telegram_deliveries", "status='SENT' AND created_at LIKE ?", (madrid_now().date().isoformat() + "%",))
    except Exception as exc:
        warnings.append(f"DB no accesible: {str(exc)[:160]}")
    for key in ("api_football_configured", "odds_api_configured", "telegram_configured", "automation_secret_configured"):
        if not checks.get(key):
            warnings.append(f"{key} pendiente en entorno Render")
    checks["ok"] = checks["db_accessible"] and checks["automation_secret_configured"]
    checks["warnings"] = warnings
    return checks


def automation_status(db_path: str, app_version: str, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = env or os.environ
    now = madrid_now()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_automation_schema_conn(conn)
        states = [dict(row) for row in conn.execute("SELECT * FROM automation_jobs_state ORDER BY updated_at DESC LIMIT 30").fetchall()]
        today_runs = [dict(row) for row in conn.execute("SELECT * FROM automation_job_runs WHERE madrid_date=? ORDER BY started_at DESC LIMIT 50", (now.date().isoformat(),)).fetchall()]
        failed = [row for row in today_runs if row.get("status") == "FAILED"]
        telegram_sent = _count(conn, "telegram_deliveries", "status='SENT' AND created_at LIKE ?", (now.date().isoformat() + "%",))
        pending_results = _count(conn, "matches", "lower(COALESCE(status,'')) LIKE '%pendiente%'")
    return {
        "ok": True,
        "version": app_version,
        "madrid_now": now.isoformat(timespec="seconds"),
        "master_tick": states[0] if states else {},
        "next_jobs": [{"job_key": key, "name": JOB_NAMES.get(key), "window": JOB_WINDOWS.get(key, "cada tick")} for key in jobs_due(now)[:12]],
        "jobs_today": today_runs,
        "jobs_failed": failed,
        "telegram_sent_today": telegram_sent,
        "results_pending": pending_results,
        "api_usage": api_usage_snapshot(db_path, env=env),
        "telegram_policy": professional_telegram_summary(env),
        "health": system_health(db_path, app_version, env=env),
    }


def automation_runs(db_path: str, limit: int = 80) -> dict[str, Any]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_automation_schema_conn(conn)
        runs = [dict(row) for row in conn.execute("SELECT * FROM automation_job_runs ORDER BY started_at DESC LIMIT ?", (int(limit),)).fetchall()]
    return {"ok": True, "runs": runs, "count": len(runs)}


def _fallback_job(job_key: str, db_path: str, callbacks: Mapping[str, Callable[..., Mapping[str, Any]]] | None) -> dict[str, Any]:
    callbacks = callbacks or {}
    if job_key == "match_lifecycle_reconciler":
        return reconcile_match_lifecycle(db_path)
    if job_key == "system_health_daily_check":
        health_cb = callbacks.get("health")
        return dict(health_cb() if health_cb else {"ok": True, "health": "basic"})
    cb = callbacks.get(job_key)
    if cb:
        return dict(cb())
    return {"ok": True, "skipped": True, "reason": "no_safe_mutation_callback", "no_invented_data": True}


def run_master_tick(
    db_path: str,
    app_version: str,
    env: Mapping[str, str] | None = None,
    callbacks: Mapping[str, Callable[..., Mapping[str, Any]]] | None = None,
    trigger_type: str = "cron",
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    env = env or os.environ
    now = madrid_now()
    due = jobs_due(now, force=force)
    jobs_run: list[dict[str, Any]] = []
    jobs_skipped: list[dict[str, Any]] = []
    jobs_failed: list[dict[str, Any]] = []
    telegram_sent = 0
    api_calls_estimated = 0
    warnings: list[str] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_automation_schema_conn(conn)
        _cleanup_dedupe(conn, now)
        for job_key in due:
            started = madrid_now()
            daily_once = job_key in JOB_WINDOWS or job_key in {"system_health_daily_check"}
            dedupe_key = f"v818:{now.date().isoformat()}:{job_key}"
            if daily_once and not force and not claim_dedupe(conn, job_key, dedupe_key, ttl_hours=36):
                skipped = {"job_key": job_key, "reason": "dedupe_already_done", "dedupe_key": dedupe_key}
                jobs_skipped.append(skipped)
                _record_run(conn, job_key, trigger_type, "SKIPPED", started, skipped)
                continue
            if dry_run:
                skipped = {"job_key": job_key, "reason": "dry_run", "would_run": True}
                jobs_skipped.append(skipped)
                _record_run(conn, job_key, trigger_type, "DRY_RUN", started, skipped)
                continue
            provider_estimate = API_ESTIMATES.get(job_key)
            if provider_estimate:
                provider, estimate = provider_estimate
                guard = allow_api_job(db_path, provider, job_key, estimate, env=env)
                api_calls_estimated += estimate if guard.get("ok") else 0
                if not guard.get("ok"):
                    skipped = {"job_key": job_key, "reason": guard.get("reason"), "api_guard": guard}
                    jobs_skipped.append(skipped)
                    _record_run(conn, job_key, trigger_type, "SKIPPED", started, skipped)
                    continue
            try:
                summary = _fallback_job(job_key, db_path, callbacks)
                status = "OK" if summary.get("ok", True) else "FAILED"
                if status == "OK":
                    jobs_run.append({"job_key": job_key, "summary": summary})
                    telegram_sent += int(summary.get("telegram_sent") or summary.get("sent") or summary.get("sent_count") or 0)
                else:
                    jobs_failed.append({"job_key": job_key, "error": summary.get("error") or summary.get("reason") or "job_failed", "summary": summary})
                _record_run(conn, job_key, trigger_type, status, started, summary, "" if status == "OK" else str(summary.get("error") or summary.get("reason") or "job_failed"))
            except Exception as exc:
                error = str(exc)[:900]
                failed = {"job_key": job_key, "error": error}
                jobs_failed.append(failed)
                conn.execute(
                    "INSERT INTO automation_health_events(level, area, message, details_json, created_at) VALUES (?,?,?,?,?)",
                    ("ERROR", job_key, "V818 job failed", _json(failed), madrid_now().isoformat(timespec="seconds")),
                )
                _record_run(conn, job_key, trigger_type, "FAILED", started, failed, error)
        master_summary = {
            "due": due,
            "run": len(jobs_run),
            "skipped": len(jobs_skipped),
            "failed": len(jobs_failed),
            "telegram_sent": telegram_sent,
        }
        _mark_job_state(conn, "master_tick", "OK" if not jobs_failed else "PARTIAL", 0, "")
        conn.commit()
    if not env.get("AUTOMATION_SECRET"):
        warnings.append("AUTOMATION_SECRET no configurado en entorno.")
    return {
        "ok": not jobs_failed,
        "version": app_version,
        "madrid_now": now.isoformat(timespec="seconds"),
        "jobs_due": due,
        "jobs_run": jobs_run,
        "jobs_skipped": jobs_skipped,
        "jobs_failed": jobs_failed,
        "telegram_sent": telegram_sent,
        "api_calls_estimated": api_calls_estimated,
        "warnings": warnings,
        "next_recommended_run": next_recommended_run(now),
        "summary": master_summary,
        "dry_run": bool(dry_run),
    }
