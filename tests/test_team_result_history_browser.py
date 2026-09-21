"""Offline browser checks of the actual recorded-results partial, not production."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from engines.team_result_evidence_engine import build_team_result_evidence

ROOT=Path(__file__).resolve().parents[1]


def page_html(locale="es", *, empty=False, malicious=False):
    rows=[dict(id=f"qa-{n}", external_id=f"e{n}", source="api_football_cache",home_team="Club QA",
               away_team=("<script>window.qaInjected=true</script>" if malicious else f"Visitante QA {n}"),
               competition_id="140",competition_name="Liga QA",season="2026-2027",country="Spain",
               status="FT",home_score=n%3,away_score=0,kickoff_iso=f"2026-09-{n:02d}T20:00:00+02:00") for n in range(1,8)]
    h=build_team_result_evidence([] if empty else rows,"Club QA")
    env=Environment(loader=FileSystemLoader(str(ROOT/"templates")),autoescape=select_autoescape(["html"]))
    content=env.get_template("components/team_result_history.html").render(center={"result_history":h},ui_locale=locale)
    styles="\n".join((ROOT/"static"/name).read_text() for name in ["v933_design_tokens.css","v933-product.css","team-history.css"])
    return f'<!doctype html><html lang="{locale}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{styles}</style><body class="ns-app"><main><small>SIMULATED_QA · NO PRODUCCIÓN</small>{content}</main></body></html>'


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        options={"headless":True}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            options["executable_path"]=os.environ["NEMESIS_QA_CHROMIUM"]
        engine=pw.chromium.launch(**options)
        yield engine
        engine.close()


@pytest.mark.parametrize("width",[320,390,430,1366])
@pytest.mark.parametrize("locale",["es","en","fr"])
def test_recorded_results_accessible_and_not_a_season_total(browser,width,locale,tmp_path):
    page=browser.new_page(viewport={"width":width,"height":844},reduced_motion="reduce")
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.route("**/*",lambda route:route.abort())
    try:
        page.set_content(page_html(locale))
        assert page.locator('.team-history-group').count()==1
        assert page.locator('.team-history-totals dd').all_text_contents()[0]=='7'
        summary=page.locator('summary')
        assert summary.bounding_box()['height']>=44
        summary.focus(); page.keyboard.press('Enter')
        assert page.locator('details').get_attribute('open') is not None
        assert page.locator('.team-history li').count()==7
        assert page.locator('.team-history a').first.get_attribute('href')=='/match/qa-7'
        assert '0–0' in page.locator('.team-history').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        assert page.locator('main').count()==1
        assert not errors
        page.screenshot(path=str(tmp_path/f'team-history-{locale}-{width}.png'),full_page=True)
        if locale=='es' and width==390 and os.getenv('NEMESIS_TEAM_EVIDENCE_DIR'):
            target=Path(os.environ['NEMESIS_TEAM_EVIDENCE_DIR']); target.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(target/'team-history-390.png'),full_page=True)
        summary.click()
        assert page.locator('details').get_attribute('open') is None
    finally: page.close()


@pytest.mark.parametrize("locale",["es","en","fr","unsupported"])
def test_empty_sample_does_not_fabricate_totals(browser,locale):
    page=browser.new_page(viewport={"width":390,"height":844},java_script_enabled=False)
    try:
        page.set_content(page_html(locale,empty=True))
        assert page.locator('.team-history-group').count()==0
        assert page.locator('.team-history-totals').count()==0
        assert page.locator('.team-history').inner_text().strip()
    finally: page.close()


def test_names_are_escaped_and_native_details_work_without_javascript(browser):
    page=browser.new_page(viewport={"width":390,"height":844},java_script_enabled=False)
    try:
        page.set_content(page_html(malicious=True))
        page.locator('summary').click()
        assert page.locator('.team-history script').count()==0
        assert '<script>' in page.locator('.team-history a').first.inner_text()
        assert page.locator('details').get_attribute('open') is not None
        assert page.locator('.team-history a').first.bounding_box()['height']>=44
    finally: page.close()
