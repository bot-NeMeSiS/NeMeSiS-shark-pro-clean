"""V773 privacy-first commercial data marketplace utilities.

This module only reads the existing SQLite data. It never invents sport data,
never exports personal identifiers and logs export audits without storing CSV
content.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

MADRID_TZ = ZoneInfo("Europe/Madrid")

SENSITIVE_COLUMNS = {
    "email", "password", "password_hash", "telegram_id", "telegram_chat_id",
    "chat_id", "ip", "ip_address", "session", "session_id", "token", "secret",
    "user_id", "customer_id", "admin_id", "stripe_customer_id", "stripe_subscription_id",
    "reset_token", "api_key", "bot_token",
}

EXPORTS = {
    "closed-picks": {
        "label": "Picks cerrados",
        "format": "csv",
        "description": "Picks auditables con mercado, cuota, resultado y ROI cuando existan columnas reales.",
    },
    "market-performance": {
        "label": "Rendimiento por mercado",
        "format": "csv",
        "description": "Agregado por mercado sin datos personales.",
    },
    "league-performance": {
        "label": "Rendimiento por liga",
        "format": "csv",
        "description": "Agregado por competición/liga sin datos personales.",
    },
    "trends": {
        "label": "Tendencias",
        "format": "csv",
        "description": "Evolución diaria de picks cerrados y señales disponibles.",
    },
    "highlights": {
        "label": "Highlights",
        "format": "csv",
        "description": "Metadatos de resúmenes disponibles, sin descargar ni rehostear vídeo.",
    },
    "monthly-report": {
        "label": "Informe mensual JSON",
        "format": "json",
        "description": "Resumen ejecutivo mensual con tablas agregadas y privacidad aplicada.",
    },
}

PREFERRED_PICK_COLUMNS = [
    "id", "match_id", "home_team", "away_team", "competition_name", "league_name", "competition",
    "market", "pick_type", "selection", "recommendation", "odds", "stake", "stake_units",
    "confidence", "shark_score", "score", "risk", "risk_level", "status", "result_status",
    "profit", "roi", "created_at", "updated_at", "kickoff_time", "commence_time", "match_date",
]

PREFERRED_HIGHLIGHT_COLUMNS = [
    "id", "match_id", "home_team", "away_team", "competition_name", "league_name", "title",
    "source", "original_url", "embed_url", "thumbnail_url", "published_at", "created_at", "updated_at",
]

CLOSED_STATUS_TOKENS = {"won", "lost", "void", "push", "closed", "graded", "resolved", "settled", "final", "finished", "win", "loss", "ganado", "perdido", "nulo"}


def madrid_now_iso() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def _connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _db_exists(db_path: str) -> bool:
    return bool(db_path) and os.path.exists(db_path)


def _tables(conn) -> list[str]:
    try:
        return [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    except Exception:
        return []


def _columns(conn, table: str) -> list[str]:
    try:
        return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def _safe_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if c.lower() not in SENSITIVE_COLUMNS and not any(marker in c.lower() for marker in ("password", "secret", "token", "chat_id", "telegram_id", "session"))]


def privacy_guard_export(columns: list[str]) -> dict:
    blocked = [c for c in columns if c.lower() not in {x.lower() for x in _safe_columns(columns)}]
    return {
        "ok": not blocked,
        "blocked_columns": blocked,
        "policy": "No se exportan emails, passwords, telegram/chat IDs, IPs, sesiones, tokens, secrets ni IDs personales.",
    }


def ensure_data_export_audit_schema(db_path: str) -> None:
    if not _db_exists(db_path):
        return
    conn = _connect(db_path)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS data_export_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_key TEXT,
                actor TEXT,
                status TEXT,
                row_count INTEGER DEFAULT 0,
                blocked_columns TEXT,
                created_at_madrid TEXT,
                created_at_utc TEXT
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def log_export_audit(db_path: str, export_key: str, actor: str, status: str, row_count: int = 0, blocked_columns=None) -> None:
    if not _db_exists(db_path):
        return
    ensure_data_export_audit_schema(db_path)
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO data_export_audit (export_key, actor, status, row_count, blocked_columns, created_at_madrid, created_at_utc) VALUES (?,?,?,?,?,?,?)",
            (
                str(export_key or ""),
                str(actor or "admin")[:120],
                str(status or "")[:80],
                int(row_count or 0),
                json.dumps(blocked_columns or [], ensure_ascii=False),
                madrid_now_iso(),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _rowdicts(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]


def _first_existing(columns: list[str], options: list[str], fallback: str = "") -> str:
    lower = {c.lower(): c for c in columns}
    for option in options:
        if option.lower() in lower:
            return lower[option.lower()]
    return fallback


def _select_rows(conn, table: str, preferred: list[str], limit: int) -> tuple[list[dict], list[str]]:
    cols = _columns(conn, table)
    safe = _safe_columns(cols)
    selected = [c for c in preferred if c in safe]
    if not selected:
        selected = safe[:18]
    if not selected:
        return [], []
    order_col = _first_existing(cols, ["updated_at", "created_at", "match_date", "id"], selected[0])
    sql = f"SELECT {', '.join(selected)} FROM {table} ORDER BY {order_col} DESC LIMIT ?"
    return _rowdicts(conn.execute(sql, (int(limit or 5000),))), selected


def _is_closed(row: dict) -> bool:
    status = " ".join(str(row.get(k) or "") for k in ("status", "result_status", "pick_status", "grading_status")).lower()
    if not status.strip():
        return False
    return any(token in status for token in CLOSED_STATUS_TOKENS)


def _profit(row: dict) -> float:
    for key in ("profit", "pnl", "net_profit"):
        try:
            if row.get(key) not in (None, ""):
                return float(row.get(key))
        except Exception:
            pass
    return 0.0


def _odds(row: dict) -> float:
    try:
        return float(row.get("odds") or row.get("odds_value") or 0)
    except Exception:
        return 0.0


def _market(row: dict) -> str:
    return str(row.get("market") or row.get("pick_type") or "Mercado pendiente").strip() or "Mercado pendiente"


def _league(row: dict) -> str:
    return str(row.get("competition_name") or row.get("league_name") or row.get("competition") or "Competición pendiente").strip() or "Competición pendiente"


def _status_bucket(row: dict) -> str:
    status = str(row.get("result_status") or row.get("status") or "pendiente").lower()
    if any(x in status for x in ("won", "win", "ganado")):
        return "ganado"
    if any(x in status for x in ("lost", "loss", "perdido")):
        return "perdido"
    if any(x in status for x in ("void", "push", "nulo")):
        return "nulo"
    return status or "pendiente"


def _csv(rows: list[dict], columns: list[str] | None = None) -> str:
    columns = columns or sorted({k for row in rows for k in row.keys()})
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in columns})
    return output.getvalue()


def _closed_pick_rows(conn, limit: int) -> tuple[list[dict], list[str]]:
    tables = _tables(conn)
    if "picks" not in tables:
        return [], []
    rows, cols = _select_rows(conn, "picks", PREFERRED_PICK_COLUMNS, limit)
    closed = [r for r in rows if _is_closed(r)]
    return closed if closed else rows, cols


def _aggregate(rows: list[dict], key_fn) -> list[dict]:
    groups: dict[str, dict] = defaultdict(lambda: {"total": 0, "ganados": 0, "perdidos": 0, "nulos": 0, "profit": 0.0, "odds_sum": 0.0, "odds_count": 0})
    for row in rows:
        key = key_fn(row)
        g = groups[key]
        g["total"] += 1
        bucket = _status_bucket(row)
        if bucket == "ganado":
            g["ganados"] += 1
        elif bucket == "perdido":
            g["perdidos"] += 1
        elif bucket == "nulo":
            g["nulos"] += 1
        g["profit"] += _profit(row)
        odd = _odds(row)
        if odd:
            g["odds_sum"] += odd
            g["odds_count"] += 1
    output = []
    for key, g in sorted(groups.items(), key=lambda kv: (kv[1]["total"], kv[1]["profit"]), reverse=True):
        winrate = round((g["ganados"] / max(1, g["ganados"] + g["perdidos"])) * 100, 2)
        output.append({
            "segmento": key,
            "picks": g["total"],
            "ganados": g["ganados"],
            "perdidos": g["perdidos"],
            "nulos": g["nulos"],
            "winrate_pct": winrate,
            "profit": round(g["profit"], 2),
            "cuota_media": round(g["odds_sum"] / max(1, g["odds_count"]), 2) if g["odds_count"] else "",
        })
    return output


def _trends(rows: list[dict]) -> list[dict]:
    groups = defaultdict(lambda: {"total": 0, "ganados": 0, "perdidos": 0, "profit": 0.0})
    for row in rows:
        raw = str(row.get("created_at") or row.get("updated_at") or row.get("match_date") or "sin_fecha")[:10]
        g = groups[raw]
        g["total"] += 1
        if _status_bucket(row) == "ganado":
            g["ganados"] += 1
        elif _status_bucket(row) == "perdido":
            g["perdidos"] += 1
        g["profit"] += _profit(row)
    return [{"fecha": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}} for k, v in sorted(groups.items(), reverse=True)]


def _highlights_rows(conn, limit: int) -> tuple[list[dict], list[str]]:
    tables = _tables(conn)
    table = "sportsdb_highlights" if "sportsdb_highlights" in tables else ("highlights" if "highlights" in tables else "")
    if not table:
        return [], []
    return _select_rows(conn, table, PREFERRED_HIGHLIGHT_COLUMNS, limit)


def build_data_marketplace_summary(db_path: str, app_version: str = "") -> dict:
    summary = {
        "version": app_version,
        "enabled": os.getenv("DATA_MARKETPLACE_ENABLED", "true").lower() not in {"0", "false", "no", "off"},
        "db_exists": _db_exists(db_path),
        "db_path_masked": (db_path.replace(os.path.expanduser("~"), "~") if db_path else ""),
        "generated_at_madrid": madrid_now_iso(),
        "exports": [],
        "privacy": {
            "protected_columns": sorted(SENSITIVE_COLUMNS),
            "policy": "Exportaciones agregadas y client-safe. No salen datos personales ni secrets.",
        },
        "counts": {},
        "readiness_score": 0,
        "warnings": [],
    }
    if not summary["db_exists"]:
        summary["warnings"].append("No existe DB_PATH en este entorno; en Render debe apuntar al disco persistente.")
        return summary
    limit = int(os.getenv("DATA_MARKETPLACE_EXPORT_MAX_ROWS", "5000") or 5000)
    conn = _connect(db_path)
    try:
        tables = _tables(conn)
        summary["tables"] = tables
        for table in tables:
            try:
                summary["counts"][table] = int(conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()["total"])
            except Exception:
                pass
        pick_rows, pick_cols = _closed_pick_rows(conn, min(limit, 800))
        highlight_rows, _ = _highlights_rows(conn, min(limit, 800))
        exports = []
        for key, cfg in EXPORTS.items():
            available = True
            rows_estimate = len(pick_rows)
            if key == "highlights":
                rows_estimate = len(highlight_rows)
                available = bool(highlight_rows)
            elif key != "monthly-report":
                available = bool(pick_rows)
            exports.append({"key": key, **cfg, "available": available, "rows_estimate": rows_estimate})
        summary["exports"] = exports
        privacy_probe = privacy_guard_export(pick_cols)
        summary["privacy"]["last_probe_ok"] = privacy_probe.get("ok")
        summary["privacy"]["blocked_in_pick_columns"] = privacy_probe.get("blocked_columns")
        score = 55
        score += 10 if "picks" in tables else 0
        score += 8 if pick_rows else 0
        score += 8 if highlight_rows else 0
        score += 7 if "data_export_audit" in tables else 0
        score += 7 if privacy_probe.get("ok") else 0
        summary["readiness_score"] = min(100, score)
    finally:
        conn.close()
    return summary


def run_data_marketplace_export(db_path: str, export_key: str, fmt: str = "csv", actor: str = "admin", app_version: str = "") -> dict:
    key = str(export_key or "").strip().lower().replace("_", "-")
    if key not in EXPORTS:
        return {"ok": False, "error": "EXPORT_NOT_FOUND", "message": "Exportación no reconocida.", "available_exports": sorted(EXPORTS)}
    if not _db_exists(db_path):
        return {"ok": False, "error": "DB_MISSING", "message": "No existe DB_PATH en este entorno."}
    if os.getenv("DATA_MARKETPLACE_ENABLED", "true").lower() in {"0", "false", "no", "off"}:
        return {"ok": False, "error": "DATA_MARKETPLACE_DISABLED", "message": "DATA_MARKETPLACE_ENABLED no está activo."}
    limit = int(os.getenv("DATA_MARKETPLACE_EXPORT_MAX_ROWS", "5000") or 5000)
    generated = madrid_now_iso()
    conn = _connect(db_path)
    try:
        if key in {"closed-picks", "market-performance", "league-performance", "trends", "monthly-report"}:
            pick_rows, pick_cols = _closed_pick_rows(conn, limit)
            guard = privacy_guard_export(pick_cols)
            if not guard.get("ok"):
                log_export_audit(db_path, key, actor, "BLOCKED", 0, guard.get("blocked_columns"))
                return {"ok": False, "error": "PRIVACY_GUARD_BLOCKED", **guard}
            if key == "closed-picks":
                rows = pick_rows
                columns = pick_cols
            elif key == "market-performance":
                rows = _aggregate(pick_rows, _market)
                columns = ["segmento", "picks", "ganados", "perdidos", "nulos", "winrate_pct", "profit", "cuota_media"]
            elif key == "league-performance":
                rows = _aggregate(pick_rows, _league)
                columns = ["segmento", "picks", "ganados", "perdidos", "nulos", "winrate_pct", "profit", "cuota_media"]
            elif key == "trends":
                rows = _trends(pick_rows)
                columns = ["fecha", "total", "ganados", "perdidos", "profit"]
            else:
                rows = []
                data = {
                    "version": app_version,
                    "generated_at_madrid": generated,
                    "closed_picks": len(pick_rows),
                    "market_performance": _aggregate(pick_rows, _market)[:20],
                    "league_performance": _aggregate(pick_rows, _league)[:20],
                    "trends": _trends(pick_rows)[:40],
                    "privacy": "Sin datos personales exportados.",
                }
                log_export_audit(db_path, key, actor, "OK", len(pick_rows), [])
                return {"ok": True, "key": key, "format": "json", "generated_at_madrid": generated, "data": data}
        elif key == "highlights":
            rows, columns = _highlights_rows(conn, limit)
            guard = privacy_guard_export(columns)
            if not guard.get("ok"):
                log_export_audit(db_path, key, actor, "BLOCKED", 0, guard.get("blocked_columns"))
                return {"ok": False, "error": "PRIVACY_GUARD_BLOCKED", **guard}
        else:
            rows, columns = [], []
    finally:
        conn.close()
    if fmt == "json" or EXPORTS[key].get("format") == "json":
        log_export_audit(db_path, key, actor, "OK", len(rows), [])
        return {"ok": True, "key": key, "format": "json", "generated_at_madrid": generated, "data": rows}
    content = _csv(rows, columns)
    log_export_audit(db_path, key, actor, "OK", len(rows), [])
    filename = f"nemesis_{key}_{datetime.now(MADRID_TZ).strftime('%Y%m%d_%H%M')}.csv"
    return {"ok": True, "key": key, "format": "csv", "filename": filename, "row_count": len(rows), "generated_at_madrid": generated, "content": content}
