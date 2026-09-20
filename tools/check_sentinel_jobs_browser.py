"""Real loopback Flask browser checks; no mocked transport or provider calls."""
import json
import os
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/local_dev/sentinel-browser"
OUT.mkdir(exist_ok=True)
preview = json.loads((ROOT / "data/local_dev/sentinel-preview.json").read_text())
BASE = "http://127.0.0.1:" + str(preview["port"])
report = {"environment":"LOCAL_ONLY", "transport":"REAL_FLASK_HTTP", "observations":[], "external_blocked":[], "errors":[]}

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path=os.environ["NEMESIS_QA_CHROMIUM"])
    context = browser.new_context(viewport={"width":1366,"height":900}, timezone_id="Asia/Tokyo")
    def network(route):
        if route.request.url.startswith(BASE + "/"):
            route.continue_()
        else:
            report["external_blocked"].append(route.request.url.split("?")[0])
            route.abort()
    context.route("**/*", network)
    context.request.get(preview["url"], max_redirects=0)
    page = context.new_page()
    page.on("pageerror", lambda error: report["errors"].append(str(error)))
    page.goto(BASE + "/admin/sentinel-issues", wait_until="domcontentloaded")
    button = page.locator("[data-request-review]")
    button.wait_for()
    page.wait_for_function("!document.querySelector('[data-request-review]').disabled")
    before = context.request.get(BASE + "/api/admin/sentinel/jobs").json()["jobs"]
    with page.expect_response(lambda r: r.url == BASE + '/api/admin/sentinel/jobs' and r.request.method == 'POST') as submitted:
        button.click()
    accepted = submitted.value.json()
    requested_id = accepted['job']['id']
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        job = context.request.get(BASE + "/api/admin/sentinel/jobs/" + requested_id).json()["job"]
        if job["state"] in ("COMPLETED","FAILED","INTERRUPTED"):
            break
        page.wait_for_timeout(200)
    assert job["state"] == "COMPLETED", job
    assert job["attempt"] == 1
    report["job"] = job
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('[data-job-detail]').textContent.includes('Revisión terminada')")
    second = context.new_page()
    second.goto(BASE + "/admin/sentinel-issues", wait_until="domcontentloaded")
    second.wait_for_function("!document.querySelector('[data-request-review]').disabled")
    second.locator("[data-request-review]").click()
    second.wait_for_function("document.querySelector('[data-job-message]').textContent.includes('existente recuperado')")
    assert context.request.get(BASE + "/api/admin/sentinel/jobs").json()["jobs"][0]["id"] == job["id"]
    assert len(context.request.get(BASE + "/api/admin/sentinel/jobs").json()["jobs"]) == len(before) + (0 if accepted['reused'] else 1)
    search = page.locator('[data-v892-search]')
    search.fill('comprobacion conservada')
    page.wait_for_timeout(3500)
    assert search.input_value() == 'comprobacion conservada'
    assert search.evaluate('(el) => document.activeElement === el')
    search.fill('')
    for width in (1366, 390, 430):
        page.set_viewport_size({"width":width,"height":932 if width < 500 else 900})
        if width >= 1024:
            assert page.locator('.v927-admin-kpi-deck').bounding_box()['height'] < 220
            assert page.locator('[data-v892-filters]').bounding_box()['width'] >= 280
        page.locator('[data-sentinel-jobs]').scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
        panel_overflow = page.locator('[data-sentinel-jobs]').evaluate('(e) => e.scrollWidth > e.clientWidth + 1')
        name = f"sentinel-{width}.png"
        page.screenshot(path=str(OUT/name), full_page=False)
        report["observations"].append({"width":width,"document_overflow":overflow,"panel_overflow":panel_overflow,"screenshot":name})
        if panel_overflow:
            report["overflow_nodes"] = page.locator('[data-sentinel-jobs]').evaluate("e => [...e.querySelectorAll('*')].filter(n=>n.getBoundingClientRect().right > e.getBoundingClientRect().right+1).map(n=>({tag:n.tagName,cls:n.className,text:n.textContent.slice(0,80),width:n.getBoundingClientRect().width}))")
            (OUT / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        assert not panel_overflow, width
        assert not overflow, width
        assert not page.locator('.v927-admin-ops-grid .ns-table-wrap').evaluate('(e) => e.scrollWidth > e.clientWidth + 1')
        page.evaluate("document.activeElement.blur(); window.scrollTo({top:0, behavior:'instant'})")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT/f'sentinel-overview-{width}.png'), full_page=True)
    page.locator('[data-sentinel-jobs]').evaluate("""e => {
      const sizes = [...e.querySelectorAll('*')].map(n => [n, parseFloat(getComputedStyle(n).fontSize)]);
      sizes.forEach(([n,size]) => n.style.fontSize = (size * 2) + 'px');
      e.querySelector('h2').textContent = 'Revisión interna de superficies cliente y verificación de evidencias conservadas';
    }""")
    assert not page.locator('[data-sentinel-jobs]').evaluate('(e) => e.scrollWidth > e.clientWidth + 1')
    report['enlarged_text_200_percent'] = 'PASS_LOCAL_430'
    page.locator('[data-sentinel-jobs]').screenshot(path=str(OUT/'sentinel-430-text-200.png'))
    assert not report["errors"], report["errors"]
    context.close()
    browser.close()
(OUT / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"job_id":job["id"], "state":job["state"], "attempt":job["attempt"], "viewports":len(report["observations"]), "errors":report["errors"], "external_blocked_count":len(report["external_blocked"])}))
