"""User/admin journey checks for Autonomous Sentinel Worker."""
from __future__ import annotations

import re
from typing import Any


CLIENT_ROUTES = [
    "/",
    "/cliente-login",
    "/registro",
    "/app",
    "/calendar",
    "/partidos",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/profile",
    "/telegram",
    "/support",
    "/track-record",
    "/combis",
    "/mercados",
    "/favorites",
]

ADMIN_ROUTES = [
    "/admin-login",
    "/admin/dashboard",
    "/admin/telegram/command-center",
    "/admin/sentinel-autopilot",
    "/admin/visual-worker",
    "/admin/sentinel-issues",
    "/admin/daily-automation",
    "/admin/data-center",
    "/admin/users",
    "/admin/memberships",
    "/admin/payments",
    "/admin/final-certification",
]

ROLES = ["anonymous", "FREE", "PRO", "ELITE", "ADMIN"]
DEVICES = ["desktop_1440x900", "mobile_390x844", "tablet_static"]

MOJIBAKE_RE = re.compile(r"(Ãƒ|Ã‚|ï¿½|Ã¯Â¿Â½|EspaÃ|MÃ³vil|CrÃ|SÃ­)")
TECHNICAL_RE = re.compile(r"\b(None|null|undefined|Traceback|sqlite3\.|werkzeug\.)\b", re.I)
BAD_LINK_RE = re.compile(r"href=[\"'](?:#|javascript:void\(0\)|javascript:;|)[\"']", re.I)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
PROTECTED_CLIENT_ROUTES = {"/app", "/profile", "/telegram", "/favorites"}


def _text(response: Any) -> str:
    try:
        return response.get_data(as_text=True) or ""
    except Exception:
        return ""


def _visible_text(html: str) -> str:
    cleaned = SCRIPT_STYLE_RE.sub(" ", html or "")
    cleaned = TAG_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _issue(title: str, area: str, route: str, severity: str, evidence: str, source: str = "autonomous_worker") -> dict[str, Any]:
    return {
        "title": title,
        "area": area,
        "route": route,
        "severity": severity,
        "source": source,
        "evidence": evidence[:800],
        "impact": "Puede degradar experiencia cliente/admin o generar falsa confianza operativa.",
        "recommendation": "Revisar la causa real, corregir de forma segura y revalidar con Sentinel.",
        "validation": [
            "python -m py_compile app.py",
            "python tools/run_continuous_sentinel_static.py",
        ],
        "tags": [area, "autonomous_sentinel"],
    }


def inspect_route_html(route: str, status_code: int, html: str, admin_expected: bool = False) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    lower = html.lower()
    visible = _visible_text(html)
    if status_code >= 500:
        issues.append(_issue("Ruta devuelve error 500/502", "route", route, "critical", f"HTTP {status_code}"))
    elif status_code == 404:
        issues.append(_issue("Ruta no disponible", "route", route, "medium", "ROUTE_MISSING_OR_NOT_AVAILABLE"))
    elif status_code in {301, 302, 303, 307, 308}:
        if admin_expected or route in {"/cliente-login", "/registro"} or route in PROTECTED_CLIENT_ROUTES:
            pass
        else:
            issues.append(_issue("Ruta redirige y requiere revision de flujo", "buttons_routes", route, "low", f"HTTP {status_code}"))
    if html and BAD_LINK_RE.search(html):
        issues.append(_issue("Link falso detectado", "buttons_routes", route, "medium", "href # o javascript:void(0)"))
    if visible and TECHNICAL_RE.search(visible):
        issues.append(_issue("Texto tecnico visible", "texts", route, "medium", "None/null/undefined/Traceback/sqlite visible"))
    if visible and MOJIBAKE_RE.search(visible):
        issues.append(_issue("Mojibake visible", "texts", route, "medium", "Caracteres rotos tipo Ã/Â/�"))
    if admin_expected and route != "/admin-login" and status_code == 200 and ("bottom-nav-clean" in html or "ns-client-sidebar" in html or "sharkFab" in html):
        issues.append(_issue("Navegacion cliente aparece en admin", "admin", route, "high", "bottom nav/sidebar/floating SHARK detectado en admin"))
    if not admin_expected and route.startswith("/admin"):
        issues.append(_issue("Ruta admin dentro de journey cliente", "security", route, "medium", "Cruce cliente/admin"))
    if route in {"/picks", "/telegram"} and "apuesta segura" in lower:
        issues.append(_issue("Claim de apuesta garantizada", "security", route, "critical", "Copy irresponsable detectado"))
    return issues


def run_user_journey_checks(flask_client: Any, mode: str = "safe_scan") -> dict[str, Any]:
    routes = CLIENT_ROUTES + ADMIN_ROUTES
    checked: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for route in routes:
        try:
            response = flask_client.get(route)
            html = _text(response)
            checked.append({"route": route, "status_code": response.status_code, "bytes": len(html)})
            issues.extend(inspect_route_html(route, response.status_code, html, admin_expected=route.startswith("/admin")))
        except Exception as exc:
            checked.append({"route": route, "status_code": 0, "error": str(exc)[:180]})
            issues.append(_issue("Ruta lanza excepcion en journey", "route", route, "critical", str(exc)[:500]))
    return {
        "mode": mode,
        "routes_checked": len(checked),
        "roles": ROLES,
        "devices": DEVICES,
        "checked": checked,
        "issues": issues,
    }
