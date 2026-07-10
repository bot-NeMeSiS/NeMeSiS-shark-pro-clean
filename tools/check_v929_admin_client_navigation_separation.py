from __future__ import annotations

from v929_check_support import finish, mock_session, prepare_app


def main() -> int:
    app_module = prepare_app()
    client = app_module.app.test_client()
    mock_session(client, "client")
    client_html = client.get("/app").get_data(as_text=True)
    admin = app_module.app.test_client()
    mock_session(admin, "admin")
    admin_response = admin.get("/admin/dashboard")
    admin_html = admin_response.get_data(as_text=True)
    checks = {
        "client_has_client_topbar": "v928-client-topbar" in client_html,
        "client_has_no_admin_sidebar": "v928-admin-sidebar" not in client_html,
        "client_has_mobile_bottom_nav": "v928-mobile-bottom-nav" in client_html,
        "admin_200": admin_response.status_code == 200,
        "admin_has_admin_sidebar": "v928-admin-sidebar" in admin_html,
        "admin_has_admin_topbar": "v928-admin-topbar" in admin_html,
        "admin_has_no_client_topbar": "v928-client-topbar" not in admin_html,
        "admin_has_no_mobile_bottom_nav": "v928-mobile-bottom-nav" not in admin_html,
        "admin_api_without_session_403": app_module.app.test_client().get("/api/admin/navigation-integrity/summary").status_code == 403,
    }
    return finish("V929 admin client navigation separation", checks)


if __name__ == "__main__":
    raise SystemExit(main())
