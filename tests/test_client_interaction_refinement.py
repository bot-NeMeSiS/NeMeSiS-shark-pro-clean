"""Offline UI regressions: real scripts and media template, synthetic DOM/transport.

No provider requests, authentication, playback certificate or production DB.
The complete Flask navigation suite remains a separate CI requirement.
"""
from contextlib import contextmanager
import html
import os
from pathlib import Path
import re

from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape
import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_NAV = ROOT / 'static/app-navigation.js'
MEDIA = ROOT / 'static/postmatch-media.js'
YOUTUBE = 'https://www.youtube-nocookie.com/embed/SIMULATED_QA'
VIMEO = 'https://player.vimeo.com/video/123456'


@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        instance = pw.chromium.launch(headless=True, executable_path=os.environ.get('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path)
        yield instance
        instance.close()


@contextmanager
def page_context(browser, width=390, javascript=True):
    context = browser.new_context(viewport={'width':width, 'height':844}, java_script_enabled=javascript, service_workers='block')
    page = context.new_page()
    calls, errors = [], []
    def intercept(route):
        calls.append((route.request.method, route.request.url))
        # A deliberately unavailable third-party iframe. Never contact its host.
        route.fulfill(status=404, content_type='text/html', body='<p>SIMULATED_QA unavailable source</p>')
    context.route('**/*', intercept)
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        yield page, calls, errors
        assert not errors
    finally:
        context.close()


def wrap(body):
    styles = (ROOT/'static/product-system.css').read_text() + '\n' + (ROOT/'static/app-navigation.css').read_text()
    return '<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width"><style>'+styles+'</style></head><body class="ns-app">'+body+'</body></html>'


def navigation_fixture(modal=False, admin=False):
    entries = [('Historial','/historico','pronósticos rendimiento'), ('Pronósticos','/picks','picks análisis'), ('Resúmenes','/resumenes','highlights vídeos'), ('Cuenta','/mi-cuenta','plan')]
    links=''.join('<a href="'+href+'" data-explore-item data-explore-label="'+label+' '+alias+'"><span>'+label+'</span><span aria-hidden="true">→</span></a>' for label,href,alias in entries)
    fallback = '' if admin else '<a data-explore-match hidden href="/calendario"><span data-explore-match-query></span></a>'
    body='<div class="app-explore" data-app-explore><form data-explore-form><label for="qa-query">Buscar</label><div class="app-explore-search"><input id="qa-query" type="search" maxlength="90" data-explore-query><button type="submit">Buscar</button></div></form><p data-explore-count role="status"></p><div data-explore-group><div class="app-explore-links">'+links+'</div></div><p data-explore-empty hidden>Sin coincidencias</p>'+fallback+'<p data-explore-keyboard hidden>Flechas y Escape</p></div>'
    if modal:
        body='<button data-open-explore id="qa-opener">Explorar</button><dialog id="app-navigation-dialog" class="app-navigation-dialog" aria-label="Explorar"><form method="dialog"><button>Cerrar</button></form>'+body+'</dialog>'
    return body


def mount_nav(page, modal=False, admin=False):
    page.set_content(wrap(navigation_fixture(modal,admin)))
    page.add_script_tag(content="window.chosen=[]; window.inputEvents=0; window.sportsEvents=0; document.addEventListener('click',e=>{const a=e.target.closest('a[href]');if(a){e.preventDefault();window.chosen.push(a.getAttribute('href'));}},true); document.addEventListener('input',()=>window.inputEvents++); document.querySelector('input').addEventListener('sports:query',()=>window.sportsEvents++);")
    page.add_script_tag(content=APP_NAV.read_text())
    if modal:
        page.locator('#qa-opener').click()


@pytest.mark.parametrize('modal',[False,True])
@pytest.mark.parametrize('width',[320,390,1440])
def test_ambiguous_search_keeps_user_in_control(browser,modal,width):
    with page_context(browser,width) as (page,calls,errors):
        mount_nav(page,modal)
        page.locator('input').fill('pronó')
        page.locator('input').press('Enter')
        assert page.evaluate('window.chosen') == []
        assert page.locator('[data-explore-item]:visible').count() == 2
        assert page.locator('[data-explore-item]:visible').first.evaluate('(el)=>el===document.activeElement')
        if modal: assert page.locator('dialog').is_visible()
        page.locator('[href="/picks"]').press('Enter')
        assert page.evaluate('window.chosen') == ['/picks']
        assert not calls


@pytest.mark.parametrize('query,expected',[('Pronósticos','/picks'),('  PRONOSTICOS  ','/picks'),('highlights','/resumenes'),('zz & <equipo>','/calendario?lane=week&q=zz+%26+%3Cequipo%3E')])
def test_exact_unique_or_calendar_destination_is_preserved(browser,query,expected):
    with page_context(browser) as (page,calls,errors):
        mount_nav(page)
        page.locator('input').fill(query);page.locator('input').press('Enter')
        assert page.evaluate('window.chosen') == [expected]
        assert not calls


@pytest.mark.parametrize('admin',[False,True])
def test_clear_restores_all_sections_and_notifies_search_consumers(browser,admin):
    with page_context(browser) as (page,calls,errors):
        mount_nav(page,admin=admin)
        assert page.locator('[data-explore-clear]').is_hidden()
        page.locator('input').fill('highlights')
        assert page.locator('[data-explore-item]:visible').count()==1
        page.locator('[data-explore-clear]').click()
        assert page.locator('input').input_value()==''
        assert page.locator('input').evaluate('(el)=>el===document.activeElement')
        assert page.locator('[data-explore-item]:visible').count()==4
        assert page.locator('[data-explore-clear]').is_hidden()
        assert page.evaluate('window.sportsEvents')==1
        if not admin: assert page.locator('[data-explore-match]').is_hidden()
        assert not calls


def test_composition_and_unknown_admin_search_do_not_navigate(browser):
    with page_context(browser) as (page,calls,errors):
        mount_nav(page,admin=True)
        search=page.locator('input');search.fill('highlights')
        search.dispatch_event('compositionstart');search.press('Enter')
        assert page.evaluate('window.chosen')==[]
        search.dispatch_event('compositionend');search.press('Enter')
        assert page.evaluate('window.chosen')==['/resumenes']
        search.fill('unknown');search.press('Enter')
        assert page.evaluate('window.chosen')==['/resumenes']
        assert not page.locator('[data-explore-match]').count()
        assert not calls


def test_repeated_navigation_script_does_not_duplicate_controls_or_clicks(browser):
    with page_context(browser) as (page,calls,errors):
        mount_nav(page,modal=True)
        page.add_script_tag(content=APP_NAV.read_text())
        assert page.locator('[data-explore-clear]').count()==1
        page.locator('input').fill('highlights');page.locator('input').press('Enter')
        assert page.evaluate('window.chosen')==['/resumenes']
        assert not calls


def media_markup(url=YOUTUBE,can_embed=True):
    env=Environment(loader=ChoiceLoader([DictLoader({'base.html':'{% block content %}{% endblock %}'}),FileSystemLoader(ROOT/'templates')]),autoescape=select_autoescape(['html']))
    env.globals['url_for']=lambda endpoint,**kw:'/static/'+kw.get('filename','')
    data={'highlight':{'match_label':'Equipo QA vs Rival QA','title':'SIMULATED_QA','competition_label':'Liga de prueba','event_date_label':'11/10/2026','source_label':'SIMULATED_QA', 'client_status':'Vídeo autorizado', 'provider':'QA', 'can_embed':can_embed,'embed_url':url,'safe_url':'https://www.youtube.com/watch?v=SIMULATED_QA','match_url':'/match/simulated-qa'}}
    markup=env.get_template('highlight_detail.html').render(data=data)
    # Inject the exact production JS locally; never fetch a script over the network.
    return re.sub(r'<script\b[^>]*>.*?</script>','',markup,flags=re.S)


@pytest.mark.parametrize('width',[320,390,1440])
@pytest.mark.parametrize('url',[YOUTUBE,VIMEO])
def test_video_has_explicit_retry_close_and_focus_recovery(browser,width,url):
    with page_context(browser,width) as (page,calls,errors):
        page.set_content(wrap(media_markup(url)))
        page.add_script_tag(content=MEDIA.read_text())
        assert not calls and page.locator('iframe').count()==0
        start=page.locator('[data-video-activate]');start.click()
        page.wait_for_function('document.querySelector("iframe") !== null')
        assert page.locator('iframe').count()==1
        assert page.locator('iframe').get_attribute('src')==url
        assert page.locator('[data-video-close]').evaluate('(el)=>el===document.activeElement')
        assert start.is_disabled()
        assert start.get_attribute('aria-expanded')=='true'
        assert page.locator('[data-video-notice]').inner_text().startswith('La plataforma puede limitar')
        page.locator('[data-video-retry]').click()
        assert page.locator('iframe').count()==1
        page.locator('[data-video-close]').click()
        assert page.locator('iframe').count()==0
        assert start.is_enabled() and start.inner_text()=='Ver vídeo aquí'
        assert start.evaluate('(el)=>el===document.activeElement')
        assert start.get_attribute('aria-expanded')=='false'
        assert page.locator('[data-video-mount]').is_hidden()
        start.click();assert page.locator('[data-video-controls]').count()==1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
        assert all(method=='GET' and target==url for method,target in calls)
        out=os.environ.get('CLIENT_REFINEMENT_QA_OUTPUT')
        if out and url==YOUTUBE:
            folder=Path(out);folder.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(folder/f'video-controls-{width}-SIMULATED_QA.png'),full_page=True)


@pytest.mark.parametrize('bad',['javascript:alert(1)','http://www.youtube-nocookie.com/embed/QA','https://www.youtube-nocookie.com.evil.invalid/embed/QA','https://user@www.youtube-nocookie.com/embed/QA','https://player.vimeo.com/video/123?autoplay=1','https://www.youtube-nocookie.com/embed/QA#fragment','https://player.vimeo.com:444/video/123','not a url'])
def test_disallowed_players_cannot_be_opened(browser,bad):
    with page_context(browser) as (page,calls,errors):
        page.set_content(wrap(media_markup(bad)));page.add_script_tag(content=MEDIA.read_text())
        page.locator('[data-video-activate]').click()
        assert page.locator('iframe').count()==0
        assert page.locator('[data-video-controls]').count()==0
        assert page.locator('[data-video-activate]').is_enabled()
        assert not calls


def test_retry_revalidates_url_and_pagehide_releases_player(browser):
    with page_context(browser) as (page,calls,errors):
        page.set_content(wrap(media_markup()));page.add_script_tag(content=MEDIA.read_text())
        page.locator('[data-video-activate]').click()
        page.locator('[data-video-activate]').evaluate('(el)=>el.dataset.videoActivate="https://evil.invalid/embed/QA"')
        page.locator('[data-video-retry]').click()
        assert page.locator('iframe').get_attribute('src')==YOUTUBE
        assert 'No se puede cargar' in page.locator('[data-video-notice]').inner_text()
        page.evaluate('window.dispatchEvent(new Event("pagehide"))')
        assert page.locator('iframe').count()==0
        assert page.locator('[data-video-activate]').is_enabled()
        assert all(target==YOUTUBE for _,target in calls)


def test_duplicate_script_and_multiple_video_cards_stay_independent(browser):
    with page_context(browser) as (page,calls,errors):
        page.set_content(wrap(media_markup()+media_markup(VIMEO)))
        page.add_script_tag(content=MEDIA.read_text());page.add_script_tag(content=MEDIA.read_text())
        page.locator('[data-video-activate]').nth(0).click();page.locator('[data-video-activate]').nth(1).click()
        assert page.locator('iframe').count()==2
        assert page.locator('[data-video-controls]').count()==2
        page.locator('[data-video-close]').nth(0).click()
        assert page.locator('iframe').count()==1
        assert page.locator('iframe').get_attribute('src')==VIMEO
        assert all(target in (YOUTUBE,VIMEO) for _,target in calls)


@pytest.mark.parametrize('javascript',[False,True])
@pytest.mark.parametrize('can_embed',[False,True])
def test_original_source_and_back_navigation_remain_available(browser,javascript,can_embed):
    with page_context(browser,javascript=javascript) as (page,calls,errors):
        page.set_content(wrap(media_markup(can_embed=can_embed)))
        if javascript:page.add_script_tag(content=MEDIA.read_text())
        assert page.locator('iframe').count()==0
        assert page.locator('a[href="/resumenes"]').is_visible()
        assert page.locator('a[href="/historico"]').is_visible()
        assert page.locator('a[target="_blank"]').count()>=1
        assert all(link.get_attribute('rel')=='noopener noreferrer' for link in page.locator('a[target="_blank"]').all())
        assert not calls


def test_cache_versions_only_change_the_affected_assets():
    base=(ROOT/'templates/base.html').read_text()
    assert "filename='app-navigation.js') }}?v=3-intent" in base
    assert "-core-4-home-leagues" in base
    for name in ('match_detail.html','highlight_detail.html'):
        template=(ROOT/'templates'/name).read_text()
        assert template.count("filename='postmatch-media.js') }}?v=2-controls")==1
        assert "filename='postmatch-media.js') }}?v=1" not in template
