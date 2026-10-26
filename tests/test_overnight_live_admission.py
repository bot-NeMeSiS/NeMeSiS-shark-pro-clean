"""A current own LIVE observation must survive the Madrid day boundary."""
from datetime import datetime,timedelta,timezone
import json
import re
import sqlite3

import pytest


def row(key,day,status='LIVE',clock=None):
    return {'id':key,'match_date':day,'kickoff_iso':day+'T23:30:00+01:00',
            'updated_at':datetime.now(timezone.utc).isoformat(),
            'last_synced_at':clock,'status':status}


def database(tmp_path,records,extra=(),canonical_clock=True):
    path=tmp_path/'overnight.sqlite'
    columns=['id','match_date','kickoff_iso','updated_at','status']
    if canonical_clock:columns.append('last_synced_at')
    columns+=list(extra)
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE matches ('+','.join(k+' TEXT'+(' PRIMARY KEY' if k=='id' else '') for k in columns)+')')
        c.executemany('INSERT INTO matches VALUES('+','.join('?' for _ in columns)+')',
                      [tuple(r.get(k) for k in columns) for r in records])
    return path


@pytest.mark.parametrize('offset',[-1,-2,-30])
def test_recent_past_day_candidate_survives_dense_current_and_future_dates(app_module,tmp_path,monkeypatch,offset):
    today=app_module.today_iso();fresh=datetime.now(timezone.utc).isoformat()
    current=[row('today-'+str(i),today,'NS',fresh) for i in range(1004)]
    records=current+[row('overnight',app_module.today_iso(offset),'HT',fresh),
                     row('fresh-today',today,'1H',fresh),
                     row('tomorrow',app_module.today_iso(1),'LIVE',fresh)]
    path=database(tmp_path,records);before=path.read_bytes()
    monkeypatch.setattr(app_module,'DB_PATH',str(path))
    selected,meta=app_module._v931_read_table_rows('matches',800)
    assert meta['status']=='ok' and len(selected)==800
    assert {r['id'] for r in selected[:2]}=={'overnight','fresh-today'}
    assert 'tomorrow' not in {r['id'] for r in selected}
    expected={r['id']:r for r in records}
    assert all(r==expected[r['id']] for r in selected)
    assert before==path.read_bytes()


@pytest.mark.parametrize('offset,status,age',[
    (-2,'LIVE',10800),(1,'LIVE',0),(-1,'LIVE',10800),(-1,'LIVE',None),
    (-1,'LIVE',-900),(-1,'FT',0),(-1,'PEN',0),(-1,'NS',0),
])
def test_non_current_hints_cannot_displace_today(app_module,tmp_path,monkeypatch,offset,status,age):
    clock=None if age is None else (datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()
    records=[row('today',app_module.today_iso(),'NS',clock),
             row('hint',app_module.today_iso(offset),status,clock)]
    path=database(tmp_path,records);monkeypatch.setattr(app_module,'DB_PATH',str(path))
    selected,meta=app_module._v931_read_table_rows('matches',1)
    assert meta['status']=='ok' and [r['id'] for r in selected]==['today']


@pytest.mark.parametrize('top,middle,expected',[
    ('old','fresh','today'),(None,'old','today'),
    ('null',None,'overnight'),('undefined','None','overnight'),
    ('',None,'overnight'),('fresh','old','overnight'),
])
def test_candidate_clock_uses_canonical_precedence(app_module,tmp_path,monkeypatch,top,middle,expected):
    now=datetime.now(timezone.utc)
    clocks={'old':(now-timedelta(hours=3)).isoformat(),'fresh':now.isoformat()}
    previous=row('overnight',app_module.today_iso(-1),'LIVE',clocks['fresh'])
    previous.update(live_updated_at=clocks.get(top,top),provider_updated_at=clocks.get(middle,middle))
    path=database(tmp_path,[row('today',app_module.today_iso(),'NS'),previous],
                  extra=('live_updated_at','provider_updated_at'))
    monkeypatch.setattr(app_module,'DB_PATH',str(path))
    selected,meta=app_module._v931_read_table_rows('matches',1)
    assert meta['status']=='ok' and selected[0]['id']==expected


def test_generic_updated_at_is_not_a_live_provider_clock(app_module,tmp_path,monkeypatch):
    path=database(tmp_path,[row('today',app_module.today_iso(),'NS'),
        row('overnight',app_module.today_iso(-1),'LIVE')],canonical_clock=False)
    monkeypatch.setattr(app_module,'DB_PATH',str(path))
    selected,meta=app_module._v931_read_table_rows('matches',1)
    assert meta['status']=='ok' and selected[0]['id']=='today'


@pytest.mark.parametrize('table',['matches','picks','favorites'])
def test_other_readers_and_legacy_dateless_matches_keep_recent_order(app_module,tmp_path,monkeypatch,table):
    path=tmp_path/'recent-only.sqlite'
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE '+table+' (id TEXT PRIMARY KEY, updated_at TEXT)')
        c.executemany('INSERT INTO '+table+' VALUES(?,?)',[('old','2026-01-01'),('new','2026-02-01')])
    monkeypatch.setattr(app_module,'DB_PATH',str(path))
    selected,meta=app_module._v931_read_table_rows(table,2)
    assert meta['status']=='ok' and meta['selection_policy']=='recent_update'
    assert [r['id'] for r in selected]==['new','old']


@pytest.mark.parametrize('native_conflict',[False,True])
@pytest.mark.parametrize('extra_days',[0,29])
def test_actual_http_retains_previous_day_live_without_changing_source_day_or_truth(
    app_module,tmp_path,monkeypatch,native_conflict,extra_days
):
    path=tmp_path/'actual-overnight.sqlite'
    monkeypatch.setattr(app_module,'DB_PATH',str(path));app_module.seed_core()
    now=datetime.now(app_module.TZ)
    kickoff=now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(minutes=30,days=extra_days)
    future=now+timedelta(days=1)
    common={'source':'api_football_live','sport_key':'soccer','competition_key':'laliga',
        'competition_id':'140','competition_name':'LaLiga','league_name':'LaLiga','country':'Spain',
        'season':str(now.year),'home_team':'Synthetic Night Home','away_team':'Synthetic Night Away',
        'home_team_id':'99401','away_team_id':'99402','minute':50,'home_score':2,'away_score':1,
        'updated_at':now.isoformat(),'last_synced_at':now.isoformat()}
    own=dict(common,id='af-994001',external_id='994001',status='2H',match_date=kickoff.date().isoformat(),
             kickoff_iso=kickoff.isoformat(),kickoff_time=kickoff.strftime('%H:%M'),match_time=kickoff.strftime('%H:%M'))
    own['raw_json']=json.dumps({'fixture':{'id':994001,'date':kickoff.isoformat(),
        'status':{'short':'FT' if native_conflict else '2H','elapsed':50}},
        'league':{'id':140,'name':'LaLiga','country':'Spain','season':now.year},
        'teams':{'home':{'id':99401,'name':own['home_team']},'away':{'id':99402,'name':own['away_team']}},
        'goals':{'home':2,'away':1}})
    stale=dict(own,id='af-994002',external_id='994002',raw_json='',
               last_synced_at=(now-timedelta(hours=3)).isoformat())
    upcoming=[dict(common,id='future-'+str(i),status='NS',minute=None,home_score=None,away_score=None,
        home_team='Synthetic Future Home '+str(i),away_team='Synthetic Future Away '+str(i),
        match_date=future.date().isoformat(),kickoff_iso=future.isoformat(),
        kickoff_time=future.strftime('%H:%M'),match_time=future.strftime('%H:%M')) for i in range(1004)]
    with sqlite3.connect(path) as c:
        c.execute('DELETE FROM matches');c.execute('DELETE FROM picks')
        c.execute("DELETE FROM competitions WHERE key='laliga'")
        c.execute('INSERT INTO competitions(key,name,country,source,external_id) VALUES(?,?,?,?,?)',
                  ('laliga','LaLiga','Spain','API_FOOTBALL','140'))
        columns={r[1] for r in c.execute('PRAGMA table_info(matches)')}
        for r in upcoming+[own,stale]:
            values={k:v for k,v in r.items() if k in columns}
            c.execute('INSERT INTO matches('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))
        before=c.execute('SELECT * FROM matches ORDER BY id').fetchall()
    client=app_module.app.test_client()
    response=client.get('/api/realtime/sports',query_string={'scope':'matches','consumer':'directo-v2','f':'live'})
    assert response.status_code==200
    body=response.get_json();frames={r['id']:r for r in body['matches']}
    expected_live=0 if native_conflict else 1
    assert body['counts']['live']==expected_live
    assert len(set(frames)&{r['id'] for r in upcoming})==799
    assert stale['id'] not in frames
    if not native_conflict:
        assert frames[own['id']]['match_date']==kickoff.date().isoformat()
        state=frames[own['id']]['realtime_state']
        assert state['is_live'] is True and state['score_home']==2 and state['score_away']==1
        assert state['provider_observed_at']==own['last_synced_at']
        assert body['counts']['today']==0
    view=body['fixture_identity']['view']
    assert [r['id'] for r in view['members']]==([] if native_conflict else [own['id']])
    page=client.get('/live');assert page.status_code==200
    html=page.get_data(as_text=True)
    assert len(re.findall(r'class="[^"]*\bv933-live-card\b',html))==expected_live
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT * FROM matches ORDER BY id').fetchall()==before
        assert c.execute('SELECT COUNT(*) FROM picks').fetchone()[0]==0
