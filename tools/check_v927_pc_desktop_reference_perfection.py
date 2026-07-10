#!/usr/bin/env python3
"""Release identity, safety, runtime and ZIP audit for V927."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V927_PC_DESKTOP_REFERENCE_PERFECTION_ADMIN_CLIENT_SPORTS_FINAL"
V928_VERSION = "V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL"
ZIP = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REQUIRED_ROOT = {
    "app.py",
    "VERSION.txt",
    "requirements.txt",
    "templates",
    "static",
    "engines",
    "tools",
    "reports",
    "reference_images",
    "browser_qa",
    "automation_workforce",
    ".github",
}
FORBIDDEN_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "release_output", "releases", "logs"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".zip", ".pyc", ".pyo"}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def app_version(source: str) -> str:
    match = re.search(r"^APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", source, re.MULTILINE)
    return match.group(1) if match else ""


def audit_zip() -> dict:
    if not ZIP.exists():
        return {"exists": False, "forbidden_count": 0, "missing_required_root": sorted(REQUIRED_ROOT)}
    forbidden: list[str] = []
    top_level: set[str] = set()
    with zipfile.ZipFile(ZIP) as archive:
        for name in archive.namelist():
            path = PurePosixPath(name)
            if not path.parts:
                continue
            top_level.add(path.parts[0])
            lower_parts = {part.lower() for part in path.parts}
            if lower_parts & FORBIDDEN_PARTS or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                forbidden.append(name)
            if path.name.lower() == ".env":
                forbidden.append(name)
    return {
        "exists": True,
        "forbidden_count": len(set(forbidden)),
        "forbidden": sorted(set(forbidden))[:20],
        "missing_required_root": sorted(REQUIRED_ROOT - top_level),
    }


def main() -> int:
    failures: list[str] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    version_text = version_bytes.decode("utf-8-sig", errors="replace").strip()
    source = read("app.py")
    css = read("static/app.css")
    template_names = (
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
    templates = {name: read(f"templates/{name}.html") for name in template_names}

    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt contains UTF-8 BOM")
    is_v928 = version_text == V928_VERSION
    if version_text not in {VERSION, V928_VERSION}:
        failures.append(f"VERSION.txt mismatch: {version_text}")
    if app_version(source) != version_text:
        failures.append(f"APP_VERSION mismatch: {app_version(source)}")

    flags = (
        "has_v927_pc_desktop_reference_perfection",
        "has_v927_admin_pc_command_center_perfection",
        "has_v927_client_pc_dashboard_perfection",
        "has_v927_sports_pc_value_perfection",
        "has_v927_desktop_layout_quality_guard",
    )
    for flag in flags:
        if flag not in source:
            failures.append(f"missing runtime flag: {flag}")

    css_markers = (
        "/* V927 PC desktop reference perfection */",
        ".v927-desktop-shell",
        ".v927-desktop-grid",
        ".v927-desktop-above-fold",
        ".v927-desktop-sidebar",
        ".v927-desktop-main",
        ".v927-desktop-aside",
        ".v927-kpi-deck",
        ".v927-kpi-card",
        ".v927-action-card",
        ".v927-reference-button",
        ".v927-reference-icon",
        ".v927-reference-logo-slot",
        ".v927-status-strip",
        ".v927-data-toolbar",
        ".v927-filter-tabs",
        ".v927-table-card",
        ".v927-compact-section",
        ".v927-no-dead-space",
        ".v927-pc-command-row",
        ".v927-admin-desktop-shell",
        ".v927-admin-command-center",
        ".v927-admin-kpi-deck",
        ".v927-admin-ops-grid",
        ".v927-admin-worker-card",
        ".v927-admin-runtime-card",
        ".v927-admin-table-area",
        ".v927-client-desktop-shell",
        ".v927-client-hero-row",
        ".v927-client-quick-actions",
        ".v927-client-sports-overview",
        ".v927-client-value-grid",
        ".v927-client-next-action",
        ".v927-sports-desktop-board",
        ".v927-sports-filters",
        ".v927-match-desktop-card",
        ".v927-odds-desktop-card",
        ".v927-live-desktop-card",
        ".v927-picks-desktop-grid",
        "@media (min-width: 1024px)",
    )
    for marker in css_markers:
        if marker not in css:
            failures.append(f"missing V927 CSS marker: {marker}")

    template_markers = {
        "home": "data-v927-template=\"home-public\"",
        "client_app_center": "data-v927-template=\"client_app_center\"",
        "calendar": "data-v927-template=\"calendar\"",
        "live": "data-v927-template=\"live\"",
        "picks": "data-v927-template=\"picks\"",
        "shark": "data-v927-template=\"shark\"",
        "telegram": "data-v927-template=\"telegram\"",
        "profile": "data-v927-template=\"profile\"",
        "membership": "data-v927-template=\"membership\"",
        "admin_dashboard": "data-v927-template=\"admin_dashboard\"",
        "admin_automation_workforce": "data-v927-template=\"admin_automation_workforce\"",
        "admin_autonomous_company_sentinel": "data-v927-template=\"admin_autonomous_company_sentinel\"",
        "admin_sentinel_issues": "data-v927-template=\"admin_sentinel_issues\"",
        "admin_sentinel_codex_outbox": "data-v927-template=\"admin_sentinel_codex_outbox\"",
        "admin_telegram_command_center": "data-v927-template=\"admin_telegram_command_center\"",
    }
    if is_v928:
        template_markers = {
            "home": 'data-v928-template="home"',
            "client_app_center": 'data-v928-template="client_app_center"',
            "calendar": 'data-v928-template="calendar"',
            "live": 'data-v928-template="live"',
            "picks": 'data-v928-template="picks"',
            "shark": 'data-v928-template="shark"',
            "telegram": 'data-v928-template="telegram"',
            "profile": 'data-v928-template="profile"',
            "membership": 'data-v928-template="membership"',
            "admin_dashboard": 'data-v928-template="admin_dashboard"',
            "admin_automation_workforce": 'data-v928-template="admin_automation_workforce"',
            "admin_autonomous_company_sentinel": 'data-v928-template="admin_autonomous_company_sentinel"',
            "admin_sentinel_issues": 'data-v928-template="admin_sentinel_issues"',
            "admin_sentinel_codex_outbox": 'data-v928-template="admin_sentinel_codex_outbox"',
            "admin_telegram_command_center": 'data-v928-template="admin_telegram_command_center"',
        }
    for name, marker in template_markers.items():
        if marker not in templates[name]:
            failures.append(f"{name} missing marker: {marker}")

    if is_v928:
        if "v928-home-hero" not in templates["home"] or 'data-v928-template="home"' not in templates["home"]:
            failures.append("home is missing the V928 canonical hero")
    elif sum("v925-public-hero" in value.split() for value in re.findall(r'class="([^"]*)"', templates["home"])) != 1:
        failures.append("home has a duplicated or missing public hero")
    for helper in (
        "get_safe_sports_calendar_context",
        "get_safe_live_context",
        "get_safe_picks_context",
        "get_safe_odds_context",
    ):
        if f"def {helper}" not in source:
            failures.append(f"missing safe context helper: {helper}")
    if source.count('"no_render_api_call": True') < 4:
        failures.append("safe sports contexts do not all block render-time API calls")
    if '"v927_pixel_perfect_claim_allowed": False' not in source:
        failures.append("V927 pixel-perfect claim is not explicitly false")

    admin_text = "\n".join(value for key, value in templates.items() if key.startswith("admin_"))
    if "Salir cliente" in admin_text:
        failures.append("admin/client navigation mix found")
    normalized_admin = re.sub(r"\s+", "", admin_text).lower()
    for stale in ("capturas0", "comparaciones18"):
        if stale in normalized_admin:
            failures.append(f"stale admin label found: {stale}")
    for prefix in ("sk_live_", "xoxb-", "ghp_", "github_pat_", "rnd_"):
        if prefix in source + css + admin_text:
            failures.append(f"suspicious secret prefix found: {prefix}")

    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v927_release.sqlite"))
    os.environ.setdefault("FLASK_ENV", "testing")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    http = app_module.app.test_client()
    routes = (
        "/", "/cliente-login", "/registro", "/app", "/calendar", "/calendario",
        "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support",
        "/admin-login", "/admin/dashboard", "/admin/automation-workforce",
        "/admin/autonomous-company-sentinel", "/admin/sentinel-issues",
        "/admin/sentinel-codex-outbox", "/admin/telegram/command-center",
        "/api/admin/automation-workforce/status", "/api/runtime-version", "/ruta-inventada",
        "/api/ruta-inventada", "/manifest.json", "/service-worker.js",
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
        failures.append("admin workforce API is not protected")
    if smoke.get("/ruta-inventada") != 404 or smoke.get("/api/ruta-inventada") != 404:
        failures.append("404 contracts are not safe")

    runtime = http.get("/api/runtime-version").get_json() or {}
    if runtime.get("version") != version_text:
        failures.append("runtime version does not match the active V927+ container")
    if runtime.get("version_files_match") is not True:
        failures.append("runtime version files do not match")
    if runtime.get("deployment_alignment_status") != "aligned_local_files":
        failures.append("runtime local files are not aligned")
    for flag in flags:
        if runtime.get(flag) is not True:
            failures.append(f"runtime flag false: {flag}")
    if runtime.get("v927_pixel_perfect_claim_allowed") is not False:
        failures.append("runtime wrongly allows pixel-perfect claim")

    for template in (ROOT / "templates").glob("*.html"):
        try:
            app_module.app.jinja_env.parse(template.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception as exc:
            failures.append(f"Jinja parse failed {template.name}: {exc.__class__.__name__}")

    zip_audit = audit_zip()
    if not zip_audit["exists"]:
        failures.append("V927 release ZIP is missing")
    if zip_audit["forbidden_count"]:
        failures.append("V927 release ZIP contains forbidden files")
    if zip_audit["missing_required_root"]:
        failures.append(f"V927 ZIP missing root entries: {zip_audit['missing_required_root']}")

    result = {
        "ok": not failures,
        "version": version_text,
        "failures": failures,
        "smoke": smoke,
        "runtime": {
            "version": runtime.get("version"),
            "version_files_match": runtime.get("version_files_match"),
            "deployment_alignment_status": runtime.get("deployment_alignment_status"),
            "v927_browser_qa_still_required": runtime.get("v927_browser_qa_still_required"),
            "v927_pixel_perfect_claim_allowed": runtime.get("v927_pixel_perfect_claim_allowed"),
        },
        "zip_audit": zip_audit,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
