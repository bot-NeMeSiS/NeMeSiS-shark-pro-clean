"""Incremental canonical match coverage. Ingestion writes; page reads never do.

The cursor inventories rows, not provider coverage. Only a validated event lookup
or an already associated video counts as checked. Rights remain in their engine.
"""
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import secrets
import sqlite3
import time
from zoneinfo import ZoneInfo

from engines.postmatch_store import identity, is_final
from engines.postmatch_sources import match_event, integer_id, sportsdb_query_date

STATES = ('UNSCANNED', 'CHECK_PENDING', 'CHECKED_NO_VIDEO', 'VIDEO_FOUND',
          'LINKED', 'RETRY_LATER', 'AMBIGUOUS', 'PROVIDER_ERROR')
RECENT_MARGIN = 3
HISTORY_BATCH = 8
FIELDS = ('id','external_id','source','home_team','away_team','match_date',
          'kickoff_time','competition_name','league_name','league_id','status',
          'score','home_score','away_score','raw_json','country','competition_key','league_key','league')
SCHEMA = '''
CREATE TABLE IF NOT EXISTS highlight_coverage (
 match_id TEXT PRIMARY KEY, identity TEXT NOT NULL, state TEXT NOT NULL,
 event_id TEXT NOT NULL DEFAULT '', checked_at REAL, due_at REAL NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '',
 lease TEXT NOT NULL DEFAULT '', lease_until REAL NOT NULL DEFAULT 0,
 updated_at REAL NOT NULL, priority INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS highlight_coverage_due ON highlight_coverage(state,due_at);
CREATE TABLE IF NOT EXISTS highlight_coverage_cursor (
 id INTEGER PRIMARY KEY CHECK(id=1), row_cursor INTEGER NOT NULL DEFAULT 0,
 updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS highlight_coverage_budget (
 window INTEGER PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0,
 historical_used INTEGER NOT NULL DEFAULT 0);
'''


def eligible(match, now):
    return bool(is_final(match, now) and (match.get('competition_name') or
                match.get('league_name') or match.get('league_id')))


def event_id(match):
    ext = str(match.get('external_id') or '')
    if ext.startswith('sportsdb-'):
        return integer_id(ext.removeprefix('sportsdb-'))
    if 'sportsdb' in str(match.get('source') or '').lower():
        return integer_id(ext)
    return ''


def persisted_event_id(conn, match):
    sid = event_id(match)
    if sid:
        return sid
    cols = {row[1] for row in conn.execute('PRAGMA table_info(sportsdb_event_profiles)')}
    if not {'match_id','sportsdb_event_id','raw_json'} <= cols:
        return ''
    rows = conn.execute('SELECT sportsdb_event_id,raw_json FROM sportsdb_event_profiles WHERE match_id=? LIMIT 2',
                        (str(match['id']),)).fetchall()
    if len(rows) != 1:
        return ''
    try:
        item = json.loads(rows[0]['raw_json'])
        mapped = integer_id(rows[0]['sportsdb_event_id'])
        return mapped if mapped and str(item.get('idEvent')) == mapped and match_event(match,item) else ''
    except (ValueError,TypeError,AttributeError):
        return ''


def persisted_event(conn, match, sid):
    """Reuse an exact provider payload; an ID alone never proves identity."""
    candidates = []
    if event_id(match) == sid:
        candidates.append(match.get('raw_json'))
    cols = {row[1] for row in conn.execute('PRAGMA table_info(sportsdb_event_profiles)')}
    if {'match_id','sportsdb_event_id','raw_json'} <= cols:
        candidates.extend(row['raw_json'] for row in conn.execute(
            'SELECT raw_json FROM sportsdb_event_profiles WHERE match_id=? AND sportsdb_event_id=? LIMIT 2',
            (str(match['id']),sid)))
    valid = []
    for raw in candidates:
        try:
            item = json.loads(raw or '{}')
            if isinstance(item,dict) and str(item.get('idEvent')) == sid and match_event(match,item):
                valid.append(item)
        except (ValueError,TypeError):
            pass
    return valid[0] if valid else None


def retry_delay(match, now, attempts):
    age = (datetime.fromtimestamp(now, ZoneInfo('Europe/Madrid')).date() -
           datetime.fromisoformat(str(match['match_date'])[:10]).date()).days
    if age <= 7:
        return (24 if age>1 and attempts>=2 else 6) * 3600
    if age <= 30:
        return 3 * 86400
    return (90 if attempts >= 3 else 30) * 86400


class Coverage:
    def __init__(self, path, now=None, priority=None):
        self.path = Path(path).resolve()
        self.now = time.time() if now is None else float(now)
        self.priority = priority or (lambda match: 0)

    def connect(self, write=False):
        conn = sqlite3.connect(self.path.as_uri() + ('?mode=rw' if write else '?mode=ro'),
                               uri=True, timeout=.6)
        conn.row_factory = sqlite3.Row
        conn.create_function('coverage_eligible', 1, lambda raw: int(eligible(json.loads(raw), self.now)))
        conn.create_function('coverage_identity', 1, lambda raw: identity(json.loads(raw)))
        if not write:
            conn.execute('PRAGMA query_only=ON')
        return conn

    @staticmethod
    def projection(conn, alias='m'):
        cols = {row[1] for row in conn.execute('PRAGMA table_info(matches)')}
        return 'json_object(' + ','.join("'%s',%s.%s" % (k, alias, k)
                                         for k in FIELDS if k in cols) + ')'

    def prepare(self, batch=200):
        """Bounded inventory; anti-join also notices old rows becoming finalized.

        No provider calls and no writes to matches. Row cursor survives deployment.
        Identity changes invalidate checked evidence before another lookup.
        """
        with closing(self.connect(True)) as conn, conn:
            conn.executescript(SCHEMA)
            budget_cols = {row[1] for row in conn.execute('PRAGMA table_info(highlight_coverage_budget)')}
            for name, default in [('recent_reserve',RECENT_MARGIN),('historical_checked',0)]:
                if name not in budget_cols:
                    conn.execute(f'ALTER TABLE highlight_coverage_budget ADD COLUMN {name} INTEGER NOT NULL DEFAULT {default}')
            conn.execute('INSERT OR IGNORE INTO highlight_coverage_cursor(id,row_cursor,updated_at) VALUES(1,0,?)', (self.now,))
            cursor_cols = {row[1] for row in conn.execute('PRAGMA table_info(highlight_coverage_cursor)')}
            if 'media_row_cursor' not in cursor_cols:
                conn.execute('ALTER TABLE highlight_coverage_cursor ADD COLUMN media_row_cursor INTEGER NOT NULL DEFAULT 0')
            cursor = conn.execute('SELECT row_cursor FROM highlight_coverage_cursor').fetchone()[0]
            expr = self.projection(conn)
            rows = conn.execute(f'SELECT m.rowid AS inventory_row,{expr} AS payload FROM matches m '
                                'WHERE m.rowid>? ORDER BY m.rowid LIMIT ?', (cursor, batch)).fetchall()
            if rows:
                conn.execute('UPDATE highlight_coverage_cursor SET row_cursor=?,updated_at=?',
                             (rows[-1]['inventory_row'], self.now))
            # Changed identity and newly final matches below the inventory cursor.
            extra = conn.execute(f'SELECT {expr} AS payload FROM matches m '
                'LEFT JOIN highlight_coverage c ON c.match_id=m.id '
                f'WHERE coverage_eligible({expr}) AND (c.match_id IS NULL OR c.identity<>coverage_identity({expr})) '
                'ORDER BY m.match_date DESC,m.id LIMIT ?', (batch,)).fetchall()
            # Catalogue evidence has its own bounded persistent traversal. A
            # linked historical match need not wait behind the inventory scan.
            # Missing/ambiguous associations are excluded; payloads are verified
            # again below, so a stored link alone never proves coverage.
            media_cursor = conn.execute('SELECT media_row_cursor FROM highlight_coverage_cursor').fetchone()[0]
            def media_rows(after):
                return conn.execute(f'SELECT h.rowid AS media_row,{expr} AS payload '
                    'FROM sportsdb_match_highlights h JOIN matches m ON m.id=h.match_id '
                    "WHERE h.rowid>? AND COALESCE(h.video_url,'')<>'' ORDER BY h.rowid LIMIT ?",
                    (after,batch)).fetchall()
            catalogue = media_rows(media_cursor)
            if not catalogue and media_cursor:
                catalogue = media_rows(0)
            if catalogue:
                conn.execute('UPDATE highlight_coverage_cursor SET media_row_cursor=?',
                             (catalogue[-1]['media_row'],))
            for raw in list(rows) + list(extra) + list(catalogue):
                match = json.loads(raw['payload'])
                if not eligible(match, self.now):
                    continue
                conn.execute('INSERT INTO highlight_coverage(match_id,identity,state,event_id,due_at,updated_at,priority) '
                    "VALUES(?,?,'UNSCANNED',?,?,?,?) ON CONFLICT(match_id) DO UPDATE SET "
                    "identity=excluded.identity,state='UNSCANNED',event_id=excluded.event_id,checked_at=NULL,"
                    "attempts=0,due_at=excluded.due_at,reason='',lease='',lease_until=0,updated_at=excluded.updated_at,priority=excluded.priority "
                    'WHERE highlight_coverage.identity<>excluded.identity',
                    (str(match['id']), identity(match), persisted_event_id(conn,match), self.now, self.now,int(self.priority(match))))
                conn.execute('UPDATE highlight_coverage SET priority=? WHERE match_id=? AND identity=?',
                             (int(self.priority(match)),str(match['id']),identity(match)))
            # Reuse concrete catalog evidence rather than buying another lookup
            # for an already linked video. The two unassociated assets are excluded.
            from engines.sportsdb_highlights_engine import _find_match
            from engines.highlight_url_engine import public_https_url
            media_ids = [raw['media_row'] for raw in catalogue]
            known = conn.execute('SELECT c.match_id,h.raw_json,h.video_url FROM highlight_coverage c '
                'JOIN sportsdb_match_highlights h ON h.match_id=c.match_id '
                "WHERE c.state<>'LINKED' AND c.lease_until<=? AND h.rowid IN (" +
                ','.join('?' for _ in media_ids) + ')', (self.now,*media_ids)).fetchall() if media_ids else []
            for item in known:
                try:
                    event = json.loads(item['raw_json'])
                except (ValueError,TypeError):
                    continue
                match = dict(conn.execute('SELECT * FROM matches WHERE id=?',(item['match_id'],)).fetchone())
                if (public_https_url(item['video_url']) and match_event(match,event) and
                        _find_match(conn,event) == item['match_id'] and eligible(match,self.now)):
                    conn.execute("UPDATE highlight_coverage SET state='LINKED',reason='CATALOGUE_LINK_REUSED',"
                        "event_id=?,checked_at=?,updated_at=? WHERE match_id=? AND identity=?",
                        (integer_id(event.get('idEvent')),self.now,self.now,item['match_id'],identity(match)))

    def claim(self, historical=True):
        with closing(self.connect(True)) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM highlight_coverage WHERE lease_until>? LIMIT 1', (self.now,)).fetchone():
                return None
            expr = self.projection(conn)
            cutoff = datetime.fromtimestamp(self.now - 7 * 86400, ZoneInfo('Europe/Madrid')).date().isoformat()
            row = conn.execute(f'SELECT c.*,{expr} AS payload FROM highlight_coverage c JOIN matches m ON m.id=c.match_id '
                f'WHERE coverage_eligible({expr}) AND c.identity=coverage_identity({expr}) '
                "AND c.state NOT IN ('LINKED','VIDEO_FOUND','AMBIGUOUS') AND c.due_at<=? AND c.lease_until<=? "
                + ('AND substr(m.match_date,1,10)<? ' if historical else '') +
                'ORDER BY CASE WHEN c.checked_at IS NULL THEN 0 ELSE 1 END,c.priority DESC,c.due_at,m.match_date DESC,c.match_id LIMIT 1',
                (self.now, self.now, cutoff) if historical else (self.now, self.now)).fetchone()
            if not row:
                return None
            job = dict(row)
            job['historical'] = historical
            job['match'] = json.loads(job.pop('payload'))
            job['lease'] = secrets.token_hex(16)
            conn.execute("UPDATE highlight_coverage SET state='CHECK_PENDING',lease=?,lease_until=?,updated_at=? WHERE match_id=?",
                         (job['lease'], self.now + 90, self.now, job['match_id']))
            return job

    def has_due_history(self):
        cutoff = datetime.fromtimestamp(self.now-7*86400,ZoneInfo('Europe/Madrid')).date().isoformat()
        with closing(self.connect()) as conn:
            return bool(conn.execute('SELECT 1 FROM highlight_coverage c JOIN matches m ON m.id=c.match_id '
                "WHERE c.state NOT IN ('LINKED','VIDEO_FOUND','AMBIGUOUS') AND c.due_at<=? AND substr(m.match_date,1,10)<? LIMIT 1",
                (self.now,cutoff)).fetchone())

    def set_recent_reserve(self, pending_calls=0):
        """Recent demand and an operational margin precede historical spending."""
        remaining = (int(self.now//21600)+1)*21600-self.now
        margin = 1 if remaining<=1800 else RECENT_MARGIN
        reserve = min(12,max(margin,int(pending_calls)))
        with closing(self.connect(True)) as conn, conn:
            conn.execute('INSERT OR IGNORE INTO highlight_coverage_budget(window) VALUES(?)',(int(self.now//21600),))
            conn.execute('UPDATE highlight_coverage_budget SET recent_reserve=? WHERE window=?',
                         (reserve,int(self.now//21600)))

    def media_allowance(self):
        with closing(self.connect()) as conn:
            row = conn.execute('SELECT * FROM highlight_coverage_budget WHERE window=?',(int(self.now//21600),)).fetchone()
        used = row['used'] if row else 0
        reserved = row['recent_reserve'] if row else RECENT_MARGIN
        return {'limit':12,'used':used,'recent_used':used-(row['historical_used'] if row else 0),
                'historical_used':row['historical_used'] if row else 0,'remaining':max(0,12-used),
                'recent_reserved':reserved,'historical_available':max(0,12-used-reserved),
                'historical_checked':row['historical_checked'] if row else 0,'window_hours':6}

    def reserve_media_call(self, historical=False):
        """Twelve calls per six hours; history consumes only unreserved capacity.

        This caps the existing 12-call / 360-minute collector allowance rather
        than multiplying it when the master invokes the persistent queue again.
        Atomic reservation precedes HTTP; restarts and errors never refund calls.
        """
        from engines.sportsdb_request_budget import SportsDBStopped
        window = int(self.now // (6 * 3600))
        with closing(self.connect(True)) as conn, conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('INSERT OR IGNORE INTO highlight_coverage_budget(window) VALUES(?)',(window,))
            row = conn.execute('SELECT * FROM highlight_coverage_budget WHERE window=?',(window,)).fetchone()
            if row['used'] >= 12 or (historical and row['used'] >= 12-row['recent_reserve']):
                raise SportsDBStopped('MEDIA_BUDGET')
            conn.execute('UPDATE highlight_coverage_budget SET used=used+1,historical_used=historical_used+? WHERE window=?',
                         (int(historical),window))
            conn.execute('DELETE FROM highlight_coverage_budget WHERE window<?',(window-120,))

    def finish(self, job, state, reason='', checked=False, sid=''):
        assert state in STATES
        match = job['match']
        attempts = job['attempts'] + int(checked or state == 'PROVIDER_ERROR')
        delay = retry_delay(match, self.now, attempts) if checked else (3600 if state == 'PROVIDER_ERROR' else 86400)
        if reason == 'MEDIA_BUDGET':
            delay = (int(self.now // 21600) + 1) * 21600 + 5 - self.now
        elif reason in {'TIME_BUDGET','REQUEST_BUDGET','ITEM_BUDGET'}:
            delay = 300
        with closing(self.connect(True)) as conn, conn:
            current = conn.execute('SELECT * FROM matches WHERE id=?', (job['match_id'],)).fetchone()
            if not current or not eligible(dict(current), self.now) or identity(dict(current)) != job['identity']:
                return False
            updated = bool(conn.execute('UPDATE highlight_coverage SET state=?,reason=?,event_id=?,checked_at=CASE WHEN ? '
                'THEN ? ELSE checked_at END,attempts=?,due_at=?,lease=\'\',lease_until=0,updated_at=? '
                'WHERE match_id=? AND identity=? AND lease=? AND lease_until>?',
                (state, reason, sid or job['event_id'], checked, self.now, attempts, self.now+delay,
                 self.now, job['match_id'], job['identity'], job['lease'], self.now)).rowcount)
            if updated and checked and job.get('historical') and job['checked_at'] is None:
                conn.execute('INSERT OR IGNORE INTO highlight_coverage_budget(window) VALUES(?)',(int(self.now//21600),))
                conn.execute('UPDATE highlight_coverage_budget SET historical_checked=historical_checked+1 WHERE window=?',
                             (int(self.now//21600),))
            return updated

    def observe(self, sid, items):
        """Recent exact lookups update the same evidence, including empty responses."""
        with closing(self.connect(True)) as conn, conn:
            jobs = conn.execute('SELECT c.*,m.* FROM highlight_coverage c JOIN matches m ON m.id=c.match_id '
                'WHERE (c.event_id=? OR c.match_id IN (SELECT match_id FROM sportsdb_match_highlights WHERE sportsdb_event_id=?)) '
                'AND c.lease_until<=?', (sid,sid,self.now)).fetchall()
            for raw in jobs:
                match = conn.execute('SELECT * FROM matches WHERE id=?', (raw['match_id'],)).fetchone()
                match = dict(match)
                if not eligible(match, self.now) or identity(match) != raw['identity']:
                    continue
                if raw['checked_at'] == self.now:
                    continue
                state = 'CHECKED_NO_VIDEO'
                if items:
                    from engines.sportsdb_highlights_engine import _find_match, _video_url
                    from engines.highlight_url_engine import public_https_url
                    valid = [item for item in items if public_https_url(_video_url(item))]
                    if valid:
                        state = 'LINKED' if all(_find_match(conn, item) == match['id'] for item in valid) else 'AMBIGUOUS'
                    elif any(_video_url(item) for item in items):
                        state = 'PROVIDER_ERROR'  # Invalid URL does not prove no video.
                attempts = raw['attempts'] + 1
                conn.execute('UPDATE highlight_coverage SET state=?,checked_at=CASE WHEN ? THEN ? ELSE checked_at END,'
                    'reason=?,attempts=?,due_at=?,updated_at=?,event_id=? WHERE match_id=?',
                    (state, state != 'PROVIDER_ERROR', self.now, 'NO_VIDEO' if state == 'CHECKED_NO_VIDEO' else state,
                     attempts, self.now + retry_delay(match, self.now, attempts), self.now, sid, raw['match_id']))

    def snapshot(self):
        unknown = {'read_state':'NOT_INITIALIZED','eligible':None,'inventoried':None,'checked':None,'pending':None,'coverage_percent':None,
                   'states':{},'cursor':None,'next_batch':[], 'external_calls':0}
        try:
            with closing(self.connect()) as conn:
                # Denominator and evidence must come from the same database
                # snapshot while sports ingestion updates matches concurrently.
                conn.execute('BEGIN')
                expr = self.projection(conn)
                total = conn.execute(f'SELECT COUNT(*) FROM matches m WHERE coverage_eligible({expr})').fetchone()[0]
                exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='highlight_coverage'").fetchone()
                if not exists:
                    return {**unknown, 'read_state':'UNSCANNED','eligible':total,'inventoried':0,'checked':0,'pending':total,
                            'coverage_percent':0 if total else None,'states':{'UNSCANNED':total}}
                rows = conn.execute(f'SELECT c.state,COUNT(*) AS n,SUM(c.checked_at IS NOT NULL) AS checked '
                    'FROM highlight_coverage c JOIN matches m ON m.id=c.match_id '
                    f'WHERE coverage_eligible({expr}) AND c.identity=coverage_identity({expr}) GROUP BY c.state').fetchall()
                states = {row['state']:row['n'] for row in rows}
                states['UNSCANNED'] = states.get('UNSCANNED',0) + total - sum(states.values())
                states = {state:states.get(state,0) for state in STATES}
                checked = sum(row['checked'] for row in rows)
                cursor = dict(conn.execute('SELECT * FROM highlight_coverage_cursor').fetchone())
                cursor['catalogue_rows'] = conn.execute('SELECT COUNT(*) FROM matches').fetchone()[0]
                cursor['last_row'] = conn.execute('SELECT COALESCE(MAX(rowid),0) FROM matches').fetchone()[0]
                budget_row = conn.execute('SELECT * FROM highlight_coverage_budget WHERE window=?',
                                          (int(self.now//21600),)).fetchone()
                budget = dict(budget_row) if budget_row else None
                cutoff = datetime.fromtimestamp(self.now-7*86400,ZoneInfo('Europe/Madrid')).date().isoformat()
                upcoming = [dict(row) for row in conn.execute('SELECT c.match_id,c.state,c.event_id,c.due_at FROM highlight_coverage c '
                    'JOIN matches m ON m.id=c.match_id '
                    f"WHERE c.state NOT IN ('LINKED','VIDEO_FOUND','AMBIGUOUS') AND substr(m.match_date,1,10)<? AND coverage_eligible({expr}) "
                    f'AND c.identity=coverage_identity({expr}) ORDER BY CASE WHEN c.checked_at IS NULL THEN 0 ELSE 1 END,'
                    'c.priority DESC,c.due_at,m.match_date DESC,c.match_id LIMIT 3',(cutoff,))]
                inventoried = sum(row['n'] for row in rows)
                used = budget['used'] if budget else 0
                reserved = budget.get('recent_reserve',RECENT_MARGIN) if budget else RECENT_MARGIN
                return {**unknown,'read_state':'VERIFIED','eligible':total,'inventoried':inventoried,'checked':checked,'pending':total-checked,
                        'coverage_percent':round(100*checked/total,2) if total else None,'states':states,
                        'cursor':cursor,'next_batch':upcoming,'batch_limit':HISTORY_BATCH,
                        'media_budget':{'window_hours':6,'limit':12,'used':used,'remaining':max(0,12-used),
                            'recent_used':used-(budget['historical_used'] if budget else 0),'recent_reserved':reserved,
                            'historical_available':max(0,12-used-reserved),
                            'historical_checked':budget.get('historical_checked',0) if budget else 0,
                            'historical_used':budget['historical_used'] if budget else 0},
                        'note':'Comprobados por evento; catálogo de vídeos y permisos son métricas independientes.'}
        except (sqlite3.Error, OSError, ValueError, TypeError):
            return {**unknown,'read_state':'READ_UNAVAILABLE'}


def run_one(coverage, scope, lookup, save, v1, batch_lookup=None):
    """One historical match, inside the collector's existing 12-call allowance.

    Reconciliation uses the existing exact date/teams/competition contract. This
    lane never reserves any of the separate 60/day critical postmatch allowance.
    """
    from engines.sportsdb_request_budget import SportsDBStopped
    from engines.sportsdb_highlights_engine import _find_match, _video_url
    from engines.highlight_url_engine import public_https_url
    if scope.calls >= scope.max_calls or scope.remaining() < 1:
        return {'processed':0,'state':'RETRY_LATER','reason':'BUDGET_RESERVED_FOR_RECENT'}
    job = coverage.claim()
    if not job:
        return {'processed':0,'state':'IDLE'}
    sid, match = job['event_id'], job['match']
    try:
        # Persist exact event verification by identity. Empty V2 is only evidence
        # about this match after the provider mapping has been checked.
        cache_key = 'coverage:identity:' + job['identity']
        with closing(coverage.connect()) as conn:
            cached = conn.execute('SELECT payload_json,expires_at FROM sportsdb_highlight_feed_cache WHERE cache_key=?',
                                  (cache_key,)).fetchone()
        event = None
        if cached and datetime.fromisoformat(cached['expires_at']).timestamp() > coverage.now:
            event = json.loads(cached['payload_json'])
        if not event and sid:
            with closing(coverage.connect()) as conn:
                event = persisted_event(conn,match,sid)
        if batch_lookup:
            feed = batch_lookup(match)
            exact = [item for item in feed if match_event(match,item) and
                     (not sid or str(item.get('idEvent')) == sid)]
            if len(exact) == 1:
                # Complete event metadata can verify identity, but absent video
                # metadata still requires the exact Premium V2 lookup below.
                event = exact[0]
        if not event:
            params = {'id':sid} if sid else {'d':sportsdb_query_date(match),'s':'Soccer'}
            endpoint = 'lookupevent.php' if sid else 'eventsday.php'
            payload = scope.call(1, endpoint, params, lambda: v1(endpoint, params))
            if 'events' not in payload or (payload['events'] is not None and not isinstance(payload['events'],list)):
                raise SportsDBStopped('MALFORMED')
            rows = payload['events'] or []
            if len(rows) > 1500 or any(not isinstance(row,dict) for row in rows):
                raise SportsDBStopped('MALFORMED')
            found = [row for row in rows if match_event(match,row) and (not sid or str(row.get('idEvent')) == sid)]
            if len(found) > 1:
                coverage.finish(job,'AMBIGUOUS','AMBIGUOUS_MATCH')
                return {'processed':1,'state':'AMBIGUOUS'}
            if not found:
                state = 'AMBIGUOUS' if sid and rows else 'RETRY_LATER'
                reason = 'IDENTITY_MISMATCH' if sid and rows else 'NO_EVENT'
                coverage.finish(job,state,reason)
                return {'processed':1,'state':state,'reason':reason}
            event = found[0]
            sid = integer_id(event.get('idEvent'))
            if not sid:
                raise SportsDBStopped('MALFORMED')
            with closing(coverage.connect(True)) as conn, conn:
                conn.execute('INSERT OR REPLACE INTO sportsdb_highlight_feed_cache VALUES(?,?,?,?)',
                    (cache_key,json.dumps(event),datetime.fromtimestamp(coverage.now,ZoneInfo('Europe/Madrid')).isoformat(),
                     datetime.fromtimestamp(coverage.now+90*86400,ZoneInfo('Europe/Madrid')).isoformat()))
        # Reject a stale or inconsistent identity cache too.
        if not match_event(match,event) or not integer_id(event.get('idEvent')) or (sid and str(event.get('idEvent'))!=sid):
            raise SportsDBStopped('IDENTITY_MISMATCH')
        sid = integer_id(event.get('idEvent'))
        if public_https_url(_video_url(event)):
            with closing(coverage.connect()) as conn:
                exact = _find_match(conn,event) == match['id']
            if exact:
                save([event])
                coverage.finish(job,'LINKED','PROFILE_VIDEO_REUSED',checked=True,sid=sid)
                return {'processed':1,'state':'LINKED','evidence':'PERSISTED_EVENT_PROFILE'}
        items = lookup(sid)
        valid = [dict(item) for item in items if public_https_url(_video_url(item))]
        for item in valid:
            for field in ('strHomeTeam','strAwayTeam','dateEvent','strTimestamp','strLeague','idLeague'):
                if not item.get(field) and event.get(field):
                    item[field] = event[field]  # Same exact V2 event, verified above.
        if not valid and any(_video_url(item) for item in items):
            raise SportsDBStopped('MALFORMED')
        state = 'CHECKED_NO_VIDEO'
        if valid:
            with closing(coverage.connect()) as conn:
                if any(_find_match(conn,item) != match['id'] for item in valid):
                    coverage.finish(job,'AMBIGUOUS','AMBIGUOUS_MATCH',sid=sid)
                    return {'processed':1,'state':'AMBIGUOUS'}
            save(valid)
            state = 'LINKED'
        if not coverage.finish(job,state,'NO_VIDEO' if not valid else 'VIDEO_FOUND',checked=True,sid=sid):
            return {'processed':1,'state':'RETRY_LATER','reason':'IDENTITY_CHANGED'}
        return {'processed':1,'state':state}
    except SportsDBStopped as exc:
        reason = str(exc)
        deferred = reason in {'REQUEST_BUDGET','TIME_BUDGET','ITEM_BUDGET','MEDIA_BUDGET'}
        coverage.finish(job,'RETRY_LATER' if deferred else 'AMBIGUOUS' if reason == 'IDENTITY_MISMATCH' else 'PROVIDER_ERROR',reason,sid=sid)
        if not deferred:
            raise
        return {'processed':1,'state':'RETRY_LATER','reason':reason}
