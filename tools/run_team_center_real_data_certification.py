#!/usr/bin/env python3
"""Realistic local certification for Team Center using existing local data only."""

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
from urllib.parse import quote, unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MADRID = ZoneInfo("Europe/Madrid")
CONTRACT = "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1"
SOURCE_DB = ROOT / "data" / "v844_smoke.db"
REAL_DB = ROOT / "data" / "database.db"
OUTPUT_DEFAULT = ROOT / "browser_qa" / "TEAM_CENTER_REAL_DATA_CERTIFICATION"

PROFILES = {
    "desktop_1366x768": {"width": 1366, "height": 768, "is_mobile": False},
    "tablet_834x1194": {"width": 834, "height": 1194, "is_mobile": False},
    "mobile_390x844": {"width": 390, "height": 844, "is_mobile": True},
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

CASE_DEFINITIONS = [
    {
        "id": "complete_fixture_club_local",
        "route": "/team/Club%20Local",
        "expected_status": 200,
        "category": "equipo con datos completos de fixture local",
        "source": "tests/test_team_center_premium_experience.py",
    },
    {
        "id": "partial_seed_real_madrid",
        "route": "/team/Real%20Madrid",
        "expected_status": 200,
        "category": "equipo seed real con datos parciales y sin partidos locales",
        "source": "data/v844_smoke.db teams(seed propio)",
    },
    {
        "id": "no_crest_seed_malaga",
        "route": "/team/Malaga%20CF",
        "expected_status": 200,
        "category": "equipo seed sin escudo provider disponible",
        "source": "data/v844_smoke.db teams(seed propio)",
    },
    {
        "id": "long_name_fixture",
        "route": "/team/Real%20Club%20Deportivo%20Local",
        "expected_status": 200,
        "category": "nombre largo con fixture local",
        "source": "tests/test_v944_match_center_foundation.py",
    },
    {
        "id": "alias_seed_barcelona",
        "route": "/team/Barcelona",
        "expected_status": 200,
        "category": "alias que resuelve equipo seed existente",
        "source": "data/v844_smoke.db + SPORTSDB_SEARCH_ALIASES",
    },
    {
        "id": "wide_calendar_fixture_pattern",
        "route": "/team/Local%200",
        "expected_status": 200,
        "category": "calendario amplio de fixture QA existente",
        "source": "tests/test_v940_calendar_sports_experience.py pattern",
    },
    {
        "id": "international_seed_manchester_united",
        "route": "/team/Manchester%20United",
        "expected_status": 200,
        "category": "equipo internacional seed si existe localmente",
        "source": "data/v844_smoke.db teams(seed propio)",
        "optional": True,
    },
    {
        "id": "unresolved_safe_state",
        "route": "/team/Equipo%20No%20Disponible%20QA",
        "expected_status": 404,
        "category": "equipo no resuelto con estado seguro",
        "source": "estado negativo controlado, sin inventar entidad",
    },
]


def madrid_now() -> str:
    return datetime.now(MADRID).replace(microsecond=0).isoformat()


def insert_row(connection: sqlite3.Connection, table: str, payload: dict) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    data = {key: value for key, value in payload.items() if key in columns}
    if not data:
        return
    keys = list(data)
    placeholders = ",".join("?" for _ in keys)
    connection.execute(
        f"INSERT OR REPLACE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
        [data[key] for key in keys],
    )


def rows_from_source_db() -> tuple[list[dict], list[dict]]:
    if not SOURCE_DB.exists():
        return [], []
    connection = sqlite3.connect(f"file:{SOURCE_DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    teams = [dict(row) for row in connection.execute("SELECT * FROM teams ORDER BY name")]
    competitions = [dict(row) for row in connection.execute("SELECT * FROM competitions ORDER BY name")]
    connection.close()
    return teams, competitions


def match_payload(
    match_id: str,
    date: str,
    home: str,
    away: str,
    *,
    competition: str = "Liga Real",
    competition_key: str = "liga-real",
    competition_id: str = "140",
    status: str = "NS",
    home_score: str | None = None,
    away_score: str | None = None,
    score: str = "",
    source: str = "fixture-local",
    updated_at: str = "2026-07-28T10:00:00+02:00",
) -> dict:
    return {
        "id": match_id,
        "external_id": match_id,
        "sport_key": "soccer",
        "match_date": date,
        "kickoff_time": "20:30",
        "match_time": "20:30",
        "kickoff_iso": date + "T20:30:00+02:00",
        "competition_id": competition_id,
        "competition_key": competition_key,
        "competition_name": competition,
        "league_name": competition,
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
        "venue": "Estadio Central" if home in {"Club Local", "Real Club Deportivo Local"} else "",
        "season": "2026",
        "round": "Jornada QA",
        "source": source,
        "legal_note": "Fixture local existente para QA; no se presenta como dato real certificado.",
        "updated_at": updated_at,
    }


def seed_database(db_path: Path) -> dict:
    import app as app_module

    app_module.DB_PATH = str(db_path)
    app_module._SEEDED_DB_PATH = None
    app_module._SEEDING_DB_PATH = None
    if hasattr(app_module, "TEAM_IDENTITY_CACHE"):
        app_module.TEAM_IDENTITY_CACHE.clear()
    app_module.init_db()

    connection = sqlite3.connect(db_path)
    source_teams, source_competitions = rows_from_source_db()
    for competition in source_competitions:
        insert_row(connection, "competitions", competition)
    for team in source_teams:
        insert_row(connection, "teams", team)

    # Existing fixture teams used by current Sports Core tests.
    fixture_teams = [
        {
            "key": "club-local",
            "name": "Club Local",
            "official_name": "Club Local FC",
            "country": "Spain",
            "league": "Liga Real",
            "logo_url": "/team-crest.svg?name=Club+Local",
            "external_id": "club-local",
            "source": "tests/test_team_center_premium_experience.py",
            "sync_status": "verified_fixture",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
        {
            "key": "real-club-deportivo-local",
            "name": "Real Club Deportivo Local",
            "official_name": "Real Club Deportivo Local",
            "country": "Spain",
            "league": "Competición de prueba local con nombre largo",
            "logo_url": "/team-crest.svg?name=Real+Club+Deportivo+Local",
            "external_id": "fixture-long-local",
            "source": "tests/test_v944_match_center_foundation.py",
            "sync_status": "verified_fixture",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
        {
            "key": "local-0",
            "name": "Local 0",
            "country": "Spain",
            "league": "Liga 0",
            "logo_url": "",
            "external_id": "fixture-v940-local-0",
            "source": "tests/test_v940_calendar_sports_experience.py",
            "sync_status": "fixture_stress",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    ]
    for team in fixture_teams:
        insert_row(connection, "teams", team)

    competitions = [
        {"key": "liga-real", "name": "Liga Real", "country": "Spain", "external_id": "140", "source": "fixture-local", "sync_status": "verified", "updated_at": "2026-07-28T10:00:00+02:00"},
        {"key": "test-local", "name": "Competición de prueba local con nombre largo", "country": "Spain", "external_id": "fixture-test-local", "source": "fixture-local", "sync_status": "verified", "updated_at": "2026-07-28T10:00:00+02:00"},
        {"key": "liga-0", "name": "Liga 0", "country": "Spain", "external_id": "fixture-liga-0", "source": "fixture-test", "sync_status": "fixture_stress", "updated_at": "2026-07-28T10:00:00+02:00"},
    ]
    for competition in competitions:
        insert_row(connection, "competitions", competition)

    matches = [
        match_payload("tc-complete-4", "2026-07-31", "Club Local", "Racing Este", status="NS"),
        match_payload("tc-complete-1", "2026-07-20", "Club Local", "Union Norte", status="FT", home_score="2", away_score="0", score="2-0"),
        match_payload("tc-complete-2", "2026-07-17", "Club Local", "Deportivo Centro", status="FT", home_score="1", away_score="1", score="1-1"),
        match_payload("tc-complete-3", "2026-07-13", "Club Local", "Atletico Sur", status="FT", home_score="0", away_score="1", score="0-1"),
        match_payload(
            "tc-long-1",
            "2026-07-29",
            "Real Club Deportivo Local",
            "Union Deportiva Visitante",
            competition="Competición de prueba local con nombre largo",
            competition_key="test-local",
            competition_id="fixture-test-local",
            status="NS",
        ),
        match_payload(
            "tc-long-2",
            "2026-07-12",
            "Real Club Deportivo Local",
            "Union Deportiva Visitante",
            competition="Competición de prueba local con nombre largo",
            competition_key="test-local",
            competition_id="fixture-test-local",
            status="FT",
            home_score="3",
            away_score="2",
            score="3-2",
        ),
    ]
    for index in range(18):
        date = f"2026-08-{(index % 24) + 1:02d}"
        matches.append(
            match_payload(
                f"tc-wide-{index}",
                date,
                "Local 0",
                f"Visitante {index}",
                competition=f"Liga {index % 4}",
                competition_key=f"liga-{index % 4}",
                competition_id=f"fixture-liga-{index % 4}",
                status="NS",
                source="tests/test_v940_calendar_sports_experience.py",
            )
        )
    for item in matches:
        insert_row(connection, "matches", item)

    insert_row(
        connection,
        "picks",
        {
            "id": "pick-team-realdata-1",
            "match_id": "tc-complete-4",
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
            "source": "tests/test_team_center_premium_experience.py",
            "legal_note": "Pick temporal de QA local; no produccion.",
            "created_at": "2026-07-28T10:00:00+02:00",
            "updated_at": "2026-07-28T10:00:00+02:00",
        },
    )
    connection.commit()
    connection.close()
    return {
        "source_db": str(SOURCE_DB),
        "source_db_read_only": True,
        "source_db_exists": SOURCE_DB.exists(),
        "source_teams_loaded": len(source_teams),
        "source_competitions_loaded": len(source_competitions),
        "real_db_excluded": str(REAL_DB),
        "fixtures_loaded": len(fixture_teams),
        "matches_loaded": len(matches),
    }


def is_visual_icon_text(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    codepoints = [ord(ch) for ch in text if not ch.isspace() and ch not in ("\ufe0f", "\u200d")]
    return bool(codepoints) and all(
        0x1F1E6 <= codepoint <= 0x1FAFF
        or 0x25A0 <= codepoint <= 0x25FF
        or 0x2600 <= codepoint <= 0x26FF
        for codepoint in codepoints
    )


def inspect_page(page) -> dict:
    return page.evaluate(
        r"""() => {
          const root = document.querySelector('[data-team-center-contract]');
          const text = (root ? root.innerText : document.body.innerText).replace(/\s+/g, ' ').trim();
          const allText = document.body.innerText.replace(/\s+/g, ' ').trim();
          const actions = Array.from((root || document).querySelectorAll('a, button, input, select'));
          const smallTargets = actions.filter((node) => {
            const rect = node.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32);
          }).map((node) => ({text: (node.innerText || node.getAttribute('aria-label') || '').trim(), width: Math.round(node.getBoundingClientRect().width), height: Math.round(node.getBoundingClientRect().height)}));
          const clippedText = Array.from((root || document).querySelectorAll('strong, p, span, small, a, button, dd, dt, li'))
            .filter((node) => {
              const style = getComputedStyle(node);
              if (style.overflow !== 'hidden') return false;
              return (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1) && style.textOverflow !== 'ellipsis';
            })
            .map((node) => (node.textContent || '').trim().slice(0, 120));
          const imageIssues = Array.from((root || document).querySelectorAll('img')).filter((img) => img.complete && img.naturalWidth === 0).map((img) => img.getAttribute('src') || '');
          const hrefs = Array.from((root || document).querySelectorAll('a[href]')).map((node) => node.getAttribute('href'));
          const layoutShift = performance.getEntriesByType('layout-shift').filter((entry) => !entry.hadRecentInput).reduce((sum, entry) => sum + entry.value, 0);
          return {
            root_count: document.querySelectorAll('[data-team-center-contract]').length,
            resource_unavailable_count: document.querySelectorAll('.resource-unavailable, [data-resource-unavailable]').length,
            contract: root?.getAttribute('data-team-center-contract') || '',
            sports_domain_contract: root?.getAttribute('data-sports-domain-model') || '',
            sports_knowledge_contract: root?.getAttribute('data-sports-knowledge-contract') || '',
            sports_graph_contract: root?.getAttribute('data-sports-graph-contract') || '',
            section_count: document.querySelectorAll('[data-team-center-section]').length,
            canonical_card_count: document.querySelectorAll('[data-v939-match-card-spec="canonical-v1"]').length,
            legacy_match_card_count: document.querySelectorAll('.card.match-card').length,
            admin_nav_count: document.querySelectorAll('.ns-admin-sidebar, [data-admin-sidebar]').length,
            client_sidebar_count: document.querySelectorAll('.ns-client-sidebar').length,
            mobile_bottom_nav_count: document.querySelectorAll('.bottom-nav, .v933-mobile-bottom-nav').length,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            unsafe_literal_visible: /\b(?:None|null|undefined|Traceback|sqlite3\.OperationalError)\b/.test(text),
            fake_claim_visible: /\b(?:garantizado|seguro que gana|beneficio asegurado)\b/i.test(allText),
            missing_state_visible: allText.includes('No disponible') || allText.includes('Información pendiente') || allText.includes('Informacion pendiente') || allText.includes('Ninguna fuente lo confirma'),
            no_fake_copy_visible: allText.includes('no se presenta como dato real certificado') || allText.includes('sin datos inventados') || allText.includes('No disponible'),
            image_issues: imageIssues,
            hrefs,
            small_targets: smallTargets,
            clipped_text: clippedText,
            cls: Number(layoutShift.toFixed(4)),
            text_length: text.length || allText.length,
          };
        }"""
    )


def extract_api_contract(page) -> dict:
    payload = page.evaluate("() => JSON.parse(document.body.innerText)")
    if not isinstance(payload, dict) or not payload.get("ok"):
        return {"ok": False, "payload_ok": bool(isinstance(payload, dict) and payload.get("ok"))}
    center = ((payload.get("team") or {}).get("team_center") or {})
    team = center.get("team") or {}
    canonical = team.get("canonical") or {}
    identity = team.get("identity") or {}
    data_quality = center.get("data_quality") or {}
    graph = center.get("sports_graph") or {}
    return {
        "ok": True,
        "contract": center.get("contract"),
        "canonical_team_id": canonical.get("canonical_team_id"),
        "provider_team_ids": canonical.get("provider_team_ids"),
        "official_name": canonical.get("official_name") or team.get("official_name"),
        "display_name": canonical.get("display_name") or team.get("name"),
        "aliases": canonical.get("aliases") or [],
        "crest": canonical.get("crest") or identity.get("crest_url"),
        "crest_source": canonical.get("crest_source") or identity.get("crest_source") or identity.get("provider"),
        "competition_ids": canonical.get("competition_ids") or [],
        "matches": center.get("metrics", {}).get("upcoming", 0) + center.get("metrics", {}).get("recent", 0),
        "recent_form": center.get("form", {}).get("sample_size", 0),
        "upcoming_matches": center.get("metrics", {}).get("upcoming", 0),
        "recent_results": center.get("metrics", {}).get("recent", 0),
        "streak": center.get("streak", {}).get("label"),
        "freshness": data_quality.get("freshness"),
        "source": data_quality.get("source"),
        "data_quality": data_quality.get("certification_state"),
        "limitations": data_quality.get("limitations") or [],
        "relationships": graph.get("relationships") or [],
        "graph_edges": center.get("metrics", {}).get("graph_edges", 0),
        "diagnostics": center.get("diagnostics") or {},
        "no_fake_data": center.get("no_fake_data"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_DEFAULT))
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ.setdefault("SECRET_KEY", "team-center-real-data-certification")
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY", "APISPORTS_KEY", "API_FOOTBALL_KEY", "THESPORTSDB_KEY", "THESPORTSDB_API_KEY"):
        os.environ[key] = ""

    db_path = Path(tempfile.gettempdir()) / "nemesis_team_center_real_data_certification.sqlite"
    os.environ["DB_PATH"] = str(db_path)
    if db_path.exists():
        db_path.unlink()
    inventory = seed_database(db_path)

    import app as app_module
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, app_module.app)
    base_url = f"http://127.0.0.1:{server.server_port}"
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
                for case in CASE_DEFINITIONS:
                    route = case["route"]
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    server_errors: list[dict] = []
                    failed_assets: list[dict] = []
                    provider_requests: list[str] = []
                    external_requests: list[str] = []
                    def record_console(message, bucket=console_errors) -> None:
                        if message.type != "error":
                            return
                        text = message.text or ""
                        if case["expected_status"] == 404 and "Failed to load resource: the server responded with a status of 404" in text:
                            return
                        bucket.append(text)

                    page.on("console", record_console)
                    page.on("pageerror", lambda error, bucket=page_errors: bucket.append(str(error)))

                    def record_request(request) -> None:
                        parsed = urlparse(request.url)
                        host = parsed.netloc.lower()
                        if host and not host.startswith("127.0.0.1"):
                            external_requests.append(request.url)
                        if any(token in host for token in BLOCKED_PROVIDER_HOSTS):
                            provider_requests.append(request.url)

                    def record_response(response) -> None:
                        if response.status >= 500:
                            server_errors.append({"status": response.status, "url": response.url})
                        if response.status >= 400 and response.request.resource_type in {"image", "media", "font", "stylesheet", "script"}:
                            failed_assets.append({"status": response.status, "url": response.url, "type": response.request.resource_type})

                    page.on("request", record_request)
                    page.on("response", record_response)
                    url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
                    response = page.goto(url, wait_until="networkidle", timeout=30_000)
                    page.wait_for_timeout(350)
                    failures: list[str] = []
                    metrics = inspect_page(page)
                    api_contract: dict = {}
                    screenshot = ""
                    optional_skipped = bool(case.get("optional") and response is not None and response.status == 404)
                    if response is None or (response.status != case["expected_status"] and not optional_skipped):
                        failures.append(f"http_status={response.status if response else 'none'}")

                    if case["expected_status"] == 200 and not optional_skipped:
                        if metrics["root_count"] != 1:
                            failures.append("team_center_root_not_unique")
                        if metrics["contract"] != CONTRACT:
                            failures.append("team_center_contract_missing")
                        if metrics["section_count"] < 10:
                            failures.append("team_center_sections_missing")
                        if metrics["legacy_match_card_count"]:
                            failures.append("legacy_match_cards_present")
                        if metrics["admin_nav_count"]:
                            failures.append("admin_navigation_mixed")
                        if metrics["client_sidebar_count"] > 1 or metrics["mobile_bottom_nav_count"] > 1:
                            failures.append("navigation_duplicated")
                        if not metrics["missing_state_visible"]:
                            failures.append("missing_state_not_visible")
                        api_page = context.new_page()
                        team_identifier = unquote(route.rsplit("/", 1)[-1])
                        api_route = "/api/teams/" + quote(team_identifier, safe="") + "/detail"
                        api_response = api_page.goto(urljoin(base_url.rstrip("/") + "/", api_route.lstrip("/")), wait_until="networkidle", timeout=30_000)
                        try:
                            api_contract = extract_api_contract(api_page)
                        except Exception as exc:
                            api_contract = {"ok": False, "error": str(exc)}
                        api_page.close()
                        if api_response is None or api_response.status != 200:
                            failures.append("api_detail_not_200")
                        if not api_contract.get("ok"):
                            failures.append("api_contract_not_ok")
                        if api_contract.get("contract") != CONTRACT:
                            failures.append("api_contract_missing")
                        if not api_contract.get("canonical_team_id"):
                            failures.append("canonical_team_id_missing")
                        if api_contract.get("diagnostics", {}).get("database_writes") != 0:
                            failures.append("database_writes_reported")
                        if api_contract.get("diagnostics", {}).get("external_calls") != 0:
                            failures.append("external_calls_reported")
                        if api_contract.get("no_fake_data") is not True:
                            failures.append("no_fake_data_flag_missing")
                    else:
                        if optional_skipped:
                            pass
                        elif response is not None and response.status == 404 and "No disponible" not in page.inner_text("body"):
                            failures.append("safe_404_copy_missing")

                    meaningful_clipped = [text for text in metrics["clipped_text"] if not is_visual_icon_text(text)]
                    metrics["meaningful_clipped_text"] = meaningful_clipped
                    if metrics["horizontal_overflow"]:
                        failures.append("horizontal_overflow")
                    if meaningful_clipped:
                        failures.append("clipped_text")
                    if metrics["unsafe_literal_visible"]:
                        failures.append("unsafe_literal_visible")
                    if metrics["fake_claim_visible"]:
                        failures.append("fake_claim_visible")
                    if metrics["image_issues"]:
                        failures.append("broken_visible_images")
                    if metrics["cls"] > 0.1:
                        failures.append("cls_significant")
                    if profile["is_mobile"] and metrics["small_targets"]:
                        failures.append("small_mobile_targets")
                    if console_errors:
                        failures.append("console_errors")
                    if page_errors:
                        failures.append("page_errors")
                    if server_errors:
                        failures.append("server_5xx")
                    if failed_assets:
                        failures.append("failed_assets")
                    if provider_requests:
                        failures.append("provider_call_during_render")
                    if external_requests:
                        failures.append("external_request_during_render")

                    if case["expected_status"] == 200 and not optional_skipped:
                        screenshot_path = output / f"{profile_name}__{case['id']}.png"
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        screenshot = screenshot_path.relative_to(ROOT).as_posix()
                    results.append({
                        "profile": profile_name,
                        "case": case,
                        "url": url,
                        "http_status": response.status if response else None,
                        "screenshot": screenshot,
                        "metrics": metrics,
                        "api_contract": api_contract,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "server_errors": server_errors,
                        "failed_assets": failed_assets,
                        "provider_requests": sorted(set(provider_requests)),
                        "external_requests": sorted(set(external_requests)),
                        "failures": failures,
                        "status": "SKIPPED" if optional_skipped and not failures else "PASS" if not failures else "FAIL",
                    })
                    page.close()
                context.close()
            browser.close()
    finally:
        server.shutdown()

    failures = [
        {"profile": item["profile"], "case_id": item["case"]["id"], "failures": item["failures"]}
        for item in results
        if item["failures"]
    ]
    payload = {
        "version": CONTRACT,
        "generated_at_madrid": madrid_now(),
        "base_url": base_url,
        "inventory": inventory,
        "db_path": str(db_path),
        "db_is_temporary": True,
        "real_db_excluded": str(REAL_DB),
        "read_only_browser": True,
        "production_modified": False,
        "telegram_sent": False,
        "stripe_called": False,
        "external_provider_calls": sum(len(item["provider_requests"]) for item in results),
        "external_requests": sum(len(item["external_requests"]) for item in results),
        "screenshots_captured": len([item for item in results if item.get("screenshot")]),
        "profiles": list(PROFILES),
        "cases": CASE_DEFINITIONS,
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