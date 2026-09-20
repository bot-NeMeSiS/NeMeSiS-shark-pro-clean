from datetime import datetime,timedelta,timezone
import json
import sqlite3
from engines import founder_os_engine as founder

def test_obligation_due_alert_and_paid_rollover(tmp_path):
    db=str(tmp_path/'founder.db'); due=(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()
    saved=founder.save_obligation(db,{'provider_key':'the_odds_api','label':'The Odds API','amount':'49','cadence':'monthly','due_date':due,'payment_status':'PENDING','auto_renew':'1'})
    assert saved['obligation']['effective_state']=='DUE_NOW'
    obs=founder.obligations_snapshot(db); providers=founder.providers_snapshot(db,obs); founder.sync_generated_alerts(db,obs,providers)
    assert founder.alerts_snapshot(db)['counts']['HIGH']>=1
    paid=founder.mark_obligation_paid(db,saved['obligation']['id']); assert paid['ok'] and paid['obligation']['due_date']!=due

def test_unknown_billing_is_never_inferred_paid(tmp_path,monkeypatch):
    db=str(tmp_path/'unknown.db'); monkeypatch.setenv('THE_ODDS_API_KEY','secret-not-visible'); monkeypatch.setenv('ENABLE_ODDS_API','true')
    snap=founder.founder_os_snapshot(db); odds=next(i for i in snap['providers']['items'] if i['key']=='the_odds_api')
    assert odds['configured'] is True and odds['billing_state']=='UNKNOWN'; assert 'secret-not-visible' not in str(snap)

def test_push_configuration_never_exposes_private_key(monkeypatch):
    monkeypatch.setenv('FOUNDER_PUSH_ENABLED','true'); monkeypatch.setenv('VAPID_PUBLIC_KEY','public-test'); monkeypatch.setenv('VAPID_PRIVATE_KEY','PRIVATE-CANARY'); monkeypatch.setenv('VAPID_SUBJECT','https://example.invalid')
    cfg=founder.push_configuration(); assert cfg['configured'] and cfg['public_key']=='public-test' and 'PRIVATE-CANARY' not in str(cfg)

def test_push_subscription_public_result_is_hashed(tmp_path):
    db=str(tmp_path/'push.db'); result=founder.save_push_subscription(db,{'endpoint':'https://push.example.invalid/a','keys':{'p256dh':'p','auth':'a'}})
    assert result['ok'] and 'push.example.invalid' not in str(result); assert founder.push_snapshot(db)['subscriptions']==1


def _save_automation_state(db,key,payload):
    conn=sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS automation_state(key TEXT PRIMARY KEY,value_json TEXT,updated_at TEXT)")
    conn.execute("INSERT OR REPLACE INTO automation_state(key,value_json,updated_at) VALUES (?,?,?)",(key,json.dumps(payload),datetime.now(timezone.utc).isoformat(timespec="seconds")))
    conn.commit(); conn.close()


def test_founder_os_surfaces_canonical_sports_freshness_from_last_tick(tmp_path):
    db=str(tmp_path/'sports-freshness.db')
    observed=datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save_automation_state(db,'telegram_tick_last_detail',{
        'called_at':observed,
        'finished_at':observed,
        'compact':{
            'sports_pipeline':{
                'data_freshness':{
                    'state':'PARTIAL',
                    'entity_timestamps_evaluated':True,
                    'scope':'MATCH_ROWS_CANONICAL_PROVIDER_CLOCKS',
                    'total':10,
                    'fresh':3,
                    'observed':4,
                    'stale':2,
                    'not_established':1,
                    'reason':'Parte de la muestra está stale o no establece reloj válido.',
                    'stale_samples':[{
                        'fixture_id':'stale-founder-1',
                        'home_team':'Equipo A',
                        'away_team':'Equipo B',
                        'competition':'Liga Founder',
                        'provider':'SportsDB',
                        'provider_observed_at':'2026-09-20T09:00:00+00:00',
                        'freshness_seconds':5400,
                        'stale_reason':'LIVE_OBSERVATION_TOO_OLD',
                        'status_canonical':'LIVE',
                    }],
                }
            }
        }
    })

    snap=founder.founder_os_snapshot(db)
    freshness=snap['sports_data_freshness']

    assert freshness['contract']=='NEMESIS-FOUNDER-SPORTS-FRESHNESS-V1'
    assert freshness['state']=='PARTIAL'
    assert freshness['total']==10
    assert freshness['fresh']==3
    assert freshness['stale']==2
    assert freshness['not_established']==1
    assert freshness['source_state_key']=='telegram_tick_last_detail'
    assert freshness['provider_calls']==0
    assert isinstance(freshness['evidence_age_seconds'],int)
    assert freshness['stale_samples'][0]['fixture_id']=='stale-founder-1'
    assert freshness['stale_samples'][0]['provider']=='SportsDB'
    assert freshness['stale_samples'][0]['freshness_seconds']==5400
    assert freshness['stale_samples'][0]['stale_reason']=='LIVE_OBSERVATION_TOO_OLD'
    assert any(item['category']=='SPORTS_DATA' and item['severity']=='WARNING' for item in snap['alerts']['items'])


def test_founder_os_does_not_infer_sports_freshness_without_evidence(tmp_path):
    db=str(tmp_path/'sports-unknown.db')
    snap=founder.founder_os_snapshot(db)
    freshness=snap['sports_data_freshness']

    assert freshness['state']=='NOT_ESTABLISHED'
    assert freshness['entity_timestamps_evaluated'] is False
    assert freshness['total']==0
    assert freshness['provider_calls']==0
    assert freshness['observed_at']==''
    assert freshness['evidence_age_seconds'] is None
    assert freshness['stale_samples']==[]
    sports_alert=next(item for item in snap['alerts']['items'] if item['category']=='SPORTS_DATA')
    assert sports_alert['severity']=='HIGH'
    assert sports_alert['push_eligible'] is False
