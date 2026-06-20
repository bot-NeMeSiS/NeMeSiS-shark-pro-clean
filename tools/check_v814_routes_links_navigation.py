#!/usr/bin/env python3
"""V814 route, link and navigation QA."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def ok(name: str, condition: bool, detail: str = "") -> bool:
    print(f"[V814_ROUTES] {'OK' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")
    return bool(condition)


def route_patterns(app_text: str) -> set[str]:
    found: set[str] = set()
    for match in re.finditer(r"@app\.route\(\s*['\"]([^'\"]+)['\"]", app_text):
        route = match.group(1)
        found.add(route)
        found.add(re.sub(r"<(?:[^:<>]+:)?[^<>]+>", "<id>", route))
    return found


def template_links() -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for path in sorted((ROOT / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for attr in ("href", "action"):
            for match in re.finditer(rf"{attr}\s*=\s*['\"]([^'\"]+)['\"]", text):
                value = match.group(1).strip()
                if value.startswith("/") and not value.startswith("//"):
                    links.append((path.relative_to(ROOT).as_posix(), value))
    return links


def main() -> int:
    failures = 0
    app_text = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    routes = route_patterns(app_text)
    links = template_links()
    href_values = {value.split("?", 1)[0] for _, value in links}

    critical_client = {
        "/", "/app", "/calendar", "/partidos", "/live", "/directo", "/picks",
        "/match/<id>", "/team/<id>", "/shark", "/shark-core", "/telegram",
        "/profile", "/perfil", "/mi-cuenta", "/favorites", "/track-record",
        "/support", "/soporte", "/logout",
    }
    critical_admin = {
        "/admin/dashboard", "/admin/map", "/admin/control-center", "/admin/users",
        "/admin/memberships", "/admin/matches-sync", "/admin/data-center",
        "/admin/data-memory", "/admin/data-vault", "/admin/automation-center",
        "/admin/telegram/command-center", "/admin/telegram/pro-preview",
        "/admin/live-depth", "/admin/final-certification", "/admin/payments",
        "/admin/track-record", "/admin/highlights-center", "/admin/visual-experience",
        "/admin/go-live", "/admin/client-success", "/admin/public-launch",
        "/admin/route-health", "/admin/client-experience", "/admin/sale-ready",
        "/admin/final-release",
    }
    for route in sorted(critical_client | critical_admin):
        failures += not ok(f"ruta crÃ­tica {route}", route in routes)

    malformed = [
        f"{name}:{value}"
        for name, value in links
        if re.search(r"/[^/?#'\"]+=[^/?#'\"]*", value) and "?" not in value
    ]
    failures += not ok("sin query strings mal formadas", not malformed, ", ".join(malformed[:10]))

    for needed in ["/app", "/calendar", "/live", "/picks", "/shark", "/mi-cuenta", "/logout"]:
        failures += not ok(f"cliente enlaza {needed}", needed in href_values)
    for needed in ["/admin/control-center", "/admin/map", "/admin/users", "/admin/data-center", "/admin/telegram/command-center", "/admin/automation-center", "/logout"]:
        failures += not ok(f"admin enlaza {needed}", needed in href_values)

    failures += not ok("shell V814 activo", 'data-v814-shell="true"' in base)
    failures += not ok("capa visual V814 presente", "V814_CODEX_DEEP_PROJECT_RECONCILIATION_CLIENT_ADMIN_REFERENCE_FINAL" in css)
    failures += not ok("cliente sin rail antiguo activo", "v798-client-rail" in css and "display:none" in css)
    failures += not ok("un solo widget SHARK en base", base.count('class="shark-widget"') == 1)
    failures += not ok("SHARK flotante ocultable en /shark", ".shark-widget.is-on-shark-page" in css and "display:none" in css)
    failures += not ok("salir visible", "/logout" in base)
    failures += not ok("sin texto tÃ©cnico base", not any(token in base.lower() for token in ("db_path", "traceback", "sqlite locked", "internal server error")))
    failures += not ok("sin mojibake visible base", not any(token in base for token in ("Ãƒ", "Ã‚", "Ã¢â‚¬", "Ã¢â€ ", "ï¿½")))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())


