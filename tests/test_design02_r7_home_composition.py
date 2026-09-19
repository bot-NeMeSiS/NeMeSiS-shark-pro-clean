"""Home-only presentation preserves sports identity and default shared consumers."""
from pathlib import Path
import pytest
from jinja2 import ChoiceLoader, DictLoader
from test_design02_calendar_presentation import Structure
from engines.ui_localization_engine import catalogue_issues, translate

ROOT = Path(__file__).resolve().parents[1]

def render_home(app_module, data, language='es'):
    env = app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}), app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/app',headers={'Accept-Language':language}):
        return env.get_template('client_app_center.html').render(data=data,
            current_user={'membership':'FREE'},greeting={'label':'QA','name':''})

@pytest.mark.parametrize('language',['es','en','fr'])
@pytest.mark.parametrize('count',[1,2,3,5])
def test_home_preview_region_is_bounded_labelled_and_keeps_match_links(app_module,language,count):
    matches=[{'id':f'QA-{i}','home_team':f'Home {i}','away_team':f'Away {i}',
        'competition':'SIMULATED_QA','source':'SIMULATED_QA','kickoff_iso':'2026-09-14T23:30:00Z',
        'client_schedule_label':'15/09/2026 01:30','status_info':{'key':'UPCOMING'}} for i in range(count)]
    dom=Structure(render_home(app_module,{'match_hub':{'upcoming':matches}},language))
    region,=[n for n in dom.nodes if 'data-home-match-previews' in n['attrs']]
    assert region['attrs']['role']=='region' and region['attrs']['tabindex']=='0'
    assert region['attrs']['aria-label']==translate('Partidos destacados',language)
    cards=[n for n in dom.nodes if 'data-v934-match-id' in n['attrs'] and region in n['parents']]
    assert [n['attrs']['data-v934-match-id'] for n in cards]==[f'QA-{i}' for i in range(min(3,count))]
    for card in cards:
        identity=card['attrs']['data-v934-match-id']
        assert any(n['attrs'].get('href')=='/match/'+identity and card in n['parents'] for n in dom.nodes)
        number=identity.rsplit('-',1)[-1]
        crests=[n['attrs']['title'] for n in dom.nodes if card in n['parents'] and 'v933-team-logo' in n['attrs'].get('class','')]
        assert crests==[f'Home {number}',f'Away {number}']
        assert any(n['attrs'].get('data-value')==identity and card in n['parents'] for n in dom.nodes)

@pytest.mark.parametrize('language',['es','en','fr'])
@pytest.mark.parametrize('mode',['full','summary'])
def test_pick_compact_mode_preserves_reason_risks_and_actions(app_module,language,mode):
    pick={'id':'qa-pick','match_id':'qa-match','home_team':'QA Home','away_team':'QA Away',
          'market':'Resultado final','selection':'QA Home','odds':1.82,'status':'published',
          'reasoning':'<not-markup> SIMULATED_QA','risk_note':'RISK_QA','invalidation':'STOP_QA'}
    with app_module.app.test_request_context('/app',headers={'Accept-Language':language}):
        macro=app_module.app.jinja_env.get_template('components/v933_ui.html').make_module({'current_user':None})
        html=str(macro.pick_card(pick,True,mode))
        default=str(macro.pick_card(pick,True))
    assert '&lt;not-markup&gt;' in html and '<not-markup>' not in html
    assert 'RISK_QA' in html and 'STOP_QA' in html
    assert 'href="/match/qa-match"' in html and 'href="/picks"' in html
    assert 'data-v934-odds>1.82<' in html
    assert ('class="v933-pick-summary"' in html) is (mode=='summary')
    if mode=='full':
        assert html==default
    else:
        assert '<details><summary>'+translate('Contexto y riesgos',language)+'</summary>' in html

@pytest.mark.parametrize('status',['draft','blocked'])
def test_unpublishable_pick_has_no_summary_or_odds(app_module,status):
    with app_module.app.test_request_context('/app'):
        macro=app_module.app.jinja_env.get_template('components/v933_ui.html').make_module({'current_user':None})
        html=str(macro.pick_card({'id':'qa','status':status},True,'summary'))
    assert 'data-v934-odds' not in html and 'v933-pick-summary' not in html

def test_home_presentation_is_scoped_without_new_navigation_or_artist_changes():
    css=(ROOT/'static/v933-product.css').read_text(encoding='utf-8')
    home=(ROOT/'templates/client_app_center.html').read_text(encoding='utf-8')
    assert '.ns16-home-sports .ns16-match-row[data-home-match-previews]' in css
    assert 'grid-auto-columns: 86%' in css and 'scroll-snap-type: x proximity' in css
    assert '.ns16-featured-pick .v933-pick-card dl > div' in css
    assert "pick_card(picks[0], true, 'summary')" in home
    assert 'ns16-journey' not in home and 'data-home-match-previews' not in (ROOT/'templates/calendar.html').read_text(encoding='utf-8')
    assert catalogue_issues()==[]
    for source in ['Contexto y riesgos','Resultado final','Cuota actual','Última cuota registrada','MEDIO']:
        assert all(translate(source,lang)!=source for lang in ('en','fr'))
