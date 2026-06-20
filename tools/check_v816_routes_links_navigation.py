from __future__ import annotations

import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "V816_RENDER_LIVE_REFERENCE_VISUAL_DIFF_CLIENT_ADMIN_FINAL"
CURRENT_VERSION = "V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL"
V818_VERSION = "V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL"

CLIENT_ROUTES = {
    "/": "home.html",
    "/cliente-login": "client_login.html",
    "/app": "client_app_center.html",
    "/calendar": "calendar.html",
    "/partidos": "calendar.html",
    "/live": "live.html",
    "/directo": "live.html",
    "/picks": "picks.html",
    "/match/<match_id>": "match_detail.html",
    "/shark": "shark.html",
    "/shark-core": "shark_core.html",
    "/profile": "profile.html",
    "/telegram": "telegram.html",
    "/favorites": "favorites.html",
    "/track-record": "track_record.html",
    "/support": "support.html",
}

ADMIN_ROUTES = [
    "/admin/dashboard",
    "/admin/map",
    "/admin/control-center",
    "/admin/telegram/command-center",
    "/admin/telegram/pro-preview",
    "/admin/users",
    "/admin/memberships",
    "/admin/matches-sync",
    "/admin/data-center",
    "/admin/automation-center",
]


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def has_route(app_py: str, route: str) -> bool:
    escaped = re.escape(route)
    return re.search(rf'@app\.route\("{escaped}"(?:,|\))', app_py) is not None


def fail(message: str, details=None) -> None:
    print(json.dumps({"ok": False, "error": message, "details": details or {}}, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def main() -> None:
    app_py = read(ROOT / "app.py")
    base = read(ROOT / "templates" / "base.html")
    css = read(ROOT / "static" / "app.css")
    route_results = {}
    for route, template in CLIENT_ROUTES.items():
        route_exists = has_route(app_py, "/match/<match_id>") if "<match_id>" in route else has_route(app_py, route)
        route_results[route] = {
            "route_exists": route_exists,
            "template_rendered": f'render_template("{template}"' in app_py,
            "template_exists": (ROOT / "templates" / template).exists(),
        }
    admin_results = {route: has_route(app_py, route) for route in ADMIN_ROUTES}
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', "\n".join(read(p) for p in (ROOT / "templates").glob("*.html")))
    malformed = [h for h in hrefs if ("None" in h or "undefined" in h.lower()) and not h.strip().startswith("{{")]
    checks = {
        "version": read(ROOT / "VERSION.txt").strip() in {VERSION, CURRENT_VERSION, V818_VERSION} and any(v in app_py for v in [VERSION, CURRENT_VERSION, V818_VERSION]),
        "client_routes_templates": all(v["route_exists"] and v["template_exists"] for v in route_results.values()),
        "admin_routes_exist": all(admin_results.values()),
        "base_links_core": all(link in base for link in ["/app", "/calendar", "/live", "/picks", "/shark", "/logout"]),
        "admin_links_core": all(link in base for link in ["/admin/control-center", "/admin/users", "/admin/data-center", "/admin/telegram/command-center"]),
        "no_malformed_hrefs": not malformed,
        "v816_css_active": "data-v816-shell" in css and "v816-certified-screen" in css,
        "css_cache_busting": VERSION in base or CURRENT_VERSION in base or V818_VERSION in base,
        "runtime_v816": "has_v816_shell" in app_py and "has_v816_css" in app_py,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Fallan checks rutas/navegacion V816: " + ", ".join(failed), {"routes": route_results, "admin": admin_results, "malformed_hrefs": malformed[:20]})
    print(json.dumps({"ok": True, "version": VERSION, "checks": checks, "routes": route_results, "admin": admin_results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

