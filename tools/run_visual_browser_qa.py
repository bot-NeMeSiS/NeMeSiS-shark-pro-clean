"""Capture the local premium system; no provider calls or simulated sports data."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    'public': ['/', '/precios', '/cliente-login', '/soporte'],
    'client': ['/app', '/calendario', '/directo', '/picks', '/shark', '/telegram',
               '/mi-cuenta', '/membresias', '/soporte', '/team/Real%20Madrid', '/match/unavailable'],
    'admin': ['/admin/dashboard', '/admin/matches', '/admin/picks',
              '/admin/telegram/command-center', '/admin/users', '/admin/memberships', '/admin/data-center'],
}
PROFILES = {'desktop': (1440, 900), 'laptop': (1024, 768), 'mobile': (390, 844), 'small-mobile': (320, 740)}
INSPECT = '''() => {
  const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  const navs = [...document.querySelectorAll('[data-nav-zone]')].filter(visible);
  const duplicateIds = [...document.querySelectorAll('[id]')].map(e=>e.id).filter((id,i,ids)=>ids.indexOf(id)!==i);
  return {
    overflow: document.documentElement.scrollWidth > innerWidth + 2,
    overflowing: [...document.querySelectorAll('main *')].filter(visible).filter(e=>e.getBoundingClientRect().right > innerWidth+2).slice(0,12).map(e=>e.tagName+'.'+e.className),
    navigation: navs.map(e=>e.dataset.navZone), duplicateIds,
    mainCount: document.querySelectorAll('main').length,
    styles: [...document.querySelectorAll('link[rel=stylesheet]')].map(e=>new URL(e.href).pathname),
    emptyStates: document.querySelectorAll('[data-empty-state]').length,
    heading: document.querySelector('main h1')?.textContent.trim(),
    plan: document.body.dataset.nsPlan,
    visibleButtons: [...document.querySelectorAll('button,a[role=button],.v933-action')].filter(visible).length
  };
}'''


def run(output, profiles=None):
    meta = json.loads((ROOT / 'data/local_dev/visual-preview.json').read_text())
    base = 'http://127.0.0.1:' + str(meta['port'])
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    routes_by_surface = {key: list(value) for key, value in ROUTES.items()}
    routes_by_surface['client'].extend('/match/' + value for value in meta.get('match_ids', [])[:3])
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for profile, size in PROFILES.items():
            if profiles and profile not in profiles:
                continue
            for surface, routes in routes_by_surface.items():
                context = browser.new_context(viewport=dict(zip(('width', 'height'), size)), reduced_motion='reduce', service_workers='block')
                # No external traffic, including provider endpoints or third-party images.
                context.route('**/*', lambda route: route.continue_() if urlparse(route.request.url).hostname in ('127.0.0.1', 'localhost', None) else route.abort())
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                if surface != 'public':
                    page.goto(base + '/local-safe/login/' + surface + '?token=' + meta['token'])
                for index, route in enumerate(routes):
                    errors.clear()
                    response = page.goto(base + route, wait_until='load', timeout=120000)
                    page.evaluate('document.fonts.ready')
                    filename = f'{profile}-{surface}-{index}.png'
                    page.screenshot(path=str(output / filename), full_page=True)
                    row = {'profile': profile, 'surface': surface, 'route': route,
                           'status': response.status, 'finalPath': urlparse(page.url).path,
                           'screenshot': filename, 'jsErrors': list(errors), **page.evaluate(INSPECT)}
                    rows.append(row)
                    print(json.dumps({k:row[k] for k in ('profile','surface','route','status','overflow','duplicateIds','jsErrors')},ensure_ascii=False),flush=True)
                if surface == 'client' and profile == 'mobile':
                    page.goto(base + '/app')
                    page.locator('.product-account-menu summary').click()
                    page.locator('.product-account-menu a[href="/soporte"]').click()
                    assert urlparse(page.url).path == '/soporte'
                    page.go_back()
                    page.locator('[data-nav-zone="client-bottom"] a[href="/calendario?lane=today"]').click()
                    assert urlparse(page.url).path == '/calendario'
                    page.locator('.v933-filter-tabs a[href="/directo"]').click()
                    assert urlparse(page.url).path == '/directo'
                    page.keyboard.press('Tab')
                context.close()
        browser.close()
    (output / 'observations.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    failures = [r for r in rows if r['overflow'] or r['duplicateIds'] or r['jsErrors']
                or r['status'] != (404 if r['route'] == '/match/unavailable' else 200) or r['mainCount'] != 1]
    print(f'{len(rows)} captures, {len(failures)} failures')
    return 1 if failures else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profiles', nargs='+', choices=PROFILES)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.profiles))
