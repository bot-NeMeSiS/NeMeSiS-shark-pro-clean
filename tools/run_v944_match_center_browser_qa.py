#!/usr/bin/env python3
"""Six rendered Match Center observations, never production certification."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import urlparse
from urllib.request import url2pathname

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"desktop": (1366, 768), "tablet": (834, 1194), "mobile": (390, 844)}
SCENARIOS = {"available": "m-1", "partial": "m-2"}
COMPONENTS = (
    "MatchHeader", "ScoreWidget", "MatchStory", "Timeline", "StatsPanel",
    "SharkPanel", "TelegramPanel", "BankrollPanel", "CompetitionPanel", "QuickActions",
)
DEFAULT_OUTPUT = ROOT / "browser_qa/V944_MATCH_CENTER_FOUNDATION"


def qa_identity() -> dict[str, str]:
    """Ephemeral credentials shared only by this isolated app and its browser."""
    return {
        "ADMIN_EMAIL": "qa@example.invalid",
        "ADMIN_PASSWORD": secrets.token_urlsafe(24),
        "SECRET_KEY": secrets.token_urlsafe(32),
        "AUTOMATION_SECRET": "",
    }

# DOM observations are shared by the CI browser and supervised local browser QA.
INSPECT_JS = r"""() => {
  const root = document.querySelector('[data-v944-match-center-foundation]');
  const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const clipped = [...(root || document).querySelectorAll('button,a,strong,p,small')]
    .filter(visible).filter(e => {
      const s = getComputedStyle(e);
      return e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 2 &&
        !['auto','scroll'].includes(s.overflowX) && s.display !== 'inline';
    }).map(e => e.tagName + '.' + e.className);
  return {
    shell_count: document.querySelectorAll('[data-v944-match-center-foundation]').length,
    components: [...document.querySelectorAll('[data-match-component]')].map(e => e.dataset.matchComponent),
    component_states: [...document.querySelectorAll('[data-match-component]')].map(e => [e.dataset.matchComponent,e.dataset.componentState]),
    teams: [...document.querySelectorAll('.v944-match-team strong')].map(e => e.textContent.trim()),
    score: document.querySelector('.v944-score-widget strong')?.textContent.trim() || '',
    phase: document.querySelector('.v944-score-widget__phase')?.textContent.trim() || '',
    horizontal_overflow: document.documentElement.scrollWidth > innerWidth + 2,
    clipped_text: clipped,
    broken_images: [...document.images].filter(e => !e.complete || e.naturalWidth === 0).map(e => new URL(e.src).pathname),
    admin_links: [...document.querySelectorAll('a[href]')].filter(visible).filter(e => new URL(e.href).pathname.startsWith('/admin')).length,
    viewport: [innerWidth, innerHeight],
    temporal_labels: [...document.querySelectorAll('[data-match-temporal-context]')].map(e => e.textContent.trim())
  };
}"""


def source_fingerprint(root: Path = ROOT) -> str:
    """Bind generated evidence to relevant source bytes, including uncommitted work."""
    paths = [root / "app.py", root / "VERSION.txt", root / "APP_VERSION"]
    for directory in ("engines", "templates", "static", "tools", "automation_workforce"):
        paths.extend(p for p in (root / directory).rglob("*")
                     if p.is_file() and p.suffix != ".pyc" and "__pycache__" not in p.parts)
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def observation_failures(row: dict) -> list[str]:
    errors = []
    expected = SCENARIOS.get(row.get("scenario"))
    if row.get("http") != 200 or row.get("path") != "/match/" + str(expected):
        errors.append("match response/identity")
    if row.get("shell_count") != 1 or any(row.get("components", []).count(c) != 1 for c in COMPONENTS):
        errors.append("missing or duplicate component")
    if row.get("teams") != (["Club Norte", "Club Sur"] if expected == "m-1" else ["Club Este", "Club Oeste"]):
        errors.append("teams")
    if row.get("score") != ("2-0" if expected == "m-1" else "VS"):
        errors.append("score/unknown score")
    states = dict(row.get("component_states", []))
    if expected == "m-1" and any(states.get(c) != s for c, s in (
        ("MatchHeader", "finished"), ("Timeline", "ready"), ("StatsPanel", "ready"),
    )):
        errors.append("available data not rendered")
    if expected == "m-2" and any(states.get(c) != "partial" for c in ("Timeline", "StatsPanel")):
        errors.append("missing data is not partial")
    if not row.get("temporal_labels"):
        errors.append("temporal context")
    for key in ("horizontal_overflow", "clipped_text", "broken_images", "admin_links", "js_errors", "console_errors", "http_errors", "external_requests"):
        if row.get(key) not in (False, 0, []):
            errors.append(key)
    if row.get("navigation") != ["/calendar", "/match/" + str(expected)]:
        errors.append("real back/return navigation")
    if row.get("viewport") != list(PROFILES.get(row.get("profile"), ())):
        errors.append("viewport")
    return errors


def screenshot_failures(output: Path, row: dict) -> list[str]:
    from PIL import Image
    image = output / row.get("screenshot", "")
    if image.resolve().parent != output.resolve() or not image.is_file():
        return ["Browser screenshot missing or outside artifact"]
    errors = []
    if hashlib.sha256(image.read_bytes()).hexdigest() != row.get("screenshot_sha256"):
        errors.append("Browser screenshot hash mismatch")
    with Image.open(image) as rendered:
        width, height = PROFILES.get(row.get("profile"), (0, 0))
        if rendered.format != "PNG" or rendered.width != width or rendered.height < height:
            errors.append("Browser screenshot dimensions/format mismatch")
    return errors


def write_result(output: Path, captures: list[dict], fingerprint: str, guards: list[str], driver: str) -> dict:
    from datetime import datetime, timezone
    result = {
        "schema": "V944-RENDERED-EVIDENCE-1", "evidence_origin": "SIMULATED_QA",
        "generated_at": datetime.now(timezone.utc).isoformat(), "source_fingerprint": fingerprint,
        "driver": driver, "production_modified": False, "production_certified": False,
        "profiles": list(PROFILES), "captures": captures,
        "screenshots_captured": len(captures), "blocked_attempts": guards,
        "external_calls": 0, "status": "FAIL",
    }
    expected = {(s, p) for s in SCENARIOS for p in PROFILES}
    if len(captures) == 6 and {(r.get("scenario"), r.get("profile")) for r in captures} == expected:
        if not guards and all(not observation_failures(r) and not screenshot_failures(output, r) for r in captures):
            result["status"] = "PASS"
    (output / "browser_qa_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def install_boundary(temp: Path, output: Path, database: Path, driver_command: list[str]) -> list[str]:
    """Restrict the Python app to this run's disposable storage and loopback."""
    blocked: list[str] = []

    def inside(raw):
        value = os.fsdecode(raw)
        if value.startswith("file:"):
            parsed = urlparse(value)
            if parsed.netloc not in ("", "localhost"):
                return False
            value = url2pathname(parsed.path)
        p = Path(value).resolve()
        return p.is_relative_to(temp) or p.is_relative_to(output) or p in (
            database, Path(str(database) + "-wal"), Path(str(database) + "-shm"), Path(str(database) + "-journal"),
        )

    def audit(event, args):
        path = None
        if event == "socket.connect":
            if isinstance(args[1], tuple) and args[1][0] in ("127.0.0.1", "::1", "localhost"):
                return
            blocked.append("NETWORK")
            raise PermissionError("V944_QA_NETWORK_BLOCKED")
        if event == "subprocess.Popen":
            if driver_command and list(args[1]) == driver_command:
                return
            blocked.append("PROCESS")
            raise PermissionError("V944_QA_PROCESS_BLOCKED")
        if event in ("os.system", "os.exec", "os.spawn"):
            blocked.append("PROCESS")
            raise PermissionError("V944_QA_PROCESS_BLOCKED")
        if event == "sqlite3.connect" and args[0] != ":memory:":
            path = args[0]
        elif event == "open" and isinstance(args[0], (str, bytes)):
            if any(c in (args[1] or "") for c in "wax+") or (args[2] or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                path = args[0]
        elif event in ("os.mkdir", "os.remove", "os.rmdir", "os.rename"):
            path = args[0]
            if event == "os.mkdir" and Path(os.fsdecode(path)).is_dir():
                return
            if event == "os.rename" and not inside(args[1]):
                blocked.append("RENAME")
                raise PermissionError("V944_QA_WRITE_BLOCKED")
        if path is not None and not inside(path):
            blocked.append(event)
            raise PermissionError("V944_QA_WRITE_BLOCKED")

    sys.addaudithook(audit)
    return blocked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--serve", action="store_true", help="Supervised local browser, same isolated app; no automatic PASS")
    args = parser.parse_args()
    output = args.output.resolve()
    if not any(output.is_relative_to(ROOT / p) for p in ("browser_qa", ".tmp_reference_review")):
        parser.error("Evidence must remain in the excluded QA areas")
    output.mkdir(parents=True, exist_ok=True)
    import tempfile
    import uuid
    from datetime import datetime
    from zoneinfo import ZoneInfo
    sys.path.insert(0, str(ROOT))
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(output / "bytecode")
    fingerprint = source_fingerprint()
    temp = ROOT / "data/local_dev" / ("qa_v944_" + uuid.uuid4().hex)
    temp.mkdir(parents=True)
    database = temp.with_suffix(".sqlite")
    os.environ["TEMP"] = os.environ["TMP"] = str(temp)
    tempfile.tempdir = str(temp)
    os.environ["NEMESIS_LOCAL_EXTERNAL_AUTHORIZED"] = "0"
    from tools.local_desktop.run_local_desktop import configure_local_environment
    configure_local_environment("OFFLINE_SAFE", 5000, database.name)
    for key in ("BACKGROUND_JOBS_ENABLED", "AUTO_GENERATE_PICKS", "AUTO_SEND_TELEGRAM_PICKS"):
        os.environ[key] = "false"
    identity = qa_identity()
    os.environ.update(identity, CONTINUOUS_EVOLUTION_STORAGE_PATH=str(temp / "continuous_evolution_os"))
    driver_command = []
    if not args.serve:
        from playwright._impl._driver import compute_driver_executable
        driver_command = [*map(str, compute_driver_executable()), "run-driver"]
    guards = install_boundary(temp, output, database, driver_command)
    from tools import run_autonomous_product_qa as qa
    qa.seed_database(database)
    qa._seed_extra(database, identity["ADMIN_PASSWORD"], datetime.now(ZoneInfo("Europe/Madrid")))
    import app
    app.DB_PATH = str(database)
    app._SEEDED_DB_PATH = str(database)
    app.APP_INITIALIZED = True
    app.app.config.update(TESTING=True)
    app.v896_not_found_memory_path = lambda: temp / "not_found_events.json"

    http_observations = []

    @app.app.after_request
    def local_only(response):
        from flask import request
        http_observations.append({"path": request.path, "http": response.status_code})
        (output / "http_observations.json").write_text(json.dumps(http_observations), encoding="utf-8")
        response.headers["Content-Security-Policy"] = "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; font-src 'self' data:; frame-src 'none'"
        return response

    from werkzeug.serving import make_server
    server = make_server("127.0.0.1", 0, app.app, threaded=True)
    base_url = "http://127.0.0.1:" + str(server.server_port)
    (output / "session.json").write_text(json.dumps({"url": base_url, "source_fingerprint": fingerprint,
        "temp_relative": temp.relative_to(ROOT).as_posix(), "db_relative": database.relative_to(ROOT).as_posix(),
        "origin": "SIMULATED_QA"}, indent=2), encoding="utf-8")
    if args.serve:
        print("V944_QA_READY " + base_url, flush=True)
        try:
            server.serve_forever()
        finally:
            server.server_close()
            (output / "guards.json").write_text(json.dumps(guards), encoding="utf-8")
        return 0
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    captures = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for profile, (width, height) in PROFILES.items():
                context = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
                external = []

                def route_guard(route):
                    if urlparse(route.request.url).netloc == urlparse(base_url).netloc:
                        route.continue_()
                    else:
                        external.append(urlparse(route.request.url).hostname)
                        route.abort()

                context.route("**/*", route_guard)
                page = context.new_page()
                js_errors, console_errors, http_errors = [], [], []
                page.on("pageerror", lambda e: js_errors.append(str(e)))
                page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
                page.on("response", lambda r: http_errors.append({"path": urlparse(r.url).path, "http": r.status}) if r.status >= 400 else None)
                page.goto(base_url + "/cliente-login", wait_until="domcontentloaded")
                page.locator("input[name='login']").fill("client-qa@example.invalid")
                page.locator("input[name='password']").fill(identity["ADMIN_PASSWORD"])
                page.locator("button[type='submit']").click()
                page.wait_for_url("**/app")
                for scenario, match_id in SCENARIOS.items():
                    path = "/match/" + match_id
                    response = page.goto(base_url + path, wait_until="domcontentloaded")
                    page.locator("[data-match-component='MatchHeader']").wait_for(state="visible")
                    page.evaluate("() => document.fonts.ready")
                    screenshot = output / (scenario + "-" + profile + ".png")
                    page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
                    row = page.evaluate(INSPECT_JS)
                    row.update(scenario=scenario, profile=profile, path=urlparse(page.url).path,
                               http=response.status, screenshot=screenshot.name,
                               screenshot_sha256=hashlib.sha256(screenshot.read_bytes()).hexdigest())
                    page.locator("a.v944-back-link").click()
                    page.wait_for_url("**/calendar")
                    navigation = [urlparse(page.url).path]
                    page.go_back(wait_until="domcontentloaded")
                    page.locator("[data-match-component='MatchHeader']").wait_for(state="visible")
                    navigation.append(urlparse(page.url).path)
                    row.update(navigation=navigation, js_errors=list(js_errors), console_errors=list(console_errors),
                               http_errors=list(http_errors), external_requests=list(external))
                    captures.append(row)
                context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        result = write_result(output, captures, fingerprint, guards, "Playwright Chromium")
    print(json.dumps({"status": result["status"], "screenshots": len(captures), "origin": "SIMULATED_QA"}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
