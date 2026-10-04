"""Final-match event and lineup recovery; strict identities, bounded factual receipts."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from engines.postmatch_sources import SourceError, match_event, final_scope, integer_id, norm
from engines.postmatch_store import BudgetStopped
from engines.match_record_archive import _disk_free_bytes, MIN_FREE_DISK_BYTES


def capacity(conn, incoming=0):
    free = _disk_free_bytes(conn)
    if free is None:
        raise sqlite3.DatabaseError('ARCHIVE_STORAGE_UNVERIFIABLE')
    used = conn.execute('SELECT COALESCE(SUM(length(CAST(payload_json AS BLOB))),0) FROM postmatch_sections').fetchone()[0]
    return used+incoming<=16*1024*1024 and free-incoming>=MIN_FREE_DISK_BYTES


def health(conn):
    """Stored receipts and storage guard; deliberately not catalogue coverage."""
    free = _disk_free_bytes(conn)
    row = conn.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(payload_json AS BLOB))),0) FROM postmatch_sections').fetchone()
    return {'state':'READ_UNAVAILABLE' if free is None else 'DISK_RESERVE' if free<MIN_FREE_DISK_BYTES else
            'ARCHIVE_LIMIT' if row[1]>=16*1024*1024 else 'READY',
            'receipts':row[0],'payload_bytes':row[1],'payload_limit':16*1024*1024,
            'disk_free_bytes':free,'disk_reserve_bytes':MIN_FREE_DISK_BYTES,
            'scope':'STORED_RECEIPTS_NOT_MATCH_COVERAGE','external_calls':0}


def text(value):
    return ('' if value is None else str(value)).strip()[:160]


def rows(payload, field):
    if field not in payload:
        raise SourceError('MALFORMED')
    value = payload[field] or []
    if not isinstance(value, list) or len(value) > 1500 or any(not isinstance(r, dict) for r in value):
        raise SourceError('MALFORMED')
    return value


def normalize(items, section, provider, event, match, sid):
    result = []
    for raw in items:
        if provider == 'thesportsdb':
            if str(raw.get('idEvent')) != sid:
                raise SourceError('IDENTITY_MISMATCH')
            home = raw.get('strHome') == 'Yes'
            name = text(raw.get('strTeam'))
            if name:
                if norm(name) not in {norm(match['home_team']), norm(match['away_team'])}:
                    raise SourceError('IDENTITY_MISMATCH')
                home = norm(name) == norm(match['home_team'])
            elif raw.get('strHome') not in {'Yes','No'}:
                raise SourceError('IDENTITY_MISMATCH')
            team = match['home_team'] if home else match['away_team']
            if section == 'lineups':
                pid = integer_id(raw.get('idPlayer'))
                if not pid or not text(raw.get('strPlayer')) or raw.get('strSubstitute') not in {'Yes','No'}:
                    raise SourceError('MALFORMED')
                result.append({'player_id':'sportsdb-'+pid,'player_name':text(raw['strPlayer']),
                    'team_id':text(raw.get('idTeam')),'team_name':team,'position':text(raw.get('strPosition')),
                    'number':text(raw.get('intSquadNumber')),'is_starting':raw['strSubstitute']=='No',
                    'source':'TheSportsDB'})
            else:
                eid = integer_id(raw.get('idTimeline'))
                if not eid or not text(raw.get('strTimeline')):
                    raise SourceError('MALFORMED')
                result.append({'id':'sportsdb-timeline-'+eid,'type':text(raw.get('strTimeline')),
                    'minute':text(raw.get('intTime')),'detail':text(raw.get('strTimelineDetail')),
                    'team':team,'player':text(raw.get('strPlayer')),
                    'related_player':text(raw.get('strAssist')),'source':'TheSportsDB'})
        else:
            teams = event.get('teams') or {}
            expected = {str((teams.get(side) or {}).get('id')):match[side+'_team'] for side in ('home','away')}
            team_info = raw.get('team') or {}
            tid = str(team_info.get('id'))
            if tid not in expected:
                raise SourceError('IDENTITY_MISMATCH')
            team = expected[tid]
            if section == 'lineups':
                for field, starting in (('startXI',True),('substitutes',False)):
                    members = rows(raw,field)
                    for member in members:
                        player = member.get('player') or {}
                        pid = integer_id(player.get('id'))
                        if not pid or not text(player.get('name')):
                            raise SourceError('MALFORMED')
                        result.append({'player_id':'api-football-'+pid,'player_name':text(player['name']),
                            'team_id':'api-football-'+tid,'team_name':team,'position':text(player.get('pos')),
                            'number':text(player.get('number')),'is_starting':starting,
                            'formation':text(raw.get('formation')),'source':'API-Football'})
            else:
                digest = hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()[:24]
                timing = raw.get('time') or {}
                minute = text(timing.get('elapsed'))
                extra = text(timing.get('extra'))
                result.append({'id':'api-football-event-'+sid+'-'+digest,'type':text(raw.get('type')),
                    'minute':minute+('+'+extra if extra and extra!='0' else ''),
                    'detail':text(raw.get('detail')),'team':team,
                    'player':text((raw.get('player') or {}).get('name')),
                    'related_player':text((raw.get('assist') or {}).get('name')),'source':'API-Football'})
    if len(result)>300:
        raise SourceError('MALFORMED')
    return result


def acquire(source, match):
    with source.store.connection() as conn:
        if not capacity(conn):
            return {'sections':[],'reasons':['ARCHIVE_BUDGET'],'external_calls':0}
    observations, reasons = [], []
    sid, fid = source.identities(match)
    for provider in ('api_football','thesportsdb'):
        if provider not in source.config['sources']:
            continue
        try:
            if provider == 'api_football':
                if not fid:
                    reasons.append('MISSING_PROVIDER_ID'); continue
                fixtures = rows(source.request(provider,'fixtures',{'id':fid}),'response')
                if len(fixtures)!=1:
                    raise SourceError('IDENTITY_MISMATCH')
                event = fixtures[0]
                fixture, teams, league = event.get('fixture') or {}, event.get('teams') or {}, event.get('league') or {}
                mapped = {'strHomeTeam':(teams.get('home') or {}).get('name'),
                          'strAwayTeam':(teams.get('away') or {}).get('name'),
                          'strTimestamp':fixture.get('date'),'strLeague':league.get('name')}
                if str(fixture.get('id'))!=fid or not match_event(match,mapped):
                    raise SourceError('IDENTITY_MISMATCH')
                team_ids = [integer_id((teams.get(side) or {}).get('id')) for side in ('home','away')]
                if not all(team_ids) or team_ids[0]==team_ids[1]:
                    raise SourceError('IDENTITY_MISMATCH')
                scope = final_scope((fixture.get('status') or {}).get('short'))
                event_id = fid
                endpoints = (('events','fixtures/events','response'),('lineups','fixtures/lineups','response'))
            else:
                event = source.sportsdb_event(match)
                if not event:
                    reasons.append('NO_EVENT'); continue
                scope = final_scope(event.get('strStatus'))
                event_id = integer_id(event.get('idEvent'))
                endpoints = (('events','lookuptimeline.php','timeline'),('lineups','lookuplineup.php','lineup'))
            if scope != final_scope(match.get('status')):
                raise SourceError('SOURCE_NOT_FINAL')
            for section, endpoint, field in endpoints:
                if any(o['section']==section and o['items'] for o in observations):
                    continue
                try:
                    params = {'fixture':event_id} if provider=='api_football' else {'id':event_id}
                    items = normalize(rows(source.request(provider,endpoint,params),field),section,provider,event,match,event_id)
                    observed = source.receipts.get((provider,endpoint,tuple(sorted(params.items()))),source.clock())
                    observations.append({'section':section,'source':provider,'reference':provider+':event:'+event_id,
                                         'scope':scope,'items':items,'observed_at':observed})
                except (SourceError,BudgetStopped) as exc:
                    reasons.append(str(exc))
            if all(any(o['section']==s and o['items'] for o in observations) for s in ('events','lineups')):
                break
        except (SourceError,BudgetStopped) as exc:
            reasons.append(str(exc))
    return {'sections':observations,'reasons':reasons,'external_calls':source.calls}


def save(conn, job, observations):
    for item in observations:
        if item['section'] not in {'events','lineups'} or item['source'] not in {'api_football','thesportsdb'}:
            raise SourceError('MALFORMED')
        raw = json.dumps(item['items'],sort_keys=True,ensure_ascii=False)
        digest = hashlib.sha256(json.dumps([job['match_id'],job['identity'],item['section'],item['source'],
                                          item['scope'],raw],sort_keys=True).encode()).hexdigest()
        if conn.execute('SELECT 1 FROM postmatch_sections WHERE digest=?',(digest,)).fetchone():
            continue
        if not capacity(conn,len(raw.encode())):
            return 'ARCHIVE_BUDGET'
        conn.execute('INSERT INTO postmatch_sections(match_id,identity,section,source,reference,scope,payload_json,observed_at,digest) '
                     'VALUES(?,?,?,?,?,?,?,?,?)',(job['match_id'],job['identity'],item['section'],item['source'],item['reference'],
                                               item['scope'],raw,item['observed_at'],digest))
    return None


def read(conn, mid, ident, scope):
    result = {}
    for row in conn.execute('SELECT * FROM postmatch_sections WHERE match_id=? AND identity=? AND scope=? '
                            "ORDER BY CASE WHEN payload_json='[]' THEN 1 ELSE 0 END,observed_at DESC,id DESC",
                            (mid,ident,scope)):
        if row['section'] not in result:
            result[row['section']] = {'items':json.loads(row['payload_json']),'source':row['source'],
                'scope':row['scope'],'reference':row['reference'],
                'observed_at':datetime.fromtimestamp(row['observed_at'],timezone.utc).isoformat()}
    return result
