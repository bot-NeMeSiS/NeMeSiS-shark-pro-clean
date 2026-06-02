"""Commercial Launch Preparation engine for NeMeSiS SHARK PRO.

V574 does not add a heavy new module. It adds a compact commercial readiness
layer so the admin can see if the product is ready to sell: pricing, conversion,
member mix, launch blockers, trust/compliance basics and monetisation signals.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


DEFAULT_PRICING = {
    "FREE": {"price": 0, "label": "Gratis", "headline": "Calendario, live básico y favoritos"},
    "PRO": {"price": 19.99, "label": "PRO", "headline": "Picks PRO, SHARK recomendado y Telegram PRO"},
    "ELITE": {"price": 49.99, "label": "ELITE", "headline": "SHARK completo, auto picks, combinadas y prioridad"},
}


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
        return int(float(str(value if value is not None else default).replace(",", ".")))
    except Exception:
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value if value is not None else default).replace(",", "."))
    except Exception:
        return default


def dumps(payload: Any) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, default=str)[:20000]


def ensure_commercial_schema(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS commercial_settings(
        key TEXT PRIMARY KEY,
        value_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS commercial_launch_checks(
        id TEXT PRIMARY KEY,
        area TEXT,
        title TEXT,
        detail TEXT,
        status TEXT,
        priority INTEGER DEFAULT 50,
        payload_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS commercial_daily_metrics(
        metric_date TEXT PRIMARY KEY,
        readiness_score INTEGER DEFAULT 0,
        users_total INTEGER DEFAULT 0,
        paid_users INTEGER DEFAULT 0,
        estimated_mrr REAL DEFAULT 0,
        conversion_rate REAL DEFAULT 0,
        payload_json TEXT,
        updated_at TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_commercial_checks_status ON commercial_launch_checks(status, priority)")
    cur.execute(
        "INSERT OR IGNORE INTO commercial_settings(key,value_json,updated_at) VALUES (?,?,?)",
        ("pricing", dumps(DEFAULT_PRICING), utc_now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "schema": "commercial_launch_v574"}


def _pricing(conn: sqlite3.Connection) -> Dict[str, Any]:
    raw = scalar(conn, "SELECT value_json FROM commercial_settings WHERE key='pricing'", default="")
    try:
        parsed = json.loads(raw or "{}")
        if isinstance(parsed, dict) and parsed:
            return parsed
    except Exception:
        pass
    return DEFAULT_PRICING


def _membership_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    result = {"FREE": 0, "PRO": 0, "ELITE": 0, "ADMIN": 0}
    for row in rows(conn, "SELECT UPPER(COALESCE(membership, role, 'FREE')) AS tier, COUNT(*) AS total FROM users GROUP BY UPPER(COALESCE(membership, role, 'FREE'))"):
        tier = str(row.get("tier") or "FREE").upper()
        if tier not in result:
            tier = "FREE"
        result[tier] += as_int(row.get("total"))
    return result


def _upsert_check(conn: sqlite3.Connection, area: str, title: str, detail: str, status: str, priority: int, payload: Dict[str, Any] | None = None) -> None:
    check_id = f"{area.lower().replace(' ', '_')}:{title.lower().replace(' ', '_')[:80]}"
    conn.execute(
        """INSERT OR REPLACE INTO commercial_launch_checks
           (id,area,title,detail,status,priority,payload_json,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (check_id, area, title, detail, status, int(priority), dumps(payload or {}), utc_now()),
    )


def rebuild_launch_checks(db_path: str) -> Dict[str, Any]:
    ensure_commercial_schema(db_path)
    conn = connect(db_path)
    conn.execute("DELETE FROM commercial_launch_checks")
    pricing = _pricing(conn)
    users_total = as_int(scalar(conn, "SELECT COUNT(*) FROM users", default=0))
    matches_total = as_int(scalar(conn, "SELECT COUNT(*) FROM matches", default=0))
    picks_total = as_int(scalar(conn, "SELECT COUNT(*) FROM picks", default=0))
    odds_total = as_int(scalar(conn, "SELECT COUNT(*) FROM odds_snapshots", default=0))
    telegram_settings = as_int(scalar(conn, "SELECT COUNT(*) FROM telegram_settings WHERE enabled=1", default=0))
    warehouse_days = as_int(scalar(conn, "SELECT COUNT(*) FROM warehouse_daily_metrics", default=0))
    auto_runs = as_int(scalar(conn, "SELECT COUNT(*) FROM autonomous_runs WHERE created_at >= datetime('now','-1 day')", default=0))

    _upsert_check(conn, "Producto", "Membresías visibles", "FREE/PRO/ELITE están definidas para empaquetar el producto comercial.", "OK", 20, pricing)
    _upsert_check(conn, "Producto", "Usuarios registrados", f"Hay {users_total} usuarios guardados en SQLite persistente.", "OK" if users_total > 0 else "PENDING", 75)
    _upsert_check(conn, "Datos", "Partidos guardados", f"Partidos en base: {matches_total}.", "OK" if matches_total >= 20 else "PENDING", 90)
    _upsert_check(conn, "Datos", "Cuotas integradas", f"Snapshots de cuotas: {odds_total}.", "OK" if odds_total > 0 else "PENDING", 85)
    _upsert_check(conn, "Picks", "Picks comerciales", f"Picks disponibles: {picks_total}.", "OK" if picks_total > 0 else "PENDING", 82)
    _upsert_check(conn, "Automatización", "Ciclos autónomos", f"Runs últimas 24h: {auto_runs}.", "OK" if auto_runs > 0 else "PENDING", 78)
    _upsert_check(conn, "Warehouse", "Histórico activo", f"Días de métricas históricas: {warehouse_days}.", "OK" if warehouse_days > 0 else "PENDING", 74)
    _upsert_check(conn, "Telegram", "Telegram comercial", "Cola y ajustes Telegram listos para enviar valor por membresía.", "OK" if telegram_settings > 0 else "PENDING", 80)
    _upsert_check(conn, "Pagos", "Stripe pendiente", "Preparado para lanzamiento manual/beta. Stripe queda como siguiente integración real cuando decidas activar cobros.", "PENDING", 65)
    _upsert_check(conn, "Confianza", "Apuesta responsable", "Mantener textos claros: no prometer beneficios, mostrar riesgo, stake y responsabilidad.", "OK", 45)
    conn.commit()
    total = as_int(scalar(conn, "SELECT COUNT(*) FROM commercial_launch_checks", default=0))
    pending = as_int(scalar(conn, "SELECT COUNT(*) FROM commercial_launch_checks WHERE status!='OK'", default=0))
    conn.close()
    return {"ok": True, "checks_total": total, "checks_pending": pending}


def commercial_summary(db_path: str, rebuild: bool = True) -> Dict[str, Any]:
    ensure_commercial_schema(db_path)
    if rebuild:
        rebuild_launch_checks(db_path)
    conn = connect(db_path)
    pricing = _pricing(conn)
    counts = _membership_counts(conn)
    users_total = sum(counts.values())
    paid_users = counts.get("PRO", 0) + counts.get("ELITE", 0)
    pro_price = as_float((pricing.get("PRO") or {}).get("price"), 19.99)
    elite_price = as_float((pricing.get("ELITE") or {}).get("price"), 49.99)
    estimated_mrr = round(counts.get("PRO", 0) * pro_price + counts.get("ELITE", 0) * elite_price, 2)
    conversion_rate = round((paid_users / users_total) * 100, 1) if users_total else 0.0
    checks = rows(conn, "SELECT * FROM commercial_launch_checks ORDER BY status DESC, priority DESC LIMIT 30")
    total_checks = len(checks) or as_int(scalar(conn, "SELECT COUNT(*) FROM commercial_launch_checks", default=0))
    ok_checks = len([c for c in checks if str(c.get("status") or "").upper() == "OK"])
    readiness = 45
    readiness += min(15, as_int(scalar(conn, "SELECT COUNT(*) FROM matches", default=0)) // 20)
    readiness += min(10, as_int(scalar(conn, "SELECT COUNT(*) FROM picks", default=0)) * 2)
    readiness += min(10, as_int(scalar(conn, "SELECT COUNT(*) FROM odds_snapshots", default=0)) // 5)
    readiness += min(10, as_int(scalar(conn, "SELECT COUNT(*) FROM warehouse_daily_metrics", default=0)) * 4)
    readiness += min(10, as_int(scalar(conn, "SELECT COUNT(*) FROM autonomous_runs", default=0)) * 2)
    readiness -= min(15, len([c for c in checks if str(c.get("status") or "").upper() != "OK"]) * 2)
    readiness = max(0, min(100, readiness))
    today = utc_now()[:10]
    conn.execute(
        """INSERT OR REPLACE INTO commercial_daily_metrics
           (metric_date,readiness_score,users_total,paid_users,estimated_mrr,conversion_rate,payload_json,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (today, readiness, users_total, paid_users, estimated_mrr, conversion_rate, dumps({"counts": counts}), utc_now()),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "version": "V574_COMMERCIAL_LAUNCH_PREPARATION",
        "readiness_score": readiness,
        "status": "Listo para beta comercial" if readiness >= 80 else ("Preparación comercial avanzada" if readiness >= 65 else "Necesita más datos antes de vender fuerte"),
        "pricing": pricing,
        "membership_counts": counts,
        "users_total": users_total,
        "paid_users": paid_users,
        "estimated_mrr": estimated_mrr,
        "conversion_rate": conversion_rate,
        "checks_total": total_checks,
        "checks_ok": ok_checks,
        "checks_pending": max(0, total_checks - ok_checks),
        "checks": checks,
    }
