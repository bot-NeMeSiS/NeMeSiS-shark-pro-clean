"""Exercise the real fallback script and Sentinel DOM evidence, entirely offline.

Every HTTP request is intercepted and fulfilled locally. Missing provider images
are synthetic; these tests do not certify or access production or provider APIs.
"""
from html import escape
import os
from pathlib import Path
import time

import pytest

from tools.run_production_quality_browser_gate import _image_failure_evidence, classify_browser_resources


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://sentinel-qa.invalid"


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        executable = os.environ.get("NEMESIS_QA_CHROMIUM")
        launched = playwright.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
        yield launched
        launched.close()


@pytest.mark.parametrize("case,expected", [
    ("api_sports_path", "PASS"), ("opaque_cdn_path", "PASS"),
    ("hidden_fallback", "FAIL"), ("overflowing_fallback", "FAIL"),
    ("hidden_component", "FAIL"), ("required_local_image", "FAIL"),
    ("unknown_component", "NOT_RUN"), ("brand_component", "FAIL"),
])
def test_missing_crest_requires_real_visible_component_fallback(browser, case, expected):
    url = "https://sports-media.invalid/football/teams/28553.png"
    if case == "opaque_cdn_path":
        url = "https://another-cdn.invalid/opaque/123.png"
    elif case == "required_local_image":
        url = BASE + "/static/required.png"
    css = """.v928-crest,.unrelated {display:inline-grid;width:36px;height:36px;place-items:center;}
      .v928-crest img,.unrelated img {width:36px;height:36px;}
      .v928-crest em,.unrelated em {grid-area:1/1;font:14px Arial;}
    """
    if case == "hidden_fallback":
        css += ".v928-crest em {display:none!important;}"
    elif case == "overflowing_fallback":
        css += ".v928-crest em {transform:translateX(80px);}"
    elif case == "hidden_component":
        css += ".v928-crest {display:none;}"
    component = "unrelated" if case == "unknown_component" else "v928-crest"
    if case == "brand_component":
        component += " ns-brand"
    markup = f'''<!doctype html><html><head><style>{css}</style></head><body>
      <h1>SIMULATED_QA: upstream image unavailable</h1>
      <span class="{component}" data-fallback="QA" title="Synthetic club">
        <img src="{escape(url, quote=True)}" alt="Synthetic club"><em>QA</em>
      </span><script src="/static/v937-product-client.js"></script></body></html>'''
    context = browser.new_context(service_workers="block")
    page = context.new_page()
    scope = {"page_id": 1, "document_id": 42, "document_url": BASE + "/live"}
    page._sentinel_resource_scope = scope
    responses, console, unexpected = [], [], []

    def intercept(route):
        request = route.request
        if request.method != "GET":
            unexpected.append((request.method, request.url))
            route.abort()
        elif request.url == BASE + "/live":
            route.fulfill(status=200, content_type="text/html", body=markup)
        elif request.url == BASE + "/static/v937-product-client.js":
            route.fulfill(status=200, content_type="text/javascript",
                body=(ROOT / "static/v937-product-client.js").read_text(encoding="utf-8"))
        elif request.url == url:
            route.fulfill(status=404, content_type="image/png", body="")
        else:
            unexpected.append((request.method, request.url))
            route.abort()

    context.route("**/*", intercept)
    page.on("response", lambda response: responses.append({
        "url": response.url, "status": response.status, "type": response.request.resource_type,
        "method": response.request.method, "received_at": time.perf_counter(), **scope,
    }))
    page.on("console", lambda message: console.append({
        "url": message.location.get("url", ""), "text": message.text,
        "emitted_at": time.perf_counter(), **scope,
    }) if message.type == "error" else None)
    try:
        page.goto(BASE + "/live", wait_until="networkidle")
        images = _image_failure_evidence(page)
        assert len(images) == 1
        if case in {"api_sports_path", "opaque_cdn_path"}:
            assert images[0]["kind"] == "TEAM_CREST"
            assert images[0]["kind_source"] == "DOM_COMPONENT"
            assert images[0]["fallback_working"] is True
            assert images[0]["image_visible"] is False
            assert images[0]["display"] == "none"
        result = classify_browser_resources(BASE, [], [], console, images, responses)
        assert result["subresources_and_fallbacks"] == expected, result
        assert any(message["url"] == url for message in console)
        if expected == "PASS":
            assert result["unexplained_console"] == []
            assert len(result["external_degradations"]) == 1
            assert result["external_degradations"][0]["severity"] == "WARNING"
        else:
            assert result["unexplained_console"]
            assert not result["external_degradations"]
        assert not unexpected, unexpected
    finally:
        context.close()


def test_full_collector_preserves_each_navigation_and_reports_degradation(monkeypatch, tmp_path):
    """Run the actual observer/navigation pipeline with intercepted HTTP only."""
    from playwright.sync_api import Browser
    from engines.canonical_assets import template_css_href
    from tools import run_production_quality_browser_gate as gate

    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    css_href = template_css_href((ROOT / "templates/base.html").read_text(encoding="utf-8"), version)
    sha = "a" * 40
    missing_url = "https://sports-media.invalid/football/teams/28553.png"
    replies = {
        "/api/runtime-version": {"git_commit_hint": sha, "sentinel_active_issues_count": 0},
        "/api/health": {"ok": True},
        "/api/realtime/sports": {"no_external_calls": True, "live": [], "counts": {"live": 0}},
    }
    monkeypatch.setattr(gate, "_request_json", lambda base, path: (replies[path], 200))
    nav = "".join('<nav data-nav-zone="'+zone+'">'+"".join(
        '<a href="'+escape(path, quote=True)+'">Ruta QA</a>' for path in paths)+'</nav>'
        for zone, paths in (("public-desktop", gate.PUBLIC_NAV), ("client-bottom", gate.MOBILE_NAV)))
    css = """a {display:inline-block;min-height:44px;} .v928-crest {display:inline-grid;width:36px;height:36px;place-items:center;}
      .v928-crest img {width:36px;height:36px;} .v928-crest em {grid-area:1/1;font:14px Arial;}
      .qa-brand {width:32px;height:32px;}"""
    unexpected = []
    real_new_context = Browser.new_context

    def intercept(route):
        request = route.request
        if request.method != "GET":
            unexpected.append((request.method, request.url))
            route.abort()
        elif request.url == missing_url:
            route.fulfill(status=404, content_type="image/png", body="")
        elif request.url == BASE + "/admin/dashboard":
            # The guard's auth branch is outside this collector regression.
            # An inert page sets its final path without following an HTTP
            # redirect, whose continuation can bypass Playwright routing.
            route.fulfill(status=200, content_type="text/html",
                body='<html><body>SIMULATED_QA<script>history.replaceState(null,"","/admin-login")</script></body></html>')
        elif request.url == BASE + css_href:
            route.fulfill(status=200, content_type="text/css", body=css)
        elif request.url == BASE + "/static/v937-product-client.js":
            route.fulfill(status=200, content_type="text/javascript",
                body=(ROOT / "static/v937-product-client.js").read_text(encoding="utf-8"))
        elif request.url in {BASE + "/static/nemesis-shark-brand.svg", BASE + "/static/nemesis-shark-atmosphere-v2.webp"}:
            route.fulfill(status=200, content_type="image/svg+xml",
                body='<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="blue"/></svg>')
        elif request.url.startswith(BASE + "/"):
            crest = ('<span class="v928-crest" data-fallback="QA" title="Synthetic club">'
                '<img src="'+missing_url+'" alt="Synthetic club"><em>QA</em></span>') if request.url in {BASE + "/live", BASE + "/directo"} else ""
            markup = ('<!doctype html><html><head><meta name="viewport" content="width=device-width">'
                '<link rel="stylesheet" href="'+escape(css_href, quote=True)+'"></head><body data-v933-surface="public">'
                '<h1>SIMULATED_QA</h1>'+nav+crest
                +'<img class="qa-brand" src="/static/nemesis-shark-brand.svg" alt="Synthetic brand">'
                +'<img class="qa-brand" src="/static/nemesis-shark-atmosphere-v2.webp" alt="Synthetic atmosphere">'
                +'<script src="/static/v937-product-client.js"></script></body></html>')
            route.fulfill(status=200, content_type="text/html", body=markup)
        else:
            unexpected.append((request.method, request.url))
            route.abort()

    def new_context(self, **kwargs):
        kwargs["service_workers"] = "block"
        context = real_new_context(self, **kwargs)
        context.route("**/*", intercept)
        return context

    monkeypatch.setattr(Browser, "new_context", new_context)
    report = gate.run_gate(BASE, sha, tmp_path, os.environ.get("NEMESIS_QA_CHROMIUM", ""))
    assert report["result"] == "PRODUCTION_CERTIFIED", report
    assert report["external_image_degradation_count"] >= 2
    resources = report["evidence"]["resource_classification"]
    assert not resources["unexplained_console"]
    assert {row["document_url"] for row in resources["external_degradations"]} >= {BASE + "/live", BASE + "/directo"}
    assert len({(row["page_id"], row["document_id"]) for row in resources["external_degradations"]}) >= 2
    assert report["production_mutations"] == 0
    assert not unexpected, unexpected
