"""R8 keeps identity/lifecycle intact while correcting Home presentation."""
from copy import deepcopy
from pathlib import Path
import pytest
from engines.ui_localization_engine import translate
from test_design02_calendar_presentation import Structure
from test_design02_r7_home_composition import render_home

@pytest.mark.parametrize('language,prefix',[('es','En directo'),('en','Live'),('fr','En direct')])
@pytest.mark.parametrize('minute',["0'","67'","45+2'","90+10’","120"])
def test_compound_live_label_preserves_minute(language,prefix,minute):
    assert translate('En directo · '+minute,language)==prefix+' · '+minute

@pytest.mark.parametrize('value',['En directo · pendiente','Nota: En directo · 67', 'En directo · 67\ntexto', 'Paris Saint-Germain', 'En directo · <b>67</b>'])
def test_compound_translation_does_not_translate_arbitrary_content(value):
    assert translate(value,'fr')==value

def fixture(identity):
    return {'id':identity,'home_team':'Home '+identity,'away_team':'Away '+identity,
            'competition':'SIMULATED_QA','source':'SIMULATED_QA','client_schedule_label':'14/09/2026 16:00',
            'status_info':{'key':'LIVE','is_live':True},'client_status_label':"En directo · 67'"}

@pytest.mark.parametrize('language',['es','en','fr'])
@pytest.mark.parametrize('live_count',[1,3,4])
def test_home_visible_live_ids_are_not_duplicated_in_spotlight(app_module,language,live_count):
    matches=[fixture(str(i)) for i in range(live_count)]
    data={'match_hub':{'sports_home':{'live_now':matches,'important_today':matches,
          'upcoming':[fixture('upcoming')],'recent_results':[matches[0],fixture('final')]}}}
    before=deepcopy(data)
    dom=Structure(render_home(app_module,data,language))
    live=[n for n in dom.nodes if 'data-v934-match-id' in n['attrs'] and any('ns16-live-priority' in p['attrs'].get('class','') for p in n['parents'])]
    featured=[n for n in dom.nodes if 'data-v934-match-id' in n['attrs'] and any('data-home-match-previews' in p['attrs'] for p in n['parents'])]
    live_ids=[n['attrs']['data-v934-match-id'] for n in live]
    featured_ids=[n['attrs']['data-v934-match-id'] for n in featured]
    assert live_ids==[str(i) for i in range(min(3,live_count))]
    assert not set(live_ids)&set(featured_ids)
    assert len(featured_ids)<=3
    if live_count==4: assert '3' in featured_ids
    else: assert 'upcoming' in featured_ids
    assert data==before

def test_quick_actions_remain_unique_with_same_destinations(app_module):
    dom=Structure(render_home(app_module,{}))
    nav,=[n for n in dom.nodes if 'ns16-home-actions' in n['attrs'].get('class','')]
    assert any('ns16-home-command' in p['attrs'].get('class','') for p in nav['parents'])
    assert [n['attrs']['href'] for n in dom.nodes if n['tag']=='a' and nav in n['parents']]==['/favorites','/memberships','/support']
    css=(Path(__file__).resolve().parents[1]/'static/v933-product.css').read_text(encoding='utf-8')
    assert 'grid-template-areas: "sports pick" "actions pick"' in css
    assert 'grid-template-areas: none' in css and 'grid-auto-columns: 86%' in css
