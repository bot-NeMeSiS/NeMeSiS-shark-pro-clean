"""V773 app/video UX quality snapshot helpers."""
from __future__ import annotations

from pathlib import Path

CLIENT_CRITICAL_ROUTES = ["/", "/app", "/calendar", "/partidos", "/live", "/picks", "/combis", "/mercados", "/highlights", "/track-record", "/shark", "/menu"]
ADMIN_CRITICAL_ROUTES = ["/admin/control-center", "/admin/telegram/command-center", "/admin/data-marketplace", "/admin/automation-center", "/admin/app-experience-quality", "/admin/final-certification", "/admin/highlights-center"]
TECH_MARKERS = ["Traceback", "sqlite3.OperationalError", "UndefinedError", "NoneType", "admin 123", "demo Damian", "UTC crudo"]
MOJIBAKE_MARKERS = ["\u00c3", "\u00c2", "\ufffd", "\u00e2\u20ac"]


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def _template_scan(template_root: str) -> dict:
    root = Path(template_root)
    files = sorted(root.glob("*.html")) if root.exists() else []
    mojibake = []
    technical = []
    for path in files:
        text = _read(str(path))
        bad = [m for m in MOJIBAKE_MARKERS if m in text]
        tech = [m for m in TECH_MARKERS if m.lower() in text.lower()]
        if bad:
            mojibake.append({"file": path.name, "markers": bad[:6]})
        if tech:
            technical.append({"file": path.name, "markers": tech[:6]})
    return {"templates": len(files), "mojibake": mojibake, "technical_markers": technical}


def _css_scan(static_css_path: str) -> dict:
    css = _read(static_css_path)
    required = [".nav-clean", ".bottom-nav-clean", ".shark-widget", ".v773-quality-hero", ".v773-admin-rail"]
    return {
        "css_exists": bool(css),
        "required_tokens": [{"token": token, "ok": token in css} for token in required],
        "has_responsive_rules": "@media" in css,
        "size_bytes": len(css.encode("utf-8")),
    }


def build_v773_app_experience_quality_snapshot(app_version: str, registered_routes: list[str], template_root: str, static_css_path: str) -> dict:
    registered = set(registered_routes or [])
    client = [{"route": route, "ok": route in registered} for route in CLIENT_CRITICAL_ROUTES]
    admin = [{"route": route, "ok": route in registered} for route in ADMIN_CRITICAL_ROUTES]
    templates = _template_scan(template_root)
    css = _css_scan(static_css_path)
    route_score = int(100 * (len([r for r in client + admin if r["ok"]]) / max(1, len(client + admin))))
    text_score = 100 - min(45, len(templates["mojibake"]) * 15 + len(templates["technical_markers"]) * 5)
    css_score = 65 + len([r for r in css["required_tokens"] if r["ok"]]) * 7
    score = min(100, round(route_score * .45 + text_score * .30 + css_score * .25))
    return {
        "version": app_version,
        "score": score,
        "status": "READY" if score >= 88 else ("REVIEW" if score >= 72 else "FIX_REQUIRED"),
        "client_routes": client,
        "admin_routes": admin,
        "templates": templates,
        "css": css,
        "video_review_findings": [
            "El ZIP real ya venía en V772, pero faltaban centros V770 de datos comerciales/automatización descritos en el resumen; se reintroducen de forma segura.",
            "En el vídeo se aprecia navegación admin/cliente muy cargada; V773 refuerza scroll horizontal, estados activos y rail compacto sin borrar accesos.",
            "Había mojibake en pantallas admin de Telegram/Data Center; V773 limpia los textos corruptos detectados.",
            "SHARK flotante y bottom nav reciben límites visuales para no tapar cards principales en pantallas estrechas.",
        ],
        "guardrails": [
            "No inventar partidos, picks, cuotas, resultados ni ROI.",
            "No exportar datos personales ni secretos.",
            "Mantener Telegram/Cron/DB_PATH/Madrid Time intactos.",
            "Admin técnico separado del cliente.",
        ],
    }
