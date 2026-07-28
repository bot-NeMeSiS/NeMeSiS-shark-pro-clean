#!/usr/bin/env python3
"""Focused local Browser QA for User Intelligence Platform."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_competition_center_browser_qa import (  # noqa: E402
    BLOCKED_PROVIDER_HOSTS,
    PROFILES,
    madrid_now,
    seed_database,
)


SCENARIOS = {
    "user_intelligence_page": "/user-intelligence",
    "user_intelligence_alias": "/inteligencia-usuario",
    "api_summary": "/api/user-intelligence/summary",
    "api_export": "/api/user-intelligence/export",
}


def seed_user_data(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT OR REPLACE INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            ("qa-user-intelligence", "Cliente QA", "cliente_qa", "qa@example.invalid", "not-used", "PRO", "PRO", madrid_now(), madrid_now()),
        )
        conn.execute(
            """INSERT OR REPLACE INTO favorites(id,user_id,kind,value,label,created_at)
               VALUES(?,?,?,?,?,?)""",
            ("fav-team-norte", "qa-user-intelligence", "team", "club-norte", "Club Norte", madrid_now()),
        )
        conn.execute(
            """INSERT OR REPLACE INTO favorites(id,user_id,kind,value,label,created_at)
               VALUES(?,?,?,?,?,?)""",
            ("fav-league-real", "qa-user-intelligence", "league", "liga-real", "Liga Real", madrid_now()),
        )
        events = [
            ("act-match", "view", "match", "match-browser-1", {"match_title": "Club Norte vs Club Sur", "home_team": "Club Norte", "away_team": "Club Sur", "competition_name": "Liga Real", "lane": "today"}),
            ("act-team", "view", "team", "club-norte", {"team_name": "Club Norte"}),
            ("act-competition", "view", "competition", "liga-real", {"competition_name": "Liga Real"}),
            ("act-filter", "view", "calendar", "calendar", {"lane": "favorites", "filter": "favorites"}),
        ]
        for event_id, activity_type, target_type, target_id, payload in events:
            conn.execute(
                """INSERT OR REPLACE INTO user_activity(id,user_id,activity_type,target_type,target_id,payload_json,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (event_id, "qa-user-intelligence", activity_type, target_type, target_id, json.dumps(payload, ensure_ascii=False), madrid_now()),
            )
        conn.execute(
            """INSERT OR REPLACE INTO client_profiles
               (id,name,membership_plan,favorite_teams_json,favorite_competitions_json,telegram_chat_id,preferences_json,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                "user-intelligence:8f6dfa88455af7e87f",
                "User Intelligence Profile",
                "PRO",
                "[]",
                "[]",
                "",
                json.dumps({"personalization_enabled": True, "consent_state": "GRANTED", "remember_filters": True}, ensure_ascii=False),
                madrid_now(),
                madrid_now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def session_cookie(app_module) -> str:
    serializer = app_module.app.session_interface.get_signing_serializer(app_module.app)
    return serializer.dumps(
        {
            "user_id": "qa-user-intelligence",
            "user_name": "Cliente QA",
            "username": "cliente_qa",
            "user_email": "qa@example.invalid",
            "user_role": "PRO",
            "user_membership": "PRO",
            "membership": "PRO",
        }
    )


def inspect_user_intelligence_page(page) -> dict:
    return page.evaluate(
        """() => {
          const root = document.querySelector('[data-user-intelligence-contract]');
          const visibleText = (root ? root.innerText : document.body.innerText).replace(/\\s+/g, ' ').trim();
          const actions = Array.from((root || document).querySelectorAll('a, button, input, select'));
          const smallTargets = actions.filter((node) => {
            const rect = node.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32);
          }).map((node) => ({
            text: (node.innerText || node.getAttribute('aria-label') || '').trim(),
            width: Math.round(node.getBoundingClientRect().width),
            height: Math.round(node.getBoundingClientRect().height),
          }));
          const clippedText = Array.from((root || document).querySelectorAll('strong, p, span, small, a, button, dd, dt, li'))
            .filter((node) => {
              const style = getComputedStyle(node);
              return style.overflow === 'hidden' &&
                (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1) &&
                style.textOverflow !== 'ellipsis';
            })
            .map((node) => (node.textContent || '').trim().slice(0, 120));
          const brokenImages = Array.from((root || document).querySelectorAll('img'))
            .filter((img) => img.complete && img.naturalWidth === 0)
            .map((img) => img.getAttribute('src') || '');
          return {
            root_count: document.querySelectorAll('[data-user-intelligence-contract]').length,
            contract: root?.getAttribute('data-user-intelligence-contract') || '',
            privacy_contract: root?.getAttribute('data-user-privacy-contract') || '',
            sports_domain_contract: root?.getAttribute('data-sports-domain-model') || '',
            sports_knowledge_contract: root?.getAttribute('data-sports-knowledge-contract') || '',
            sports_graph_contract: root?.getAttribute('data-sports-graph-contract') || '',
            shark_intelligence_contract: root?.getAttribute('data-shark-intelligence-contract') || '',
            section_count: document.querySelectorAll('[data-user-intelligence-section]').length,
            signal_count: document.querySelectorAll('[data-user-intelligence-signal]').length,
            recommendation_count: document.querySelectorAll('[data-user-intelligence-recommendation]').length,
            admin_nav_count: document.querySelectorAll('.ns-admin-sidebar, [data-admin-sidebar]').length,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            unsafe_literal_visible: /\\b(?:None|null|undefined)\\b/.test(visibleText),
            privacy_visible: document.querySelectorAll('[data-user-privacy-control]').length >= 4 && visibleText.toLowerCase().includes('privacidad'),
            no_auto_visible: visibleText.includes('No cambia la Home automaticamente'),
            no_external_visible: visibleText.includes('Datos salen de NeMeSiS') && visibleText.includes('No'),
            broken_images: brokenImages,
            text_length: visibleText.length,
            small_targets: smallTargets,
            clipped_text: clippedText,
          };
        }"""
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "browser_qa" / "USER_INTELLIGENCE_PLATFORM"))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_user_intelligence_browser_qa.sqlite")
    os.environ.setdefault("SECRET_KEY", "user-intelligence-browser-qa-secret")
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY"):
        os.environ[key] = ""
    db_path = Path(os.environ["DB_PATH"])
    if db_path.exists():
        db_path.unlink()
    seed_database(db_path)
    seed_user_data(db_path)

    import app as app_module
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    app_module.DB_PATH = str(db_path)
    app_module._SEEDED_DB_PATH = None
    app_module._SEEDING_DB_PATH = None

    server = make_server("127.0.0.1", 0, app_module.app)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results: list[dict] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for profile_name, profile in PROFILES.items():
                context = browser.new_context(
                    viewport={"width": profile["width"], "height": profile["height"]},
                    is_mobile=profile["is_mobile"],
                    has_touch=profile["is_mobile"],
                    locale="es-ES",
                    timezone_id="Europe/Madrid",
                    service_workers="block",
                )
                context.add_cookies([
                    {
                        "name": app_module.app.config.get("SESSION_COOKIE_NAME", "session"),
                        "value": session_cookie(app_module),
                        "domain": "127.0.0.1",
                        "path": "/",
                        "httpOnly": True,
                        "sameSite": "Lax",
                    }
                ])
                for scenario_name, route in SCENARIOS.items():
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    server_errors: list[dict] = []
                    provider_requests: list[str] = []
                    page.on("console", lambda message, bucket=console_errors: bucket.append(message.text) if message.type == "error" else None)
                    page.on("pageerror", lambda error, bucket=page_errors: bucket.append(str(error)))

                    def record_response(response) -> None:
                        if response.status >= 500:
                            server_errors.append({"status": response.status, "url": response.url})

                    def record_request(request) -> None:
                        host = urlparse(request.url).netloc.lower()
                        if any(token in host for token in BLOCKED_PROVIDER_HOSTS):
                            provider_requests.append(request.url)

                    page.on("response", record_response)
                    page.on("request", record_request)
                    response = page.goto(base_url + route, wait_until="networkidle")
                    status = response.status if response else 0
                    if scenario_name.startswith("api_"):
                        data = page.evaluate("() => JSON.parse(document.body.innerText)")
                        if scenario_name == "api_summary":
                            ui = data.get("user_intelligence") or {}
                        else:
                            ui = (data.get("export") or {}).get("snapshot") or {}
                        inspection = {
                            "api_ok": bool(data.get("ok")),
                            "contract": ui.get("contract", ""),
                            "privacy_contract": ui.get("privacy_contract", ""),
                            "external_calls": (ui.get("diagnostics") or {}).get("external_calls"),
                            "telegram_sends": (ui.get("diagnostics") or {}).get("telegram_sends"),
                            "stripe_calls": (ui.get("diagnostics") or {}).get("stripe_calls"),
                            "database_writes_by_get": (ui.get("diagnostics") or {}).get("database_writes_by_get"),
                            "personalization_enabled": ((ui.get("privacy") or {}).get("personalization_enabled")),
                        }
                    else:
                        inspection = inspect_user_intelligence_page(page)
                        screenshot = output / f"{profile_name}_{scenario_name}.png"
                        page.screenshot(path=str(screenshot), full_page=True)
                        inspection["screenshot"] = str(screenshot)
                    results.append({
                        "profile": profile_name,
                        "scenario": scenario_name,
                        "route": route,
                        "status": status,
                        "inspection": inspection,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "server_errors": server_errors,
                        "provider_requests": provider_requests,
                    })
                    page.close()
                context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)

    failures: list[str] = []
    for item in results:
        route_key = f"{item['profile']}::{item['scenario']}"
        inspection = item["inspection"]
        if item["status"] >= 500:
            failures.append(f"{route_key}: http_{item['status']}")
        if item["console_errors"]:
            failures.append(f"{route_key}: console_errors")
        if item["page_errors"]:
            failures.append(f"{route_key}: page_errors")
        if item["server_errors"]:
            failures.append(f"{route_key}: server_errors")
        if item["provider_requests"]:
            failures.append(f"{route_key}: provider_requests")
        if item["scenario"].startswith("api_"):
            if item["status"] != 200 or not inspection.get("api_ok"):
                failures.append(f"{route_key}: api_not_ok")
            if inspection.get("contract") != "USER-INTELLIGENCE-PLATFORM-V1":
                failures.append(f"{route_key}: contract_missing")
            if inspection.get("privacy_contract") != "USER-PRIVACY-CONTROLS-V1":
                failures.append(f"{route_key}: privacy_contract_missing")
            for key in ("external_calls", "telegram_sends", "stripe_calls", "database_writes_by_get"):
                if inspection.get(key) != 0:
                    failures.append(f"{route_key}: {key}")
            continue
        if item["status"] != 200:
            failures.append(f"{route_key}: http_{item['status']}")
        if inspection.get("root_count") != 1:
            failures.append(f"{route_key}: root_count")
        if inspection.get("contract") != "USER-INTELLIGENCE-PLATFORM-V1":
            failures.append(f"{route_key}: contract_missing")
        if inspection.get("privacy_contract") != "USER-PRIVACY-CONTROLS-V1":
            failures.append(f"{route_key}: privacy_contract_missing")
        if inspection.get("section_count", 0) < 6:
            failures.append(f"{route_key}: section_count")
        if inspection.get("signal_count", 0) < 6:
            failures.append(f"{route_key}: signal_count")
        if inspection.get("admin_nav_count"):
            failures.append(f"{route_key}: admin_nav_visible")
        if inspection.get("horizontal_overflow"):
            failures.append(f"{route_key}: horizontal_overflow")
        if inspection.get("unsafe_literal_visible"):
            failures.append(f"{route_key}: unsafe_literal")
        if inspection.get("broken_images"):
            failures.append(f"{route_key}: broken_images")
        if not inspection.get("privacy_visible"):
            failures.append(f"{route_key}: privacy_controls_missing")
        if not inspection.get("no_auto_visible"):
            failures.append(f"{route_key}: no_auto_copy_missing")
        if not inspection.get("no_external_visible"):
            failures.append(f"{route_key}: no_external_copy_missing")
        if inspection.get("small_targets"):
            failures.append(f"{route_key}: small_targets")
        if inspection.get("clipped_text"):
            failures.append(f"{route_key}: clipped_text")

    report = {
        "ok": not failures,
        "generated_at_madrid": madrid_now(),
        "base_url": base_url,
        "database": "temporary_sqlite",
        "external_provider_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "database_writes_real": 0,
        "results": results,
        "failures": failures,
    }
    report_path = output / "browser_qa_result.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
