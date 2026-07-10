#!/usr/bin/env python3
"""Rendered desktop quality and route-contract checks for V927."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def main() -> int:
    failures: list[str] = []
    templates = {
        name: read(f"templates/{name}.html")
        for name in (
            "home",
            "client_app_center",
            "calendar",
            "live",
            "picks",
            "shark",
            "telegram",
            "profile",
            "membership",
            "admin_dashboard",
            "admin_automation_workforce",
            "admin_autonomous_company_sentinel",
            "admin_sentinel_issues",
            "admin_sentinel_codex_outbox",
            "admin_telegram_command_center",
        )
    }
    css = read("static/app.css")

    required_markers = {
        "home": ("data-v927-template=\"home-public\"", "v927-kpi-deck", "v927-client-value-grid"),
        "client_app_center": ("data-v927-template=\"client_app_center\"", "v927-client-sports-overview", "Siguiente paso"),
        "calendar": ("data-v927-template=\"calendar\"", "v927-data-toolbar", "v927-sports-filters"),
        "live": ("data-v927-template=\"live\"", "v927-data-toolbar", "v927-filter-tabs"),
        "picks": ("data-v927-template=\"picks\"", "v927-table-card", "Los candidatos incompletos"),
        "shark": ("data-v927-template=\"shark\"", "v927-client-next-action"),
        "telegram": ("data-v927-template=\"telegram\"", "v927-pc-command-row"),
        "profile": ("data-v927-template=\"profile\"", "v927-reference-logo-slot"),
        "membership": ("data-v927-template=\"membership\"", "v927-client-value-grid"),
        "admin_dashboard": ("data-v927-template=\"admin_dashboard\"", "v927-admin-command-center", "Siguiente accion visible"),
        "admin_automation_workforce": ("data-v927-template=\"admin_automation_workforce\"", "v927-admin-worker-card"),
        "admin_autonomous_company_sentinel": ("data-v927-template=\"admin_autonomous_company_sentinel\"", "v927-admin-kpi-deck"),
        "admin_sentinel_issues": ("data-v927-template=\"admin_sentinel_issues\"", "v927-admin-table-area"),
        "admin_sentinel_codex_outbox": ("data-v927-template=\"admin_sentinel_codex_outbox\"", "v927-table-card"),
        "admin_telegram_command_center": ("data-v927-template=\"admin_telegram_command_center\"", "v927-admin-ops-grid"),
    }
    for name, markers in required_markers.items():
        for marker in markers:
            if marker not in templates[name]:
                failures.append(f"{name} missing V927 marker: {marker}")

    if sum("v925-public-hero" in value.split() for value in re.findall(r'class="([^"]*)"', templates["home"])) != 1:
        failures.append("public home has a duplicated or missing primary hero")
    if "/* V927 PC desktop reference perfection */" not in css:
        failures.append("V927 CSS layer is missing")
    if "@media (min-width: 1024px)" not in css:
        failures.append("desktop breakpoint is missing")
    if ".v927-no-dead-space" not in css or "padding-top: 8px !important" not in css:
        failures.append("desktop top-space guard is missing")

    admin_text = "\n".join(value for key, value in templates.items() if key.startswith("admin_"))
    if "Salir cliente" in admin_text:
        failures.append("client logout copy leaked into admin templates")
    compact_admin = re.sub(r"\s+", "", admin_text).lower()
    for stale in ("capturas0", "comparaciones18"):
        if stale in compact_admin:
            failures.append(f"stale Browser QA copy found: {stale}")
    if "BLOCKED_NO_SCREENSHOT" not in templates["admin_sentinel_codex_outbox"]:
        failures.append("outbox does not explain the screenshot evidence gate")

    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v927_layout.sqlite"))
    os.environ.setdefault("FLASK_ENV", "testing")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    http = app_module.app.test_client()
    routes = (
        "/",
        "/cliente-login",
        "/registro",
        "/app",
        "/calendar",
        "/calendario",
        "/live",
        "/directo",
        "/picks",
        "/shark",
        "/telegram",
        "/profile",
        "/support",
        "/admin-login",
        "/admin/dashboard",
        "/admin/automation-workforce",
        "/admin/autonomous-company-sentinel",
        "/admin/sentinel-issues",
        "/admin/sentinel-codex-outbox",
        "/admin/telegram/command-center",
        "/api/admin/automation-workforce/status",
        "/api/runtime-version",
        "/ruta-inventada",
        "/api/ruta-inventada",
        "/manifest.json",
        "/service-worker.js",
    )
    smoke: dict[str, int] = {}
    for route in routes:
        response = http.get(route, follow_redirects=False)
        smoke[route] = response.status_code
        if response.status_code >= 500:
            failures.append(f"route returned {response.status_code}: {route}")
    for route in ("/", "/cliente-login", "/registro", "/calendar", "/live", "/picks", "/support", "/admin-login"):
        if smoke.get(route) != 200:
            failures.append(f"critical route is not 200: {route}={smoke.get(route)}")
    if smoke.get("/api/admin/automation-workforce/status") != 403:
        failures.append("admin workforce API is not protected with 403")
    if smoke.get("/ruta-inventada") != 404 or smoke.get("/api/ruta-inventada") != 404:
        failures.append("HTML/JSON 404 contract is broken")

    rendered_home = http.get("/").get_data(as_text=True)
    if rendered_home.count("<h1") != 1:
        failures.append("rendered public home does not contain exactly one H1")
    rendered_hero_count = sum(
        "v925-public-hero" in value.split()
        for value in re.findall(r'class="([^"]*)"', rendered_home)
    )
    if rendered_hero_count != 1:
        failures.append("rendered public home does not contain exactly one hero")
    if "v927-desktop-above-fold" not in rendered_home:
        failures.append("rendered home is missing the V927 above-fold marker")

    result = {
        "ok": not failures,
        "version": VERSION,
        "failures": failures,
        "smoke": smoke,
        "hero_count": rendered_hero_count,
        "rendered_h1_count": rendered_home.count("<h1"),
        "desktop_breakpoint": 1024,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
