from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from engines.v934_realtime_sports_engine import normalize_match
from engines.ui_localization_engine import translate


@pytest.mark.parametrize('locale', ['es', 'en', 'fr'])
def test_live_renders_all_supplied_rows_without_mutating_evidence(app_module, locale):
    now = datetime.now(ZoneInfo('Europe/Madrid'))
    rows = [normalize_match(dict(id=f'qa-{i}',home_team=f'Local QA {i}',away_team='Visitante QA',
        competition_name='Liga QA',source='SIMULATED_QA',match_date=now.date().isoformat(),
        kickoff_time='12:00',status='LIVE',minute=0,home_score=0,away_score=0,
        last_synced_at=(now-timedelta(seconds=10)).isoformat()),now=now) for i in range(12)]
    original=deepcopy(rows)
    from flask import g, render_template
    with app_module.app.test_request_context('/live'):
        g.ui_locale=locale
        html=render_template('live.html',data={'live_experience':{'matches':rows},'sports_metrics':{'live_confirmed':12}})
    assert html.count('data-realtime-consumer="directo-v1"') == 12
    assert html.count('data-canonical-live="true"') == 12
    assert rows == original


@pytest.mark.parametrize('locale', ['en', 'fr'])
def test_new_dynamic_copy_is_delivered_to_the_canonical_browser_catalogue(app_module,locale):
    from flask import g
    source='Marcador actualizado: {score}. No confirma un evento de gol.'
    with app_module.app.test_request_context('/live'):
        g.ui_locale=locale
        context={}
        app_module.app.update_template_context(context)
    assert context['ui_messages'][source] == translate(source,locale)
    assert translate(source,locale) != source
    assert '{score}' in translate(source,locale)


@pytest.mark.parametrize('locale', ['es','en','fr'])
def test_match_center_keeps_observed_minute_zero_and_compacts_missing_context(app_module,locale):
    from flask import g, render_template_string
    with app_module.app.test_request_context('/match/qa'):
        g.ui_locale=locale
        context={'lifecycle':{'minute':0,'label':'En directo'},'score':{'label':'0-0','confirmed':True},
                 'competition':{'name':'Liga QA'},'facts':{},'teams':{}}
        html=render_template_string('{% from "components/v944_match_center.html" import score_widget, competition_panel %}{{ score_widget(c) }}{{ competition_panel(c) }}',c=context)
    assert '<small>0</small>' in html
    assert 'data-missing-context' in html
    assert html.count('<dd>'+translate('No disponible',locale)+'</dd>') == 0
    assert 'Liga QA' in html


@pytest.mark.parametrize('locale', ['en','fr'])
@pytest.mark.parametrize('source', [
    'No disponible: faltan señales deportivas suficientes o frescas.',
    'No disponible: faltan senales deportivas suficientes o frescas.',
    'Partido en curso',
])
def test_shark_insufficient_evidence_message_is_localized(locale,source):
    assert translate(source,locale) != source


def test_known_match_context_values_remain_visible(app_module):
    from flask import render_template_string
    context={'competition':{'name':'Liga QA','round':'8','country':'España'},
             'facts':{'season':'2026','stadium':'Estadio QA','city':'Madrid','referee':'Árbitro QA'}}
    with app_module.app.test_request_context('/match/qa'):
        html=render_template_string('{% from "components/v944_match_center.html" import competition_panel %}{{ competition_panel(c) }}',c=context)
    for value in ('Liga QA','2026','Estadio QA','Madrid','Árbitro QA'):
        assert value in html
    assert 'data-missing-context' not in html


@pytest.mark.parametrize('minute,expected', [(0,0), (None,None), ('',None)])
def test_canonical_match_preserves_zero_but_never_fills_missing_minute(minute,expected):
    from engines.sports_domain_model_engine import normalize_match_entity
    now=datetime.now(ZoneInfo('Europe/Madrid'))
    row={'id':'qa-zero','home_team':'Local QA','away_team':'Visitante QA','status':'LIVE',
         'minute':minute,'source':'SIMULATED_QA','last_synced_at':now.isoformat()}
    result=normalize_match_entity(row,now_madrid=now.isoformat())
    assert result['status_truth']['is_live'] is True
    assert result['minute'] == expected


@pytest.mark.parametrize('minute,expected', [(0,'0'), ('0','0'), (None,''), ('',''), (False,'')])
def test_web_domain_adapter_preserves_observed_zero_only_when_live(app_module,minute,expected):
    now=datetime.now(ZoneInfo('Europe/Madrid'))
    row={'id':'qa-zero','home_team':'Local QA','away_team':'Visitante QA','status':'LIVE',
         'minute':minute,'source':'SIMULATED_QA','last_synced_at':now.isoformat()}
    with app_module.app.test_request_context('/match/qa-zero'):
        assert app_module.canonical_live_minute(row) == expected
        assert app_module.canonical_match_for_domain_context(row)['minute'] == (expected or None)
        assert app_module.canonical_live_minute(dict(row,status='FT')) == ''
        assert app_module.canonical_live_minute(dict(row,last_synced_at='2000-01-01T00:00:00Z')) == ''
