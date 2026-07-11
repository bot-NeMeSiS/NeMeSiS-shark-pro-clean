from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
SUCCESSOR_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
V934_VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def fake_user(role: str) -> dict:
    role = role.upper()
    return {
        "id": f"v932-{role.lower()}-check",
        "name": f"{role.title()} QA",
        "username": f"{role.lower()}_qa",
        "email": f"{role.lower()}@example.invalid",
        "role": role,
        "membership": role,
        "created_at": "",
        "last_login": "",
    }


def csrf_for(client, path: str) -> str:
    client.get(path)
    with client.session_transaction() as session:
        return str(session.get("csrf_token") or "")


def main() -> int:
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    with tempfile.TemporaryDirectory(prefix="nemesis_v932_redirects_", ignore_cleanup_errors=True) as temp_dir:
        os.environ["DB_PATH"] = str(Path(temp_dir) / "redirects.sqlite")
        import app as app_module

        app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        app_module.app.logger.disabled = True
        logging.disable(logging.CRITICAL)
        original_auth_user = app_module.authenticate_user
        original_auth_admin = app_module.authenticate_env_admin
        original_security_event = app_module.security_event_for_auth
        app_module.security_event_for_auth = lambda *args, **kwargs: None
        try:
            app_module.authenticate_user = lambda *args, **kwargs: fake_user("PRO")
            client_external = app_module.app.test_client()
            client_external_token = csrf_for(client_external, "/cliente-login")
            response_client_external = client_external.post(
                "/cliente-login?next=https://example.com/steal",
                data={"login": "client@example.invalid", "password": "not-a-real-secret", "next": "https://example.com/steal", "csrf_token": client_external_token},
                follow_redirects=False,
            )
            client_internal = app_module.app.test_client()
            client_internal_token = csrf_for(client_internal, "/cliente-login")
            response_client_internal = client_internal.post(
                "/cliente-login", data={"login": "client@example.invalid", "password": "not-a-real-secret", "next": "/calendar", "csrf_token": client_internal_token}, follow_redirects=False,
            )
            response_client_logout = client_internal.get("/logout", follow_redirects=False)
            with client_internal.session_transaction() as session:
                client_session_cleared = not bool(session.get("user_id"))

            app_module.authenticate_env_admin = lambda *args, **kwargs: fake_user("ADMIN")
            app_module.authenticate_user = lambda *args, **kwargs: None
            admin_external = app_module.app.test_client()
            admin_external_token = csrf_for(admin_external, "/admin-login")
            response_admin_external = admin_external.post(
                "/admin-login", data={"login": "admin@example.invalid", "password": "not-a-real-secret", "next": "https://example.com/steal", "csrf_token": admin_external_token}, follow_redirects=False,
            )
            admin_internal = app_module.app.test_client()
            admin_internal_token = csrf_for(admin_internal, "/admin-login")
            response_admin_internal = admin_internal.post(
                "/admin-login", data={"login": "admin@example.invalid", "password": "not-a-real-secret", "next": "/admin/dashboard", "csrf_token": admin_internal_token}, follow_redirects=False,
            )
            response_admin_logout = admin_internal.get("/admin/logout", follow_redirects=False)
            with admin_internal.session_transaction() as session:
                admin_session_cleared = not bool(session.get("user_id"))
        finally:
            app_module.authenticate_user = original_auth_user
            app_module.authenticate_env_admin = original_auth_admin
            app_module.security_event_for_auth = original_security_event

    checks = {
        "version_v932_or_successor": app_module.APP_VERSION in {VERSION, SUCCESSOR_VERSION, V934_VERSION},
        "client_external_next_blocked": response_client_external.status_code == 302 and response_client_external.headers.get("Location") == "/app",
        "client_internal_next_allowed": response_client_internal.status_code == 302 and response_client_internal.headers.get("Location") == "/calendar",
        "client_logout_safe": response_client_logout.status_code == 302 and response_client_logout.headers.get("Location") == "/" and client_session_cleared,
        "admin_external_next_blocked": response_admin_external.status_code == 302 and response_admin_external.headers.get("Location") == "/admin/import-center",
        "admin_internal_next_allowed": response_admin_internal.status_code == 302 and response_admin_internal.headers.get("Location") == "/admin/dashboard",
        "admin_logout_safe": response_admin_logout.status_code == 302 and response_admin_logout.headers.get("Location") == "/admin-login" and admin_session_cleared,
        "redirect_helpers_internal_only": (
            app_module._safe_client_next("//example.com") == "/app"
            and app_module._safe_admin_next("/calendar") == "/admin/import-center"
            and app_module._safe_admin_next("\\\\example.com") == "/admin/import-center"
        ),
        "no_real_credentials_used": True,
    }
    failed = [name for name, ok in checks.items() if not ok]
    payload = {
        "version": VERSION,
        "ok": not failed,
        "checks": checks,
        "failed": failed,
        "locations": {
            "client_external": response_client_external.headers.get("Location", ""),
            "client_internal": response_client_internal.headers.get("Location", ""),
            "admin_external": response_admin_external.headers.get("Location", ""),
            "admin_internal": response_admin_internal.headers.get("Location", ""),
        },
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
