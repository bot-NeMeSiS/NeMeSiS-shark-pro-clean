"""Durable, fenced post-match jobs and append-only statistical evidence.

All mutation is explicit. Readers never create a database/schema. No provider I/O
is performed while a SQLite write lock is held. Production starts paused.
"""
from __future__ import annotations

from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from zoneinfo import ZoneInfo

CONTRACT = 'NEMESIS-POSTMATCH-RECOVERY-V1'
KINDS = ('highlights', 'statistics')
SOURCES = ('thesportsdb', 'api_football')
RETRY_DELAYS = (1800, 7200, 43200, 172800)
FINAL_STATUSES = {'FT', 'AET', 'PEN'}
DEFAULT = {'enabled': False, 'sources': [], 'daily_limit': 60, 'batch_size': 2}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS postmatch_settings (
 id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, actor TEXT NOT NULL,
 updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS postmatch_jobs (
 id INTEGER PRIMARY KEY, match_id TEXT NOT NULL, kind TEXT NOT NULL,
 identity TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0, due_at REAL NOT NULL,
 checks INTEGER NOT NULL DEFAULT 0,
 priority INTEGER NOT NULL DEFAULT 0, match_day TEXT NOT NULL DEFAULT '',
 lease_token TEXT, lease_until REAL NOT NULL DEFAULT 0,
 reason TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL, updated_at REAL NOT NULL,
 UNIQUE(match_id,kind,identity));
CREATE INDEX IF NOT EXISTS postmatch_due ON postmatch_jobs(state,due_at,lease_until);
CREATE TABLE IF NOT EXISTS postmatch_observations (
 id INTEGER PRIMARY KEY, match_id TEXT NOT NULL, identity TEXT NOT NULL,
 source TEXT NOT NULL, reference TEXT NOT NULL, scope TEXT NOT NULL,
 values_json TEXT NOT NULL, observed_at REAL NOT NULL, digest TEXT NOT NULL UNIQUE);
CREATE INDEX IF NOT EXISTS postmatch_obs_match ON postmatch_observations(match_id,identity);
CREATE TABLE IF NOT EXISTS postmatch_selected (
 match_id TEXT NOT NULL, identity TEXT NOT NULL, stat_key TEXT NOT NULL,
 observation_id INTEGER NOT NULL, PRIMARY KEY(match_id,identity,stat_key));
CREATE TABLE IF NOT EXISTS postmatch_manual_locks (
 match_id TEXT NOT NULL, identity TEXT NOT NULL, stat_key TEXT NOT NULL,
 PRIMARY KEY(match_id,identity,stat_key));
CREATE TABLE IF NOT EXISTS postmatch_audit (
 id INTEGER PRIMARY KEY, job_id INTEGER, action TEXT NOT NULL,
 detail TEXT NOT NULL, actor TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS postmatch_source_budget (
 source TEXT NOT NULL, day TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(source,day));
CREATE TABLE IF NOT EXISTS postmatch_circuits (
 source TEXT PRIMARY KEY, failures INTEGER NOT NULL DEFAULT 0,
 blocked_until REAL NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS postmatch_request_cache (
 cache_key TEXT PRIMARY KEY, identity TEXT NOT NULL, payload_json TEXT NOT NULL,
 expires_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS postmatch_sections (
 id INTEGER PRIMARY KEY, match_id TEXT NOT NULL, identity TEXT NOT NULL,
 section TEXT NOT NULL, source TEXT NOT NULL, reference TEXT NOT NULL,
 scope TEXT NOT NULL, payload_json TEXT NOT NULL, observed_at REAL NOT NULL,
 digest TEXT NOT NULL UNIQUE);
CREATE INDEX IF NOT EXISTS postmatch_sections_match ON postmatch_sections(match_id,identity,scope,observed_at);
CREATE TABLE IF NOT EXISTS postmatch_inventory_cursor (
 id INTEGER PRIMARY KEY CHECK(id=1), row_cursor INTEGER NOT NULL DEFAULT 0, updated_at REAL NOT NULL);
'''


def stamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec='seconds')


def identity(match: dict) -> str:
    # Exclude mutable score/refresh timestamps; a new date/team/competition is a new job.
    fields = ('id', 'home_team', 'away_team', 'match_date', 'kickoff_time',
              'external_id', 'source', 'competition_name', 'league_name', 'league_id')
    raw = {key: str(match.get(key) or '').strip() for key in fields}
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()


def is_final(match: dict, now: float | None = None) -> bool:
    from engines.v935_launch_trust_engine import match_status_truth, match_kickoff_madrid
    if not (match.get('id') and match.get('source') and match.get('home_team') and match.get('away_team')):
        return False
    clock = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc)
    kickoff = match_kickoff_madrid(match)
    # Neither elapsed time nor score alone can imply a final.
    return bool(kickoff and kickoff <= clock and match_status_truth(match, clock).get('lifecycle') == 'FINISHED')


class StaleLease(RuntimeError):
    pass


class BudgetStopped(RuntimeError):
    pass


class Store:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()

    @contextmanager
    def connection(self, write=False):
        conn = sqlite3.connect(self.path.as_uri() + ('?mode=rw' if write else '?mode=ro'),
                               uri=True, timeout=.6)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA busy_timeout=600')
            if not write:
                conn.execute('PRAGMA query_only=ON')
            conn.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield conn
            if write:
                conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        # Only called by an explicit authenticated admin action or offline test setup.
        if not self.path.is_file():
            raise ValueError('La base de datos existente no está disponible.')
        with closing(sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=.6)) as conn:
            conn.executescript(SCHEMA)
            columns = {row[1] for row in conn.execute('PRAGMA table_info(postmatch_jobs)')}
            for field,spec in (('checks','INTEGER NOT NULL DEFAULT 0'),('priority','INTEGER NOT NULL DEFAULT 0'),
                               ('match_day',"TEXT NOT NULL DEFAULT ''")):
                if field not in columns:
                    conn.execute('ALTER TABLE postmatch_jobs ADD COLUMN '+field+' '+spec)
            conn.commit()
        from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema
        ensure_sportsdb_highlights_schema(str(self.path))

    def config(self) -> dict:
        try:
            with self.connection() as conn:
                row = conn.execute('SELECT payload FROM postmatch_settings WHERE id=1').fetchone()
            if not row:
                return {**DEFAULT, 'read_state':'NOT_INITIALIZED'}
            payload = json.loads(row[0])
            if (not isinstance(payload, dict) or type(payload.get('enabled')) is not bool
                or not isinstance(payload.get('sources'), list)
                or not all(source in SOURCES for source in payload['sources'])
                or type(payload.get('daily_limit')) is not int or not 1 <= payload['daily_limit'] <= 200):
                raise ValueError('INVALID_CONFIG')
            return {**DEFAULT, **payload, 'read_state':'VERIFIED'}
        except sqlite3.OperationalError as exc:
            state = 'NOT_INITIALIZED' if 'no such table' in str(exc) or not self.path.is_file() else 'READ_UNAVAILABLE'
            return {**DEFAULT, 'read_state':state}
        except (OSError, sqlite3.Error, ValueError, TypeError):
            return {**DEFAULT, 'read_state':'READ_UNAVAILABLE'}

    def configure(self, *, enabled, sources, daily_limit, actor, confirmed=False):
        if type(enabled) is not bool or not actor or not isinstance(sources, list) or not set(sources) <= set(SOURCES):
            raise ValueError('Configuración no válida.')
        if enabled and (not sources or not confirmed):
            raise ValueError('Confirma los permisos de las fuentes antes de activar.')
        budget = int(daily_limit)
        if not 1 <= budget <= 200:
            raise ValueError('El presupuesto debe estar entre 1 y 200 consultas diarias.')
        self.initialize()
        payload = {**DEFAULT, 'enabled': enabled, 'sources': sorted(set(sources)), 'daily_limit': budget}
        now = time.time()
        with self.connection(True) as conn:
            conn.execute('INSERT INTO postmatch_settings VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                         'payload=excluded.payload,actor=excluded.actor,updated_at=excluded.updated_at',
                         (json.dumps(payload), str(actor)[:120], now))
            self.audit(conn, None, 'CONFIGURATION', payload, actor, now)
        return payload

    @staticmethod
    def audit(conn, job, action, detail, actor, now):
        conn.execute('INSERT INTO postmatch_audit(job_id,action,detail,actor,created_at) VALUES(?,?,?,?,?)',
                     (job, action, json.dumps(detail, ensure_ascii=False, sort_keys=True), str(actor)[:120], now))

    def discover(self, now: float, *, include_archive=False, priority=None, inventory_batch=250) -> int:
        day = datetime.fromtimestamp(now - 7 * 86400, ZoneInfo('Europe/Madrid')).date().isoformat()
        with self.connection(True) as conn:
            # Only source-confirmed terminal matches; include score truth checks below.
            rows = conn.execute("SELECT * FROM matches WHERE substr(match_date,1,10)>=? "
                                "AND upper(status) IN ('FT','FINISHED','FINAL','AET','PEN','FINALIZADO') "
                                "ORDER BY match_date DESC,id LIMIT 500", (day,)).fetchall()
            if include_archive:
                conn.execute('INSERT OR IGNORE INTO postmatch_inventory_cursor VALUES(1,0,?)',(now,))
                cursor = conn.execute('SELECT row_cursor FROM postmatch_inventory_cursor WHERE id=1').fetchone()[0]
                historical = conn.execute('SELECT rowid AS inventory_row,* FROM matches WHERE rowid>? '
                                          'ORDER BY rowid LIMIT ?',(cursor,max(1,min(500,int(inventory_batch))))).fetchall()
                conn.execute('UPDATE postmatch_inventory_cursor SET row_cursor=?,updated_at=? WHERE id=1',
                             (historical[-1]['inventory_row'] if historical else 0,now))
                rows = list(rows)+list(historical)
            count = 0
            seen = set()
            for raw in rows:
                match = dict(raw)
                if str(match.get('id')) in seen or not is_final(match, now) or not (
                    match.get('competition_name') or match.get('league_name') or match.get('league_id')):
                    continue
                seen.add(str(match['id']))
                mid, ident = str(match['id']), identity(match)
                conn.execute("UPDATE postmatch_jobs SET state='CANCELLED',reason='IDENTITY_CHANGED',"
                             "lease_token=NULL,lease_until=0,updated_at=? WHERE match_id=? AND identity<>? "
                             "AND state NOT IN ('COMPLETE','CANCELLED')", (now, mid, ident))
                for kind in (*KINDS, 'archive') if include_archive else KINDS:
                    count += conn.execute('INSERT OR IGNORE INTO postmatch_jobs'
                        '(match_id,kind,identity,due_at,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                        (mid, kind, ident, now, now, now)).rowcount
                conn.execute('UPDATE postmatch_jobs SET priority=?,match_day=? WHERE match_id=? AND identity=?',
                             (int(priority(match)) if priority else 0,str(match['match_date'])[:10],mid,ident))
                if include_archive:
                    from engines.postmatch_sources import final_scope
                    scope = final_scope(match.get('status'))
                    # A corrected period must be checked again, without mixing old receipts.
                    conn.execute("UPDATE postmatch_jobs SET state='PENDING',attempts=0,due_at=?,reason='SCOPE_CHANGED' "
                                 "WHERE match_id=? AND identity=? AND kind='archive' AND state='COMPLETE' "
                                 'AND EXISTS (SELECT 1 FROM postmatch_sections s WHERE s.match_id=? AND s.identity=? AND s.scope<>?) '
                                 'AND NOT EXISTS (SELECT 1 FROM postmatch_sections s WHERE s.match_id=? AND s.identity=? '
                                 "AND s.scope=? AND s.payload_json<>'[]' GROUP BY s.match_id HAVING COUNT(DISTINCT section)=2)",
                                 (now,mid,ident,mid,ident,scope,mid,ident,scope))
            return count

    def claim(self, now: float, *, prefer_critical=False) -> dict | None:
        with self.connection(True) as conn:
            if conn.execute("SELECT COUNT(*) FROM postmatch_jobs WHERE state='RUNNING' AND lease_until>?", (now,)).fetchone()[0]:
                return None  # One bounded processor across all web workers / overlapping crons.
            # Exhausted jobs must not consume the entire tick while other due
            # work is ready. Preserve the error-attempt ceiling and lease fencing.
            conn.execute("UPDATE postmatch_jobs SET state='FAILED',reason='ATTEMPTS_EXHAUSTED',"
                         "lease_token=NULL,lease_until=0,updated_at=? WHERE attempts>=5 AND "
                         "((state IN ('PENDING','RETRY') AND due_at<=?) OR "
                         "(state='RUNNING' AND lease_until<=?))", (now, now, now))
            priority = ("CASE WHEN state='RUNNING' THEN 0 ELSE 1 END,"
                        "CASE WHEN match_day>='"+datetime.fromtimestamp(now-7*86400,ZoneInfo('Europe/Madrid')).date().isoformat()+"' THEN 0 ELSE 1 END,"
                        "CASE kind WHEN 'statistics' THEN 0 WHEN 'archive' THEN 1 ELSE 2 END,match_day DESC,priority DESC,"
                        if prefer_critical else '')
            row = conn.execute("SELECT * FROM postmatch_jobs WHERE "
                               "(state IN ('PENDING','RETRY') AND due_at<=?) OR "
                               "(state='RUNNING' AND lease_until<=?) ORDER BY " + priority + "due_at,"
                               "CASE WHEN state='RUNNING' THEN 0 ELSE 1 END,attempts,id LIMIT 1", (now, now)).fetchone()
            if not row:
                return None
            token = secrets.token_hex(16)
            job = dict(row)
            if job['attempts'] >= 5:
                conn.execute("UPDATE postmatch_jobs SET state='FAILED',reason='ATTEMPTS_EXHAUSTED',"
                             "lease_token=NULL,lease_until=0,updated_at=? WHERE id=?", (now, job['id']))
                return None
            conn.execute("UPDATE postmatch_jobs SET state='RUNNING',attempts=attempts+1,"
                         "lease_token=?,lease_until=?,updated_at=? WHERE id=?", (token, now + 90, now, job['id']))
            self.audit(conn, job['id'], 'CLAIM', {'recovered_lease': job['state'] == 'RUNNING'}, 'worker', now)
            return {**job, 'lease_token': token, 'attempts': job['attempts'] + 1, 'lease_until': now + 90}

    def cached_request(self, key, ident, now):
        with self.connection() as conn:
            row = conn.execute('SELECT payload_json,updated_at FROM postmatch_request_cache '
                               'WHERE cache_key=? AND identity=? AND expires_at>?', (key, ident, now)).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row[0])
            if not isinstance(payload,dict):
                raise ValueError('INVALID_CACHE')
            return {'payload':payload,'observed_at':row['updated_at']}
        except (ValueError,TypeError):
            raise sqlite3.DatabaseError('POSTMATCH_CACHE_CORRUPT') from None

    def cache_request(self, key, job, payload, now):
        from engines.match_record_archive import _clean_json
        fields = {'events','eventstats','tvhighlights','eventshighlights','highlights','lineup','timeline','response'}
        safe = _clean_json({name:value for name,value in payload.items() if name in fields})
        raw = json.dumps(safe, ensure_ascii=False, separators=(',', ':'),allow_nan=False)
        # A bounded operational cache, not a second unbounded raw data archive.
        if len(raw.encode()) > 128 * 1024:
            return
        with self.connection(True) as conn:
            self.check_lease(conn, job, now)
            conn.execute('INSERT OR REPLACE INTO postmatch_request_cache VALUES(?,?,?,?,?)',
                         (key, job['identity'], raw, now + 21600, now))
            conn.execute('DELETE FROM postmatch_request_cache WHERE cache_key NOT IN '
                         '(SELECT cache_key FROM postmatch_request_cache ORDER BY updated_at DESC LIMIT 32)')

    def check_lease(self, conn, job, now):
        row = conn.execute("SELECT * FROM postmatch_jobs WHERE id=? AND state='RUNNING' "
                           "AND lease_token=? AND lease_until>?", (job['id'], job['lease_token'], now)).fetchone()
        if not row:
            raise StaleLease('LEASE_LOST')
        config = conn.execute('SELECT payload FROM postmatch_settings WHERE id=1').fetchone()
        if not config or not json.loads(config[0]).get('enabled'):
            raise StaleLease('PAUSED')
        return dict(row)

    def reserve(self, source: str, job: dict, now: float, limit: int):
        """Count attempts BEFORE provider I/O; crashes do not refund spent requests."""
        if source not in SOURCES:
            raise BudgetStopped('SOURCE_NOT_ALLOWED')
        day = datetime.fromtimestamp(now, ZoneInfo('Europe/Madrid')).date().isoformat()
        with self.connection(True) as conn:
            self.check_lease(conn, job, now)
            config = json.loads(conn.execute('SELECT payload FROM postmatch_settings WHERE id=1').fetchone()[0])
            if source not in config.get('sources', []):
                raise BudgetStopped('SOURCE_NOT_ALLOWED')
            circuit = conn.execute('SELECT blocked_until FROM postmatch_circuits WHERE source=?', (source,)).fetchone()
            if circuit and circuit[0] > now:
                raise BudgetStopped('SOURCE_COOLDOWN')
            conn.execute('INSERT OR IGNORE INTO postmatch_source_budget VALUES(?,?,0)', (source, day))
            used = conn.execute('SELECT COALESCE(SUM(used),0) FROM postmatch_source_budget WHERE day=?', (day,)).fetchone()[0]
            if used >= min(int(limit), int(config['daily_limit']), 60):
                raise BudgetStopped('DAILY_BUDGET')
            conn.execute('UPDATE postmatch_source_budget SET used=used+1 WHERE source=? AND day=?', (source, day))

    def circuit(self, source, failed: bool, reason: str, now: float):
        # Only closed labels, never raw provider response/URL/key.
        if reason not in {'ACCESS_DENIED', 'RATE_LIMIT', 'NETWORK', 'MALFORMED', ''}:
            reason = 'NETWORK'
        with self.connection(True) as conn:
            conn.execute('INSERT OR IGNORE INTO postmatch_circuits(source) VALUES(?)', (source,))
            row = conn.execute('SELECT failures FROM postmatch_circuits WHERE source=?', (source,)).fetchone()
            failures = row[0] + 1 if failed else 0
            delay = 86400 if reason == 'ACCESS_DENIED' else 3600 if reason == 'RATE_LIMIT' else 300 if failures >= 3 else 0
            conn.execute('UPDATE postmatch_circuits SET failures=?,blocked_until=?,reason=? WHERE source=?',
                         (failures, now + delay if delay else 0, reason, source))

    def match(self, mid):
        with self.connection() as conn:
            row = conn.execute('SELECT * FROM matches WHERE id=?', (str(mid),)).fetchone()
            return dict(row) if row else None

    def requeue(self, jid, actor):
        now = time.time()
        with self.connection(True) as conn:
            row = conn.execute('SELECT * FROM postmatch_jobs WHERE id=?', (int(jid),)).fetchone()
            if not row or (row['state'] == 'RUNNING' and row['lease_until'] > now):
                raise ValueError('La tarea no existe o sigue ejecutándose.')
            conn.execute("UPDATE postmatch_jobs SET state='PENDING',attempts=0,due_at=?,updated_at=?,"
                         "lease_token=NULL,lease_until=0,reason='' WHERE id=?", (now, now, jid))
            self.audit(conn, jid, 'MANUAL_RETRY', {}, actor, now)

    def snapshot(self):
        payload = {'contract': CONTRACT, 'state': 'NOT_INITIALIZED', 'config': self.config(),
                   'jobs': [], 'counts': {}, 'budget': [], 'circuits': [], 'observations': []}
        try:
            with self.connection() as conn:
                payload['jobs'] = [dict(row) for row in conn.execute(
                    'SELECT id,match_id,kind,state,attempts,due_at,lease_until,reason,updated_at '
                    'FROM postmatch_jobs ORDER BY updated_at DESC,id DESC LIMIT 100')]
                payload['counts'] = {row[0]: row[1] for row in conn.execute('SELECT state,COUNT(*) FROM postmatch_jobs GROUP BY state')}
                payload['kinds'] = [dict(row) for row in conn.execute('SELECT kind,state,COUNT(*) AS total '
                                       'FROM postmatch_jobs GROUP BY kind,state')]
                try:
                    row = conn.execute('SELECT row_cursor,updated_at FROM postmatch_inventory_cursor WHERE id=1').fetchone()
                    payload['inventory_cursor'] = dict(row) if row else None
                    from engines.postmatch_archive import health
                    payload['archive'] = health(conn)
                except sqlite3.OperationalError as exc:
                    if 'no such table' not in str(exc):
                        raise
                day = datetime.now(ZoneInfo('Europe/Madrid')).date().isoformat()
                payload['budget'] = [dict(row) for row in conn.execute('SELECT source,day,used FROM postmatch_source_budget WHERE day=?', (day,))]
                payload['circuits'] = [dict(row) for row in conn.execute('SELECT * FROM postmatch_circuits')]
                payload['observations'] = [dict(row) for row in conn.execute(
                    'SELECT id,match_id,identity,source,reference,scope,observed_at,values_json FROM postmatch_observations ORDER BY id DESC LIMIT 25')]
                from engines.postmatch_recovery import selection_revision, selected_values
                for observation in payload['observations']:
                    observation['items'] = json.loads(observation.pop('values_json'))
                    selection = selected_values(conn, observation['match_id'], observation['identity'])
                    observation['selection_revision'] = selection_revision(selection)
                    observation['current_items'] = list(selection.values())
                payload['state'] = 'ACTIVE' if payload['config']['enabled'] else 'PAUSED'
        except sqlite3.OperationalError as exc:
            payload['state'] = 'NOT_INITIALIZED' if 'no such table' in str(exc) else 'READ_UNAVAILABLE'
        except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
            payload.update(state='READ_UNAVAILABLE', jobs=[], observations=[])
        # Never expose lease tokens, filesystem paths, actor IDs or raw payloads to the endpoint.
        for job in payload['jobs']:
            job['due_at_madrid'] = datetime.fromtimestamp(job['due_at'], ZoneInfo('Europe/Madrid')).isoformat(timespec='seconds')
        return payload
