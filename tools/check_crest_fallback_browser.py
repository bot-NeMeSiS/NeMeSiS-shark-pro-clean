"""Real DOM regression for shared crest consumers, with synthetic data and no network."""
from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path

from jinja2 import Environment, nodes
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = [("components/v933_ui.html", "team_logo"), ("components/v928_ui.html", "crest"), ("partials/team_identity.html", "crest")]
CASES = {"valid": "/valid.png", "404": "/404.png", "blocked": "/blocked.png", "timeout": "/timeout.png",
         "empty": "", "malformed": "http://[", "missing": None}


def render_crest(path: str, name: str, source: str | None) -> str:
    env = Environment(autoescape=True)
    env.filters["team_crest_url"] = lambda value: ""
    ast = env.parse((ROOT / "templates" / path).read_text(encoding="utf-8"))
    macro = next(item for item in ast.find_all(nodes.Macro) if item.name == name)
    template = env.from_string(nodes.Template([macro]))
    if name == "team_logo":
        return template.module.team_logo("QA United", source)
    if path.startswith("partials/"):
        return template.module.crest({"crest_url": source, "initials": "QA"}, "QA United")
    return template.module.crest({"name": "QA United", "logo": source})


def run(output: Path, script: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "#29ba73").save(buffer, format="PNG")
    script_text = (script or ROOT / "static/v937-product-client.js").read_text(encoding="utf-8")
    css = "\n".join((ROOT / "static" / name).read_text(encoding="utf-8") for name in
        ["app.css", "v928-canonical.css", "v933_design_tokens.css", "v933-product.css"])
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width, height in [(1366, 768), (390, 844)]:
            context = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            cards = []
            for variant, (path, macro) in enumerate(VARIANTS):
                for case, source in CASES.items():
                    cards.append(f'<div data-case="{variant}-{case}" style="padding:12px">' + str(render_crest(path, macro, source)) + '</div>')
            html = '<!doctype html><meta charset="utf-8"><style>' + css + '</style><body class="ns-app" data-v820-shell="true"><main>' + ''.join(cards) + '</main></body>'
            def route(request):
                url = request.request.url
                if url == "https://qa.example.invalid/":
                    request.fulfill(status=200, content_type="text/html", body=html)
                elif url == "https://qa.example.invalid/valid.png":
                    request.fulfill(status=200, content_type="image/png", body=buffer.getvalue())
                elif url.endswith('/404.png'):
                    request.fulfill(status=404, body="SIMULATED_QA")
                else:
                    request.abort("timedout" if url.endswith('/timeout.png') else "blockedbyclient")
            page.route("**/*", route)
            page.goto("https://qa.example.invalid/", wait_until="networkidle")
            # Loading the real executor late reproduces cached/error-before-listener cases.
            page.add_script_tag(content=script_text)
            if page.locator('[data-case]').count() != len(cards):
                (output/'fixture-error.html').write_text(page.content(),encoding='utf-8')
                raise AssertionError('Fixture markup missing: ' + page.url)
            for variant, _ in enumerate(VARIANTS):
                for case in CASES:
                    node = page.locator(f'[data-case="{variant}-{case}"]')
                    node.scroll_into_view_if_needed()
                    expected = 'loaded' if case == 'valid' else 'fallback'
                    try:
                        page.wait_for_function("([selector, state]) => document.querySelector(selector).firstElementChild.dataset.crestState === state",
                            arg=[f'[data-case="{variant}-{case}"]', expected], timeout=500)
                    except Exception:
                        pass
                    data = node.evaluate("""node => {
                        const box=node.firstElementChild, img=box.querySelector('img'), fb=box.querySelector('em');
                        const visible=n=>Boolean(n && n.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}));
                        const rect=box.getBoundingClientRect();
                        return {state:box.dataset.crestState, image:visible(img), fallback:visible(fb),
                            broken:visible(img)&&img.complete&&img.naturalWidth===0, width:rect.width,height:rect.height};
                    }""")
                    passed = data.get('state') == expected and data['image'] == (case == 'valid') and data['fallback'] == (case != 'valid') and not data['broken'] and data['width'] > 0 and data['height'] > 0
                    results.append({'viewport':[width,height], 'variant':variant, 'case':case,'pass':passed,'observed':data})
            # New consumers and URL corrections use the same executor, not a page-specific handler.
            page.evaluate("""() => {const node=document.createElement('div');node.id='dynamic-crest';node.innerHTML='<span class="crest" data-fallback="QA"><img src="/blocked.png"><em>QA</em></span>';document.body.appendChild(node)}""")
            recovered = False
            try:
                page.wait_for_function("document.querySelector('#dynamic-crest span').dataset.crestState === 'fallback'", timeout=1000)
                before = page.locator('#dynamic-crest span').bounding_box()
                page.locator('#dynamic-crest img').evaluate("img => img.src='/valid.png'")
                page.wait_for_function("document.querySelector('#dynamic-crest span').dataset.crestState === 'loaded'", timeout=1000)
                after = page.locator('#dynamic-crest span').bounding_box()
                recovered = all(abs(before[k]-after[k]) <= 1 for k in ('width','height'))
            except Exception:
                pass
            results.append({'viewport':[width,height], 'case':'dynamic_failure_recovery', 'pass': recovered})
            page.screenshot(path=str(output/f'crests-{width}.png'))
            assert not errors, errors
            context.close()
        browser.close()
    result={'scope':'SIMULATED_QA','external_requests':0,'total':len(results),'passed':sum(x['pass'] for x in results),'cases':results}
    (output/'crest-browser.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--script',type=Path)
    args=parser.parse_args()
    result=run(args.output_dir,args.script)
    print(json.dumps({key:value for key,value in result.items() if key!='cases'}))
    raise SystemExit(0 if result['total']==result['passed'] else 1)
