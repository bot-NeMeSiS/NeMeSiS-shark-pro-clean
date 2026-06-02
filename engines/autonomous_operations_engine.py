"""Autonomous Operations engine for NeMeSiS SHARK PRO.

V573 adds an operations memory on top of the scheduler: every automatic run is
stored, health is scored, and the admin gets clear next actions instead of
having to guess what failed or what should run next.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass
    return conn


def rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
    try:
        return [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
    except sqlite3.OperationalError:
        return []


def scalar(conn: sqlite3.Connection, query: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    try:
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            return default
        return list(dict(row).values())[0]
    except sqlite3.OperationalError:
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or default).replace(",", ".")))
    except Exception:
        return default


def stable_id(prefix: str, *parts: Any) -> str:
    raw = ":".join(str(p or "") for p in parts)
    return hashlib.sha1(f"{prefix}:{raw}".encode("utf-8")).hexdigest()[:24]


def dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:20000]


def ensure_autonomous_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS autonomous_runs(
        id TEXT PRIMARY KEY,
        run_group TEXT,
        task_name TEXT,
        status TEXT,
        ok INTEGER DEFAULT 0,
        processed INTEGER DEFAULT 0,
        inserted INTEGER DEFAULT 0,
        updated INTEGER DEFAULT 0,
        skipped INTEGER DEFAULT 0,
        errors_count INTEGER DEFAULT 0,
        payload_json TEXT,
        started_at TEXT,
        finished_at TEXT,
        created_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS autonomous_actions(
        id TEXT PRIMARY KEY,
        action_type TEXT,
        task_name TEXT,
        priority INTEGER DEFAULT 50,
        title TEXT,
        detail TEXT,
        status TEXT DEFAULT 'OPEN',
        payload_json TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS autonomous_daily_state(
        state_date TEXT PRIMARY KEY,
        health_score INTEGER DEFAULT 0,
        tasks_total INTEGER DEFAULT 0,
        tasks_ok INTEGER DEFAULT 0,
        tasks_error INTEGER DEFAULT 0,
        actions_open INTEGER DEFAULT 0,
        payload_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auto_runs_task_created ON autonomous_runs(task_name, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auto_runs_status_created ON autonomous_runs(status, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auto_actions_status_priority ON autonomous_actions(status, priority)")
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "autonomous_operations_v573"}


def record_autonomous_run(db_path: str, task_name: str, result: Dict[str, Any], run_group: str = "scheduler") -> Dict[str, Any]:
    ensure_autonomous_schema(db_path)
    now = utc_now()
    status = "OK" if result.get("ok") and not result.get("errors") else ("PARTIAL" if result.get("ok") else "ERROR")
    errors = result.get("errors") or []
    run_id = stable_id("auto-run", run_group, task_name, result.get("started_at"), result.get("finished_at"), now)
    conn = connect(db_path)
    conn.execute(
        """INSERT OR REPLACE INTO autonomous_runs
           (id,run_group,task_name,status,ok,processed,inserted,updated,skipped,errors_count,payload_json,started_at,finished_at,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run_id,
            run_group,
            task_name,
            status,
            1 if result.get("ok") else 0,
            as_int(result.get("processed")),
            as_int(result.get("inserted")),
            as_int(result.get("updated")),
            as_int(result.get("skipped")),
            len(errors),
            dumps(result),
            result.get("started_at") or now,
            result.get("finished_at") or now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "id": run_id, "status": status}


def upsert_action(conn: sqlite3.Connection, action_type: str, task_name: str, priority: int, title: str, detail: str, payload: Dict[str, Any] | None = None) -> None:
    action_id = stable_id("auto-action", action_type, task_name, title)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO autonomous_actions
           (id,action_type,task_name,priority,title,detail,status,payload_json,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,COALESCE((SELECT created_at FROM autonomous_actions WHERE id=?),?),?)""",
        (action_id, action_type, task_name, int(priority), title, detail, "OPEN", dumps(payload or {}), action_id, now, now),
    )


def generate_autonomous_actions(db_path: str, scheduler: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ensure_autonomous_schema(db_path)
    conn = connect(db_path)
    conn.execute("UPDATE autonomous_actions SET status='RESOLVED', updated_at=? WHERE status='OPEN'", (utc_now(),))
    tasks = (scheduler or {}).get("tasks") or []
    for task in tasks:
        status = str(task.get("status") or "PENDING").upper()
        name = task.get("name") or "unknown"
        label = task.get("label") or name
        if status in {"ERROR", "PARTIAL"}:
            upsert_action(conn, "repair", name, 95, f"Revisar {label}", task.get("error_message") or "La tarea no terminó limpia.", task)
        elif task.get("due"):
            upsert_action(conn, "run_due", name, 80, f"Ejecutar {label}", "La tarea está vencida y lista para ejecutarse.", task)
        elif status == "RUNNING":
            upsert_action(conn, "watch", name, 70, f"Vigilar {label}", "La tarea está en ejecución; confirmar que no queda bloqueada.", task)
    pending_telegram = scalar(conn, "SELECT COUNT(*) FROM telegram_queue WHERE status IN ('PENDING','RETRY')", default=0)
    if as_int(pending_telegram) > 0:
        upsert_action(conn, "telegram", "telegram", 88, "Procesar cola Telegram", f"Hay {pending_telegram} mensajes pendientes o en reintento.", {"pending": pending_telegram})
    stale_matches = scalar(conn, "SELECT COUNT(*) FROM matches", default=0)
    if as_int(stale_matches) == 0:
        upsert_action(conn, "data", "calendar", 100, "Sincronizar calendario inicial", "No hay partidos guardados todavía; el calendario necesita población.", {})
    open_actions = scalar(conn, "SELECT COUNT(*) FROM autonomous_actions WHERE status='OPEN'", default=0)
    conn.commit()
    conn.close()
    return {"ok": True, "open_actions": as_int(open_actions)}


def autonomous_summary(db_path: str, scheduler: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ensure_autonomous_schema(db_path)
    if scheduler:
        generate_autonomous_actions(db_path, scheduler=scheduler)
    conn = connect(db_path)
    recent_runs = rows(conn, "SELECT * FROM autonomous_runs ORDER BY created_at DESC LIMIT 20")
    actions = rows(conn, "SELECT * FROM autonomous_actions WHERE status='OPEN' ORDER BY priority DESC, updated_at DESC LIMIT 20")
    tasks_total = len((scheduler or {}).get("tasks") or []) or scalar(conn, "SELECT COUNT(DISTINCT task_name) FROM autonomous_runs", default=0)
    last_24 = rows(conn, "SELECT * FROM autonomous_runs WHERE created_at >= datetime('now','-1 day') ORDER BY created_at DESC LIMIT 200")
    ok_count = len([r for r in last_24 if as_int(r.get("ok")) == 1 and as_int(r.get("errors_count")) == 0])
    err_count = len([r for r in last_24 if as_int(r.get("ok")) == 0 or as_int(r.get("errors_count")) > 0])
    pending_telegram = scalar(conn, "SELECT COUNT(*) FROM telegram_queue WHERE status IN ('PENDING','RETRY')", default=0)
    matches_total = scalar(conn, "SELECT COUNT(*) FROM matches", default=0)
    picks_total = scalar(conn, "SELECT COUNT(*) FROM picks", default=0)
    warehouse_days = scalar(conn, "SELECT COUNT(*) FROM warehouse_daily_metrics", default=0)
    base = 55
    base += min(15, as_int(matches_total) // 10)
    base += min(10, as_int(picks_total) * 2)
    base += min(10, as_int(warehouse_days) * 2)
    base += min(10, ok_count)
    base -= min(25, err_count * 5)
    base -= min(10, len(actions) * 2)
    health_score = max(0, min(100, base))
    state_date = utc_now()[:10]
    conn.execute(
        """INSERT OR REPLACE INTO autonomous_daily_state
           (state_date,health_score,tasks_total,tasks_ok,tasks_error,actions_open,payload_json,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (state_date, health_score, as_int(tasks_total), ok_count, err_count, len(actions), dumps({"telegram_pending": pending_telegram}), utc_now()),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "version": "V573_AUTONOMOUS_OPERATIONS",
        "health_score": health_score,
        "status": "Autónomo estable" if health_score >= 80 else ("Autónomo vigilado" if health_score >= 60 else "Necesita datos/acciones"),
        "tasks_total": as_int(tasks_total),
        "runs_24h": len(last_24),
        "tasks_ok_24h": ok_count,
        "tasks_error_24h": err_count,
        "actions_open": len(actions),
        "telegram_pending": as_int(pending_telegram),
        "matches_total": as_int(matches_total),
        "picks_total": as_int(picks_total),
        "warehouse_days": as_int(warehouse_days),
        "actions": actions,
        "recent_runs": recent_runs,
    }
