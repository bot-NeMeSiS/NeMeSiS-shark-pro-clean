"""One SSR featured block reuses canonical Home admission, not a new data feed."""
from copy import deepcopy
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
import re

import pytest

from test_home_canonical_consistency import data_for, render, row

ROOT = Path(__file__).resolve().parents[1]


class Cards(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.ids = []
        self.slides = []
        self.blocks = 0
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'data-v934-match-id' in attrs:
            self.ids.append(attrs['data-v934-match-id'])
        if 'data-home-featured' in attrs:
            self.blocks += 1
        if 'data-home-featured-slide' in attrs:
            self.slides.append(attrs)


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
@pytest.mark.parametrize('state', ['LIVE', 'UPCOMING', 'FINISHED'])
def test_mixed_feature_preserves_nine_accepted_ids_without_changing_truth(template, state):
    data = data_for([row(str(i), state) for i in range(9)])
    before = deepcopy(data)
    markup = render(template, data)
    cards = Cards(markup)
    assert len(cards.ids) == len(set(cards.ids)) == 9
    assert set(cards.ids) == {str(i) for i in range(9)}
    assert cards.blocks == int(state != 'FINISHED')
    assert len(cards.slides) == (0 if state == 'FINISHED' else 8)
    if cards.slides:
        assert 'hidden' not in cards.slides[0]
    assert all('hidden' in slide for slide in cards.slides[1:])
    assert data == before
    if len(cards.slides) > 1:
        assert '<noscript>' in markup
        assert 'data-home-featured-controls hidden' in markup


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
def test_featured_mixes_live_and_today_and_keeps_results_separate(template):
    data = data_for([row('live', 'LIVE'), row('upcoming', 'UPCOMING'),
                     row('finished', 'FINISHED')])
    cards = Cards(render(template, data))
    assert cards.blocks == 1 and len(cards.slides) == 2
    assert set(cards.ids) == {'live', 'upcoming', 'finished'}


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
@pytest.mark.parametrize('rows', [[], [row('stale', 'LIVE', stale=True)]])
def test_empty_or_stale_snapshot_never_uses_promotional_fallback(template, rows):
    markup = render(template, data_for(rows))
    assert Cards(markup).blocks == 0
    assert 'data-v934-match-id="cached-expired"' not in markup
    assert 'data-v934-match-id="stale"' not in markup


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
def test_native_fixture_links_and_sports_only_featured_content(template):
    data = data_for([row('one', 'LIVE'), row('two', 'LIVE')])
    markup = render(template, data)
    featured = markup.split('data-home-featured role=', 1)[1].split('</noscript>', 1)[0]
    assert 'href="/match/one"' in featured and 'href="/match/two"' in featured
    for name in ('data-pick-id', 'data-stake', 'data-odds', '/checkout', '/combinadas'):
        assert name not in featured
    assert 'data-home-featured-next' in featured
    assert 'data-home-featured-prev' in featured
    assert 'aria-live="polite"' in featured
    assert 'onclick=' not in featured


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
def test_real_application_filter_supports_featured_opt_in(app_module, template):
    from jinja2 import ChoiceLoader, DictLoader
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/' if template == 'home.html' else '/app'):
        markup = render(template, data_for([row('one', 'LIVE'), row('two', 'LIVE')]), env)
    assert Cards(markup).blocks == 1
    assert len(Cards(markup).slides) == 2


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
@pytest.mark.parametrize('lane', ['live', 'today', 'upcoming'])
def test_real_home_prioritizes_active_phase_over_favorite_results(app_module, template, lane):
    from jinja2 import ChoiceLoader, DictLoader
    active = [row('active-' + str(i), 'LIVE' if lane == 'live' else 'UPCOMING')
              for i in range(5)]
    if lane == 'upcoming':
        for match in active:
            match['kickoff_iso'] = (datetime.fromisoformat(match['kickoff_iso'])
                                    + timedelta(days=1)).isoformat()
    finished = dict(row('favorite-result', 'FINISHED'), is_favorite=True)
    data = data_for(active + [finished])
    before = deepcopy(data)
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/' if template == 'home.html' else '/app'):
        markup = render(template, data, env)
    cards = Cards(markup)
    assert cards.blocks == int(lane != 'upcoming')
    assert len(cards.slides) == (0 if lane == 'upcoming' else 5)
    assert set(cards.ids) == {'active-' + str(i) for i in range(5)} | {'favorite-result'}
    assert len(cards.ids) == len(set(cards.ids)) == 6
    assert all('data-v934-match-id="favorite-result"' not in article
               for _, article in _featured_fragments(markup))
    assert all('href="/match/active-' + str(i) + '"' in markup for i in range(5))
    assert data['home_matchday']['results']['total'] == 1
    assert data == before


def test_featured_assets_are_bound_without_a_new_polling_transport():
    for template in ('home.html', 'client_app_center.html'):
        source = (ROOT / 'templates' / template).read_text('utf-8')
        assert "filename='home-featured.css'" in source
        assert "featured_limit=8, mode='mixed_today'" in source
    base = (ROOT / 'templates/base.html').read_text('utf-8')
    assert "filename='platform-motion.js') }}?v={{ app_version }}-home-featured-2" in base
    component = (ROOT / 'templates/components/home_featured.html').read_text('utf-8')
    assert 'realtime_state_bar' not in component and '<script' not in component
    css = (ROOT / 'static/home-featured.css').read_text('utf-8')
    assert '.home-match-featured-slide[hidden]' in css
    assert 'prefers-reduced-motion' in css


def test_public_fully_featured_lane_does_not_create_a_duplicate_empty_panel():
    markup = render('home.html', data_for([row('one', 'LIVE'), row('two', 'LIVE')]))
    assert Cards(markup).blocks == 1
    assert 'data-sports-live-confirmed="2"' in markup
    assert 'data-sports-priority="live-now"' not in markup
    assert 'href="/directo"' in markup


def _native_home_markup(app_module, template, data, user=None):
    from jinja2 import ChoiceLoader, DictLoader
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block content %}{% endblock %}'}),
        app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/' if template == 'home.html' else '/app'):
        return env.get_template(template).render(
            data=data, current_user=user,
            greeting={'label': 'Prueba', 'name': 'SIMULATED_QA'},
            evidence_origin='SIMULATED_QA')


def _featured_fragments(markup):
    # Read each SSR slide's own context and canonical article, before any later
    # result group. Hidden slides remain in the same HTML and are not cloned.
    for fragment in markup.split('data-home-featured-slide')[1:]:
        context, article = fragment.split('<article ', 1)
        yield context, article.split('</article>', 1)[0]


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
def test_sparse_upcoming_hero_is_not_named_for_a_favorite_finished_elsewhere(app_module, template):
    upcoming = [row('next-one'), row('next-two')]
    for match in upcoming:
        match['kickoff_iso'] = (datetime.fromisoformat(match['kickoff_iso'])
                                + timedelta(days=1)).isoformat()
    data = data_for(upcoming + [dict(row('favorite-finished', 'FINISHED'), is_favorite=True)])
    before = deepcopy(data)
    markup = _native_home_markup(app_module, template, data)
    cards = Cards(markup)
    assert set(cards.ids) == {'next-one', 'next-two', 'favorite-finished'}
    assert len(cards.ids) == len(set(cards.ids)) == 3
    parts = list(_featured_fragments(markup))
    assert parts == []  # Tomorrow and finished fixtures remain ordinary cards.
    assert 'Favorito destacado' not in markup
    assert 'Tus favoritos, primero' not in markup
    if template == 'home.html':
        assert re.search(r'<h1[^>]*>Tu jornada deportiva', markup)
        assert '<h2 data-home-featured-title>Grandes partidos de hoy</h2>' in markup
    assert data['home_matchday']['results']['total'] == 1
    assert data == before


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
def test_featured_favorite_and_highlight_belong_only_to_their_own_fixture(app_module, template):
    first = row('plain-live', 'LIVE')
    favorite = dict(row('saved-live', 'LIVE'), is_favorite=True, has_highlights=True)
    data = data_for([first, favorite])
    before = deepcopy(data)
    user = {'id': 'owned-featured-user', 'name': 'QA', 'role': 'FREE', 'membership': 'FREE'}
    markup = _native_home_markup(app_module, template, data, user)
    parts = list(_featured_fragments(markup))
    assert len(parts) == 2
    for context, article in parts:
        identity = re.search(r'data-v934-match-id="([^"]+)"', article)[1]
        expected = identity == 'saved-live'
        badge = re.search(r'<span [^>]*data-home-featured-favorite[^>]*>', context)[0]
        assert (' hidden' not in badge) is expected
        button = re.search(r'<button [^>]*data-kind="match"[^>]*>', article)[0]
        assert f'data-value="{identity}"' in button
        assert f'aria-pressed="{"true" if expected else "false"}"' in button
        assert f'href="/match/{identity}"' in article
        assert (f'href="/match/{identity}#match-section-video"' in article) is expected
    assert data == before


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
@pytest.mark.parametrize('state', ['LIVE', 'UPCOMING', 'FINISHED'])
def test_featured_reuses_confirmed_zero_score_and_never_fills_missing_time_or_minute(app_module, template, state):
    match = row('owned-truth', state)
    match.update(home_team='Club de nombre muy largo de la ciudad de prueba',
                 away_team='Unión deportiva visitante de nombre completo',
                 home_logo='', away_logo='', client_live_minute=None)
    if state != 'UPCOMING':
        match.update(home_score=0, away_score=0)
    data = data_for([match])
    before = deepcopy(data)
    markup = _native_home_markup(app_module, template, data)
    parts = list(_featured_fragments(markup))
    assert len(parts) == int(state != 'FINISHED')
    article = (parts[0][1] if parts else
               markup.split('data-v934-match-id="owned-truth"', 1)[1].split('</article>', 1)[0])
    score = re.search(r'<b data-v934-score[^>]*>(.*?)</b>', article, re.S)[1].strip()
    if state == 'UPCOMING':
        assert score == 'VS'
        assert 'data-match-kickoff-clock' in article and 'Madrid' in article
    else:
        assert score == '0 - 0'
    assert '<small data-v934-minute hidden></small>' in article
    assert match['home_team'] in article and match['away_team'] in article
    assert f'href="/match/{match["id"]}"' in article
    assert 'data-match-temporal-context=' in article
    assert data == before


def test_legacy_upcoming_title_and_card_do_not_follow_a_favorite_result(app_module):
    upcoming = row('legacy-next', 'UPCOMING')
    favorite = dict(row('legacy-result', 'FINISHED'), is_favorite=True)
    data = {'home_summary': {'sports_home': {
        'live_now': [], 'important_today': [], 'upcoming': [upcoming],
        'recent_results': [favorite], 'favorites': [favorite]}}}
    before = deepcopy(data)
    markup = _native_home_markup(app_module, 'home.html', data)
    parts = list(_featured_fragments(markup))
    assert len(parts) == 1
    context, article = parts[0]
    assert 'data-v934-match-id="legacy-next"' in article
    assert 'data-home-featured-favorite' not in context
    assert re.search(r'<h1[^>]*>Próximos partidos', markup)
    assert '<h2 data-home-featured-title>Grandes partidos de hoy</h2>' in markup
    assert data == before
