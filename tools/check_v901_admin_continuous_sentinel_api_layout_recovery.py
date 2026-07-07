from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VERSION = "V901_ADMIN_CONTINUOUS_SENTINEL_API_LAYOUT_RECOVERY_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def csrf_from_html(html: str) -> str:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else ""


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    admin_login_tpl = read("templates/admin_login.html")
    continuous_tpl = read("templates/admin_continuous_sentinel.html")
    workflow_tpl = read("templates/admin_sentinel_workflow.html")
    shark_tpl = read("templates/admin_shark_sentinel.html")

    require(read("VERSION.txt").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "VERSION.txt is not V901/V902", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "APP_VERSION is not V901/V902", failures)
    require(app_version_from_source(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION is not V901/V902", failures)
    require("has_v901_admin_continuous_sentinel_api_layout_recovery" in app_py, "runtime V901 flag missing", failures)
    require('data-v901-shell="true"' in base, "base V901 shell marker missing", failures)
    require("NEMESIS_CACHE_V901" in app_py or "NEMESIS_CACHE_V902" in app_py, "service worker cache V901/V902 missing", failures)

    require("is_admin_surface = request.path == '/admin-login'" in base, "admin surface detection missing admin-login", failures)
    require("show_mobile_bottom_nav = not is_admin_surface" in base, "admin surface must hide client bottom nav", failures)
    require("show_floating_shark = is_client_area" in base, "floating SHARK must be client-only", failures)
    require("show_admin_nav = current_user and current_user.role == 'ADMIN'" in base, "admin nav should require real admin session", failures)

    require('action="/admin-login{% if request.args.get(' in admin_login_tpl and "?next=" in admin_login_tpl, "admin-login next action malformed", failures)
    require('name="login"' in admin_login_tpl and 'type="password"' in admin_login_tpl, "admin-login form fields missing", failures)
    require("Contraseña" in admin_login_tpl, "admin-login password label not fixed", failures)
    require("bottom-nav" not in admin_login_tpl and "shark-widget" not in admin_login_tpl, "admin-login template contains client nav/floating shark", failures)
    require("Ã" not in admin_login_tpl and "�" not in admin_login_tpl, "admin-login mojibake visible", failures)

    combined_admin = "\n".join([continuous_tpl, workflow_tpl, shark_tpl])
    require('href="/api/admin/continuous-sentinel/run' not in combined_admin, "continuous sentinel action still links directly to API", failures)
    require("data-sentinel-run" in continuous_tpl and "fetch(`/api/admin/continuous-sentinel/run" in continuous_tpl, "continuous sentinel fetch buttons missing", failures)
    require("v901-sentinel-status" in continuous_tpl, "continuous sentinel result panel missing", failures)
    require('href="/api/admin/shark-sentinel/run' not in shark_tpl, "shark sentinel action still links directly to API", failures)
    require("data-shark-sentinel-run" in shark_tpl and 'fetch("/api/admin/shark-sentinel/run"' in shark_tpl, "shark sentinel fetch button missing", failures)
    for bad in ["javascript:void", 'href="#"', "Internal Server Error"]:
        require(bad not in combined_admin, f"bad admin UI token present: {bad}", failures)
    for bad in ["Ã", "Â", "�"]:
        require(bad not in combined_admin, f"admin sentinel mojibake present: {bad}", failures)

    require("@app.errorhandler(500)" in app_py and "safe_message" in app_py and "v901_register_admin_api_issue" in app_py, "safe 500/API issue handler missing", failures)

    import app as app_module

    flask_app = app_module.app
    flask_app.testing = True
    client = flask_app.test_client()

    admin_login = client.get("/admin-login")
    admin_login_html = admin_login.get_data(as_text=True)
    require(admin_login.status_code == 200, "/admin-login not 200", failures)
    require("<form" in admin_login_html and "admin-login-password" in admin_login_html, "/admin-login form not visible", failures)
    require('data-nav-zone="client-bottom"' not in admin_login_html and '<aside class="ns-client-sidebar"' not in admin_login_html and '<div class="shark-widget"' not in admin_login_html, "/admin-login contains client nav/floating shark", failures)
    require("Contraseña" in admin_login_html, "/admin-login password label missing", failures)
    require("Ã" not in admin_login_html and "�" not in admin_login_html, "/admin-login mojibake in rendered HTML", failures)

    protected = client.get("/api/admin/continuous-sentinel/run?mode=client&dry_run=1")
    require(protected.status_code == 403 and protected.is_json, "continuous sentinel API without session must be JSON 403", failures)

    with client.session_transaction() as sess:
        sess["user_id"] = "admin-test"
        sess["user_name"] = "Admin Test"
        sess["user_role"] = "ADMIN"
        sess["membership"] = "ADMIN"
        sess["user_membership"] = "ADMIN"

    admin_page = client.get("/admin/continuous-sentinel")
    admin_page_html = admin_page.get_data(as_text=True)
    token = csrf_from_html(admin_page_html)
    require(admin_page.status_code == 200, "/admin/continuous-sentinel admin session not 200", failures)
    require("data-sentinel-run" in admin_page_html and "/api/admin/continuous-sentinel/run?mode=client" not in admin_page_html, "admin continuous page still exposes direct API navigation", failures)
    require(token, "csrf token missing in admin continuous page", failures)

    response = client.post(
        "/api/admin/continuous-sentinel/run?mode=client&dry_run=1",
        json={"mode": "client", "dry_run": True, "csrf_token": token},
        headers={"X-CSRF-Token": token},
    )
    require(response.status_code == 200 and response.is_json, "continuous sentinel dry-run admin POST not JSON 200", failures)
    payload = response.get_json() or {}
    require("Internal Server Error" not in response.get_data(as_text=True), "continuous sentinel returned Internal Server Error text", failures)
    require("ok" in payload and payload.get("mode") == "client" and payload.get("dry_run") is True, "continuous sentinel JSON payload incomplete", failures)

    original_runner = app_module.run_continuous_sentinel_cycle

    def failing_runner(*args, **kwargs):
        raise RuntimeError("V901 simulated failure without secrets")

    app_module.run_continuous_sentinel_cycle = failing_runner
    try:
        failed = client.post(
            "/api/admin/continuous-sentinel/run?mode=client&dry_run=1",
            json={"mode": "client", "dry_run": True, "csrf_token": token},
            headers={"X-CSRF-Token": token},
        )
        failed_payload = failed.get_json() or {}
        require(failed.status_code == 200 and failed.is_json, "simulated failure should return JSON 200", failures)
        require(failed_payload.get("ok") is False and failed_payload.get("error") == "continuous_sentinel_run_failed", "simulated failure payload not safe", failures)
        require("safe_message" in failed_payload and "traceback" not in failed.get_data(as_text=True).lower(), "simulated failure exposes unsafe detail", failures)
    finally:
        app_module.run_continuous_sentinel_cycle = original_runner

    for route in ["/", "/api/runtime-version", "/ruta-inventada", "/api/ruta-inventada"]:
        resp = client.get(route)
        require(resp.status_code in {200, 302, 403, 404}, f"{route} unexpected status {resp.status_code}", failures)
        if route.startswith("/api/"):
            require(resp.is_json, f"{route} should return JSON", failures)

    runtime = client.get("/api/runtime-version").get_json() or {}
    require(runtime.get("app_version") in CURRENT_ALLOWED, "runtime app_version not V901/V902", failures)
    require(runtime.get("has_v901_admin_continuous_sentinel_api_layout_recovery") is True, "runtime V901 flag false", failures)

    if failures:
        print("V901 admin continuous sentinel recovery check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V901 admin continuous sentinel recovery check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
