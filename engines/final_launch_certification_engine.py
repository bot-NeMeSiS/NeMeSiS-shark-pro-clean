"""V768 final launch certification helpers for NeMeSiS SHARK PRO.

This module is intentionally read-only apart from optional calls made elsewhere.
It summarizes the exact commercial blockers Damian needs to watch before selling:
Telegram automation, pick results/ROI, sports data richness and client clarity.
No secrets are returned and no Telegram messages are sent from here.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable

try:
    from engines.pick_grading_engine import ensure_pick_grading_schema, pick_grading_summary
except Exception:  # pragma: no cover
    ensure_pick_grading_schema = None
    pick_grading_summary = None


MADRID_NOTE = "Todo horario visible debe pasar por Europe/Madrid antes de mostrarse."


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
    except sqlite3.OperationalError:
        pass
    return conn


def _rows(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> list[dict]:
    try:
        return [dict(r) for r in conn.execute(query, tuple(params)).fetchall()]
    except sqlite3.OperationalError:
        return []


def _one(conn: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> dict:
    rows = _rows(conn, query, params)
    return rows[0] if rows else {}


def _count(conn: sqlite3.Connection, table: str, where: str = "1=1", params: Iterable[Any] = ()) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) AS total FROM {table} WHERE {where}", tuple(params)).fetchone()
        return int((dict(row or {}).get("total") or 0))
    except Exception:
        return 0


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
    except Exception:
        return False


def _env_bool(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _env_present(name: str) -> bool:
    return bool(str(os.getenv(name, "")).strip())


def _safe_ts(value: Any) -> str:
    return str(value or "").replace("T", " ")[:19]


def _json_loads(value: Any) -> dict:
    try:
        data = json.loads(value or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def telegram_certification_snapshot(conn: sqlite3.Connection) -> Dict[str, Any]:
    env = {
        "bot_token": _env_present("TELEGRAM_BOT_TOKEN"),
        "chat_id": _env_present("TELEGRAM_CHAT_ID"),
        "automation_secret": _env_present("AUTOMATION_SECRET"),
        "enable_auto": any(_env_bool(k) for k in ("ENABLE_TELEGRAM_AUTO", "AUTO_SEND_TELEGRAM_PICKS", "ENABLE_TELEGRAM_AUTOMATION", "TELEGRAM_AUTO_SEND_ENABLED")),
    }
    queue_total = _count(conn, "telegram_queue") if _table_exists(conn, "telegram_queue") else 0
    queue_sent = _count(conn, "telegram_queue", "lower(COALESCE(status,''))='sent'") if _table_exists(conn, "telegram_queue") else 0
    auto_queue_sent = _count(conn, "telegram_queue", "lower(COALESCE(status,''))='sent' AND lower(COALESCE(source,'')) LIKE '%automatic%'") if _table_exists(conn, "telegram_queue") else 0
    delivery_total = _count(conn, "telegram_deliveries") if _table_exists(conn, "telegram_deliveries") else 0
    delivery_sent = _count(conn, "telegram_deliveries", "lower(COALESCE(status,'')) IN ('sent','ok','success')") if _table_exists(conn, "telegram_deliveries") else 0
    last_log = _one(conn, "SELECT * FROM telegram_logs ORDER BY created_at DESC LIMIT 1") if _table_exists(conn, "telegram_logs") else {}
    last_auto = {}
    if _table_exists(conn, "telegram_queue"):
        last_auto = _one(conn, """SELECT * FROM telegram_queue
                                  WHERE lower(COALESCE(source,'')) LIKE '%automatic%'
                                  ORDER BY COALESCE(sent_at,created_at) DESC LIMIT 1""")
    published_candidates = _count(conn, "picks", "lower(COALESCE(status,'')) IN ('published','telegram_test')") if _table_exists(conn, "picks") else 0
    sendable_hint = _count(conn, "picks", "lower(COALESCE(status,'')) IN ('published','telegram_test') AND COALESCE(match_id,'')!='' AND COALESCE(selection,'')!=''") if _table_exists(conn, "picks") else 0
    ready = all(env.values()) and (published_candidates > 0 or queue_sent > 0 or delivery_sent > 0)
    return {
        "title": "Telegram automático",
        "status": "CERTIFICABLE" if ready else "REVISAR EN RENDER",
        "ready_score": round(100 * sum(1 for v in env.values() if v) / max(1, len(env))),
        "env": env,
        "queue_total": queue_total,
        "queue_sent": queue_sent,
        "auto_queue_sent": auto_queue_sent,
        "deliveries": {"total": delivery_total, "sent": delivery_sent},
        "published_candidates": published_candidates,
        "sendable_hint": sendable_hint,
        "last_log": {"status": last_log.get("status"), "message": last_log.get("message"), "created_at": _safe_ts(last_log.get("created_at"))},
        "last_auto": {"status": last_auto.get("status"), "source": last_auto.get("source"), "sent_at": _safe_ts(last_auto.get("sent_at") or last_auto.get("created_at"))},
        "next_action": "Si no envía solo, revisar /api/admin/telegram/auto-candidates y logs del Cron Render." if not ready else "Mantener Cron activo y vigilar duplicados/destino.",
    }


def track_record_certification_snapshot(db_path: str, conn: sqlite3.Connection) -> Dict[str, Any]:
    if ensure_pick_grading_schema:
        ensure_pick_grading_schema(db_path)
    summary = dict(pick_grading_summary(db_path) if pick_grading_summary else {})
    won = int(summary.get("won") or 0)
    lost = int(summary.get("lost") or 0)
    pending = int(summary.get("pending_review") or 0)
    auto_validated = int(summary.get("auto_validated") or 0)
    graded = int(summary.get("graded_total") or 0)
    decided = won + lost
    picks_total = _count(conn, "picks") if _table_exists(conn, "picks") else 0
    finished_matches = _count(conn, "matches", "lower(COALESCE(status,'')) LIKE '%final%' OR lower(COALESCE(status,'')) LIKE '%finish%' OR lower(COALESCE(status,'')) LIKE '%complete%'") if _table_exists(conn, "matches") else 0
    final_with_score = _count(conn, "matches", "(COALESCE(score,'')!='' OR (COALESCE(home_score,'')!='' AND COALESCE(away_score,'')!='')) AND (lower(COALESCE(status,'')) LIKE '%final%' OR lower(COALESCE(status,'')) LIKE '%finish%' OR lower(COALESCE(status,'')) LIKE '%complete%')") if _table_exists(conn, "matches") else 0
    if decided > 0:
        status = "ROI REAL ACTIVO"
    elif graded > 0:
        status = "AUDITORÍA ACTIVA"
    elif picks_total > 0:
        status = "PENDIENTE DE RESULTADOS"
    else:
        status = "SIN PICKS"
    return {
        "title": "Pick → Resultado → ROI",
        "status": status,
        "picks_total": picks_total,
        "graded_total": graded,
        "auto_validated": auto_validated,
        "won": won,
        "lost": lost,
        "pending_review": pending,
        "finished_matches": finished_matches,
        "final_with_score": final_with_score,
        "profit": summary.get("profit") or 0,
        "readiness_score": summary.get("readiness_score") or 0,
        "recent_results": summary.get("recent_results") or [],
        "next_action": "Ejecutar /api/automation/picks/grade con AUTOMATION_SECRET tras sincronizar resultados." if decided == 0 else "Mostrar histórico/ROI solo con resultados reales.",
    }


def data_richness_snapshot(conn: sqlite3.Connection) -> Dict[str, Any]:
    matches_total = _count(conn, "matches") if _table_exists(conn, "matches") else 0
    with_time = _count(conn, "matches", "COALESCE(kickoff_iso,kickoff_time,match_time,'')!=''") if _table_exists(conn, "matches") else 0
    with_score = _count(conn, "matches", "COALESCE(score,'')!='' OR (COALESCE(home_score,'')!='' AND COALESCE(away_score,'')!='')") if _table_exists(conn, "matches") else 0
    with_logos = _count(conn, "matches", "COALESCE(home_logo,'')!='' AND COALESCE(away_logo,'')!=''") if _table_exists(conn, "matches") else 0
    live_now = _count(conn, "matches", "lower(COALESCE(status,'')) LIKE '%live%' OR lower(COALESCE(status,'')) LIKE '%inplay%' OR lower(COALESCE(status,'')) LIKE '%1h%' OR lower(COALESCE(status,'')) LIKE '%2h%'") if _table_exists(conn, "matches") else 0
    highlights_total = _count(conn, "match_highlights") if _table_exists(conn, "match_highlights") else _count(conn, "sportsdb_highlights")
    score = 0
    if matches_total:
        score += min(25, round(25 * with_time / matches_total))
        score += min(25, round(25 * with_score / matches_total))
        score += min(25, round(25 * with_logos / matches_total))
    if highlights_total:
        score += 25
    return {
        "title": "Datos deportivos visibles",
        "status": "RICO" if score >= 70 else "MEJORABLE" if matches_total else "SIN DATOS",
        "score": score,
        "matches_total": matches_total,
        "with_time": with_time,
        "with_score": with_score,
        "with_logos": with_logos,
        "live_now": live_now,
        "highlights_total": highlights_total,
        "next_action": "Mantener sync diario de calendario/live/highlights; no inventar escudos/resultados si la API no los trae.",
    }


def commercial_launch_snapshot(db_path: str, app_version: str = "") -> Dict[str, Any]:
    conn = _connect(db_path)
    try:
        telegram = telegram_certification_snapshot(conn)
        track = track_record_certification_snapshot(db_path, conn)
        data = data_richness_snapshot(conn)
        checks = [
            telegram.get("env", {}).get("bot_token"),
            telegram.get("env", {}).get("chat_id"),
            telegram.get("env", {}).get("automation_secret"),
            track.get("picks_total", 0) > 0,
            track.get("graded_total", 0) > 0 or track.get("finished_matches", 0) > 0,
            data.get("matches_total", 0) > 0,
            data.get("with_time", 0) > 0,
            data.get("with_score", 0) > 0 or data.get("live_now", 0) > 0,
        ]
        score = round(100 * sum(1 for x in checks if x) / len(checks))
        blockers = []
        if not telegram.get("env", {}).get("automation_secret"):
            blockers.append("Falta AUTOMATION_SECRET en Render.")
        if not telegram.get("env", {}).get("bot_token") or not telegram.get("env", {}).get("chat_id"):
            blockers.append("Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")
        if track.get("picks_total", 0) == 0:
            blockers.append("No hay picks reales publicados para vender rendimiento.")
        if track.get("graded_total", 0) == 0:
            blockers.append("Track Record todavía no tiene picks auditados.")
        if data.get("matches_total", 0) == 0:
            blockers.append("No hay partidos sincronizados en base real.")
        return {
            "ok": True,
            "version": app_version,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": "Certificación comercial V768",
            "score": score,
            "status": "LISTO PARA TESTERS" if score >= 75 and not blockers[:2] else "REQUIERE VALIDACIÓN RENDER",
            "madrid_note": MADRID_NOTE,
            "telegram": telegram,
            "track_record": track,
            "data_richness": data,
            "blockers": blockers,
            "next_actions": [
                "Subir ZIP a Render y verificar /api/runtime-version.",
                "Ejecutar Cron Telegram y revisar /admin/telegram/command-center.",
                "Ejecutar /api/automation/picks/grade?secret=AUTOMATION_SECRET tras sync de resultados.",
                "Revisar /track-record y confirmar que no aparece ROI inventado.",
            ],
        }
    finally:
        conn.close()
