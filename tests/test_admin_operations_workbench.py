"""Synthetic evidence, no providers or product writes. Existing admin routes only."""
from copy import deepcopy
from pathlib import Path
import pytest
from engines.admin_operations_workbench import build_admin_workbench, TOOLS, MAX_ITEMS
from blueprints.admin_productivity import PAGES, create_admin_productivity_blueprint

ROOT=Path(__file__).resolve().parents[1]


def issue(ident='OPS-QA',**kw):
    return {'issue_id':ident,'title':'Revisar recepción de cuotas','area':'sports_data','severity':'high',
            'evidence_state':'NO_CERTIFICADO','status':'CERTIFICATION_REQUIRED','evidence':'Sin recepción reciente confirmada.',
            'source':'Muestra sintética','next_action':'Comprobar cobertura sin forzar consultas.',**kw}


def sample():
    return {'generated_at_madrid':'2026-09-23T09:00:00+02:00','incidents':[
        issue('pending',severity='critical'),
        issue('confirmed',title='Error de lectura',area='database',evidence_state='CONFIRMADO',status='OPEN'),
        issue('investigate',title='Incidencia sin clasificación',evidence_state='OTRO',status='OPEN'),
    ]}


@pytest.mark.parametrize('value',[None,{},'bad',True,[]])
def test_missing_collection_is_unknown_not_empty(value):
    s={'incidents':value} if value!=[] else {}
    w=build_admin_workbench(s)
    assert w['state']=='UNAVAILABLE' and w['counts'] is None and w['total_supplied'] is None


def test_verified_empty_preserves_zero_not_global_health():
    w=build_admin_workbench({'incidents':[]})
    assert w['state']=='READABLE' and w['counts']['confirmed']==0 and w['next_task'] is None
    assert 'health' not in w


def test_confirmed_first_even_when_certification_has_higher_severity():
    w=build_admin_workbench(sample())
    assert [t['id'] for t in w['tasks']]==['confirmed','investigate','pending']
    assert w['counts']=={'confirmed':1,'verify':1,'investigate':1}


@pytest.mark.parametrize('state',['NO_CERTIFICADO','BLOQUEADO_POR_ACCESO','HIPOTESIS','REQUIERE_REVISION'])
def test_missing_evidence_never_becomes_confirmed_by_high_priority(state):
    w=build_admin_workbench({'incidents':[issue(evidence_state=state,status='OPEN',severity='critical')]})
    assert w['tasks'][0]['category']=='verify'


def test_input_and_review_status_not_mutated():
    data=sample();orig=deepcopy(data);w=build_admin_workbench(data)
    assert data==orig and w['external_calls']==w['writes']==0
    assert 'NO significa resolverla' in w['tasks'][0]['brief']


def test_targets_come_only_from_internal_registry():
    w=build_admin_workbench({'incidents':[issue(href='https://invalid.test/evil',area='https://invalid.test/evil')]})
    assert w['tasks'][0]['href']=='/admin/sentinel-issues'
    assert all(t['href'].startswith('/admin/') and '?' not in t['href'] for t in w['tools'])


def test_duplicate_identifiers_preserved_with_distinct_dom_and_warning():
    w=build_admin_workbench({'incidents':[issue(),issue(evidence='Otro hallazgo')]})
    assert len(w['tasks'])==2 and len({t['dom_id'] for t in w['tasks']})==2
    assert all(t['identity_conflict'] for t in w['tasks'])


def test_malformed_rows_not_silently_counted_as_clear():
    w=build_admin_workbench({'incidents':[None,{},issue()]})
    assert w['state']=='PARTIAL' and w['invalid']==2 and w['displayed']==1 and w['total_supplied']==3


def test_explicit_bound_reports_scope():
    w=build_admin_workbench({'incidents':[issue(str(i)) for i in range(MAX_ITEMS+3)]})
    assert w['truncated'] and w['displayed']==MAX_ITEMS and w['total_supplied']==MAX_ITEMS+3


@pytest.mark.parametrize('time',['not a date','2026-09-23T10:00:00','',None])
def test_unknown_or_naive_clock_not_presented_as_verified(time):
    assert build_admin_workbench({'incidents':[], 'generated_at_madrid':time})['generated_at']==''


def test_generated_time_is_not_provider_clock():
    assert build_admin_workbench(sample())['timestamp_scope']=='LOCAL_SNAPSHOT_NOT_PROVIDER_FRESHNESS'


def test_sensitive_assignment_redacted_and_no_untrusted_link():
    w=build_admin_workbench({'incidents':[issue(evidence='token=synthetic-private password:synthetic-password https://u:p@invalid.test')]})
    text=w['tasks'][0]['brief']
    assert 'synthetic-private' not in text and 'synthetic-password' not in text and 'u:p@' not in text


def test_display_is_deterministic_and_not_scheduled():
    assert build_admin_workbench(sample())==build_admin_workbench(sample())
    source=(ROOT/'engines/admin_operations_workbench.py').read_text()
    for token in ('sqlite3','requests','subprocess','os.environ','open('):assert token not in source


@pytest.mark.parametrize('role',[None,'FREE','PRO'])
@pytest.mark.parametrize('route',['/admin/operations-center','/admin/sala-control','/api/admin/operations-center/summary'])
def test_existing_auth_precedes_snapshot(app_module,monkeypatch,role,route):
    def forbidden():pytest.fail('Unauthorized request reached snapshot')
    monkeypatch.setattr(app_module,'v938_operations_snapshot',forbidden)
    c=app_module.app.test_client()
    if role:
        with c.session_transaction() as sess:sess.update(user_id='synthetic-account',user_role=role,membership=role)
    r=c.get(route)
    assert r.status_code in (302,303,403)
    assert r.headers['Cache-Control']=='private, no-store'


def test_context_is_not_injected_into_client_pages():
    from flask import Flask,render_template_string
    a=Flask(__name__);a.register_blueprint(create_admin_productivity_blueprint(lambda:True))
    @a.get('/client')
    def page():return render_template_string('{{ admin_workbench is defined }}')
    assert a.test_client().get('/client').data==b'False'


def test_auth_callback_exception_does_not_inject_helper():
    from flask import Flask,render_template_string
    def fail():raise RuntimeError('authentication unavailable')
    a=Flask(__name__);a.register_blueprint(create_admin_productivity_blueprint(fail))
    @a.get('/admin/operations-center')
    def page():return render_template_string('{{ admin_workbench is defined }}')
    assert a.test_client().get('/admin/operations-center').data==b'False'


def test_registered_registry_links_and_aliases_exist(app_module):
    adapter=app_module.app.url_map.bind('localhost')
    for _,_,href,_ in TOOLS:assert adapter.match(href,method='GET')
    for path in PAGES:assert adapter.match(path,method='GET')[0]=='admin_v938_operations_center_page'


def test_real_template_and_route_render_with_synthetic_snapshot(app_module,monkeypatch):
    monkeypatch.setattr(app_module,'v938_operations_snapshot',lambda:{**sample(),'next_issue_id':'pending','monitoring':{'dead_man':{}},'scores':{},'global_score':{},'release_1_gate':{}})
    monkeypatch.setattr(app_module,'dashboard_data',lambda:{})
    monkeypatch.setattr(app_module,'load_operations_reviews',lambda *_:{'reviews':[]})
    c=app_module.app.test_client()
    with c.session_transaction() as sess:sess.update(user_id='admin-workbench-qa',user_role='ADMIN',membership='ADMIN')
    r=c.get('/admin/operations-center');text=r.get_data(as_text=True)
    assert r.status_code==200 and 'Tu jornada de operaciones' in text
    assert text.count('id="operations-incidents"')==1
    assert 'data-admin-workbench="NEMESIS-ADMIN-WORKBENCH-V1"' in text
    assert '/static/admin-operations.js' in text and 'id="v938-safe-actions"' in text
    assert r.headers['Cache-Control']=='private, no-store' and 'Cookie' in r.headers['Vary']


def test_normal_routes_no_write_semantics_introduced():
    text=(ROOT/'blueprints/admin_productivity.py').read_text()
    assert '@bp.route' not in text and '@bp.post' not in text


@pytest.mark.parametrize('payload',[{}, {'incidents':[]}, {'incidents':None}])
def test_missing_diagnostic_sections_do_not_crash_or_invent_workbench_health(app_module,monkeypatch,payload):
    monkeypatch.setattr(app_module,'v938_operations_snapshot',lambda:payload)
    monkeypatch.setattr(app_module,'dashboard_data',lambda:{})
    monkeypatch.setattr(app_module,'load_operations_reviews',lambda *_:{'reviews':[]})
    c=app_module.app.test_client()
    with c.session_transaction() as sess:sess.update(user_id='admin-partial-qa',user_role='ADMIN',membership='ADMIN')
    response=c.get('/admin/operations-center')
    assert response.status_code==200
    text=response.get_data(as_text=True)
    assert 'No hay una observación independiente disponible' in text
    if payload.get('incidents') != []:assert 'No equivale a cero incidencias' in text
