"""Navigation boundaries and functional matching, independent of provider data."""
from urllib.parse import urlsplit

import pytest
from engines.app_navigation import navigation_matches
from test_design02_calendar_presentation import Structure


@pytest.mark.parametrize('label,query,expected', [
    ('Competiciones', '  competicíones  ', True),
    ('Copias de seguridad', 'seguridad copias', True),
    ('Mi cuenta', 'Mi inexistente', False), ('Mi cuenta', '', True),
    ('Membresías', 'MEMBRESIAS', True),
])
def test_matching_ignores_accents_and_word_order(label, query, expected):
    assert navigation_matches(label, query) is expected


def render_directory(app_module, scope='public', query='', language='es'):
    from flask import render_template
    user = None if scope == 'public' else {'id':'navigation-qa','name':'QA', 'role':'ADMIN' if scope == 'admin' else 'CLIENT','membership':'ADMIN' if scope == 'admin' else 'FREE'}
    path = '/admin/explorar' if scope == 'admin' else '/explorar'
    with app_module.app.test_request_context(path, headers={'Accept-Language':language}):
        return render_template('app_navigation.html', data={}, current_user=user, navigation_query=query)


@pytest.mark.parametrize('scope',['public','client','admin'])
def test_catalogue_destinations_resolve_and_respect_role_boundaries(app_module, scope):
    dom = Structure(render_directory(app_module, scope))
    links = [n['attrs']['href'] for n in dom.nodes if 'data-explore-item' in n['attrs']]
    adapter = app_module.app.url_map.bind('localhost')
    for href in links:
        assert href.startswith('/') and not href.startswith('//')
        adapter.match(urlsplit(href).path, method='GET')
        assert href.startswith('/admin/') is (scope == 'admin')
        assert 'logout' not in href and 'execute' not in href
    if scope == 'public':
        assert '/mi-cuenta' not in links and '/favoritos' not in links
    elif scope == 'client':
        assert '/favoritos' in links and '/mi-cuenta' in links
    else:
        assert '/admin/backups' in links and '/admin/users' in links


def test_server_search_without_javascript_and_escaped_query(app_module):
    markup = render_directory(app_module, 'client', '  membresias  ')
    dom = Structure(markup)
    page = next(n for n in dom.nodes if n['attrs'].get('id') == 'explore-page-results')
    visible = [n for n in dom.nodes if page in n['parents'] and 'data-explore-item' in n['attrs'] and 'hidden' not in n['attrs']]
    assert [n['attrs']['href'] for n in visible] == ['/membresias']
    malicious = '<img src=x onerror=alert(1)>&q=/admin/users'
    markup = render_directory(app_module, query=malicious)
    assert '<img src=x' not in markup and '&lt;img' in markup


@pytest.mark.parametrize('language,query', [('en','competitions'),('fr','competitions')])
def test_translated_labels_remain_searchable(app_module, language, query):
    from engines.ui_localization_engine import catalogue_issues
    assert catalogue_issues() == []
    dom = Structure(render_directory(app_module, 'public', query, language))
    page = next(n for n in dom.nodes if n['attrs'].get('id') == 'explore-page-results')
    visible = [n['attrs']['href'] for n in dom.nodes if page in n['parents'] and 'data-explore-item' in n['attrs'] and 'hidden' not in n['attrs']]
    assert visible == ['/competiciones']


def test_directory_route_is_lightweight_and_admin_is_protected(app_module, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Directory triggered operational context')
    monkeypatch.setattr(app_module, 'dashboard_data', forbidden)
    monkeypatch.setattr(app_module, 'v932_safe_dashboard_data', forbidden)
    monkeypatch.setattr(app_module, 'is_admin_session', lambda: False)
    with app_module.app.test_request_context('/admin/explorar'):
        response = app_module.app_navigation_page()
        assert response.status_code == 302
        assert response.location == '/admin-login?next=/admin/explorar'
    monkeypatch.setattr(app_module, 'render_template', lambda name, **kwargs: (name,kwargs))
    with app_module.app.test_request_context('/explorar?q=' + 'a'*110):
        name, data = app_module.app_navigation_page()
        assert name == 'app_navigation.html' and data['data'] == {}
        assert len(data['navigation_query']) == 90
    monkeypatch.setattr(app_module, 'is_admin_session', lambda: True)
    with app_module.app.test_request_context('/admin/explorar'):
        assert app_module.app_navigation_page()[0] == 'app_navigation.html'
