"""Real Flask wiring, temporary pytest database, no provider calls or real accounts."""
from datetime import datetime, timedelta, timezone
import json
import secrets
import sqlite3

from engines.security_engine import generate_csrf_token
from engines import client_combi_store as store


def test_real_app_keeps_routes_and_shark_target_in_sync(app_module, monkeypatch):
    token_prefix=secrets.token_hex(8)
    user_id='combi-qa-'+token_prefix
    ids=[token_prefix+'-1',token_prefix+'-2']
    client=app_module.app.test_client()
    client.get('/combis')  # existing app bootstrap on the isolated pytest DB
    now=datetime.now(timezone.utc)
    with sqlite3.connect(app_module.DB_PATH) as conn:
        conn.execute('INSERT INTO users(id,email,password_hash,role,membership,created_at) VALUES (?,?,?,?,?,?)',
                     (user_id,user_id+'@example.invalid','invalid_test_hash','ELITE','ELITE',now.isoformat()))
        for index,pid in enumerate(ids):
            conn.execute('INSERT INTO matches(id,sport_key,match_date,kickoff_iso,home_team,away_team,status,competition_name,source) VALUES (?,?,?,?,?,?,?,?,?)',
                (pid,'soccer',now.date().isoformat(),(now+timedelta(hours=index+2)).isoformat(),pid+' local',pid+' away','NS','Liga QA','TheSportsDB API'))
            conn.execute('INSERT INTO picks(id,match_id,home_team,away_team,market,selection,odds,bookmaker,status,membership_required,source,raw_json,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (pid,pid,pid+' local',pid+' away','1x2','1',1.5,'Casa QA','published','PRO','The Odds API',json.dumps({'odds_updated_at':now.isoformat()}),now.isoformat()))
    try:
        with client.session_transaction() as sess:
            sess['user_id']=user_id;sess['user_role']='ELITE';sess['membership']='ELITE'
            token=generate_csrf_token(sess)
        assert app_module.app.extensions['nemesis_combi_routes']['legacy_build_is_preview_only']
        legacy=client.get('/combis');modern=client.get('/combinadas')
        assert legacy.status_code==modern.status_code==200
        assert b'NEMESIS-COMBI-ADVICE-V1' in legacy.data
        assert client.post('/api/combis/build',json={'pick_ids':ids}).status_code==403
        result=client.post('/api/combis/build',json={'pick_ids':ids,'stake':'0.10','csrf_token':token})
        assert result.status_code==200 and result.json['combi']['total_odds']=='2.25'
        advice=client.get('/shark?pick='+ids[0])
        assert advice.status_code==200 and ids[0].encode() in advice.data
        assert b'data-combi-advice' in advice.data
        picks=client.get('/picks')
        assert picks.status_code==200 and b'/combinadas' in picks.data
    finally:
        with sqlite3.connect(app_module.DB_PATH) as conn:
            for pid in ids:
                conn.execute('DELETE FROM picks WHERE id=?',(pid,));conn.execute('DELETE FROM matches WHERE id=?',(pid,))
            conn.execute('DELETE FROM users WHERE id=?',(user_id,))
        # Do not leave a public summary containing test records in later tests.
        app_module.invalidate_v934_realtime_cache('v934:sports:')

