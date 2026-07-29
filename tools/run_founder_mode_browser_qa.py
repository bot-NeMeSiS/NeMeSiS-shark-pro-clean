#!/usr/bin/env python3
"""Focused local Browser QA for Founder Mode.

Runs against a temporary SQLite database and a local Flask server. It blocks
external providers and does not send Telegram, call Stripe, push, deploy or
modify production.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_competition_center_browser_qa import (  # noqa: E402
    BLOCKED_PROVIDER_HOSTS,
    PROFILES,
    seed_database,
)

SCENARIOS = {
    "founder_dashboard": "/admin/founder-dashboard",
    "company_command_center": "/admin/company-command-center",
    "api_founder": "/api/admin/founder-dashboard",
}


def session_cookie(app_module) -> str:
    serializer = app_module.app.session_interface.get_signing_serializer(app_module.app)
    return serializer.dumps(
        {
            "user_id": "qa-founder-admin",
            "user_name": "Admin Founder QA",
            "username": "admin_founder_qa",
            "user_email": "founder-admin@example.invalid",
            "user_role": "ADMIN",
            "user_membership": "ADMIN",
            "membership": "ADMIN",
        }
    )


def inspect_founder_page(page) -> dict:
    return page.evaluate(
        """() => {
          const root = document.querySelector('[data-founder-command-center]');
          const text = (root ? root.innerText : document.body.innerText).replace(/\\s+/g, ' ').trim();
          const rect = root ? root.getBoundingClientRect() : document.body.getBoundingClientRect();
          const interactive = Array.from((root || document).querySelectorAll('a, button, input, select, textarea'));
          const smallTargets = interactive.filter((node) => {
            const box = node.getBoundingClientRect();
            return box.width > 0 && box.height > 0 && (box.width < 32 || box.height < 32);
          }).map((node) => ({
            text: (node.innerText || node.getAttribute('aria-label') || '').trim(),
            width: Math.round(node.getBoundingClientRect().width),
            height: Math.round(node.getBoundingClientRect().height),
          }));
          return {
            hasRoot: Boolean(root),
            contract: root ? root.getAttribute('data-founder-contract') : '',
            mode: root ? root.getAttribute('data-founder-mode') : '',
            hasFounderTitle: text.includes('Founder Dashboard'),
            hasBusinessKpis: text.includes('Business KPIs') || text.includes('Usuarios'),
            hasBetaControl: text.includes('Beta Control'),
            hasOperationsSummary: text.includes('Operations Summary'),
            hasReportExport: text.includes('Exportacion de informes'),
            hasDangerousWords: /deploy|push|Stripe|Telegram/i.test(text) && text.includes('sin'),
            hasLiteralNulls: /\b(None|null|undefined)\b/i.test(text),
            rootHeight: Math.round(rect.height),
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            smallTargets,
          };
        }"""
    )


def run(output_dir: Path, keep_server: bool = False) -> dict:
    tmp_dir = ROOT / "tmp" / "founder_mode_browser_qa"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "nemesis_founder_browser_qa.sqlite"
    if db_path.exists():
        db_path.unlink()
    seed_database(db_path)

    os.environ["DB_PATH"] = str(db_path)
    os.environ["SECRET_KEY"] = "founder-mode-browser-qa-secret"
    os.environ["BACKGROUND_JOBS_ENABLED"] = "false"
    os.environ["AUTO_GENERATE_PICKS"] = "false"
    os.environ["AUTO_SEND_TELEGRAM_PICKS"] = "false"

    import app as app_module  # noqa: E402
    from playwright.sync_api import sync_playwright  # noqa: E402
    from werkzeug.serving import make_server  # noqa: E402

    app_module.app.config.update(TESTING=True)
    server = make_server("127.0.0.1", 0, app_module.app)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    output_dir.mkdir(parents=True, exist_ok=True)
    cookie = session_cookie(app_module)
    results: list[dict] = []
    external_requests: list[str] = []
    js_errors: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for profile_name, profile in PROFILES.items():
                context = browser.new_context(
                    viewport={"width": profile["width"], "height": profile["height"]},
                    device_scale_factor=profile.get("device_scale_factor", 1),
                    is_mobile=profile.get("is_mobile", False),
                    has_touch=profile.get("has_touch", False),
                )
                context.add_cookies([
                    {
                        "name": "session",
                        "value": cookie,
                        "domain": "127.0.0.1",
                        "path": "/",
                        "httpOnly": True,
                        "sameSite": "Lax",
                    }
                ])

                def handle_route(route):
                    host = urlparse(route.request.url).netloc.lower()
                    if host and "127.0.0.1" not in host and any(token in host for token in BLOCKED_PROVIDER_HOSTS):
                        external_requests.append(route.request.url)
                        return route.abort()
                    return route.continue_()

                context.route("**/*", handle_route)
                page = context.new_page()
                page.on("pageerror", lambda exc: js_errors.append(str(exc)))
                page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)
                for key, route in SCENARIOS.items():
                    response = page.goto(base_url + route, wait_until="networkidle", timeout=20000)
                    status = response.status if response else 0
                    record = {"profile": profile_name, "scenario": key, "route": route, "status": status}
                    if key.startswith("api_"):
                        payload = page.locator("body").inner_text(timeout=5000)
                        record["api_ok"] = '"ok":true' in payload.replace(" ", "").lower()
                    else:
                        inspection = inspect_founder_page(page)
                        screenshot = output_dir / f"{profile_name}_{key}.png"
                        page.screenshot(path=str(screenshot), full_page=True)
                        record.update(inspection)
                        record["screenshot"] = screenshot.relative_to(ROOT).as_posix()
                    results.append(record)
                context.close()
            browser.close()
    finally:
        if not keep_server:
            server.shutdown()

    failures = []
    for record in results:
        if record["status"] >= 500 or record["status"] == 0:
            failures.append({"record": record, "reason": "http_error"})
        if record["scenario"].startswith("api_"):
            if not record.get("api_ok"):
                failures.append({"record": record, "reason": "api_not_ok"})
            continue
        if not record.get("hasRoot") or record.get("contract") != "NEMESIS-FOUNDER-COMMAND-CENTER-V1":
            failures.append({"record": record, "reason": "contract_missing"})
        if record.get("mode") != "read-only":
            failures.append({"record": record, "reason": "read_only_mode_missing"})
        if record.get("scrollWidth", 0) > record.get("clientWidth", 0) + 2:
            failures.append({"record": record, "reason": "horizontal_overflow"})
        if record.get("hasLiteralNulls"):
            failures.append({"record": record, "reason": "literal_null_visible"})
        if record.get("smallTargets"):
            failures.append({"record": record, "reason": "small_interactive_targets"})

    report = {
        "ok": not failures and not js_errors and not external_requests,
        "contract": "NEMESIS-FOUNDER-COMMAND-CENTER-V1",
        "base_url": base_url,
        "viewports": list(PROFILES),
        "results": results,
        "failures": failures,
        "js_errors": js_errors,
        "external_requests_blocked": external_requests,
        "database": "temporary_sqlite",
        "production_modified": False,
        "telegram_sent": False,
        "stripe_called": False,
        "push_executed": False,
        "deploy_executed": False,
    }
    (output_dir / "founder_mode_browser_qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="browser_qa/FOUNDER_MODE")
    parser.add_argument("--keep-server", action="store_true")
    args = parser.parse_args()
    report = run(ROOT / args.output, keep_server=args.keep_server)
    print(json.dumps({"ok": report["ok"], "failures": len(report["failures"]), "js_errors": len(report["js_errors"]), "external_requests_blocked": len(report["external_requests_blocked"]), "output": args.output}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())