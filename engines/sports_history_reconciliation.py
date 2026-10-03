"""Explicit, audited identity reconciliation. No fuzzy matching or network.

Original entities, match rows and detail rows remain stored. Redirects remove
duplicates from derived counts while preserving old URLs and provider IDs.
"""
import json
from itertools import groupby

from engines.sports_history_engine import FINAL, encode, entity, key, now


def has_redirects(conn):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sports_history_redirects'").fetchone())


def resolve(conn, identifier):
    if not has_redirects(conn):
        return identifier
    seen = set()
    while identifier not in seen:
        seen.add(identifier)
        row = conn.execute("SELECT target_id FROM sports_history_redirects WHERE source_id=?", (identifier,)).fetchone()
        if not row:
            return identifier
        identifier = row[0]
    raise ValueError('Cyclic sports identity redirect')


def active_filter(conn, column='id'):
    return f"{column} NOT IN (SELECT source_id FROM sports_history_redirects WHERE kind='match')" if has_redirects(conn) else '1=1'


def _snapshot(conn, old, kind):
    entity_row = conn.execute('SELECT kind,facts,updated_at FROM sports_history_entities WHERE id=?', (old,)).fetchone()
    identities = conn.execute('SELECT kind,source,external_id,canonical_id FROM sports_history_ids WHERE canonical_id=?', (old,)).fetchall()
    selector = 'home=? OR away=?' if kind == 'team' else 'competition=?' if kind == 'competition' else 'id=?'
    params = (old,old) if kind == 'team' else (old,)
    cursor = conn.execute('SELECT * FROM sports_history_matches WHERE ' + selector, params)
    columns = [column[0] for column in cursor.description]
    return dict(entity=list(entity_row), ids=[list(row) for row in identities], matches=[dict(zip(columns,row)) for row in cursor])


def _deduplicate_matches(conn, kind, target_id):
    selector = '(home=? OR away=?)' if kind == 'team' else 'competition=?'
    params = (target_id,target_id) if kind == 'team' else (target_id,)
    cursor = conn.execute('SELECT * FROM sports_history_matches WHERE ' + active_filter(conn) + ' AND ' + selector + ' ORDER BY competition,season,home,away,kickoff,id', params)
    columns = [column[0] for column in cursor.description]
    rows = [dict(zip(columns,row)) for row in cursor]
    merged = []
    for fingerprint, group in groupby(rows, lambda row: tuple(row[field] for field in ('competition','season','home','away','kickoff'))):
        candidates = list(group)
        if len(candidates) < 2 or not fingerprint[1] or 'T' not in fingerprint[4] or not fingerprint[4].endswith('+00:00'):
            continue
        sources = []
        for match in candidates:
            sources.append({row[0] for row in conn.execute("SELECT source FROM sports_history_ids WHERE kind='match' AND canonical_id=? AND source<>'nemesis_internal'", (match['id'],))})
        if any(sources[i] & sources[j] for i in range(len(sources)) for j in range(i)):
            raise ValueError('Different match IDs from the same provider require match-level review')
        finals = {(row['home_score'],row['away_score']) for row in candidates if row['status'] in FINAL and row['home_score'] is not None and row['away_score'] is not None}
        if len(finals) > 1:
            raise ValueError('Conflicting final scores require review')
        ordered = sorted(candidates, key=lambda row: (0 if row['status'] in FINAL and row['home_score'] is not None and row['away_score'] is not None else 1, 0 if row['internal_id'] else 1, row['id']))
        target = ordered[0]
        for old in ordered[1:]:
            conn.execute('INSERT INTO sports_history_redirects VALUES(?,?,?,?)', (old['id'],target['id'],'match',now()))
            conn.execute("UPDATE sports_history_ids SET canonical_id=? WHERE kind='match' AND canonical_id=?", (target['id'],old['id']))
            # Copy details to the active match, retaining originals at the old ID.
            conn.execute('''INSERT INTO sports_history_details SELECT ?,kind,source,external_id,payload,captured_at FROM sports_history_details WHERE match_id=?
                ON CONFLICT(match_id,kind,source,external_id) DO UPDATE SET payload=excluded.payload,captured_at=excluded.captured_at
                WHERE excluded.captured_at>sports_history_details.captured_at''', (target['id'],old['id']))
            merged.append(dict(source=old['id'], target=target['id'], original=old))
    return merged


def reconcile_identity(conn, kind, source, external_id, target_id, evidence):
    """Apply a reviewed link atomically; caller owns commit/rollback.

    Evidence is an operator-supplied reference, never an inferred name match.
    The source entity may already exist; conflicts roll back the entire link.
    """
    from engines.sports_history_engine import provider_name
    if kind not in {'team','competition','player','stadium','referee'}:
        raise ValueError('Unsupported reconciliation entity type')
    if not isinstance(evidence,str) or len(evidence.strip()) < 8:
        raise ValueError('A reviewed evidence reference is required')
    source = provider_name(source)
    if not str(external_id or '').strip():
        raise ValueError('A provider ID is required')
    target_id = resolve(conn,target_id)
    target = conn.execute('SELECT kind,facts FROM sports_history_entities WHERE id=?', (target_id,)).fetchone()
    if not target or target[0] != kind:
        raise ValueError('Target identity type mismatch')
    existing = conn.execute('SELECT canonical_id FROM sports_history_ids WHERE kind=? AND source=? AND external_id=?', (kind,source,str(external_id))).fetchone()
    old = resolve(conn,existing[0]) if existing else None
    if old == target_id:
        return dict(status='already_linked', merged_matches=0)
    conn.execute('SAVEPOINT sports_identity_reconciliation')
    try:
        snapshot = _snapshot(conn,old,kind) if old else {}
        if old:
            if kind == 'team' and conn.execute('SELECT 1 FROM sports_history_matches WHERE (home=? AND away=?) OR (home=? AND away=?)', (old,target_id,target_id,old)).fetchone():
                raise ValueError('Opponent teams cannot share identity')
            conn.execute('UPDATE sports_history_ids SET canonical_id=? WHERE canonical_id=?', (target_id,old))
            facts = json.loads(target[1])
            for field,value in json.loads(snapshot['entity'][1]).items():
                if facts.get(field) in (None,'') and value is not None and value != '':
                    facts[field] = value
            conn.execute('UPDATE sports_history_entities SET facts=?,updated_at=? WHERE id=?', (encode(facts),now(),target_id))
            conn.execute('INSERT INTO sports_history_redirects VALUES(?,?,?,?)', (old,target_id,kind,now()))
            if kind == 'team':
                conn.execute('UPDATE sports_history_matches SET home=? WHERE home=?', (target_id,old))
                conn.execute('UPDATE sports_history_matches SET away=? WHERE away=?', (target_id,old))
            elif kind == 'competition':
                conn.execute('UPDATE sports_history_matches SET competition=? WHERE competition=?', (target_id,old))
            if kind in {'team','competition'}:
                field = 'team' if kind == 'team' else 'competition'
                for row in conn.execute('SELECT team,competition,season,expected,source FROM sports_history_coverage WHERE ' + field + '=?', (old,)).fetchall():
                    team,comp,season,expected,coverage_source = row
                    team = target_id if kind == 'team' else team
                    comp = target_id if kind == 'competition' else comp
                    conn.execute('''INSERT INTO sports_history_coverage VALUES(?,?,?,?,0,?,?)
                        ON CONFLICT(team,competition,season) DO UPDATE SET verified_complete=0,
                        expected=CASE WHEN sports_history_coverage.expected=excluded.expected THEN excluded.expected ELSE NULL END,
                        source=excluded.source,updated_at=excluded.updated_at''', (team,comp,season,expected,coverage_source,now()))
                # A merge changes the population; previous completeness must be rechecked.
                conn.execute('UPDATE sports_history_coverage SET verified_complete=0 WHERE ' + field + '=?', (target_id,))
        else:
            entity(conn,kind,source,str(external_id),canonical_id=target_id)
        matches = _deduplicate_matches(conn,kind,target_id) if kind in {'team','competition'} else []
        audit_id = key(kind,source,str(external_id),target_id,now())
        conn.execute('INSERT INTO sports_history_identity_audit VALUES(?,?,?,?,?,?,?,?,?)', (audit_id,kind,source,str(external_id),old,target_id,evidence.strip(),encode(dict(before=snapshot,merged_matches=matches)),now()))
        conn.execute('RELEASE SAVEPOINT sports_identity_reconciliation')
        return dict(status='linked', merged_matches=len(matches), audit_id=audit_id)
    except Exception:
        conn.execute('ROLLBACK TO SAVEPOINT sports_identity_reconciliation')
        conn.execute('RELEASE SAVEPOINT sports_identity_reconciliation')
        raise
