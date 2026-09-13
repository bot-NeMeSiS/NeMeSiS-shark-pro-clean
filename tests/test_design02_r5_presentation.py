"""R5 keeps presentation independent of sports truth and language-independent time."""
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import pytest

from engines.ui_localization_engine import catalogue_issues, owned_text, translate


class Tags(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.items = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
@pytest.mark.parametrize('state,score,kickoff_visible', [
    ('UPCOMING', (None, None), True), ('UNKNOWN', (None, None), False),
    ('LIVE', (0, 0), False), ('FINISHED', (0, 0), False),
    ('STALE', (None, None), False), ('POSTPONED', (None, None), False),
    ('SUSPENDED', (None, None), False), ('UPCOMING', (None, 0), True),
])
def test_canonical_row_time_and_score(app_module, language, state, score, kickoff_visible):
    match = {'id': 'SIMULATED_QA', 'home_team': 'Paris Saint-Germain',
             'away_team': 'Real Madrid', 'competition': 'Official league',
             'kickoff_iso': '2026-07-15T23:30:00Z', 'source': 'SIMULATED_QA',
             'status_info': {'key': state, 'is_live': state == 'LIVE'},
             'home_score': score[0], 'away_score': score[1], 'is_stale': state == 'STALE'}
    before = deepcopy(match)
    with app_module.app.test_request_context('/', headers={'Accept-Language': language}):
        template = app_module.app.jinja_env.from_string(
            '{% from "components/v933_ui.html" import match_card with context %}'
            '{{ match_card(match, false, true) }}')
        rendered = template.render(match=match, current_user=None)
    tags = Tags(rendered).items
    score_tags = [attrs for _, attrs in tags if 'data-v934-score' in attrs]
    clocks = [attrs for _, attrs in tags if 'data-match-kickoff-clock' in attrs]
    assert len(score_tags) == 1
    assert bool(clocks) is kickoff_visible
    assert ('hidden' in score_tags[0]) is kickoff_visible
    assert '01:30' in rendered and 'Paris Saint-Germain' in rendered
    assert ('0 - 0' in rendered) is (score == (0, 0))
    assert match == before


@pytest.mark.parametrize('source', [
    'Resultado disponible', 'Conocimiento ampliado', 'Tus favoritos',
    'Tu historial', 'Últimos movimientos', 'Limitaciones de los datos',
    'Añadir favorito manualmente', 'Sin actividad aún',
])
@pytest.mark.parametrize('language', ['en', 'fr'])
def test_reported_ui_gaps_have_translations(source, language):
    assert translate(source, language) != source
    assert '{' not in translate(source, language)


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
def test_market_parameters_and_names_are_not_rewritten(language):
    for line in ['2.5', '0,5']:
        assert line in owned_text('Más de ' + line + ' goles', language)
        assert line in owned_text('Menos de ' + line + ' goles', language)
    for name in ['Real Madrid', 'Paris Saint-Germain', 'Champions League', 'Kylian Mbappé']:
        assert owned_text(name, language) == name
    assert owned_text('A provider narrative without an approved translation', language) == 'A provider narrative without an approved translation'


@pytest.mark.parametrize('language', ['en', 'fr'])
def test_round_pressure_and_risk_are_ui(language):
    assert '12' in owned_text('Jornada 12', language)
    assert owned_text('Jornada 12', language) != 'Jornada 12'
    assert 'Paris Saint-Germain' in owned_text('Paris Saint-Germain presiona', language)
    assert owned_text('HIGH', language) not in {'HIGH', 'Alto'}
    assert owned_text('STALE', language) not in {'STALE', 'LIVE'}


def test_r5_catalogue_and_single_master_contract():
    assert catalogue_issues() == []
    root = Path(__file__).resolve().parents[1]
    master = (root/'static/img/app-icons/official_app_icon_master.svg').read_text(encoding='utf-8')
    assert 'nemesis-shark-atmosphere-v2.webp' in master
    css = (root/'static/v933-product.css').read_text(encoding='utf-8')
    assert 'nemesis-ocean-depth-r5.png' in css
    assert '.v933-match-center [hidden] { display: none !important; }' in css
    assert 'body.ns-app.ns-admin::before { opacity: .18; }' in css
    chip = css.split('body.ns-app .v933-status-chip {\n  max-width: 100%;', 1)[1].split('}', 1)[0]
    assert 'min-width: min-content;' in chip
    assert 'overflow-wrap: normal;' in chip


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
@pytest.mark.parametrize('logo', ['', '/static/league-official.png', 'javascript:alert(1)'])
def test_competition_logo_reuses_safe_crest_fallback(app_module, language, logo):
    with app_module.app.test_request_context('/', headers={'Accept-Language': language}):
        template = app_module.app.jinja_env.from_string(
            '{% from "components/v933_ui.html" import competition_logo with context %}'
            '{{ competition_logo(name, {"name": name, "league_logo": logo}|v850_league_logo) }}')
        rendered = template.render(name='LaLiga Hypermotion', logo=logo)
    assert 'data-logo-kind="competition"' in rendered
    assert 'javascript:' not in rendered
    assert 'LaLiga Hypermotion' in rendered
    assert 'crest' in rendered


@pytest.mark.parametrize('language', ['en', 'fr'])
def test_preferences_and_owned_alert_counts(language):
    for message in ['No', 'Pausado', 'Activar', 'Desactivar', 'Muestra limitada',
                    'Datos insuficientes', 'Destacar equipos consultados']:
        translated = translate(message, language)
        assert translated and '{' not in translated
        if not (message == 'No' and language == 'en'):
            assert translated != message
    sentence = owned_text('Hay 3 partido(s) en directo. Revisa marcador, estado y favoritos.', language)
    assert '3' in sentence and not sentence.startswith('Hay ')
