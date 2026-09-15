"""Presentation regressions; SIMULATED_QA only, no provider or business writes."""
from html.parser import HTMLParser
from pathlib import Path

import pytest
from datetime import date, timedelta
from urllib.parse import urlparse, parse_qs


@pytest.mark.parametrize('day', ['2026-03-29', '2026-10-25', '2026-01-01', '2026-12-31'])
def test_date_navigation_uses_madrid_civil_days_and_preserves_existing_filters(app_module, monkeypatch, day):
    current = date.fromisoformat(day)
    monkeypatch.setattr(app_module, 'today_iso', lambda offset=0: (current + timedelta(days=offset)).isoformat())
    filters = {'date': day, 'lane': 'today', 'league': 'Segunda', 'q': 'SIMULATED_QA'}
    navigation = app_module._design02_calendar_date_navigation(filters)
    assert navigation['selected'] == day
    assert [item['label'] for item in navigation['shortcuts']] == ['Ayer', 'Hoy', 'Mañana']
    for key, offset in [('previous', -1), ('next', 1)]:
        query = parse_qs(urlparse(navigation[key]).query)
        assert query['date'] == [(current + timedelta(days=offset)).isoformat()]
        assert query['league'] == ['Segunda']
        assert query['q'] == ['SIMULATED_QA']
        assert query['lane'] == ['today']


class Structure(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.nodes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'parents': list(self.stack)}
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]
                break

    def with_class(self, name):
        return [n for n in self.nodes if name in n['attrs'].get('class', '').split()]


def assert_calendar_structure(html):
    dom = Structure(html)
    root, = dom.with_class('v940-calendar-experience')
    advanced, = dom.with_class('v940-calendar-advanced')
    collection, = [n for n in dom.nodes if 'data-v940-calendar-collection' in n['attrs']]
    header, = dom.with_class('v933-page-header')
    form, = dom.with_class('v940-calendar-filter-form')
    assert not any(n['tag'] == 'details' for n in root['parents'])
    for node in (header, collection):
        assert root in node['parents']
        assert advanced not in node['parents']
    assert advanced in form['parents']
    assert root in advanced['parents']
    return advanced


@pytest.mark.parametrize('route', ['/calendar', '/calendario', '/calendario-global', '/partidos', '/partidos/calendario'])
@pytest.mark.parametrize('query', ['', 'SIMULATED_QA'])
def test_calendar_disclosure_never_hides_header_or_collection(client, app_module, monkeypatch, route, query):
    match = {'id': 'design02-simulated', 'home_team': 'SIMULATED_QA Local',
             'away_team': 'SIMULATED_QA Visitante', 'competition_name': 'Liga QA',
             'match_date': app_module.today_iso(), 'kickoff_time': '18:00',
             'source': 'SIMULATED_QA', 'v935_lifecycle': 'UPCOMING'}
    summary = {'all_valid_matches': [match], 'valid_upcoming_matches': [match],
               'valid_matches_today': [match], 'valid_matches_available': [match],
               'valid_live_events': [], 'valid_active_picks': [], 'finished_matches': [],
               'incident_matches': [], 'incomplete_matches': [], 'raw_matches_count': 1}
    metrics = app_module.build_sports_metrics_contract(summary)
    monkeypatch.setattr(app_module, 'v932_safe_dashboard_data', lambda *a, **kw: ({'sports_metrics': metrics}, summary))
    response = client.get(route, query_string={'lane': 'week', 'q': query})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    advanced = assert_calendar_structure(html)
    assert ('open' in advanced['attrs']) is bool(query)
    assert 'data-v934-match-id="design02-simulated"' in html


def test_structure_detector_rejects_original_outer_disclosure():
    broken = '<details class="v940-calendar-advanced"><div class="v940-calendar-experience"><header class="v933-page-header"></header><form class="v940-calendar-filter-form"></form></details><main data-v940-calendar-collection></main></div>'
    with pytest.raises(AssertionError):
        assert_calendar_structure(broken)


@pytest.mark.parametrize('scores,expected', [((None, None), 'VS'), ((0, 0), '0 - 0'), ((2, None), 'VS'), ((2, 1), '2 - 1')])
def test_shared_card_preserves_unknown_and_confirmed_zero(app_module, scores, expected):
    with app_module.app.test_request_context('/calendar'):
        module = app_module.app.jinja_env.get_template('components/v933_ui.html').make_module({'current_user': None})
        html = str(module.match_card({'id': 'SIMULATED_QA', 'home_team': 'Local', 'away_team': 'Visitante',
                                     'home_score': scores[0], 'away_score': scores[1]}))
    assert f'<b data-v934-score>{expected}</b>' in html


@pytest.mark.parametrize('authenticated', [True, False])
def test_mobile_primary_navigation_keeps_account_and_calendar(app_module, authenticated):
    with app_module.app.test_request_context('/calendar'):
        module = app_module.app.jinja_env.get_template('components/v933_navigation.html').make_module()
        html = str(module.v933_mobile_bottom_nav(authenticated))
    dom = Structure(html)
    links = [n['attrs']['href'] for n in dom.nodes if n['tag'] == 'a']
    assert links == ['/app' if authenticated else '/', '/calendar', '/live', '/picks', '/profile' if authenticated else '/cliente-login']
    assert '<span>Calendario</span>' in html
    assert '/shark' not in links


def test_sports_styles_use_canonical_sizes_and_version_both_stylesheets():
    root = Path(__file__).resolve().parents[1]
    css = (root / 'static/v933-product.css').read_text(encoding='utf-8')
    base = (root / 'templates/base.html').read_text(encoding='utf-8')
    assert 'font-size: var(--score-size)' in css
    assert 'font-size: var(--score-size-compact)' in css
    assert 'width: var(--sports-crest-size, var(--crest-md))' in css
    assert '.v933-team-logo img' in css and 'object-fit: contain' in css
    token_link = next(line for line in base.splitlines() if "filename='v933_design_tokens.css'" in line)
    product_link = next(line for line in base.splitlines() if "filename='v933-product.css'" in line)
    assert '-design-02-sports-1' in token_link
    realtime_script = next(line for line in base.splitlines() if "filename='v934-realtime.js'" in line)
    assert '-design-02-r6-1' in product_link
    assert '-design-02-r5-1' not in product_link
    assert '-design-02-r5-1' in realtime_script
    assert '-design-02-r3-1' not in product_link
    assert '-design-02-conformance-2' not in product_link


@pytest.mark.parametrize('route', ['/calendar', '/calendario', '/calendario-global', '/partidos', '/partidos/calendario'])
@pytest.mark.parametrize('surface', ['v933_public_navigation', 'v933_client_navigation', 'v933_mobile_bottom_nav'])
def test_calendar_aliases_share_visible_navigation_state(app_module, route, surface):
    with app_module.app.test_request_context(route):
        module = app_module.app.jinja_env.get_template('components/v933_navigation.html').make_module()
        dom = Structure(str(getattr(module, surface)()))
    selected = [n for n in dom.nodes if n['tag'] == 'a' and n['attrs'].get('aria-current') == 'page']
    assert selected
    assert all(n['attrs'].get('href') == '/calendar' for n in selected)


def test_client_copy_reduction_does_not_hide_temporal_container():
    root = Path(__file__).resolve().parents[1]
    css = (root / 'static/v933-product.css').read_text(encoding='utf-8')
    for owner in ('sports-priority-home', 'ns16-home', 'ns16-live', 'v933-calendar-board'):
        rule = next(line for line in css.splitlines() if line.startswith('.' + owner + ' .v933-match-card :is('))
        assert '.v937-confidence-badge' in rule
        assert '.v937-card-trust' not in rule
