"""Synthetic regressions for the combined #139 + #141 candidate."""
from copy import deepcopy

import pytest

from engines.match_editorial_engine import build_editorial
from engines.ui_localization_engine import catalogue_issues
from test_match_editorial import CONTEXT


def test_decisive_events_are_not_displaced_by_four_minor_events():
    context = deepcopy(CONTEXT)
    minor = [dict(id=str(i), type='substitution', label='Cambio', minute_label=str(i)) for i in range(4)]
    decisive = [dict(id='goal', type='goal', label='Gol', minute_label='80'),
                dict(id='red', type='red_card', label='Tarjeta roja', minute_label='85')]
    context['event_summary'] = dict(available=True, source='SIMULATED_QA', items=minor + decisive)
    before = deepcopy(context)
    result = build_editorial(context)
    assert len(result['moments']) == 4
    assert {'Gol', 'Tarjeta roja'} <= {event['label'] for event in result['moments']}
    assert context == before
    assert [event['minute'] for event in result['moments']] == ['0', '1', '80', '85']


@pytest.mark.parametrize('language,title,phase', [('en', 'How the match unfolded', 'Full time'),
                                                ('fr', 'Le fil du match', 'Terminé')])
def test_editorial_language_preserves_facts_and_identities(language, title, phase):
    context = deepcopy(CONTEXT)
    context['teams'] = {'home': {'name': 'Equipo Uno'}, 'away': {'name': 'Equipo Dos'}}
    context['summaries'] = {'items': [{'type': 'FULLTIME_SUMMARY'}]}
    result = build_editorial(context, language=language)
    assert result['title'] == title
    assert result['phase'] == phase
    assert 'Equipo Uno' in result['summary'] and '0-0' in result['summary']
    assert result['facts'][0]['home'] == '0'
    assert result['facts'][0]['label'] == 'Corners'
    assert result['external_calls'] == result['generative_ai_calls'] == 0


@pytest.mark.parametrize('language', ['es', 'en', 'fr'])
def test_stale_editorial_never_promotes_saved_events(language):
    context = deepcopy(CONTEXT)
    context['lifecycle'].update(is_stale=True, is_live=True)
    result = build_editorial(context, language=language)
    assert not result['facts'] and not result['moments']
    assert result['observed_at'] == context['evidence']['updated_at']


def test_editorial_catalogue_has_no_missing_or_incompatible_parameters():
    assert catalogue_issues() == []


@pytest.mark.parametrize('kind,label,en,fr', [
    ('yellow_red_card', 'Segunda amarilla', 'Second yellow card', 'Deuxième carton jaune'),
    ('penalty_shootout_goal', 'Gol en la tanda', 'Shoot-out goal', 'Tir au but marqué'),
    ('red_card', 'Tarjeta roja', 'Red card', 'Carton rouge'),
])
def test_canonical_decisive_event_types_remain_visible_and_localized(kind, label, en, fr):
    context = deepcopy(CONTEXT)
    context['event_summary'].update(available=True, source='SIMULATED_QA')
    context['event_summary']['items'] = [dict(type='substitution',label='Cambio',minute_label=str(i)) for i in range(4)]
    context['event_summary']['items'].append(dict(type=kind,label=label,minute_label='90'))
    for language, expected in [('en', en), ('fr', fr)]:
        assert any(row['label'] == expected for row in build_editorial(context,language=language)['moments'])
