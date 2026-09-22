"""Read correctness on synthetic SQLite files; no live provider or account access."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import socket
import sqlite3

import pytest
from engines import api_usage_guard_engine as guard

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=guard.TZ)
ENV = {'API_FOOTBALL_DAILY_CALL_BUDGET':'5','ODDS_API_DAILY_CALL_BUDGET':'3'}

@pytest.fixture(autouse=True)
def fixed_clock_and_no_network(monkeypatch):
    monkeypatch.setattr(guard,'madrid_now',lambda: NOW)
    def deny(*args,**kwargs):
        raise AssertionError('No network in read-only budget tests')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)

@pytest.fixture
def db(tmp_path):
    path=tmp_path/'qa.db'
    with closing(sqlite3.connect(path)) as conn,conn:
        guard.ensure_api_usage_guard_schema(conn)
    return path

@pytest.mark.parametrize('relative',['missing.db','missing-folder/private.db'])
def test_budget_missing_db_is_unknown_and_not_created(tmp_path,relative):
    path=tmp_path/relative
    result=guard.api_usage_snapshot(str(path),ENV)
    assert not path.exists()
    assert result['state']=='NOT_INITIALIZED' and not result['ok']
    assert result['used_estimated']=={'api_football':None,'odds_api':None}
    assert result['remaining_estimated']=={'api_football':None,'odds_api':None}
    assert 'private.db' not in str(result)

@pytest.mark.parametrize('reader',['snapshot','cache'])
def test_existing_database_is_not_migrated_by_a_read(tmp_path,reader):
    path=tmp_path/'unrelated.db'
    with closing(sqlite3.connect(path)) as conn,conn:
        conn.execute('CREATE TABLE unrelated(id INTEGER)')
    before=path.read_bytes()
    if reader=='snapshot':
        result=guard.api_usage_snapshot(str(path),ENV)
        assert result['state']=='NOT_INITIALIZED'
    else:
        assert guard.cache_get(str(path),'api_football','k') is None
    assert path.read_bytes()==before

@pytest.mark.parametrize('path_kind',['corrupt','directory'])
def test_unreadable_budget_never_reports_full_balance(tmp_path,path_kind):
    path=tmp_path/'private-path'
    path.mkdir() if path_kind=='directory' else path.write_bytes(b'not a SQLite database')
    result=guard.api_usage_snapshot(str(path),ENV)
    assert not result['ok'] and result['state']=='READ_UNAVAILABLE'
    assert all(v is None for v in result['remaining_estimated'].values())
    assert 'private-path' not in str(result)


def test_empty_valid_ledger_is_a_known_zero_not_provider_quota(db):
    result=guard.api_usage_snapshot(str(db),ENV)
    assert result['state']=='READY' and result['ok']
    assert result['used_estimated']=={'api_football':0,'odds_api':0}
    assert result['remaining_estimated']=={'api_football':5,'odds_api':3}
    assert result['usage_scope']=='LOCAL_GUARD_RESERVATIONS_NOT_PROVIDER_QUOTA'
    assert not result['provider_quota_verified']


def test_known_reservations_preserve_zero_remaining_and_read_only(db):
    assert guard.allow_api_job(str(db),'api_football','qa',5,ENV)['ok']
    before=db.read_bytes()
    result=guard.api_usage_snapshot(str(db),ENV)
    assert result['ok'] and result['used_estimated']['api_football']==5
    assert result['remaining_estimated']['api_football']==0
    assert db.read_bytes()==before


def test_no_partial_balances_escape_a_failed_read(db,monkeypatch):
    original=sqlite3.connect
    class FailedSecondProvider(sqlite3.Connection):
        def execute(self,sql,parameters=()):
            if parameters and parameters[0]=='odds_api' and 'SUM' in sql:
                raise sqlite3.OperationalError('secret-path-do-not-echo')
            return super().execute(sql,parameters)
    monkeypatch.setattr(guard.sqlite3,'connect',lambda *a,**kw:original(*a,**{**kw,'factory':FailedSecondProvider}))
    result=guard.api_usage_snapshot(str(db),ENV)
    assert not result['ok']
    assert all(v is None for v in result['remaining_estimated'].values())
    assert 'secret-path' not in str(result)


def test_read_functions_close_connections_and_only_execute_reads(db,monkeypatch):
    original=sqlite3.connect; connections=[]; statements=[]
    def watched(*args,**kwargs):
        conn=original(*args,**kwargs);conn.set_trace_callback(statements.append);connections.append(conn)
        return conn
    monkeypatch.setattr(guard.sqlite3,'connect',watched)
    assert guard.api_usage_snapshot(str(db),ENV)['ok']
    assert guard.cache_get(str(db),'api_football','missing') is None
    assert not any(s.lstrip().upper().startswith(('CREATE','ALTER','INSERT','UPDATE','DELETE','REPLACE')) for s in statements)
    assert sum('query_only' in s.lower() for s in statements)==2
    for conn in connections:
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):conn.execute('SELECT 1')


def test_reader_can_run_while_a_reserved_writer_is_waiting(db):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute('BEGIN IMMEDIATE')
        result=guard.api_usage_snapshot(str(db),ENV)
        assert result['ok'] and result['used_estimated']['api_football']==0
        conn.rollback()


def test_exclusive_lock_is_unknown_not_full_balance(db):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute('BEGIN EXCLUSIVE')
        result=guard.api_usage_snapshot(str(db),ENV)
        assert not result['ok'] and all(v is None for v in result['remaining_estimated'].values())
        conn.rollback()

@pytest.mark.parametrize('expires',['','invalid','2026-09-22T12:00:00',NOW.isoformat(),(NOW-timedelta(seconds=1)).isoformat()])
def test_missing_invalid_or_expired_cache_clock_is_a_miss(db,expires):
    with closing(sqlite3.connect(db)) as conn,conn:
        conn.execute('INSERT INTO api_response_cache VALUES(?,?,?,?,?)',('k','api_football','{"value":7}',expires,NOW.isoformat()))
    assert guard.cache_get(str(db),'api_football','k') is None


def test_live_cache_is_read_without_mutation_and_wrong_provider_is_not_used(db):
    guard.cache_set(str(db),'api_football','k',{'value':0},60)
    before=db.read_bytes()
    assert guard.cache_get(str(db),'api_football','k')=={'value':0}
    assert guard.cache_get(str(db),'odds_api','k') is None
    assert db.read_bytes()==before


def test_cache_miss_does_not_create_file(tmp_path):
    path=tmp_path/'not-created.db'
    assert guard.cache_get(str(path),'api_football','k') is None
    assert not path.exists()


def test_cache_ttl_is_elapsed_time_during_madrid_fallback(db,monkeypatch):
    before_fallback=datetime(2026,10,25,2,59,50,tzinfo=guard.TZ,fold=0)
    after_expiry=(before_fallback.astimezone(timezone.utc)+timedelta(seconds=121)).astimezone(guard.TZ)
    monkeypatch.setattr(guard,'madrid_now',lambda:before_fallback)
    guard.cache_set(str(db),'api_football','clock',{'value':1},120)
    monkeypatch.setattr(guard,'madrid_now',lambda:after_expiry)
    assert guard.cache_get(str(db),'api_football','clock') is None


def test_explicit_empty_env_does_not_import_process_keys(db,monkeypatch):
    monkeypatch.setenv('API_FOOTBALL_KEY','synthetic-not-a-key')
    monkeypatch.setenv('API_FOOTBALL_DAILY_CALL_BUDGET','999')
    result=guard.api_usage_snapshot(str(db),env={})
    assert result['budgets']['api_football']==120
    assert not result['configured']['api_football']


def test_current_reservation_uses_storage_even_if_display_unavailable(db,monkeypatch):
    monkeypatch.setattr(guard,'api_usage_snapshot',lambda *a,**kw: {'ok':False,'remaining_estimated':{'api_football':None}})
    assert guard.allow_api_job(str(db),'api_football','first',5,ENV)['ok']
    assert not guard.allow_api_job(str(db),'api_football','extra',1,ENV)['ok']

@pytest.mark.parametrize('bad',[1.5,'unmeasured',None])
def test_ambiguous_approved_estimates_do_not_grant_more_credit(db,bad):
    with closing(sqlite3.connect(db)) as conn,conn:
        conn.execute('INSERT INTO api_usage_guard(provider,window_key,estimated_calls,status) VALUES(?,?,?,?)',
            ('api_football','2026-09-22',bad,'ALLOWED'))
    display=guard.api_usage_snapshot(str(db),ENV)
    assert not display['ok'] and display['remaining_estimated']['api_football'] is None
    result=guard.allow_api_job(str(db),'api_football','must-not-be-approved',1,ENV)
    assert not result['ok'] and result['remaining_before'] is None
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute('SELECT COUNT(*) FROM api_usage_guard').fetchone()[0]==1

@pytest.mark.parametrize('state',['READY','NOT_INITIALIZED','READ_UNAVAILABLE'])
def test_admin_displays_unknown_without_technical_null_or_full_balance(state):
    from jinja2 import Environment,ChoiceLoader,DictLoader,FileSystemLoader,select_autoescape
    root=Path(__file__).resolve().parents[1]
    env=Environment(loader=ChoiceLoader([DictLoader({
       'base.html':'{% block content %}{% endblock %}',
       'partials/admin_visual_system.html':
         "{% macro shell(a,b,c) %}{{ caller() }}{% endmacro %}"
         "{% macro kpi(label,value,detail,icon,tone) %}<div><b>{{ label }}</b><strong>{{ value }}</strong><small>{{ detail }}</small></div>{% endmacro %}"
         "{% macro status(label,tone) %}{{ label }}{% endmacro %}"
       }),FileSystemLoader(root/'templates')]),autoescape=select_autoescape())
    ready=state=='READY'
    usage={'ok':ready,'state':state,'remaining_estimated':{'api_football':0 if ready else None,'odds_api':3 if ready else None}}
    status={'api_usage':usage,'ok':True,'madrid_now':'22/09/2026 12:00','telegram_sent_today':0,
            'jobs_failed':[],'results_pending':0,'next_jobs':[]}
    html=env.get_template('admin_daily_automation.html').render(data={'daily_automation_os':{'status':status,'runs':[],'telegram_policy':{}}})
    assert '>None<' not in html and '>null<' not in html
    if ready:
        assert '<b>API Football</b><strong>0</strong>' in html
    else:
        assert html.count('<strong>No verificable</strong>')==2
        assert '<b>Estado general</b><strong>Revisar</strong>' in html
        assert '<b>API Football</b><strong>5</strong>' not in html
    assert 'Reserva local, no saldo del proveedor' in html


def test_read_database_uri_handles_spaces_and_hash_in_path(tmp_path):
    path=tmp_path/'ledger # with spaces.db'
    with closing(sqlite3.connect(path)) as conn,conn:
        guard.ensure_api_usage_guard_schema(conn)
    assert guard.api_usage_snapshot(str(path),ENV)['ok']


def test_corrupt_cache_json_never_causes_a_write(db):
    with closing(sqlite3.connect(db)) as conn,conn:
        conn.execute('INSERT INTO api_response_cache VALUES(?,?,?,?,?)',('k','api_football','{broken',(NOW+timedelta(minutes=1)).isoformat(),NOW.isoformat()))
    before=db.read_bytes()
    assert guard.cache_get(str(db),'api_football','k') is None
    assert db.read_bytes()==before


def test_main_admin_surface_preserves_unknown_budget_and_access_control(app_module,monkeypatch):
    from engines import daily_automation_engine as daily
    unknown=guard.api_usage_snapshot(str(Path(app_module.DB_PATH).parent/'definitely-absent-usage.db'),ENV)
    assert not unknown['ok']
    monkeypatch.setattr(daily,'api_usage_snapshot',lambda *args,**kwargs:unknown)
    client=app_module.app.test_client()
    assert client.get('/api/admin/daily-automation/status').status_code==403
    with client.session_transaction() as sess:
        sess['user_role']='ADMIN'
    page=client.get('/admin/daily-automation')
    assert page.status_code==200
    assert 'No verificable' in page.get_data(as_text=True)
    response=client.get('/api/admin/daily-automation/status')
    assert response.status_code==200
    # The nested estimate remains explicitly unknown, independent of outer status.
    assert 'LOCAL_GUARD_RESERVATIONS_NOT_PROVIDER_QUOTA' in response.get_data(as_text=True)
    assert '"api_football":null' in response.get_data(as_text=True).replace(' ','')


def test_recursive_cache_decode_error_is_a_safe_miss(db,monkeypatch):
    # App initialization can raise Python's recursion limit, so do not assume
    # that an arbitrary JSON depth causes an exception on every test runner.
    with closing(sqlite3.connect(db)) as conn,conn:
        conn.execute('INSERT INTO api_response_cache VALUES(?,?,?,?,?)',('k','api_football','{}',(NOW+timedelta(minutes=1)).isoformat(),NOW.isoformat()))
    def recursive_decode(*args,**kwargs):
        raise RecursionError('synthetic decoder limit')
    monkeypatch.setattr(guard.json,'loads',recursive_decode)
    assert guard.cache_get(str(db),'api_football','k') is None
