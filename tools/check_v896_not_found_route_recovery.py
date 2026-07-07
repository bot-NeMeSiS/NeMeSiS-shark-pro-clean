from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V896_PRODUCTION_NOT_FOUND_ROUTE_RECOVERY_FULL_APP_SMOKE_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V897_SENTINEL_TRUTHFUL_ISSUES_ROUTE_ALIAS_REFERENCE_QA_FIX_FINAL",
    "V898_PRODUCTION_404_PWA_REFERENCE_OUTBOX_TRUTH_FINAL",
    "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL",
    "V900_REFERENCE_IMAGES_IMPORT_FIRST_REAL_VISUAL_GAP_AUDIT_FINAL",
    "V901_ADMIN_CONTINUOUS_SENTINEL_API_LAYOUT_RECOVERY_FINAL",
    "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL",
    "V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL",
    "V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL",
}
CACHE_MARKERS = (
    "NEMESIS_CACHE_V896",
    "NEMESIS_CACHE_V897",
    "NEMESIS_CACHE_V898",
    "NEMESIS_CACHE_V899",
    "NEMESIS_CACHE_V900",
    "NEMESIS_CACHE_V901",
    "NEMESIS_CACHE_V902",
    "NEMESIS_CACHE_V902B",
    "NEMESIS_CACHE_V903",
)


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
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    not_found_template = read("templates/404.html")

    require(version_txt in CURRENT_ALLOWED, f"VERSION.txt is {version_txt}", failures)
    require(app_version_file in CURRENT_ALLOWED, f"APP_VERSION file is {app_version_file}", failures)
    require(app_version_from_source(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION mismatch", failures)
    require(version_txt in base, "base.html cache marker does not match current version", failures)
    require("has_v896_not_found_route_recovery" in app_py, "runtime V896 flag missing", failures)
    require("client_safe_404" in app_py and "@app.errorhandler(404)" in app_py, "404 handler missing", failures)
    require((ROOT / "templates" / "404.html").exists(), "templates/404.html missing", failures)
    require("Ruta no encontrada" in not_found_template, "404 template Spanish title missing", failures)
    require("href=\"#\"" not in not_found_template, "404 template contains href #", failures)
    require("javascript:void" not in not_found_template.lower(), "404 template contains javascript:void", failures)
    require("V896 PRODUCTION NOT FOUND ROUTE RECOVERY" in css, "V896 CSS marker missing", failures)
    require("/manifest.json" in app_py and "manifest_json" in app_py, "manifest route missing", failures)
    require("/service-worker.js" in app_py and any(marker in app_py for marker in CACHE_MARKERS), "service worker current cache missing", failures)
    require("data/runtime/not_found_events.json" in app_py or "not_found_events.json" in app_py, "not found memory path missing", failures)
    require("run_sentinel_issues_scan" in app_py and "Ruta devuelve Not Found" in app_py, "Sentinel Not Found integration missing", failures)
    require("V896_PRIMARY_ROUTE_SMOKE" in app_py and "/admin/autonomous-company-sentinel" in app_py, "autonomous route smoke list missing", failures)

    for route in [
        "/dashboard",
        "/client",
        "/cliente",
        "/client-dashboard",
        "/home",
        "/inicio-cliente",
        "/mi-cuenta",
        "/perfil",
        "/soporte",
        "/ayuda",
        "/partidos-hoy",
        "/calendario",
        "/directos",
        "/en-vivo",
        "/recomendaciones",
        "/pick",
        "/apuestas",
        "/admin-panel",
        "/admin/home",
        "/admin/control",
        "/admin/sentinel",
        "/admin/qa",
        "/admin/prompts",
    ]:
        require(route in app_py, f"alias route missing: {route}", failures)
    require("register_alias_if_missing" in app_py, "safe alias helper missing", failures)

    for route in [
        "/api/admin/route-map",
        "/api/admin/route-smoke",
        "/api/admin/not-found-events",
    ]:
        require(route in app_py, f"admin route diagnostic missing: {route}", failures)

    for forbidden in ["TELEGRAM_BOT_TOKEN =", "AUTOMATION_SECRET =", "API_SPORTS_KEY =", "OPENAI_API_KEY ="]:
        require(forbidden not in app_py, f"possible secret assignment found: {forbidden}", failures)

    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, f"runtime status {runtime.status_code}", failures)
    runtime_json = runtime.get_json(silent=True) or {}
    require(runtime_json.get("app_version") in CURRENT_ALLOWED, f"runtime app_version is {runtime_json.get('app_version')}", failures)
    require(runtime_json.get("has_v896_not_found_route_recovery") is True, "runtime V896 flag false", failures)

    manifest = client.get("/manifest.json")
    require(manifest.status_code == 200, f"manifest status {manifest.status_code}", failures)
    manifest_json = manifest.get_json(silent=True) or {}
    require(manifest_json.get("start_url") == "/", "manifest start_url is not /", failures)
    require(manifest_json.get("scope") == "/", "manifest scope is not /", failures)

    sw = client.get("/service-worker.js")
    require(sw.status_code == 200, f"service worker status {sw.status_code}", failures)
    require(any(marker in sw.get_data(as_text=True) for marker in CACHE_MARKERS), "service worker does not expose current cache", failures)

    expected_status = {
        "/": {200},
        "/app": {200, 302},
        "/cliente-login": {200},
        "/registro": {200},
        "/calendar": {200},
        "/live": {200},
        "/picks": {200},
        "/support": {200},
        "/admin-login": {200},
        "/admin/dashboard": {302, 401, 403},
        "/admin/autonomous-company-sentinel": {302, 401, 403},
        "/api/runtime-version": {200},
        "/ruta-inventada-v896": {404},
        "/api/ruta-inventada-v896": {404},
        "/dashboard": {301, 302, 303, 307, 308},
        "/admin-panel": {301, 302, 303, 307, 308},
        "/directos": {301, 302, 303, 307, 308},
    }
    for route, statuses in expected_status.items():
        response = client.get(route, follow_redirects=False)
        require(response.status_code in statuses, f"{route} returned {response.status_code}", failures)
        if route == "/ruta-inventada-v896":
            body = response.get_data(as_text=True)
            require("Ruta no encontrada" in body and "Not Found" not in body[:300], "premium 404 body missing", failures)
        if route == "/api/ruta-inventada-v896":
            payload = response.get_json(silent=True) or {}
            require(payload.get("error") == "not_found", "API 404 JSON not controlled", failures)

    for route in ["/api/admin/route-map", "/api/admin/route-smoke", "/api/admin/not-found-events"]:
        response = client.get(route)
        require(response.status_code == 403, f"{route} without admin is not 403", failures)

    memory_path = ROOT / "data" / "runtime" / "not_found_events.json"
    require(memory_path.exists(), "not_found_events.json was not created by smoke", failures)
    if memory_path.exists():
        payload = json.loads(memory_path.read_text(encoding="utf-8"))
        require(isinstance(payload.get("events"), list), "not_found_events payload invalid", failures)

    if failures:
        print("V896 Not Found route recovery check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V896 Not Found route recovery check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
