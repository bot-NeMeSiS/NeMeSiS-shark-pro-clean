#!/usr/bin/env python3
"""Focused read-only Browser QA for Team Center Premium Club Experience."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MADRID = ZoneInfo("Europe/Madrid")
PROFILES = {
    "desktop_1366x768": {"width": 1366, "height": 768, "is_mobile": False},
    "tablet_834x1194": {"width": 834, "height": 1194, "is_mobile": False},
    "mobile_390x844": {"width": 390, "height": 844, "is_mobile": True},
}
SCENARIOS = {
    "team_page": "/team/Club%20Local",
    "team_alias": "/equipo/Club%20Local",
    "api_detail": "/api/teams/Club%20Local/detail",
}
BLOCKED_PROVIDER_HOSTS = (
    "api-sports",
    "api-football",
    "thesportsdb",
    "the-odds-api",
    "api.telegram",
    "api.openai",
    "stripe.com",
)


def madrid_now() -> str:
    return datetime.now(MADRID).replace(microsecond=0).isoformat()


def insert_row(connection: sqlite3.Connection, table: str, payload: dict) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    data = {key: value for key, value in payload.items() if key in columns}
    keys = list(data)
    placeholders = ",".join("?" for _ in keys)
    connection.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
        [data[key] for key in keys],
    )


def seed_database(db_path: Path) -> None:
    import app as app_module

    app_module.DB_PATH = str(db_path)
    app_module._SEEDED_DB_PATH = None
    app_module._SEEDING_DB_PATH = None
    app_module.init_db()
    connection = sqlite3.connect(db_path)
    insert_row(
        connection,
        "competitions",
        {
            "key": "liga-real",
            "name": "Liga Real",
            "country": "Spain",
            "external_id": "140",
            "source": "browser_qa_temp_db",
            "sync_status": "verified",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    insert_row(
        connection,
        "teams",
        {
            "key": "club-local",
            "name": "Club Local",
            "country": "Spain",
            "league": "Liga Real",
            "logo_url": "/team-crest.svg?name=Club+Local",
            "external_id": "club-local",
            "source": "browser_qa_temp_db",
            "sync_status": "verified",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    matches = [
        ("m-4", "2026-07-31", "NS", None, None, "", "Racing Este"),
        ("m-1", "2026-07-20", "FT", "2", "0", "2-0", "Union Norte"),
        ("m-2", "2026-07-17", "FT", "1", "1", "1-1", "Deportivo Centro"),
        ("m-3", "2026-07-13", "FT", "0", "1", "0-1", "Atletico Sur"),
    ]
    for match_id, date, status, home_score, away_score, score, opponent in matches:
        insert_row(
            connection,
            "matches",
            {
                "id": match_id,
                "external_id": match_id,
                "sport_key": "soccer",
                "match_date": date,
                "kickoff_time": "20:30",
                "match_time": "20:30",
                "kickoff_iso": date + "T20:30:00+02:00",
                "competition_id": "140",
                "competition_key": "liga-real",
                "competition_name": "Liga Real",
                "league_name": "Liga Real",
                "country": "Spain",
                "home_team": "Club Local",
                "away_team": opponent,
                "home_team_id": "club-local",
                "away_team_id": opponent.lower().replace(" ", "-"),
                "home_logo": "/team-crest.svg?name=Club+Local",
                "away_logo": "/team-crest.svg?name=" + opponent.replace(" ", "+"),
                "status": status,
                "score": score,
                "home_score": home_score,
                "away_score": away_score,
                "venue": "Estadio Temporal QA",
                "season": "2026",
                "round": "Jornada QA",
                "source": "browser_qa_temp_db",
                "legal_note": "Datos temporales de QA local, no produccion.",
                "updated_at": date + "T22:30:00+02:00",
            },
        )
    insert_row(
        connection,
        "picks",
        {
            "id": "pick-team-qa-1",
            "match_id": "m-4",
            "match_date": "2026-07-31",
            "sport_key": "soccer",
            "competition_key": "liga-real",
            "competition_name": "Liga Real",
            "home_team": "Club Local",
            "away_team": "Racing Este",
            "pick_type": "1X2",
            "selection": "Club Local",
            "odds": 1.8,
            "confidence": 60,
            "stake_units": 1,
            "status": "published",
            "source": "browser_qa_temp_db",
            "legal_note": "Pick temporal de QA local, no produccion.",
            "created_at": "2026-07-28T10:00:00+02:00",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    connection.commit()
    connection.close()


def inspect_team_page(page) -> dict:
    return page.evaluate(
        """() => {
          const root = document.querySelector('[data-team-center-contract]');
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
          const clippedText = Array.from((root || document).querySelectorAll('strong, p, span, small, a, button'))
            .filter((node) => {
              const style = getComputedStyle(node);
              return style.overflow === 'hidden' &&
                (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1) &&
                style.textOverflow !== 'ellipsis';
            })
            .map((node) => (node.textContent || '').trim().slice(0, 120));
          return {
            root_count: document.querySelectorAll('[data-team-center-contract]').length,
            contract: root?.getAttribute('data-team-center-contract') || '',
            sports_domain_contract: root?.getAttribute('data-sports-domain-model') || '',
            sports_knowledge_contract: root?.getAttribute('data-sports-knowledge-contract') || '',
            sports_graph_contract: root?.getAttribute('data-sports-graph-contract') || '',
            section_count: document.querySelectorAll('[data-team-center-section]').length,
            canonical_card_count: document.querySelectorAll('[data-v939-match-card-spec="canonical-v1"]').length,
            legacy_match_card_count: document.querySelectorAll('.card.match-card').length,
            client_sidebar_count: document.querySelectorAll('.ns-client-sidebar').length,
            mobile_bottom_nav_count: document.querySelectorAll('.bottom-nav, .v933-mobile-bottom-nav').length,
            admin_nav_count: document.querySelectorAll('.ns-admin-sidebar, [data-admin-sidebar]').length,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            unsafe_literal_visible: /\b(?:None|null|undefined)\b/.test(visibleText),
            legacy_v540_visible: /\bV540\b/.test(visibleText),
            missing_state_visible: visibleText.includes('No disponible') || visibleText.includes('Informacion pendiente'),
            text_length: visibleText.length,
            small_targets: smallTargets,
            clipped_text: clippedText,
          };
        }"""
    )


def is_visual_icon_text(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    if "\u00f0\u0178\u2021" in text:
        return True
    codepoints = [
        ord(character)
        for character in text
        if not character.isspace() and character not in ("\ufe0f", "\u200d")
    ]
    return bool(codepoints) and all(0x1F1E6 <= codepoint <= 0x1F1FF for codepoint in codepoints)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "browser_qa" / "TEAM_CENTER_PREMIUM_CLUB_EXPERIENCE"))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_team_center_browser_qa.sqlite")
    os.environ.setdefault("SECRET_KEY", "team-center-browser-qa-secret")
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY"):
        os.environ[key] = ""
    db_path = Path(os.environ["DB_PATH"])
    if db_path.exists():
        db_path.unlink()
    seed_database(db_path)

    import app as app_module
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

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
                    url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
                    response = page.goto(url, wait_until="networkidle", timeout=30_000)
                    page.wait_for_timeout(250)
                    failures: list[str] = []
                    metrics = {}
                    screenshot = ""

                    if scenario_name == "api_detail":
                        api_payload = page.evaluate("() => JSON.parse(document.body.innerText)")
                        team_center = ((api_payload.get("team") or {}).get("team_center") or {}) if isinstance(api_payload, dict) else {}
                        if not api_payload.get("ok"):
                            failures.append("api_not_ok")
                        if team_center.get("contract") != "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1":
                            failures.append("api_contract_missing")
                        if (team_center.get("diagnostics") or {}).get("database_writes") != 0:
                            failures.append("api_reports_db_writes")
                        metrics = {"api_contract": team_center.get("contract"), "graph_edges": (team_center.get("metrics") or {}).get("graph_edges")}
                    else:
                        metrics = inspect_team_page(page)
                        metrics["meaningful_clipped_text"] = [
                            text
                            for text in metrics["clipped_text"]
                            if not is_visual_icon_text(text)
                        ]
                        screenshot_path = output / f"{profile_name}__{scenario_name}.png"
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        screenshot = screenshot_path.relative_to(ROOT).as_posix()
                        if metrics["root_count"] != 1:
                            failures.append("team_center_root_not_unique")
                        if metrics["contract"] != "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1":
                            failures.append("team_center_contract_missing")
                        if metrics["section_count"] < 10:
                            failures.append("team_center_sections_missing")
                        if metrics["canonical_card_count"] < 1:
                            failures.append("canonical_match_cards_missing")
                        if metrics["legacy_match_card_count"]:
                            failures.append("legacy_match_cards_present")
                        if metrics["admin_nav_count"]:
                            failures.append("admin_navigation_mixed_into_client")
                        if metrics["client_sidebar_count"] > 1 or metrics["mobile_bottom_nav_count"] > 1:
                            failures.append("navigation_duplicated")
                        if metrics["horizontal_overflow"]:
                            failures.append("horizontal_overflow")
                        if metrics["unsafe_literal_visible"]:
                            failures.append("unsafe_literal_visible")
                        if metrics["legacy_v540_visible"]:
                            failures.append("legacy_v540_visible")
                        if not metrics["missing_state_visible"]:
                            failures.append("missing_state_not_visible")
                        if profile["is_mobile"] and metrics["small_targets"]:
                            failures.append("small_mobile_targets")
                        if metrics["meaningful_clipped_text"]:
                            failures.append("clipped_text")

                    if response is None or response.status != 200:
                        failures.append(f"http_status={response.status if response else 'none'}")
                    if console_errors:
                        failures.append("console_errors")
                    if page_errors:
                        failures.append("page_errors")
                    if server_errors:
                        failures.append("server_5xx")
                    if provider_requests:
                        failures.append("provider_call_during_render")

                    results.append({
                        "profile": profile_name,
                        "scenario": scenario_name,
                        "route": route,
                        "url": url,
                        "http_status": response.status if response else None,
                        "screenshot": screenshot,
                        "metrics": metrics,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "server_errors": server_errors,
                        "provider_requests": sorted(set(provider_requests)),
                        "failures": failures,
                        "status": "PASS" if not failures else "FAIL",
                    })
                    page.close()
                context.close()
            browser.close()
    finally:
        server.shutdown()

    failures = [
        {"profile": item["profile"], "scenario": item["scenario"], "failures": item["failures"]}
        for item in results
        if item["failures"]
    ]
    payload = {
        "version": "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1",
        "generated_at_madrid": madrid_now(),
        "base_url": base_url,
        "db_path": str(db_path),
        "db_is_temporary": True,
        "read_only_browser": True,
        "production_modified": False,
        "telegram_sent": False,
        "stripe_called": False,
        "external_provider_calls": 0,
        "screenshots_captured": len([item for item in results if item.get("screenshot")]),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "results": results,
    }
    result_path = output / "browser_qa_result.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())