from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V926_DESKTOP_REFERENCE_MODEL_COMMAND_CENTER_AND_SPORTS_VALUE_PASS_FINAL"
ZIP_PATH = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
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
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def app_version(source: str) -> str:
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "APP_VERSION" for target in node.targets):
            return str(getattr(node.value, "value", ""))
    return ""


def audit_zip(failures: list[str]) -> dict:
    if not ZIP_PATH.exists():
        return {"status": "not_built_yet", "forbidden_count": None, "missing_required_root": None}
    forbidden = []
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = [name.replace("\\", "/") for name in archive.namelist() if not name.endswith("/")]
    roots = {name.split("/", 1)[0] for name in names}
    missing = sorted(REQUIRED_ROOT - roots)
    for name in names:
        low = name.lower()
        if low.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".log", ".pyc", ".pyo")) or any(
            marker in f"/{low}/"
            for marker in ("/.git/", "/.venv/", "/__pycache__/", "/.pytest_cache/", "/release_output/")
        ):
            forbidden.append(name)
    if forbidden:
        failures.append(f"ZIP contains forbidden entries: {forbidden[:5]}")
    if missing:
        failures.append(f"ZIP missing required root: {missing}")
    return {"status": "audited", "forbidden_count": len(forbidden), "missing_required_root": missing}


def main() -> int:
    failures: list[str] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    version_text = version_bytes.decode("utf-8")
    app_source = read("app.py")
    css = read("static/app.css")
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
            "admin_dashboard",
            "admin_automation_workforce",
            "admin_autonomous_company_sentinel",
            "admin_sentinel_issues",
            "admin_sentinel_codex_outbox",
            "admin_telegram_command_center",
        )
    }

    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt has UTF-8 BOM")
    if version_text.strip() != VERSION:
        failures.append(f"VERSION.txt mismatch: {version_text.strip()}")
    if app_version(app_source) != VERSION:
        failures.append(f"APP_VERSION mismatch: {app_version(app_source)}")

    for flag in (
        "has_v926_desktop_reference_model_pass",
        "has_v926_admin_desktop_command_center",
        "has_v926_client_desktop_dashboard",
        "has_v926_sports_desktop_boards",
        "has_v926_desktop_empty_space_fix",
    ):
        if flag not in app_source:
            failures.append(f"missing runtime flag {flag}")

    required_css = (
        "/* V926 desktop reference model */",
        ".v926-desktop-shell",
        ".v926-desktop-grid",
        ".v926-desktop-two-col",
        ".v926-desktop-three-col",
        ".v926-desktop-command-center",
        ".v926-desktop-kpi-row",
        ".v926-desktop-data-table",
        ".v926-desktop-side-panel",
        ".v926-desktop-main-panel",
        ".v926-desktop-sticky-actions",
        ".v926-desktop-sports-board",
        ".v926-desktop-odds-board",
        ".v926-desktop-live-board",
        ".v926-desktop-picks-board",
        "@media (min-width: 1024px)",
    )
    for marker in required_css:
        if marker not in css:
            failures.append(f"missing CSS marker {marker}")

    if templates["home"].count('class="v925-public-hero v925-above-fold"') != 1:
        failures.append("home contains a duplicated or missing hero")
    template_markers = {
        "home": "v926-home-desktop",
        "client_app_center": "v926-client-dashboard",
        "calendar": "v926-desktop-sports-board",
        "live": "v926-desktop-live-board",
        "picks": "v926-desktop-picks-board",
        "shark": "v926-shark-desktop",
        "telegram": "v926-telegram-desktop",
        "admin_dashboard": "v926-desktop-command-center",
        "admin_automation_workforce": "v926-desktop-command-center",
        "admin_autonomous_company_sentinel": "v926-desktop-command-center",
        "admin_sentinel_issues": "v926-desktop-command-center",
        "admin_sentinel_codex_outbox": "v926-desktop-command-center",
        "admin_telegram_command_center": "v926-desktop-command-center",
    }
    for name, marker in template_markers.items():
        if marker not in templates[name]:
            failures.append(f"{name} missing desktop marker {marker}")

    if "safe_picks_context.get('picks')" not in templates["picks"] or "ready_picks" not in templates["picks"]:
        failures.append("picks desktop board is not gated by safe picks")
    if app_source.count('"no_render_api_call": True') < 4:
        failures.append("safe sports contexts do not all declare no_render_api_call")
    for helper in (
        "get_safe_sports_calendar_context",
        "get_safe_live_context",
        "get_safe_picks_context",
        "get_safe_odds_context",
    ):
        if f"def {helper}" not in app_source:
            failures.append(f"missing safe context helper {helper}")

    admin_text = "\n".join(value for key, value in templates.items() if key.startswith("admin_"))
    for marker in ("bottom-nav-clean", "v812-phone-card", "v924-client-shell"):
        if marker in admin_text:
            failures.append(f"admin/client navigation mix marker found: {marker}")
    if 'href="/api/admin/continuous-sentinel/run"' in admin_text:
        failures.append("direct continuous Sentinel API href found")
    if 'v926_pixel_perfect_claim_allowed": False' not in app_source:
        failures.append("pixel-perfect evidence gate is not false")

    for rel in ("app.py", "static/app.css", "templates/home.html", "templates/admin_dashboard.html"):
        content = read(rel)
        for prefix in ("sk_live_", "xoxb-", "ghp_", "github_pat_", "rnd_"):
            if prefix in content:
                failures.append(f"suspicious secret prefix in {rel}: {prefix}")

    os.environ.setdefault("DB_PATH", str(Path(tempfile.gettempdir()) / "nemesis_v926_check.sqlite"))
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
    smoke = {}
    for route in routes:
        response = http.get(route, follow_redirects=False)
        smoke[route] = response.status_code
        if response.status_code >= 500:
            failures.append(f"route {route} returned {response.status_code}")
    for route in ("/", "/cliente-login", "/registro", "/calendar", "/live", "/picks", "/support", "/admin-login"):
        if smoke.get(route) != 200:
            failures.append(f"critical route {route} returned {smoke.get(route)}")
    if smoke.get("/api/admin/automation-workforce/status") != 403:
        failures.append("workforce status API is not protected with 403")
    if smoke.get("/ruta-inventada") != 404 or smoke.get("/api/ruta-inventada") != 404:
        failures.append("404 contract mismatch")

    runtime = http.get("/api/runtime-version").get_json() or {}
    if runtime.get("version") != VERSION or not runtime.get("version_files_match"):
        failures.append("runtime identity is not aligned with V926")
    if runtime.get("deployment_alignment_status") != "aligned_local_files":
        failures.append("runtime deployment alignment is not local-file aligned")
    for flag in (
        "has_v926_desktop_reference_model_pass",
        "has_v926_admin_desktop_command_center",
        "has_v926_client_desktop_dashboard",
        "has_v926_sports_desktop_boards",
        "has_v926_desktop_empty_space_fix",
    ):
        if runtime.get(flag) is not True:
            failures.append(f"runtime flag false: {flag}")

    for template in (ROOT / "templates").glob("*.html"):
        try:
            app_module.app.jinja_env.parse(template.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception as exc:
            failures.append(f"Jinja parse failed {template.name}: {exc.__class__.__name__}")

    zip_audit = audit_zip(failures)
    result = {
        "ok": not failures,
        "version": VERSION,
        "failures": failures,
        "smoke": smoke,
        "runtime": {
            "version": runtime.get("version"),
            "version_files_match": runtime.get("version_files_match"),
            "deployment_alignment_status": runtime.get("deployment_alignment_status"),
            "v926_browser_qa_still_required": runtime.get("v926_browser_qa_still_required"),
            "v926_pixel_perfect_claim_allowed": runtime.get("v926_pixel_perfect_claim_allowed"),
        },
        "zip_audit": zip_audit,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
