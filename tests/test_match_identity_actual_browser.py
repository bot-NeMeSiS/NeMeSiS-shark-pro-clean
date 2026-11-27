"""Actual original LOCAL SAFE App/SQLite/login/Chromium identity geometry."""
from pathlib import Path
import ast
import json
import os
import runpy
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright
from browser_http_server import owned_http_server
from test_shark_functional_flow import prepared_probe, shark_probe

ROOT = Path(__file__).resolve().parents[1]
CASES = [("ANONYMOUS", 320), ("FREE", 390), ("ANONYMOUS", 768), ("PRO", 1024), ("ELITE", 1440)]
HOME = "Real Club Deportivo del Norte de la Ciudad"
AWAY = "Union Deportiva de la Ciudad del Sur"
_loaded = sys.modules.get("app")
_OWNED = bool(_loaded is not None and _loaded.local_safe_mode_enabled())


def _observe_identity(probe, width, principal, tmp_path):
    a = probe["a"]
    with sqlite3.connect(probe["path"]) as connection:
        for mid in ("af-99990001", "af-99990002", "af-99990003"):
            raw = json.loads(connection.execute("SELECT raw_json FROM matches WHERE id=?", (mid,)).fetchone()[0])
            raw["teams"]["home"].update(name=HOME, logo="/team-crest.svg?name=owned-home")
            raw["teams"]["away"].update(name=AWAY, logo="/team-crest.svg?name=owned-away")
            connection.execute("UPDATE matches SET home_team=?,away_team=?,home_logo=?,away_logo=?,raw_json=? WHERE id=?",
                (HOME, AWAY, "/team-crest.svg?name=owned-home", "/team-crest.svg?name=owned-away", json.dumps(raw), mid))
        connection.execute("UPDATE teams SET name=?,logo_url=? WHERE key='qa-favorite-ref'",
            (HOME, "/team-crest.svg?name=owned-home"))
    a.invalidate_v934_realtime_cache()
    cookie_name = a.app.config.get("SESSION_COOKIE_NAME", "session")
    cookie = None
    expected_user = None
    if principal != "ANONYMOUS":
        client, _csrf = probe["login"](principal)
        cookie = client.get_cookie(cookie_name, domain="127.0.0.1").value
        expected_user = probe["users"][principal][0]
    documents = []
    def observed_application(environ, start_response):
        def observe(status, headers, exc_info=None):
            if environ.get("PATH_INFO") in ("/calendario", "/directo"):
                user = a.current_session_user() or {}
                documents.append({"path": environ["PATH_INFO"], "status": status.split()[0],
                                  "same_user": user.get("id") == expected_user})
            return start_response(status, headers, exc_info)
        return a.app(environ, observe)

    with owned_http_server(observed_application) as server, sync_playwright() as pw:
        origin = "http://127.0.0.1:" + str(server.server_port)
        browser = pw.chromium.launch(headless=True, executable_path=os.environ["NEMESIS_QA_CHROMIUM"])
        context = browser.new_context(viewport={"width": width, "height": 960}, locale="es-ES",
            timezone_id="Europe/Madrid", reduced_motion="reduce", service_workers="block")
        calls, external, errors = [], [], []
        if cookie:
            context.add_cookies([{"name": cookie_name, "value": cookie, "url": origin, "httpOnly": True}])
        def boundary(route):
            request = route.request
            path = urlsplit(request.url).path
            calls.append((request.method, path))
            if not request.url.startswith(origin + "/"):
                external.append(urlsplit(request.url).netloc)
                route.abort()
            else:
                route.continue_()
        context.route("**/*", boundary)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(type(error).__name__))
        observations = []
        try:
            for path, fixture_id in (("/calendario", "af-99990002"), ("/directo", "af-99990001")):
                response = page.goto(origin + path, wait_until="domcontentloaded", timeout=30000)
                assert response.status == 200 and urlsplit(page.url).path == path
                page.wait_for_function("() => Array.from(document.styleSheets).some(sheet => sheet.href && new URL(sheet.href).pathname === '/static/sports-match-density.css' && sheet.cssRules.length > 0)", timeout=10000)
                selector = '.v933-match-card[data-v934-match-id="' + fixture_id + '"]'
                assert page.locator(selector).count() >= 1
                for disclosure in page.locator("details").all():
                    if disclosure.locator(selector).count() and disclosure.get_attribute("open") is None:
                        disclosure.locator(":scope > summary").click()
                card = page.locator(selector).first
                card.scroll_into_view_if_needed()
                page.evaluate("() => document.fonts.ready.then(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))")
                assert card.locator(".v933-match-teams strong").all_text_contents() == [HOME, AWAY]
                metrics = card.evaluate("""node => {
                    const rect = node.getBoundingClientRect();
                    return {width: rect.width, fits: node.scrollWidth <= node.clientWidth + 1,
                      documentFits: document.documentElement.scrollWidth <= innerWidth + 1,
                      teams: [...node.querySelectorAll('.v933-match-teams strong')].map(el => ({
                        font: parseFloat(getComputedStyle(el).fontSize),
                        fits: el.scrollWidth <= el.clientWidth + 1,
                        clearOfCrest: (() => {
                          const text = el.getBoundingClientRect();
                          const crest = el.parentElement.querySelector('.v933-team-logo').getBoundingClientRect();
                          return text.right <= crest.left + .5 || text.left >= crest.right - .5
                            || text.bottom <= crest.top + .5 || text.top >= crest.bottom - .5;
                        })(),
                        text: el.textContent,
                      })),
                      crests: [...node.querySelectorAll('.v933-match-teams .v933-team-logo')].map(el => ({
                        width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height,
                      })),
                      links: [...node.querySelectorAll('.v933-match-teams a')].map(el => el.getAttribute('href')),
                    };
                }""")
                metrics.update(path=path, width=width, principal=principal)
                observations.append(metrics)
                card.screenshot(path=str(tmp_path / (principal + "-" + str(width) + "-" + path[1:] + ".png")))
                print("ACTUAL_MATCH_IDENTITY " + json.dumps(metrics, ensure_ascii=False))
                assert metrics["documentFits"] and metrics["fits"], metrics
                assert len(metrics["teams"]) == len(metrics["crests"]) == 2, metrics
                assert all(team["fits"] for team in metrics["teams"]), metrics
                assert all(href and href.startswith("/team/") for href in metrics["links"]), metrics
                if width >= 1024:
                    assert all(team["font"] >= 15 for team in metrics["teams"]), metrics
                    minimum_crest = 48 if path == "/directo" else 36
                    assert all(crest["width"] >= minimum_crest and crest["height"] >= minimum_crest for crest in metrics["crests"]), metrics
                    assert all(team["clearOfCrest"] for team in metrics["teams"]), metrics
                else:
                    assert all(team["font"] >= 12 for team in metrics["teams"]), metrics
                    assert all(crest["width"] >= 22 for crest in metrics["crests"]), metrics
                link = card.locator('.v933-match-card-actions a[href^="/match/"]').first
                expected_path = urlsplit(link.get_attribute("href")).path
                with page.expect_navigation(wait_until="domcontentloaded", timeout=10000) as navigation:
                    link.click()
                assert navigation.value.status == 200 and urlsplit(page.url).path == expected_path
            assert documents and all(doc["status"] == "200" and doc["same_user"] for doc in documents), documents
            assert not external and not errors, (external, errors)
            assert all(method in ("GET", "HEAD") or
                       (method == "POST" and path == "/api/growth/funnel-event") for method, path in calls), calls
            (tmp_path / "actual-match-identity.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
        finally:
            context.close()
            browser.close()


if _OWNED:
    @pytest.mark.parametrize("principal,width", CASES, ids=[p + "-" + str(w) for p, w in CASES])
    def test_actual_match_identity_keeps_names_crests_and_roles(prepared_probe, principal, width, tmp_path):
        _observe_identity(prepared_probe, width, principal, tmp_path)
else:
    def test_match_identity_in_original_guarded_browser_process(tmp_path):
        runner = ROOT / "tools/check_local_candidate.py"
        bootstrap = ("import platform,runpy,sys;platform.uname();platform.platform();"
                     "sys.argv=[sys.argv[1],sys.argv[2],'-s','--tb=short'];"
                     "runpy.run_path(sys.argv[0],run_name='__main__')")
        result = subprocess.run([sys.executable, "-B", "-c", bootstrap, str(runner), str(Path(__file__).resolve())],
            cwd=ROOT, env=dict(os.environ, PYTEST_ADDOPTS="", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                              PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        (tmp_path / "guarded-browser.stdout.log").write_text(result.stdout, encoding="utf-8")
        (tmp_path / "guarded-browser.stderr.log").write_text(result.stderr, encoding="utf-8")
        failure_lines = [line for line in result.stdout.splitlines()
                         if line.startswith(("E ", "FAILED ", "ERROR ", "tests/"))]
        if result.returncode != 0:
            # Keep the actual child assertion and geometry visible in CI. A tuple
            # assertion is abbreviated by pytest before its captured log exists.
            geometry = [line for line in result.stdout.splitlines()
                        if line.startswith("ACTUAL_MATCH_IDENTITY ")]
            pytest.fail("Original guarded browser failed:\n" +
                        "\n".join(failure_lines + geometry) + "\n" + result.stderr[-2000:],
                        pytrace=False)
        outputs = [line.removeprefix("QA_OUTPUT ") for line in result.stdout.splitlines() if line.startswith("QA_OUTPUT ")]
        boundaries = [line.removeprefix("BOUNDARY_EVENTS ") for line in result.stdout.splitlines() if line.startswith("BOUNDARY_EVENTS ")]
        assert len(outputs) == len(boundaries) == 1 and ast.literal_eval(boundaries[0]) == []
        output = Path(outputs[0]).resolve()
        assert output.is_relative_to((ROOT / "data/local_dev").resolve()) and output.name.startswith("candidate-")
        suite = ET.parse(output / "result.xml").find("testsuite")
        assert suite.attrib["tests"] == "5"
        assert all(suite.attrib[key] == "0" for key in ("errors", "failures", "skipped"))
