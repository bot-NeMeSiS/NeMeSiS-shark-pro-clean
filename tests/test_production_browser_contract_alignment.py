"""Regression tests for the real release checker; all browser traffic is intercepted."""
from copy import deepcopy
from html import escape
import os
from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader
import pytest

from engines.canonical_assets import template_css_href
from tools.run_production_quality_browser_gate import (
    MOBILE_NAV, PUBLIC_NAV, _click_journey, _navigation_url_matches,
    _page_evidence, _stylesheet_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://release-qa.invalid"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
HREF = template_css_href((ROOT / "templates/base.html").read_text(encoding="utf-8"), VERSION)


@pytest.mark.parametrize("actual,target,expected", [
    (BASE+"/", "/", True),
    (BASE+"/calendario?lane=finished", "/calendario?lane=finished", True),
    (BASE+"/calendario?q=club&lane=finished", "/calendario?lane=finished&q=club", True),
    (BASE+"/calendario?lane=today", "/calendario?lane=finished", False),
    (BASE+"/calendario", "/calendario?lane=finished", False),
    (BASE+"/calendario?lane=finished&lane=today", "/calendario?lane=finished", False),
    (BASE+"/calendario?lane=finished&lane=finished", "/calendario?lane=finished", False),
    (BASE+"/calendario?lane=finished&unexpected=", "/calendario?lane=finished", False),
    (BASE+"/cliente-login", "/calendario?lane=finished", False),
    ("https://other.invalid/calendario?lane=finished", "/calendario?lane=finished", False),
    ("http://release-qa.invalid/calendario?lane=finished", "/calendario?lane=finished", False),
    ("https://user@release-qa.invalid/calendario?lane=finished", "/calendario?lane=finished", False),
    (BASE+"/calendario?lane=finished#other", "/calendario?lane=finished", False),
    ("https://[", "/", False),
    ("", "/", False),
])
def test_navigation_keeps_origin_and_calendar_lane(actual, target, expected):
    assert _navigation_url_matches(actual, target, BASE) is expected


def css_case():
    assert HREF, "The checked-out release must have a canonical stylesheet"
    markup = f'<link rel="stylesheet" href="{escape(HREF, quote=True)}">'
    metrics = {
        "stylesheetLinks": [{
            "href": BASE+HREF, "sheetLoaded": True, "disabled": False, "mediaMatches": True,
        }],
        "resources": [BASE+HREF],
        "stylesheetResponses": [{"url": BASE+HREF, "status": 200}],
    }
    return markup, metrics


def test_canonical_css_requires_actual_loaded_sheet():
    markup, metrics = css_case()
    before = deepcopy(metrics)
    evidence = _stylesheet_evidence(metrics, markup, BASE, VERSION, HREF)
    assert evidence["pass"] is True
    assert evidence["active_loaded_sheet"] is True
    assert evidence["version_matches"] is True
    assert evidence["http_delivery_verified"] is True
    assert evidence["http_statuses"] == [200]
    assert metrics == before


@pytest.mark.parametrize("case", [
    "old_file", "old_version", "old_suffix", "offsite", "duplicate",
    "comment_only", "disabled", "print_only", "resource_missing",
    "sheet_missing", "sheet_disabled", "media_inactive", "links_missing",
    "empty_version", "empty_expected_href", "http_404", "http_500",
    "http_missing", "http_wrong_resource", "http_conflicting",
])
def test_bad_or_unproven_stylesheet_never_passes(case):
    markup, metrics = css_case()
    version, expected = VERSION, HREF
    if case == "old_file":
        markup = markup.replace("product-system.css", "app.css")
    elif case == "old_version":
        markup = markup.replace(VERSION, "V000_OLD_RELEASE")
    elif case == "old_suffix":
        wrong = "/static/product-system.css?v="+VERSION+"-old-styles"
        markup = f'<link rel="stylesheet" href="{wrong}">'
        metrics["stylesheetLinks"][0]["href"] = BASE+wrong
        metrics["resources"] = [BASE+wrong]
        metrics["stylesheetResponses"][0]["url"] = BASE+wrong
    elif case == "offsite":
        markup = markup.replace(HREF, "https://other.invalid"+HREF)
    elif case == "duplicate":
        markup += markup
        metrics["stylesheetLinks"] *= 2
    elif case == "comment_only":
        markup = "<!--"+markup+"-->"
    elif case == "disabled":
        markup = markup.replace("<link", "<link disabled")
    elif case == "print_only":
        markup = markup.replace("<link", '<link media="print"')
    elif case == "resource_missing":
        metrics["resources"] = []
    elif case == "sheet_missing":
        metrics["stylesheetLinks"][0]["sheetLoaded"] = False
    elif case == "sheet_disabled":
        metrics["stylesheetLinks"][0]["disabled"] = True
    elif case == "media_inactive":
        metrics["stylesheetLinks"][0]["mediaMatches"] = False
    elif case == "links_missing":
        metrics["stylesheetLinks"] = []
    elif case == "http_404":
        metrics["stylesheetResponses"][0]["status"] = 404
    elif case == "http_500":
        metrics["stylesheetResponses"][0]["status"] = 500
    elif case == "http_missing":
        metrics["stylesheetResponses"] = []
    elif case == "http_wrong_resource":
        metrics["stylesheetResponses"][0]["url"] = BASE+"/static/unrelated.css"
    elif case == "http_conflicting":
        metrics["stylesheetResponses"].append({"url": BASE+HREF, "status": 404})
    elif case == "empty_version":
        version = ""
    elif case == "empty_expected_href":
        expected = ""
    assert _stylesheet_evidence(metrics, markup, BASE, version, expected)["pass"] is False


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        executable = os.environ.get("NEMESIS_QA_CHROMIUM")
        browser = pw.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        yield browser
        browser.close()


@pytest.mark.parametrize("zone,width", [("public-desktop", 1366), ("client-bottom", 390)])
def test_real_clicks_follow_the_canonical_navigation(browser, zone, width):
    # Links come from the application contract, independently of the checker's constants.
    navigation = Environment(loader=FileSystemLoader(ROOT/"templates")).get_template(
        "components/navigation_contracts.html"
    ).module
    entries = navigation.PUBLIC_LINKS if zone == "public-desktop" else navigation.PUBLIC_MOBILE_LINKS
    paths = PUBLIC_NAV if zone == "public-desktop" else MOBILE_NAV
    links = "".join(f'<a href="{escape(href, quote=True)}">{escape(label)}</a>' for label, href, _ in entries)
    html = f'<!doctype html><html><head><meta name="viewport" content="width=device-width"></head><body><nav data-nav-zone="{zone}">{links}</nav></body></html>'
    observed = []
    context = browser.new_context(viewport={"width": width, "height": 844}, service_workers="block")

    def intercept(route):
        observed.append((route.request.method, route.request.url))
        assert route.request.method == "GET"
        assert route.request.url.startswith(BASE+"/")
        route.fulfill(status=200, content_type="text/html", body=html)

    context.route("**/*", intercept)
    try:
        results = _click_journey(context.new_page(), BASE, zone, paths)
        assert len(results) == len(entries)
        assert all(item["pass"] for item in results), results
        calendar = next(item for item in results if item["href"].startswith("/calendario"))
        assert calendar["final_query"] == "lane=finished"
        assert calendar["final_url"] == BASE+"/calendario?lane=finished"
        assert observed
    finally:
        context.close()


@pytest.mark.parametrize("variant,expected", [
    ("current", True), ("old_file", False), ("old_suffix", False),
    ("missing", False), ("disabled", False), ("duplicate", False),
    ("print", False),
])
def test_browser_cssom_and_resource_evidence(browser, variant, expected):
    href = HREF
    if variant == "old_file":
        href = HREF.replace("product-system.css", "app.css")
    elif variant == "old_suffix":
        href = "/static/product-system.css?v="+VERSION+"-old-styles"
    extra = ' disabled' if variant == "disabled" else (' media="print"' if variant == "print" else "")
    link = f'<link rel="stylesheet" href="{escape(href, quote=True)}"{extra}>'
    if variant == "duplicate":
        link += link
    html = '<!doctype html><html><head>'+link+'</head><body data-v933-surface="public"><h1>SIMULATED_QA</h1></body></html>'
    context = browser.new_context(service_workers="block")

    def intercept(route):
        assert route.request.method == "GET"
        assert route.request.url.startswith(BASE+"/")
        if urlsplit(route.request.url).path.startswith("/static/"):
            route.fulfill(status=404 if variant == "missing" else 200,
                          content_type="text/css", body="body { font-family: sans-serif; }")
        else:
            route.fulfill(status=200, content_type="text/html", body=html)

    context.route("**/*", intercept)
    try:
        metrics = _page_evidence(context.new_page(), BASE, "/")
        assert metrics["cssVersioned"] is expected, metrics["css_contract"]
        assert metrics["http"] == 200
        if variant == "missing":
            assert metrics["css_contract"]["http_statuses"] == [404]
            assert metrics["css_contract"]["http_delivery_verified"] is False
        elif variant == "current":
            assert metrics["css_contract"]["http_statuses"] == [200]
            assert metrics["css_contract"]["http_delivery_verified"] is True
    finally:
        context.close()
