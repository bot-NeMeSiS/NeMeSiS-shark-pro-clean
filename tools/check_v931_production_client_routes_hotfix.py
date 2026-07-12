from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from jinja2 import StrictUndefined


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V931_PRODUCTION_CLIENT_ROUTES_AND_HOME_DATA_CONSISTENCY_HOTFIX_FINAL"
V932_VERSION = "V932_AUTHENTICATED_PRODUCTION_CLIENT_ADMIN_AND_REAL_SPORTS_VALUE_FINAL"
V933_VERSION = "V933_REFERENCE_PARITY_PRODUCT_DESIGN_SPRINT_SYSTEM_FINAL"
V934_VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
V935_VERSION = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
V936_VERSION = "V936_COMMERCIAL_PRODUCT_READINESS_REFERENCE_EXCELLENCE_FINAL"
V937_VERSION = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
ALLOWED_VERSIONS = {VERSION, V932_VERSION, V933_VERSION, V934_VERSION, V935_VERSION, V936_VERSION, V937_VERSION}
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


PUBLIC_ROUTES = [
    "/", "/cliente-login", "/login", "/registro", "/calendar", "/calendario",
    "/live", "/directo", "/picks", "/track-record", "/support",
]
CLIENT_NO_SESSION = ["/app", "/profile", "/telegram", "/shark", "/memberships"]
CLIENT_SESSION = [
    "/app", "/calendar", "/live", "/picks", "/track-record", "/profile",
    "/telegram", "/shark", "/memberships",
]
ADMIN_SESSION = ["/admin/dashboard", "/admin/navigation-integrity"]


def mock_session(client, role: str) -> None:
    with client.session_transaction() as session:
        if role == "admin":
            session.update({
                "user_id": "v931-admin-check",
                "user_name": "Admin QA",
                "username": "admin_qa",
                "user_email": "admin@example.invalid",
                "user_role": "ADMIN",
                "membership": "ADMIN",
                "user_membership": "ADMIN",
            })
        else:
            session.update({
                "user_id": "v931-client-check",
                "user_name": "Cliente QA",
                "username": "client_qa",
                "user_email": "client@example.invalid",
                "user_role": "PRO",
                "membership": "PRO",
                "user_membership": "PRO",
            })


def route_rows(client, paths: list[str], profile: str, session_kind: str) -> list[dict]:
    rows = []
    for path in paths:
        response = client.get(path, follow_redirects=False)
        body = response.get_data(as_text=True)
        rows.append({
            "profile": profile,
            "session": session_kind,
            "path": path,
            "status": int(response.status_code),
            "location": response.headers.get("Location", ""),
            "ok": int(response.status_code) < 500,
            "jinja_undefined": "UndefinedError" in body,
            "database_locked": "database is locked" in body.lower(),
        })
    return rows


def create_legacy_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY, match_date TEXT, home_team TEXT, away_team TEXT)")
    conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY, match_id TEXT, status TEXT)")
    conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, email TEXT)")
    conn.commit()
    conn.close()


def create_home_consistency_db(path: Path, app_module) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE matches(
            id TEXT PRIMARY KEY, match_date TEXT, kickoff_time TEXT, match_time TEXT,
            kickoff_iso TEXT, competition_key TEXT, competition_name TEXT, league_name TEXT,
            country TEXT, home_team TEXT, away_team TEXT, status TEXT, minute TEXT, score TEXT,
            home_score TEXT, away_score TEXT, source TEXT, updated_at TEXT
        )"""
    )
    today = app_module.today_iso()
    tomorrow = app_module.today_iso(1)
    records = [
        ("valid", today, "18:30", "", "", "laliga", "LaLiga", "", "Spain", "Equipo Uno", "Equipo Dos", "scheduled", "", "", "", "", "api-sports", "2026-07-11T08:00:00"),
        ("no-comp", today, "19:00", "", "", "", "", "", "Spain", "Equipo Tres", "Equipo Cuatro", "scheduled", "", "", "", "", "api-sports", ""),
        ("no-time", today, "", "", "", "laliga", "LaLiga", "", "Spain", "Equipo Cinco", "Equipo Seis", "scheduled", "", "", "", "", "api-sports", ""),
        ("no-source", today, "20:00", "", "", "laliga", "LaLiga", "", "Spain", "Equipo Siete", "Equipo Ocho", "scheduled", "", "", "", "", "", ""),
        ("future", tomorrow, "21:00", "", "", "premier", "Premier League", "", "England", "Equipo Nueve", "Equipo Diez", "scheduled", "", "", "", "", "api-sports", ""),
    ]
    conn.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", records)
    conn.execute(
        """CREATE TABLE picks(
            id TEXT PRIMARY KEY, match_id TEXT, match_date TEXT, home_team TEXT, away_team TEXT,
            market TEXT, selection TEXT, odds REAL, status TEXT, result_status TEXT, source TEXT
        )"""
    )
    conn.commit()
    conn.close()


def switch_db(app_module, path: Path) -> None:
    app_module.DB_PATH = str(path)
    app_module._SEEDED_DB_PATH = str(path)
    app_module.APP_INITIALIZED = True
    app_module.initialize_once = lambda: True


def main() -> int:
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    current_version = version_bytes.decode("utf-8").strip().lstrip("\ufeff")
    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_v931_normal.sqlite")
    os.environ.setdefault("SECRET_KEY", "v931-local-check-only")
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    for key in ("TELEGRAM_BOT_TOKEN", "AUTOMATION_SECRET", "STRIPE_SECRET_KEY", "OPENAI_API_KEY"):
        os.environ[key] = ""

    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
    app_module.app.logger.disabled = True
    logging.disable(logging.CRITICAL)
    original_db = app_module.DB_PATH
    original_init = app_module.initialize_once
    original_issue = app_module.v931_record_client_route_issue
    original_v932_issue = getattr(app_module, "v932_record_authenticated_issue", None)
    original_fetch = app_module.fetch_json_url
    external_calls = {"count": 0}

    def blocked_external(*args, **kwargs):
        external_calls["count"] += 1
        raise AssertionError("external provider call during render")

    app_module.fetch_json_url = blocked_external
    app_module.v931_record_client_route_issue = lambda *args, **kwargs: True
    if original_v932_issue is not None:
        app_module.v932_record_authenticated_issue = lambda *args, **kwargs: True
    results: list[dict] = []

    normal_public = app_module.app.test_client()
    results += route_rows(normal_public, PUBLIC_ROUTES + CLIENT_NO_SESSION + ["/admin-login"], "normal", "public")
    normal_client = app_module.app.test_client()
    mock_session(normal_client, "client")
    results += route_rows(normal_client, CLIENT_SESSION, "normal", "client_mock")
    normal_admin = app_module.app.test_client()
    mock_session(normal_admin, "admin")
    results += route_rows(normal_admin, ADMIN_SESSION, "normal", "admin_mock")

    with tempfile.TemporaryDirectory(prefix="nemesis_v931_degraded_", ignore_cleanup_errors=True) as temp_dir:
        temp_root = Path(temp_dir)
        for profile in ("empty", "legacy"):
            db_path = temp_root / f"{profile}.sqlite"
            if profile == "legacy":
                create_legacy_db(db_path)
            else:
                sqlite3.connect(db_path).close()
            switch_db(app_module, db_path)
            public = app_module.app.test_client()
            results += route_rows(public, PUBLIC_ROUTES + CLIENT_NO_SESSION, profile, "public")
            client = app_module.app.test_client()
            mock_session(client, "client")
            results += route_rows(client, CLIENT_SESSION, profile, "client_mock")

        consistency_path = temp_root / "consistency.sqlite"
        create_home_consistency_db(consistency_path, app_module)
        switch_db(app_module, consistency_path)
        with app_module.app.test_request_context("/"):
            home_summary = app_module.get_public_home_sports_summary()
            legacy_summary = app_module.home_live_summary_data()
        consistency_response = app_module.app.test_client().get("/")

        locked_path = temp_root / "locked.sqlite"
        lock_conn = sqlite3.connect(locked_path, timeout=0.1)
        lock_conn.execute("PRAGMA journal_mode=DELETE")
        lock_conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY)")
        lock_conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY)")
        lock_conn.commit()
        lock_conn.execute("BEGIN EXCLUSIVE")
        switch_db(app_module, locked_path)
        locked_client = app_module.app.test_client()
        lock_started = time.monotonic()
        locked_results = route_rows(locked_client, ["/calendar", "/live", "/picks"], "locked", "public")
        lock_elapsed = round(time.monotonic() - lock_started, 2)
        results += locked_results
        lock_conn.rollback()
        lock_conn.close()

    app_module.DB_PATH = original_db
    app_module.initialize_once = original_init
    app_module.v931_record_client_route_issue = original_issue
    if original_v932_issue is not None:
        app_module.v932_record_authenticated_issue = original_v932_issue
    app_module.fetch_json_url = original_fetch

    runtime = app_module.app.test_client().get("/api/runtime-version").get_json(silent=True) or {}
    source = (ROOT / "app.py").read_text(encoding="utf-8-sig", errors="replace")
    failures = [item for item in results if not item["ok"] or item["jinja_undefined"] or item["database_locked"]]
    valid_today = home_summary.get("valid_matches_today") or []
    incomplete = home_summary.get("incomplete_matches") or []
    checks = {
        "version_v931_or_successor": current_version in ALLOWED_VERSIONS,
        "version_without_bom": not version_bytes.startswith(b"\xef\xbb\xbf"),
        "app_version_v931_or_successor": app_module.APP_VERSION == current_version,
        "runtime_v931_or_successor": runtime.get("version") == current_version,
        "runtime_files_match": runtime.get("version_files_match") is True,
        "runtime_aligned": runtime.get("deployment_alignment_status") == "aligned_local_files",
        "routes_no_500": not failures,
        "client_login_200": any(item["path"] == "/cliente-login" and item["status"] == 200 for item in results),
        "calendar_200": all(item["status"] == 200 for item in results if item["path"] == "/calendar"),
        "live_200": all(item["status"] == 200 for item in results if item["path"] == "/live"),
        "picks_200": all(item["status"] == 200 for item in results if item["path"] == "/picks"),
        "track_record_200": all(item["status"] == 200 for item in results if item["path"] == "/track-record"),
        "app_without_session_safe_redirect": any(item["path"] == "/app" and item["session"] == "public" and item["status"] in {301, 302, 303, 307, 308} for item in results),
        "home_count_matches_visible_list": home_summary.get("valid_matches_today_count") == len(valid_today) == legacy_summary.get("counts", {}).get("today") == len(legacy_summary.get("upcoming_matches") or []),
        "incomplete_matches_separated": len(incomplete) == 3 and not any(item.get("id") in {"no-comp", "no-time", "no-source"} for item in valid_today),
        "valid_matches_have_essentials": all(app_module._v931_match_essentials(item).get("complete") for item in valid_today),
        "home_renders_consistent": consistency_response.status_code == 200,
        "no_external_provider_calls": external_calls["count"] == 0 and home_summary.get("no_render_api_call") is True,
        "no_jinja_undefined": not any(item["jinja_undefined"] for item in results),
        "no_database_locked_response": not any(item["database_locked"] for item in results) and all(item["status"] == 200 for item in locked_results),
        "locked_routes_bounded": lock_elapsed < 12.0,
        "safe_500_template": (
            (ROOT / "templates" / "500.html").exists()
            and "render_template(" in source
            and '"500.html"' in source
            and 'data-v931-template="safe_500"' in (ROOT / "templates" / "500.html").read_text(encoding="utf-8")
        ),
        "api_500_safe_json": '"error_type": type(root_error).__name__' in source and '"safe_message": "Se ha producido un error controlado.' in source,
        "sentinel_issue_deduplicated": "issue_key = hashlib.sha256" in source and 'item.get("id") == issue_key' in source,
        "v929_navigation_preserved": "v929_clients_legacy_alias" in source and (ROOT / "engines" / "navigation_integrity_engine.py").exists(),
        "v930_visual_preserved": (ROOT / "static" / "v930-canonical.css").exists() and (ROOT / "templates" / "components" / "v930_ui.html").exists(),
        "no_secrets": not any(token in source for token in ("sk_live_", "xoxb-", "ghp_")),
    }
    failed_checks = [name for name, ok in checks.items() if not ok]
    payload = {
        "version": current_version,
        "ok": not failed_checks,
        "checks": checks,
        "failed_checks": failed_checks,
        "routes_tested": len(results),
        "route_failures": failures,
        "profiles": sorted({item["profile"] for item in results}),
        "home_consistency": {
            "valid_today_count": home_summary.get("valid_matches_today_count"),
            "visible_list_count": len(valid_today),
            "incomplete_count": len(incomplete),
            "provider_status": home_summary.get("provider_status"),
        },
        "locked_elapsed_seconds": lock_elapsed,
        "external_provider_calls": external_calls["count"],
        "dangerous_actions_executed": False,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
