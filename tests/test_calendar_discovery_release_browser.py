"""Rendered Calendar components and simulated browser history, NOT live app navigation."""
from pathlib import Path
import os, json, re
import pytest
from test_calendar_discovery_release import render_calendar
from test_v940_calendar_sports_experience import _summary

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'static/v940-calendar.js').read_text()

@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path,headless=True)
        yield b
        b.close()


def mount(browser,app_module,*,width=390,language='es',query='',before='',run_script=True):
    html,_=render_calendar(app_module,query,language,summary=_summary(app_module,3))
    # The main Jinja template, main styles and scoped delivery styles; no providers.
    html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S|re.I)
    css='\n'.join((ROOT/'static'/name).read_text() for name in ('v930-canonical.css','v933_design_tokens.css','v933-product.css','calendar-discovery.css'))
    page=browser.new_page(viewport={'width':width,'height':844}, reduced_motion='reduce')
    attempted=[]; errors=[]
    page.route('**/*',lambda route:(attempted.append(route.request.url),route.abort()))
    page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.set_content('<!doctype html><html lang="'+language+'"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style><style>body{margin:0}main.qa-component{max-width:1050px;padding:12px;margin:auto}.qa-proof{padding:8px;color:#dceafd;font:13px system-ui}*{box-sizing:border-box}</style><body class="ns-app" data-v928-shell="true"><main class="qa-component"><p class="qa-proof">SIMULATED_QA · Componentes locales · No producción</p>'+html+'</main></body></html>')
    page.add_script_tag(content=(ROOT/'static/v930-icons.js').read_text())
    page.evaluate('document.dispatchEvent(new Event("DOMContentLoaded"))')
    if before:page.add_script_tag(content=before)
    if run_script:page.add_script_tag(content=SCRIPT)
    return page,attempted,errors

@pytest.mark.parametrize('width',[320,390,430,1366])
@pytest.mark.parametrize('language',['es','en','fr'])
def test_visible_search_native_form_and_touch_targets(browser,app_module,width,language,tmp_path):
    page,requests,errors=mount(browser,app_module,width=width,language=language)
    try:
        search=page.locator('[data-v940-calendar-search]'); form=page.locator('[data-v940-discovery-form]')
        assert search.is_visible()
        assert page.locator('.v940-calendar-advanced').get_attribute('open') is None
        submit=form.locator('button[type=submit]')
        assert submit.is_visible()
        for el in (search,submit,page.locator('.v940-calendar-advanced > summary')):
            assert el.bounding_box()['height']>=44
        for glyph in page.locator('.v940-calendar-advanced > summary .v933-icon, .v933-calendar-date-picker > summary .v933-icon').all():
            box=glyph.bounding_box()
            assert 16 <= box['width'] <= 24 and 16 <= box['height'] <= 24
        assert page.locator('[data-v940-calendar-context]').is_visible()
        assert page.locator('[data-v940-visible-count]').is_visible()
        page.locator('.v940-calendar-advanced > summary').click()
        for field in ('league','country'):
            sel=form.locator(f'select[name={field}]');assert sel.is_visible()
            assert sel.bounding_box()['height']>=44
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.locator('.v940-calendar-advanced > summary').click()
        search.fill('Club QA')
        assert page.locator('[data-v940-pending-filters]').is_visible()
        page.evaluate('''document.querySelector('[data-v940-discovery-form]').addEventListener('submit',e=>{e.preventDefault();window.qaSubmission=Object.fromEntries(new FormData(e.target));})''')
        search.press('Enter')
        assert page.evaluate('window.qaSubmission.q')=='Club QA'
        assert page.evaluate('window.qaSubmission.lane')=='today'
        assert not errors
        assert not any('/api/' in u for u in requests)
        if language=='es':
            search.fill('');page.evaluate('document.querySelector("[data-v940-discovery-form]").reset();document.activeElement.blur()')
            page.screenshot(path=str(tmp_path/f'calendar-discovery-{width}.png'),full_page=True)
    finally:page.close()


def test_pending_changes_and_collapsing_filters_never_change_the_result_collection(browser,app_module):
    page,_,errors=mount(browser,app_module,query='?lane=week&league=Retenida+QA&q=Club')
    try:
        original=page.locator('[data-v940-calendar-collection]').inner_html()
        originalCount=page.locator('[data-v940-visible-count]').inner_text()
        assert not page.locator('[data-v940-pending-filters]').is_visible()
        league=page.locator('select[name=league]')
        assert league.input_value()=='Retenida QA'
        league.select_option('')
        assert page.locator('[data-v940-pending-filters]').is_visible()
        page.locator('.v940-calendar-advanced summary').click()
        assert page.locator('[data-v940-calendar-collection]').inner_html()==original
        assert page.locator('[data-v940-visible-count]').inner_text()==originalCount
        page.locator('.v940-calendar-advanced summary').click()
        league.select_option('Retenida QA')
        assert not page.locator('[data-v940-pending-filters]').is_visible()
        assert not errors
    finally:page.close()


def test_return_to_filters_moves_keyboard_focus_without_erasing_input(browser,app_module):
    page,_,_=mount(browser,app_module)
    try:
        page.locator('[data-v940-calendar-search]').fill('Mi búsqueda QA')
        # Do not navigate away. This is the existing document's native fragment.
        link=page.locator('[data-v940-calendar-context] a')
        link.focus();link.press('Enter')
        page.wait_for_function('document.activeElement===document.querySelector("[data-v940-calendar-search]")')
        assert page.locator('[data-v940-calendar-search]').input_value()=='Mi búsqueda QA'
    finally:page.close()

@pytest.mark.parametrize('markup',[
 '<input id="qa-editor">','<textarea id="qa-editor"></textarea>',
 '<div contenteditable="true"><span id="qa-editor" tabindex="0">Editar</span></div>',
 '<div role="textbox" tabindex="0" id="qa-editor">Editar</div>',
 '<div role="dialog"><button id="qa-editor">Dialog</button></div>',
 '<div aria-modal="true"><button id="qa-editor">Dialog</button></div>',
])
def test_search_shortcut_never_steals_input_from_editors_or_dialogs(browser,app_module,markup):
    page,_,_=mount(browser,app_module)
    try:
        page.evaluate('(html)=>document.querySelector("[data-v940-calendar-experience]").insertAdjacentHTML("beforeend",html)',markup)
        editor=page.locator('#qa-editor');editor.focus();editor.press('/')
        if 'contenteditable' in markup:
            assert editor.evaluate("(e)=>{const host=e.closest('[contenteditable]');return host.contains(document.activeElement) && host.textContent.includes('/') && host.contains(getSelection().anchorNode)}")
        else:
            assert editor.evaluate('(e)=>document.activeElement===e')
    finally:page.close()


def test_shortcut_is_scoped_and_initialization_is_idempotent(browser,app_module):
    page,_,_=mount(browser,app_module)
    try:
        page.evaluate('document.body.insertAdjacentHTML("beforeend",\'<button id="qa-outside">Outside</button>\')')
        outside=page.locator('#qa-outside');outside.focus();outside.press('/')
        assert outside.evaluate('(e)=>document.activeElement===e')
        summary=page.locator('.v940-calendar-advanced summary');summary.focus();summary.press('/')
        assert page.locator('[data-v940-calendar-search]').evaluate('(e)=>document.activeElement===e')
        page.add_script_tag(content=SCRIPT)
        assert page.locator('[data-v940-calendar-experience]').get_attribute('data-v940-enhanced')=='true'
    finally:page.close()


def history_simulation(state,nav='back_forward',interrupt=False):
    # Deliberate component test doubles; do not claim an actual Back/Forward journey.
    return '''window.qaScrolls=[];window.qaFrames=[];
    window.requestAnimationFrame=callback=>{window.qaFrames.push(callback);return window.qaFrames.length;};
    window.scrollTo=(value)=>window.qaScrolls.push(value);
    Object.defineProperty(window,'IntersectionObserver',{value:undefined,configurable:true});
    delete window.IntersectionObserver;
    Object.defineProperty(performance,'getEntriesByType',{value:()=>[{type:'''+json.dumps(nav)+'''}],configurable:true});
    const state='''+json.dumps(state)+''';
    if(state){if(state.url==='CURRENT')state.url=location.pathname+location.search;
      if(state.savedAt==='NOW')state.savedAt=Date.now();
      if(state.savedAt==='FUTURE')state.savedAt=Date.now()+60000;
      if(state.savedAt==='OLD')state.savedAt=Date.now()-3*3600000;}
    const memory=new Map();window.qaMemory=memory;
    const key=`nemesis:v940:calendar:${document.documentElement.lang}:${location.pathname}${location.search}`;
    memory.set(key,JSON.stringify(state));
    Object.defineProperty(window,'sessionStorage',{value:{getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v)},configurable:true});
    window.qaFlush=()=>{for(let i=0;i<5 && window.qaFrames.length;i++){const frames=window.qaFrames.splice(0);frames.forEach(f=>f());}};
    '''

VALID={'contract':'calendar-position-v2','url':'CURRENT','savedAt':'NOW','scrollY':120,'sectionId':''}

@pytest.mark.parametrize('bad',[
 None,{}, {**VALID,'savedAt':'OLD'}, {**VALID,'savedAt':'FUTURE'},
 {**VALID,'savedAt':'123'}, {**VALID,'savedAt':None}, {**VALID,'scrollY':-1},
 {**VALID,'scrollY':'100'}, {**VALID,'scrollY':None}, {**VALID,'url':'/different-filters'},
 {**VALID,'contract':'legacy','context':'Invented league'},
])
def test_malformed_or_stale_position_does_not_move_the_page(browser,app_module,bad):
    page,_,errors=mount(browser,app_module,before=history_simulation(bad))
    try:
        page.evaluate('window.qaFlush()')
        assert page.evaluate('window.qaScrolls')==[]
        assert not errors
    finally:page.close()

@pytest.mark.parametrize('nav',['navigate','reload'])
def test_normal_visit_never_restores_history_scroll(browser,app_module,nav):
    page,_,_=mount(browser,app_module,before=history_simulation(VALID,nav))
    try:
        page.evaluate('window.qaFlush()');assert not page.evaluate('window.qaScrolls')
    finally:page.close()


def test_position_does_not_restore_cached_sports_label_and_clamps_distance(browser,app_module):
    page,_,errors=mount(browser,app_module,before=history_simulation({**VALID,'scrollY':100000,'context':'Invented old league'}))
    try:
        before=page.locator('[data-v940-current-context]').inner_text()
        page.evaluate('window.qaFlush()')
        scroll,=page.evaluate('window.qaScrolls')
        assert scroll['behavior']=='instant'
        assert scroll['top']<=page.evaluate('Math.max(0,document.documentElement.scrollHeight-innerHeight)')
        assert page.locator('[data-v940-current-context]').inner_text()==before
        assert not errors
    finally:page.close()

@pytest.mark.parametrize('event',['pointerdown','wheel','keydown'])
def test_user_input_cancels_delayed_scroll_restoration(browser,app_module,event):
    page,_,_=mount(browser,app_module,before=history_simulation(VALID))
    try:
        page.evaluate('(name)=>document.dispatchEvent(new Event(name,{bubbles:true}))',event)
        page.evaluate('window.qaFlush()');assert not page.evaluate('window.qaScrolls')
    finally:page.close()


def test_storage_denial_keeps_the_search_usable(browser,app_module):
    setup="Object.defineProperty(window,'sessionStorage',{get(){throw new Error('QA_STORAGE_DENIED')},configurable:true});"
    page,_,errors=mount(browser,app_module,before=setup)
    try:
        page.locator('[data-v940-calendar-search]').fill('Club QA')
        page.evaluate('window.dispatchEvent(new Event("pagehide"))')
        assert page.locator('[data-v940-pending-filters]').is_visible()
        assert not errors
    finally:page.close()
