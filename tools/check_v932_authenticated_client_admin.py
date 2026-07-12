from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
SUCCESSOR_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
V934_VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
V935_VERSION = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CLIENT_ROUTES = [
    "/app", "/calendar", "/live", "/picks", "/track-record", "/shark",
    "/telegram", "/profile", "/memberships", "/favorites",
]
ADMIN_ROUTES = [
    "/admin/dashboard", "/admin/users", "/admin/memberships", "/admin/payments",
    "/admin/picks", "/admin/matches", "/admin/data-center",
    "/admin/telegram/command-center", "/admin/automation-workforce",
    "/admin/autonomous-company-sentinel", "/admin/navigation-integrity",
]


def set_mock_session(client, role: str) -> None:
    with client.session_transaction() as session:
        if role == "admin":
            session.update({
                "user_id": "v932-admin-check", "user_name": "Admin QA",
                "username": "admin_qa", "user_email": "admin@example.invalid",
                "user_role": "ADMIN", "membership": "ADMIN", "user_membership": "ADMIN",
            })
        else:
            session.update({
                "user_id": "v932-client-check", "user_name": "Cliente QA",
                "username": "client_qa", "user_email": "client@example.invalid",
                "user_role": "PRO", "membership": "PRO", "user_membership": "PRO",
            })


def inspect_routes(client, routes: list[str]) -> list[dict]:
    results = []
    for route in routes:
        started = time.monotonic()
        response = client.get(route, follow_redirects=False)
        body = response.get_data(as_text=True)
        results.append({
            "route": route,
            "status": response.status_code,
            "location": response.headers.get("Location", ""),
            "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
            "final_route": response.headers.get("Location", "") or route,
            "ok": response.status_code == 200,
            "visible_error": any(value in body for value in (
                "Internal Server Error", "Internal Error", "database is locked", "UndefinedError",
            )),
            "screenshot": "",
            "overflow": "not_measured_without_authorized_browser_session",
        })
    return results


def main() -> int:
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["STRIPE_SECRET_KEY"] = ""
    with tempfile.TemporaryDirectory(prefix="nemesis_v932_auth_", ignore_cleanup_errors=True) as temp_dir:
        os.environ["DB_PATH"] = str(Path(temp_dir) / "auth.sqlite")
        import app as app_module

        app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        app_module.app.logger.disabled = True
        logging.disable(logging.CRITICAL)
        original_v931 = app_module.v931_record_client_route_issue
        original_v932 = app_module.v932_record_authenticated_issue
        app_module.v931_record_client_route_issue = lambda *args, **kwargs: True
        app_module.v932_record_authenticated_issue = lambda *args, **kwargs: True
        try:
            public = app_module.app.test_client()
            login_status = public.get("/cliente-login").status_code
            admin_login_status = public.get("/admin-login").status_code
            client = app_module.app.test_client()
            set_mock_session(client, "client")
            admin = app_module.app.test_client()
            set_mock_session(admin, "admin")
            client_results = inspect_routes(client, CLIENT_ROUTES)
            admin_results = inspect_routes(admin, ADMIN_ROUTES)
            protected_api = public.get("/api/admin/automation-workforce/status")
            runtime = public.get("/api/runtime-version").get_json(silent=True) or {}
        finally:
            app_module.v931_record_client_route_issue = original_v931
            app_module.v932_record_authenticated_issue = original_v932

    failures = [item for item in client_results + admin_results if not item["ok"] or item["visible_error"]]
    checks = {
        "version_v932_or_successor": app_module.APP_VERSION in {VERSION, SUCCESSOR_VERSION, V934_VERSION, V935_VERSION},
        "login_pages_200": login_status == 200 and admin_login_status == 200,
        "client_mock_routes_200": all(item["ok"] for item in client_results),
        "admin_mock_routes_200": all(item["ok"] for item in admin_results),
        "no_visible_internal_errors": not failures,
        "admin_api_protected": protected_api.status_code == 403,
        "runtime_flags_v932": all(runtime.get(flag) is True for flag in (
            "has_v932_authenticated_client_qa", "has_v932_authenticated_admin_qa",
            "has_v932_sqlite_regression_guard", "has_v932_real_sports_value_qa",
            "has_v932_login_redirect_guard",
        )),
        "runtime_no_auth_claim": "production_session_required" in str(runtime.get("v932_client_auth_routes_status")),
        "no_dangerous_actions": True,
    }
    failed = [name for name, ok in checks.items() if not ok]
    payload = {
        "version": VERSION,
        "ok": not failed,
        "checks": checks,
        "failed": failed,
        "client_routes": client_results,
        "admin_routes": admin_results,
        "production_credentials_used": False,
        "payments_executed": False,
        "telegram_sent": False,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
