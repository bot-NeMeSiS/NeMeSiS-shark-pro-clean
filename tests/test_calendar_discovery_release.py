"""Frontend publication regressions, SIMULATED_QA only. Backend rules unchanged."""
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
import pytest
from jinja2 import ChoiceLoader, DictLoader
from test_design02_calendar_presentation import Structure

ROOT=Path(__file__).resolve().parents[1]

def render_calendar(app_module, query='', language='es', facets=None, summary=None):
    env=app_module.app.jinja_env.overlay(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}),app_module.app.jinja_env.loader]))
    with app_module.app.test_request_context('/calendar'+query, headers={'Accept-Language':language}):
        calendar=app_module.v940_calendar_context(summary or {},app_module.request.args.get('lane','today'))
        if facets is not None: calendar['facets']=facets
        data={'calendar':calendar,'v925_calendar':{'has_real_data':False,'provider_status':'waiting_for_sync'}}
        params={'data':data};app_module.app.update_template_context(params)
        return env.get_template('calendar.html').render(**params), calendar

@pytest.mark.parametrize('language',['es','en','fr'])
def test_search_and_submit_are_always_outside_disclosures(app_module,language):
    html,_=render_calendar(app_module,language=language)
    dom=Structure(html)
    form,=dom.with_class('v940-calendar-filter-form')
    search,=[n for n in dom.nodes if 'data-v940-calendar-search' in n['attrs']]
    submit,=[n for n in dom.nodes if n['tag']=='button' and n['attrs'].get('type')=='submit' and form in n['parents']]
    for node in (search,submit):
        assert form in node['parents']
        assert not any(p['tag']=='details' for p in node['parents'])
    assert form['attrs']['method']=='get' and form['attrs']['action']=='/calendar'
    assert search['attrs']['maxlength']=='90'
    assert any(n['tag']=='label' and n['attrs'].get('for')==search['attrs']['id'] for n in dom.nodes)

@pytest.mark.parametrize('field,value', [('league','Liga ausente QA'),('country','País ausente QA'),('league','time'),('country','<img src=x onerror=alert(1)>')])
def test_selected_filter_survives_missing_facet_without_fabricated_count(app_module,field,value):
    from urllib.parse import urlencode
    html,cal=render_calendar(app_module,'?'+urlencode({field:value}),facets={'leagues':[],'countries':[]})
    dom=Structure(html)
    select,=[n for n in dom.nodes if n['tag']=='select' and n['attrs'].get('name')==field]
    options=[n for n in dom.nodes if n['tag']=='option' and select in n['parents'] and 'selected' in n['attrs']]
    assert len(options)==1
    assert options[0]['attrs']['value']==cal['filters'][field]
    assert options[0]['attrs'].get('data-v940-retained-selection')=='true'
    assert not any(n['tag']=='img' and n['attrs'].get('onerror') for n in dom.nodes)

@pytest.mark.parametrize('field,options_key,value',[('league','leagues','Liga QA'),('country','countries','España')])
def test_available_filter_is_not_duplicated(app_module,field,options_key,value):
    from urllib.parse import urlencode
    facets={options_key:[{'value':value,'label':value,'count':3}]}
    html,_=render_calendar(app_module,'?'+urlencode({field:value}),facets=facets)
    dom=Structure(html)
    select,=[n for n in dom.nodes if n['tag']=='select' and n['attrs'].get('name')==field]
    options=[n for n in dom.nodes if n['tag']=='option' and select in n['parents'] and n['attrs'].get('value')==value]
    assert len(options)==1 and 'selected' in options[0]['attrs']
    assert 'data-v940-retained-selection' not in options[0]['attrs']




@pytest.mark.parametrize('language',['es','en','fr'])
def test_clear_search_only_removes_search_and_keeps_context(app_module,language):
    html,cal=render_calendar(app_module,'?lane=week&date=2026-09-21&q=Club&league=Liga+QA&country=España&team=Club&status=Próximo&sort=time&with_pick=1',language)
    dom=Structure(html)
    link,=[n for n in dom.nodes if 'data-v940-clear-search' in n['attrs']]
    parsed=urlsplit(link['attrs']['href']); args=parse_qs(parsed.query)
    assert parsed.path=='/calendar' and not parsed.netloc
    assert 'q' not in args
    for key in ('lane','date','league','country','team','status','sort','with_pick'):
        assert args[key]==[cal['filters'][key]]


def test_form_fields_do_not_repeat_or_hide_the_query(app_module):
    html,cal=render_calendar(app_module,'?q=Club&team=Equipo&status=Próximo&sort=league&with_pick=1')
    dom=Structure(html); form,=dom.with_class('v940-calendar-filter-form')
    fields=[n for n in dom.nodes if form in n['parents'] and n['tag'] in ('input','select') and n['attrs'].get('name')]
    names=[n['attrs']['name'] for n in fields]
    assert len(names)==len(set(names))
    assert set(names)==set(app_module.V940_CALENDAR_STATE_KEYS)
    advanced,=dom.with_class('v940-calendar-advanced')
    assert form in advanced['parents']
    assert not any(n['tag']=='form' and form in n['parents'] for n in dom.nodes)


def test_selected_result_count_is_explicit_without_claiming_provider_coverage(app_module):
    html,cal=render_calendar(app_module)
    dom=Structure(html)
    count,=[n for n in dom.nodes if 'data-v940-visible-count' in n['attrs']]
    assert count['attrs']['data-v940-visible-count']==str(cal['counts']['visible'])
    assert 'data-calendar-empty="DATA_NOT_AVAILABLE"' in html


def test_calendar_preserves_non_search_contract_and_one_collection(app_module):
    html,_=render_calendar(app_module,'?q=QA')
    for marker in ['data-v940-calendar-experience','data-v940-calendar-context','data-v940-calendar-command','data-sports-contract','data-v940-calendar-collection']:
        assert marker in html
    assert html.count('data-v940-calendar-search')==1
    assert html.count('data-v940-calendar-collection')==1


