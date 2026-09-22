"""Synthetic odds and accounts only; no bets, providers, payments or Telegram."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import uuid

import pytest
from engines import combi_advisor_engine as eng
from engines import client_combi_store as store

NOW = datetime(2026,9,22,10,tzinfo=timezone.utc)


def fixture(i=1, **kw):
    return dict(id='m'+str(i),external_id='ext'+str(i),sport_key='soccer',home_team='Local '+str(i),
                away_team='Visitante '+str(i), competition_name='Liga QA',source='TheSportsDB API',status='NS',
                kickoff_iso=(NOW+timedelta(hours=i)).isoformat(),last_synced_at=NOW.isoformat(),**kw)


def pick(i=1, **kw):
    row = dict(id='p'+str(i),match_id='m'+str(i),home_team='Local '+str(i),away_team='Visitante '+str(i),
               status='published',market='1x2',selection='1',odds='1.5',bookmaker='Casa QA',
               membership_required='PRO',source='The Odds API',result_status='pending',
               updated_at=NOW.isoformat(),raw_json=json.dumps({'odds_updated_at':NOW.isoformat()}))
    row.update(kw); return row


def leg(i=1, **kw):
    q=dict(id='q'+str(i),odds='1.5',bookmaker='Casa QA',source='The Odds API',observed_at=NOW.isoformat())
    q.update(kw)
    return eng.assess_pick(pick(i),fixture(i),q,{'membership':'ELITE'},now=NOW)


@pytest.fixture
def db(tmp_path):
    path=tmp_path/'combis.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE users(id TEXT PRIMARY KEY,membership TEXT,role TEXT,membership_expires_at TEXT)')
        conn.executemany('INSERT INTO users VALUES (?,?,?,?)',[('a','ELITE','ELITE',''),('b','PRO','PRO',''),('f','FREE','FREE','')])
        for table,row in [('matches',fixture()),('picks',pick())]:
            conn.execute('CREATE TABLE '+table+'('+','.join('"'+k+'" TEXT' for k in row)+')')
        conn.execute('CREATE TABLE odds_snapshots(id TEXT,match_id TEXT,market TEXT,bookmaker TEXT,source TEXT,home_team TEXT,away_team TEXT,home_price TEXT,draw_price TEXT,away_price TEXT,created_at TEXT)')
        for i in range(1,18):
            for table,row in [('matches',fixture(i)),('picks',pick(i))]:
                conn.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in row)+')',list(row.values()))
    return str(path)


def preview_values():
    return {'pick_ids':['p1','p2'],'stake':'0,10'}


def ready_save(db,owner='a'):
    values=preview_values();result=store.make_preview(db,owner,values,now=NOW)
    return {**values,'revision':result['revision'],'request_id':uuid.uuid4().hex}


@pytest.mark.parametrize('bad',['NaN','inf','Infinity','-1','0','1e3','1001','1.234',True,None])
def test_amounts_fail_closed(bad):
    with pytest.raises(eng.CombiError):eng.preview([leg(1),leg(2)],bad,user={'membership':'ELITE'},now=NOW)


def test_exact_decimal_math_and_no_probability():
    result=eng.preview([leg(1,odds='1.25'),leg(2,odds='1.60')],'0.10',user={'membership':'PRO'},now=NOW)
    assert result['total_odds']=='2.0000'
    assert result['potential_return']=='0.20' and result['potential_net']=='0.10'
    assert result['probability'] is None and result['not_a_bet']


@pytest.mark.parametrize('status',['FT','LIVE','HT','PST','CANC','SUSP','ABD'])
def test_nonupcoming_match_is_never_a_leg(status):
    m=fixture();m['status']=status
    row=eng.assess_pick(pick(),m,{'odds':'2','bookmaker':'Q','source':'Q','observed_at':NOW.isoformat()},{'membership':'ELITE'},now=NOW)
    assert not row['eligible']


@pytest.mark.parametrize('status',['won','lost','void','draft','pending','archived'])
def test_nonpublished_pick_is_excluded(status):
    p=pick(status=status)
    assert not eng.assess_pick(p,fixture(),dict(odds='2',bookmaker='Q',source='Q',observed_at=NOW.isoformat()),{'membership':'ELITE'},now=NOW)['eligible']


@pytest.mark.parametrize('market,selection',[('dnb','1'),('double chance','1X'),('over 2.5','over'),('1x2','1X'),('1x2','gana local quizá'),('h2h_lay','1')])
def test_no_market_guessing(market,selection):
    assert not eng.outcome(pick(market=market,selection=selection),fixture())


@pytest.mark.parametrize('selection,expected',[('1','1'),('X','X'),('2','2'),('Local 1','1'),('Visitante 1','2'),('Empate','X')])
def test_all_three_outcomes(selection,expected):
    assert eng.outcome(pick(selection=selection),fixture())==expected


@pytest.mark.parametrize('minutes',[16,60,61,-1])
def test_stale_and_future_quotes_are_not_buildable(minutes):
    assert not leg(observed_at=(NOW-timedelta(minutes=minutes)).isoformat())['eligible']


def test_published_time_is_not_used_as_quote_time(db):
    with sqlite3.connect(db) as conn:conn.execute("UPDATE picks SET raw_json='{}'")
    assert store.read_center(db,'a',now=NOW)['candidates']==[]


def test_newest_matching_book_quote_is_authoritative(db):
    with sqlite3.connect(db) as conn:
        conn.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)',('q1','m1','h2h','Casa QA','The Odds API','Local 1','Visitante 1','1.80','3.20','4.50',NOW.isoformat()))
        conn.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)',('q2','m1','h2h','Other','The Odds API','Local 1','Visitante 1','9','9','9',(NOW+timedelta(seconds=1)).isoformat()))
    rows=store.read_center(db,'a',now=NOW)['candidates']
    assert next(p for p in rows if p['id']=='p1')['odds']=='1.80'


def test_same_match_and_crossprovider_aliases_cannot_duplicate():
    a,b=leg(1),leg(2);b.update(event_key=a['event_key'],match_id='different-local-id')
    with pytest.raises(eng.CombiError,match='mismo partido'):eng.preview([a,b],'0.10',user={'membership':'ELITE'},now=NOW)


def test_mixed_books_rejected():
    with pytest.raises(eng.CombiError,match='misma casa'):eng.preview([leg(1),leg(2,bookmaker='Other')],'0.10',user={'membership':'ELITE'},now=NOW)


@pytest.mark.parametrize('plan,count,allowed',[('FREE',2,False),('PRO',3,True),('PRO',4,False),('ELITE',15,True),('ELITE',16,False)])
def test_plan_and_leg_limits(plan,count,allowed):
    legs=[leg(i) for i in range(1,count+1)]
    if allowed:assert len(eng.preview(legs,'0.10',user={'membership':plan},now=NOW)['legs'])==count
    else:
        with pytest.raises(eng.CombiError):eng.preview(legs,'0.10',user={'membership':plan},now=NOW)


def test_auto_no_filler_and_no_correlated_duplicates():
    assert len(eng.suggest([leg(i) for i in range(1,16)],15,user={'membership':'ELITE'}))==15
    with pytest.raises(eng.CombiError,match='relleno'):eng.suggest([leg(1),leg(1)],2,user={'membership':'ELITE'})
    with pytest.raises(eng.CombiError):eng.suggest([leg(1),leg(2)],2,user={'membership':'PRO'})


def test_anonymous_cannot_build_or_save(db):
    with pytest.raises(eng.CombiError):store.make_preview(db,'',preview_values(),now=NOW)


def test_get_never_creates_table_and_private_saved_is_persistent(db):
    before=open(db,'rb').read();store.read_center(db,'a',now=NOW);assert open(db,'rb').read()==before
    data=ready_save(db);result=store.save_draft(db,'a',data,now=NOW)
    assert result['not_a_bet']
    a=store.read_center(db,'a',now=NOW);b=store.read_center(db,'b',now=NOW)
    assert len(a['saved'])==1 and b['saved']==[]
    with sqlite3.connect(db) as conn:assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='combis'").fetchone()[0]==0


def test_post_revalidates_quote_expiry_change_and_finalization(db):
    data=ready_save(db)
    with pytest.raises(eng.CombiError):store.save_draft(db,'a',data,now=NOW+timedelta(minutes=16))
    with sqlite3.connect(db) as conn:conn.execute("UPDATE picks SET odds='2' WHERE id='p1'")
    with pytest.raises(eng.CombiError,match='cambiado'):store.save_draft(db,'a',data,now=NOW)
    data=ready_save(db)
    with sqlite3.connect(db) as conn:conn.execute("UPDATE matches SET status='FT' WHERE id='m1'")
    with pytest.raises(eng.CombiError):store.save_draft(db,'a',data,now=NOW)


def test_concurrent_retries_create_one_draft(db):
    data=ready_save(db)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:store.save_draft(db,'a',data,now=NOW),range(6)))
    assert len({r['id'] for r in results})==1 and sum(not r['replayed'] for r in results)==1


def test_idempotency_key_cannot_change_revision(db):
    data=ready_save(db);store.save_draft(db,'a',data,now=NOW)
    with pytest.raises(eng.CombiError):store.save_draft(db,'a',{**data,'revision':'a'*64},now=NOW)


def test_downgrade_revokes_new_creation_and_redacts_old_premium_picks(db):
    data=ready_save(db);store.save_draft(db,'a',data,now=NOW)
    with sqlite3.connect(db) as conn:conn.execute("UPDATE users SET membership='FREE',role='FREE' WHERE id='a'")
    result=store.read_center(db,'a',now=NOW)
    assert result['candidates']==result['blocked']==[]
    assert result['saved'][0]['payload']=={} and result['saved'][0]['locked']
    with pytest.raises(eng.CombiError):store.make_preview(db,'a',preview_values(),now=NOW)


def test_expired_plan_or_deleted_account_not_authorized(db):
    with sqlite3.connect(db) as conn:conn.execute("UPDATE users SET membership_expires_at='2000-01-01T00:00:00+00:00' WHERE id='a'")
    assert not store.read_center(db,'a',now=NOW)['capabilities']['can_build']
    with sqlite3.connect(db) as conn:conn.execute("DELETE FROM users WHERE id='a'")
    with pytest.raises(eng.CombiError):store.read_center(db,'a',now=NOW)


def test_unsupported_and_inaccessible_ids_not_disclosed(db):
    with pytest.raises(eng.CombiError):store.make_preview(db,'b',{'pick_ids':['does-not-exist','p1']},now=NOW)
    with sqlite3.connect(db) as conn:conn.execute("UPDATE picks SET membership_required='ELITE' WHERE id='p1'")
    with pytest.raises(eng.CombiError):store.read_advice(db,'b',pick_id='p1',now=NOW)


def test_shark_discusses_match_without_a_pick_and_without_predicting(db):
    result=store.read_advice(db,'',match_id='m1',now=NOW)
    assert result['pick'] is None and result['probability'] is None and result['external_calls']==0
    assert result['mode']=='EVIDENCE_RULES_NO_GENERATIVE_MODEL'


def test_inputs_not_mutated():
    p,m,q=pick(),fixture(),dict(odds='1.7',bookmaker='Q',source='Q',observed_at=NOW.isoformat())
    originals=deepcopy((p,m,q));eng.assess_pick(p,m,q,{'membership':'ELITE'},now=NOW)
    assert (p,m,q)==originals


def test_recent_form_counts_zero_goals_and_not_future_or_current(db):
    with sqlite3.connect(db) as conn:
        conn.execute('ALTER TABLE matches ADD COLUMN home_score TEXT')
        conn.execute('ALTER TABLE matches ADD COLUMN away_score TEXT')
        for i in range(2,9):
            conn.execute("UPDATE matches SET home_team='Local 1',away_team=?,status='FT',home_score='0',away_score='0',kickoff_iso=? WHERE id=?",
                ('Rival '+str(i),(NOW-timedelta(days=i)).isoformat(),'m'+str(i)))
        conn.execute("UPDATE matches SET home_team='Local 1',status='LIVE',home_score='0',away_score='1' WHERE id='m9'")
    result=store.read_advice(db,'a',match_id='m1',now=NOW)
    form=result['team_form']['home']
    assert form['sample_size']==5 and form['draws']==5 and form['goals_for']==0
    assert not form['season_complete']
    assert all('/match/m1' != row['href'] and '/match/m9' != row['href'] for row in form['items'])


@pytest.mark.parametrize('flag',['is_demo','is_fake','simulated'])
def test_demonstration_rows_cannot_be_used(flag):
    p=pick(**{flag:True})
    assert not eng.assess_pick(p,fixture(),dict(odds='2',bookmaker='Casa',source='The Odds API',observed_at=NOW.isoformat()),{'membership':'ELITE'},now=NOW)['eligible']


def test_invalid_zero_stake_is_not_replaced_by_default(db):
    with pytest.raises(eng.CombiError):store.make_preview(db,'a',{**preview_values(),'stake':0},now=NOW)


def test_changed_payload_cannot_replay_old_save(db):
    data=ready_save(db);store.save_draft(db,'a',data,now=NOW)
    with pytest.raises(eng.CombiError):store.save_draft(db,'a',{**data,'pick_ids':['p1','p3']},now=NOW)


def test_latest_snapshot_conflict_is_not_arbitrarily_priced(db):
    with sqlite3.connect(db) as conn:
        for ident,price in [('one','1.80'),('two','2.00')]:
            conn.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (ident,'m1','h2h','Casa QA','The Odds API','Local 1','Visitante 1',price,'3','4',NOW.isoformat()))
    result=store.read_center(db,'a',now=NOW)
    assert 'p1' not in {p['id'] for p in result['candidates']}
    assert 'p1' in {p['id'] for p in result['blocked']}


def test_snapshot_does_not_override_closed_market(db):
    with sqlite3.connect(db) as conn:
        conn.execute('UPDATE picks SET raw_json=? WHERE id=?',(json.dumps({'market_closed':True}), 'p1'))
        conn.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            ('quote','m1','h2h','Casa QA','The Odds API','Local 1','Visitante 1','1.80','3','4',NOW.isoformat()))
    assert 'p1' not in {p['id'] for p in store.read_center(db,'a',now=NOW)['candidates']}


def test_same_amount_representation_keeps_idempotency(db):
    body=ready_save(db)
    first=store.save_draft(db,'a',body,now=NOW)
    second=store.save_draft(db,'a',{**body,'stake':'0.1'},now=NOW)
    assert second['id']==first['id'] and second['replayed']


def test_combi_limit_is_shared_with_membership_policy():
    from engines.membership_engine import get_membership_limits
    for plan,count in [('FREE',0),('PRO',3),('ELITE',15),('ADMIN',15)]:
        assert eng.capabilities({'membership':plan})['max_legs']==get_membership_limits(plan)['combi_matches']==count


def test_new_receipt_cannot_refresh_an_old_provider_quote(db):
    with sqlite3.connect(db) as conn:
        conn.execute('ALTER TABLE odds_snapshots ADD COLUMN payload_json TEXT')
        original={'bookmakers':[{'title':'Casa QA','key':'qa','last_update':(NOW-timedelta(hours=2)).isoformat(),
                                'markets':[{'key':'h2h'}]}]}
        conn.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            ('q','m1','h2h','Casa QA','The Odds API','Local 1','Visitante 1','1.8','3','4',NOW.isoformat(),json.dumps(original)))
    assert 'p1' not in {p['id'] for p in store.read_center(db,'a',now=NOW)['candidates']}


@pytest.mark.parametrize('raw',["broken-json",json.dumps({'bookmakers':[]}),json.dumps({'bookmakers':[{'title':'Another','last_update':NOW.isoformat()}]})])
def test_ambiguous_or_broken_provider_clock_is_not_guessed(db,raw):
    with sqlite3.connect(db) as conn:
        conn.execute('ALTER TABLE odds_snapshots ADD COLUMN payload_json TEXT')
        conn.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            ('q','m1','h2h','Casa QA','The Odds API','Local 1','Visitante 1','1.8','3','4',NOW.isoformat(),raw))
    assert 'p1' not in {p['id'] for p in store.read_center(db,'a',now=NOW)['candidates']}


def test_zero_requested_count_is_not_changed_to_three(db):
    with pytest.raises(eng.CombiError,match='número'):
        store.make_preview(db,'a',{'mode':'suggest','count':0},now=NOW)
