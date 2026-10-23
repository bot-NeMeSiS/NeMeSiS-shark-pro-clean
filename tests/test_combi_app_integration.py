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


def test_legacy_combi_apis_enforce_paid_membership_and_selected_pick_tiers(app_module, monkeypatch):
    token_prefix = secrets.token_hex(8)
    free_user_id = 'combi-free-qa-' + token_prefix
    pro_user_id = 'combi-pro-qa-' + token_prefix
    pick_ids = [token_prefix + '-pro-1', token_prefix + '-pro-2', token_prefix + '-elite']
    client = app_module.app.test_client()
    client.get('/combis')
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    kickoff = now_dt + timedelta(days=1)
    with sqlite3.connect(app_module.DB_PATH) as conn:
        for user_id, plan in ((free_user_id, 'FREE'), (pro_user_id, 'PRO')):
            conn.execute(
                'INSERT INTO users(id,email,password_hash,role,membership,created_at) VALUES (?,?,?,?,?,?)',
                (user_id, user_id + '@example.invalid', 'invalid_test_hash', plan, plan, now),
            )
        for pick_id, required in zip(pick_ids, ('PRO', 'PRO', 'ELITE')):
            conn.execute(
                '''INSERT INTO matches(id,sport_key,match_date,kickoff_iso,home_team,away_team,status,competition_name,source)
                   VALUES (?,?,?,?,?,?,?,?,?)''',
                (pick_id, 'soccer', kickoff.date().isoformat(), kickoff.isoformat(),
                 'Local QA ' + pick_id[-5:], 'Visitante QA ' + pick_id[-5:], 'NS', 'Liga QA', 'TheSportsDB API'),
            )
            conn.execute(
                '''INSERT INTO picks(id,match_id,home_team,away_team,market,selection,odds,bookmaker,
                   status,membership_required,source,raw_json,updated_at,published_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (pick_id, pick_id, 'Local QA ' + pick_id[-5:], 'Visitante QA ' + pick_id[-5:],
                 '1x2', '1', 1.8, 'Casa QA', 'published', required, 'The Odds API',
                 json.dumps({'odds_updated_at': now}), now, now),
            )
        conn.execute(
            '''INSERT INTO combis(id,name,picks_json,total_odds,risk_level,status,source,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            (token_prefix, 'Combi QA privada', json.dumps([{'selection': '1', 'odds': 1.8}]),
             1.8, 'MEDIO', 'DRAFT', 'QA', now, now),
        )

    try:
        with client.session_transaction() as sess:
            sess.update(user_id=free_user_id, user_role='FREE', user_membership='FREE', membership='FREE')
            free_token = generate_csrf_token(sess)
        free_list = client.get('/api/combis')
        assert free_list.status_code == 200
        free_payload = free_list.get_json()
        assert free_payload['capabilities']['can_build'] is False
        assert free_payload['candidates'] == []
        assert free_payload['combis'] == []
        def unexpected_candidate_read(*args, **kwargs):
            raise AssertionError('A denied combinada request must not resolve submitted picks.')
        with monkeypatch.context() as guard:
            guard.setattr(store, 'candidates', unexpected_candidate_read)
            free_build = client.post('/api/combis/build', json={
                'pick_ids': pick_ids[:2], 'stake': '0.10', 'csrf_token': free_token,
            })
        assert free_build.status_code == 403
        assert free_build.get_json()['error'] == 'PLAN_REQUIRED'
        assert 'Combi QA privada' not in free_list.get_data(as_text=True)

        with client.session_transaction() as sess:
            sess.update(user_id=pro_user_id, user_role='PRO', user_membership='PRO', membership='PRO')
            pro_token = generate_csrf_token(sess)
        pro_list = client.get('/api/combis')
        assert pro_list.status_code == 200
        pro_payload = pro_list.get_json()
        assert pro_payload['capabilities']['can_build'] is True
        pro_candidate_ids = {item['id'] for item in pro_payload['candidates']}
        assert set(pick_ids[:2]).issubset(pro_candidate_ids)
        assert pick_ids[2] not in pro_candidate_ids
        assert pro_payload['combis'] == []
        assert 'Combi QA privada' not in pro_list.get_data(as_text=True)

        locked_pick_build = client.post('/api/combis/build', json={
            'pick_ids': pick_ids, 'stake': '0.10', 'csrf_token': pro_token,
        })
        assert locked_pick_build.status_code == 409
        assert locked_pick_build.get_json()['ok'] is False

        with monkeypatch.context() as guard:
            guard.setattr(store, 'candidates', unexpected_candidate_read)
            elite_suggestion = client.post('/api/combis/build', json={
                'mode': 'suggest', 'count': 2, 'stake': '0.10', 'csrf_token': pro_token,
            })
        assert elite_suggestion.status_code == 403
        assert elite_suggestion.get_json()['error'] == 'PLAN_REQUIRED'

        allowed_pick_build = client.post('/api/combis/build', json={
            'pick_ids': pick_ids[:2], 'stake': '0.10', 'csrf_token': pro_token,
        })
        assert allowed_pick_build.status_code == 200
        assert allowed_pick_build.get_json()['ok'] is True
        assert all(leg['membership_required'] == 'PRO' for leg in allowed_pick_build.get_json()['combi']['legs'])
    finally:
        with sqlite3.connect(app_module.DB_PATH) as conn:
            conn.execute('DELETE FROM combis WHERE id=?', (token_prefix,))
            conn.executemany('DELETE FROM picks WHERE id=?', [(pick_id,) for pick_id in pick_ids])
            conn.executemany('DELETE FROM matches WHERE id=?', [(pick_id,) for pick_id in pick_ids])
            conn.executemany('DELETE FROM users WHERE id=?', [(free_user_id,), (pro_user_id,)])

