"""Synthetic API-Football odds refresh tests; no provider credentials or HTTP calls."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from engines import api_football_odds_engine as odds
from engines import api_football_live_tracker_engine as live_tracker
from engines.v935_launch_trust_engine import get_odds_freshness


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
ENV = {
    "API_FOOTBALL_KEY": "synthetic-key",
    "API_FOOTBALL_DAILY_CALL_BUDGET": "120",
    "API_FOOTBALL_ODDS_DAILY_CALL_BUDGET": "60",
    "API_FOOTBALL_ODDS_FIXTURES_PER_TICK": "2",
    "NEMESIS_LOCAL_MODE": "INTEGRATION_TEST",
    "NEMESIS_OFFLINE_MODE": "false",
    "NEMESIS_LOCAL_EXTERNAL_AUTHORIZED": "true",
    "NEMESIS_LOCAL_SAFE_MODE": "false",
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = str(tmp_path / "api-football-odds.sqlite")
    kickoff = NOW + timedelta(days=2)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("""CREATE TABLE matches(
            id TEXT PRIMARY KEY, external_id TEXT, source TEXT, match_date TEXT NOT NULL,
            kickoff_iso TEXT, kickoff_time TEXT, match_time TEXT, status TEXT,
            home_team TEXT, away_team TEXT, league_name TEXT, competition_name TEXT,
            bookmaker TEXT, odds_h2h_json TEXT, odds_updated_at TEXT)""")
        conn.execute("""CREATE TABLE odds_snapshots(
            id TEXT PRIMARY KEY, match_id TEXT, external_id TEXT, source TEXT, sport_key TEXT,
            league_name TEXT, bookmaker TEXT, market TEXT, home_team TEXT, away_team TEXT,
            home_price TEXT, draw_price TEXT, away_price TEXT, commence_time TEXT,
            payload_json TEXT, created_at TEXT)""")
        conn.execute("""INSERT INTO matches(id,external_id,source,match_date,kickoff_iso,status,
            home_team,away_team,league_name) VALUES(?,?,?,?,?,?,?,?,?)""",
            ("af-501", "501", "API-Football", kickoff.date().isoformat(),
             kickoff.isoformat(), "NS", "Granada", "Málaga", "LaLiga QA"))
    monkeypatch.setattr(odds, "_now", lambda: NOW)
    return path


def payload(fixture_id=501, *, update=None, bookmakers=None):
    return {
        "http_status": 200,
        "ok": True,
        "response": [{
            "fixture": {"id": fixture_id},
            "update": update or (NOW - timedelta(minutes=5)).isoformat(),
            "bookmakers": bookmakers if bookmakers is not None else [{
                "id": 8, "name": "Casa verificada", "bets": [{
                    "id": 1, "name": "Match Winner", "values": [
                        {"value": "Home", "odd": "2.10"},
                        {"value": "Draw", "odd": "3.25"},
                        {"value": "Away", "odd": "3.80"},
                    ],
                }],
            }],
        }],
    }


def query(path, sql, params=()):
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute(sql, params).fetchall()


def test_persists_only_verified_1x2_and_reuses_provider_cooldown(store):
    calls = []

    def transport(endpoint, params, timeout=0):
        calls.append((endpoint, params, timeout))
        return payload()

    first = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert first["status"] == "OK"
    assert first["external_calls"] == 1
    assert first["provider_observation_current"] is True
    assert first["provider_http"] == 200
    assert first["provider_http_statuses"] == [200]
    assert first["provider_quota_consulted"] is False
    assert first["snapshots_inserted"] == 1
    assert calls == [("odds", {"fixture": "501"}, 4)]
    assert query(store, "SELECT source,market,home_price,draw_price,away_price FROM odds_snapshots") == [
        ("API-Football", "1x2", "2.1", "3.25", "3.8")
    ]
    stored = json.loads(query(store, "SELECT odds_h2h_json FROM matches WHERE id='af-501'")[0][0])
    assert stored["source"] == "API-Football"
    assert stored["last_update"] == (NOW - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")

    second = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert second["external_calls"] == 0
    assert second["status"] == "NO_DUE_ODDS"
    assert len(calls) == 1


def test_no_data_or_unsupported_markets_never_create_prices(store):
    calls = []

    def transport(*args, **kwargs):
        calls.append(args)
        return {**payload(bookmakers=[{"id": 8, "name": "Casa", "bets": [{
            "name": "Over/Under", "values": [{"value": "Over 2.5", "odd": "1.90"}],
        }]}])}

    result = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert result["status"] == "NO_DATA"
    assert result["external_calls"] == 1
    assert result["snapshots_inserted"] == 0
    assert query(store, "SELECT COUNT(*) FROM odds_snapshots") == [(0,)]
    assert query(store, "SELECT COALESCE(odds_h2h_json,'') FROM matches WHERE id='af-501'") == [("",)]


def test_access_failure_sets_global_backoff_without_repeating_request(store):
    calls = []

    def transport(*args, **kwargs):
        calls.append(args)
        return {"ok": False, "response": [], "http_status": 403,
                "errors": {"access": "Your account is suspended"}}

    first = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert first["provider_observation_current"] is True
    assert first["provider_http"] == 403
    assert first["provider_http_statuses"] == [403]
    assert first["failure_categories"] == ["ACCOUNT_SUSPENDED"]
    assert first["external_calls"] == 1
    second = odds.refresh_api_football_odds_if_due(store, env=ENV, transport=transport)
    assert second["status"] == "PROVIDER_FAILURE_BACKOFF"
    assert second["external_calls"] == 0
    assert second["provider_observation_current"] is False
    assert second["provider_http"] is None
    assert len(calls) == 1


def test_local_budget_and_offline_mode_stop_before_transport(store):
    called = []
    transport = lambda *args, **kwargs: called.append(args) or payload()
    capped = odds.refresh_api_football_odds_if_due(
        store, env={**ENV, "API_FOOTBALL_ODDS_DAILY_CALL_BUDGET": "0"}, transport=transport,
    )
    assert capped["status"] == "DAILY_BUDGET"
    assert capped["external_calls"] == 0
    offline = odds.refresh_api_football_odds_if_due(
        store, env={**ENV, "NEMESIS_OFFLINE_MODE": "true"}, transport=transport,
    )
    assert offline["status"] == "OFFLINE_SAFE"
    assert offline["external_calls"] == 0
    assert called == []


def test_only_api_football_fixtures_are_candidates(store):
    with closing(sqlite3.connect(store)) as conn, conn:
        conn.execute("UPDATE matches SET source='TheSportsDB'")
    called = []
    result = odds.refresh_api_football_odds_if_due(
        store, env=ENV, transport=lambda *args, **kwargs: called.append(args),
    )
    assert result["status"] == "SKIPPED_NO_API_FOOTBALL_FIXTURE"
    assert result["external_calls"] == 0
    assert called == []


def test_historical_provider_rows_do_not_hide_upcoming_odds_fixtures(store):
    old_date = (NOW - timedelta(days=30)).date().isoformat()
    with closing(sqlite3.connect(store)) as conn, conn:
        conn.executemany(
            """INSERT INTO matches(id,external_id,source,match_date,kickoff_iso,status,
                home_team,away_team,league_name) VALUES(?,?,?,?,?,?,?,?,?)""",
            [(f"old-{index}", str(100000 + index), "api_football_live", old_date,
              f"{old_date}T12:00:00+00:00", "FT", "Old Home", "Old Away", "Archive")
             for index in range(3100)],
        )
    with closing(sqlite3.connect(store)) as conn:
        conn.row_factory = sqlite3.Row
        candidates = odds._candidates(conn, NOW, 14)
    assert [item["fixture_id"] for item in candidates] == ["501"]


def test_api_football_quote_freshness_matches_slow_provider_cadence(monkeypatch):
    monkeypatch.setenv("API_FOOTBALL_ODDS_FRESH_SECONDS", "10800")
    now = NOW
    api_quote = get_odds_freshness((now - timedelta(hours=2, minutes=30)).isoformat(), now,
                                   odds=2.1, source="API-Football", match_lifecycle="UPCOMING")
    other_quote = get_odds_freshness((now - timedelta(minutes=20)).isoformat(), now,
                                     odds=2.1, source="The Odds API", match_lifecycle="UPCOMING")
    expired_api_quote = get_odds_freshness((now - timedelta(hours=3, minutes=1)).isoformat(), now,
                                           odds=2.1, source="API-Football", match_lifecycle="UPCOMING")
    assert api_quote["status"] == "FRESH"
    assert api_quote["label"] == "Cuota reciente de API-Football"
    assert other_quote["status"] == "RECORDED"
    assert expired_api_quote["status"] == "STALE"


def test_api_get_captures_only_safe_http_status(monkeypatch):
    import urllib.error
    import io

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, *_args): return b'{"response":[],"errors":[],"paging":{}}'

    monkeypatch.setenv("API_FOOTBALL_KEY", "synthetic-never-log-this")
    monkeypatch.setattr(live_tracker.urllib.request, "urlopen", lambda *_a, **_k: Response())
    success = live_tracker._api_get("odds", {"fixture": "501"})
    assert success["http_status"] == 200
    assert "synthetic-never-log-this" not in json.dumps(success)

    def forbidden(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://example.invalid/odds", 403, "forbidden", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr(live_tracker.urllib.request, "urlopen", forbidden)
    failure = live_tracker._api_get("odds", {"fixture": "501"})
    assert failure["http_status"] == 403
    assert "synthetic-never-log-this" not in json.dumps(failure)


def test_the_odds_api_is_never_called_without_explicit_funding(monkeypatch):
    import app as app_module

    monkeypatch.setenv("THE_ODDS_API_FUNDED", "false")
    monkeypatch.setenv("THE_ODDS_API_KEY", "synthetic-only")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: pytest.fail("unfunded path must not initialize data"))
    result = app_module.sync_odds_events(limit=5)
    assert result["status"] == "UNFUNDED_NOT_CONFIGURED"
    assert result["funded"] is False
    assert result["external_calls"] == 0


def test_provider_wrapper_respects_zero_limit_and_reports_unfunded_optional_source(monkeypatch):
    import app as app_module

    refreshes = []
    optional_calls = []
    monkeypatch.setattr(app_module, "refresh_api_football_odds_if_due",
                        lambda *args, **kwargs: refreshes.append(kwargs.get("limit")) or {
                            "ok": True, "status": "DISABLED", "external_calls": 0, "processed": 0,
                            "fixtures_count": 0, "snapshots_inserted": 0,
                        })
    monkeypatch.setattr(app_module, "sync_odds_events",
                        lambda *args, **kwargs: optional_calls.append(1) or {"ok": True})
    monkeypatch.setenv("THE_ODDS_API_FUNDED", "false")
    monkeypatch.setenv("THE_ODDS_API_KEY", "synthetic-only")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")

    result = app_module.sync_provider_odds(limit=0)
    assert refreshes == [0]
    assert optional_calls == []
    assert result["external_calls"] == 0
    assert result["the_odds_api"]["status"] == "UNFUNDED_NOT_CONFIGURED"


def _master_odds_result(app_module, result, monkeypatch):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('odds_evidence_master',
        Path(__file__).resolve().parents[1]/'tools/render_cron_master_tick.py')
    master=importlib.util.module_from_spec(spec);spec.loader.exec_module(master)
    compact=app_module._cron_compact_payload('odds_sync',result,NOW.isoformat(),NOW.isoformat())
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self,*args):return json.dumps(compact).encode()
    monkeypatch.setattr(master.urllib.request,'urlopen',lambda *a,**k:Response())
    return compact,master.odds_tick('https://synthetic.invalid','synthetic-header-only')


def test_cached_rate_cooldown_survives_wrapper_compaction_and_master(store, app_module, monkeypatch):
    calls=[]
    def transport(*args,**kwargs):
        calls.append(1)
        return {'ok':False,'response':[],'http_status':429,
                'errors':{'requests':'Rate limit reached'}}
    monkeypatch.setattr(app_module,'refresh_api_football_odds_if_due',
        lambda *a,**k:odds.refresh_api_football_odds_if_due(store,env=ENV,transport=transport))
    monkeypatch.setattr(app_module,'odds_enabled',lambda:False)
    first=app_module.sync_provider_odds()
    _,fresh=_master_odds_result(app_module,first,monkeypatch)
    assert fresh['odds_status']=='FAIL'
    assert fresh['api_football_external_calls']==1
    monkeypatch.setattr(odds,'_now',lambda:NOW+timedelta(seconds=30))
    second=app_module.sync_provider_odds()
    compact,cached=_master_odds_result(app_module,second,monkeypatch)
    assert cached['odds_status']=='PARTIAL'
    assert cached['api_football_status']=='PROVIDER_FAILURE_BACKOFF'
    assert cached['api_football_failure_categories']==['RATE_OR_QUOTA']
    assert cached['odds_provider_failure_backoff'] is True
    assert cached['odds_controlled_deferrals']==['PROVIDER_FAILURE_COOLDOWN']
    assert cached['provider_observation_current'] is False
    assert cached['provider_http'] is None
    assert cached['external_calls']==0 and len(calls)==1
    assert not compact.get('errors_count') and not compact.get('error') and not compact.get('technical_errors')
    assert cached['api_football_observation_scope']=='REUSED'
    assert datetime.fromisoformat(cached['api_football_provider_observed_at'])==NOW
    assert compact['api_football_provider_http'] is None
    assert cached['the_odds_api_status']=='UNFUNDED_NOT_CONFIGURED'
    assert cached['the_odds_api_funded'] is False
    with sqlite3.connect(store) as conn:
        assert conn.execute('SELECT count(*) FROM odds_snapshots').fetchone()[0]==0


def _cached_rate_result():
    return {'ok':False,'status':'PROVIDER_FAILURE_BACKOFF','skipped':True,
        'provider_failure_backoff':True,'external_calls':0,'processed':0,'fixtures_count':0,
        'snapshots_inserted':0,'provider_observation_current':False,'provider_http':None,
        'provider_http_statuses':[],'failure_category':'RATE_OR_QUOTA',
        'failure_categories':['RATE_OR_QUOTA'],'errors':[],'items':[],
        'provider_observed_at':NOW.isoformat(),'retry_after':(NOW+timedelta(minutes=15)).isoformat()}


@pytest.mark.parametrize('change', [
    {'status':'PROVIDER_FAILURE'}, {'external_calls':1}, {'external_calls':False},
    {'provider_observation_current':True}, {'provider_http':429},
    {'failure_category':'AUTH_OR_ACCESS','failure_categories':['AUTH_OR_ACCESS']},
    {'failure_categories':['RATE_OR_QUOTA','AUTH_OR_ACCESS']},
    {'errors':['RATE_OR_QUOTA']}, {'technical_errors':['LOCAL_STORAGE_UNAVAILABLE']},
    {'skipped':False}, {'provider_failure_backoff':False}, {'retry_after':'invalid'},
    {'items':[{'status':'PROVIDER_FAILURE_INVALID_RESPONSE'}]},
])
def test_only_explicit_no_call_rate_cooldown_is_controlled(app_module, monkeypatch, change):
    raw={**_cached_rate_result(),**change}
    monkeypatch.setattr(app_module,'refresh_api_football_odds_if_due',lambda *a,**k:raw)
    monkeypatch.setattr(app_module,'odds_enabled',lambda:False)
    result=app_module.sync_provider_odds()
    _,observed=_master_odds_result(app_module,result,monkeypatch)
    assert result['ok'] is False
    assert result['controlled_deferrals']==[]
    assert observed['odds_status']=='FAIL'


@pytest.mark.parametrize('message,category', [
    ('Your account is suspended','ACCOUNT_SUSPENDED'),('Access denied','AUTH_OR_ACCESS'),
])
def test_cached_access_rejection_is_not_downgraded(store, app_module, monkeypatch, message, category):
    calls=[]
    def transport(*args,**kwargs):
        calls.append(1)
        return {'ok':False,'response':[],'http_status':403,'errors':{'access':message}}
    monkeypatch.setattr(app_module,'refresh_api_football_odds_if_due',
        lambda *a,**k:odds.refresh_api_football_odds_if_due(store,env=ENV,transport=transport))
    monkeypatch.setattr(app_module,'odds_enabled',lambda:False)
    app_module.sync_provider_odds()
    result=app_module.sync_provider_odds()
    _,observed=_master_odds_result(app_module,result,monkeypatch)
    assert observed['odds_status']=='FAIL'
    assert observed['api_football_failure_categories']==[category]
    assert observed['external_calls']==0 and len(calls)==1
    assert observed['provider_observation_current'] is False


def test_optional_provider_failure_wins_over_controlled_api_cooldown(app_module, monkeypatch):
    monkeypatch.setattr(app_module,'refresh_api_football_odds_if_due',lambda *a,**k:_cached_rate_result())
    monkeypatch.setattr(app_module,'odds_enabled',lambda:True)
    monkeypatch.setattr(app_module,'odds_funded',lambda:True)
    monkeypatch.setattr(app_module,'sync_odds_events',lambda **k:{
        'ok':False,'status':'PROVIDER_FAILURE','funded':True,'external_calls':1,
        'errors':['AUTH_REJECTED'],'quota':{'http_status':401,'error_type':'HTTPError'}})
    result=app_module.sync_provider_odds()
    _,observed=_master_odds_result(app_module,result,monkeypatch)
    assert result['ok'] is False and observed['odds_status']=='FAIL'
    assert observed['api_football_external_calls']==0
    assert observed['api_football_observation_scope']=='REUSED'
    assert observed['the_odds_api_external_calls']==1
    assert observed['the_odds_api_provider_http']==401


@pytest.mark.parametrize('saved_clock',['invalid','',None,'2026-10-19T12:00:00',(NOW+timedelta(days=1)).isoformat()])
def test_invalid_saved_clock_is_not_replaced_by_current_clock(store, app_module, monkeypatch, saved_clock):
    calls=[]
    def transport(*args,**kwargs):
        calls.append(1)
        return {'ok':False,'response':[],'http_status':429,'errors':{'requests':'Rate limit reached'}}
    monkeypatch.setattr(app_module,'refresh_api_football_odds_if_due',
        lambda *a,**k:odds.refresh_api_football_odds_if_due(store,env=ENV,transport=transport))
    monkeypatch.setattr(app_module,'odds_enabled',lambda:False)
    app_module.sync_provider_odds()
    with sqlite3.connect(store) as conn:
        conn.execute('UPDATE '+odds.STATE_TABLE+" SET provider_observed_at=? WHERE fixture_id='*'",(saved_clock,))
    monkeypatch.setattr(odds,'_now',lambda:NOW+timedelta(seconds=30))
    result=app_module.sync_provider_odds()
    _,observed=_master_odds_result(app_module,result,monkeypatch)
    assert observed['odds_status']=='PARTIAL'
    assert observed['api_football_provider_observed_at']==''
    assert observed['api_football_observation_scope']=='REUSED'
    assert not observed['provider_observation_current'] and len(calls)==1
