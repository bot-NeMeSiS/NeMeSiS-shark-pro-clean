from datetime import datetime,timedelta,timezone
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
