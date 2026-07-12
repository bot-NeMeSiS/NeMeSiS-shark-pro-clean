from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL"
SUCCESSOR = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
SUPPORTED_VERSIONS = {VERSION, SUCCESSOR}
MADRID = ZoneInfo("Europe/Madrid")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def add(checks: list[dict], name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:240]})


def _session(client, role: str) -> None:
    admin = role == "ADMIN"
    with client.session_transaction() as session:
        session.update({
            "user_id": f"v934-{role.lower()}-check",
            "user_name": "Admin QA" if admin else "Cliente QA",
            "username": "admin_qa" if admin else "client_qa",
            "user_role": role,
            "membership": "ADMIN" if admin else "PRO",
            "user_membership": "ADMIN" if admin else "PRO",
        })


def _load_app(temp_dir: str):
    os.environ["DB_PATH"] = str(Path(temp_dir) / "v934.sqlite")
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["STRIPE_SECRET_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    if "app" in sys.modules:
        return importlib.reload(sys.modules["app"])
    return importlib.import_module("app")


def _app_checks(checks: list[dict], suite: str) -> None:
    with tempfile.TemporaryDirectory(prefix="nemesis_v934_", ignore_cleanup_errors=True) as temp_dir:
        try:
            app_module = _load_app(temp_dir)
            app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
            public = app_module.app.test_client()
            client = app_module.app.test_client()
            admin = app_module.app.test_client()
            _session(client, "PRO")
            _session(admin, "ADMIN")

            if suite in {"reference", "authenticated", "admin", "real_data", "performance"}:
                runtime_response = public.get("/api/runtime-version")
                runtime = runtime_response.get_json(silent=True) or {}
                add(checks, "runtime_200", runtime_response.status_code == 200, runtime_response.status_code)
                add(checks, "runtime_version", runtime.get("version") in SUPPORTED_VERSIONS, runtime.get("version"))
                add(checks, "runtime_files_match", runtime.get("version_files_match") is True)
                add(checks, "runtime_cache_busting", runtime.get("static_css_cache_busting") is True)
                add(checks, "runtime_service_worker", runtime.get("service_worker_cache_name") == f"NEMESIS_CACHE_{str(runtime.get('version') or VERSION).split('_', 1)[0]}")
                required_flags = [
                    "has_v934_reference_exactness", "has_v934_realtime_matches", "has_v934_realtime_live",
                    "has_v934_odds_freshness", "has_v934_admin_realtime_center",
                    "has_v934_component_consolidation", "has_v934_real_data_guard",
                ]
                add(checks, "runtime_flags", all(runtime.get(key) is True for key in required_flags), ",".join(key for key in required_flags if runtime.get(key) is not True))
                add(checks, "pixel_claim_blocked", runtime.get("v934_pixel_perfect_claim_allowed") is False)

            if suite in {"reference", "authenticated"}:
                public_routes = ["/", "/cliente-login", "/registro", "/calendar", "/live", "/picks", "/track-record"]
                client_routes = ["/app", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/profile", "/memberships"]
                admin_routes = ["/admin/dashboard", "/admin/realtime-center", "/admin/users", "/admin/payments", "/admin/picks", "/admin/data-center", "/admin/automation-workforce", "/admin/autonomous-company-sentinel"]
                public_status = {route: public.get(route, follow_redirects=False).status_code for route in public_routes}
                client_status = {route: client.get(route, follow_redirects=False).status_code for route in client_routes}
                admin_status = {route: admin.get(route, follow_redirects=False).status_code for route in admin_routes}
                add(checks, "public_routes_200", all(value == 200 for value in public_status.values()), public_status)
                add(checks, "client_routes_200", all(value == 200 for value in client_status.values()), client_status)
                add(checks, "admin_routes_200", all(value == 200 for value in admin_status.values()), admin_status)
                add(checks, "admin_realtime_api_protected", public.get("/api/admin/realtime-center/status").status_code == 403)

            if suite in {"reference", "matches", "live", "odds", "real_data", "performance"}:
                started = time.perf_counter()
                response = public.get("/api/realtime/sports")
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                payload = response.get_json(silent=True) or {}
                add(checks, "realtime_api_200", response.status_code == 200, response.status_code)
                add(checks, "realtime_api_safe", payload.get("ok") is True and payload.get("no_external_calls") is True)
                add(checks, "realtime_api_budget", elapsed_ms < 1500, f"{elapsed_ms}ms")
                add(checks, "realtime_poll_budget", 30 <= int(payload.get("poll_after_seconds") or 0) <= 300, payload.get("poll_after_seconds"))

            if suite == "admin":
                page = admin.get("/admin/realtime-center")
                add(checks, "admin_center_200", page.status_code == 200, page.status_code)
                add(checks, "admin_center_visible", b"data-v934-template" in page.data and b"data-v934-admin-action" in page.data)
                add(checks, "admin_center_no_secret_values", b"RENDER_API_KEY=" not in page.data and b"TELEGRAM_BOT_TOKEN=" not in page.data)
        except Exception as exc:
            add(checks, "app_check_exception", False, f"{type(exc).__name__}: {exc}")


def _engine_checks(checks: list[dict], suite: str) -> None:
    from engines.v934_realtime_sports_engine import (
        apply_test_transition,
        build_realtime_snapshot,
        cached_realtime_snapshot,
        invalidate_realtime_cache,
        normalize_match,
        normalize_pick,
        odds_freshness,
    )

    now = datetime.now(MADRID).replace(microsecond=0)
    base_match = {
        "id": "test-transition-only", "home_team": "Local QA", "away_team": "Visitante QA",
        "competition_name": "Liga QA", "match_date": now.date().isoformat(), "kickoff_time": "21:00",
        "source": "isolated_test", "updated_at": now.isoformat(), "status": "NS",
    }
    if suite in {"matches", "live", "real_data"}:
        scheduled = normalize_match(base_match, now)
        live = normalize_match(apply_test_transition(base_match, "live", minute=17, home_score=1, away_score=0), now)
        halftime = normalize_match(apply_test_transition(base_match, "halftime", minute=45, home_score=1, away_score=1), now)
        finished = normalize_match(apply_test_transition(base_match, "finished", home_score=2, away_score=1), now)
        add(checks, "scheduled_transition", bool(scheduled and scheduled["status"] == "scheduled"))
        add(checks, "live_transition", bool(live and live["is_live"] and live["minute"] == 17 and live["home_score"] == 1))
        add(checks, "halftime_transition", bool(halftime and halftime["status"] == "halftime"))
        add(checks, "finished_transition", bool(finished and finished["is_finished"] and finished["away_score"] == 1))
        invalid = normalize_match({"id": "incomplete", "home_team": "Only one field"}, now)
        add(checks, "incomplete_match_rejected", invalid is None)

    if suite in {"odds", "real_data"}:
        fresh = odds_freshness((now - timedelta(minutes=2)).isoformat(), now)
        recorded = odds_freshness((now - timedelta(minutes=30)).isoformat(), now)
        stale = odds_freshness((now - timedelta(hours=2)).isoformat(), now)
        add(checks, "odds_fresh", fresh["status"] == "fresh")
        add(checks, "odds_recorded", recorded["status"] == "recorded")
        add(checks, "odds_stale", stale["status"] == "stale")
        good_pick = normalize_pick({
            "id": "pick-test-only", "match_id": "test-transition-only", "home_team": "Local QA",
            "away_team": "Visitante QA", "market": "Mercado QA", "selection": "Selección QA",
            "odds": 1.75, "updated_at": now.isoformat(), "status": "published",
        }, now)
        bad_pick = normalize_pick({"id": "bad", "odds": 0}, now)
        add(checks, "complete_pick_accepted_in_test", bool(good_pick and good_pick["odds"] == 1.75))
        add(checks, "incomplete_pick_rejected", bad_pick is None)

    if suite in {"live", "performance"}:
        invalidate_realtime_cache("v934-test")
        first, state = cached_realtime_snapshot("v934-test", lambda: build_realtime_snapshot({"valid_matches_today": [base_match]}), force=True)
        fallback, fallback_state = cached_realtime_snapshot("v934-test", lambda: (_ for _ in ()).throw(TimeoutError("test timeout")), force=True)
        add(checks, "cache_initial_snapshot", state == "refreshed" and first["counts"]["matches"] == 1)
        add(checks, "cache_stale_fallback", fallback_state == "stale_fallback" and fallback.get("cache_status") == "stale_fallback")
        invalidate_realtime_cache("v934-test")


def _static_checks(checks: list[dict], suite: str) -> None:
    app = read("app.py")
    base = read("templates/base.html")
    ui = read("templates/components/v933_ui.html")
    nav = read("templates/components/v933_navigation.html")
    css = read("static/v933-product.css")
    js = read("static/v934-realtime.js")
    engine = read("engines/v934_realtime_sports_engine.py")
    version = read("VERSION.txt").strip()

    if suite in {"reference", "component", "accessibility", "performance", "real_data"}:
        add(checks, "version_exact", version in SUPPORTED_VERSIONS, version)
        add(checks, "version_without_bom", not (ROOT / "VERSION.txt").read_bytes().startswith(b"\xef\xbb\xbf"))
        add(checks, "app_version_exact", f"APP_VERSION = '{version}'" in app)
        add(checks, "service_worker_v934", f"NEMESIS_CACHE_{version.split('_', 1)[0]}" in app and "cache:'no-store'" in app and "cache:'reload'" in app)
        add(checks, "v929_navigation_preserved", "V929 navigation integrity route recovery" in base)
        add(checks, "v930_visual_preserved", "v930-client-desktop-shell" in base and "v930-admin-shell" in base)
        add(checks, "v931_sqlite_preserved", "_v931_read_table_rows" in app)
        add(checks, "v932_auth_preserved", "v932_safe_dashboard_data" in app)

    if suite == "component":
        add(checks, "shared_realtime_component", "macro realtime_state_bar" in ui)
        add(checks, "single_component_source", "v934-realtime-state" in ui and "v934-realtime-state" in css)
        add(checks, "admin_navigation_link", "/admin/realtime-center" in nav)
        add(checks, "templates_use_component", all("realtime_state_bar" in read(path) for path in ["templates/home.html", "templates/calendar.html", "templates/live.html", "templates/picks.html", "templates/client_app_center.html"]))

    if suite == "performance":
        detail_segment = app[app.find("def match_detail_page"):app.find("def get_safe_calendar_context")]
        add(checks, "no_provider_call_in_detail_render", "sync_api_sports_fixture_detail(" not in detail_segment)
        polling_fetches = js.count("fetch(endpoint + '?scope='")
        add(checks, "client_polling_shared", polling_fetches == 1, polling_fetches)
        add(checks, "polling_backoff", "Math.pow(2" in js and "document.hidden" in js)
        add(checks, "js_budget", len(js.encode("utf-8")) < 30000, len(js.encode("utf-8")))
        add(checks, "css_budget", len(css.encode("utf-8")) < 100000, len(css.encode("utf-8")))

    if suite == "accessibility":
        add(checks, "focus_visible", "focus-visible" in read("static/v933_design_tokens.css"))
        add(checks, "reduced_motion", "prefers-reduced-motion" in css)
        add(checks, "touch_targets", "min-height: 44px" in css)
        add(checks, "nav_labels", 'aria-label="Navegación' in nav or 'aria-label="Navegaci' in nav)
        add(checks, "live_region", 'aria-live="polite"' in read("templates/admin_realtime_center.html"))

    if suite == "real_data":
        forbidden_examples = ["Real Madrid vs Dortmund", "18.74%", "125.684", "48.732"]
        v934_scope = engine + js + read("templates/admin_realtime_center.html")
        add(checks, "no_reference_numbers_copied", not any(value in v934_scope for value in forbidden_examples))
        add(checks, "required_match_fields", "all((match_id, home, away, competition, match_date, kickoff, source))" in engine)
        add(checks, "required_pick_fields", "odds <= 1.0" in engine and "market" in engine and "selection" in engine)
        add(checks, "no_external_provider_calls", "requests." not in engine and "urlopen" not in engine)


def run_suite(suite: str) -> int:
    checks: list[dict] = []
    _static_checks(checks, suite)
    _engine_checks(checks, suite)
    _app_checks(checks, suite)
    failed = [item for item in checks if not item["ok"]]
    payload = {"version": read("VERSION.txt").strip() or VERSION, "suite": suite, "ok": not failed, "checks": checks, "failed": failed}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failed else 1
