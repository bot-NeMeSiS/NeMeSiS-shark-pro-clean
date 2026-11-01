"""Real Chromium, wholly intercepted HTTP: no live account/provider/server."""
from copy import deepcopy
import os
import pytest

from tools import run_production_quality_browser_gate as gate

BASE = "https://read-only-qa.invalid"
CONTEXTS = ["public-desktop", "public-mobile", "admin-protection"]


@pytest.fixture
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        executable = os.environ.get("NEMESIS_QA_CHROMIUM")
        browser = p.chromium.launch(headless=True,
            **({"executable_path": executable} if executable else {}))
        yield browser
        browser.close()


@pytest.mark.parametrize("scope", CONTEXTS)
def test_browser_scripts_and_beacons_cannot_forward_writes(browser, monkeypatch, scope):
    from playwright.sync_api import Browser
    real_new_context = Browser.new_context
    reached_transport = []
    options = []

    def inert_transport(route):
        req = route.request
        reached_transport.append((req.method, req.url))
        assert req.method in {"GET", "HEAD"}, "A write bypassed the real read-only guard"
        route.fulfill(status=200, content_type="text/html", body="<h1>SIMULATED_QA</h1>")

    def new_context(self, **kwargs):
        options.append(dict(kwargs))
        context = real_new_context(self, **kwargs)
        context.route("**/*", inert_transport)
        return context

    monkeypatch.setattr(Browser, "new_context", new_context)
    names, blocks = [], {}
    context = gate._read_only_context(browser, BASE, scope, names, blocks)
    try:
        page = context.new_page()
        page.goto(BASE+"/", wait_until="domcontentloaded")
        replies = page.evaluate("""async () => {
          const call=async (url, method) => {
            try { const r=await fetch(url,{method});return r.status; }
            catch (_) { return 'blocked'; }
          };
          const outcomes=[];
          for (const method of ['POST','PUT','PATCH','DELETE','OPTIONS'])
            outcomes.push(await call('/unexpected-write',method));
          outcomes.push(await call('/api/growth/funnel-event','POST'));
          outcomes.push(await call('/api/growth/funnel-event?extra=1','POST'));
          outcomes.push(await call('/read-head','HEAD'));
          navigator.sendBeacon('/beacon-write','SIMULATED_QA');
          return outcomes;
        }""")
        page.wait_for_function("performance.getEntriesByType('resource').some(e=>e.name.endsWith('/beacon-write'))")
        assert replies == ["blocked"]*5+[204,"blocked",200]
        assert names == [scope]
        assert options[0]["service_workers"] == "block"
        assert len(blocks) == 8
        assert all(row["network_forwarded"] is False for row in blocks.values())
        assert sum(row["disposition"] == "LOCAL_TELEMETRY_204" for row in blocks.values()) == 1
        assert {method for method, _ in reached_transport} == {"GET", "HEAD"}
        assert all("write" not in url and "funnel-event" not in url for _, url in reached_transport)
        proof = gate._read_only_evidence(CONTEXTS, blocks)
        assert proof["unexpected_write_attempts"] == 7
        assert proof["telemetry_delivery"] == "NOT_TESTED_QA_SUPPRESSED"
        assert gate._read_only_check({"read_only_browser": proof}) == "FAIL"
    finally:
        context.close()


@pytest.mark.parametrize("alter", ["missing", "context", "worker", "outbound", "bool_count", "contract"])
def test_missing_or_incomplete_guard_can_never_certify_read_only(alter):
    proof = gate._read_only_evidence(CONTEXTS, {})
    evidence = {"read_only_browser": proof}
    if alter == "missing":
        evidence.clear()
    elif alter == "context":
        proof["guarded_contexts"] = CONTEXTS[:-1]
    elif alter == "worker":
        proof["service_workers"] = "allow"
    elif alter == "outbound":
        proof["outbound_write_requests"] = 1
    elif alter == "bool_count":
        proof["outbound_write_requests"] = False
    elif alter == "contract":
        proof["contract"] = "UNVERIFIED"
    before = deepcopy(evidence)
    report = gate.build_post_deploy_result(expected_sha="a"*40, actual_sha="a"*40,
        checks={"health":"PASS", "read_only_browser":"PASS"}, evidence=evidence)
    assert report["result"] == "BLOCKED"
    assert report["read_only"] is False
    assert report["production_mutations"] is None
    assert report["checks"]["read_only_browser"] == "NOT_RUN"
    assert evidence == before


@pytest.mark.parametrize("change", ["counter", "forwarded", "read_method", "unknown_context", "bad_row", "bad_proof"])
def test_inconsistent_receipts_cannot_turn_an_unexpected_write_into_a_pass(change):
    row={"context":CONTEXTS[0],"method":"POST","url":BASE+"/unexpected",
         "network_forwarded":False,"disposition":"ABORTED_UNEXPECTED_WRITE"}
    proof=gate._read_only_evidence(CONTEXTS,{object():row})
    if change == "counter": proof["unexpected_write_attempts"]=0
    elif change == "forwarded": proof["intercepted_writes"][0]["network_forwarded"]=True
    elif change == "read_method": proof["intercepted_writes"][0]["method"]="GET"
    elif change == "unknown_context": proof["intercepted_writes"][0]["context"]="unguarded"
    elif change == "bad_row": proof["intercepted_writes"]=[None]
    elif change == "bad_proof": proof="unverified"
    assert gate._read_only_check({"read_only_browser":proof}) == "NOT_RUN"


def test_navigation_diagnostics_use_real_browser_timing_and_response_headers(browser):
    context=browser.new_context(service_workers="block")
    def inert(route):
        assert route.request.method == "GET" and route.request.url.startswith(BASE+"/")
        route.fulfill(status=200,content_type="text/html",body="<h1>SIMULATED_QA</h1>",
            headers={"server-timing":"app;dur=123.4, calendar_context;dur=34.5"})
    context.route("**/*",inert)
    try:
        evidence=gate._page_evidence(context.new_page(),BASE,"/calendar")
        assert evidence["navigationTiming"]["name"] == BASE+"/calendar"
        assert evidence["timing_document_matches_sample"] is True
        assert evidence["navigationTiming"]["responseStart"] > 0
        assert evidence["navigationTiming"]["responseEnd"] >= evidence["navigationTiming"]["responseStart"]
        assert evidence["response_timing_headers"]["server-timing"] == "app;dur=123.4, calendar_context;dur=34.5"
        timings={row["name"]:row["duration"] for row in evidence["navigationTiming"]["serverTiming"]}
        assert timings == {"app":123.4,"calendar_context":34.5}
    finally:
        context.close()


def test_all_actual_collector_contexts_use_guard_and_local_telemetry_is_labelled(monkeypatch, tmp_path):
    # Reuse the complete original collector regression, adding a real script
    # that attempts a write on every page, and intercepting only below the guard.
    from tests import test_production_resource_fallback_browser as original
    from playwright.sync_api import Route
    real_fulfill = Route.fulfill
    real_build = gate.build_post_deploy_result
    captured = []

    def fulfill(self, **kwargs):
        if kwargs.get("content_type") == "text/html" and isinstance(kwargs.get("body"), str):
            kwargs["body"] += "<script>fetch('/api/growth/funnel-event',{method:'POST'}).catch(()=>{});</script>"
        return real_fulfill(self, **kwargs)

    def capture(**kwargs):
        report = real_build(**kwargs)
        captured.append(report)
        return report

    monkeypatch.setattr(Route, "fulfill", fulfill)
    monkeypatch.setattr(gate, "build_post_deploy_result", capture)
    original.test_full_collector_preserves_each_navigation_and_reports_degradation(monkeypatch, tmp_path)
    assert len(captured) == 1
    report = captured[0]
    proof = report["evidence"]["read_only_browser"]
    assert proof["guarded_contexts"] == CONTEXTS
    assert proof["unexpected_write_attempts"] == 0
    assert len(proof["intercepted_writes"]) > 3
    assert report["checks"]["read_only_browser"] == "PASS"
    responses = [row for row in report["evidence"]["resource_responses"] if row["method"] == "POST"]
    assert responses and all(row["qa_local_response"] and row["network_forwarded"] is False
                             and row["status"] == 204 for row in responses)
    for page in report["evidence"]["pages"]:
        assert page["navigationTiming"]["name"] == BASE.replace("read-only-qa", "sentinel-qa")+page["path"]
        assert page["navigation_scope"]["document_url"].endswith(page["path"])
        assert page["elapsed_ms"] >= 0
        assert "response_timing_headers" in page
