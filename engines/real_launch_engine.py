"""V789 real launch certification helpers for NeMeSiS SHARK PRO.

The goal is operational readiness, not legal advice. It checks the app is
positioned as an informational sports analytics SaaS, that Stripe live is not
activated blindly, and that production dependencies are visible without exposing
secrets.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:  # Local import kept defensive so this engine never breaks boot.
    from engines.stripe_payments_engine import stripe_runtime_status
except Exception:  # pragma: no cover
    stripe_runtime_status = None  # type: ignore

try:
    from engines.legal_compliance_engine import legal_admin_snapshot
except Exception:  # pragma: no cover
    legal_admin_snapshot = None  # type: ignore

REAL_LAUNCH_VERSION = "V789-REAL-LAUNCH-2026-06-14"

RISKY_COPY_TERMS = [
    "ganancia segura",
    "dinero garantizado",
    "beneficio garantizado",
    "apuesta segura",
    "cuota segura",
    "sin riesgo",
    "rentabilidad fija",
    "te hacemos ganar",
    "ROI garantizado",
]

SAFE_REQUIRED_PUBLIC_ROUTES = [
    "/legal",
    "/terminos",
    "/privacidad",
    "/cookies",
    "/reembolsos",
    "/aviso-legal",
    "/juego-responsable",
    "/no-somos-casa-de-apuestas",
    "/membresias",
]

PRODUCTION_CRON_ENDPOINTS = [
    "/api/automation/telegram/tick",
    "/api/automation/picks/grade",
    "/api/automation/highlights/sync",
]


def _env(name: str) -> str:
    return str(os.getenv(name) or "").strip()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _present(name: str) -> bool:
    return bool(_env(name))


def _prefix(name: str, prefix: str) -> bool:
    return _env(name).startswith(prefix)


def _mask_state(name: str, prefix: str | None = None) -> Dict[str, Any]:
    value = _env(name)
    ok = bool(value) and (not prefix or value.startswith(prefix))
    if not value:
        state = "vacía"
    elif prefix and not value.startswith(prefix):
        state = f"formato inválido: debe empezar por {prefix}"
    else:
        state = "configurada"
    return {"name": name, "ok": ok, "state": state, "prefix": prefix or ""}


def _row(status: str, title: str, detail: str, priority: int = 50, action: str = "", group: str = "") -> Dict[str, Any]:
    status = status.upper().strip()
    return {
        "status": status,
        "title": title,
        "detail": detail,
        "priority": int(priority),
        "action": action,
        "group": group,
    }


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        return bool(row)
    except Exception:
        return False


def _scalar(conn: sqlite3.Connection, query: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    try:
        row = conn.execute(query, tuple(params)).fetchone()
        if not row:
            return default
        return list(dict(row).values())[0]
    except Exception:
        return default


def _database_snapshot(db_path: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"path": db_path, "exists": Path(db_path).exists(), "counts": {}, "error": ""}
    try:
        conn = _connect(db_path)
        for table in ["users", "matches", "picks", "payment_webhook_events", "stripe_subscriptions", "telegram_deliveries", "user_legal_acceptances"]:
            data["counts"][table] = int(_scalar(conn, f"SELECT COUNT(*) FROM {table}", default=0)) if _table_exists(conn, table) else 0
        conn.close()
    except Exception as exc:
        data["error"] = str(exc)
    return data


def _file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _route_presence(root: Path) -> List[Dict[str, Any]]:
    app_py = _file_text(root / "app.py")
    return [{"path": route, "ok": route in app_py} for route in SAFE_REQUIRED_PUBLIC_ROUTES]


def _unsafe_copy_scan(root: Path) -> Dict[str, Any]:
    targets = []
    for directory in [root / "templates", root / "static", root / "engines"]:
        if directory.exists():
            targets.extend(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in {".html", ".css", ".js", ".py"})
    findings = []
    for path in targets:
        rel = path.relative_to(root).as_posix()
        text = _file_text(path).lower()
        for term in RISKY_COPY_TERMS:
            term_lower = term.lower()
            if term_lower in text:
                findings.append({"file": rel, "term": term, "count": text.count(term_lower)})
    return {"ok": not findings, "findings": findings[:50], "total": len(findings), "terms": RISKY_COPY_TERMS}


def _stripe_section(db_path: str) -> Dict[str, Any]:
    runtime = stripe_runtime_status(db_path) if callable(stripe_runtime_status) else {"flags": {}, "summary": {}, "plans": {}, "blockers": []}
    secret = _env("STRIPE_SECRET_KEY")
    live = secret.startswith("sk_live_")
    test = secret.startswith("sk_test_")
    price_pro = _prefix("STRIPE_PRICE_PRO", "price_")
    price_elite = _prefix("STRIPE_PRICE_ELITE", "price_")
    webhook = _prefix("STRIPE_WEBHOOK_SECRET", "whsec_")
    portal = _env_bool("STRIPE_CUSTOMER_PORTAL_ENABLED", True)
    payments_enabled = _env_bool("PAYMENTS_ENABLED", True)
    verified = _env_bool("STRIPE_ACCOUNT_VERIFIED", False)
    items = []
    items.append(_row("READY" if live else "ACTION" if test else "CRITICAL", "Stripe en modo real", "Detectada clave sk_live_." if live else "Sigue en test con sk_test_. Correcto para pruebas; no cobra dinero real." if test else "Falta STRIPE_SECRET_KEY.", 98, "Pasar a sk_live_ solo tras verificar cuenta, IBAN y revisión legal.", "stripe"))
    items.append(_row("READY" if price_pro and price_elite else "CRITICAL", "Price IDs PRO/ELITE", "STRIPE_PRICE_PRO y STRIPE_PRICE_ELITE tienen formato price_." if price_pro and price_elite else "Faltan Price IDs o se han puesto importes en lugar de price_.", 95, "Crear productos/precios live y copiar price_ de modo real.", "stripe"))
    items.append(_row("READY" if webhook else "ACTION", "Webhook Stripe", "STRIPE_WEBHOOK_SECRET presente con whsec_." if webhook else "Sin webhook la app puede no aplicar PRO/ELITE automáticamente.", 92, "Crear webhook live/test y pegar whsec_ en Render.", "stripe"))
    items.append(_row("READY" if portal else "ACTION", "Portal del cliente", "Portal Stripe activado." if portal else "El cliente necesita gestionar tarjeta/cancelación/facturas.", 75, "Activar STRIPE_CUSTOMER_PORTAL_ENABLED y configurar portal en Stripe.", "stripe"))
    items.append(_row("READY" if payments_enabled else "CRITICAL", "Pagos habilitados", "PAYMENTS_ENABLED activo." if payments_enabled else "Pagos desactivados en Render.", 90, "Poner PAYMENTS_ENABLED=true cuando toque vender.", "stripe"))
    items.append(_row("READY" if verified else "ACTION", "Verificación bancaria/manual", "Confirmación manual STRIPE_ACCOUNT_VERIFIED=true presente." if verified else "La app no puede comprobar el IBAN/identidad de Stripe desde aquí.", 85, "Cuando Stripe esté verificado y con IBAN real, marcar STRIPE_ACCOUNT_VERIFIED=true en Render.", "stripe"))
    return {"runtime": runtime, "items": items, "live": live, "test": test, "masked": [_mask_state("STRIPE_SECRET_KEY", "sk_live_" if live else None), _mask_state("STRIPE_PRICE_PRO", "price_"), _mask_state("STRIPE_PRICE_ELITE", "price_"), _mask_state("STRIPE_WEBHOOK_SECRET", "whsec_")]}


def _environment_section() -> Dict[str, Any]:
    public_url = _env("APP_PUBLIC_URL") or _env("PUBLIC_BASE_URL") or _env("RENDER_EXTERNAL_URL")
    db_path = _env("DB_PATH") or "/data/database.db"
    items = [
        _row("READY" if _present("SECRET_KEY") else "CRITICAL", "SECRET_KEY", "Clave de sesión configurada." if _present("SECRET_KEY") else "Falta SECRET_KEY real en Render.", 96, "Generar valor largo y secreto.", "render"),
        _row("READY" if _present("AUTOMATION_SECRET") else "CRITICAL", "AUTOMATION_SECRET", "Cron protegido con secreto." if _present("AUTOMATION_SECRET") else "Sin AUTOMATION_SECRET no debes abrir cron/automatizaciones.", 96, "Poner AUTOMATION_SECRET largo y usarlo en Render Cron.", "render"),
        _row("READY" if public_url.startswith("https://") else "ACTION", "URL pública HTTPS", public_url or "Falta APP_PUBLIC_URL/PUBLIC_BASE_URL.", 80, "Usar https://bot-apuestas-crgf.onrender.com o dominio final.", "render"),
        _row("READY" if db_path.startswith("/data/") else "ACTION", "DB persistente", db_path, 88, "En Render debe apuntar a /data/database.db para no perder usuarios.", "render"),
        _row("READY" if _env("TZ") == "Europe/Madrid" and _env("APP_TIMEZONE") == "Europe/Madrid" else "ACTION", "Hora Madrid", f"TZ={_env('TZ') or '—'} · APP_TIMEZONE={_env('APP_TIMEZONE') or '—'}", 70, "Poner TZ y APP_TIMEZONE en Europe/Madrid.", "render"),
    ]
    return {"items": items, "public_url": public_url, "db_path": db_path}


def _data_channels_section() -> Dict[str, Any]:
    live_enabled = _env_bool("ENABLE_LIVE_API", True)
    odds_enabled = _env_bool("ENABLE_ODDS_API", True)
    telegram_enabled = any(_env_bool(name, False) for name in ["ENABLE_TELEGRAM_AUTO", "AUTO_SEND_TELEGRAM_PICKS", "TELEGRAM_AUTO_SEND_ENABLED", "ENABLE_TELEGRAM_AUTOMATION"])
    items = [
        _row("READY" if (not live_enabled or _present("THESPORTSDB_KEY") or _present("THESPORTSDB_API_KEY")) else "ACTION", "Directo / TheSportsDB", "Directo activo y key configurada." if (live_enabled and (_present("THESPORTSDB_KEY") or _present("THESPORTSDB_API_KEY"))) else "Live puede estar activo sin key real." if live_enabled else "Live API desactivada.", 80, "Configurar THESPORTSDB_KEY/THESPORTSDB_API_KEY para directos, escudos y highlights.", "data"),
        _row("READY" if (not odds_enabled or _present("THE_ODDS_API_KEY")) else "ACTION", "Cuotas / The Odds API", "Odds API activa con key." if odds_enabled and _present("THE_ODDS_API_KEY") else "Odds activa sin key real." if odds_enabled else "Odds API desactivada.", 82, "Configurar THE_ODDS_API_KEY para picks con cuotas reales.", "data"),
        _row("READY" if (not telegram_enabled or (_present("TELEGRAM_BOT_TOKEN") and _present("TELEGRAM_CHAT_ID") and _present("AUTOMATION_SECRET"))) else "ACTION", "Telegram producción", "Telegram tiene token, chat y secret." if telegram_enabled and _present("TELEGRAM_BOT_TOKEN") and _present("TELEGRAM_CHAT_ID") and _present("AUTOMATION_SECRET") else "Telegram auto está activo pero falta token/chat/secret." if telegram_enabled else "Telegram auto desactivado.", 85, "Completar TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID y AUTOMATION_SECRET.", "data"),
        _row("READY" if (not _env_bool("ENABLE_OPENAI", False) or _present("OPENAI_API_KEY")) else "ACTION", "SHARK/OpenAI", "OpenAI configurado o desactivado." if (not _env_bool("ENABLE_OPENAI", False) or _present("OPENAI_API_KEY")) else "ENABLE_OPENAI activo sin OPENAI_API_KEY.", 60, "Configurar OPENAI_API_KEY o desactivar ENABLE_OPENAI.", "data"),
        _row("READY" if (not _env_bool("ENABLE_PUSH_NOTIFICATIONS", False) or (_present("PUSH_VAPID_PUBLIC_KEY") and _present("PUSH_VAPID_PRIVATE_KEY"))) else "ACTION", "Push", "Push configurado o desactivado." if (not _env_bool("ENABLE_PUSH_NOTIFICATIONS", False) or (_present("PUSH_VAPID_PUBLIC_KEY") and _present("PUSH_VAPID_PRIVATE_KEY"))) else "Push activo sin claves VAPID.", 55, "Desactivar push o completar VAPID.", "data"),
    ]
    return {"items": items}


def _legal_section(root: Path, db_path: str) -> Dict[str, Any]:
    legal = legal_admin_snapshot(db_path) if callable(legal_admin_snapshot) else {"score": 0, "checks": []}
    copy_scan = _unsafe_copy_scan(root)
    routes = _route_presence(root)
    owner = _env_bool("LEGAL_OWNER_DETAILS_COMPLETED", False)
    reviewed = _env_bool("LEGAL_REVIEW_COMPLETED", False)
    items = []
    items.append(_row("READY" if all(r["ok"] for r in routes) else "CRITICAL", "Páginas legales públicas", "Rutas legales presentes." if all(r["ok"] for r in routes) else "Falta alguna página legal pública.", 90, "Revisar /legal, /terminos, /privacidad, /juego-responsable y /no-somos-casa-de-apuestas.", "legal"))
    items.append(_row("READY" if copy_scan["ok"] else "ACTION", "Copys peligrosos", "No se detectan frases obvias de garantía." if copy_scan["ok"] else f"Detectadas {copy_scan['total']} coincidencias que conviene revisar.", 88, "Eliminar promesas tipo ganancia segura, sin riesgo o beneficio garantizado.", "legal"))
    items.append(_row("READY" if owner else "ACTION", "Datos del titular", "LEGAL_OWNER_DETAILS_COMPLETED=true confirmado." if owner else "Pendiente completar titular, NIF/CIF, domicilio y email soporte en aviso legal.", 88, "Completar datos reales antes de cobrar público real.", "legal"))
    items.append(_row("READY" if reviewed else "ACTION", "Revisión profesional", "LEGAL_REVIEW_COMPLETED=true confirmado." if reviewed else "Pendiente revisión por asesoría antes de escalar.", 92, "Revisar modelo, textos, privacidad y Stripe con profesional.", "legal"))
    items.append(_row("READY", "Checkout responsable", "La capa V787/V788 exige +18, términos, privacidad, no garantía y no operador antes de Stripe.", 86, "Mantener esta puerta activa.", "legal"))
    return {"items": items, "legal": legal, "routes": routes, "copy_scan": copy_scan}


def _operational_section(root: Path) -> Dict[str, Any]:
    smoke = (root / "tools" / "smoke_flask_real_routes.py").exists()
    preflight = (root / "tools" / "render_preflight_check.py").exists()
    checks = [p.name for p in (root / "tools").glob("check_v78*.py")] if (root / "tools").exists() else []
    items = [
        _row("READY" if smoke else "ACTION", "Smoke Flask real", "tools/smoke_flask_real_routes.py presente." if smoke else "Falta smoke real para entorno con Flask.", 75, "Ejecutar en local/Render shell tras instalar requirements.", "ops"),
        _row("READY" if preflight else "ACTION", "Preflight Render", "tools/render_preflight_check.py presente." if preflight else "Falta preflight HTTP post-deploy.", 75, "Ejecutar contra la URL pública tras redeploy.", "ops"),
        _row("READY" if len(checks) >= 6 else "INFO", "Checks acumulados", f"{len(checks)} checks V78x disponibles.", 45, "Mantener checks antes de subir ZIP.", "ops"),
    ]
    return {"items": items, "checks": checks}


def real_launch_snapshot(db_path: str, app_version: str = "", root_path: str | None = None) -> Dict[str, Any]:
    root = Path(root_path or Path(__file__).resolve().parents[1])
    stripe = _stripe_section(db_path)
    env = _environment_section()
    channels = _data_channels_section()
    legal = _legal_section(root, db_path)
    ops = _operational_section(root)
    db = _database_snapshot(db_path)
    all_items = stripe["items"] + env["items"] + channels["items"] + legal["items"] + ops["items"]
    weights = {"READY": 1.0, "INFO": 0.75, "ACTION": 0.45, "CRITICAL": 0.0}
    total_priority = sum(max(1, item["priority"]) for item in all_items) or 1
    score = int(round(sum(max(1, item["priority"]) * weights.get(item["status"], 0.4) for item in all_items) / total_priority * 100))
    critical = [item for item in all_items if item["status"] == "CRITICAL"]
    actions = [item for item in all_items if item["status"] in {"CRITICAL", "ACTION"}]
    live_go = score >= 88 and not critical and _prefix("STRIPE_SECRET_KEY", "sk_live_") and _env_bool("LEGAL_REVIEW_COMPLETED", False) and _env_bool("LEGAL_OWNER_DETAILS_COMPLETED", False)
    state = "GO LIVE CONTROLADO" if live_go else "NO PASAR A LIVE TODAVÍA" if critical or not _prefix("STRIPE_SECRET_KEY", "sk_live_") else "LIVE CON ACCIONES PENDIENTES"
    return {
        "ok": True,
        "version": REAL_LAUNCH_VERSION,
        "app_version": app_version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "score": score,
        "state": state,
        "live_go": bool(live_go),
        "critical_count": len(critical),
        "action_count": len(actions),
        "sections": {"stripe": stripe, "environment": env, "channels": channels, "legal": legal, "ops": ops, "database": db},
        "items": sorted(all_items, key=lambda x: (x["status"] != "CRITICAL", x["status"] != "ACTION", -x["priority"])),
        "critical": critical,
        "actions": actions[:20],
        "production_commands": [
            "python -m pip install -r requirements.txt",
            "python tools/smoke_flask_real_routes.py",
            "python tools/render_preflight_check.py https://bot-apuestas-crgf.onrender.com",
        ],
        "manual_live_confirmations": [
            "STRIPE_ACCOUNT_VERIFIED=true cuando Stripe esté verificado con IBAN real.",
            "LEGAL_OWNER_DETAILS_COMPLETED=true cuando aviso legal tenga titular real.",
            "LEGAL_REVIEW_COMPLETED=true cuando asesoría revise el modelo y textos.",
        ],
        "safe_business_description": "Software/SaaS informativo de análisis deportivo, seguimiento de eventos, alertas y herramientas para adultos. No acepta apuestas, depósitos ni paga premios.",
        "cron_endpoints": PRODUCTION_CRON_ENDPOINTS,
    }
