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
def test_featured_reuses_the_same_five_ids_without_changing_truth(template, state):
    data = data_for([row(str(i), state) for i in range(9)])
    before = deepcopy(data)
    markup = render(template, data)
    cards = Cards(markup)
    from engines.home_preview import home_preview
    old = home_preview(data['home_matchday'], with_hero=False)
    expected = {m['id'] for lane in ('live', 'today', 'upcoming', 'results')
                for group in old[lane]['groups'] for m in group['matches']}
    assert len(cards.ids) == len(set(cards.ids)) == 5
    assert set(cards.ids) == expected
    assert cards.blocks == 1
    assert len(cards.slides) == (1 if state == 'FINISHED' else 2)
    assert 'hidden' not in cards.slides[0]
    assert all('hidden' in slide for slide in cards.slides[1:])
    assert data == before
    if len(cards.slides) == 2:
        assert '<noscript>' in markup
        assert 'data-home-featured-controls hidden' in markup


@pytest.mark.parametrize('template', ['home.html', 'client_app_center.html'])
def test_featured_does_not_take_the_only_fixture_of_another_lane(template):
    data = data_for([row('live', 'LIVE'), row('upcoming', 'UPCOMING'),
                     row('finished', 'FINISHED')])
    cards = Cards(render(template, data))
    assert cards.blocks == 1 and len(cards.slides) == 1
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
    assert cards.blocks == 1 and len(cards.slides) == 2
    assert set(cards.ids) == {'active-' + str(i) for i in range(5)}
    assert len(cards.ids) == len(set(cards.ids)) == 5
    assert 'data-v934-match-id="favorite-result"' not in markup
    assert all('href="/match/active-' + str(i) + '"' in markup for i in range(5))
    assert data['home_matchday']['results']['total'] == 1
    assert data == before


def test_featured_assets_are_bound_without_a_new_polling_transport():
    for template in ('home.html', 'client_app_center.html'):
        source = (ROOT / 'templates' / template).read_text('utf-8')
        assert "filename='home-featured.css'" in source
        assert 'featured_limit=2' in source
    base = (ROOT / 'templates/base.html').read_text('utf-8')
    assert "filename='platform-motion.js') }}?v={{ app_version }}-home-featured-1" in base
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
