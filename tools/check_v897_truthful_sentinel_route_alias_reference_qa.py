from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V897_SENTINEL_TRUTHFUL_ISSUES_ROUTE_ALIAS_REFERENCE_QA_FIX_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V898_PRODUCTION_404_PWA_REFERENCE_OUTBOX_TRUTH_FINAL",
    "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL",
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    issues_engine = read("engines/sentinel_issues_engine.py")
    shark_sentinel = read("engines/shark_sentinel_engine.py")
    reference_engine = read("engines/sentinel_reference_qa_engine.py")

    require(read("VERSION.txt").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "VERSION.txt is not V897/V898/V899", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "APP_VERSION file is not V897/V898/V899", failures)
    require(app_version_from_source(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION is not V897/V898/V899", failures)
    require("has_v897_truthful_sentinel_route_alias_reference_qa" in app_py, "runtime V897 flag missing", failures)
    require("register_alias_if_missing" in app_py, "safe alias helper missing", failures)
    require("V897_ALIAS_REGISTRATION" in app_py, "alias registration summary missing", failures)
    require("is_admin_surface = request.path == '/admin-login'" in base, "admin-login surface isolation missing", failures)
    require("not is_admin_surface" in base and "data-v897-shell" in base, "base admin/client shell V897 markers missing", failures)
    require("extract_visible_user_text" in shark_sentinel, "visible text helper missing", failures)
    require("<(script|style|template|svg|noscript)" in shark_sentinel, "script/style visible-text cleanup missing", failures)
    require("STALE_NEEDS_REVALIDATION" in issues_engine, "STALE_NEEDS_REVALIDATION status missing", failures)
    require("RESOLVED_BY_RESCAN" in issues_engine, "RESOLVED_BY_RESCAN status missing", failures)
    require("reconcile_sentinel_issues" in issues_engine, "issue reconciliation helper missing", failures)
    require((ROOT / "reference_images").exists(), "reference_images folder missing", failures)
    require((ROOT / "reference_images" / "README.md").exists(), "reference_images README missing", failures)
    require("REFERENCE_IMAGES_MISSING" in reference_engine, "reference missing issue code missing", failures)
    require((ROOT / "tools" / "run_browser_reference_qa.py").exists(), "optional browser QA tool missing", failures)

    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433
    from engines.sentinel_issues_engine import normalize_sentinel_issue, reconcile_sentinel_issues
    from engines.shark_sentinel_engine import extract_visible_user_text

    client = nemesis_app.app.test_client()
    runtime = client.get("/api/runtime-version").get_json(silent=True) or {}
    require(runtime.get("app_version") in CURRENT_ALLOWED, f"runtime app_version is {runtime.get('app_version')}", failures)
    require(runtime.get("has_v897_truthful_sentinel_route_alias_reference_qa") is True, "runtime V897 flag false", failures)

    alias_summary = runtime.get("v897_alias_registration") or []
    by_source = {item.get("source"): item for item in alias_summary if isinstance(item, dict)}
    for real_route in ["/calendario", "/partidos-hoy", "/recomendaciones", "/ayuda", "/soporte", "/perfil", "/mi-cuenta", "/admin/client-screens"]:
        if real_route in by_source:
            require(by_source[real_route].get("registered") is False, f"{real_route} alias registered despite real route", failures)
            require(by_source[real_route].get("reason") == "real_route_exists", f"{real_route} alias reason not real_route_exists", failures)
    for alias_route in ["/directos", "/admin-panel"]:
        require(by_source.get(alias_route, {}).get("registered") is True, f"{alias_route} alias not registered", failures)

    response = client.get("/dashboard", follow_redirects=False)
    require(response.status_code in {301, 302, 303, 307, 308}, f"/dashboard status {response.status_code}", failures)
    require((response.headers.get("Location") or "").endswith("/app"), "/dashboard does not redirect to /app", failures)

    response = client.get("/admin-panel", follow_redirects=False)
    require(response.status_code in {301, 302, 303, 307, 308}, f"/admin-panel status {response.status_code}", failures)
    require("/admin/dashboard" in (response.headers.get("Location") or ""), "/admin-panel does not target admin dashboard", failures)

    admin_login = client.get("/admin-login").get_data(as_text=True)
    require('data-nav-zone="client-bottom"' not in admin_login, "admin-login shows client bottom nav", failures)
    require(re.search(r"<aside[^>]+ns-client-sidebar", admin_login, re.I) is None, "admin-login shows client sidebar", failures)
    require(re.search(r"<a[^>]+v825-public-floating-shark", admin_login, re.I) is None, "admin-login shows public floating SHARK", failures)

    visible = extract_visible_user_text("<html><script>let keyboardTimer=null;</script><body><p>Modo seguro activo</p></body></html>")
    require("null" not in visible.lower(), "visible text helper keeps JS null", failures)
    require("Modo seguro activo" in visible, "visible text helper removed real user text", failures)

    old = normalize_sentinel_issue({"title": "Ruta con error 500", "area": "route", "route": "/picks", "evidence": "HTTP 500", "severity": "critical"}, "test")
    stale = reconcile_sentinel_issues([old], [])
    require(stale[0].get("status") == "STALE_NEEDS_REVALIDATION", "old issue was not marked stale after clean scan", failures)
    stale = reconcile_sentinel_issues(stale, [])
    stale = reconcile_sentinel_issues(stale, [])
    require(stale[0].get("status") == "RESOLVED_BY_RESCAN", "old issue was not resolved by repeated rescan", failures)

    invented_html = client.get("/ruta-inventada-v897").get_data(as_text=True)
    require("Ruta no encontrada" in invented_html, "premium 404 missing for invented route", failures)
    invented_api = client.get("/api/ruta-inventada-v897")
    require(invented_api.status_code == 404 and (invented_api.get_json(silent=True) or {}).get("error") == "not_found", "API 404 JSON missing", failures)

    for route in ["/api/admin/route-map", "/api/admin/not-found-events"]:
        require(client.get(route).status_code == 403, f"{route} is not protected", failures)

    if failures:
        print("V897 truthful sentinel route alias reference QA check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V897 truthful sentinel route alias reference QA check OK")
    print(json.dumps({"version": VERSION, "alias_checked": True, "visible_text_checked": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
