"""Public launch readiness engine for NeMeSiS SHARK PRO.

V734 aggregates the six areas needed before opening to a larger public: Render
production QA, Telegram stability, persistent data, pick track record, payments
and gradual architecture/tests. It is read-only and safe.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


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


def scalar(conn: sqlite3.Connection, query: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    try:
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            return default
        return list(dict(row).values())[0]
    except sqlite3.OperationalError:
        return default


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return bool(scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,), 0))


def env_present(name: str) -> bool:
    return bool(str(os.getenv(name) or "").strip())


def score_stage(checks: list[bool]) -> int:
    return round(100 * sum(1 for ok in checks if ok) / len(checks)) if checks else 0


def db_metrics(db_path: str) -> Dict[str, Any]:
    conn = connect(db_path)
    tables = {name: table_exists(conn, name) for name in [
        "users", "matches", "picks", "telegram_queue", "telegram_delivery_memory",
        "match_snapshots", "pick_grading_results", "subscription_accounts", "payment_webhook_events",
    ]}
    counts = {}
    for name, exists in tables.items():
        counts[name] = scalar(conn, f"SELECT COUNT(*) FROM {name}", default=0) if exists else 0
    conn.close()
    return {"tables": tables, "counts": counts}


def public_launch_snapshot(db_path: str, app_version: str = "") -> Dict[str, Any]:
    metrics = db_metrics(db_path)
    counts = metrics["counts"]
    tables = metrics["tables"]
    db_path_text = str(db_path or "")
    persistent_db = db_path_text.startswith("/data/") or env_present("RENDER") or env_present("RENDER_SERVICE_ID")
    production_env = env_present("RENDER") or env_present("RENDER_SERVICE_ID") or env_present("RENDER_EXTERNAL_URL")
    telegram_ready = env_present("TELEGRAM_BOT_TOKEN") and (env_present("TELEGRAM_CHAT_ID") or env_present("TELEGRAM_CHANNEL_ID"))
    automation_ready = env_present("AUTOMATION_SECRET")
    secret_ready = env_present("SECRET_KEY") or env_present("FLASK_SECRET_KEY")
    payments_env_ready = env_present("STRIPE_SECRET_KEY") and env_present("STRIPE_WEBHOOK_SECRET") and env_present("STRIPE_PRICE_PRO") and env_present("STRIPE_PRICE_ELITE")
    app_py = Path(__file__).resolve().parents[1] / "app.py"
    app_lines = len(app_py.read_text(encoding="utf-8", errors="ignore").splitlines()) if app_py.exists() else 0
    tests_count = len(list((Path(__file__).resolve().parents[1] / "tests").glob("test_*.py")))
    tools_count = len(list((Path(__file__).resolve().parents[1] / "tools").glob("check_*.py")))

    stages = [
        {
            "key": "production_qa",
            "title": "Producción Render certificada",
            "score": score_stage([secret_ready, automation_ready, persistent_db, production_env or db_path_text.startswith("/data/")]),
            "checks": [
                {"label": "SECRET_KEY configurada", "ok": secret_ready},
                {"label": "AUTOMATION_SECRET configurado", "ok": automation_ready},
                {"label": "DB persistente /data/database.db", "ok": persistent_db},
                {"label": "Entorno Render detectado", "ok": production_env},
            ],
            "next": "Validar /api/runtime-version, /api/health, Cron 403/200 y capturas móviles después del deploy.",
        },
        {
            "key": "telegram_stability",
            "title": "Telegram producción estable",
            "score": score_stage([telegram_ready, automation_ready, tables.get("telegram_queue"), tables.get("telegram_delivery_memory")]),
            "checks": [
                {"label": "Token/chat configurados", "ok": telegram_ready},
                {"label": "Cron protegido", "ok": automation_ready},
                {"label": "Cola Telegram disponible", "ok": tables.get("telegram_queue")},
                {"label": "Memoria delivery disponible", "ok": tables.get("telegram_delivery_memory")},
            ],
            "next": "Usar /admin/telegram/command-center en producción y confirmar envíos reales varios días.",
        },
        {
            "key": "data_memory",
            "title": "Persistencia y memoria de datos",
            "score": score_stage([tables.get("users"), tables.get("matches"), tables.get("picks"), tables.get("match_snapshots") or counts.get("matches", 0) > 0]),
            "checks": [
                {"label": "Usuarios persistidos", "ok": tables.get("users"), "value": counts.get("users")},
                {"label": "Partidos persistidos", "ok": tables.get("matches"), "value": counts.get("matches")},
                {"label": "Picks persistidos", "ok": tables.get("picks"), "value": counts.get("picks")},
                {"label": "Snapshots/Data Memory", "ok": tables.get("match_snapshots"), "value": counts.get("match_snapshots")},
            ],
            "next": "Confirmar crecimiento real de Data Memory tras daily run y live/tick en Render.",
        },
        {
            "key": "track_record",
            "title": "Histórico, ROI y credibilidad de picks",
            "score": score_stage([tables.get("pick_grading_results"), counts.get("pick_grading_results", 0) > 0, tables.get("picks"), counts.get("picks", 0) > 0]),
            "checks": [
                {"label": "Tabla de grading", "ok": tables.get("pick_grading_results")},
                {"label": "Resultados evaluados", "ok": counts.get("pick_grading_results", 0) > 0, "value": counts.get("pick_grading_results")},
                {"label": "Picks reales disponibles", "ok": tables.get("picks"), "value": counts.get("picks")},
                {"label": "Base para ROI público", "ok": counts.get("picks", 0) > 0},
            ],
            "next": "Ejecutar /admin/track-record y publicar ROI solo cuando haya resultados reales suficientes.",
        },
        {
            "key": "payments",
            "title": "Pagos PRO/ELITE",
            "score": score_stage([tables.get("subscription_accounts"), payments_env_ready, env_present("STRIPE_WEBHOOK_SECRET"), env_present("STRIPE_PRICE_PRO") and env_present("STRIPE_PRICE_ELITE")]),
            "checks": [
                {"label": "Suscripciones internas", "ok": tables.get("subscription_accounts")},
                {"label": "Stripe básico configurado", "ok": payments_env_ready},
                {"label": "Webhook secret", "ok": env_present("STRIPE_WEBHOOK_SECRET")},
                {"label": "Precios PRO/ELITE", "ok": env_present("STRIPE_PRICE_PRO") and env_present("STRIPE_PRICE_ELITE")},
            ],
            "next": "Configurar Stripe real y probar webhook antes de activar alta automática.",
        },
        {
            "key": "architecture_tests",
            "title": "Arquitectura y tests para escalar",
            "score": score_stage([app_lines < 12000, tests_count >= 4, tools_count >= 5, Path("tools/build_clean_release.py").exists()]),
            "checks": [
                {"label": "app.py bajo control temporal", "ok": app_lines < 12000, "value": app_lines},
                {"label": "Tests preparados", "ok": tests_count >= 4, "value": tests_count},
                {"label": "Checks de release", "ok": tools_count >= 5, "value": tools_count},
                {"label": "Builder limpio", "ok": Path("tools/build_clean_release.py").exists()},
            ],
            "next": "Extraer blueprints por bloques pequeños después de certificar producción y pagos.",
        },
    ]
    global_score = round(sum(stage["score"] for stage in stages) / len(stages)) if stages else 0
    blockers = []
    for stage in stages:
        if stage["score"] < 75:
            blockers.append({"stage": stage["title"], "score": stage["score"], "next": stage["next"]})
    return {
        "ok": True,
        "schema": "public_launch_v734",
        "version": app_version,
        "generated_at": utc_now(),
        "global_score": global_score,
        "status": "BETA_COMERCIAL_CONTROLADA" if global_score >= 75 else "PREPARACION_PUBLICO_GRANDE",
        "stages": stages,
        "blockers": blockers,
        "counts": counts,
        "safe_env": {
            "secret_key": secret_ready,
            "automation_secret": automation_ready,
            "telegram": telegram_ready,
            "stripe": payments_env_ready,
            "render": production_env,
            "db_path": db_path_text,
        },
        "next_release_recommendation": "V735 debería certificar producción real en Render con capturas/logs antes de activar pagos públicos.",
    }
