"""NeMeSiS SHARK PRO - Observability Center V607.

Pequeño motor defensivo para registrar errores, rutas críticas y salud general sin
romper el arranque si alguna tabla antigua no existe todavía.
"""
from __future__ import annotations

import os
import platform
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_observability_schema(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observability_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'INFO',
                event_type TEXT NOT NULL,
                path TEXT,
                method TEXT,
                status_code INTEGER,
                message TEXT,
                detail TEXT,
                user_id TEXT,
                ip TEXT,
                user_agent TEXT,
                request_id TEXT,
                app_version TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observability_events_created ON observability_events(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observability_events_type ON observability_events(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observability_events_status ON observability_events(status_code)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observability_route_checks (
                route TEXT PRIMARY KEY,
                last_checked_at TEXT,
                status TEXT NOT NULL DEFAULT 'unknown',
                note TEXT
            )
            """
        )
        conn.commit()


def record_observability_event(
    db_path: str,
    *,
    level: str = "INFO",
    event_type: str = "event",
    path: str = "",
    method: str = "",
    status_code: Optional[int] = None,
    message: str = "",
    detail: str = "",
    user_id: str = "",
    ip: str = "",
    user_agent: str = "",
    request_id: str = "",
    app_version: str = "",
) -> bool:
    try:
        ensure_observability_schema(db_path)
        with _connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO observability_events
                (created_at, level, event_type, path, method, status_code, message, detail, user_id, ip, user_agent, request_id, app_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now(),
                    str(level or "INFO")[:20],
                    str(event_type or "event")[:80],
                    str(path or "")[:400],
                    str(method or "")[:20],
                    status_code,
                    str(message or "")[:1000],
                    str(detail or "")[:3000],
                    str(user_id or "")[:120],
                    str(ip or "")[:120],
                    str(user_agent or "")[:500],
                    str(request_id or "")[:120],
                    str(app_version or "")[:120],
                ),
            )
            conn.commit()
        return True
    except Exception:
        return False


def _count(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    try:
        row = conn.execute(sql, params).fetchone()
        return int(row[0] if row else 0)
    except Exception:
        return 0


def _latest_events(conn: sqlite3.Connection, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        rows = conn.execute(
            """
            SELECT created_at, level, event_type, path, method, status_code, message
            FROM observability_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return _count(conn, f"SELECT COUNT(*) FROM {table}")
    except Exception:
        return 0


def observability_summary(db_path: str, app_version: str = "") -> Dict[str, Any]:
    start = time.time()
    ensure_observability_schema(db_path)
    db_ok = False
    db_size_mb = 0.0
    latest_events: List[Dict[str, Any]] = []
    critical_last_24h = 0
    errors_total = 0
    not_found_total = 0
    warnings_total = 0
    routes_total = 0
    picks_total = 0
    queue_pending = 0
    queue_failed = 0

    try:
        if os.path.exists(db_path):
            db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        with _connect(db_path) as conn:
            conn.execute("SELECT 1").fetchone()
            db_ok = True
            latest_events = _latest_events(conn, limit=20)
            errors_total = _count(conn, "SELECT COUNT(*) FROM observability_events WHERE status_code >= 500 OR level IN ('ERROR','CRITICAL')")
            not_found_total = _count(conn, "SELECT COUNT(*) FROM observability_events WHERE status_code = 404")
            warnings_total = _count(conn, "SELECT COUNT(*) FROM observability_events WHERE level = 'WARNING'")
            critical_last_24h = _count(
                conn,
                """
                SELECT COUNT(*) FROM observability_events
                WHERE (status_code >= 500 OR level IN ('ERROR','CRITICAL'))
                AND datetime(created_at) >= datetime('now', '-1 day')
                """,
            )
            routes_total = _table_count(conn, "observability_route_checks")
            picks_total = _table_count(conn, "picks")
            queue_pending = _count(conn, "SELECT COUNT(*) FROM telegram_queue WHERE status IN ('pending','PENDING')")
            queue_failed = _count(conn, "SELECT COUNT(*) FROM telegram_queue WHERE status IN ('failed','FAILED')")
    except Exception as exc:
        latest_events = [{"created_at": utc_now(), "level": "ERROR", "event_type": "summary", "message": str(exc)[:300]}]

    health_score = 100
    if not db_ok:
        health_score -= 35
    if critical_last_24h:
        health_score -= min(30, critical_last_24h * 5)
    if queue_failed:
        health_score -= min(15, queue_failed)
    if db_size_mb > 900:
        health_score -= 10
    health_score = max(0, min(100, health_score))

    alerts = []
    if not db_ok:
        alerts.append("Base de datos no disponible.")
    if critical_last_24h:
        alerts.append(f"Hay {critical_last_24h} errores críticos en las últimas 24 horas.")
    if queue_failed:
        alerts.append(f"Telegram tiene {queue_failed} mensajes fallidos en cola.")
    if not alerts:
        alerts.append("Sin alertas críticas detectadas.")

    return {
        "ok": db_ok,
        "status": "OK" if health_score >= 85 else "REVISAR" if health_score >= 60 else "CRITICO",
        "health_score": health_score,
        "app_version": app_version,
        "db_path": db_path,
        "db_size_mb": db_size_mb,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "latency_ms": round((time.time() - start) * 1000, 2),
        "events_total": errors_total + not_found_total + warnings_total,
        "errors_total": errors_total,
        "not_found_total": not_found_total,
        "warnings_total": warnings_total,
        "critical_last_24h": critical_last_24h,
        "routes_checked": routes_total,
        "picks_total": picks_total,
        "telegram_queue_pending": queue_pending,
        "telegram_queue_failed": queue_failed,
        "alerts": alerts,
        "latest_events": latest_events,
    }


def mark_route_check(db_path: str, route: str, status: str = "ok", note: str = "") -> None:
    try:
        ensure_observability_schema(db_path)
        with _connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO observability_route_checks(route, last_checked_at, status, note)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(route) DO UPDATE SET
                    last_checked_at=excluded.last_checked_at,
                    status=excluded.status,
                    note=excluded.note
                """,
                (route, utc_now(), status, note[:500]),
            )
            conn.commit()
    except Exception:
        pass
