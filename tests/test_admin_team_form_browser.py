"""Offline components with labelled synthetic records; no production actions."""
import os
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from engines.team_form_engine import team_form_snapshot

ROOT = Path(__file__).resolve().parents[1]


def render_form(*, empty=False, legacy=False, unsafe=False):
    rows = [dict(id=f"qa-{n}", external_id=f"e{n}", source="api_football_cache", home_team="Club QA",
                 away_team="<script>window.injected=1</script>" if unsafe else f"Rival QA {n}",
                 status="FT", home_score=0, away_score=0, kickoff_iso=f"2026-09-{n:02d}T20:00:00Z")
            for n in range(1,8)]
    snapshot = team_form_snapshot([] if empty else rows,"Club QA")
    if legacy: snapshot.pop("contract")
    env = Environment(loader=FileSystemLoader(str(ROOT/"templates")),autoescape=select_autoescape(["html"]))
    fragment = env.get_template("components/admin_team_form.html").render(mi={"team_form":{"home":snapshot,"away":{}}})
    css = (ROOT/"static/admin-team-form.css").read_text()
    return f'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{{background:#091323;color:#eaf3ff;font-family:Arial;margin:12px}}{css}</style><body><main><p>SIMULATED_QA · NO PRODUCCIÓN</p>{fragment}</main></body></html>'


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        options = {"headless":True}
        if os.getenv("NEMESIS_QA_CHROMIUM"): options["executable_path"] = os.environ["NEMESIS_QA_CHROMIUM"]
        browser = pw.chromium.launch(**options)
        yield browser
        browser.close()


@pytest.mark.parametrize("width", [320,390,430,1366])
@pytest.mark.parametrize("javascript", [False,True])
def test_native_disclosure_zero_scores_and_layout(browser,width,javascript,tmp_path):
    page = browser.new_page(viewport={"width":width,"height":844},java_script_enabled=javascript)
    requests = []; page.route("**/*", lambda route:(requests.append(route.request.url),route.abort()))
    try:
        page.set_content(render_form())
        assert page.locator("[data-form-side]").count() == 2
        assert page.locator(".admin-team-form-totals dd").all_text_contents() == ["5","0","5","0","0","0"]
        summary = page.locator("summary"); summary.focus(); page.keyboard.press("Enter")
        assert page.locator("details").get_attribute("open") is not None
        assert page.locator("li").count() == 5
        assert page.locator("li strong").all_text_contents() == ["0–0"] * 5
        assert page.locator("li a").first.get_attribute("href") == "/match/qa-7"
        assert summary.bounding_box()["height"] >= 44 and page.locator("li a").first.bounding_box()["height"] >= 44
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert "Total de temporada: no verificado" in page.locator("body").inner_text()
        assert "ni reconstruye" in page.locator("body").inner_text()
        assert not requests
        page.screenshot(path=str(tmp_path/f"admin-form-{width}-{javascript}.png"),full_page=True)
        if width==390 and javascript and os.getenv("NEMESIS_FORM_EVIDENCE_DIR"):
            target = Path(os.environ["NEMESIS_FORM_EVIDENCE_DIR"]);target.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(target/"admin-form-390.png"),full_page=True)
    finally: page.close()


@pytest.mark.parametrize("arguments",[{"empty":True},{"legacy":True}])
def test_missing_or_old_evidence_does_not_invent_stats(browser,arguments):
    page = browser.new_page()
    try:
        page.set_content(render_form(**arguments))
        assert page.locator(".admin-team-form-totals").count() == 0
        assert page.locator("[data-form-empty]").count() == 2
    finally: page.close()


def test_provider_names_remain_escaped(browser):
    page = browser.new_page()
    try:
        page.set_content(render_form(unsafe=True)); page.locator("summary").click()
        assert page.locator("script").count() == 0
        assert page.evaluate("window.injected") is None
        assert "<script>" in page.locator("li a").first.inner_text()
    finally: page.close()
