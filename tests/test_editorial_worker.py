"""Synthetic approved feeds only. Every external transport is explicitly replaced."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import socket
import sqlite3

import pytest
from engines import editorial_worker as w
from engines import editorial_feed_reader as reader
from engines import match_news_store as news
from engines.postmatch_store import identity

NOW = datetime(2026,10,1,12,tzinfo=timezone.utc).timestamp()
MATCH = {'id':'news-qa','source':'TheSportsDB','external_id':'101','home_team':'Equipo Uno',
         'away_team':'Equipo Dos','match_date':'2026-10-01','kickoff_time':'10:00','status':'FT',
         'home_score':2,'away_score':1,'score':'2-1','league_id':'4328',
         'league_name':'Liga de Prueba','competition_name':'Liga de Prueba'}
DATA = {'publisher':'Medio QA','feed_url':'https://news.example/feed.xml','article_host':'news.example',
        'competition':'Liga de Prueba','basis':'Política sintética para pruebas; no autoriza una fuente real.',
        'evidence_url':'https://news.example/terms','expires_at':'2026-11-01T00:00:00+00:00',
        'confirmed':'1','scope_confirmed':'1','auto_publish':'1','auto_confirmed':'1'}


def feed(title='Equipo Uno derrota a Equipo Dos',url='https://news.example/partido',date='Thu, 01 Oct 2026 11:00:00 GMT'):
    return f'<rss version="2.0"><channel><item><title>{title}</title><link>{url}</link><pubDate>{date}</pubDate></item></channel></rss>'.encode()


def transport(*_a,**_kw): return feed()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*_a,**_kw): raise AssertionError('Unexpected external network')
    monkeypatch.setattr(socket.socket,'connect',blocked)


@pytest.fixture
def db(tmp_path):
    path=tmp_path/'news.sqlite'
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE matches ('+','.join(k+' TEXT' for k in MATCH)+')')
        c.execute('INSERT INTO matches VALUES('+','.join('?' for _ in MATCH)+')',tuple(MATCH.values()))
    return path


def enable(db,**changes):
    sid=w.add_source(db,{**DATA,**changes},actor='admin-qa',now=NOW)
    snap=w.state(db,now=NOW)
    w.configure(db,{'enabled':'1','daily_limit':'12','revision':snap['revision'],'confirmed':'1'},actor='admin-qa',now=NOW)
    return sid


def run(db,at=NOW,fetcher=transport): return w.tick(db,clock=lambda:at,fetcher=fetcher)


def raw_news(db):
    with news.connection(db) as c: return [dict(r) for r in c.execute('SELECT * FROM match_news_references')]


def action(db,sid,kind,at=NOW):
    source=next(s for s in w.state(db,now=at)['sources'] if s['id']==sid)
    w.source_action(db,sid,{'action':kind,'revision':source['revision'],'confirmed':'1'},actor='admin-qa',now=at)


def test_unconfigured_reads_never_create_schema(db,tmp_path):
    before=db.read_bytes(); assert run(db)['result']=='PAUSED';assert db.read_bytes()==before
    absent=tmp_path/'absent.sqlite'
    assert w.state(absent)['state']=='READ_UNAVAILABLE';assert not absent.exists()


@pytest.mark.parametrize('missing',['confirmed','scope_confirmed','basis','publisher','evidence_url','article_host','competition','expires_at','auto_confirmed'])
def test_source_requires_real_explicit_policy_fields(db,missing):
    data=dict(DATA);data.pop(missing)
    before=db.read_bytes()
    with pytest.raises(news.NewsError): w.add_source(db,data,actor='admin',now=NOW)
    assert db.read_bytes()==before


def test_register_does_not_enable_editor(db):
    w.add_source(db,DATA,actor='admin',now=NOW)
    assert not w.state(db)['enabled'];assert run(db)['external_calls']==0


def test_positive_feed_to_client_and_no_article_copy(db):
    enable(db);r=run(db)
    assert r['published']==1 and r['external_calls']==1 and r['ok']
    public=news.snapshot(db,MATCH['id']);assert public['state']=='VERIFIED'
    assert len(public['items'])==1
    item=public['items'][0]
    assert 'Equipo Uno — Equipo Dos' in item['title'] and 'derrota' not in item['title']
    assert set(item)=={'id','url','title','publisher','published_at','revision'}
    assert 'Política sintética' not in json.dumps(public['items'])
    assert run(db,at=NOW+1)['result']=='IDLE'


def test_draft_mode_does_not_publish(db):
    enable(db,auto_publish='0');r=run(db)
    assert r['drafts']==1 and not news.snapshot(db,MATCH['id'])['items']
    assert raw_news(db)[0]['state']=='DRAFT'


def test_manual_review_can_publish_and_withdraw_automatic_draft(db):
    enable(db,auto_publish='0');run(db);row=raw_news(db)[0]
    news.decide(db,MATCH['id'],row['id'],{'action':'PUBLISH','confirmed':'1','revision':row['revision']},actor='human',now=NOW+1)
    assert len(news.snapshot(db,MATCH['id'])['items'])==1
    row=raw_news(db)[0]
    news.decide(db,MATCH['id'],row['id'],{'action':'RETRACT','confirmed':'1','revision':row['revision']},actor='human',now=NOW+2)
    run(db,at=NOW+7201)
    assert raw_news(db)[0]['state']=='RETRACTED'
    assert not news.snapshot(db,MATCH['id'])['items']


def test_repeated_feed_is_idempotent(db):
    enable(db);run(db);r=run(db,at=NOW+7201)
    assert r['unchanged']==1 and r['published']==0
    with news.connection(db) as c:
        assert c.execute('SELECT COUNT(*) FROM match_news_references').fetchone()[0]==1
        assert c.execute('SELECT COUNT(*) FROM match_news_audit').fetchone()[0]==1


def test_pause_during_fetch_fences_publication(db):
    enable(db)
    def paused(*a,**k):
        cfg=w.state(db,now=NOW)
        w.configure(db,{'enabled':'0','daily_limit':'12','revision':cfg['revision']},actor='admin',now=NOW)
        return feed()
    assert run(db,fetcher=paused)['result']=='STALE_EXECUTION'
    assert not raw_news(db)


def test_revoked_source_in_flight_never_publishes(db):
    sid=enable(db)
    def revoked(*a,**k):action(db,sid,'REVOKE');return feed()
    assert run(db,fetcher=revoked)['result']=='STALE_EXECUTION'
    assert not raw_news(db)


def test_revoke_hides_published_reference_immediately(db):
    sid=enable(db);run(db);action(db,sid,'REVOKE')
    assert not news.snapshot(db,MATCH['id'])['items']
    assert raw_news(db)[0]['state']=='PUBLISHED'  # History retained; visibility fails closed.
    row=raw_news(db)[0]
    with pytest.raises(news.NewsError):
        news.decide(db,MATCH['id'],row['id'],{'action':'PUBLISH','revision':row['revision'],'confirmed':'1'},actor='admin',now=NOW)


def test_expiry_hides_without_cron(db,monkeypatch):
    enable(db);run(db)
    monkeypatch.setattr(news.time,'time',lambda:datetime(2026,11,2,tzinfo=timezone.utc).timestamp())
    assert not news.snapshot(db,MATCH['id'])['items']


def test_pausing_fetch_keeps_valid_publication(db):
    sid=enable(db);run(db);action(db,sid,'PAUSE')
    assert len(news.snapshot(db,MATCH['id'])['items'])==1
    assert run(db,at=NOW+7201)['external_calls']==0


def test_identity_change_hides_old_publication(db):
    enable(db);run(db)
    with news.connection(db,True) as c:c.execute("UPDATE matches SET away_team='Otro Equipo'")
    assert not news.snapshot(db,MATCH['id'])['items']


def test_identity_is_rechecked_after_network(db):
    enable(db)
    def moved(*a,**k):
        with news.connection(db,True) as c:c.execute("UPDATE matches SET match_date='2026-10-05'")
        return feed()
    r=run(db,fetcher=moved)
    assert r['published']==0 and r['unmatched']==1


def test_changed_source_title_demotes_auto_but_not_manual(db):
    enable(db);run(db)
    r=run(db,at=NOW+7201,fetcher=lambda *a,**k:feed('Equipo Uno y Equipo Dos: corrección posterior'))
    assert r['changed']==1 and raw_news(db)[0]['state']=='DRAFT'
    row=raw_news(db)[0]
    news.decide(db,MATCH['id'],row['id'],{'action':'PUBLISH','revision':row['revision'],'confirmed':'1'},actor='human',now=NOW+7202)
    run(db,at=NOW+14402,fetcher=transport)
    assert raw_news(db)[0]['state']=='PUBLISHED' and raw_news(db)[0]['reviewed_by']=='human'


def test_failures_backoff_do_not_delete_valid_content(db):
    enable(db);run(db)
    def fail(*a,**k):raise reader.FeedError('NETWORK_OR_TLS')
    r=run(db,at=NOW+7201,fetcher=fail)
    assert not r['ok'] and r['result']=='NETWORK_OR_TLS'
    assert len(news.snapshot(db,MATCH['id'])['items'])==1
    assert w.state(db)['sources'][0]['due_at']==NOW+7201+1800


def test_empty_feed_is_not_claimed_as_complete_match_coverage(db):
    enable(db);r=run(db,fetcher=lambda *a,**k:b'<rss><channel/></rss>')
    assert r['result']=='NO_NEW_REFERENCES' and r['published']==0


def test_global_budget_survives_crash_and_new_day(db):
    sid=enable(db);cfg=w.state(db,now=NOW)
    w.configure(db,{'enabled':'1','daily_limit':'1','confirmed':'1','revision':cfg['revision']},actor='admin',now=NOW)
    old,_=w.claim(db,NOW)
    assert w.claim(db,NOW+61)[1]=='DAILY_BUDGET'
    new,_=w.claim(db,NOW+86400)
    assert new and new['token']!=old['token']
    with pytest.raises(w.LostLease):w.finish(db,old,[],now=NOW+86401)


def test_atomic_single_claim(db):
    enable(db)
    with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:w.claim(db,NOW),range(2)))
    assert sum(job is not None for job,_ in rs)==1
    assert w.state(db,now=NOW)['used']==1


def test_dry_run_no_network_no_writes(db):
    enable(db);before=db.read_bytes()
    r=w.tick(db,dry_run=True,clock=lambda:NOW,fetcher=lambda *a,**k:pytest.fail('network'))
    assert r['external_calls']==r['database_writes']==0 and db.read_bytes()==before


def test_exhausted_deadline_no_claim(db):
    enable(db);r=w.tick(db,deadline=0,monotonic=lambda:1,clock=lambda:NOW)
    assert r['result']=='TIME_BUDGET' and w.state(db,now=NOW)['used']==0


def test_ambiguous_match_stays_in_inbox(db):
    enable(db)
    with news.connection(db,True) as c:
        m={**MATCH,'id':'duplicate'};c.execute('INSERT INTO matches VALUES('+','.join('?' for _ in m)+')',tuple(m.values()))
    r=run(db);assert r['ambiguous']==1 and not raw_news(db)
    assert w.state(db)['inbox'][0]['state']=='AMBIGUOUS'


@pytest.mark.parametrize('title',['Equipo Uno B y Equipo Dos B','Equipo Uno femenino y Equipo Dos','Equipo Uno sub-19 contra Equipo Dos sub-19','Equipo Uno ficha a un jugador','Equipo Uno y Otro Equipo'])
def test_unrelated_youth_or_partial_team_mentions_never_publish(db,title):
    enable(db);r=run(db,fetcher=lambda *a,**k:feed(title))
    assert r['published']==0 and not news.snapshot(db,MATCH['id'])['items']


@pytest.mark.parametrize('changes',[{'status':'2H'}, {'status':'NS'}, {'score':'','home_score':None,'away_score':None}, {'competition_name':'Otra Liga','league_name':'Otra Liga'}])
def test_no_inferred_final_or_wrong_competition(db,changes):
    enable(db)
    with news.connection(db,True) as c:
        c.execute('UPDATE matches SET '+','.join(k+'=?' for k in changes),tuple(changes.values()))
    assert run(db)['published']==0


@pytest.mark.parametrize('url',['http://news.example/x','https://127.0.0.1/x','https://news.example@private.local/x','https://elsewhere.example/x','javascript:alert(1)'])
def test_feed_links_must_use_reviewed_exact_https_host(url):
    items,rejected=reader.parse_feed(feed(url=url),feed_url=DATA['feed_url'],article_host='news.example',now=NOW)
    assert not items and rejected==1


@pytest.mark.parametrize('bad',[b'<!DOCTYPE rss [<!ENTITY x "boom">]><rss/>',b'<rss>\0</rss>',b'bad xml',b'x'*(reader.MAX_BYTES+1)],
                         ids=['doctype', 'null-byte', 'malformed', 'oversized'])
def test_xml_safety_and_size(bad):
    with pytest.raises(reader.FeedError):reader.parse_feed(bad,feed_url=DATA['feed_url'],article_host='news.example',now=NOW)


@pytest.mark.parametrize('date',['','Thu, 01 Oct 2026 14:00:00 GMT','Thu, 24 Sep 2026 01:00:00 GMT','2026-10-01T11:00:00'])
def test_dates_must_be_known_recent_and_not_future(date):
    items,rejected=reader.parse_feed(feed(date=date),feed_url=DATA['feed_url'],article_host='news.example',now=NOW)
    assert not items


def test_atom_and_relative_link():
    raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Equipo Uno y Equipo Dos</title><link href="/match"/><published>2026-10-01T11:00:00Z</published></entry></feed>'
    items,rejected=reader.parse_feed(raw,feed_url=DATA['feed_url'],article_host='news.example',now=NOW)
    assert items[0]['url']=='https://news.example/match' and not rejected


def test_conflicting_duplicate_feed_urls_rejected():
    item=feed().decode().split('<channel>')[1].split('</channel>')[0]
    raw=('<rss><channel>'+item+item.replace('derrota','gana')+'</channel></rss>').encode()
    assert not reader.parse_feed(raw,feed_url=DATA['feed_url'],article_host='news.example',now=NOW)[0]


@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','169.254.169.254','::1','fc00::1','::ffff:127.0.0.1'])
def test_dns_private_addresses_blocked_before_connection(monkeypatch,ip):
    monkeypatch.setattr(reader.socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))])
    with pytest.raises(reader.FeedError,match='UNSAFE_DNS'):
        reader.https_feed(DATA['feed_url'],deadline=20,monotonic=lambda:1)


def test_one_unsafe_dns_result_rejects_whole_source(monkeypatch):
    monkeypatch.setattr(reader.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('10.0.0.1',443))])
    with pytest.raises(reader.FeedError,match='UNSAFE_DNS'):reader.https_feed(DATA['feed_url'],deadline=20,monotonic=lambda:1)


def test_config_revision_prevents_lost_update(db):
    enable(db);old=w.state(db)
    w.configure(db,{'enabled':'0','daily_limit':'12','revision':old['revision']},actor='admin',now=NOW)
    with pytest.raises(news.NewsError):w.configure(db,{'enabled':'1','daily_limit':'12','confirmed':'1','revision':old['revision']},actor='other',now=NOW)


def test_recheck_does_not_override_minimum_spacing(db):
    sid=enable(db);run(db)
    with pytest.raises(news.NewsError):action(db,sid,'RECHECK',at=NOW+1)
    action(db,sid,'RECHECK',at=NOW+301)
    assert run(db,at=NOW+301)['external_calls']==1


def test_expired_policy_requires_explicit_renewal_and_does_not_enable_paused_source(db):
    sid=enable(db);run(db);action(db,sid,'PAUSE')
    later=datetime(2026,11,2,tzinfo=timezone.utc).timestamp()
    src=w.state(db,now=later)['sources'][0]
    assert not src['policy_valid']
    w.source_action(db,sid,{'action':'RENEW','revision':src['revision'],'confirmed':'1','expires_at':'2026-12-01T00:00:00Z'},actor='reviewer',now=later)
    src=w.state(db,now=later)['sources'][0]
    assert src['policy_valid'] and not src['enabled']


def test_revocation_cannot_be_undone_by_recheck_or_renewal(db):
    sid=enable(db);action(db,sid,'REVOKE')
    src=w.state(db,now=NOW)['sources'][0]
    with pytest.raises(news.NewsError):
        w.source_action(db,sid,{'action':'RENEW','revision':src['revision'],'confirmed':'1','expires_at':'2026-12-01T00:00:00Z'},actor='reviewer',now=NOW)


@pytest.mark.parametrize('status,headers,expected',[(302,{},'REDIRECT_REVIEW'),(401,{},'ACCESS_DENIED'),(429,{},'RATE_LIMIT'),(200,{'Content-Encoding':'gzip'},'ENCODING_UNSUPPORTED'),(200,{'Content-Length':'9999999'},'RESPONSE_TOO_LARGE')])
def test_transport_pins_dns_preserves_tls_and_never_follows_redirect(monkeypatch,status,headers,expected):
    calls=[]
    class Sock:
        def settimeout(self,n):calls.append(('timeout',n))
        def connect(self,addr):calls.append(('connect',addr))
        def close(self):pass
    class TLS:
        def wrap_socket(self,sock,server_hostname):calls.append(('tls',server_hostname));return sock
    class Response:
        def getheader(self,key,default=None):return headers.get(key,default)
    Response.status=status
    class HTTP:
        def __init__(self,*a,**kw):pass
        def request(self,method,path,headers):calls.append(('request',method,path,headers))
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(reader.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443))])
    monkeypatch.setattr(reader.socket,'socket',lambda *a:Sock())
    monkeypatch.setattr(reader.ssl,'create_default_context',lambda:TLS())
    monkeypatch.setattr(reader.http.client,'HTTPConnection',HTTP)
    with pytest.raises(reader.FeedError,match=expected):reader.https_feed(DATA['feed_url'],deadline=20,monotonic=lambda:1)
    assert ('connect',('8.8.8.8',443)) in calls
    assert ('tls','news.example') in calls
    requests=[c for c in calls if c[0]=='request']
    assert len(requests)==1 and requests[0][3]['Host']=='news.example'
    assert not any(k in requests[0][3] for k in ('Cookie','Authorization'))


def test_second_feed_cannot_demote_another_sources_publication(db):
    enable(db);run(db)
    sid=w.add_source(db,{**DATA,'feed_url':'https://news.example/second-feed'},actor='admin',now=NOW+1)
    run(db,at=NOW+1)  # duplicate URL, owned by the first source
    action(db,sid,'RECHECK',at=NOW+302)
    result=run(db,at=NOW+302,fetcher=lambda *a,**k:feed('Equipo Uno y Equipo Dos: otro título'))
    assert result['unchanged']==1 and raw_news(db)[0]['state']=='PUBLISHED'


def test_future_agenda_does_not_exhaust_postmatch_window(db):
    enable(db)
    with news.connection(db,True) as c:
        for i in range(501):
            m={**MATCH,'id':'future-'+str(i),'match_date':'2026-10-05','status':'NS'}
            c.execute('INSERT INTO matches VALUES('+','.join('?' for _ in m)+')',tuple(m.values()))
    assert run(db)['published']==1


def test_active_sources_visible_after_many_revocations(db):
    for i in range(11):
        sid=w.add_source(db,{**DATA,'feed_url':f'https://news.example/feed-{i}'},actor='admin',now=NOW)
        action(db,sid,'REVOKE')
    sid=w.add_source(db,{**DATA,'feed_url':'https://news.example/current'},actor='admin',now=NOW)
    assert w.state(db,now=NOW)['sources'][0]['id']==sid
