"""Safe click-through Browser QA for V929 navigation integrity.

The runner starts Flask with a temporary database, signs local mock sessions,
clicks visible internal navigation, and never submits forms or calls mutation APIs.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL"
OUTPUT_JSON = ROOT / "reports" / "V929_CLICK_NAVIGATION_MATRIX.json"
OUTPUT_DIR = ROOT / "reports" / "V929_browser_qa_navigation"

PUBLIC_ORIGINS = ["/", "/cliente-login", "/registro"]
CLIENT_ORIGINS = [
    "/app", "/calendar", "/live", "/picks", "/track-record",
    "/shark", "/telegram", "/profile", "/memberships", "/favorites",
]
MOBILE_ORIGINS = list(CLIENT_ORIGINS)
ADMIN_ORIGINS = [
    "/admin/dashboard", "/admin/matches", "/admin/realtime-center", "/admin/picks",
    "/admin/telegram/command-center", "/admin/users", "/admin/memberships",
    "/admin/payments", "/admin/shark-center", "/admin/data-center",
    "/admin/automation-center", "/admin/sentinel-issues", "/admin/highlights-center",
    "/admin/system", "/admin/final-release",
]

DANGEROUS_PARTS = (
    "/api/", "/logout", "/cerrar-sesion", "/checkout", "/stripe",
    "/payment", "/comprar", "/delete", "/remove", "/send", "/enqueue", "/trigger",
    "refresh=1", "force=1", "continuar_pago", "/sync",
)


def _now_madrid() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat()
    except Exception:
        return datetime.now().replace(microsecond=0).isoformat()



def _same_dynamic_navigation_target(expected: str, observed: str) -> bool:
    """Allow a link discovered before midnight to refresh only its date parameter."""
    left = urlsplit(str(expected or ""))
    right = urlsplit(str(observed or ""))
    if left.path != right.path or not left.path:
        return False
    left_query = dict(parse_qsl(left.query, keep_blank_values=True))
    right_query = dict(parse_qsl(right.query, keep_blank_values=True))
    if "date" not in left_query or "date" not in right_query:
        return False
    left_query.pop("date", None)
    right_query.pop("date", None)
    return left_query == right_query


def _dynamic_visible_link(page, expected_target: str, expected_text: str):
    links = page.locator("a[href]:visible")
    normalized_text = " ".join(str(expected_text or "").split())
    for index in range(min(links.count(), 100)):
        node = links.nth(index)
        href = node.get_attribute("href") or ""
        if not _same_dynamic_navigation_target(expected_target, href):
            continue
        text = " ".join((node.inner_text() or node.get_attribute("aria-label") or "").split())
        if normalized_text and text != normalized_text:
            continue
        return node
    return None


def _safe_internal_target(value: str) -> bool:
    target = str(value or "").strip()
    path = urlsplit(target).path
    if not target.startswith("/") or target.startswith("//") or not path:
        return False
    lowered = target.lower()
    return not any(part in lowered for part in DANGEROUS_PARTS)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _prepare_local_app():
    db_path = Path(tempfile.gettempdir()) / "nemesis_v929_click_navigation.db"
    os.environ["DB_PATH"] = str(db_path)
    os.environ["SECRET_KEY"] = "v929-local-click-qa-only"
    os.environ["DISABLE_BROWSER_QA"] = "1"
    os.environ["ENABLE_AUTOMATED_RENDER_DEPLOY"] = "0"
    os.environ.pop("AUTOMATION_SECRET", None)
    for key in (
        "TELEGRAM_BOT_TOKEN", "STRIPE_SECRET_KEY", "STRIPE_SECRET",
        "OPENAI_API_KEY", "API_SPORTS_KEY", "API_FOOTBALL_KEY",
        "THE_ODDS_API_KEY", "ODDS_API_KEY", "THESPORTSDB_API_KEY",
    ):
        os.environ[key] = ""
    import app as app_module

    app_module.app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
    return app_module


def _signed_sessions(flask_app) -> dict[str, str]:
    serializer = flask_app.session_interface.get_signing_serializer(flask_app)
    sessions = {
        "cookie_name": flask_app.config.get("SESSION_COOKIE_NAME", "session"),
        "client": serializer.dumps({
            "user_id": "v929-click-client",
            "user_name": "Cliente QA",
            "username": "cliente_qa",
            "user_email": "qa-client@example.invalid",
            "user_role": "PRO",
            "membership": "PRO",
            "user_membership": "PRO",
        }),
        "admin": serializer.dumps({
            "user_id": "v929-click-admin",
            "user_name": "Admin QA",
            "username": "admin_qa",
            "user_email": "qa-admin@example.invalid",
            "user_role": "ADMIN",
            "membership": "ADMIN",
            "user_membership": "ADMIN",
        }),
    }
    for plan in ("FREE", "PRO", "ELITE"):
        sessions["client_" + plan.lower()] = serializer.dumps({
            "user_id": "v941-click-" + plan.lower(), "user_name": "Cliente QA",
            "user_role": plan, "membership": plan, "user_membership": plan,
        })
    return sessions


def _visible_internal_actions(page) -> list[dict]:
    actions = page.locator("a[href]:visible, button[data-q]:visible")
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for index in range(min(actions.count(), 80)):
        node = actions.nth(index)
        tag = node.evaluate("el => el.tagName.toLowerCase()")
        target = node.get_attribute("href") if tag == "a" else node.get_attribute("data-q")
        if not _safe_internal_target(target or ""):
            continue
        if (node.get_attribute("target") or "").lower() == "_blank":
            continue
        text = " ".join((node.inner_text() or node.get_attribute("aria-label") or "").split())[:180]
        key = (str(target), text)
        if key in seen:
            continue
        seen.add(key)
        found.append({"tag": tag, "target": str(target), "text": text or "Accion interna"})
    return found


def _click_one(page, base_url: str, origin: str, action: dict, timeout: int, profile: str) -> dict:
    item = {
        "profile": profile,
        "origin": origin,
        "visible_text": action.get("text") or "Accion interna",
        "target": action.get("target") or "",
        "selector": "a[href]" if action.get("tag") == "a" else "button[data-q]",
        "status": 0,
        "result": "BROKEN",
        "final_path": "",
        "screenshot": "",
        "retry_count": 0,
    }
    response = page.goto(base_url + origin, wait_until="domcontentloaded", timeout=timeout)
    if response and response.status >= 500:
        item.update(status=response.status, result="ORIGIN_500", final_path=urlsplit(page.url).path)
        return item

    target = item["target"]
    for attempt in range(2):
        if attempt:
            item["retry_count"] = attempt
            try:
                response = page.goto(base_url + origin, wait_until="domcontentloaded", timeout=timeout)
                if response and response.status >= 500:
                    item.update(status=response.status, result="ORIGIN_500", final_path=urlsplit(page.url).path)
                    return item
            except Exception as exc:
                item.update(result="CLICK_ERROR", error=f"{exc.__class__.__name__}: {str(exc)[:240]}")
                return item

        if action.get("tag") == "a":
            locator = page.locator(f'a[href="{target}"]:visible').first
            if locator.count() == 0:
                dynamic_locator = _dynamic_visible_link(page, target, action.get("text") or "")
                if dynamic_locator is not None:
                    locator = dynamic_locator
                    refreshed_target = locator.get_attribute("href") or target
                    item["target_refreshed_after_date_rollover"] = refreshed_target != target
                    target = refreshed_target
        else:
            locator = page.locator(f'button[data-q="{target}"]:visible').first
        if locator.count() == 0:
            item["result"] = "SELECTOR_NOT_VISIBLE"
            return item

        try:
            if locator.get_attribute("data-open-explore") is not None:
                # Progressive navigation opens a finder first. Verify that
                # interaction, then follow a real, safe destination from it.
                origin_url = page.url
                locator.click(timeout=timeout)
                dialog = page.locator("#app-navigation-dialog")
                dialog.wait_for(state="visible", timeout=timeout)
                if page.url != origin_url:
                    raise AssertionError("Section finder unexpectedly changed the current page")
                search = dialog.locator("[data-explore-query]")
                if not search.evaluate("el => el === document.activeElement"):
                    raise AssertionError("Section finder did not focus its search field")
                choices = dialog.locator("[data-explore-item]:visible")
                destination = None
                for index in range(choices.count()):
                    choice = choices.nth(index)
                    href = choice.get_attribute("href") or ""
                    if _safe_internal_target(href) and urlsplit(href).path != urlsplit(page.url).path:
                        destination = choice
                        item["selected_navigation_target"] = href
                        break
                if destination is None:
                    raise AssertionError("Section finder has no safe destination to verify")
                item["interaction"] = "navigation_dialog"
                locator = destination
            with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout) as nav:
                locator.click(timeout=timeout)
            click_response = nav.value
            page.wait_for_timeout(150)
            status = int(click_response.status) if click_response else 200
            final_path = urlsplit(page.url).path or "/"
            body = page.locator("body").inner_text(timeout=3000)[:4000]
            route_not_found = "Ruta no encontrada" in body
            server_error = "Error interno" in body or "Internal Server Error" in body
            result = "OK"
            if status >= 500 or server_error:
                result = "ROTA_500"
            elif status == 404 or route_not_found:
                result = "ROTA_404"
            item.update(status=status, result=result, final_path=final_path)
            return item
        except Exception as exc:
            if attempt == 0 and exc.__class__.__name__ == "TimeoutError":
                continue
            item.update(result="CLICK_ERROR", error=f"{exc.__class__.__name__}: {str(exc)[:240]}")
            return item
    return item


def _run_profile(browser, base_url: str, sessions: dict, profile: str, viewport: dict, origins: list[str], timeout: int) -> list[dict]:
    context = browser.new_context(viewport=viewport, service_workers="block", locale="es-ES", timezone_id="Europe/Madrid")
    if profile.startswith(("client_", "admin_")):
        role = "admin" if profile.startswith("admin_") else "_".join(profile.split("_")[:2])
        if role not in sessions:
            role = "client"
        context.add_cookies([{
            "name": sessions["cookie_name"],
            "value": sessions[role],
            "url": base_url,
            "httpOnly": True,
        }])
    page = context.new_page()
    # No providers, remote logos, fonts or analytics in isolated browser QA.
    context.route("**/*", lambda route: route.continue_()
                  if urlsplit(route.request.url).netloc == urlsplit(base_url).netloc
                  else route.abort())
    results: list[dict] = []
    tested_targets: set[str] = set()
    console_errors: list[str] = []
    page_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text[:500]) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)[:500]))
    try:
        for origin in origins:
            console_before = len(console_errors)
            errors_before = len(page_errors)
            response = page.goto(base_url + origin, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(120)
            status = int(response.status) if response else 0
            final_path = urlsplit(page.url).path or "/"
            try:
                body = page.locator("body").inner_text(timeout=3000)[:4000]
            except Exception:
                body = ""
            try:
                layout = page.evaluate("""() => ({
                    overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
                    scrollWidth: document.documentElement.scrollWidth,
                    viewportWidth: window.innerWidth
                })""")
            except Exception:
                layout = {"overflow": False, "scrollWidth": 0, "viewportWidth": viewport.get("width", 0)}
            new_page_errors = page_errors[errors_before:]
            new_console_errors = [
                item for item in console_errors[console_before:]
                if "Failed to load resource" not in item and "favicon" not in item.lower()
            ]
            direct = {
                "profile": profile,
                "origin": origin,
                "visible_text": "Abrir pantalla",
                "target": origin,
                "selector": "direct_origin_check",
                "status": status,
                "result": "OK",
                "final_path": final_path,
                "screenshot": "",
                "overflow": bool(layout.get("overflow")),
                "scroll_width": int(layout.get("scrollWidth") or 0),
                "viewport_width": int(layout.get("viewportWidth") or viewport.get("width") or 0),
                "page_errors": list(new_page_errors),
                "console_errors": list(new_console_errors),
            }
            if not response or status >= 500 or "Error interno" in body or "Internal Server Error" in body:
                direct["result"] = "ORIGIN_500"
            elif status == 404 or "Ruta no encontrada" in body:
                direct["result"] = "ORIGIN_404"
            elif new_page_errors:
                direct["result"] = "JS_ERROR"
            elif new_console_errors:
                direct["result"] = "CONSOLE_ERROR"
            elif layout.get("overflow"):
                direct["result"] = "HORIZONTAL_OVERFLOW"
            if direct["result"] != "OK":
                failure_dir = OUTPUT_DIR / "failures"
                failure_dir.mkdir(parents=True, exist_ok=True)
                safe_name = f"{profile}__{origin.strip('/').replace('/', '_') or 'home'}__origin.png"
                shot = failure_dir / safe_name
                try:
                    page.screenshot(path=str(shot), full_page=True)
                    direct["screenshot"] = str(shot.relative_to(ROOT).as_posix())
                except Exception:
                    pass
            results.append(direct)
            if direct["result"] != "OK":
                continue
            if profile in {"client_free_desktop", "client_free_mobile", "admin_desktop", "admin_mobile"} and origin in {"/app", "/telegram", "/profile", "/admin/dashboard", "/admin/payments"}:
                capture_dir = OUTPUT_DIR / "verified"
                capture_dir.mkdir(parents=True, exist_ok=True)
                shot = capture_dir / f"{profile}__{origin.strip('/').replace('/', '_')}.png"
                page.screenshot(path=str(shot), full_page=True)
                direct["screenshot"] = shot.relative_to(ROOT).as_posix()

            actions = [
                action for action in _visible_internal_actions(page)
                if action.get("target") not in tested_targets
            ]
            for action in actions:
                tested_targets.add(str(action.get("target") or ""))
                item = _click_one(page, base_url, origin, action, timeout, profile)
                if item["result"] != "OK":
                    failure_dir = OUTPUT_DIR / "failures"
                    failure_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = f"{profile}__{origin.strip('/').replace('/', '_') or 'home'}__{len(results)+1}.png"
                    shot = failure_dir / safe_name
                    try:
                        page.screenshot(path=str(shot), full_page=True)
                        item["screenshot"] = str(shot.relative_to(ROOT).as_posix())
                    except Exception:
                        pass
                results.append(item)
    finally:
        context.close()
    return results


def _run_profile_isolated(base_url: str, sessions: dict, profile: str, viewport: dict, origins: list[str], timeout: int) -> list[dict]:
    """Run one browser profile with its own Playwright driver and Chromium process."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("NEMESIS_QA_CHROMIUM") or playwright.chromium.executable_path
        )
        try:
            return _run_profile(browser, base_url, sessions, profile, viewport, origins, timeout)
        finally:
            browser.close()


def run(timeout: int = 15000, workers: int = 3) -> dict:
    app_module = _prepare_local_app()
    from werkzeug.serving import make_server

    port = _free_port()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", port, app_module.app, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"
    sessions = _signed_sessions(app_module.app)
    results: list[dict] = []
    profiles = [
        ("public_desktop", {"width": 1440, "height": 900}, PUBLIC_ORIGINS),
        *[(f"client_{plan}_{device}", viewport, CLIENT_ORIGINS)
          for plan in ("free", "pro", "elite")
          for device, viewport in (("desktop", {"width":1440,"height":900}), ("mobile", {"width":390,"height":844}))],
        ("admin_desktop", {"width": 1440, "height": 900}, ADMIN_ORIGINS),
        ("admin_mobile", {"width": 390, "height": 844}, ADMIN_ORIGINS),
    ]
    parallel_profiles = [item for item in profiles if not item[0].startswith("admin_")]
    serial_profiles = [item for item in profiles if item[0].startswith("admin_")]
    worker_count = max(1, min(int(workers), len(parallel_profiles)))
    profile_results: dict[str, list[dict]] = {}
    try:
        if worker_count == 1:
            for profile, viewport, origins in profiles:
                profile_results[profile] = _run_profile_isolated(
                    base_url, sessions, profile, viewport, origins, timeout
                )
                print(f"BROWSER_PROFILE_COMPLETE {profile}", flush=True)
        else:
            # Public/client profiles are read-only and isolated enough to run in
            # parallel. Admin pages share heavier operational reads against the
            # same temporary Flask/SQLite process, so keep them serial to avoid
            # actionability/navigation timeouts caused by test-only contention.
            with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="v929-browser") as executor:
                futures = {
                    executor.submit(
                        _run_profile_isolated,
                        base_url,
                        sessions,
                        profile,
                        viewport,
                        origins,
                        timeout,
                    ): profile
                    for profile, viewport, origins in parallel_profiles
                }
                for future in as_completed(futures):
                    profile = futures[future]
                    profile_results[profile] = future.result()
                    print(f"BROWSER_PROFILE_COMPLETE {profile}", flush=True)
            for profile, viewport, origins in serial_profiles:
                profile_results[profile] = _run_profile_isolated(
                    base_url, sessions, profile, viewport, origins, timeout
                )
                print(f"BROWSER_PROFILE_COMPLETE {profile}", flush=True)
        for profile, _viewport, _origins in profiles:
            results.extend(profile_results[profile])
    finally:
        server.shutdown()
        server.server_close()

    video_check_client = app_module.app.test_client()
    video_response = video_check_client.get("/clientes", follow_redirects=False)
    video_location = video_response.headers.get("Location", "")
    failures = [item for item in results if item.get("result") not in {"OK"}]
    payload = {
        "version": VERSION,
        "generated_at_madrid": _now_madrid(),
        "browser_engine": "Playwright Chromium",
        "safe_mock_sessions": True,
        "temporary_database": True,
        "service_workers_blocked": True,
        "dangerous_actions_executed": False,
        "clicks_tested": len(results),
        "clicks_ok": len(results) - len(failures),
        "failures_count": len(failures),
        "video_route_validation": {
            "path": "/clientes",
            "status": int(video_response.status_code),
            "location": video_location,
            "ok": int(video_response.status_code) in {301, 302, 303, 307, 308}
            and "/cliente-login" in video_location,
        },
        "profiles": {
            profile: len([item for item in results if item.get("profile") == profile])
            for profile, _viewport, _origins in profiles
        },
        "canonical_admin_routes": list(ADMIN_ORIGINS),
        "canonical_client_routes": list(CLIENT_ORIGINS),
        "results": results,
        "failures": failures,
        "next_required_action": "fix_click_failures" if failures else "deploy_v929_and_verify_runtime",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=15000)
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("NEMESIS_BROWSER_QA_WORKERS", "2")),
        help="Parallel isolated browser profiles. Default: 2.",
    )
    args = parser.parse_args()
    payload = run(
        timeout=max(3000, int(args.timeout)),
        workers=max(1, int(args.workers)),
    )
    print(json.dumps({
        "version": payload["version"],
        "clicks_tested": payload["clicks_tested"],
        "clicks_ok": payload["clicks_ok"],
        "failures_count": payload["failures_count"],
        "video_route_validation": payload["video_route_validation"],
        "next_required_action": payload["next_required_action"],
    }, ensure_ascii=False, indent=2))
    return 0 if payload["failures_count"] == 0 and payload["video_route_validation"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
