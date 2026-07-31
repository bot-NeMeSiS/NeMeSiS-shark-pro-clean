#!/usr/bin/env python3
"""Product finalization Browser QA for key NeMeSiS surfaces.

Read-only QA against a temporary SQLite database. It does not call external
providers, Telegram, Stripe, OpenAI or production.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_competition_center_browser_qa import (  # noqa: E402
    BLOCKED_PROVIDER_HOSTS,
    PROFILES,
    madrid_now,
    seed_database as seed_competition_database,
)
from tools.run_action_platform_browser_qa import seed_action_data  # noqa: E402

MADRID = ZoneInfo("Europe/Madrid")

SCENARIOS = [
    {"key": "home", "route": "/", "audience": "public", "category": "client"},
    {"key": "dashboard", "route": "/app", "audience": "client", "category": "client"},
    {"key": "calendar", "route": "/calendar", "audience": "client", "category": "sports"},
    {"key": "live", "route": "/live", "audience": "client", "category": "sports"},
    {"key": "picks", "route": "/picks", "audience": "client", "category": "sports"},
    {"key": "track_record", "route": "/track-record", "audience": "client", "category": "sports"},
    {"key": "telegram", "route": "/telegram", "audience": "client", "category": "client"},
    {"key": "memberships", "route": "/memberships", "audience": "client", "category": "commerce"},
    {"key": "profile", "route": "/profile", "audience": "client", "category": "client"},
    {"key": "favorites", "route": "/favorites", "audience": "client", "category": "client"},
    {"key": "beta_program", "route": "/beta", "audience": "public", "category": "beta"},
    {"key": "company_landing", "route": "/landing", "audience": "public", "category": "commerce"},
    {"key": "company_pricing", "route": "/precios", "audience": "public", "category": "commerce"},
    {"key": "company_faq", "route": "/faq", "audience": "public", "category": "commerce"},
    {"key": "company_help", "route": "/help-center", "audience": "public", "category": "commerce"},
    {"key": "company_knowledge", "route": "/knowledge-base", "audience": "public", "category": "commerce"},
    {"key": "company_roadmap", "route": "/roadmap", "audience": "public", "category": "commerce"},
    {"key": "company_status", "route": "/service-status", "audience": "public", "category": "commerce"},
    {"key": "company_blog", "route": "/blog", "audience": "public", "category": "commerce"},
    {"key": "admin_go_to_market_office", "route": "/admin/go-to-market-office", "audience": "admin", "category": "commerce"},
    {"key": "match_center", "route": "/match/m-1", "audience": "client", "category": "sports_core"},
    {"key": "team_center", "route": "/team/Club%20Norte", "audience": "client", "category": "sports_core"},
    {"key": "competition_center", "route": "/competition/140", "audience": "client", "category": "sports_core"},
    {"key": "player_center", "route": "/player/101", "audience": "client", "category": "sports_core"},
    {"key": "shark", "route": "/shark", "audience": "client", "category": "intelligence"},
    {"key": "shark_intelligence", "route": "/shark-intelligence", "audience": "client", "category": "intelligence"},
    {"key": "action_platform", "route": "/smart-home", "audience": "client", "category": "personalization"},
    {"key": "user_intelligence", "route": "/user-intelligence", "audience": "client", "category": "personalization"},
    {"key": "admin_dashboard", "route": "/admin/dashboard", "audience": "admin", "category": "admin"},
    {"key": "developer_center", "route": "/admin/developer-center", "audience": "admin", "category": "admin"},
    {"key": "company_board", "route": "/admin/company-board", "audience": "admin", "category": "admin"},
    {"key": "operations_center", "route": "/admin/operations-center", "audience": "admin", "category": "admin"},
    {"key": "product_review_center", "route": "/admin/product-review-center", "audience": "admin", "category": "admin"},
    {"key": "executive_board", "route": "/admin/executive-board", "audience": "admin", "category": "admin"},
    {"key": "beta_center", "route": "/admin/beta-center", "audience": "admin", "category": "admin"},
    {"key": "sentinel_autopilot", "route": "/admin/sentinel-autopilot", "audience": "admin", "category": "admin"},
    {"key": "settings", "route": "/admin/system", "audience": "admin", "category": "admin"},
]


def session_cookie(app_module, role: str) -> str:
    serializer = app_module.app.session_interface.get_signing_serializer(app_module.app)
    if role == "ADMIN":
        payload = {
            "user_id": "qa-admin-product-finalization",
            "user_name": "Admin QA",
            "username": "admin_qa",
            "user_email": "admin-qa@example.invalid",
            "user_role": "ADMIN",
            "user_membership": "ADMIN",
            "membership": "ADMIN",
        }
    else:
        payload = {
            "user_id": "qa-action-platform",
            "user_name": "Cliente QA",
            "username": "cliente_qa",
            "user_email": "qa-action@example.invalid",
            "user_role": "PRO",
            "user_membership": "PRO",
            "membership": "PRO",
        }
    return serializer.dumps(payload)


def seed_extra_data(db_path: Path) -> None:
    seed_action_data(db_path)
    conn = sqlite3.connect(db_path)
    try:
        now = madrid_now()
        conn.execute(
            """INSERT OR REPLACE INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            ("qa-admin-product-finalization", "Admin QA", "admin_qa", "admin-qa@example.invalid", "not-used", "ADMIN", "ADMIN", now, now),
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS player_registry(
                player_id TEXT PRIMARY KEY,
                player_name TEXT,
                team_id TEXT,
                team_name TEXT,
                competition_id TEXT,
                competition_name TEXT,
                source TEXT,
                updated_at TEXT
            )"""
        )
        conn.execute(
            """INSERT OR REPLACE INTO player_registry(player_id,player_name,team_id,team_name,competition_id,competition_name,source,updated_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            ("101", "Jugador QA", "club-norte", "Club Norte", "140", "Liga Real", "browser_qa_temp_db", now),
        )
        conn.commit()
    finally:
        conn.close()


def inspect_page(page, scenario: dict) -> dict:
    return page.evaluate(
        """(scenario) => {
          const bodyText = document.body ? document.body.innerText.replace(/\\s+/g, ' ').trim() : '';
          const selectors = [
            '[data-action-platform-contract]',
            '[data-user-intelligence-contract]',
            '[data-shark-intelligence-contract]',
            '[data-match-center-contract]',
            '[data-team-center-contract]',
            '[data-competition-center-contract]',
            '[data-player-center-contract]',
            'main',
            '.v933-page',
            '.admin-page',
            'body'
          ];
          let root = null;
          for (const selector of selectors) {
            root = document.querySelector(selector);
            if (root) break;
          }
          const visibleText = (root ? root.innerText : bodyText).replace(/\\s+/g, ' ').trim();
          const actions = Array.from((root || document).querySelectorAll('a, button, input, select, textarea'));
          const visibleActions = actions.filter((node) => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
          });
          const smallTargets = visibleActions.filter((node) => {
            const rect = node.getBoundingClientRect();
            return rect.width < 32 || rect.height < 32;
          }).map((node) => ({
            text: (node.innerText || node.getAttribute('aria-label') || node.getAttribute('title') || '').trim().slice(0, 80),
            width: Math.round(node.getBoundingClientRect().width),
            height: Math.round(node.getBoundingClientRect().height),
            tag: node.tagName.toLowerCase(),
            classes: node.className || '',
            href: node.getAttribute('href') || '',
          })).slice(0, 12);
          const clippedText = Array.from((root || document).querySelectorAll('h1,h2,h3,strong,p,span,small,a,button,dd,dt,li,th,td'))
            .filter((node) => {
              if (node.classList && node.classList.contains('sr-only')) return false;
              if (node.getAttribute('aria-hidden') === 'true') return false;
              const text = (node.textContent || '').replace(/\\s+/g, '').trim();
              if (text && Array.from(text).every((char) => {
                const cp = char.codePointAt(0);
                return cp >= 0x1F1E6 && cp <= 0x1F1FF;
              })) return false;
              const rect = node.getBoundingClientRect();
              if (!rect.width || !rect.height || rect.width <= 2 || rect.height <= 2) return false;
              const style = getComputedStyle(node);
              if (style.visibility === 'hidden' || style.display === 'none') return false;
              return style.overflow === 'hidden' &&
                (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1) &&
                style.textOverflow !== 'ellipsis';
            })
            .map((node) => (node.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120))
            .filter(Boolean)
            .slice(0, 12);
          const brokenImages = Array.from((root || document).querySelectorAll('img'))
            .filter((img) => img.complete && img.naturalWidth === 0)
            .map((img) => img.getAttribute('src') || '')
            .slice(0, 12);
          const emptyLike = Array.from((root || document).querySelectorAll('section, article, .card, .v933-panel, .action-platform-card'))
            .filter((node) => {
              const text = (node.innerText || '').replace(/\\s+/g, ' ').trim();
              const rect = node.getBoundingClientRect();
              return rect.width > 80 && rect.height > 80 && text.length < 8;
            }).length;
          const primaryActions = Array.from((root || document).querySelectorAll('a[href], button'))
            .map((node) => (node.innerText || node.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim())
            .filter(Boolean);
          const mojibakeMatches = visibleText.match(/(?:\u00c3.|\u00c2.|\u00e2\u20ac\u2122|\u00e2\u20ac\u0153|\u00e2\u20ac|\ufffd)/g) || [];
          const technicalMatches = (visibleText.match(/\\b(?:Traceback|sqlite3\\.|OperationalError|Exception|stack trace)\\b/gi) || []).concat(visibleText.match(/\\b(?:TODO|FIXME)\\b/g) || []);
          return {
            title: document.title || '',
            path: window.location.pathname,
            text_length: visibleText.length,
            has_h1: !!document.querySelector('h1'),
            action_count: visibleActions.length,
            primary_actions_sample: primaryActions.slice(0, 10),
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            empty_like_blocks: emptyLike,
            unsafe_literal_visible: /\b(?:None|null|undefined)\b/.test(visibleText),
            mojibake_visible: /(?:\u00c3.|\u00c2.|\u00e2\u20ac\u2122|\u00e2\u20ac\u0153|\u00e2\u20ac|\ufffd)/.test(visibleText),
            technical_text_visible: /\\b(?:Traceback|sqlite3\\.|OperationalError|Exception|stack trace)\\b/i.test(visibleText) || /\\b(?:TODO|FIXME)\\b/.test(visibleText),
            mojibake_samples: mojibakeMatches.slice(0, 12),
            technical_samples: technicalMatches.slice(0, 12),
            transparency_visible: /(?:Procedencia|Evidencia|Frescura|Calidad|Limitaciones|No disponible|Fuente)/.test(visibleText),
            conversion_visible: /(?:PRO|ELITE|Plan|Membres|Comparar|Cuenta|Telegram|Picks)/i.test(visibleText),
            broken_images: brokenImages,
            small_targets: smallTargets,
            clipped_text: clippedText,
            category: scenario.category,
          };
        }""",
        scenario,
    )


def score_result(result: dict) -> tuple[int, list[str]]:
    score = 100
    failures: list[str] = []
    inspection = result.get("inspection") or {}
    hard_checks = {
        "server_errors": result.get("server_errors"),
        "console_errors": result.get("console_errors"),
        "page_errors": result.get("page_errors"),
        "external_requests": result.get("external_requests"),
        "provider_requests": result.get("provider_requests"),
        "broken_images": inspection.get("broken_images"),
        "small_targets": inspection.get("small_targets"),
        "clipped_text": inspection.get("clipped_text"),
    }
    if result.get("status") not in (200, 304):
        failures.append(f"http_status_{result.get('status')}")
        score -= 30
    for key, value in hard_checks.items():
        if value:
            failures.append(key)
            score -= 12
    for key in ("horizontal_overflow", "unsafe_literal_visible", "mojibake_visible", "technical_text_visible"):
        if inspection.get(key):
            failures.append(key)
            score -= 15
    if not inspection.get("has_h1"):
        failures.append("missing_h1")
        score -= 8
    if inspection.get("text_length", 0) < 120:
        failures.append("thin_visible_content")
        score -= 8
    if inspection.get("empty_like_blocks", 0) > 2:
        failures.append("empty_blocks_without_explanation")
        score -= 6
    return max(0, score), failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "browser_qa" / "PRODUCT_FINALIZATION"))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    db_path = ROOT / "tmp" / "nemesis_product_finalization_browser_qa.sqlite"
    db_path.parent.mkdir(exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    os.environ["DB_PATH"] = str(db_path)
    os.environ.setdefault("SECRET_KEY", "product-finalization-browser-qa-secret")
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY"):
        os.environ[key] = ""

    seed_competition_database(db_path)
    seed_extra_data(db_path)

    import app as app_module
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
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
                for scenario in SCENARIOS:
                    context = browser.new_context(
                        viewport={"width": profile["width"], "height": profile["height"]},
                        is_mobile=profile["is_mobile"],
                        has_touch=profile["is_mobile"],
                        locale="es-ES",
                        timezone_id="Europe/Madrid",
                        service_workers="block",
                    )
                    if scenario["audience"] in {"client", "admin"}:
                        role = "ADMIN" if scenario["audience"] == "admin" else "PRO"
                        context.add_cookies([
                            {
                                "name": app_module.app.config.get("SESSION_COOKIE_NAME", "session"),
                                "value": session_cookie(app_module, role),
                                "domain": "127.0.0.1",
                                "path": "/",
                                "httpOnly": True,
                                "sameSite": "Lax",
                            }
                        ])
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    server_errors: list[dict] = []
                    provider_requests: list[str] = []
                    external_requests: list[str] = []
                    page.on("console", lambda message, bucket=console_errors: bucket.append(message.text) if message.type == "error" else None)
                    page.on("pageerror", lambda error, bucket=page_errors: bucket.append(str(error)))

                    def record_response(response) -> None:
                        if response.status >= 500:
                            server_errors.append({"status": response.status, "url": response.url})

                    def record_request(request) -> None:
                        host = urlparse(request.url).netloc.lower()
                        if host and not host.startswith("127.0.0.1"):
                            external_requests.append(request.url)
                        if any(token in host for token in BLOCKED_PROVIDER_HOSTS):
                            provider_requests.append(request.url)

                    page.on("response", record_response)
                    page.on("request", record_request)
                    response = page.goto(base_url + scenario["route"], wait_until="domcontentloaded", timeout=45000)
                    try:
                        page.wait_for_load_state("load", timeout=10000)
                    except PlaywrightTimeoutError:
                        pass
                    page.wait_for_timeout(350)
                    status = response.status if response else 0
                    inspection = inspect_page(page, scenario)
                    screenshot = output / f"{profile_name}_{scenario['key']}.png"
                    page.screenshot(path=str(screenshot), full_page=True)
                    inspection["screenshot"] = str(screenshot)
                    result = {
                        "profile": profile_name,
                        "scenario": scenario["key"],
                        "route": scenario["route"],
                        "audience": scenario["audience"],
                        "category": scenario["category"],
                        "status": status,
                        "inspection": inspection,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "server_errors": server_errors,
                        "provider_requests": provider_requests,
                        "external_requests": external_requests,
                    }
                    result["experience_score"], result["failures"] = score_result(result)
                    results.append(result)
                    page.close()
                    context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)

    failures = [
        f"{item['profile']}::{item['scenario']}:{','.join(item['failures'])}"
        for item in results
        if item.get("failures")
    ]
    category_scores: dict[str, list[int]] = {}
    for item in results:
        category_scores.setdefault(item["category"], []).append(int(item["experience_score"]))
    category_summary = {
        key: round(sum(values) / len(values), 1) if values else 0
        for key, values in sorted(category_scores.items())
    }
    payload = {
        "ok": not failures,
        "generated_at_madrid": datetime.now(MADRID).replace(microsecond=0).isoformat(),
        "base_url": base_url,
        "database": "temporary_sqlite",
        "production_modified": False,
        "external_provider_calls": sum(len(item.get("provider_requests") or []) for item in results),
        "external_requests": sum(len(item.get("external_requests") or []) for item in results),
        "telegram_sends": 0,
        "stripe_calls": 0,
        "database_writes_real": 0,
        "scenarios": len(SCENARIOS),
        "viewports": list(PROFILES),
        "total_checks": len(results),
        "average_experience_score": round(sum(int(item["experience_score"]) for item in results) / len(results), 1) if results else 0,
        "category_scores": category_summary,
        "failures": failures,
        "results": results,
    }
    result_path = output / "browser_qa_result.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "ok": payload["ok"],
        "generated_at_madrid": payload["generated_at_madrid"],
        "total_checks": payload["total_checks"],
        "average_experience_score": payload["average_experience_score"],
        "category_scores": payload["category_scores"],
        "failures": payload["failures"][:30],
        "report": str(result_path),
    }, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


