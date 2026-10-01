"""Two real post-match workers: recover metadata, validate, persist, expose read-only.

Never changes match scores, bets, memberships or published predictions. Provider
failures are isolated and publication rights are never inferred from a URL.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time

from engines.postmatch_store import Store, StaleLease, identity, is_final, RETRY_DELAYS, stamp
from engines.postmatch_sources import OfficialSources, REQUIRED, STAT_NAMES, norm, final_scope, SourceError

REASONS = {'NO_VIDEO','NO_EVENT','NO_STATISTICS','PARTIAL_COVERAGE','RIGHTS_REVIEW',
           'COMPLETE','CONFLICT','IDENTITY_CHANGED','NOT_FINAL','MISSING_KEY','SOURCE_DISABLED',
           'SOURCE_NOT_ALLOWED','SOURCE_COOLDOWN','DAILY_BUDGET','TICK_BUDGET','MISSING_PROVIDER_ID',
           'ACCESS_DENIED','RATE_LIMIT','NETWORK','MALFORMED','REDIRECT_BLOCKED','AMBIGUOUS_MATCH',
           'IDENTITY_MISMATCH','INVALID_STATISTIC','CONFLICTING_STATISTICS','INCONSISTENT_STATISTICS',
           'SOURCE_NOT_FINAL','INTERNAL_ERROR','STORAGE_UNAVAILABLE','NO_APPROVED_SOURCE'}


def closed_reason(reason):
    return str(reason) if str(reason) in REASONS else 'INTERNAL_ERROR'


def selected_values(conn, mid, ident):
    rows = conn.execute('SELECT s.stat_key,o.* FROM postmatch_selected s JOIN postmatch_observations o '
                        'ON o.id=s.observation_id WHERE s.match_id=? AND s.identity=?', (mid, ident)).fetchall()
    result = {}
    for raw in rows:
        row = dict(raw)
        found = next((item for item in json.loads(row['values_json']) if item['key'] == row['stat_key']), None)
        if found:
            result[row['stat_key']] = {**found, 'source': row['source'], 'reference': row['reference'],
                                      'observed_at': row['observed_at'], 'scope': row['scope'], 'observation_id': row['id']}
    return result


def save_statistics(conn, job, observations, now):
    selected = selected_values(conn, job['match_id'], job['identity'])
    locks = {r[0] for r in conn.execute('SELECT stat_key FROM postmatch_manual_locks WHERE match_id=? AND identity=?', (job['match_id'],job['identity']))}
    conflicts = 0
    for observation in observations:
        source, scope = observation['source'], observation['scope']
        serialized = json.dumps(observation['items'], sort_keys=True)
        digest = hashlib.sha256((job['identity'] + source + scope + serialized).encode()).hexdigest()
        conn.execute('INSERT OR IGNORE INTO postmatch_observations'
                     '(match_id,identity,source,reference,scope,values_json,observed_at,digest) VALUES(?,?,?,?,?,?,?,?)',
                     (job['match_id'], job['identity'], source, observation['reference'], scope,
                      serialized, observation['observed_at'], digest))
        oid = conn.execute('SELECT id FROM postmatch_observations WHERE digest=?', (digest,)).fetchone()[0]
        for item in observation['items']:
            old = selected.get(item['key'])
            # Never overwrite a different observation automatically. Missing field != wrong value.
            conflict = old and (old['scope'] != scope or any(
                old.get(side) is not None and item.get(side) is not None and old[side] != item[side]
                for side in ('home', 'away')))
            if conflict:
                conflicts += 1
                Store.audit(conn, job['id'], 'STAT_CONFLICT', {'observation_id': oid, 'key': item['key'],
                            'previous_observation_id': old['observation_id']}, 'worker', now)
                continue
            # Replacing a single-sided record is only safe if this same-source snapshot contains
            # its existing side plus the missing side. Never drop evidence or mix definitions.
            extends = old and old['source'] == source and all(
                old.get(side) is None or item.get(side) == old[side] for side in ('home','away')) and any(
                old.get(side) is None and item.get(side) is not None for side in ('home','away'))
            if (not old or extends) and item['key'] not in locks:
                conn.execute('INSERT INTO postmatch_selected VALUES(?,?,?,?) ON CONFLICT(match_id,identity,stat_key) '
                             'DO UPDATE SET observation_id=excluded.observation_id',
                             (job['match_id'],job['identity'],item['key'],oid))
                selected[item['key']] = {**item, 'scope': scope, 'source': source, 'observation_id': oid}
    complete = REQUIRED <= {key for key, value in selected.items() if value.get('home') is not None and value.get('away') is not None}
    return 'CONFLICT' if conflicts else 'COMPLETE' if complete else 'PARTIAL_COVERAGE' if selected else 'NO_STATISTICS'


def finish(store, job, result, now):
    from engines.sportsdb_highlights_engine import _upsert_highlight, classify_stored_highlight
    with store.connection(True) as conn:
        store.check_lease(conn, job, now)
        row = conn.execute('SELECT * FROM matches WHERE id=?', (job['match_id'],)).fetchone()
        current = dict(row) if row else {}
        if not current or identity(current) != job['identity']:
            reason = 'IDENTITY_CHANGED'
        elif not is_final(current, now):
            reason = 'NOT_FINAL'
        elif job['kind'] == 'statistics' and result.get('observations'):
            try:
                expected_scope = final_scope(current.get('status'))
            except SourceError:
                expected_scope = 'REGULATION'
            observations = [o for o in result['observations'] if o['scope'] == expected_scope]
            reason = save_statistics(conn, job, observations, now) if observations else 'CONFLICT'
        elif job['kind'] == 'highlights' and result.get('event'):
            saved = _upsert_highlight(conn, result['event'])
            if not saved or str(saved.get('match_id')) != job['match_id']:
                # Entire transaction rollback avoids storing an ambiguous association.
                raise SourceError('IDENTITY_MISMATCH')
            media = dict(conn.execute('SELECT * FROM sportsdb_match_highlights WHERE id=?', (saved['id'],)).fetchone())
            reason = 'COMPLETE' if classify_stored_highlight(media).get('show_block') else 'RIGHTS_REVIEW'
        else:
            reasons = result.get('reasons') or ['NO_APPROVED_SOURCE']
            reason = closed_reason(reasons[-1])
        if reason == 'COMPLETE':
            state = 'COMPLETE'
        elif reason in {'RIGHTS_REVIEW','CONFLICT','AMBIGUOUS_MATCH','IDENTITY_MISMATCH'}:
            state = 'REVIEW_REQUIRED'
        elif reason in {'IDENTITY_CHANGED','NOT_FINAL'}:
            state = 'CANCELLED'
        elif job['attempts'] >= 5:
            state = 'PARTIAL' if reason == 'PARTIAL_COVERAGE' else 'FAILED'
        else:
            state = 'RETRY'
        delay = RETRY_DELAYS[min(job['attempts'] - 1, len(RETRY_DELAYS) - 1)]
        conn.execute('UPDATE postmatch_jobs SET state=?,reason=?,due_at=?,updated_at=?,lease_token=NULL,lease_until=0 WHERE id=?',
                     (state, reason, now + delay, now, job['id']))
        Store.audit(conn, job['id'], 'FINISH', {'state':state,'reason':reason,'external_calls':int(result.get('external_calls') or 0)}, 'worker', now)
        return {'job_id':job['id'],'kind':job['kind'],'state':state,'reason':reason,'external_calls':int(result.get('external_calls') or 0)}


def reconcile_media_reviews(store, now):
    """A rights decision can complete a waiting task without another provider call."""
    from engines.sportsdb_highlights_engine import classify_stored_highlight
    with store.connection(True) as conn:
        jobs=conn.execute("SELECT * FROM postmatch_jobs WHERE kind='highlights' AND state='REVIEW_REQUIRED' ORDER BY updated_at LIMIT 50").fetchall()
        for job in jobs:
            raw=conn.execute('SELECT * FROM matches WHERE id=?',(job['match_id'],)).fetchone()
            if not raw or identity(dict(raw))!=job['identity'] or not is_final(dict(raw),now):
                continue
            media=conn.execute('SELECT * FROM sportsdb_match_highlights WHERE match_id=? ORDER BY updated_at DESC LIMIT 8',(job['match_id'],)).fetchall()
            if any(classify_stored_highlight(dict(row)).get('show_block') for row in media):
                conn.execute("UPDATE postmatch_jobs SET state='COMPLETE',reason='COMPLETE',updated_at=? WHERE id=?",(now,job['id']))
                Store.audit(conn,job['id'],'RIGHTS_REVIEW_RECONCILED',{},'worker',now)


def tick(db_path, *, dry_run=False, clock=time.time, source_factory=OfficialSources):
    store = Store(db_path)
    config = store.config()
    if config.get('read_state') == 'READ_UNAVAILABLE':
        return {'ok':False, 'result':'STORAGE_UNAVAILABLE', 'processed':0, 'external_calls':0}
    if dry_run:
        return {'ok': True, 'result': 'DRY_RUN', 'status': store.snapshot(), 'external_calls': 0, 'database_writes': 0}
    if not config['enabled']:
        return {'ok': True, 'result': 'SKIPPED_DISABLED', 'external_calls': 0, 'processed': 0}
    began, results = clock(), []
    shared_request_cache = {}
    try:
        # Migration belongs to explicit activation, not to a page read or import.
        store.discover(began)
        reconcile_media_reviews(store, began)
        for _ in range(min(2, config['batch_size'])):
            if clock() >= began + 20:
                break
            job = store.claim(clock())
            if not job:
                break
            outcome, source = {'external_calls':0}, None
            try:
                match = store.match(job['match_id'])
                if not match or identity(match) != job['identity'] or not is_final(match, clock()):
                    outcome = {'reasons':['IDENTITY_CHANGED'], 'external_calls':0}
                else:
                    source = source_factory(store, job, config, deadline=began + 20, clock=clock)
                    if isinstance(source, OfficialSources):
                        source.cache = shared_request_cache
                    outcome = source.highlights(match) if job['kind'] == 'highlights' else source.statistics(match)
                results.append(finish(store, job, outcome, clock()))
            except StaleLease:
                results.append({'job_id':job['id'],'kind':job['kind'],'state':'LEASE_LOST','reason':'PAUSED_OR_RECLAIMED','external_calls':0})
            except Exception as exc:
                # A parser or source crash cannot disappear as a successful empty response.
                reason = closed_reason(exc) if isinstance(exc, SourceError) else 'STORAGE_UNAVAILABLE' if isinstance(exc, sqlite3.Error) else 'INTERNAL_ERROR'
                try:
                    results.append(finish(store, job, {'reasons':[reason], 'external_calls':getattr(source,'calls',outcome.get('external_calls',0))}, clock()))
                except (StaleLease, sqlite3.Error):
                    results.append({'job_id':job['id'],'kind':job['kind'],'state':'FAILED','reason':reason,'external_calls':0})
    except (sqlite3.Error, OSError, ValueError):
        return {'ok':False,'result':'STORAGE_UNAVAILABLE','processed':len(results),'jobs':results}
    completed = all(row['state'] == 'COMPLETE' for row in results)
    return {'ok': True, 'result': 'IDLE' if not results else 'COMPLETE' if completed else 'PARTIAL',
            'processed':len(results),'external_calls':sum(r['external_calls'] for r in results),'jobs':results}


def read_for_match(db_path, match):
    output = {'state':'NOT_INITIALIZED','items':[],'jobs':[], 'recovered_at':None}
    if not match or not match.get('id'):
        return output
    store = Store(db_path)
    try:
        with store.connection() as conn:
            raw = conn.execute('SELECT * FROM matches WHERE id=?', (str(match['id']),)).fetchone()
            if not raw:
                return output
            canonical = dict(raw)
            # Display decorators translate competition names. Bind observations to the
            # current persisted identity, not to presentation-only labels.
            if any(norm(canonical.get(key)) != norm(match.get(key)) for key in ('home_team','away_team','match_date')):
                return {**output, 'state':'IDENTITY_CHANGED'}
            ident = identity(canonical)
            values = selected_values(conn, str(match['id']), ident)
            output['jobs'] = [dict(row) for row in conn.execute('SELECT kind,state,reason,due_at FROM postmatch_jobs WHERE match_id=? AND identity=?',
                               (str(match['id']), ident))]
        # Even old stored observations must not leak into a postponed/remapped/live match.
        output['items'] = list(values.values()) if is_final(canonical) and is_final(match) else []
        output['state'] = 'RECOVERED' if output['items'] else 'PENDING'
        output['recovered_at'] = stamp(max(v['observed_at'] for v in output['items'])) if output['items'] else None
    except sqlite3.OperationalError as exc:
        output['state'] = 'NOT_INITIALIZED' if 'no such table' in str(exc) else 'READ_UNAVAILABLE'
    except (sqlite3.Error, OSError, ValueError):
        output['state'] = 'READ_UNAVAILABLE'
    return output


def attach_detail(db_path, detail):
    """Read-only presentation enrichment; never changes original statistics or prediction history."""
    match = detail.get('match') or {}
    recovery = read_for_match(db_path, match)
    detail['postmatch_recovery'] = recovery
    if not recovery['items']:
        return detail
    cached = dict(detail.get('cached_statistics') or {})
    current = list(cached.get('items') or [])
    aliases = {norm(name): spec[0] for name, spec in STAT_NAMES.items()}
    aliases.update({norm(spec[1]):spec[0] for spec in STAT_NAMES.values()})
    aliases.update({norm(spec[0]):spec[0] for spec in STAT_NAMES.values()})
    keys = {aliases.get(norm(row.get('label'))) or aliases.get(norm(row.get('key'))) for row in current}
    extras = [row for row in recovery['items'] if row['key'] not in keys]
    if extras:
        cached.update(available=True, items=current + extras, postmatch_recovered=True,
                      source=cached.get('source') or 'Recuperación pospartido',
                      updated_at=cached.get('updated_at') or recovery['recovered_at'], external_calls=0)
        detail['cached_statistics'] = cached
    return detail




def selection_revision(selection):
    return hashlib.sha256(json.dumps({key:value['observation_id'] for key,value in selection.items()}, sort_keys=True).encode()).hexdigest()


def select_observation(db_path, oid, *, actor, expected_identity, expected_revision):
    """An explicit choice binds to both the match and the currently selected facts.

    The audit preserves the previous selection. A repeated/stale form cannot
    overwrite another administrator's decision. Manual selections are locked.
    """
    store, now = Store(db_path), time.time()
    if not actor:
        raise ValueError('Falta la identidad del revisor.')
    with store.connection(True) as conn:
        row = conn.execute('SELECT * FROM postmatch_observations WHERE id=?', (int(oid),)).fetchone()
        if not row:
            raise ValueError('La observación ya no está disponible.')
        match = conn.execute('SELECT * FROM matches WHERE id=?', (row['match_id'],)).fetchone()
        if not match or identity(dict(match)) != row['identity'] or expected_identity != row['identity'] or not is_final(dict(match), now):
            raise ValueError('El partido ha cambiado. Recarga antes de decidir.')
        try:
            scope = final_scope(dict(match).get('status'))
        except SourceError:
            scope = 'REGULATION'
        if row['scope'] != scope:
            raise ValueError('La observación no corresponde al periodo del partido.')
        before = selected_values(conn, row['match_id'], row['identity'])
        if selection_revision(before) != expected_revision:
            raise ValueError('La selección ha cambiado. Recarga antes de decidir.')
        items = json.loads(row['values_json'])
        for item in items:
            conn.execute('INSERT INTO postmatch_selected VALUES(?,?,?,?) ON CONFLICT(match_id,identity,stat_key) '
                         'DO UPDATE SET observation_id=excluded.observation_id', (row['match_id'],row['identity'],item['key'],row['id']))
            conn.execute('INSERT OR IGNORE INTO postmatch_manual_locks VALUES(?,?,?)', (row['match_id'],row['identity'],item['key']))
        Store.audit(conn, None, 'ADMIN_SELECT_STATISTICS', {'observation_id':row['id'], 'previous':before}, actor, now)
        complete = REQUIRED <= {key for key,value in selected_values(conn,row['match_id'],row['identity']).items() if value.get('home') is not None and value.get('away') is not None}
        conn.execute("UPDATE postmatch_jobs SET state=?,reason='MANUAL_REVIEW',updated_at=? WHERE match_id=? AND identity=? AND kind='statistics' AND state='REVIEW_REQUIRED'",
                     ('COMPLETE' if complete else 'PARTIAL', now, row['match_id'],row['identity']))
        return {'ok':True, 'observation_id':row['id']}
