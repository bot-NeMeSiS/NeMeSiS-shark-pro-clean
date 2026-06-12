"""Go-live certification engine for NeMeSiS SHARK PRO.

V735 is intentionally read-only: it does not call Telegram, does not charge users
and does not change memberships. It converts the public launch roadmap into a
single operational gate so the admin can decide whether the product is ready for
a controlled public launch.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_LAUNCH_AREAS = [
    "Producción Render",
    "Telegram automático",
    "Persistencia y Data Memory",
    "Track Record y ROI",
    "Pagos PRO/ELITE",
    "Cliente móvil y soporte",
    "Seguridad y arquitectura",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_env_present(name: str, alternatives: Iterable[str] = ()) -> bool:
    names = [name, *list(alternatives or [])]
    return any(bool(str(os.getenv(item) or "").strip()) for item in names)


def safe_env_label(name: str, alternatives: Iterable[str] = ()) -> str:
    return "configurado" if safe_env_present(name, alternatives) else "pendiente"


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(str(db_path)) or ".", exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30, check_same_thread=False)
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
        values = list(dict(row).values())
        return values[0] if values else default
    except sqlite3.OperationalError:
        return default
    except sqlite3.DatabaseError:
        return default


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return bool(scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,), 0))


def table_count(conn: sqlite3.Connection, name: str) -> int:
    if not table_exists(conn, name):
        return 0
    try:
        return int(scalar(conn, f"SELECT COUNT(*) FROM {name}", default=0) or 0)
    except Exception:
        return 0


def latest_value(conn: sqlite3.Connection, table: str, column: str, order_column: str = "id") -> str:
    if not table_exists(conn, table):
        return ""
    try:
        row = conn.execute(f"SELECT {column} FROM {table} ORDER BY {order_column} DESC LIMIT 1").fetchone()
        return str(dict(row).get(column) or "") if row else ""
    except Exception:
        return ""


def db_snapshot(db_path: str) -> dict[str, Any]:
    wanted = [
        "users", "matches", "picks", "telegram_queue", "telegram_delivery_memory",
        "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots",
        "pick_grading_results", "payment_webhook_events", "subscription_accounts",
        "security_events", "data_memory_errors", "automation_state",
    ]
    result: dict[str, Any] = {"path": str(db_path or ""), "tables": {}, "counts": {}, "latest": {}}
    try:
        conn = connect(db_path)
        for name in wanted:
            exists = table_exists(conn, name)
            result["tables"][name] = exists
            result["counts"][name] = table_count(conn, name) if exists else 0
        result["latest"]["telegram_delivery"] = latest_value(conn, "telegram_delivery_memory", "sent_at", "id")
        result["latest"]["security_event"] = latest_value(conn, "security_events", "created_at", "id")
        result["latest"]["payment_webhook"] = latest_value(conn, "payment_webhook_events", "received_at", "id")
        conn.close()
        result["ok"] = True
    except Exception as exc:
        result["ok"] = False
        result["error"] = str(exc)[:300]
    return result


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def project_snapshot(app_version: str = "") -> dict[str, Any]:
    app_text = read_text(ROOT / "app.py")
    version_txt = read_text(ROOT / "VERSION.txt").strip()
    app_match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', app_text)
    app_py_version = app_match.group(1) if app_match else ""
    templates = ROOT / "templates"
    static_css = read_text(ROOT / "static" / "app.css")
    return {
        "version_txt": version_txt,
        "app_py_version": app_py_version,
        "expected": app_version or app_py_version or version_txt,
        "version_match": bool(version_txt and app_py_version and version_txt == app_py_version),
        "app_lines": len(app_text.splitlines()),
        "tests_count": len(list((ROOT / "tests").glob("test_*.py"))),
        "check_tools_count": len(list((ROOT / "tools").glob("check_*.py"))),
        "templates": {
            "go_live": (templates / "admin_go_live.html").exists(),
            "public_launch": (templates / "admin_public_launch.html").exists(),
            "track_record": (templates / "track_record.html").exists(),
            "payments": (templates / "admin_payments.html").exists(),
            "client_success": (templates / "client_success.html").exists(),
        },
        "css": {
            "mobile": "@media" in static_css and "max-width" in static_css,
            "v735": "V735" in static_css,
            "launch": "go-live" in static_css or "v735" in static_css.lower(),
        },
    }


def yes(value: Any) -> bool:
    return bool(value)


def score(checks: list[bool]) -> int:
    return round(100 * sum(1 for item in checks if item) / len(checks)) if checks else 0


def gate(key: str, title: str, checks: list[dict[str, Any]], next_action: str, critical: bool = False) -> dict[str, Any]:
    gate_score = score([bool(item.get("ok")) for item in checks])
    return {
        "key": key,
        "title": title,
        "score": gate_score,
        "critical": critical,
        "status": "OK" if gate_score >= 85 else ("REVISAR" if gate_score >= 65 else "BLOQUEO"),
        "checks": checks,
        "next_action": next_action,
    }


def go_live_snapshot(db_path: str, app_version: str = "") -> dict[str, Any]:
    """Return a safe go-live readiness snapshot without exposing secrets."""
    db = db_snapshot(db_path)
    project = project_snapshot(app_version)
    tables = db.get("tables", {})
    counts = db.get("counts", {})
    db_path_text = str(db_path or "")
    render_env = safe_env_present("RENDER", ["RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL"])
    persistent_path = db_path_text.startswith("/data/") or os.getenv("DB_PATH") == "/data/database.db"
    telegram_env = safe_env_present("TELEGRAM_BOT_TOKEN") and safe_env_present("TELEGRAM_CHAT_ID", ["TELEGRAM_CHANNEL_ID"])
    automation_env = safe_env_present("AUTOMATION_SECRET")
    stripe_env = safe_env_present("STRIPE_SECRET_KEY") and safe_env_present("STRIPE_WEBHOOK_SECRET") and safe_env_present("STRIPE_PRICE_PRO") and safe_env_present("STRIPE_PRICE_ELITE")
    odds_env = safe_env_present("THE_ODDS_API_KEY") or safe_env_present("ODDS_API_KEY")
    secret_env = safe_env_present("SECRET_KEY", ["FLASK_SECRET_KEY"])

    gates = [
        gate(
            "production_render",
            "Producción Render y versión",
            [
                {"label": "APP_VERSION y VERSION.txt coinciden", "ok": project["version_match"], "value": project["expected"]},
                {"label": "SECRET_KEY estable", "ok": secret_env, "value": safe_env_label("SECRET_KEY", ["FLASK_SECRET_KEY"])},
                {"label": "AUTOMATION_SECRET configurado", "ok": automation_env, "value": safe_env_label("AUTOMATION_SECRET")},
                {"label": "DB_PATH persistente /data", "ok": persistent_path, "value": db_path_text},
                {"label": "Entorno Render detectado", "ok": render_env, "value": safe_env_label("RENDER", ["RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL"])},
            ],
            "Subir ZIP, verificar /api/runtime-version, /api/health y Cron 403/200 con secret real.",
            critical=True,
        ),
        gate(
            "telegram",
            "Telegram automático estable",
            [
                {"label": "Token y canal/chat configurados", "ok": telegram_env, "value": safe_env_label("TELEGRAM_BOT_TOKEN")},
                {"label": "Cron protegido", "ok": automation_env},
                {"label": "Cola Telegram disponible", "ok": tables.get("telegram_queue"), "value": counts.get("telegram_queue", 0)},
                {"label": "Memoria antirrepetición disponible", "ok": tables.get("telegram_delivery_memory"), "value": counts.get("telegram_delivery_memory", 0)},
                {"label": "Command Center instalado", "ok": "admin_telegram_command_center.html" in [p.name for p in (ROOT / "templates").glob("admin_telegram_command_center.html")]},
            ],
            "Usar /admin/telegram/command-center en producción y confirmar envío real sin duplicados varios días.",
            critical=True,
        ),
        gate(
            "data_memory",
            "Persistencia, datos y memoria SHARK",
            [
                {"label": "Tabla usuarios", "ok": tables.get("users"), "value": counts.get("users", 0)},
                {"label": "Tabla partidos", "ok": tables.get("matches"), "value": counts.get("matches", 0)},
                {"label": "Tabla picks", "ok": tables.get("picks"), "value": counts.get("picks", 0)},
                {"label": "Snapshots de partidos", "ok": tables.get("match_snapshots"), "value": counts.get("match_snapshots", 0)},
                {"label": "Data Memory sin error crítico", "ok": db.get("ok", False)},
            ],
            "Confirmar que Daily Run y Telegram Tick aumentan memoria real en /admin/data-memory.",
            critical=True,
        ),
        gate(
            "track_record",
            "Track Record, grading y ROI real",
            [
                {"label": "Tabla grading disponible", "ok": tables.get("pick_grading_results"), "value": counts.get("pick_grading_results", 0)},
                {"label": "Picks reales disponibles", "ok": tables.get("picks"), "value": counts.get("picks", 0)},
                {"label": "Ruta pública histórico instalada", "ok": project["templates"].get("track_record")},
                {"label": "Resultados suficientes para publicar ROI", "ok": counts.get("pick_grading_results", 0) >= 10, "value": counts.get("pick_grading_results", 0)},
            ],
            "Publicar ROI solo con resultados reales suficientes; mientras tanto mostrarlo como histórico en construcción.",
            critical=False,
        ),
        gate(
            "payments",
            "Pagos PRO/ELITE",
            [
                {"label": "Tabla suscripciones", "ok": tables.get("subscription_accounts"), "value": counts.get("subscription_accounts", 0)},
                {"label": "Tabla webhooks", "ok": tables.get("payment_webhook_events"), "value": counts.get("payment_webhook_events", 0)},
                {"label": "Stripe env completo", "ok": stripe_env, "value": "configurado" if stripe_env else "pendiente"},
                {"label": "Modo auditoría seguro", "ok": True, "value": "no cobra ni cambia membresías sin activar Stripe real"},
            ],
            "Configurar Stripe real en Render y probar webhook antes de activar altas automáticas.",
            critical=False,
        ),
        gate(
            "client_mobile",
            "Cliente, móvil y soporte",
            [
                {"label": "Guía cliente", "ok": project["templates"].get("client_success")},
                {"label": "Centro público grande", "ok": project["templates"].get("public_launch")},
                {"label": "CSS móvil", "ok": project["css"].get("mobile")},
                {"label": "Capa V735 visual/control", "ok": project["css"].get("v735")},
                {"label": "The Odds API configurada", "ok": odds_env, "value": "configurado" if odds_env else "pendiente"},
            ],
            "Hacer QA real con móvil, PWA, Live, Calendar, Picks, Combis, SHARK y Match Detail.",
            critical=False,
        ),
        gate(
            "security_architecture",
            "Seguridad, tests y arquitectura",
            [
                {"label": "Eventos de seguridad", "ok": tables.get("security_events"), "value": counts.get("security_events", 0)},
                {"label": "Checks de release", "ok": project["check_tools_count"] >= 8, "value": project["check_tools_count"]},
                {"label": "Tests preparados", "ok": project["tests_count"] >= 4, "value": project["tests_count"]},
                {"label": "app.py bajo control temporal", "ok": project["app_lines"] < 12500, "value": project["app_lines"]},
            ],
            "Mantener extracción a blueprints por bloques pequeños después de certificar producción real.",
            critical=False,
        ),
    ]

    global_score = round(sum(item["score"] for item in gates) / len(gates)) if gates else 0
    critical_blockers = [item for item in gates if item.get("critical") and item["score"] < 75]
    blockers = [item for item in gates if item["score"] < 75]
    if critical_blockers:
        status = "NO_ABRIR_PUBLICO_GRANDE"
    elif global_score >= 90:
        status = "LISTO_PRELANZAMIENTO_CONTROLADO"
    elif global_score >= 78:
        status = "BETA_COMERCIAL_CONTROLADA"
    else:
        status = "PREPARACION_PUBLICO_GRANDE"

    return {
        "ok": True,
        "schema": "go_live_v735",
        "version": app_version,
        "generated_at": utc_now(),
        "status": status,
        "global_score": global_score,
        "critical_blockers": critical_blockers,
        "blockers": blockers,
        "gates": gates,
        "safe_env": {
            "secret_key": secret_env,
            "automation_secret": automation_env,
            "telegram": telegram_env,
            "stripe": stripe_env,
            "odds_api": odds_env,
            "render": render_env,
            "db_path": db_path_text,
        },
        "db": db,
        "project": project,
        "decision": {
            "can_open_public_big": not critical_blockers and global_score >= 90,
            "can_run_private_beta": not critical_blockers and global_score >= 75,
            "recommended_next": "Validar V735 en Render real: runtime, health, cron 403/200, Telegram Command Center, Data Memory y Track Record.",
        },
    }


def production_validation_plan(base_url: str = "") -> list[dict[str, Any]]:
    base_url = str(base_url or os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "https://bot-apuestas-crgf.onrender.com").rstrip("/")
    return [
        {"step": 1, "title": "Versión desplegada", "url": f"{base_url}/api/runtime-version", "expected": "V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION"},
        {"step": 2, "title": "Health", "url": f"{base_url}/api/health", "expected": "200 OK"},
        {"step": 3, "title": "Producción readiness", "url": f"{base_url}/admin/production-readiness", "expected": "200 con sesión admin"},
        {"step": 4, "title": "Go Live Center", "url": f"{base_url}/admin/go-live", "expected": "200 con sesión admin"},
        {"step": 5, "title": "Telegram Command Center", "url": f"{base_url}/admin/telegram/command-center", "expected": "200 con sesión admin"},
        {"step": 6, "title": "Cron Telegram sin secret", "url": f"{base_url}/api/automation/telegram/tick", "expected": "403"},
        {"step": 7, "title": "Cron Telegram con secret", "url": f"{base_url}/api/automation/telegram/tick?secret=***", "expected": "200 y diagnóstico claro"},
        {"step": 8, "title": "Daily Run sin secret", "url": f"{base_url}/api/automation/daily/run", "expected": "403"},
        {"step": 9, "title": "Daily Run con secret", "url": f"{base_url}/api/automation/daily/run?secret=***", "expected": "200 y memoria/errores claros"},
        {"step": 10, "title": "Histórico real", "url": f"{base_url}/track-record", "expected": "No inventa ROI; muestra histórico real o construcción"},
    ]
