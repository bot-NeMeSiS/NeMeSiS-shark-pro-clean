"""Recovered navigation fixes: real routes, templates and isolated HTTP browser."""
import html
import os
from pathlib import Path
import re
import threading
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def error_client(app_module, monkeypatch):
    event = dict(error_id='qa-detail', exception_type='SIMULATED_QA',
                 exception_message='Synthetic diagnostic', path='/qa',
                 created_at='2026-10-01T12:00:00Z')
    monkeypatch.setattr(app_module, 'observability_summary', lambda *_: {'latest_errors': [event]})
    monkeypatch.setattr(app_module, 'latest_observability_errors', lambda *_a, **_k: [event])
    monkeypatch.setattr(app_module, 'observability_error_detail',
                        lambda _db, key: event if key == event['error_id'] else {})
    from tools.run_v929_click_navigation_qa import _signed_sessions
    sessions = _signed_sessions(app_module.app)
    client = app_module.app.test_client()
    client.set_cookie(sessions['cookie_name'], sessions['admin'])
    return client, sessions, event


@pytest.mark.parametrize('path', ['/admin/observability', '/admin/observability/errors'])
@pytest.mark.parametrize('identifier', ['qa-detail', 'qa &? fragment/#'])
def test_detail_links_keep_the_query_and_identity(error_client, path, identifier):
    client, _sessions, event = error_client
    event['error_id'] = identifier
    response = client.get(path)
    assert response.status_code == 200
    links = re.findall(r'href="([^"]+)">Ver detalle</a>', response.get_data(as_text=True))
    assert len(links) == 1
    href = html.unescape(links[0])
    parsed = urlsplit(href)
    assert parsed.path == '/admin/observability/errors'
    assert parse_qs(parsed.query) == {'error_id': [identifier]}
    detail = client.get(href)
    assert detail.status_code == 200
    assert 'Synthetic diagnostic' in detail.get_data(as_text=True)
    assert detail.cache_control.no_store and not detail.cache_control.public


@pytest.mark.parametrize('role', [None, 'client_free', 'client_pro', 'client_elite'])
def test_error_detail_is_still_admin_only(app_module, error_client, role):
    _client, sessions, _event = error_client
    client = app_module.app.test_client()
    if role:
        client.set_cookie(sessions['cookie_name'], sessions[role])
    response = client.get('/admin/observability/errors?error_id=qa-detail')
    assert response.status_code in (302, 303, 403)
    assert b'Synthetic diagnostic' not in response.data


def test_blueprint_and_mapped_templates_are_not_orphans(tmp_path):
    from engines.navigation_integrity_engine import _orphan_templates, source_rendered_templates
    (tmp_path / 'app.py').write_text("render_template('home.html')", encoding='utf-8')
    (tmp_path / 'blueprints').mkdir()
    (tmp_path / 'blueprints/news.py').write_text(
        "VIEWS = {'news': 'news.html'}\nrender_template('admin_news.html')", encoding='utf-8')
    (tmp_path / 'templates').mkdir()
    for name in ('home.html', 'news.html', 'admin_news.html', 'unused.html'):
        (tmp_path / 'templates' / name).write_text('<main>QA</main>', encoding='utf-8')
    assert source_rendered_templates(tmp_path) == {'home.html', 'news.html', 'admin_news.html'}
    assert _orphan_templates(tmp_path) == ['unused.html']


def test_today_label_does_not_promise_an_action():
    text = (ROOT / 'templates/partials/admin_visual_system.html').read_text(encoding='utf-8')
    assert '<span class="v794-date-pill">' in text
    assert '<button class="v794-date-pill"' not in text


def test_relative_endpoint_requires_context_not_a_false_missing_route():
    from flask import Blueprint, Flask
    from engines.navigation_integrity_engine import _resolve_url_for_target
    app = Flask(__name__)
    blueprint = Blueprint('media', __name__)
    blueprint.add_url_rule('/news', 'news_index', lambda: 'QA')
    app.register_blueprint(blueprint)
    assert _resolve_url_for_target(app, "url_for('.news_index')")[1] == 'WARNING'
    assert _resolve_url_for_target(app, "url_for('.missing')")[1] == 'ENDPOINT_INEXISTENTE'
    assert _resolve_url_for_target(app, "url_for('media.news_index')")[1] == 'OK'
    with app.test_request_context('/news'):
        from flask import url_for
        assert url_for('.news_index') == '/news'


def test_disabled_preview_control_is_not_a_dead_enabled_action():
    from flask import Flask
    from engines.navigation_integrity_engine import _NavigationHTMLParser, _entry_payload, classify_navigation_finding
    parser = _NavigationHTMLParser('templates/preview.html')
    parser.feed('<button type="button" disabled>Preview only</button><button type="button">Broken</button>')
    app = Flask(__name__)
    disabled, broken = [_entry_payload(app, item, {}) for item in parser.entries]
    assert classify_navigation_finding(disabled)[0] == 'AVISO_ESPERADO'
    assert classify_navigation_finding(broken)[0] == 'FALLO_REAL'


def test_local_reload_has_a_real_handler():
    text = (ROOT / 'templates/local_safe_portal.html').read_text(encoding='utf-8')
    assert "querySelectorAll('[data-local-design-refresh]')" in text
    assert "addEventListener('click',function(){window.location.reload();})" in text


@pytest.mark.parametrize('width', [320, 390, 1440])
def test_admin_error_journey_over_real_http(app_module, error_client, tmp_path, width):
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    _client, sessions, _event = error_client
    server = make_server('127.0.0.1', 0, app_module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.getenv('NEMESIS_QA_CHROMIUM') or pw.chromium.executable_path)
            context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
            context.add_cookies([{'name': sessions['cookie_name'], 'value': sessions['admin'], 'url': base}])
            context.route('**/*', lambda route: route.continue_()
                          if urlsplit(route.request.url).netloc == urlsplit(base).netloc
                          and route.request.method == 'GET' else route.abort())
            try:
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                for path in ('/admin/observability', '/admin/observability/errors'):
                    assert page.goto(base + path).status == 200
                    page.get_by_role('link', name='Ver detalle', exact=True).click()
                    page.get_by_text('Synthetic diagnostic', exact=False).first.wait_for(state='visible')
                    assert parse_qs(urlsplit(page.url).query) == {'error_id': ['qa-detail']}
                    page.reload()
                    assert parse_qs(urlsplit(page.url).query) == {'error_id': ['qa-detail']}
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    evidence = Path(os.getenv('NEMESIS_NAV_EVIDENCE_DIR') or tmp_path)
                    evidence.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(evidence / ('errors-' + str(width) + '.png')), full_page=True)
                    page.get_by_role('link', name='Resumen', exact=True).click()
                    page.wait_for_url(base + '/admin/observability')
                assert errors == []
            finally:
                context.unroute_all(behavior='wait')
                context.close()
                browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
