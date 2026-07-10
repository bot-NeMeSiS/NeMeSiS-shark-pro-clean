from __future__ import annotations

import re

from v929_check_support import ROOT, finish, mock_session, prepare_app


def main() -> int:
    app_module = prepare_app()
    component = (ROOT / "templates" / "components" / "v928_navigation.html").read_text(
        encoding="utf-8-sig", errors="replace"
    )
    macro = component.split("{% macro mobile_bottom_nav", 1)[-1]
    expected = {"/app", "/calendar", "/live", "/picks", "/profile"}
    listed = set(re.findall(r"'(/[^']+)'", macro))
    adapter = app_module.app.url_map.bind("localhost")
    route_valid = True
    for path in expected:
        try:
            adapter.match(path, method="GET")
        except Exception:
            route_valid = False
    client = app_module.app.test_client()
    mock_session(client, "client")
    client_html = client.get("/app").get_data(as_text=True)
    admin = app_module.app.test_client()
    mock_session(admin, "admin")
    admin_html = admin.get("/admin/dashboard").get_data(as_text=True)
    checks = {
        "expected_client_destinations": expected.issubset(listed),
        "bottom_destinations_registered": route_valid,
        "no_admin_destination_in_bottom_nav": not any(path.startswith("/admin") for path in listed),
        "client_bottom_nav_rendered": "v928-mobile-bottom-nav" in client_html,
        "client_bottom_nav_five_items": client_html.count("v928-mobile-bottom-nav") == 1,
        "admin_bottom_nav_absent": "v928-mobile-bottom-nav" not in admin_html,
        "mobile_safe_area_css": "env(safe-area-inset-bottom" in (ROOT / "static" / "v928-canonical.css").read_text(encoding="utf-8-sig", errors="replace"),
    }
    return finish("V929 mobile bottom navigation", checks, {"destinations": sorted(expected)})


if __name__ == "__main__":
    raise SystemExit(main())
