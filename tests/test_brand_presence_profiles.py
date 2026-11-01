"""Shipped CSS/assets on an isolated composition, not authenticated App QA.

All resources come from this checkout. No Flask, DB, providers or production.
"""
from pathlib import Path
import base64
import re
import hashlib
import json
import os
import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

PROFILES = [
    ('/calendar', False, (.64, .16), (.56, .12)),
    ('/calendario', False, (.64, .16), (.56, .12)),
    ('/directo', False, (.64, .16), (.56, .12)),
    ('/picks', False, (.64, .16), (.56, .12)),
    ('/', False, (.72, .30), (.62, .22)),
    ('/app', False, (.72, .30), (.62, .22)),
    ('/shark', False, (.68, .34), (.60, .26)),
    ('/cliente-login', False, (.70, .34), (.60, .34)),
    ('/login', False, (.70, .34), (.60, .34)),
    ('/registro', False, (.70, .34), (.60, .34)),
    ('/admin/control-center', True, (.28, .06), (.28, .06)),
    # Existing admin-login cascade; intentionally not redesigned.
    ('/admin-login', True, (.28, .24), (.28, .06)),
]


def composition(path, admin, tier='free'):
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/static/product-system.css">
<link rel="stylesheet" href="/static/v1000-client-refinement.css?v=brand-presence-1">
<style>
body.ns-app[data-ns-design="core"] main.preview{{position:relative;z-index:2;width:calc(100% - 40px)!important;max-width:560px!important;min-width:0!important;padding:0!important;margin:30px 20px!important;font-family:Arial,sans-serif}}
.preview .preview-note{{font-size:12px;line-height:1.5;color:#b5c8dc;margin:10px 0 20px}}
.preview .preview-card{{padding:20px;margin:15px 0}}
.preview label{{display:grid;gap:8px;margin:12px 0}}
.preview input{{width:100%;min-height:44px;padding:10px}}
.preview button{{min-height:44px;padding:10px 18px}}
.preview h1{{font-size:28px;line-height:1.2;margin:20px 0 10px}}
.preview .preview-logo{{display:block;width:72px;height:72px}}
</style></head><body class="ns-app ns-tier-{tier}{' ns-admin' if admin else ''}" data-ns-design="core" data-ns-route="{path}">
<div class="ns-brand-scene" data-brand-scene="approved-family-20261023" aria-hidden="true"></div>
<main class="preview"><img class="preview-logo" src="/static/img/approved-identity/nemesis-approved-mark-128.webp" alt="NeMeSiS">
<p class="preview-note">REVISIÓN DE COMPOSICIÓN · CSS Y ARTE REALES<br>No es una captura de la aplicación conectada ni de producción.</p>
<h1>NeMeSiS SHARK PRO</h1><p>Identidad marina. Contenido en primer plano.</p>
<section class="v933-panel preview-card"><h2>Superficie de lectura</h2><p>El fondo conserva su presencia sin transparentar las tarjetas.</p>
<label>Control de muestra<input type="text" value="Texto legible" aria-label="Control de muestra"></label>
<button type="button" id="preview-control">Control de muestra</button></section></main>
</body></html>'''


def asset_uri(root, filename):
    data=(root/'static/img/approved-identity'/filename).read_bytes()
    return 'data:image/webp;base64,'+base64.b64encode(data).decode('ascii')


def mount(page, root, path, admin, tier='free'):
    # DOM/CSS-only rendering works without any HTTP access or browser-policy
    # changes. Inline only the already approved image bytes; source URLs and
    # real-route HTTP behavior remain covered by the existing App browser QA.
    blocked, errors = [], []
    root=root.resolve()
    def offline_css(text):
        pattern=r"url\([\"']?(/static/img/approved-identity/([^?\"'()]+)(?:\?[^\"'()]*)?)[\"']?\)"
        return re.sub(pattern, lambda match: 'url("'+asset_uri(root,match.group(2))+'")', text)
    html=composition(path,admin,tier)
    for file in ('product-system.css','v1000-client-refinement.css'):
        pattern=r'<link rel="stylesheet" href="/static/'+re.escape(file)+r'[^"]*">'
        style=offline_css((root/'static'/file).read_text(encoding='utf-8'))
        html=re.sub(pattern,lambda _match:'<style>'+style+'</style>',html)
    html=html.replace('/static/img/approved-identity/nemesis-approved-mark-128.webp',
                      asset_uri(root,'nemesis-approved-mark-128.webp'))
    page.route('**/*',lambda route:(blocked.append(route.request.url),route.abort()))
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.set_content(html,wait_until='load')
    page.locator('.ns-brand-scene').wait_for(state='visible')
    decoded=page.evaluate(r"""async () => {
      const scene=document.querySelector('.ns-brand-scene');
      const urls=['::before','::after'].flatMap(p=>[...getComputedStyle(scene,p).backgroundImage.matchAll(/url\(["']?(.*?)["']?\)/g)].map(m=>m[1]));
      await Promise.all(urls.map(url=>{const image=new Image();image.src=url;return image.decode();}));
      await Promise.all([...document.images].map(image=>image.decode()));
      await document.fonts.ready;
      return urls.length;
    }""")
    assert decoded==2
    assert blocked==[] and errors==[]
    return blocked,errors


def metrics(page):
    return page.evaluate('''() => {
      const scene=document.querySelector('.ns-brand-scene');
      const before=getComputedStyle(scene,'::before'), after=getComputedStyle(scene,'::after');
      const card=document.querySelector('.preview-card'),control=document.querySelector('input');
      const alpha=el=>{const c=document.createElement('canvas');c.width=c.height=1;const x=c.getContext('2d');x.fillStyle=getComputedStyle(el).backgroundColor;x.fillRect(0,0,1,1);return x.getImageData(0,0,1,1).data[3]/255;};
      return {ocean:Number(before.opacity),shark:Number(after.opacity),
        oceanImage:before.backgroundImage,sharkImage:after.backgroundImage,
        sceneCount:document.querySelectorAll('.ns-brand-scene').length,
        pointerEvents:getComputedStyle(scene).pointerEvents,position:getComputedStyle(scene).position,
        animation:getComputedStyle(scene).animationName,
        legacyBefore:getComputedStyle(document.body,'::before').content,
        legacyAfter:getComputedStyle(document.body,'::after').content,
        cardAlpha:alpha(card),controlAlpha:alpha(control),
        cardOpacity:Number(getComputedStyle(card).opacity),controlOpacity:Number(getComputedStyle(control).opacity),
        overflow:document.documentElement.scrollWidth>innerWidth+1,
        clipped:[card,control,document.querySelector('h1')].some(el=>{const r=el.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}),
        sceneHidden:getComputedStyle(scene).display==='none'};
    }''')


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as pw:
        options = dict(headless=True, args=['--host-resolver-rules=MAP * ~NOTFOUND', '--disable-background-networking'])
        if os.getenv('NEMESIS_QA_CHROMIUM'):
            options['executable_path'] = os.environ['NEMESIS_QA_CHROMIUM']
        b = pw.chromium.launch(**options)
        yield b
        b.close()


@pytest.mark.parametrize('width,height', [(320,740),(390,844),(768,900),(1440,900)])
@pytest.mark.parametrize('path,admin,desktop,mobile', PROFILES)
def test_scene_profiles_preserve_reading_controls_and_accessibility(browser,width,height,path,admin,desktop,mobile):
    context = browser.new_context(viewport=dict(width=width,height=height), service_workers='block', reduced_motion='reduce')
    page = context.new_page()
    try:
        blocked, errors = mount(page, ROOT, path, admin)
        actual = metrics(page)
        assert (actual['ocean'], actual['shark']) == (mobile if width < 768 else desktop)
        assert asset_uri(ROOT,'nemesis-approved-ocean-'+('768' if width<768 else '1600')+'.webp') in actual['oceanImage']
        assert asset_uri(ROOT,'nemesis-approved-wireframe-'+('480' if width<768 else '960')+'.webp') in actual['sharkImage']
        assert actual['sceneCount'] == 1
        assert actual['pointerEvents'] == 'none' and actual['position'] == 'fixed'
        assert actual['animation'] == 'none'
        assert actual['legacyBefore'] == 'none' and actual['legacyAfter'] == 'none'
        assert actual['cardAlpha'] == actual['controlAlpha'] == 1
        assert actual['cardOpacity'] == actual['controlOpacity'] == 1
        assert actual['overflow'] is False and actual['clipped'] is False
        page.locator('#preview-control').click(trial=True)
        cdp = context.new_cdp_session(page)
        for name,value in [('prefers-contrast','more'),('prefers-reduced-transparency','reduce'),('forced-colors','active')]:
            cdp.send('Emulation.setEmulatedMedia', {'features':[{'name':name,'value':value}]})
            assert metrics(page)['sceneHidden'], (name,path,width)
        cdp.send('Emulation.setEmulatedMedia', {'features':[]})
        assert not metrics(page)['sceneHidden']
        assert blocked == [] and errors == []
    finally:
        context.close()


@pytest.mark.parametrize('tier', ['free','pro','elite','eliteplus'])
def test_visual_tier_does_not_change_functional_scene_policy(browser,tier):
    context=browser.new_context(viewport=dict(width=390,height=844),service_workers='block')
    try:
        page=context.new_page();mount(page,ROOT,'/app',False,tier)
        assert metrics(page)['shark']==.22
    finally:
        context.close()


def test_approved_artwork_is_not_regenerated():
    folder=ROOT/'static/img/approved-identity'
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for asset in manifest['assets']:
        data=(folder/asset['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==asset['sha256']
        assert len(data)==asset['bytes']


def test_refinement_cache_version_is_explicit_and_stylesheet_is_unique():
    base=(ROOT/'templates/base.html').read_text(encoding='utf-8')
    assert base.count("filename='v1000-client-refinement.css'")==1
    assert "filename='v1000-client-refinement.css') }}?v={{ app_version }}-brand-presence-1" in base


def test_change_communication_is_preserved_for_codex():
    agents=(ROOT/'AGENTS.md').read_text(encoding='utf-8')
    log=(ROOT/'docs/VISUAL_CHANGELOG.md').read_text(encoding='utf-8')
    assert 'Antes de editar' in agents and 'Después' in agents
    assert 'docs/CHANGE_COMMUNICATION.md' in agents
    assert 'VIS-2026-10-29-01' in log and 'sin despliegue' in log
