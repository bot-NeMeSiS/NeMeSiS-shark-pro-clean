import uuid

import pytest


@pytest.fixture(scope='module')
def runtime():
    from tools.local_desktop.run_sentinel_local import prepare
    module, store, blocked=prepare(db_name='organization-'+uuid.uuid4().hex+'.sqlite',allow_browser=True)
    module.app.config['TESTING']=True
    yield module,store
    assert blocked==[]


def client_as(module, role='ADMIN', identified=True):
    client=module.app.test_client()
    if role:
        with client.session_transaction() as session:
            session['user_role']=role
            if identified: session['user_id']='organization-admin'
            session['csrf_token']='organization-test-csrf'
    return client


def test_real_page_and_read_only_sources(runtime):
    module,store=runtime
    client=client_as(module)
    before=store.list('organization-admin')
    response=client.get('/api/admin/sentinel/project-control')
    assert response.status_code==200
    assert len(response.json['queue'])==24
    telegram = next(row for row in response.json['queue'] if row['ID'] == 'TG-001')
    assert telegram['Estado'] == 'QA'
    assert telegram['Ambito'] == 'LOCAL_ONLY'
    assert response.headers['Cache-Control']=='no-store'
    assert client.get('/api/admin/sentinel/project-control/sources/conversations').status_code==200
    assert client.get('/api/admin/sentinel/project-control/sources/.env').status_code==404
    assert client.post('/api/admin/sentinel/project-control',json={'action':'run'}).status_code==403
    assert client.post('/api/admin/sentinel/project-control',json={'action':'run'},headers={'X-CSRF-Token':'organization-test-csrf'}).status_code==405
    page=client.get('/admin/sentinel-issues')
    assert page.status_code==200
    assert b'data-project-control' in page.data
    assert b'data-project-row' in page.data
    assert store.list('organization-admin')==before


@pytest.mark.parametrize('role,identified', [(None,False), ('FREE',True), ('PRO',True), ('ELITE',True), ('ADMIN',False)])
def test_no_client_or_anonymous_admin_access(runtime,role,identified):
    module,_=runtime
    client=client_as(module,role,identified)
    for endpoint in ['/api/admin/sentinel/project-control','/api/admin/sentinel/project-control/sources/truth']:
        assert client.get(endpoint).status_code==403
    if role=='ADMIN':
        assert b'data-project-row' not in client.get('/admin/sentinel-issues').data


def test_production_context_not_inferred_from_docs(runtime,monkeypatch):
    module,_=runtime
    monkeypatch.setitem(module.app.config,'SENTINEL_JOBS_ENABLED',False)
    assert client_as(module).get('/api/admin/sentinel/project-control').status_code==503


def test_invalid_source_does_not_crash_panel_or_invent_counts(runtime,monkeypatch):
    module,_=runtime
    from engines.project_control_reader import ControlUnavailable
    def bad(_): raise ControlUnavailable('broken document')
    monkeypatch.setattr(module,'project_control_snapshot',bad)
    client=client_as(module)
    response=client.get('/api/admin/sentinel/project-control')
    assert response.status_code==503 and 'counts' not in response.json
    page=client.get('/admin/sentinel-issues')
    assert page.status_code==200 and b'data-project-row' not in page.data
