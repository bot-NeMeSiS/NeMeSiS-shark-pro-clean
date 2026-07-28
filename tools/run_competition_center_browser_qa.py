#!/usr/bin/env python3
"""Focused read-only Browser QA for Competition Center Premium League Intelligence."""

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
from urllib.parse import urlparse
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
    "competition_page": "/competition/140",
    "competition_alias": "/competicion/140",
    "api_detail": "/api/competitions/140/detail",
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


def ensure_standings_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS api_football_standings_deep(
            league_id TEXT,
            league_name TEXT,
            team_id TEXT,
            team_name TEXT,
            rank INTEGER,
            played INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            points INTEGER,
            form TEXT,
            description TEXT,
            source TEXT,
            updated_at TEXT
        )"""
    )


def seed_database(db_path: Path) -> None:
    import app as app_module

    app_module.DB_PATH = str(db_path)
    app_module._SEEDED_DB_PATH = None
    app_module._SEEDING_DB_PATH = None
    app_module.init_db()
    connection = sqlite3.connect(db_path)
    ensure_standings_table(connection)
    insert_row(
        connection,
        "competitions",
        {
            "key": "liga-real",
            "name": "Liga Real",
            "country": "Spain",
            "scope": "League",
            "external_id": "140",
            "source": "browser_qa_temp_db",
            "sync_status": "verified",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    for key, name in (
        ("club-norte", "Club Norte"),
        ("club-sur", "Club Sur"),
        ("club-este", "Club Este"),
        ("club-oeste", "Club Oeste"),
    ):
        insert_row(
            connection,
            "teams",
            {
                "key": key,
                "name": name,
                "country": "Spain",
                "league": "Liga Real",
                "logo_url": "/team-crest.svg?name=" + name.replace(" ", "+"),
                "external_id": key,
                "source": "browser_qa_temp_db",
                "sync_status": "verified",
                "updated_at": "2026-07-28T10:00:00+02:00",
            },
        )
    matches = [
        ("m-1", "2026-07-20", "FT", "2", "0", "2-0", "Club Norte", "Club Sur"),
        ("m-2", "2026-07-31", "NS", None, None, "", "Club Este", "Club Oeste"),
    ]
    for match_id, date, status, home_score, away_score, score, home, away in matches:
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
                "home_team": home,
                "away_team": away,
                "home_team_id": home.lower().replace(" ", "-"),
                "away_team_id": away.lower().replace(" ", "-"),
                "home_logo": "/team-crest.svg?name=" + home.replace(" ", "+"),
                "away_logo": "/team-crest.svg?name=" + away.replace(" ", "+"),
                "status": status,
                "score": score,
                "home_score": home_score,
                "away_score": away_score,
                "venue": "Estadio Temporal QA",
                "season": "2026",
                "round": "Jornada 12",
                "source": "browser_qa_temp_db",
                "legal_note": "Datos temporales de QA local, no produccion.",
                "updated_at": date + "T22:30:00+02:00",
            },
        )
    for rank, team, points, goals_for, goals_against, description in (
        (1, "Club Norte", 26, 24, 10, "Champion"),
        (2, "Club Sur", 24, 19, 11, "Europa"),
        (3, "Club Este", 18, 14, 13, "Playoff"),
        (4, "Club Oeste", 9, 8, 22, "Descenso"),
    ):
        connection.execute(
            """INSERT INTO api_football_standings_deep
               (league_id, league_name, team_id, team_name, rank, played, wins, draws, losses,
                goals_for, goals_against, points, form, description, source, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "140",
                "Liga Real",
                team.lower().replace(" ", "-"),
                team,
                rank,
                12,
                6,
                3,
                3,
                goals_for,
                goals_against,
                points,
                "VVEVV",
                description,
                "browser_qa_temp_db",
                "2026-07-28T10:00:00+02:00",
            ),
        )
    insert_row(
        connection,
        "picks",
        {
            "id": "pick-competition-qa-1",
            "match_id": "m-2",
            "match_date": "2026-07-31",
            "sport_key": "soccer",
            "competition_key": "liga-real",
            "competition_name": "Liga Real",
            "home_team": "Club Este",
            "away_team": "Club Oeste",
            "pick_type": "1X2",
            "selection": "Club Este",
            "odds": 1.9,
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


def inspect_competition_page(page) -> dict:
    return page.evaluate(
        """() => {
          const root = document.querySelector('[data-competition-center-contract]');
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
          const clippedText = Array.from((root || document).querySelectorAll('strong, p, span, small, a, button, td, th'))
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
            root_count: document.querySelectorAll('[data-competition-center-contract]').length,
            contract: root?.getAttribute('data-competition-center-contract') || '',
            sports_domain_contract: root?.getAttribute('data-sports-domain-model') || '',
            sports_knowledge_contract: root?.getAttribute('data-sports-knowledge-contract') || '',
            sports_graph_contract: root?.getAttribute('data-sports-graph-contract') || '',
            section_count: document.querySelectorAll('[data-competition-center-section]').length,
            canonical_card_count: document.querySelectorAll('[data-v939-match-card-spec="canonical-v1"]').length,
            team_card_count: document.querySelectorAll('[data-competition-team-card]').length,
            standings_rows: document.querySelectorAll('[data-competition-standings-row]').length,
            legacy_match_card_count: document.querySelectorAll('.card.match-card').length,
            client_sidebar_count: document.querySelectorAll('.ns-client-sidebar').length,
            admin_nav_count: document.querySelectorAll('.ns-admin-sidebar, [data-admin-sidebar]').length,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            unsafe_literal_visible: /\\b(?:None|null|undefined)\\b/.test(visibleText),
            missing_state_visible: visibleText.includes('No disponible') || visibleText.includes('Informacion pendiente'),
            no_fake_claim_visible: visibleText.includes('No crea clasificaciones'),
            broken_images: brokenImages,
            text_length: visibleText.length,
            small_targets: smallTargets,
            clipped_text: clippedText,
          };
        }"""
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "browser_qa" / "COMPETITION_CENTER_PREMIUM_EXPERIENCE"))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_competition_center_browser_qa.sqlite")
    os.environ.setdefault("SECRET_KEY", "competition-center-browser-qa-secret")
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
                    url = base_url + route
                    response = page.goto(url, wait_until="networkidle")
                    status = response.status if response else 0
                    if scenario_name == "api_detail":
                        data = page.evaluate("() => JSON.parse(document.body.innerText)")
                        inspection = {
                            "api_ok": bool(data.get("ok")),
                            "contract": ((data.get("competition") or {}).get("competition_center") or {}).get("contract", ""),
                            "matches": ((data.get("competition") or {}).get("competition_center") or {}).get("metrics", {}).get("matches", 0),
                            "teams": ((data.get("competition") or {}).get("competition_center") or {}).get("metrics", {}).get("teams", 0),
                        }
                    else:
                        inspection = inspect_competition_page(page)
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
        if item["scenario"] == "api_detail":
            if item["status"] != 200 or not inspection.get("api_ok"):
                failures.append(f"{route_key}: api_not_ok")
            if inspection.get("contract") != "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1":
                failures.append(f"{route_key}: contract_missing")
            continue
        if item["status"] != 200:
            failures.append(f"{route_key}: http_{item['status']}")
        if inspection.get("root_count") != 1:
            failures.append(f"{route_key}: root_count")
        if inspection.get("contract") != "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1":
            failures.append(f"{route_key}: contract_missing")
        if inspection.get("section_count", 0) < 8:
            failures.append(f"{route_key}: section_count")
        if inspection.get("canonical_card_count", 0) < 2:
            failures.append(f"{route_key}: canonical_cards")
        if inspection.get("team_card_count", 0) < 4:
            failures.append(f"{route_key}: team_cards")
        if inspection.get("standings_rows", 0) < 4:
            failures.append(f"{route_key}: standings_rows")
        if inspection.get("legacy_match_card_count"):
            failures.append(f"{route_key}: legacy_match_card")
        if inspection.get("admin_nav_count"):
            failures.append(f"{route_key}: admin_nav_visible")
        if inspection.get("horizontal_overflow"):
            failures.append(f"{route_key}: horizontal_overflow")
        if inspection.get("unsafe_literal_visible"):
            failures.append(f"{route_key}: unsafe_literal")
        if inspection.get("broken_images"):
            failures.append(f"{route_key}: broken_images")
        if not inspection.get("missing_state_visible"):
            failures.append(f"{route_key}: missing_state_not_visible")
        if not inspection.get("no_fake_claim_visible"):
            failures.append(f"{route_key}: no_fake_claim_missing")
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
        "results": results,
        "failures": failures,
    }
    report_path = output / "browser_qa_result.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
