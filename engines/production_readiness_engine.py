"""Production readiness snapshot for NeMeSiS SHARK PRO.

Read-only control layer for admin checks before deploying or selling the app.
It does not contact external services, send Telegram messages, mutate the DB or
require Flask. It summarizes what can be checked from the project tree and the
runtime environment without exposing secrets.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_MARKERS = (
    "V727_TELEGRAM_RELIABILITY_COMMAND_CENTER",
    "V728_FINAL_CLIENT_EXPERIENCE_MADRID_TIME_LIVE_POLISH",
    "V729_SECURITY_STABILITY_VISUAL_QA_FOUNDATION",
    "V730_ARCHITECTURE_ROUTE_HEALTH_VISUAL_QA_FOUNDATION",
    "V731_CLIENT_EXPERIENCE_QA_POLISH_FOUNDATION",
)

CRITICAL_FILES = {
    "app.py": "Aplicación Flask principal",
    "database_manager.py": "Conexión SQLite segura",
    "VERSION.txt": "Versión de release",
    "requirements.txt": "Dependencias Render",
    "Procfile": "Arranque Render",
    ".env.example": "Variables documentadas",
    ".env.render.clean": "Plantilla Render limpia",
    "templates/base.html": "Base visual y seguridad CSRF",
    "engines/madrid_time_engine.py": "Hora Europe/Madrid",
    "engines/telegram_reliability_engine.py": "Diagnóstico Telegram V727",
    "engines/client_experience_guard_engine.py": "QA cliente V731",
    "engines/route_health_engine.py": "Salud de rutas V730",
    "engines/security_engine.py": "CSRF, rate limit y SECRET_KEY V729",
    "tools/build_clean_release.py": "ZIP limpio Render Ready",
    "tools/audit_release_zip.py": "Auditor ZIP",
    "tools/check_madrid_times.py": "Auditoría hora Madrid",
    "tools/check_telegram_reliability.py": "Auditoría Telegram",
    "tools/check_v731_client_experience.py": "Auditoría cliente",
}

ADMIN_CENTERS = [
    {"route": "/admin/telegram/command-center", "label": "Telegram Command Center", "template": "admin_telegram_command_center.html"},
    {"route": "/admin/route-health", "label": "Salud de rutas", "template": "admin_route_health.html"},
    {"route": "/admin/client-experience", "label": "Experiencia cliente", "template": "admin_client_experience.html"},
    {"route": "/admin/time-diagnostics", "label": "Diagnóstico hora Madrid", "template": "admin_time_diagnostics.html"},
    {"route": "/admin/data-memory", "label": "Memoria SHARK", "template": "admin_data_memory.html"},
]

CLIENT_ROUTES = [
    "/", "/dashboard", "/sports-hub", "/live", "/calendar", "/picks", "/combis", "/shark", "/telegram", "/favorites", "/perfil", "/membership",
]

ENV_CHECKS = [
    {"name": "SECRET_KEY", "label": "SECRET_KEY estable", "required_for_render": True},
    {"name": "AUTOMATION_SECRET", "label": "Secret Cron", "required_for_render": True},
    {"name": "DB_PATH", "label": "Ruta DB", "required_for_render": True, "expected": "/data/database.db"},
    {"name": "TELEGRAM_BOT_TOKEN", "label": "Bot token Telegram", "required_for_render": False},
    {"name": "TELEGRAM_CHAT_ID", "label": "Chat/canal Telegram", "required_for_render": False, "alternatives": ["TELEGRAM_CHANNEL_ID"]},
    {"name": "PUBLIC_BASE_URL", "label": "URL pública", "required_for_render": False},
    {"name": "THE_ODDS_API_KEY", "label": "The Odds API", "required_for_render": False},
]

FORBIDDEN_ROOT_NAMES = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "v636work", "logs", "backups"}
FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".mov", ".avi", ".mkv")


def _root(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root else Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _present_env(name: str, alternatives: list[str] | None = None) -> bool:
    names = [name] + list(alternatives or [])
    return any(str(os.getenv(item) or "").strip() for item in names)


def _version_snapshot(project_root: Path, app_version: str | None = None) -> dict[str, Any]:
    version_txt = _read(project_root / "VERSION.txt").strip()
    app_text = _read(project_root / "app.py")
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', app_text)
    app_py_version = match.group(1) if match else ""
    expected = app_version or app_py_version or version_txt
    return {
        "version_txt": version_txt,
        "app_py_version": app_py_version,
        "runtime_expected": expected,
        "match": bool(version_txt and app_py_version and version_txt == app_py_version),
        "has_recent_stack": any(marker in app_text or marker in version_txt for marker in VERSION_MARKERS),
    }


def _critical_file_checks(project_root: Path) -> list[dict[str, Any]]:
    checks = []
    for rel, label in CRITICAL_FILES.items():
        path = project_root / rel
        checks.append({
            "path": rel,
            "label": label,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "severity": "OK" if path.exists() else "WARN",
        })
    return checks


def _admin_center_checks(project_root: Path) -> list[dict[str, Any]]:
    app_text = _read(project_root / "app.py")
    checks = []
    for center in ADMIN_CENTERS:
        route_exists = center["route"] in app_text
        template_path = project_root / "templates" / center["template"]
        checks.append({
            **center,
            "route_exists": route_exists,
            "template_exists": template_path.exists(),
            "ok": route_exists and template_path.exists(),
            "severity": "OK" if route_exists and template_path.exists() else "WARN",
        })
    return checks


def _env_checks() -> list[dict[str, Any]]:
    result = []
    for item in ENV_CHECKS:
        present = _present_env(item["name"], item.get("alternatives"))
        expected = item.get("expected")
        value = str(os.getenv(item["name"]) or "")
        expected_ok = True if not expected or not present else value == expected
        severity = "OK" if present and expected_ok else ("WARN" if item.get("required_for_render") else "INFO")
        result.append({
            "name": item["name"],
            "label": item["label"],
            "present": present,
            "required_for_render": bool(item.get("required_for_render")),
            "expected": expected or "",
            "expected_ok": expected_ok,
            "alternatives": item.get("alternatives", []),
            "severity": severity,
            "safe_value": "configurado" if present else "pendiente",
        })
    return result


def _tree_cleanliness(project_root: Path) -> dict[str, Any]:
    root_entries = sorted(p.name for p in project_root.iterdir()) if project_root.exists() else []
    forbidden_dirs = [name for name in root_entries if name in FORBIDDEN_ROOT_NAMES]
    forbidden_files = []
    for p in project_root.iterdir() if project_root.exists() else []:
        if p.is_file() and p.name.lower().endswith(FORBIDDEN_SUFFIXES):
            # release manifests/reports are OK; zip/db/log/media are not.
            forbidden_files.append({"name": p.name, "size_bytes": p.stat().st_size})
    release_output = project_root / "release_output"
    return {
        "root_entries": len(root_entries),
        "forbidden_dirs": forbidden_dirs,
        "forbidden_files": forbidden_files[:30],
        "forbidden_count": len(forbidden_dirs) + len(forbidden_files),
        "release_output_exists": release_output.exists(),
        "release_output_note": "OK si está excluido del ZIP" if release_output.exists() else "No existe en raíz",
        "ok": not forbidden_dirs and not forbidden_files,
    }


def _template_quality(project_root: Path) -> dict[str, Any]:
    templates_dir = project_root / "templates"
    app_css = _read(project_root / "static" / "app.css")
    base = _read(templates_dir / "base.html")
    client_templates = ["sports_hub.html", "live.html", "calendar.html", "picks.html", "combis.html", "match_detail.html"]
    time_filters = ("match_time_short", "match_time_label", "match_date_label", "madrid_time", "safe_time")
    template_checks = []
    for name in client_templates:
        text = _read(templates_dir / name)
        template_checks.append({
            "template": name,
            "exists": bool(text),
            "uses_madrid_filters": any(token in text for token in time_filters),
            "has_empty_state": any(token in text.lower() for token in ("no hay", "sin ", "aún", "preparación", "empty")),
            "size_bytes": (templates_dir / name).stat().st_size if (templates_dir / name).exists() else 0,
        })
    css_checks = {
        "mobile_media": "@media(max-width" in app_css or "@media (max-width" in app_css,
        "bottom_nav": "bottom-nav" in app_css,
        "live_state_badges": "state-badge" in app_css,
        "shark_widget": "shark-widget" in app_css,
        "v728_layer": "V728" in app_css,
        "v731_layer": "V731" in app_css,
    }
    return {
        "base_has_csrf": "csrf-token" in base or "csrf_token" in base,
        "templates": template_checks,
        "css_checks": css_checks,
        "css_score": sum(1 for ok in css_checks.values() if ok),
        "css_max_score": len(css_checks),
    }


def _score(snapshot: dict[str, Any]) -> int:
    score = 100
    if not snapshot["version"]["match"]:
        score -= 10
    score -= min(20, snapshot["tree"]["forbidden_count"] * 4)
    missing_files = sum(1 for item in snapshot["critical_files"] if not item["exists"])
    score -= min(20, missing_files * 4)
    missing_centers = sum(1 for item in snapshot["admin_centers"] if not item["ok"])
    score -= min(15, missing_centers * 3)
    required_env_missing = sum(1 for item in snapshot["env"] if item["required_for_render"] and not item["present"])
    # Environment may be absent in local/sandbox, so penalize gently.
    score -= min(12, required_env_missing * 3)
    if not snapshot["templates"]["base_has_csrf"]:
        score -= 7
    if snapshot["templates"]["css_score"] < snapshot["templates"]["css_max_score"]:
        score -= 5
    return max(0, min(100, score))


def production_readiness_snapshot(root: str | Path | None = None, app_version: str | None = None) -> dict[str, Any]:
    """Return a safe admin snapshot for release/production readiness."""
    project_root = _root(root)
    snapshot: dict[str, Any] = {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "version": _version_snapshot(project_root, app_version),
        "critical_files": _critical_file_checks(project_root),
        "admin_centers": _admin_center_checks(project_root),
        "env": _env_checks(),
        "tree": _tree_cleanliness(project_root),
        "templates": _template_quality(project_root),
        "render_checks": [
            {"label": "runtime-version", "route": "/api/runtime-version", "expected": app_version or _version_snapshot(project_root, app_version)["runtime_expected"]},
            {"label": "health", "route": "/api/health", "expected": "200 / OK si existe"},
            {"label": "Cron Telegram sin secret", "route": "/api/automation/telegram/tick", "expected": "403"},
            {"label": "Cron Telegram con secret", "route": "/api/automation/telegram/tick?secret=***", "expected": "200"},
            {"label": "Daily sin secret", "route": "/api/automation/daily/run", "expected": "403"},
            {"label": "Daily con secret", "route": "/api/automation/daily/run?secret=***", "expected": "200"},
        ],
    }
    snapshot["score"] = _score(snapshot)
    snapshot["status"] = "OK" if snapshot["score"] >= 85 else ("REVISAR" if snapshot["score"] >= 70 else "ATENCIÓN")
    blockers: list[str] = []
    warnings: list[str] = []
    if not snapshot["version"]["match"]:
        blockers.append("VERSION.txt y APP_VERSION no coinciden.")
    if any(not item["exists"] for item in snapshot["critical_files"]):
        warnings.append("Faltan archivos críticos del release; revisar lista de archivos.")
    if snapshot["tree"]["forbidden_count"]:
        warnings.append("Hay basura local en raíz; el ZIP puede estar limpio, pero conviene purgar o excluir.")
    if any(item["required_for_render"] and not item["present"] for item in snapshot["env"]):
        warnings.append("Faltan variables críticas en este entorno local/sandbox; confirmar en Render antes de vender.")
    if not snapshot["templates"]["base_has_csrf"]:
        blockers.append("base.html no parece inyectar CSRF.")
    snapshot["blockers"] = blockers
    snapshot["warnings"] = warnings
    snapshot["recommended_next_steps"] = [
        "Subir ZIP limpio a Render y confirmar /api/runtime-version.",
        "Confirmar DB_PATH=/data/database.db y disco persistente en Render.",
        "Probar Cron Telegram/Daily 403 sin secret y 200 con secret sin compartir secrets.",
        "Entrar en /admin/telegram/command-center para ver causa real si Telegram no envía.",
        "Revisar /admin/client-experience y /admin/route-health tras cada release.",
        "Grabar QA móvil real de Home, Calendar, Live, Picks, Combis, SHARK, Telegram y Match Detail.",
    ]
    snapshot["note"] = "Snapshot local/read-only. No certifica Render real sin URL/logs/capturas de producción."
    return snapshot
