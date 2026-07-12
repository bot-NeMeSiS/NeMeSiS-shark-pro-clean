"""Focused validation suites for the V935 launch-trust release."""
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
BASE_VERSION = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
CURRENT_VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
VERSION = CURRENT_VERSION if CURRENT_VERSION.startswith("V936_") else BASE_VERSION
MADRID = ZoneInfo("Europe/Madrid")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def add(checks: list[dict], name: str, ok: bool, detail: object = "") -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:420]})


def _session(client, role: str) -> None:
    admin = role == "ADMIN"
    with client.session_transaction() as session:
        session.update({
            "user_id": f"v935-{role.lower()}-fixture",
            "user_name": "Admin QA" if admin else "Cliente QA",
            "username": "admin_qa" if admin else "client_qa",
            "user_role": role,
            "membership": "ADMIN" if admin else "PRO",
            "user_membership": "ADMIN" if admin else "PRO",
        })


def _load_app(temp_dir: str):
    os.environ["DB_PATH"] = str(Path(temp_dir) / "v935-check.sqlite")
    os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["STRIPE_SECRET_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    if "app" in sys.modules:
        return importlib.reload(sys.modules["app"])
    return importlib.import_module("app")


def _base_match(now: datetime, *, future: bool = True) -> dict:
    kickoff = now + timedelta(hours=3) if future else now - timedelta(hours=3)
    return {
        "id": "m-v935-test", "home_team": "Home QA", "away_team": "Away QA",
        "competition_name": "Competition QA", "match_date": kickoff.date().isoformat(),
        "kickoff_time": kickoff.strftime("%H:%M"), "source": "isolated_test_fixture",
        "updated_at": now.isoformat(), "status": "NS",
    }


def _engine_checks(checks: list[dict], suite: str) -> None:
    from engines.v935_launch_trust_engine import (
        MATCH_LIFECYCLES,
        ODDS_STATES,
        PICK_LIFECYCLES,
        build_data_trust_snapshot,
        classify_match_for_surface,
        enrich_pick_lifecycle,
        get_odds_freshness,
        is_match_complete,
        is_pick_evaluable,
        is_pick_publishable,
        normalize_match_lifecycle,
        normalize_pick_lifecycle,
    )

    now = datetime.now(MADRID).replace(microsecond=0)
    if suite in {"match_lifecycle", "data_trust", "launch_readiness"}:
        future = _base_match(now)
        live = {**future, "status": "LIVE", "minute": 18}
        halftime = {**future, "status": "HT", "minute": 45}
        finished = {**_base_match(now, future=False), "status": "FT", "home_score": 2, "away_score": 1}
        pending = {**_base_match(now, future=False), "status": "FT"}
        postponed = {**future, "status": "POSTPONED"}
        cancelled = {**future, "status": "CANCELLED"}
        abandoned = {**future, "status": "ABANDONED"}
        archived = {**finished, "status": "ARCHIVED"}
        incomplete = {"id": "incomplete", "home_team": "Only home"}
        states = [normalize_match_lifecycle(item, now) for item in (future, live, halftime, finished, pending, postponed, cancelled, abandoned, incomplete, archived)]
        add(checks, "all_match_states_supported", set(states) == set(MATCH_LIFECYCLES), states)
        add(checks, "past_outside_upcoming", not classify_match_for_surface(finished, now)["calendar"])
        add(checks, "finished_outside_live", not classify_match_for_surface(finished, now)["live"])
        add(checks, "incidents_separated", all(classify_match_for_surface(item, now)["incidents"] for item in (pending, postponed, cancelled, abandoned, incomplete)))
        add(checks, "incomplete_not_public", not is_match_complete(incomplete))

    if suite in {"pick_lifecycle", "historical_integrity", "data_trust", "launch_readiness"}:
        match = _base_match(now)
        base_pick = {
            **match, "id": "p-v935-test", "match_id": match["id"], "market": "Market QA",
            "selection": "Selection QA", "odds": 1.82, "odds_source": "isolated_test_fixture",
            "odds_updated_at": now.isoformat(), "status": "published", "stake": 1.0,
        }
        lifecycle_fixtures = [
            {**base_pick, "status": "draft"}, {**base_pick, "market": ""},
            {**base_pick, "status": "review"}, {**base_pick, "status": "approved"},
            base_pick, {**base_pick, "match_status": "LIVE"},
            {**base_pick, "result_status": "won"}, {**base_pick, "result_status": "lost"},
            {**base_pick, "result_status": "void"}, {**base_pick, "status": "cancelled"},
            {**base_pick, "match_status": "FT", "home_score": 1, "away_score": 0},
            {**base_pick, "status": "archived"},
        ]
        states = [normalize_pick_lifecycle(item, now) for item in lifecycle_fixtures]
        add(checks, "all_pick_states_supported", set(states) == set(PICK_LIFECYCLES), states)
        add(checks, "complete_pick_publishable", is_pick_publishable(base_pick, now))
        add(checks, "incomplete_pick_blocked", not is_pick_publishable({**base_pick, "selection": ""}, now))
        add(checks, "zero_odds_not_evaluable", not is_pick_evaluable({**base_pick, "result_status": "won", "odds": 0}, now))
        add(checks, "closed_complete_pick_evaluable", is_pick_evaluable({**base_pick, "result_status": "won"}, now))
        enriched = enrich_pick_lifecycle(base_pick, now)
        add(checks, "pick_ledger_fields", all(key in enriched for key in ("v935_lifecycle", "v935_match_lifecycle", "v935_odds", "v935_quality", "v935_publishable", "v935_evaluable")))

    if suite in {"odds_freshness", "historical_integrity", "data_trust", "launch_readiness"}:
        states = [
            get_odds_freshness((now - timedelta(minutes=2)).isoformat(), now, odds=1.8, source="test"),
            get_odds_freshness((now - timedelta(minutes=30)).isoformat(), now, odds=1.8, source="test"),
            get_odds_freshness((now - timedelta(minutes=90)).isoformat(), now, odds=1.8, source="test"),
            get_odds_freshness(now.isoformat(), now, odds=1.8, source="test", match_lifecycle="FINISHED"),
            get_odds_freshness(now.isoformat(), now, odds=0, source=""),
        ]
        add(checks, "all_odds_states_supported", [item["status"] for item in states] == list(ODDS_STATES), [item["status"] for item in states])
        add(checks, "stale_not_publishable", states[2]["is_publishable"] is False)
        add(checks, "invalid_not_usable", states[4]["is_usable"] is False)

    if suite in {"data_trust", "launch_readiness"}:
        trust = build_data_trust_snapshot([_base_match(now)], [], provider_status="test", last_sync=now.isoformat(), now=now)
        add(checks, "data_trust_counts", trust["match_counts"]["UPCOMING"] == 1)
        add(checks, "data_trust_no_secret_fields", not any("token" in key.lower() or "secret" in key.lower() for key in trust))


def _static_checks(checks: list[dict], suite: str) -> None:
    app = read("app.py")
    version = read("VERSION.txt").strip()
    base = read("templates/base.html")
    ui = read("templates/components/v933_ui.html")
    nav = read("templates/components/v933_navigation.html")
    css = read("static/v933-product.css")
    tokens = read("static/v933_design_tokens.css")
    js = read("static/v934-realtime.js")
    engine = read("engines/v935_launch_trust_engine.py")
    data_trust_template = read("templates/admin_data_trust_center.html")

    add(checks, "version_exact", version == VERSION, version)
    add(checks, "version_without_bom", not (ROOT / "VERSION.txt").read_bytes().startswith(b"\xef\xbb\xbf"))
    add(checks, "app_version_exact", f"APP_VERSION = '{VERSION}'" in app)
    add(checks, "v929_navigation_preserved", "V929 navigation integrity route recovery" in base)
    add(checks, "v930_visual_preserved", "v930-client-desktop-shell" in base and "v930-admin-shell" in base)
    add(checks, "v931_sqlite_preserved", "_v931_read_table_rows" in app)
    add(checks, "v932_auth_preserved", "v932_safe_dashboard_data" in app)
    add(checks, "v934_realtime_preserved", "get_v934_realtime_context" in app and "v934-realtime.js" in base)

    if suite == "route_performance":
        add(checks, "request_local_summary_cache", "v935_public_sports_summary" in app)
        add(checks, "server_timing", "Server-Timing" in app and "X-Nemesis-Route-Budget" in app)
        add(checks, "read_only_track_record", "mode=ro" in read("engines/pick_grading_engine.py") and "query_only=ON" in read("engines/pick_grading_engine.py"))
    elif suite == "realtime_cache":
        add(checks, "etag_enabled", "set_etag" in app and "If-None-Match" in js)
        add(checks, "last_modified_enabled", "last_modified" in app and "If-Modified-Since" in js)
        add(checks, "shared_update", "__nemesisV935Realtime" in js and "entry.pending" in js)
        add(checks, "jitter_and_backoff", "jitteredPoll" in js and "Math.pow(2" in js)
        add(checks, "no_provider_in_v935_engine", "urlopen" not in engine and "requests." not in engine)
    elif suite == "data_trust_center":
        add(checks, "data_trust_template", bool(data_trust_template) and "data-v935-template" in data_trust_template)
        add(checks, "data_trust_admin_nav", "/admin/data-trust-center" in nav)
        add(checks, "data_trust_apis", all(path in app for path in ("/api/admin/data-trust/summary", "/api/admin/data-trust/issues", "/api/admin/data-trust/run-safe-validation", "/api/admin/data-trust/refresh-cache")))
    elif suite == "historical_integrity":
        grading = read("engines/pick_grading_engine.py")
        compact_grading = grading.replace(" ", "").lower()
        add(checks, "roi_evaluable_filter", "('won','lost','void')" in compact_grading and "coalesce(odds,0)>1" in compact_grading and "coalesce(stake,0)>0" in compact_grading)
        add(checks, "non_evaluable_exposed", "non_evaluable" in app and "evaluable_total" in app)
    elif suite == "customer_trust":
        add(checks, "customer_trust_component", "macro customer_trust_panel" in ui and "v935-customer-trust" in css)
        add(checks, "provenance_badge", "macro data_provenance_badge" in ui and "v935-provenance" in css)
        add(checks, "no_publish_explanation", "No publicar" in read("templates/shark.html"))
        add(checks, "technical_details_hidden", "technical_details_hidden" in app)
    elif suite == "visual_consistency":
        add(checks, "separate_shells", "v933-client-shell" in base and "v933-admin-shell" in base)
        add(checks, "mobile_nav_preserved", "v933-mobile-bottom-nav" in nav)
        add(checks, "data_trust_command_center", "v933-admin-command-center" in data_trust_template)
        add(checks, "semantic_actions", "is-primary is-blue" in ui and "is-cyan" in css and "is-gold" in css)
    elif suite == "performance_budget":
        add(checks, "css_budget", len(css.encode("utf-8")) < 150000, len(css.encode("utf-8")))
        add(checks, "realtime_js_budget", len(js.encode("utf-8")) < 30000, len(js.encode("utf-8")))
        add(checks, "lazy_logos", 'loading="lazy"' in ui)
        add(checks, "no_mandatory_provider_render", "request_local_summary_cache_no_provider_calls" in app)
    elif suite == "accessibility":
        add(checks, "focus_visible", "focus-visible" in tokens + css)
        add(checks, "reduced_motion", "prefers-reduced-motion" in tokens + css)
        add(checks, "touch_targets", "min-height: 44px" in tokens + css)
        add(checks, "navigation_aria", "aria-label=" in nav)
        add(checks, "data_trust_live_region", 'aria-live="polite"' in data_trust_template)
    elif suite == "launch_readiness":
        required = [
            "engines/v935_launch_trust_engine.py", "templates/admin_data_trust_center.html",
            "automation_workforce/v935_launch_orchestrator.py", "reports/V935_CHECKPOINT_STATUS.json",
        ]
        add(checks, "required_artifacts", all((ROOT / item).exists() for item in required), [item for item in required if not (ROOT / item).exists()])
        required_flags = [
            "has_v935_route_performance", "has_v935_match_lifecycle", "has_v935_pick_lifecycle",
            "has_v935_odds_freshness", "has_v935_realtime_cache", "has_v935_data_trust_center",
            "has_v935_historical_integrity", "has_v935_customer_trust", "has_v935_launch_readiness",
            "has_v935_company_orchestrator",
        ]
        add(checks, "runtime_flags_static", all(flag in app for flag in required_flags), [flag for flag in required_flags if flag not in app])


def _app_checks(checks: list[dict], suite: str) -> None:
    if suite not in {"route_performance", "realtime_cache", "data_trust_center", "customer_trust", "visual_consistency", "launch_readiness"}:
        return
    with tempfile.TemporaryDirectory(prefix="nemesis_v935_", ignore_cleanup_errors=True) as temp_dir:
        try:
            module = _load_app(temp_dir)
            module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
            public = module.app.test_client()
            client = module.app.test_client()
            admin = module.app.test_client()
            _session(client, "PRO")
            _session(admin, "ADMIN")
            if suite == "route_performance":
                route_groups = {
                    "public": (public, ["/", "/calendar", "/live", "/picks", "/track-record", "/api/runtime-version"]),
                    "client": (client, ["/app", "/calendar", "/live", "/picks", "/track-record", "/shark", "/telegram", "/profile", "/memberships"]),
                    "admin": (admin, ["/admin/dashboard", "/admin/data-center", "/admin/realtime-center", "/admin/data-trust-center"]),
                }
                timings: dict[str, float] = {}
                statuses: dict[str, int] = {}
                for _, (test_client, routes) in route_groups.items():
                    for route in routes:
                        started = time.perf_counter()
                        response = test_client.get(route, follow_redirects=False)
                        timings[route] = round((time.perf_counter() - started) * 1000, 2)
                        statuses[route] = response.status_code
                add(checks, "route_statuses", all(value in {200, 302, 303} for value in statuses.values()), statuses)
                add(checks, "route_budget", all(value < (1200 if route in {"/calendar", "/live", "/picks", "/track-record"} else 1800) for route, value in timings.items()), timings)
                add(checks, "route_timing_header", bool(public.get("/").headers.get("Server-Timing")))
                db_path = Path(os.environ["DB_PATH"])
                lock = sqlite3.connect(db_path, timeout=0.1)
                try:
                    lock.execute("BEGIN EXCLUSIVE")
                    started = time.perf_counter()
                    degraded = public.get("/calendar")
                    locked_ms = round((time.perf_counter() - started) * 1000, 2)
                finally:
                    lock.rollback()
                    lock.close()
                add(checks, "locked_db_safe", degraded.status_code == 200 and locked_ms < 2500, f"{degraded.status_code}, {locked_ms}ms")
            elif suite == "realtime_cache":
                first = public.get("/api/realtime/sports")
                etag = first.headers.get("ETag")
                second = public.get("/api/realtime/sports", headers={"If-None-Match": etag or ""})
                payload = first.get_json(silent=True) or {}
                add(checks, "realtime_200", first.status_code == 200 and payload.get("no_external_calls") is True)
                add(checks, "realtime_conditional_304", bool(etag) and second.status_code == 304, second.status_code)
                add(checks, "realtime_cache_control", "max-age=15" in str(first.headers.get("Cache-Control") or ""))
            elif suite == "data_trust_center":
                add(checks, "data_trust_page_protected", public.get("/admin/data-trust-center").status_code in {302, 303})
                add(checks, "data_trust_api_protected", public.get("/api/admin/data-trust/summary").status_code == 403)
                admin_page = admin.get("/admin/data-trust-center")
                add(checks, "data_trust_page_admin", admin_page.status_code == 200)
                import re
                token_match = re.search(rb'<meta name="csrf-token" content="([^"]+)"', admin_page.data)
                csrf_token = token_match.group(1).decode("utf-8") if token_match else ""
                validation = admin.post("/api/admin/data-trust/run-safe-validation", json={}, headers={"X-CSRF-Token": csrf_token})
                add(checks, "data_trust_validation_admin", validation.status_code == 200, validation.status_code)
            elif suite == "customer_trust":
                pages = {route: client.get(route) for route in ("/app", "/picks", "/track-record", "/shark")}
                add(checks, "customer_trust_visible", all(b"v935-customer-trust" in response.data for response in pages.values()), {key: value.status_code for key, value in pages.items()})
                forbidden = (b"cache hit", b"provider exception", b"AUTOMATION_SECRET", b"DB_PATH")
                add(checks, "client_technical_details_hidden", all(not any(token in response.data for token in forbidden) for response in pages.values()))
            elif suite == "visual_consistency":
                add(checks, "client_shell", b"v933-client-shell" in client.get("/app").data)
                add(checks, "admin_shell", b"v933-admin-shell" in admin.get("/admin/data-trust-center").data)
            elif suite == "launch_readiness":
                runtime_response = public.get("/api/runtime-version")
                runtime = runtime_response.get_json(silent=True) or {}
                add(checks, "runtime_200", runtime_response.status_code == 200)
                add(checks, "runtime_version", runtime.get("version") == VERSION, runtime.get("version"))
                add(checks, "runtime_files_match", runtime.get("version_files_match") is True)
                add(checks, "runtime_cache_busting", runtime.get("static_css_cache_busting") is True)
                add(checks, "runtime_service_worker", runtime.get("service_worker_cache_name") == f"NEMESIS_CACHE_{VERSION.split('_', 1)[0]}")
        except Exception as exc:
            add(checks, "app_check_exception", False, f"{type(exc).__name__}: {exc}")


def run_suite(suite: str) -> int:
    checks: list[dict] = []
    _static_checks(checks, suite)
    _engine_checks(checks, suite)
    _app_checks(checks, suite)
    failed = [item for item in checks if not item["ok"]]
    payload = {"version": VERSION, "suite": suite, "ok": not failed, "checks": checks, "failed": failed}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failed else 1
