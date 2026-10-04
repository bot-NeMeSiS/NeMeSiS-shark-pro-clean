"""Reuse season identity and positive video evidence; never infer negatives.

Official endpoint: https://thesportsdb.readme.io/reference/geteventsbyseason
The provider's Premium response limit is 3000. Missing rows are not coverage.
"""
from contextlib import closing
from datetime import datetime
import json
import re
from zoneinfo import ZoneInfo

from engines.highlight_coverage import event_id, persisted_event, persisted_event_id
from engines.postmatch_sources import integer_id, match_event
from engines.postmatch_store import identity
from engines.sportsdb_request_budget import SportsDBStopped


def partition(coverage, match):
    sid = event_id(match)
    with closing(coverage.connect()) as conn:
        sid = sid or persisted_event_id(conn,match)
        events = [persisted_event(conn,match,sid)] if sid else []
        cached = conn.execute('SELECT payload_json,expires_at FROM sportsdb_highlight_feed_cache WHERE cache_key=?',
                              ('coverage:identity:'+identity(match),)).fetchone()
    if cached:
        try:
            if datetime.fromisoformat(cached['expires_at']).timestamp()>coverage.now:
                events.append(json.loads(cached['payload_json']))
        except (ValueError,TypeError):
            pass
    for event in events:
        if not isinstance(event,dict) or not integer_id(event.get('idEvent')) or not match_event(match,event):
            continue
        if sid and str(event.get('idEvent'))!=sid:
            continue
        league=integer_id(event.get('idLeague'))
        season=str(event.get('strSeason') or '')
        if league and re.fullmatch(r'\d{4}(?:[-/]\d{4})?',season):
            return league,season
    # Other events in an already acquired season can reuse its exact identity.
    # The partition is discovered from that provider row, never from a guessed
    # season based on the match date or an API-Football numeric league ID.
    league=integer_id(match.get('league_id')) if 'sportsdb' in str(match.get('source') or '').lower() else ''
    if sid and league:
        with closing(coverage.connect()) as conn:
            seasons=conn.execute('SELECT cache_key,payload_json,expires_at FROM sportsdb_highlight_feed_cache '
                'WHERE cache_key LIKE ? ORDER BY fetched_at DESC LIMIT 8',('coverage:season:'+league+':%',)).fetchall()
        for cached in seasons:
            try:
                payload=json.loads(cached['payload_json'])
                if datetime.fromisoformat(cached['expires_at']).timestamp()<=coverage.now:
                    continue
                items=payload.get('events') if isinstance(payload,dict) else None
                if not isinstance(items,list) or len(items)>3000:
                    continue
                for event in items:
                    if isinstance(event,dict) and str(event.get('idEvent'))==sid and match_event(match,event):
                        season=str(event.get('strSeason') or cached['cache_key'].split(':',3)[-1])
                        if str(event.get('idLeague'))==league and re.fullmatch(r'\d{4}(?:[-/]\d{4})?',season):
                            return league,season
            except (ValueError,TypeError):
                continue
    return None


def acquire(coverage, match, scope, fetch, *, allow_fetch, force=False):
    """None means no reusable partition; an empty feed proves no negatives."""
    part=partition(coverage,match)
    if not part:
        return None
    league,season=part
    key='coverage:season:'+league+':'+season
    with closing(coverage.connect()) as conn:
        cached=conn.execute('SELECT payload_json,expires_at FROM sportsdb_highlight_feed_cache WHERE cache_key=?',
                            (key,)).fetchone()
    payload=None
    if cached and not force:
        try:
            if datetime.fromisoformat(cached['expires_at']).timestamp()>coverage.now:
                payload=json.loads(cached['payload_json'])
        except (ValueError,TypeError):
            pass
    purchased=payload is None
    if purchased:
        if not allow_fetch:
            return None
        params={'id':league,'s':season}
        payload=scope.call(1,'eventsseason.php',params,lambda:fetch('eventsseason.php',params))
    if not isinstance(payload,dict) or 'events' not in payload:
        raise SportsDBStopped('MALFORMED')
    items=[] if payload['events'] is None else payload['events']
    if not isinstance(items,list) or len(items)>3000 or any(not isinstance(item,dict) for item in items):
        raise SportsDBStopped('MALFORMED')
    if any(str(item.get('idLeague'))!=league or not integer_id(item.get('idEvent')) or
           (item.get('strSeason') and str(item['strSeason'])!=season) for item in items):
        raise SportsDBStopped('IDENTITY_MISMATCH')
    if purchased:
        current_year=datetime.fromtimestamp(coverage.now,ZoneInfo('Europe/Madrid')).year
        days=3 if str(current_year) in season else 30
        with closing(coverage.connect(True)) as conn,conn:
            conn.execute('INSERT OR REPLACE INTO sportsdb_highlight_feed_cache VALUES(?,?,?,?)',
                (key,json.dumps(payload),datetime.fromtimestamp(coverage.now,ZoneInfo('Europe/Madrid')).isoformat(),
                 datetime.fromtimestamp(coverage.now+days*86400,ZoneInfo('Europe/Madrid')).isoformat()))
    return items


def new_exact_videos(coverage, items):
    """Skip proven stored videos so large positive feeds advance across ticks."""
    from engines.sportsdb_highlights_engine import _find_match, _video_url
    from engines.highlight_url_engine import public_https_url
    result=[]
    with closing(coverage.connect()) as conn:
        stored={(str(row['sportsdb_event_id']),row['video_url'],row['match_id']) for row in conn.execute(
            'SELECT sportsdb_event_id,video_url,match_id FROM sportsdb_match_highlights')}
        for item in items:
            url=public_https_url(_video_url(item))
            if not url:
                continue
            mid=_find_match(conn,item)
            row=conn.execute('SELECT * FROM matches WHERE id=?',(mid,)).fetchone() if mid else None
            if row and match_event(dict(row),item) and (str(item['idEvent']),url,mid) not in stored:
                result.append(item)
    return result
