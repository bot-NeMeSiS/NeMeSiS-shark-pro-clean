from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V898_PRODUCTION_404_PWA_REFERENCE_OUTBOX_TRUTH_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL",
}
ZIP_PATH = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"


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
    not_found = read("templates/404.html")
    builder = read("tools/build_clean_release.py")
    outbox_engine = read("engines/sentinel_codex_outbox_engine.py")
    company_engine = read("engines/autonomous_company_sentinel_engine.py")

    require(read("VERSION.txt").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "VERSION.txt is not V898/V899", failures)
    require(read("APP_VERSION").strip().lstrip("\ufeff") in CURRENT_ALLOWED, "APP_VERSION file is not V898/V899", failures)
    require(app_version_from_source(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION is not V898/V899", failures)
    require(("data-v898-shell" in base or "data-v899-shell" in base), "base V898/V899 marker missing", failures)
    require("has_v898_404_pwa_reference_outbox_truth" in app_py, "runtime V898 flag missing", failures)
    require("Ruta solicitada:" in not_found and "{{ path }}" in not_found, "404 does not show safe requested path", failures)
    require("Restablecer app/PWA" in not_found, "PWA reset button missing", failures)
    require("serviceWorker.getRegistrations" in not_found and "caches.keys" in not_found, "PWA reset JS missing", failures)
    require("href=\"#\"" not in not_found and "javascript:void(0)" not in not_found.lower(), "404 has false links", failures)
    require("NEMESIS_CACHE_V898" in app_py or "NEMESIS_CACHE_V899" in app_py, "service worker cache V898/V899 missing", failures)
    service_worker_block = app_py[app_py.find("def service_worker"):app_py.find("@app.route(\"/manifest.json\")")]
    require("res.status===404" in app_py and "caches.open" not in service_worker_block, "service worker may cache 404 or use old cache pattern", failures)
    require('"reference_images"' in builder, "build_clean_release does not include reference_images", failures)
    require((ROOT / "reference_images" / "README.md").exists(), "reference_images README missing", failures)
    require((ROOT / "reference_images" / "reference_manifest.json").exists(), "reference manifest missing", failures)
    require("Prompts archivados / obsoletos" in outbox_engine, "outbox archive section missing", failures)
    require("archived_prompt_count" in outbox_engine, "outbox archived prompt count missing", failures)
    require("active_issues_open" in company_engine and "resolved_by_rescan" in company_engine, "autonomous state active/stale counters missing", failures)

    sys.path.insert(0, str(ROOT))
    import app as nemesis_app  # noqa: WPS433

    client = nemesis_app.app.test_client()
    runtime = client.get("/api/runtime-version").get_json(silent=True) or {}
    require(runtime.get("app_version") in CURRENT_ALLOWED, f"runtime app_version is {runtime.get('app_version')}", failures)
    require(runtime.get("has_v898_404_pwa_reference_outbox_truth") is True, "runtime V898 flag false", failures)

    html = client.get("/ruta-inventada-v898?secret=SHOULD_NOT_APPEAR").get_data(as_text=True)
    require("Ruta solicitada:" in html and "/ruta-inventada-v898" in html, "404 route path not visible", failures)
    require("SHOULD_NOT_APPEAR" not in html and "secret=" not in html.lower(), "404 leaked query/secret", failures)
    require("Restablecer app/PWA" in html, "404 response lacks PWA reset button", failures)

    api = client.get("/api/ruta-inventada-v898?token=SHOULD_NOT_APPEAR")
    payload = api.get_json(silent=True) or {}
    require(api.status_code == 404 and payload.get("error") == "not_found", "API 404 JSON not controlled", failures)
    require("SHOULD_NOT_APPEAR" not in json.dumps(payload), "API 404 leaked query token", failures)

    sw = client.get("/service-worker.js")
    sw_text = sw.get_data(as_text=True)
    require(sw.status_code == 200 and ("NEMESIS_CACHE_V898" in sw_text or "NEMESIS_CACHE_V899" in sw_text), "service worker V898/V899 unavailable", failures)
    require("res.status===404" in sw_text and "caches.open" not in sw_text and ".put(" not in sw_text, "service worker caches or serves 404 incorrectly", failures)
    require(client.get("/manifest.json").status_code == 200, "manifest route not 200", failures)

    for route in ["/api/admin/not-found-events", "/api/admin/route-map"]:
        require(client.get(route).status_code == 403, f"{route} not protected", failures)

    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH) as zf:
            names = set(zf.namelist())
        require("reference_images/README.md" in names, "ZIP missing reference_images/README.md", failures)
        require("reference_images/reference_manifest.json" in names, "ZIP missing reference_manifest.json", failures)

    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "codex_outbox.md"
    if outbox.exists():
        text = outbox.read_text(encoding="utf-8", errors="replace")
        active = text.split("## Prompts archivados / obsoletos", 1)[0]
        for route in ["/partidos", "/calendar", "/live", "/directo", "/picks", "/shark"]:
            require(f"{route} 500" not in active and f"{route}:500" not in active and f"HTTP 500" not in active, f"outbox active section still has obsolete 500 prompt near {route}", failures)

    if failures:
        print("V898 404 PWA reference outbox truth check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V898 404 PWA reference outbox truth check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
