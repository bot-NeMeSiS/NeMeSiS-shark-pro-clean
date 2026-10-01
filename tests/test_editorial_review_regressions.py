"""Reproductions of the independent editorial delta review. Synthetic data only."""
import socket
from datetime import datetime, timezone
import pytest
from engines import editorial_worker as w
from engines import editorial_feed_reader as reader
from engines import match_news_store as news
from test_editorial_worker import db, offline, DATA, NOW, MATCH, feed, enable, run


@pytest.mark.parametrize('categories', [('Copa de Prueba',), ('Liga de Prueba','Copa de Prueba')])
def test_conflicting_article_categories_never_publish(db,categories):
    enable(db)
    xml=feed().replace(b'</item>',(''.join('<category>'+c+'</category>' for c in categories)+'</item>').encode())
    result=run(db,fetcher=lambda *a,**k:xml)
    assert result['published']==0
    assert not news.snapshot(db,MATCH['id'])['items']


def test_atom_category_term_is_checked_before_matching():
    xml=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Equipo Uno y Equipo Dos</title><link href="/partido"/><published>2026-10-01T11:00:00Z</published><category term="Copa de Prueba"/></entry></feed>'
    items,_=reader.parse_feed(xml,feed_url=DATA['feed_url'],article_host='news.example',now=NOW)
    assert reader.match_article(items[0],[MATCH],DATA,NOW)[0] is None


def test_oldest_feed_article_can_match_a_fixture_two_days_earlier(db):
    enable(db)
    clock=datetime(2026,10,10,12,tzinfo=timezone.utc).timestamp()
    with news.connection(db,True) as c:
        c.execute("UPDATE matches SET match_date='2026-10-02',kickoff_time='15:00'")
    xml=feed(date='Sat, 03 Oct 2026 12:00:00 GMT')
    result=run(db,at=clock,fetcher=lambda *a,**k:xml)
    assert result['published']==1,result


@pytest.mark.parametrize('slow_phase',['connect','tls','request','headers'])
def test_network_deadline_stops_before_the_next_phase(monkeypatch,slow_phase):
    clock=[0.];calls=[]
    def phase(name):
        calls.append(name)
        clock[0]+=9 if name==slow_phase else .1
    class Sock:
        def settimeout(self,n): calls.append(('timeout',n))
        def connect(self,addr): phase('connect')
        def close(self): pass
    class TLS:
        def wrap_socket(self,sock,server_hostname): phase('tls');return sock
    class Response:
        status=200
        def getheader(self,key,default=None):return default
        def read1(self,n):phase('body');return b''
    class HTTP:
        def __init__(self,*a,**kw):pass
        def request(self,*a,**kw):phase('request')
        def getresponse(self):phase('headers');return Response()
        def close(self):pass
    monkeypatch.setattr(reader.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443))])
    monkeypatch.setattr(reader.socket,'socket',lambda *a:Sock())
    monkeypatch.setattr(reader.ssl,'create_default_context',lambda:TLS())
    monkeypatch.setattr(reader.http.client,'HTTPConnection',HTTP)
    with pytest.raises(reader.FeedError,match='TIME_BUDGET'):
        reader.https_feed(DATA['feed_url'],deadline=8,monotonic=lambda:clock[0])
    assert calls[-1]==slow_phase, calls
