"""R6 presentation contracts on isolated summaries, never provider data."""
from html.parser import HTMLParser
from pathlib import Path

import pytest

from engines.ui_localization_engine import catalogue_issues, translate
from jinja2 import ChoiceLoader, DictLoader


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
@pytest.mark.parametrize('state,status,has_data,query,title', [
    ('ERROR', 'temporarily_unavailable', False, 'qa', 'Agenda temporalmente no disponible'),
    ('FILTER_EMPTY', 'data_available', True, 'qa', 'No hay partidos que coincidan'),
    ('REAL_EMPTY', 'data_available', True, '', 'No hay partidos para esta fecha'),
    ('DATA_NOT_AVAILABLE', 'waiting_for_sync', False, '', 'Agenda pendiente de actualización'),
])
def test_calendar_empty_states_are_distinct(client, app_module, monkeypatch, language,
                                           state, status, has_data, query, title):
    monkeypatch.setattr(app_module, 'v932_safe_dashboard_data', lambda *a, **kw: ({}, {}))
    monkeypatch.setattr(app_module, '_v931_provider_context', lambda _: {
        'provider_status': status, 'has_real_data': has_data})
    response = client.get('/calendar', query_string={'q': query}, headers={'Accept-Language': language})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f'data-calendar-empty="{state}"' in html
    assert translate(title, language) in html
    assert 'data-v934-score' not in html
    if state == 'ERROR':
        assert 'data-calendar-empty="REAL_EMPTY"' not in html
        assert 'data-calendar-empty="FILTER_EMPTY"' not in html


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
def test_date_picker_keeps_native_form_and_filter_identity(client, app_module, monkeypatch, language):
    monkeypatch.setattr(app_module, 'v932_safe_dashboard_data', lambda *a, **kw: ({}, {}))
    response = client.get('/calendar?date=2026-10-25&team=Real+Madrid&league=Segunda',
                          headers={'Accept-Language': language})
    tags = Elements(response.get_data(as_text=True)).tags
    picker, = [a for t, a in tags if t == 'details' and a.get('class') == 'v933-calendar-date-picker']
    assert 'open' not in picker
    form, = [a for t, a in tags if t == 'form' and a.get('class') == 'v933-calendar-date-form']
    assert form['method'] == 'get' and form['action'] == '/calendar'
    field, = [a for t, a in tags if a.get('id') == 'calendar-date']
    assert field['type'] == 'date' and field['value'] == '2026-10-25'
    assert any(a.get('name') == 'team' and a.get('value') == 'Real Madrid' for _, a in tags)
    assert any(a.get('name') == 'league' and a.get('value') == 'Segunda' for _, a in tags)


@pytest.mark.parametrize('language,month', [('es', 'septiembre'), ('en', 'September'), ('fr', 'septembre')])
def test_calendar_full_date_reuses_madrid_formatter(app_module, language, month):
    with app_module.app.test_request_context('/calendar', headers={'Accept-Language': language}):
        detailed = app_module.ui_calendar_date('2026-09-13', detail=True)
    assert '13' in detailed and month in detailed


def test_r6_uses_existing_components_and_catalogue():
    root = Path(__file__).resolve().parents[1]
    home = (root / 'templates/client_app_center.html').read_text(encoding='utf-8')
    assert 'ns16-journey-steps' not in home
    assert "recent_results|rejectattr('id', 'in', featured_matches|map(attribute='id')|list)" in home
    assert "{{ match_card(match, true, true) }}" in home
    assert catalogue_issues() == []
    for source in ['Agenda temporalmente no disponible',
                   'No hay partidos que coincidan', 'Agenda pendiente de actualización']:
        for language in ['en', 'fr']:
            assert translate(source, language) != source


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
def test_home_load_error_does_not_claim_empty_schedule(app_module, language):
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}), app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/app', headers={'Accept-Language': language}):
        html = env.get_template('client_app_center.html').render(
            data={'v925_calendar': {'provider_status': 'temporarily_unavailable'}},
            current_user={'membership': 'FREE'}, greeting={'label': 'QA', 'name': ''})
    assert 'data-home-empty="ERROR"' in html
    assert translate('Agenda temporalmente no disponible', language) in html
    assert translate('Sin partidos destacados ahora', language) not in html


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
def test_static_inspector_requires_state_component_and_localized_copy(language):
    from engines.visual_company_worker_engine import _has_safe_sports_state
    title = translate('Agenda pendiente de actualización', language)
    html = '<div data-calendar-empty="DATA_NOT_AVAILABLE"><section data-empty-state="premium">'+title+'</section></div>'
    assert _has_safe_sports_state(html, title)
    assert not _has_safe_sports_state('<div data-calendar-empty="DATA_NOT_AVAILABLE"></div>', '')
    assert not _has_safe_sports_state('<section data-empty-state="premium"></section>', '')
    assert not _has_safe_sports_state('<main></main>', '')


@pytest.mark.parametrize('result_id,expected', [('qa-next', ['qa-next']), ('qa-final', ['qa-next', 'qa-final']), (None, ['qa-next'])])
def test_home_spotlight_reuses_available_result_without_duplicate_identity(app_module, result_id, expected):
    from test_design02_calendar_presentation import Structure
    upcoming = {'id': 'qa-next', 'home_team': 'QA Home', 'away_team': 'QA Away',
                'source': 'SIMULATED_QA', 'status_info': {'key': 'UPCOMING'},
                'kickoff_iso': '2026-09-14T18:30:00Z'}
    result = {**upcoming, 'id': result_id, 'status_info': {'key': 'FINISHED'},
              'home_score': 0, 'away_score': 0}
    data = {'match_hub': {'upcoming': [upcoming], 'finished': [result] if result_id else []}}
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}), app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/app'):
        html = env.get_template('client_app_center.html').render(
            data=data, current_user={'membership': 'FREE'}, greeting={'label': 'QA', 'name': ''})
    dom = Structure(html)
    main, = dom.with_class('ns16-home-sports')
    cards = [node['attrs']['data-v934-match-id'] for node in dom.nodes
             if 'data-v934-match-id' in node['attrs'] and main in node['parents']]
    assert cards == expected
    if result_id == 'qa-final':
        assert '<b data-v934-score>0 - 0</b>' in html
