"""Real guarded Match Center/SQLite/browser geometry, never production data.

Run with tools/check_local_candidate.py, which imports the actual App under the
original LOCAL SAFE audit boundary. No route, auth, render or read-model mocks.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import threading
from urllib.parse import quote

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


@pytest.fixture
def fixture_server(monkeypatch, tmp_path):
    a = sys.modules.get("app")
    assert a is not None and a.local_safe_mode_enabled()
    assert Path(a.__file__).resolve() == Path(__file__).resolve().parents[1] / "app.py"
    assert tmp_path.resolve().is_relative_to(Path(a.LOCAL_SAFE_DATA_DIR).resolve())
    database = tmp_path / "owned-match-header.sqlite"
    monkeypatch.setattr(a, "DB_PATH", str(database))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    monkeypatch.setitem(a.app.config, "TESTING", False)
    a.seed_core()
    now = datetime.now(timezone.utc)
    scenarios = (
        ("short", "Club Norte", "Club Sur", "FT", "2", "1"),
        ("long", "Real Club Deportivo del Norte de la Ciudad", "Unión Deportiva de la Ciudad del Sur", "NS", None, None),
        ("bidi", "نادي الشمال الرياضي", "מועדון הדרום הספורטיבי", "NS", None, None),
        ("fallback", "EquipoSinEscudoNombreExtremadamenteLargo", "RivalSinEscudoNombreExtremadamenteLargo", "NS", None, None),
    )
    from tools.local_desktop.run_local_desktop import insert_row
    with sqlite3.connect(database) as conn:
        insert_row(conn, "competitions", {"key": "v1000-owned-league", "name": "Liga QA aislada", "country": "Spain", "source": "SIMULATED_QA"})
        for case, home, away, status, hs, aws in scenarios:
            for side, name in (("home", home), ("away", away)):
                key = "v1000-" + case + "-" + side
                insert_row(conn, "teams", {"key": key, "name": name, "country": "Spain", "source": "SIMULATED_QA",
                    "logo_url": "" if case == "fallback" else "/team-crest.svg?name=" + key})
            kickoff = now + timedelta(days=-1 if status == "FT" else 1)
            insert_row(conn, "matches", {"id": "v1000-" + case, "sport_key": "soccer", "home_team": home, "away_team": away,
                "home_team_id": "v1000-" + case + "-home", "away_team_id": "v1000-" + case + "-away",
                "home_logo": "" if case == "fallback" else "/team-crest.svg?name=v1000-" + case + "-home",
                "away_logo": "" if case == "fallback" else "/team-crest.svg?name=v1000-" + case + "-away",
                "competition_key": "v1000-owned-league", "competition_name": "Liga QA aislada", "country": "Spain",
                "match_date": kickoff.date().isoformat(), "kickoff_iso": kickoff.isoformat(), "kickoff_time": "20:00",
                "status": status, "home_score": hs, "away_score": aws, "score": "2-1" if status == "FT" else "",
                "source": "SIMULATED_QA", "updated_at": now.isoformat(), "raw_json": json.dumps({"evidence_origin": "SIMULATED_QA"})})
    server = make_server("127.0.0.1", 0, a.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield a, database, f"http://127.0.0.1:{server.server_port}", scenarios
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("width,height", [(320, 720), (390, 844), (834, 1112), (1440, 960)])
def test_actual_fixture_header_keeps_each_crest_with_its_name_and_score_separate(fixture_server, tmp_path, width, height):
    _a, database, origin, scenarios = fixture_server
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ["NEMESIS_QA_CHROMIUM"])
        context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
        external = []
        def boundary(route):
            if route.request.url.startswith(origin + "/"):
                route.continue_()
            else:
                external.append(route.request.url.split("?")[0])
                route.abort()
        context.route("**/*", boundary)
        page = context.new_page()
        observations = []
        failures = []
        try:
            for case, home, away, status, _hs, _aws in scenarios:
                response = page.goto(origin + "/match/v1000-" + case, wait_until="networkidle")
                assert response.status == 200
                assert page.locator('[data-match-component="MatchHeader"]').count() == 1
                page.locator(".v944-match-team").first.wait_for()
                header = page.locator('[data-match-component="MatchHeader"]')
                header.screenshot(path=str(tmp_path / f"header-{width}-{case}.png"))
                observation = page.evaluate("""() => {
                  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
                  const score=document.querySelector('.v944-match-header__status');
                  const surface=getComputedStyle(document.querySelector('[data-match-component="MatchHeader"]'));
                  return {viewport:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+2,
                    surface:{background:surface.backgroundColor,image:surface.backgroundImage,opacity:surface.opacity,
                      panel:surface.getPropertyValue('--product-panel').trim()},
                    score:rect(score),scoreLabel:score.querySelector('.v944-score-widget strong').textContent.trim(),
                    teams:[...document.querySelectorAll('.v944-match-team')].map(e=>{
                      const logo=e.querySelector('.v933-team-logo'),name=e.querySelector('strong');
                      const a=rect(logo),b=rect(name);
                      const dx=Math.max(0,a.x-b.right,b.x-a.right),dy=Math.max(0,a.y-b.bottom,b.y-a.bottom);
                      return {name:name.textContent.trim(),href:e.getAttribute('href'),box:rect(e),logo:a,text:b,
                        gap:Math.hypot(dx,dy),logoSource:logo.querySelector('img')?.getAttribute('src')||'',
                        columns:getComputedStyle(e).gridTemplateColumns,areas:getComputedStyle(e).gridTemplateAreas,
                        nameClipped:name.scrollWidth>name.clientWidth+2,role:e.querySelector('small').textContent.trim()};
                    })};
                }""")
                observation["case"] = case
                observations.append(observation)
                (tmp_path / f"geometry-{width}.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8")
                assert [team["name"] for team in observation["teams"]] == [home, away]
                assert observation["scoreLabel"] == ("2-1" if status == "FT" else "VS")
                assert observation["surface"]["background"] == "rgb(20, 28, 41)", observation["surface"]
                assert observation["surface"]["opacity"] == "1"
                assert not observation["overflow"]
                assert all(not team["nameClipped"] for team in observation["teams"])
                assert page.locator('.v944-match-team strong[dir="auto"]').count() == 2
                for side, team in zip(("home", "away"), observation["teams"]):
                    # Preserve the existing canonical fallback by name when no
                    # verified canonical-team ID exists in the synthetic row.
                    assert team["href"] == "/team/" + quote(team["name"], safe="")
                    if case != "fallback":
                        assert team["logoSource"] == "/team-crest.svg?name=v1000-" + case + "-" + side
                    else:
                        assert team["logoSource"] == "/team-crest.svg?name=" + quote(team["name"])
                    if team["gap"] > 16:
                        failures.append(f"{case}/{side}: crest/name gap {team['gap']:.1f}px")
                    score = observation["score"]
                    assert team["box"]["right"] <= score["x"] + 1 or team["box"]["x"] >= score["right"] - 1
                assert [value.strip() for value in page.locator('.v944-match-team small').all_text_contents()] == ['Local', 'Visitante']
                if case == "short":
                    for side_index, expected_name in enumerate((home, away)):
                        target = page.locator('.v944-match-team').nth(side_index)
                        target.focus()
                        assert target.evaluate("e => document.activeElement === e")
                        expected_href = "/team/" + quote(expected_name, safe="")
                        target.click()
                        page.wait_for_url(origin + expected_href)
                        page.wait_for_load_state("networkidle")
                        assert page.locator('.team-center-hero').count() == 1
                        assert expected_name in page.locator('.team-center-hero').inner_text()
                        page.goto(origin + "/match/v1000-" + case, wait_until="networkidle")
            assert not external, external
            (tmp_path / f"geometry-{width}.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8")
            print("MATCH_HEADER_GEOMETRY " + json.dumps(observations, ensure_ascii=True), flush=True)
            assert not failures, failures
        finally:
            context.close()
            browser.close()
