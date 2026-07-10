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
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL"
OUTPUT_JSON = ROOT / "reports" / "V929_CLICK_NAVIGATION_MATRIX.json"
OUTPUT_DIR = ROOT / "reports" / "V929_browser_qa_navigation"

PUBLIC_ORIGINS = ["/", "/cliente-login", "/registro"]
CLIENT_ORIGINS = [
    "/app", "/calendar", "/live", "/picks", "/track-record",
    "/shark", "/telegram", "/profile", "/memberships",
]
MOBILE_ORIGINS = ["/app", "/calendar", "/live", "/picks", "/profile"]
ADMIN_ORIGINS = [
    "/admin/dashboard", "/admin/telegram/command-center", "/admin/users",
    "/admin/payments", "/admin/picks", "/admin/data-center",
    "/admin/automation-workforce", "/admin/autonomous-company-sentinel",
    "/admin/navigation-integrity",
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
    return {
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
    }
    response = page.goto(base_url + origin, wait_until="domcontentloaded", timeout=timeout)
    if response and response.status >= 500:
        item.update(status=response.status, result="ORIGIN_500", final_path=urlsplit(page.url).path)
        return item

    target = item["target"]
    if action.get("tag") == "a":
        locator = page.locator(f'a[href="{target}"]:visible').first
    else:
        locator = page.locator(f'button[data-q="{target}"]:visible').first
    if locator.count() == 0:
        item["result"] = "SELECTOR_NOT_VISIBLE"
        return item
    try:
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
    except Exception as exc:
        item.update(result="CLICK_ERROR", error=f"{exc.__class__.__name__}: {str(exc)[:240]}")
    return item


def _run_profile(browser, base_url: str, sessions: dict, profile: str, viewport: dict, origins: list[str], timeout: int) -> list[dict]:
    context = browser.new_context(viewport=viewport, service_workers="block")
    if profile in {"client_desktop", "client_mobile", "admin_desktop"}:
        role = "admin" if profile.startswith("admin") else "client"
        context.add_cookies([{
            "name": sessions["cookie_name"],
            "value": sessions[role],
            "url": base_url,
            "httpOnly": True,
        }])
    page = context.new_page()
    results: list[dict] = []
    tested_targets: set[str] = set()
    try:
        for origin in origins:
            response = page.goto(base_url + origin, wait_until="domcontentloaded", timeout=timeout)
            if not response or response.status >= 500:
                results.append({
                    "profile": profile, "origin": origin, "visible_text": "Abrir pantalla",
                    "target": origin, "selector": "direct_origin_check",
                    "status": response.status if response else 0,
                    "result": "ORIGIN_500", "final_path": urlsplit(page.url).path,
                    "screenshot": "",
                })
                continue
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


def run(timeout: int = 15000) -> dict:
    app_module = _prepare_local_app()
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright

    port = _free_port()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", port, app_module.app, threaded=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"
    sessions = _signed_sessions(app_module.app)
    results: list[dict] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                profiles = [
                    ("public_desktop", {"width": 1440, "height": 900}, PUBLIC_ORIGINS),
                    ("client_desktop", {"width": 1440, "height": 900}, CLIENT_ORIGINS),
                    ("client_mobile", {"width": 390, "height": 844}, MOBILE_ORIGINS),
                    ("admin_desktop", {"width": 1440, "height": 900}, ADMIN_ORIGINS),
                ]
                for profile, viewport, origins in profiles:
                    results.extend(_run_profile(browser, base_url, sessions, profile, viewport, origins, timeout))
            finally:
                browser.close()
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
            for profile in ("public_desktop", "client_desktop", "client_mobile", "admin_desktop")
        },
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
    args = parser.parse_args()
    payload = run(timeout=max(3000, int(args.timeout)))
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
