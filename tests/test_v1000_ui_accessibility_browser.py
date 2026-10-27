"""Real keyboard/link journeys over owned SQLite under the original LOCAL SAFE guard.

The shared admin fixture and local client fixture perform real password logins.
The local HTTP observer forwards the actual App's responses unchanged.
No business action or SHARK question is submitted; external requests are denied.
"""
from datetime import datetime, timezone
import json
import os
import secrets
import sqlite3
import sys
import threading
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.security import generate_password_hash

from browser_surface_readability import assert_surface_legible, observe_surface

from test_v1000_actual_admin_navigation import (
    actual_admin, _Document, _get, _post,
)

@pytest.fixture
def expected_identity(actual_admin):
    _module, client, _path, _cookie_name, _cookie = actual_admin
    with client.session_transaction(base_url="http://127.0.0.1") as session:
        return {"user_id": session["user_id"]}


@pytest.fixture
def actual_client(actual_admin, expected_identity):
    module, _admin, path, cookie_name, _cookie = actual_admin
    ident = "ui-accessibility-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    with sqlite3.connect(path) as conn:
        conn.execute("""INSERT INTO users
            (id,name,username,email,password_hash,role,membership,membership_source,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""", (ident, "Lucía QA", ident,
            ident + "@example.invalid", generate_password_hash(password), "FREE", "FREE",
            "LOCAL_SAFE_QA", datetime.now(timezone.utc).isoformat()))
    client = module.app.test_client()
    login = _get(client, "/cliente-login")
    token = _Document(login.get_data(as_text=True)).root.first("meta", {"name": "csrf-token"}).attrs["content"]
    response = _post(client, "/cliente-login", {
        "login": ident + "@example.invalid", "password": password,
        "csrf_token": token, "next": "/mi-cuenta",
    })
    assert response.status_code == 302
    assert urlsplit(response.location).path == "/mi-cuenta"
    cookie = client.get_cookie(cookie_name, domain="127.0.0.1")
    assert cookie is not None
    with client.session_transaction(base_url="http://127.0.0.1") as session:
        assert session.get("user_id") == ident and session.get("user_role") == "FREE"
    expected_identity["user_id"] = ident
    return cookie_name, cookie.value


@pytest.fixture
def actual_http(actual_admin, expected_identity):
    from werkzeug.serving import make_server
    module, _client, path, cookie_name, cookie = actual_admin
    documents = []

    def observe_document(environ, start_response):
        def capture_language(status, headers, exc_info=None):
            if environ.get("REQUEST_METHOD") == "GET" and environ.get("PATH_INFO") in {
                    "/admin/founder-os", "/mi-cuenta", "/shark"}:
                documents.append({
                    "path": environ["PATH_INFO"],
                    "accept_language": environ.get("HTTP_ACCEPT_LANGUAGE", ""),
                    "content_language": next((value for name, value in headers
                                              if name.lower() == "content-language"), ""),
                    "same_user": (module.current_session_user() or {}).get("id") == expected_identity["user_id"],
                })
            return start_response(status, headers, exc_info)
        return module.app(environ, capture_language)

    server = make_server("127.0.0.1", 0, observe_document, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", cookie_name, cookie, path, documents
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _context(playwright, base, width, cookie_name, cookie):
    # Native popups can navigate before Playwright applies locale emulation or
    # request routing; declare the browser's initial HTTP language as well.
    launch = {"headless": True, "args": ["--no-sandbox", "--accept-lang=es-ES,es"]}
    if os.getenv("NEMESIS_QA_CHROMIUM"):
        launch["executable_path"] = os.environ["NEMESIS_QA_CHROMIUM"]
    browser = playwright.chromium.launch(**launch)
    context = browser.new_context(viewport={"width": width, "height": 900},
        locale="es-ES", timezone_id="Europe/Madrid", reduced_motion="reduce",
        service_workers="block")
    context.add_cookies([{"name": cookie_name, "value": cookie, "url": base, "httpOnly": True}])
    requests, external, errors = [], [], []
    context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
    def boundary(route):
        requests.append((route.request.method, urlsplit(route.request.url).path))
        if route.request.url.startswith(base + "/"):
            route.continue_()
        else:
            external.append(urlsplit(route.request.url).netloc)
            route.abort()
    context.route("**/*", boundary)
    return browser, context, requests, external, errors


def _assert_spanish_documents(documents, paths):
    assert [document["path"] for document in documents] == paths, documents
    for document in documents:
        assert document["accept_language"].split(",", 1)[0] == "es-ES", document
        assert document["content_language"] == "es", document
        assert document["same_user"] is True, document


def _keyboard_geometry(control):
    return control.evaluate("""el => {
        const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
        const points = [[rect.left + 4, rect.top + 4], [rect.right - 4, rect.top + 4],
                        [rect.left + 4, rect.bottom - 4], [rect.right - 4, rect.bottom - 4],
                        [rect.x + rect.width / 2, rect.y + rect.height / 2]];
        return {focused: el === document.activeElement,
          focusVisible: el.matches(':focus-visible'), outline: style.outline,
          hasOutline: style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0,
          rect: rect.toJSON(), unobstructed: points.every(([x,y]) => el.contains(document.elementFromPoint(x,y))),
          nav: document.querySelector('.founder-os-mobile-nav').getBoundingClientRect().toJSON()};
    }""")


@pytest.mark.parametrize("width", [320, 390, 1440])
def test_founder_keyboard_focus_is_unobstructed(actual_http, tmp_path, width):
    base, name, cookie, _path, documents = actual_http
    with sync_playwright() as pw:
        browser, context, requests, external, errors = _context(pw, base, width, name, cookie)
        try:
            page = context.new_page()
            response = page.goto(base + "/admin/founder-os", wait_until="domcontentloaded")
            page.wait_for_function("Boolean(window.NemesisNavigation)")
            assert response.status == 200
            assert response.headers.get("content-language") == "es"
            _assert_spanish_documents(documents, ["/admin/founder-os"])
            assert page.locator("html").get_attribute("lang") == "es"
            summary = page.locator(".founder-os-alert summary").first
            summary.focus()
            page.keyboard.press("Shift+Tab")
            page.evaluate("scrollTo(0,0)")
            page.keyboard.press("Tab")
            geometry = _keyboard_geometry(summary)
            (tmp_path / f"founder-keyboard-{width}.json").write_text(json.dumps(geometry, indent=2), encoding="utf-8")
            page.screenshot(path=str(tmp_path / f"founder-keyboard-{width}.png"))
            assert geometry["focused"] and geometry["focusVisible"] and geometry["hasOutline"], geometry
            assert geometry["unobstructed"], geometry
            page.keyboard.press("Enter")
            assert summary.locator("..").get_attribute("open") is not None
            assert summary.locator("..").locator("dl").is_visible()
            page.keyboard.press("Space")
            assert summary.locator("..").get_attribute("open") is None
            # Reverse navigation also clears the fixed header after scrolling.
            page.keyboard.press("Tab")
            page.evaluate("scrollTo(0,document.documentElement.scrollHeight)")
            page.keyboard.press("Shift+Tab")
            reverse = _keyboard_geometry(summary)
            (tmp_path / f"founder-keyboard-reverse-{width}.json").write_text(json.dumps(reverse, indent=2), encoding="utf-8")
            assert reverse["focused"] and reverse["focusVisible"] and reverse["hasOutline"], reverse
            assert reverse["unobstructed"], reverse
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert not external and not errors, (external, errors)
            assert all(method == "GET" for method, _ in requests), requests
        finally:
            (tmp_path / f"founder-documents-{width}.json").write_text(json.dumps(documents, indent=2), encoding="utf-8")
            print("DOCUMENT_LANGUAGES", json.dumps(documents))
            context.close()
            browser.close()


@pytest.mark.parametrize("source", ["launcher", "explorer"])
@pytest.mark.parametrize("modifier", ["Control", "Meta", "Shift"])
def test_shark_modified_click_preserves_native_navigation(actual_http, actual_client, tmp_path, source, modifier):
    base, _name, _cookie, _path, documents = actual_http
    name, cookie = actual_client
    with sync_playwright() as pw:
        browser, context, requests, external, errors = _context(pw, base, 1440, name, cookie)
        try:
            page = context.new_page()
            response = page.goto(base + "/mi-cuenta", wait_until="domcontentloaded")
            page.wait_for_function("Boolean(window.NemesisNavigation)")
            assert response.status == 200
            assert response.headers.get("content-language") == "es"
            _assert_spanish_documents(documents, ["/mi-cuenta"])
            assert page.locator("html").get_attribute("lang") == "es"
            def source_link():
                if source == "explorer":
                    page.keyboard.press("Control+k")
                    page.locator("#explore-dialog-query").fill("SHARK")
                    return page.locator("#app-navigation-dialog [data-ns-assistant-restore]")
                return page.get_by_role("link", name="Abrir SHARK", exact=True)
            link = source_link()
            assert link.get_attribute("href") == "/shark"
            # Ordinary keyboard activation retains the existing inline workspace.
            link.focus()
            page.keyboard.press("Enter")
            dialog = page.get_by_role("dialog", name="SHARK", exact=True)
            assert dialog.is_visible()
            assert dialog.locator("h2").evaluate("el => el === document.activeElement")
            page.keyboard.press("Escape")
            assert not dialog.is_visible()
            link = source_link()
            try:
                if modifier == "Meta" and sys.platform != "darwin":
                    # On Linux/Windows Meta leaves the native link in this tab;
                    # on macOS it is the browser's new-tab modifier.
                    link.click(modifiers=[modifier])
                    page.wait_for_url(base + "/shark", wait_until="domcontentloaded")
                    _assert_spanish_documents(documents, ["/mi-cuenta", "/shark"])
                    assert page.locator("html").get_attribute("lang") == "es"
                    assert not page.locator("#ns-assistant-dialog").count()
                else:
                    with context.expect_page(timeout=10000) as new_page:
                        link.click(modifiers=[modifier])
                    popup = new_page.value
                    popup.wait_for_url(base + "/shark", wait_until="domcontentloaded")
                    assert popup.url == base + "/shark"
                    _assert_spanish_documents(documents, ["/mi-cuenta", "/shark"])
                    assert popup.locator("html").get_attribute("lang") == "es"
                    assert page.url == base + "/mi-cuenta"
                    assert not dialog.is_visible()
            finally:
                state = {"source": source, "modifier": modifier, "pages": [p.url for p in context.pages],
                         "assistant_open": page.locator("#ns-assistant-dialog").is_visible()}
                (tmp_path / f"shark-modified-{source}-{modifier}.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
                page.screenshot(path=str(tmp_path / f"shark-modified-{source}-{modifier}.png"))
            assert not external and not errors, (external, errors)
            assert not any(path == "/api/shark/ask" for _method, path in requests), requests
            assert all(method == "GET" or path == "/api/growth/funnel-event" for method, path in requests), requests
        finally:
            (tmp_path / f"shark-documents-{source}-{modifier}.json").write_text(json.dumps(documents, indent=2), encoding="utf-8")
            print("DOCUMENT_LANGUAGES", json.dumps(documents))
            context.close()
            browser.close()


# Surface readability uses this module's original guarded HTTP/auth fixtures.
def _probe_controls(page):
    """Independent positive/negative controls on a blank page, never the App."""
    page.set_content('''<div style="background:#000">
      <section id="good" style="background:#000;color:#fff"><span>Readable</span></section>
      <section id="composite" style="background:rgba(255,255,255,.5);color:#000"><span>Composited</span></section>
      <section id="poor" style="background:#888;color:#777"><span>Unreadable</span></section>
      <section id="image" style="background:linear-gradient(#000,#fff);color:#fff"><span>Unresolved image</span></section>
      <div style="opacity:.5"><section id="faded" style="background:#000;color:#fff"><span>Faded ancestor</span></section></div>
      <section id="generated" style="background:#000;color:#fff;position:relative"><span>Generated paint</span></section>
      </div><style>#generated::before{content:"";position:absolute;inset:0;background:rgba(255,255,255,.2)}</style>''')
    assert assert_surface_legible(page.locator('#good'), ('span',))['samples'][0]['contrast'] == 21
    composite = assert_surface_legible(page.locator('#composite'), ('span',), require_solid=False)
    assert composite['samples'][0]['background'] == [127.5, 127.5, 127.5, 1]
    for selector in ('#poor', '#image', '#faded', '#generated'):
        with pytest.raises(AssertionError):
            assert_surface_legible(page.locator(selector), ('span',))
    unresolved = observe_surface(page.locator('#image'), ('span',))['samples'][0]
    assert unresolved['unknown'] and unresolved['contrast'] is None


def _media(page, cdp, mode):
    values = {
        'prefers-reduced-motion': 'reduce',
        'prefers-reduced-transparency': 'reduce' if mode == 'reduced-transparency' else 'no-preference',
        'prefers-contrast': 'more' if mode == 'more-contrast' else 'no-preference',
        'forced-colors': 'active' if mode == 'forced-colors' else 'none',
    }
    cdp.send('Emulation.setEmulatedMedia', {'features': [
        {'name': name, 'value': value} for name, value in values.items()]})
    assert page.evaluate('(values) => Object.entries(values).every(([k,v]) => matchMedia(`(${k}: ${v})`).matches)', values)
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')


def _goto(page, base, path):
    response = page.goto(base + path, wait_until='domcontentloaded')
    assert response.status == 200 and urlsplit(page.url).path == path
    page.wait_for_function('Boolean(window.NemesisNavigation)')
    page.evaluate('document.fonts.ready')
    assert page.locator('html').get_attribute('lang') == 'es'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


@pytest.mark.parametrize('audience,width', [('client', 390), ('client', 1440), ('admin', 390), ('admin', 1440)])
def test_actual_surfaces_keep_readable_content_across_media_preferences(actual_http, request, tmp_path, audience, width):
    base, name, cookie, _database, _documents = actual_http
    if audience == 'client':
        name, cookie = request.getfixturevalue('actual_client')
    records = []
    with sync_playwright() as pw:
        browser, context, requests, external, errors = _context(pw, base, width, name, cookie)
        page = context.new_page()
        if audience == 'client':
            page.set_viewport_size({'width': width, 'height': 960})
        cdp = context.new_cdp_session(page)

        def measure(label, surface, selectors, **kwargs):
            try:
                result = assert_surface_legible(surface, selectors, **kwargs)
            except AssertionError as exc:
                records.append({'label': label, 'failure': str(exc)})
                page.screenshot(path=str(tmp_path / f'{audience}-{width}-failure.png'))
                raise
            records.append({'label': label, **result})
            return result

        try:
            _media(page, cdp, 'normal')
            if audience == 'client' and width == 390:
                _probe_controls(page)
            if audience == 'client':
                _goto(page, base, '/app')
                measure('home data card', page.locator('.v933-kpi').first, ('div > span', 'strong'))
                page.screenshot(path=str(tmp_path / f'home-{width}.png'))
                _goto(page, base, '/mi-cuenta')
                assert page.locator('[data-v1000-admin-directory]').count() == 0
                original_classes = page.locator('body').get_attribute('class')
                original_plan = page.locator('body').get_attribute('data-ns-plan')
                assert original_plan == 'FREE'
                accents = []
                try:
                    for plan in ('free', 'pro', 'elite', 'eliteplus'):
                        accent = page.evaluate('''plan => {
                          const body = document.body;
                          body.classList.remove('ns-tier-free','ns-tier-pro','ns-tier-elite','ns-tier-eliteplus');
                          body.classList.add('ns-tier-' + plan);
                          return getComputedStyle(body).getPropertyValue('--tier-primary').trim();
                        }''', plan)
                        accents.append(accent)
                        measure('visual accent ' + plan, page.locator('.v933-panel').first,
                                ('h2', '.v933-quick-action strong', '.v933-quick-action small'))
                        assert page.locator('body').get_attribute('data-ns-plan') == original_plan
                        assert page.locator('[data-v1000-admin-directory]').count() == 0
                    assert all(accents) and len(set(accents)) == 4
                finally:
                    page.locator('body').evaluate('(body, value) => body.className = value', original_classes)
                if width == 390:
                    menu = page.locator('.product-account-menu')
                    menu.locator('summary').click()
                    measure('account menu', menu.locator('nav'), ('a[href="/mi-cuenta"]', 'a[href="/soporte"]'))
                    page.screenshot(path=str(tmp_path / f'account-menu-{width}.png'))
                    menu.locator('summary').click()
                page.screenshot(path=str(tmp_path / f'account-{width}.png'))
                primary = page.locator('.v933-panel').first
                primary_text = ('h2', '.v933-quick-action small')
            else:
                _goto(page, base, '/admin/users')
                measure('admin directory card', page.locator('.v933-user-card').first, ('header strong', 'header small', 'dt', 'dd'))
                _goto(page, base, '/admin/founder-os')
                measure('admin alert', page.locator('.founder-os-alert').first, ('.founder-os-alert-meta', 'strong', 'p', 'summary'))
                measure('admin data card', page.locator('#overview article').first, ('span', 'strong', 'small'))
                page.screenshot(path=str(tmp_path / f'founder-{width}.png'))
                primary = page.locator('#inbox')
                primary_text = ('h2', '.founder-os-alert-meta', '.founder-os-alert-content p')
                control = page.locator('.founder-os-editor input[name="currency"]')

            for mode in ('normal', 'reduced-transparency', 'more-contrast', 'forced-colors'):
                _media(page, cdp, mode)
                measure(mode + ' primary panel', primary, primary_text)
                if audience == 'admin':
                    control.scroll_into_view_if_needed()
                    measure(mode + ' form control', control, (':scope',))
                # The actual /mi-cuenta view has no language form. Its client
                # controls are the real navigation input and SHARK textarea below.
                page.keyboard.press('Control+k')
                dialog = page.locator('#app-navigation-dialog')
                assert dialog.is_visible()
                measure(mode + ' navigation dialog', dialog, ('h2', '.app-explore-help'))
                search = dialog.locator('[data-explore-query]')
                search.fill('cuenta' if audience == 'client' else 'usuarios')
                measure(mode + ' navigation input', search, (':scope',))
                search.fill('')
                measure(mode + ' navigation placeholder', search, ({'selector': ':scope', 'pseudo': '::placeholder'},))
                search.fill('cuenta' if audience == 'client' else 'usuarios')
                measure(mode + ' navigation result', dialog.locator('[data-explore-item]:visible').first, ('span',))
                page.screenshot(path=str(tmp_path / f'{audience}-{width}-{mode}-navigation.png'))
                page.keyboard.press('Escape')
                assert not dialog.is_visible()
                if audience == 'client':
                    page.get_by_role('link', name='Abrir SHARK', exact=True).click()
                    assistant = page.locator('#ns-assistant-dialog')
                    assert assistant.is_visible()
                    measure(mode + ' assistant dialog', assistant, ('h2', '.ns-assistant-note', 'footer small'))
                    question = assistant.locator('textarea')
                    question.fill('Texto para comprobar la lectura; no se envía.')
                    measure(mode + ' assistant input', question, (':scope',))
                    question.fill('')
                    measure(mode + ' assistant placeholder', question, ({'selector': ':scope', 'pseudo': '::placeholder'},))
                    page.screenshot(path=str(tmp_path / f'{audience}-{width}-{mode}-assistant.png'))
                    page.keyboard.press('Escape')
                    assert not assistant.is_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            assert not external and not errors, (external, errors)
            assert not any(path == '/api/shark/ask' for _method, path in requests), requests
            assert all(method == 'GET' or path == '/api/growth/funnel-event' for method, path in requests), requests
        finally:
            (tmp_path / f'surfaces-{audience}-{width}.json').write_text(
                json.dumps({'audience': audience, 'width': width, 'records': records,
                            'external': external, 'page_errors': errors, 'requests': requests}, ensure_ascii=False, indent=2),
                encoding='utf-8')
            cdp.detach()
            context.close()
            browser.close()
