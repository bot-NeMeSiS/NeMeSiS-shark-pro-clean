from __future__ import annotations

import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED"

CLIENT_ROUTES = {
    "/": "home.html",
    "/app": "client_app_center.html",
    "/calendar": "calendar.html",
    "/partidos": "calendar.html",
    "/live": "live.html",
    "/picks": "picks.html",
    "/match/<match_id>": "match_detail.html",
    "/shark": "shark.html",
    "/profile": "profile.html",
    "/telegram": "telegram.html",
}


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def fail(message: str, details=None) -> None:
    print(json.dumps({"ok": False, "error": message, "details": details or {}}, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def main() -> None:
    app_py = read(ROOT / "app.py")
    base = read(ROOT / "templates" / "base.html")
    css = read(ROOT / "static" / "app.css")
    route_results = {}
    for route, template in CLIENT_ROUTES.items():
        route_exists = '@app.route("/match/<match_id>")' in app_py if "<match_id>" in route else f'@app.route("{route}")' in app_py
        route_results[route] = {
            "route_exists": route_exists,
            "template_rendered": f'render_template("{template}"' in app_py,
            "template_exists": (ROOT / "templates" / template).exists(),
        }
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', "\n".join(read(p) for p in (ROOT / "templates").glob("*.html")))
    malformed = [
        h for h in hrefs
        if ("None" in h or "undefined" in h.lower())
        and not h.strip().startswith("{{")
    ]
    checks = {
        "version": VERSION in read(ROOT / "VERSION.txt") and VERSION in app_py,
        "client_routes_templates": all(v["route_exists"] and v["template_exists"] for v in route_results.values()),
        "base_links_core": all(link in base for link in ["/app", "/calendar", "/live", "/picks", "/shark", "/logout"]),
        "admin_links_core": all(link in base for link in ["/admin/control-center", "/admin/users", "/admin/data-center", "/admin/telegram/command-center"]),
        "no_malformed_hrefs": not malformed,
        "v815_css_active": "data-v815-shell" in css and "v815-certified-screen" in css,
        "css_cache_busting": VERSION in base,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Fallan checks rutas/navegacion V815: " + ", ".join(failed), {"routes": route_results, "malformed_hrefs": malformed[:20]})
    print(json.dumps({"ok": True, "version": VERSION, "checks": checks, "routes": route_results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
