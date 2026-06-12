"""Final commercial release candidate checks for NeMeSiS SHARK PRO V739.

Read-only engine. It does not send Telegram, does not charge, does not change
memberships and does not expose secrets. It consolidates the visual, security,
production, go-live and commercial checks into one final release candidate panel.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_CLIENT_TEMPLATES = [
    "home.html", "sports_hub.html", "live.html", "calendar.html", "picks.html",
    "combis.html", "favorites.html", "match_detail.html", "match_hub.html",
    "team_detail.html", "shark.html", "telegram.html", "profile.html",
    "membership.html", "track_record.html", "client_success.html",
]

CRITICAL_ADMIN_TEMPLATES = [
    "admin_telegram_command_center.html", "admin_route_health.html",
    "admin_client_experience.html", "admin_production_readiness.html",
    "admin_client_success.html", "admin_public_launch.html", "admin_track_record.html",
    "admin_payments.html", "admin_go_live.html", "admin_visual_experience.html",
    "admin_app_feel.html", "admin_final_release.html",
]

CRITICAL_ROUTES = [
    "/api/runtime-version", "/api/health", "/sports-hub", "/live", "/calendar",
    "/picks", "/combis", "/track-record", "/telegram", "/guia", "/ayuda",
    "/admin/telegram/command-center", "/admin/route-health", "/admin/client-experience",
    "/admin/production-readiness", "/admin/client-success", "/admin/public-launch",
    "/admin/track-record", "/admin/payments", "/admin/go-live",
    "/admin/visual-experience", "/admin/app-feel", "/admin/final-release",
]

REQUIRED_CSS_MARKERS = [
    "V736 Global Client Visual Membership Experience",
    "V737 Native App Feel",
    "V738 Final Commercial Release Candidate",
    "V739 Sale Ready Home Data Production Fix",
    "ns-tier-free", "ns-tier-pro", "ns-tier-elite", "ns-tier-eliteplus",
    "ns-final-release", "ns-final-badge", "ns-final-strip",
    "prefers-reduced-motion", "safe-area-inset-bottom",
]

REQUIRED_BASE_MARKERS = [
    "data-ns-route", "data-ns-plan", "tier-badge", "membership-energy-bar",
    "ns-route-glow", "nsScrollTop", "nsToastHost", "nsAppEnhance",
    "/admin/final-release",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _env_present(*names: str) -> bool:
    return any(bool(str(os.getenv(name) or "").strip()) for name in names)


def _env_label(*names: str) -> str:
    return "configurado" if _env_present(*names) else "pendiente"


def _safe_bool_label(value: bool) -> str:
    return "OK" if value else "REVISAR"


def _score(items: list[bool]) -> int:
    return round(100 * sum(1 for item in items if item) / len(items)) if items else 0


def _gate(key: str, title: str, checks: list[dict[str, Any]], next_action: str, critical: bool = False) -> dict[str, Any]:
    score = _score([bool(item.get("ok")) for item in checks])
    if score >= 95:
        status = "LISTO"
    elif score >= 80:
        status = "CASI_LISTO"
    elif critical:
        status = "BLOQUEO"
    else:
        status = "REVISAR"
    return {"key": key, "title": title, "score": score, "status": status, "critical": critical, "checks": checks, "next_action": next_action}


def _connect(db_path: str) -> sqlite3.Connection:
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


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    try:
        row = conn.execute("SELECT COUNT(*) AS total FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        return bool(row and int(row["total"] or 0) > 0)
    except Exception:
        return False


def _count(conn: sqlite3.Connection, name: str) -> int:
    if not _table_exists(conn, name):
        return 0
    try:
        row = conn.execute(f"SELECT COUNT(*) AS total FROM {name}").fetchone()
        return int(row["total"] or 0) if row else 0
    except Exception:
        return 0


def _db_state(db_path: str) -> dict[str, Any]:
    tables = [
        "users", "matches", "picks", "telegram_queue", "telegram_delivery_memory",
        "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots",
        "pick_grading_results", "payment_webhook_events", "subscription_accounts",
        "security_events", "automation_state", "data_memory_errors",
    ]
    result: dict[str, Any] = {"ok": False, "path": str(db_path or ""), "tables": {}, "counts": {}}
    try:
        conn = _connect(db_path)
        for table in tables:
            exists = _table_exists(conn, table)
            result["tables"][table] = exists
            result["counts"][table] = _count(conn, table) if exists else 0
        conn.close()
        result["ok"] = True
    except Exception as exc:
        result["error"] = str(exc)[:220]
    return result


def _project_state(app_version: str = "") -> dict[str, Any]:
    app_text = _read(ROOT / "app.py")
    version_txt = _read(ROOT / "VERSION.txt").strip()
    css = _read(ROOT / "static" / "app.css")
    base = _read(ROOT / "templates" / "base.html")
    app_match = re.search(r'APP_VERSION\s*=\s*["\\\']([^"\\\']+)["\\\']', app_text)
    app_py_version = app_match.group(1) if app_match else ""
    template_dir = ROOT / "templates"
    return {
        "expected": app_version or app_py_version or version_txt,
        "version_txt": version_txt,
        "app_py_version": app_py_version,
        "version_match": bool(version_txt and app_py_version and version_txt == app_py_version),
        "app_lines": len(app_text.splitlines()),
        "client_templates": {name: (template_dir / name).exists() for name in CRITICAL_CLIENT_TEMPLATES},
        "admin_templates": {name: (template_dir / name).exists() for name in CRITICAL_ADMIN_TEMPLATES},
        "routes": {route: route in app_text for route in CRITICAL_ROUTES},
        "base_markers": {marker: marker in base for marker in REQUIRED_BASE_MARKERS},
        "css_markers": {marker: marker in css for marker in REQUIRED_CSS_MARKERS},
        "check_tools": len(list((ROOT / "tools").glob("check_*.py"))),
        "tests": len(list((ROOT / "tests").glob("test_*.py"))),
        "release_builder": (ROOT / "tools" / "build_clean_release.py").exists(),
        "release_auditor": (ROOT / "tools" / "audit_release_zip.py").exists(),
    }


def final_release_validation_plan() -> list[dict[str, str]]:
    return [
        {"step": "1", "title": "Subir ZIP final a GitHub/Render", "detail": "Desplegar la release final y esperar build verde."},
        {"step": "2", "title": "Verificar versión", "detail": "Abrir /api/runtime-version y confirmar la versión V739_SALE_READY_HOME_DATA_PRODUCTION_FIX."},
        {"step": "3", "title": "Probar salud y seguridad", "detail": "Abrir /api/health, login cliente, login admin, CSRF/rate limit y centros admin."},
        {"step": "4", "title": "Confirmar horarios Madrid", "detail": "Revisar Calendar, Live, Picks, Match Detail y Telegram con un partido de hora conocida."},
        {"step": "5", "title": "Confirmar Telegram real", "detail": "Usar /admin/telegram/command-center, dry-run y test-send manual solo si procede."},
        {"step": "6", "title": "Confirmar persistencia", "detail": "Verificar DB_PATH=/data/database.db, usuarios siguen tras redeploy y Data Memory crece."},
        {"step": "7", "title": "QA móvil", "detail": "Probar iPhone/Android/PWA con FREE, PRO y ELITE para navegación inferior, SHARK y formularios."},
        {"step": "8", "title": "Abrir beta controlada", "detail": "Solo con Telegram, DB, horarios y login validados durante varios días."},
    ]


def final_release_snapshot(db_path: str, app_version: str = "") -> dict[str, Any]:
    project = _project_state(app_version)
    db = _db_state(db_path)
    tables = db.get("tables", {})
    counts = db.get("counts", {})
    db_path_text = str(db_path or "")

    secret_ok = _env_present("SECRET_KEY", "FLASK_SECRET_KEY")
    automation_ok = _env_present("AUTOMATION_SECRET")
    telegram_ok = _env_present("TELEGRAM_BOT_TOKEN") and _env_present("TELEGRAM_CHAT_ID", "TELEGRAM_CHANNEL_ID")
    odds_ok = _env_present("THE_ODDS_API_KEY", "ODDS_API_KEY")
    stripe_ready = _env_present("STRIPE_SECRET_KEY") and _env_present("STRIPE_WEBHOOK_SECRET")
    persistent_ok = db_path_text.startswith("/data/") or os.getenv("DB_PATH") == "/data/database.db"

    gates = [
        _gate(
            "final_version_zip",
            "Versión, ZIP limpio y release candidate",
            [
                {"label": "APP_VERSION y VERSION.txt coinciden", "ok": project["version_match"], "value": project["expected"]},
                {"label": "Builder de release limpio", "ok": project["release_builder"]},
                {"label": "Auditor ZIP limpio", "ok": project["release_auditor"]},
                {"label": "Checks disponibles", "ok": project["check_tools"] >= 10, "value": project["check_tools"]},
                {"label": "Tests preparados", "ok": project["tests"] >= 1, "value": project["tests"]},
            ],
            "Construir ZIP, auditar 0 prohibidos y subir solo el ZIP final.",
            critical=True,
        ),
        _gate(
            "client_visual",
            "Cliente premium global",
            [
                {"label": "Templates cliente críticos", "ok": all(project["client_templates"].values()), "value": f"{sum(project['client_templates'].values())}/{len(project['client_templates'])}"},
                {"label": "Base visual global", "ok": all(project["base_markers"].values()), "value": f"{sum(project['base_markers'].values())}/{len(project['base_markers'])}"},
                {"label": "CSS visual V736/V737/V738", "ok": all(project["css_markers"].values()), "value": f"{sum(project['css_markers'].values())}/{len(project['css_markers'])}"},
                {"label": "FREE/PRO/ELITE/ELITE+ preparado", "ok": all(project["css_markers"].get(m, False) for m in ["ns-tier-free", "ns-tier-pro", "ns-tier-elite", "ns-tier-eliteplus"])},
            ],
            "Hacer QA visual real en móvil y desktop con usuarios de cada plan.",
            critical=False,
        ),
        _gate(
            "admin_control_centers",
            "Centros de control admin",
            [
                {"label": "Templates admin críticos", "ok": all(project["admin_templates"].values()), "value": f"{sum(project['admin_templates'].values())}/{len(project['admin_templates'])}"},
                {"label": "Rutas críticas detectadas", "ok": all(project["routes"].values()), "value": f"{sum(project['routes'].values())}/{len(project['routes'])}"},
                {"label": "Final Release Center instalado", "ok": project["admin_templates"].get("admin_final_release.html") and project["routes"].get("/admin/final-release")},
            ],
            "Entrar como admin y revisar Final, Go Live, Visual, App Feel, Producción y Telegram.",
            critical=True,
        ),
        _gate(
            "production_env",
            "Producción Render y persistencia",
            [
                {"label": "SECRET_KEY estable", "ok": secret_ok, "value": _env_label("SECRET_KEY", "FLASK_SECRET_KEY")},
                {"label": "AUTOMATION_SECRET", "ok": automation_ok, "value": _env_label("AUTOMATION_SECRET")},
                {"label": "DB_PATH persistente /data", "ok": persistent_ok, "value": db_path_text},
                {"label": "Base de datos accesible", "ok": db.get("ok"), "value": db.get("error", "OK")},
            ],
            "En Render, confirmar variables y disco persistente antes de abrir usuarios externos.",
            critical=True,
        ),
        _gate(
            "telegram_data",
            "Telegram, datos y memoria",
            [
                {"label": "Telegram env completo", "ok": telegram_ok, "value": _env_label("TELEGRAM_BOT_TOKEN")},
                {"label": "The Odds API configurada", "ok": odds_ok, "value": _env_label("THE_ODDS_API_KEY", "ODDS_API_KEY")},
                {"label": "Usuarios", "ok": tables.get("users"), "value": counts.get("users", 0)},
                {"label": "Partidos", "ok": tables.get("matches"), "value": counts.get("matches", 0)},
                {"label": "Picks", "ok": tables.get("picks"), "value": counts.get("picks", 0)},
                {"label": "Memoria Telegram", "ok": tables.get("telegram_delivery_memory"), "value": counts.get("telegram_delivery_memory", 0)},
                {"label": "Snapshots Data Memory", "ok": tables.get("match_snapshots"), "value": counts.get("match_snapshots", 0)},
            ],
            "Usar Command Center en producción; no vender Telegram hasta confirmar envíos reales y no duplicados.",
            critical=True,
        ),
        _gate(
            "commercial",
            "Track Record, pagos y venta controlada",
            [
                {"label": "Track Record preparado", "ok": project["routes"].get("/track-record") and tables.get("pick_grading_results"), "value": counts.get("pick_grading_results", 0)},
                {"label": "Pagos en modo seguro", "ok": project["routes"].get("/admin/payments") and tables.get("payment_webhook_events"), "value": counts.get("payment_webhook_events", 0)},
                {"label": "Stripe preparado", "ok": stripe_ready, "value": "configurado" if stripe_ready else "pendiente"},
                {"label": "Soporte y guía cliente", "ok": project["routes"].get("/guia") and project["routes"].get("/ayuda")},
            ],
            "Activar pagos reales solo después de webhook probado; publicar ROI solo con resultados reales suficientes.",
            critical=False,
        ),
    ]

    critical_gates = [gate for gate in gates if gate.get("critical")]
    static_gates_ok = all(gate["score"] >= 90 for gate in gates[:3])
    critical_ok = all(gate["score"] >= 80 for gate in critical_gates)
    overall = _score([gate["score"] >= 85 for gate in gates])
    readiness_score = round(sum(gate["score"] for gate in gates) / len(gates)) if gates else 0

    if critical_ok and readiness_score >= 92 and telegram_ok and secret_ok and automation_ok and persistent_ok:
        status = "FINAL_READY_FOR_CONTROLLED_PUBLIC_BETA"
    elif static_gates_ok:
        status = "FINAL_STATIC_READY_RENDER_VALIDATION_PENDING"
    else:
        status = "FINAL_REVIEW_NEEDED"

    return {
        "version": app_version or project["expected"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "overall": overall,
        "readiness_score": readiness_score,
        "gates": gates,
        "project": project,
        "db": db,
        "production_missing": [
            item for item, ok in [
                ("SECRET_KEY/FLASK_SECRET_KEY", secret_ok),
                ("AUTOMATION_SECRET", automation_ok),
                ("TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID/CHANNEL", telegram_ok),
                ("DB_PATH=/data/database.db", persistent_ok),
                ("THE_ODDS_API_KEY/ODDS_API_KEY", odds_ok),
                ("STRIPE env completo si se activan pagos", stripe_ready),
            ] if not ok
        ],
        "safe_scope": [
            "No envía Telegram automáticamente.",
            "No cobra ni activa Stripe real.",
            "No cambia membresías ni DB_PATH.",
            "No muestra secretos reales.",
            "No cambia lógica de picks/cuotas ni horarios Madrid.",
        ],
        "final_message": "Release candidate comercial V739: home con datos reales preparado; producción grande depende de Render real, Telegram real, DB persistente, cron real y pagos reales validados.",
    }
