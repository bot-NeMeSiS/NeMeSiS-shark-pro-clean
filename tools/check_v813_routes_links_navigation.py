#!/usr/bin/env python3
"""V813 route, link and navigation QA for NeMeSiS SHARK PRO."""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def ok(name: str, condition: bool, detail: str = "") -> bool:
    status = "OK" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[V813_ROUTES] {status} {name}{suffix}")
    return condition


def route_patterns(app_text: str) -> set[str]:
    routes: set[str] = set()
    for match in re.finditer(r"@app\.route\(\s*['\"]([^'\"]+)['\"]", app_text):
        route = match.group(1)
        routes.add(route)
        routes.add(re.sub(r"<(?:[^:<>]+:)?[^<>]+>", "<id>", route))
    return routes


def template_links() -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for path in sorted((ROOT / "templates").glob("*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for attr in ("href", "action"):
            for match in re.finditer(rf"{attr}\s*=\s*['\"]([^'\"]+)['\"]", text):
                value = match.group(1).strip()
                if value.startswith("/") and not value.startswith("//"):
                    links.append((path.name, value))
    return links


def main() -> int:
    app_text = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    routes = route_patterns(app_text)
    links = template_links()
    failures = 0

    critical_routes = {
        "/",
        "/app",
        "/sports-hub",
        "/calendar",
        "/partidos",
        "/live",
        "/directo",
        "/match/<id>",
        "/team/<id>",
        "/picks",
        "/combis",
        "/favorites",
        "/telegram",
        "/shark",
        "/profile",
        "/perfil",
        "/mi-cuenta",
        "/soporte",
        "/support",
        "/admin/dashboard",
        "/admin/control-center",
        "/admin/map",
        "/admin/data-center",
        "/admin/automation-center",
        "/admin/telegram/diagnostics",
    }
    for route in sorted(critical_routes):
        failures += not ok(f"ruta crítica {route}", route in routes)

    malformed = [
        f"{name}:{value}"
        for name, value in links
        if re.search(r"/[^/?#'\"]+=[^/?#'\"]*", value) and "?" not in value
    ]
    failures += not ok("sin enlaces con formato /ruta=valor", not malformed, ", ".join(malformed[:8]))

    href_values = {value.split("?", 1)[0] for _, value in links}
    for needed in ["/app", "/calendar", "/live", "/picks", "/shark", "/mi-cuenta", "/soporte", "/logout"]:
        failures += not ok(f"navegación cliente enlaza {needed}", needed in href_values or needed == "/soporte" and "/support" in href_values)

    failures += not ok("shell V813/V814 activo", 'data-v813-shell="true"' in base and ('data-v814-shell="true"' in base or "V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY" in read("VERSION.txt")))
    failures += not ok("SHARK flotante se oculta en /shark", ".shark-widget.is-on-shark-page" in css and "display:none" in css)
    failures += not ok("sin texto técnico en base cliente", not any(token in base.lower() for token in ("db_path", "traceback", "sqlite locked")))
    failures += not ok("sin mojibake visible en base", not any(token in base for token in ("Ã", "Â", "â€", "â†", "�")))
    failures += not ok("capa visual V813/V814 presente", "V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY" in css and ("V814_CODEX_DEEP_PROJECT_RECONCILIATION_CLIENT_ADMIN_REFERENCE_FINAL" in css or "V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY" in css))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
