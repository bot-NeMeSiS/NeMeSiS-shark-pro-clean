#!/usr/bin/env python3
"""Focused read-only Browser QA for Player Center Premium Sports Identity Platform."""

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
    "player_page": "/player/101",
    "player_alias": "/jugador/101",
    "player_unresolved": "/player/no-resuelto",
    "api_detail": "/api/players/101/detail",
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
    if not data:
        raise RuntimeError(f"No compatible columns for {table}")
    keys = list(data)
    placeholders = ",".join("?" for _ in keys)
    connection.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
        [data[key] for key in keys],
    )


def ensure_player_qa_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS api_football_live_events (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            match_id TEXT,
            player_id TEXT,
            player_name TEXT,
            related_player_id TEXT,
            related_player_name TEXT,
            team_id TEXT,
            team_name TEXT,
            event_type TEXT,
            type TEXT,
            detail TEXT,
            comments TEXT,
            elapsed INTEGER,
            minute INTEGER,
            source TEXT,
            captured_at TEXT,
            updated_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS api_football_lineups_deep (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            match_id TEXT,
            player_id TEXT,
            player_name TEXT,
            team_id TEXT,
            team_name TEXT,
            position TEXT,
            number TEXT,
            shirt_number TEXT,
            is_starting INTEGER,
            source TEXT,
            captured_at TEXT,
            updated_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS api_football_injuries_history (
            id TEXT PRIMARY KEY,
            fixture_id TEXT,
            match_id TEXT,
            player_id TEXT,
            player_name TEXT,
            team_id TEXT,
            team_name TEXT,
            type TEXT,
            reason TEXT,
            source TEXT,
            captured_at TEXT,
            updated_at TEXT
        )
        """
    )


def seed_database(db_path: Path) -> None:
    import app as app_module

    app_module.DB_PATH = str(db_path)
    app_module._SEEDED_DB_PATH = None
    app_module._SEEDING_DB_PATH = None
    app_module.init_db()
    connection = sqlite3.connect(db_path)
    ensure_player_qa_tables(connection)
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
        ("m-1", "2026-07-20", "FT", "2", "0", "2-0", "Union Norte"),
        ("m-2", "2026-07-31", "NS", None, None, "", "Racing Este"),
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
        "api_football_live_events",
        {
            "id": "m-1-goal-1",
            "fixture_id": "m-1",
            "match_id": "m-1",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "team_id": "club-local",
            "team_name": "Club Local",
            "event_type": "Goal",
            "type": "Goal",
            "detail": "Gol confirmado por proveedor cacheado",
            "elapsed": 12,
            "minute": 12,
            "source": "browser_qa_temp_db",
            "captured_at": "2026-07-20T22:30:00+02:00",
            "updated_at": "2026-07-20T22:30:00+02:00",
        },
    )
    insert_row(
        connection,
        "api_football_lineups_deep",
        {
            "id": "m-1-player-101",
            "fixture_id": "m-1",
            "match_id": "m-1",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "team_id": "club-local",
            "team_name": "Club Local",
            "position": "Delantero",
            "number": "9",
            "shirt_number": "9",
            "is_starting": 1,
            "source": "browser_qa_temp_db",
            "captured_at": "2026-07-20T22:30:00+02:00",
            "updated_at": "2026-07-20T22:30:00+02:00",
        },
    )
    insert_row(
        connection,
        "picks",
        {
            "id": "pick-player-qa-1",
            "match_id": "m-2",
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


def inspect_player_page(page) -> dict:
    return page.evaluate(
        r"""() => {
          const root = document.querySelector('[data-player-center-contract]');
          const visibleText = (root ? root.innerText : document.body.innerText).replace(/\s+/g, ' ').trim();
          const foldedText = visibleText.toLocaleLowerCase('es-ES');
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
          const brokenImages = Array.from((root || document).querySelectorAll('img'))
            .filter((img) => img.complete && img.naturalWidth === 0)
            .map((img) => img.getAttribute('src') || '');
          return {
            root_count: document.querySelectorAll('[data-player-center-contract]').length,
            contract: root?.getAttribute('data-player-center-contract') || '',
            sports_domain_contract: root?.getAttribute('data-sports-domain-model') || '',
            sports_knowledge_contract: root?.getAttribute('data-sports-knowledge-contract') || '',
            player_knowledge_contract: root?.getAttribute('data-player-knowledge-contract') || '',
            sports_graph_contract: root?.getAttribute('data-sports-graph-contract') || '',
            shark_intelligence_contract: root?.getAttribute('data-shark-intelligence-contract') || '',
            user_intelligence_contract: root?.getAttribute('data-user-intelligence-contract') || '',
            section_count: document.querySelectorAll('[data-player-center-section]').length,
            canonical_card_count: document.querySelectorAll('[data-v939-match-card-spec="canonical-v1"]').length,
            legacy_match_card_count: document.querySelectorAll('.card.match-card').length,
            client_sidebar_count: document.querySelectorAll('.ns-client-sidebar').length,
            admin_nav_count: document.querySelectorAll('.ns-admin-sidebar, [data-admin-sidebar]').length,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            unsafe_literal_visible: /\b(?:None|null|undefined)\b/.test(visibleText),
            missing_state_visible: visibleText.includes('No disponible') || visibleText.includes('Informacion pendiente'),
            transparency_visible: foldedText.includes('procedencia') && foldedText.includes('limitaciones'),
            text_length: visibleText.length,
            small_targets: smallTargets,
            clipped_text: clippedText,
            broken_images: brokenImages,
          };
        }"""
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "browser_qa" / "PLAYER_CENTER_PREMIUM_EXPERIENCE"))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_player_center_browser_qa.sqlite")
    os.environ.setdefault("SECRET_KEY", "player-center-browser-qa-secret")
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
                        player_center = ((api_payload.get("player") or {}).get("player_center") or {}) if isinstance(api_payload, dict) else {}
                        if not api_payload.get("ok"):
                            failures.append("api_not_ok")
                        if player_center.get("contract") != "PLAYER-CENTER-PREMIUM-SPORTS-IDENTITY-PLATFORM-V1":
                            failures.append("api_contract_missing")
                        if (player_center.get("diagnostics") or {}).get("database_writes") != 0:
                            failures.append("api_reports_db_writes")
                        metrics = {"api_contract": player_center.get("contract"), "graph_edges": (player_center.get("metrics") or {}).get("graph_edges")}
                    else:
                        metrics = inspect_player_page(page)
                        screenshot_path = output / f"{profile_name}__{scenario_name}.png"
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        screenshot = screenshot_path.relative_to(ROOT).as_posix()
                        if metrics["root_count"] != 1:
                            failures.append("player_center_root_not_unique")
                        if metrics["contract"] != "PLAYER-CENTER-PREMIUM-SPORTS-IDENTITY-PLATFORM-V1":
                            failures.append("player_center_contract_missing")
                        if metrics["section_count"] < 10:
                            failures.append("player_center_sections_missing")
                        if scenario_name != "player_unresolved" and metrics["canonical_card_count"] < 1:
                            failures.append("canonical_match_cards_missing")
                        if metrics["legacy_match_card_count"]:
                            failures.append("legacy_match_card_detected")
                        if metrics["admin_nav_count"]:
                            failures.append("admin_navigation_visible")
                        if metrics["horizontal_overflow"]:
                            failures.append("horizontal_overflow")
                        if metrics["unsafe_literal_visible"]:
                            failures.append("unsafe_literal_visible")
                        if not metrics["missing_state_visible"]:
                            failures.append("missing_state_not_visible")
                        if not metrics["transparency_visible"]:
                            failures.append("transparency_not_visible")
                        if metrics["broken_images"]:
                            failures.append("broken_images_visible")
                        if metrics["clipped_text"]:
                            failures.append("clipped_text_detected")
                        if metrics["small_targets"]:
                            failures.append("small_targets_detected")

                    if response is None or response.status != 200:
                        failures.append(f"http_status_{getattr(response, 'status', 'none')}")
                    if console_errors:
                        failures.append("console_errors")
                    if page_errors:
                        failures.append("page_errors")
                    if server_errors:
                        failures.append("server_errors")
                    if provider_requests:
                        failures.append("external_provider_requests")

                    results.append({
                        "profile": profile_name,
                        "scenario": scenario_name,
                        "url": url,
                        "status": getattr(response, "status", None),
                        "ok": not failures,
                        "failures": failures,
                        "metrics": metrics,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "server_errors": server_errors,
                        "provider_requests": provider_requests,
                        "screenshot": screenshot,
                    })
                    page.close()
                context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)

    summary = {
        "ok": all(item["ok"] for item in results),
        "generated_at_madrid": madrid_now(),
        "db_path": str(db_path),
        "production_modified": False,
        "external_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "results": results,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())



