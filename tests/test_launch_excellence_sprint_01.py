from pathlib import Path
import re
from urllib.parse import urlsplit

from flask import render_template
import pytest

from test_design02_calendar_presentation import Structure
from test_combi_routes_and_browser import browser

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


def test_launch_excellence_home_guidance_is_present():
    home = read_text("templates/home.html")
    required = [
        'data-launch-excellence="home-start"',
        '<details class="v933-home-more" data-home-extras>',
        'class="v933-home-more-summary"',
        'data-launch-onboarding="first-run"',
        'Entiende NeMeSiS rápido',
        "section_header('Continuar'",
        'data-launch-continue="last-route"',
        'data-launch-last-match="true"',
        '/daily-briefing',
        '/evening-recap',
        '/activity-center',
    ]
    for snippet in required:
        assert snippet in home
    assert home.index('<summary class="v933-home-more-summary">') < home.index('data-launch-onboarding="first-run"')
    assert home.rstrip().endswith('{% endblock %}')
    assert '/player/101' not in home


@pytest.mark.parametrize("signed_in", [False, True])
@pytest.mark.parametrize("live_count", [0, 2])
@pytest.mark.parametrize("agenda_locked", [False, True])
def test_home_has_one_primary_action_without_repeating_it_in_the_access_strip(
    app_module, signed_in, live_count, agenda_locked,
):
    # Inspect the rendered branches, including the new idle/unknown agenda
    # states. Source-text splitting cannot distinguish nested Jinja conditions.
    user = {"id": "qa-home-actions", "role": "FREE", "membership": "FREE"} if signed_in else None
    data = {"sports_metrics": {"live_confirmed": live_count},
            "home_summary": {"storage_status": "database_locked" if agenda_locked else "available"}}
    with app_module.app.test_request_context("/"):
        dom = Structure(render_template("home.html", data=data, current_user=user,
                                        greeting={"label": "QA", "name": ""}))
    primary, = [node for node in dom.nodes if "data-home-primary-action" in node["attrs"]]
    secondary, = [node for node in dom.nodes if "data-home-secondary-actions" in node["attrs"]]
    primary_links = [node["attrs"]["href"] for node in dom.nodes if node["tag"] == "a" and primary in node["parents"]]
    secondary_links = [node["attrs"]["href"] for node in dom.nodes if node["tag"] == "a" and secondary in node["parents"]]
    confirmed_live = bool(live_count and not agenda_locked)
    expected_primary = ("/directo" if confirmed_live else "/calendario") if signed_in else "/registro"
    assert primary_links == [expected_primary]
    expected_secondary = ["/favoritos", "/picks"]
    if expected_primary != "/calendario":
        expected_secondary.insert(0, "/calendario")
    if confirmed_live and not signed_in:
        expected_secondary.insert(0, "/directo")
    assert secondary_links == expected_secondary
    assert not set(primary_links) & set(secondary_links)
    assert len(secondary_links) == len(set(secondary_links))
    assert "/calendario" in primary_links + secondary_links


@pytest.mark.parametrize("width", [320, 1440])
@pytest.mark.parametrize("signed_in,live_count,count", [(True, 0, 2), (True, 2, 3), (False, 2, 4)])
def test_home_access_strip_has_no_empty_columns(browser, app_module, width, signed_in, live_count, count):
    """Measure the real template/styles offline; this is component QA, not production."""
    user = {"id": "qa-home-actions", "role": "FREE", "membership": "FREE"} if signed_in else None
    with app_module.app.test_request_context("/"):
        html = render_template("home.html", data={"sports_metrics": {"live_confirmed": live_count}},
                               current_user=user, greeting={"label": "QA", "name": ""})
    styles = []
    for node in Structure(html).nodes:
        if node["tag"] == "link" and node["attrs"].get("rel") == "stylesheet":
            path = urlsplit(node["attrs"].get("href", "")).path
            if path.startswith("/static/"):
                styles.append((ROOT / path.lstrip("/")).read_text(encoding="utf-8"))
    # Use shipped CSS with the full server-rendered shell, suppressing scripts
    # and all network requests in this geometry-only check.
    html = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html)
    html = re.sub(r"<link\b[^>]*>", "", html)
    page = browser.new_page(viewport={"width": width, "height": 844})
    page.route("**/*", lambda route: route.abort())
    try:
        page.set_content(html)
        page.add_style_tag(content="\n".join(styles))
        nav = page.locator("[data-home-secondary-actions]")
        assert nav.is_visible()
        assert nav.locator("a").count() == count
        tracks = nav.evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ')")
        assert len(tracks) == count
        for link in nav.locator("a").all():
            assert link.is_visible()
            assert link.bounding_box()["height"] >= 44
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    finally:
        page.close()


def test_launch_excellence_client_js_is_local_and_safe():
    js = read_text("static/v937-product-client.js")
    required = [
        'nemesis.launch.recentRoutes.v1',
        'nemesis.launch.onboarding.dismissed.v1',
        'allowedRoutePrefixes',
        'data-launch-onboarding-dismiss',
        'data-launch-last-match',
        'homeExtras.open = true',
        'homeExtras.open = false',
    ]
    for snippet in required:
        assert snippet in js
    forbidden = ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', '/api/admin', 'stripe']
    lowered = js.lower()
    for snippet in forbidden:
        assert snippet.lower() not in lowered


def test_launch_excellence_css_accessibility_and_mobile_rules_exist():
    css = read_text("static/v933-product.css")
    required = [
        'Launch Excellence Sprint 01',
        '.v933-launch-start-strip',
        '.v933-launch-onboarding',
        '.v933-launch-continuity-grid',
        'min-height: 44px',
        'prefers-reduced-motion: reduce',
        'touch-action: manipulation',
    ]
    for snippet in required:
        assert snippet in css


def test_home_disclosure_visual_rules_are_scoped_to_the_home_only():
    css = read_text("static/home-league-disclosure.css")
    assert 'details.v933-home-more[data-home-extras] > summary' in css
    assert 'details[data-home-extras][open] .home-more-chevron' in css
    assert 'body.ns-app .ns16-home .v933-match-teams strong' in css
    assert '.v933-home-more > summary' not in css


def test_launch_excellence_roadmap_and_reports_are_registered():
    roadmap = read_text("engines/project_operating_system_engine.py")
    assert 'Launch Excellence Sprint 01' in roadmap
    assert 'reports/LAUNCH_EXCELLENCE_SPRINT_01_REPORT.md' in roadmap
    report_files = [
        'reports/LAUNCH_EXCELLENCE_SPRINT_01_REPORT.md',
        'reports/ONBOARDING_REVIEW_REPORT.md',
        'reports/UX_POLISH_REPORT.md',
        'reports/MOBILE_EXPERIENCE_REPORT.md',
        'reports/ACCESSIBILITY_REPORT.md',
    ]
    for file_name in report_files:
        assert (ROOT / file_name).is_file()


def test_launch_excellence_does_not_add_routes_or_runtime_version():
    app = read_text("app.py")
    assert 'launch-excellence' not in app
    assert 'LAUNCH_EXCELLENCE' not in app
    version = read_text("VERSION.txt")
    assert 'LAUNCH_EXCELLENCE' not in version
