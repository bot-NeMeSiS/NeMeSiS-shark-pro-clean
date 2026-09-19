"""Presentation-only regressions; synthetic data never enters production."""
from copy import deepcopy
from pathlib import Path

import pytest

from engines.ui_localization_engine import context_copy, form_summary, plural, price_label, shark_copy, translate


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
@pytest.mark.parametrize('count', [0, 1, 2])
def test_plural_zero_and_parameters(language, count):
    result = plural('{count} resultado', '{count} resultados', count, language)
    assert str(count) in result and '{' not in result
    assert ('results' in result) is (language == 'en' and count != 1)


@pytest.mark.parametrize('language', ['en', 'fr'])
def test_typed_context_preserves_identity_and_evidence(language):
    context = {
        'context_intelligence': {'headline': 'Original', 'evidence': [
            {'id': 'recent-form-home', 'kind': 'recent_form', 'text': 'original'},
            {'id': 'head-to-head-context', 'kind': 'head_to_head', 'text': 'original'},
        ]},
        'recent_form': {'home': {'team': 'Paris Saint-Germain', 'available': True, 'form': ['W','D','L']}},
        'head_to_head': {'available': True, 'count': 1},
    }
    before = deepcopy(context)
    result = context_copy(context, language)
    assert context == before
    assert len(result['evidence']) == 2
    assert 'Paris Saint-Germain' in result['headline']
    assert 'Forma de' not in result['headline']
    assert '1' in result['evidence'][1]


@pytest.mark.parametrize('language', ['en', 'fr'])
def test_no_results_does_not_invent_form(language):
    assert '0' not in form_summary({'available': False, 'form': []}, language)
    assert '1' in form_summary({'available': True, 'form': ['W']}, language)


@pytest.mark.parametrize('language', ['en','fr'])
def test_typed_standings_preserve_zero_and_madrid_timestamp(language):
    context = {'context_intelligence': {'evidence': [{'kind': 'standings'}]},
               'teams': {'home': {'name': 'Paris'}, 'away': {'name': 'Madrid'}},
               'standings': {'rows': [{'team_name': 'Paris','position': 1,'points': 0},
                                     {'team_name': 'Unrelated','position': 2,'points': 3}],
                             'updated_at': '2026-07-15T23:30:00Z'}}
    seen = []
    def date(value):
        seen.append(value)
        return '16/07/2026 01:30'
    result = context_copy(context, language, date)
    assert '0' in result['headline'] and 'Unrelated' not in result['headline']
    assert '01:30' in result['headline'] and seen == ['2026-07-15T23:30:00Z']


@pytest.mark.parametrize('language', ['en','fr'])
def test_unknown_evidence_is_preserved_without_inference(language):
    result = context_copy({'context_intelligence': {'evidence': [{'kind': 'future_kind', 'text': 'Official data'}]}}, language)
    assert result['evidence'] == ['Official data']


@pytest.mark.parametrize('language', ['es','en','fr'])
def test_unavailable_shark_never_creates_signals(language):
    context = {'shark_context': {'available': False}, 'intelligence': {'conclusions': {'presion': {'value': {'home_pct': 60}}}}}
    assert shark_copy(context, language) == {'available': False}


@pytest.mark.parametrize('language', ['en','fr'])
def test_shark_localization_keeps_canonical_evidence(language):
    context = {'shark_context': {'available': True, 'dominant_team': 'Paris', 'evidence': ['Marcador'], 'signals': []},
               'teams': {'home': {'name': 'Paris'}, 'away': {'name': 'Madrid'}},
               'intelligence': {'conclusions': {'presion': {'state': 'VERIFIED', 'value': {'home_pct': 0, 'away_pct': 100}}}}}
    before = deepcopy(context)
    result = shark_copy(context, language)
    assert context == before
    assert 'Paris' in result['headline']
    assert 'Paris 0%' in result['signals'][0]
    assert len(result['evidence']) == 1


@pytest.mark.parametrize('language,suffix', [('es','/mes'),('en','/month'),('fr','/mois')])
def test_membership_does_not_translate_or_invent_amount(language, suffix):
    assert price_label('19.95 EUR/mes', language) == '19.95 EUR' + suffix
    assert price_label('Custom billing', language) == 'Custom billing'


@pytest.mark.parametrize('message', [
    'Email, usuario o contraseña incorrectos.',
    'Ese email ya está registrado.',
    'El enlace ha caducado o ya fue usado.',
    'La contraseña debe tener al menos 8 caracteres.',
])
@pytest.mark.parametrize('language', ['en','fr'])
def test_actual_auth_messages_are_translated(message, language):
    assert translate(message, language) != message


def test_grouped_match_keeps_time_and_identity_contract(app_module):
    match = {'id': 'SIMULATED_QA', 'home_team': 'Paris', 'away_team': 'Madrid',
             'competition': 'Official league', 'kickoff_iso': '2026-07-15T23:30:00Z',
             'home_score': None, 'away_score': None, 'source': 'SIMULATED_QA'}
    template = app_module.app.jinja_env.from_string(
        '{% from "components/v933_ui.html" import match_card with context %}{{ match_card(match, false, true) }}')
    with app_module.app.test_request_context('/'):
        rendered = template.render(match=match, current_user=None)
    assert 'Official league' in rendered
    css = (Path(__file__).resolve().parents[1]/'static/v933-product.css').read_text(encoding='utf-8')
    assert '.v933-calendar-day .v933-match-card-header > div:first-child:not(.v937-card-trust) { display: none; }' in css
    assert '01:30' in rendered and 'data-canonical-competition-id=' in rendered
    assert '0 - 0' not in rendered


def test_account_disclosures_preserve_actions_and_accessibility():
    root = Path(__file__).resolve().parents[1]
    source = (root/'templates/profile.html').read_text(encoding='utf-8')
    assert source.count('data-account-disclosure') == 2
    assert '/actividad' in source and '/password-reset' in source and '/logout' in source
    script = (root/'static/account-disclosures.js').read_text(encoding='utf-8')
    assert 'matchMedia' in script and 'panel.open = false' in script
