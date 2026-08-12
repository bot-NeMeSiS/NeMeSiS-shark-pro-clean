#!/usr/bin/env python3
"""Browser QA for the one-click NeMeSiS LOCAL SAFE experience."""
from __future__ import annotations

import json
import os
import sys
import threading
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "local_desktop"))
sys.path.insert(0, str(ROOT))

import run_local_desktop as local_runner


def main() -> int:
    output = ROOT / "tmp" / "local_desktop_browser_qa"
    output.mkdir(parents=True, exist_ok=True)
    port = local_runner.select_port()
    local_runner.configure_local_environment("offline_safe", port, db_name="nemesis_local_browser_qa.db")
    import app as app_module

    fixtures = local_runner.seed_local_database(app_module)
    server = make_server("127.0.0.1", port, app_module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    token = urllib.parse.quote(os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"])
    base = f"http://127.0.0.1:{port}"
    results = []
    js_errors = []
    external_requests = []
    profiles = {
        "desktop": {"viewport": {"width": 1440, "height": 1000}},
        "mobile": {"viewport": {"width": 390, "height": 844}, "is_mobile": True},
    }
    client_routes = (
        "/app", "/match/local-match-2", "/team/club-local-qa",
        "/competition/liga-local-qa", "/player/local-player-101",
        "/shark", "/picks", "/membresias",
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for profile, options in profiles.items():
                context = browser.new_context(**options)
                page = context.new_page()
                page.on("pageerror", lambda exc, p=profile: js_errors.append({"profile": p, "error": str(exc)}))
                page.on("request", lambda req, p=profile: external_requests.append({"profile": p, "url": req.url}) if urllib.parse.urlparse(req.url).hostname not in {"127.0.0.1", "localhost"} and urllib.parse.urlparse(req.url).scheme in {"http", "https"} else None)
                response = page.goto(f"{base}/local-safe?token={token}", wait_until="domcontentloaded")
                inspection = page.evaluate("""() => ({
                  portal: Boolean(document.querySelector('[data-local-safe-portal]')),
                  banner: Boolean(document.querySelector('[data-local-safe-banner]')),
                  overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
                  brokenImages: Array.from(document.images).filter(img => img.complete && img.naturalWidth === 0).map(img => img.src),
                  buttons: Array.from(document.querySelectorAll('.local-safe-action-grid a')).map(node => node.textContent.trim()),
                  text: document.body.innerText.replace(/\\s+/g, ' ').trim(),
                })""")
                page.screenshot(path=str(output / f"{profile}_portal.png"), full_page=True)
                results.append({"profile": profile, "route": "/local-safe", "status": response.status if response else 0, **inspection})
                login = page.goto(f"{base}/local-safe/login/client?token={token}", wait_until="domcontentloaded")
                results.append({"profile": profile, "route": "client_login", "status": login.status if login else 0, "final_url": page.url})
                for route in client_routes:
                    response = page.goto(base + route, wait_until="domcontentloaded")
                    state = page.evaluate("""() => ({
                      overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
                      brokenImages: Array.from(document.images).filter(img => img.complete && img.naturalWidth === 0 && getComputedStyle(img).display !== 'none').map(img => img.src),
                      localBanner: Boolean(document.querySelector('[data-local-safe-banner]')),
                    })""")
                    results.append({"profile": profile, "route": route, "status": response.status if response else 0, **state})
                page.screenshot(path=str(output / f"{profile}_match_center.png"), full_page=True)
                context.close()

                admin_context = browser.new_context(**options)
                admin_page = admin_context.new_page()
                admin_page.on("pageerror", lambda exc, p=profile: js_errors.append({"profile": p, "error": str(exc)}))
                admin_page.on("request", lambda req, p=profile: external_requests.append({"profile": p, "url": req.url}) if urllib.parse.urlparse(req.url).hostname not in {"127.0.0.1", "localhost"} and urllib.parse.urlparse(req.url).scheme in {"http", "https"} else None)
                response = admin_page.goto(f"{base}/local-safe/login/founder?token={token}", wait_until="domcontentloaded")
                founder_state = admin_page.evaluate("""() => ({
                  overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
                  localBanner: Boolean(document.querySelector('[data-local-safe-banner]')),
                  founder: Boolean(document.querySelector('[data-founder-command-center]')),
                  brokenImages: Array.from(document.images).filter(img => img.complete && img.naturalWidth === 0 && getComputedStyle(img).display !== 'none').map(img => img.src),
                })""")
                results.append({"profile": profile, "route": "/admin/founder-dashboard", "status": response.status if response else 0, **founder_state})
                admin_page.screenshot(path=str(output / f"{profile}_founder.png"), full_page=True)
                admin_context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        db_path = Path(app_module.DB_PATH)
        db_path.unlink(missing_ok=True)
        Path(str(db_path) + "-wal").unlink(missing_ok=True)
        Path(str(db_path) + "-shm").unlink(missing_ok=True)
    failures = []
    for item in results:
        if item.get("status", 0) >= 500 or item.get("status", 0) == 0:
            failures.append({"route": item.get("route"), "profile": item.get("profile"), "reason": "http"})
        if item.get("overflow"):
            failures.append({"route": item.get("route"), "profile": item.get("profile"), "reason": "overflow"})
        if item.get("brokenImages"):
            failures.append({"route": item.get("route"), "profile": item.get("profile"), "reason": "broken_images"})
        if item.get("route") == "/local-safe" and (not item.get("portal") or not item.get("banner") or len(item.get("buttons") or []) != 3):
            failures.append({"route": item.get("route"), "profile": item.get("profile"), "reason": "portal_contract"})
        if item.get("route") == "/admin/founder-dashboard" and not item.get("founder"):
            failures.append({"route": item.get("route"), "profile": item.get("profile"), "reason": "founder_contract"})
    report = {
        "ok": not failures and not js_errors and not external_requests,
        "profiles": list(profiles), "checks": len(results), "fixtures": fixtures,
        "failures": failures, "js_errors": js_errors, "external_requests": external_requests,
        "production_modified": False, "telegram_sent": False, "stripe_called": False,
        "results": results,
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("ok", "profiles", "checks", "failures", "js_errors", "external_requests", "production_modified", "telegram_sent", "stripe_called")}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())