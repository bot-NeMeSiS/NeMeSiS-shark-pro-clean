"""Evidence-backed reusable highlight policies; association grants no rights.

Only explicit admin writes register policy. Read resolution never creates tables,
calls providers, fetches licences or mutates stored authorizations.
"""
from __future__ import annotations
from datetime import datetime, timezone
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from engines.highlight_url_engine import public_https_url

SCHEMA = '''CREATE TABLE IF NOT EXISTS highlight_rights_policies(
 id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
 scope_kind TEXT NOT NULL, scope_value TEXT NOT NULL,
 channels_json TEXT NOT NULL, modality TEXT NOT NULL,
 evidence_url TEXT NOT NULL, basis TEXT NOT NULL,
 attribution TEXT NOT NULL, commercial_use INTEGER NOT NULL,
 verified_at TEXT NOT NULL, review_at TEXT NOT NULL,
 actor TEXT NOT NULL, revoked_at TEXT NOT NULL DEFAULT '',
 rights_status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS highlight_policy_audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT, policy_id INTEGER NOT NULL,
 action TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);'''


def _date(value):
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('La fecha exige zona horaria.')
    return parsed.astimezone(timezone.utc)


def ensure_schema(conn):
    # Avoid executescript, which would commit the caller's review transaction.
    for statement in SCHEMA.split(';'):
        if statement.strip():
            conn.execute(statement)


def register_policy(conn, values, *, actor, now=None):
    from engines.highlight_review_engine import _generic_api_evidence
    now = now or datetime.now(timezone.utc)
    source = str(values.get('source') or '').strip()
    kind = str(values.get('scope_kind') or '').upper()
    scope = str(values.get('scope_value') or '').strip()
    mode = str(values.get('modality') or '').upper()
    evidence = public_https_url(values.get('evidence_url'))
    basis = str(values.get('basis') or '').strip()
    attribution = str(values.get('attribution') or '').strip()
    channels = values.get('channels')
    rights = str(values.get('rights_status') or '').upper()
    if not actor or not source or len(source) > 120 or kind not in {'VIDEO', 'CHANNEL'} or not scope or len(scope) > 2048:
        raise ValueError('Falta fuente o alcance inequívoco de la política.')
    if kind == 'VIDEO' and public_https_url(scope) != scope:
        raise ValueError('El alcance del vídeo exige su URL HTTPS original.')
    if kind == 'CHANNEL' and not values.get('channel_identity_verified'):
        raise ValueError('Una política de canal exige comprobar su identificador estable y el alcance documental.')
    if mode not in {'EMBED', 'LINK_ONLY', 'BLOCKED'} or channels != ['APP']:
        raise ValueError('Modalidad o canal de publicación no válidos.')
    if not evidence or _generic_api_evidence(evidence) or not basis or not attribution:
        raise ValueError('Falta evidencia específica, alcance o atribución; Premium no acredita copyright.')
    if mode != 'BLOCKED' and (values.get('commercial_use') is not True or rights not in {'OWNED', 'LICENSED', 'PROVIDER_ALLOWED', 'OPEN_LICENSE_ALLOWED', 'ATTRIBUTION_REQUIRED'}):
        raise ValueError('El uso comercial y la base de derechos deben estar acreditados.')
    review_at = _date(values.get('review_at'))
    if review_at <= now:
        raise ValueError('La fecha de expiración/revisión debe ser futura.')
    ensure_schema(conn)
    cursor = conn.execute('''INSERT INTO highlight_rights_policies
        (source,scope_kind,scope_value,channels_json,modality,evidence_url,basis,
         attribution,commercial_use,verified_at,review_at,actor,rights_status)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (source, kind, scope, json.dumps(channels), mode, evidence, basis[:1500],
         attribution[:500], int(values.get('commercial_use') is True), now.isoformat(),
         review_at.isoformat(), str(actor)[:120], rights))
    conn.execute('INSERT INTO highlight_policy_audit(policy_id,action,actor,created_at) VALUES(?,?,?,?)',
                 (cursor.lastrowid, 'REGISTER', str(actor)[:120], now.isoformat()))
    return cursor.lastrowid


def revoke_policy(conn, policy_id, *, actor):
    if not actor:
        raise ValueError('Falta revisor.')
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute("UPDATE highlight_rights_policies SET revoked_at=? WHERE id=? AND revoked_at=''", (now, int(policy_id)))
    if cursor.rowcount != 1:
        raise ValueError('La política no está activa.')
    conn.execute('INSERT INTO highlight_policy_audit(policy_id,action,actor,created_at) VALUES(?,?,?,?)',
                 (int(policy_id), 'REVOKE', str(actor)[:120], now))


def channel_identity(row):
    # Never guess a channel from a platform hostname, title, team or competition.
    try:
        payload = json.loads(row.get('raw_json') or '{}')
    except (ValueError, TypeError):
        return ''
    return str(payload.get('idChannel') or payload.get('channel_id') or '').strip() if isinstance(payload, dict) else ''


def resolve_policy(row, policies, *, channel='APP', now=None):
    now = now or datetime.now(timezone.utc)
    url = public_https_url(row.get('video_url') or row.get('original_url'))
    matched = []
    for policy in policies:
        if policy['source'] != row.get('source'):
            continue
        target = url if policy['scope_kind'] == 'VIDEO' else channel_identity(row)
        if not target or target != policy['scope_value']:
            continue
        if policy['scope_kind'] == 'CHANNEL':
            # Reusable approval is prospective, never a bulk authorization of
            # the 135 previously associated records. Missing creation date fails closed.
            try:
                if _date(row.get('created_at')) <= _date(policy['verified_at']):
                    continue
            except (TypeError, ValueError):
                continue
        matched.append(policy)
    if not matched:
        return None
    # Exact video decisions take precedence over a reusable channel scope.
    exact = [p for p in matched if p['scope_kind'] == 'VIDEO']
    matched = exact or matched
    active = []
    for policy in matched:
        try:
            valid = not policy['revoked_at'] and _date(policy['verified_at']) <= now < _date(policy['review_at'])
            valid = valid and channel in json.loads(policy['channels_json'])
            valid = valid and public_https_url(policy['evidence_url']) and policy['basis'] and policy['attribution']
        except (TypeError, ValueError, KeyError):
            valid = False
        if valid:
            active.append(policy)
    if any(p['modality'] == 'BLOCKED' for p in active):
        return {'decision': 'BLOCKED', 'modality': 'BLOCKED', 'reason': 'La política documentada bloquea esta publicación.'}
    active = [p for p in active if p['commercial_use'] == 1]
    if len(active) != 1:
        return {'decision': 'REVIEW_REQUIRED', 'modality': 'REVIEW_REQUIRED', 'reason': 'Política vencida, revocada, fuera de canal o con alcance ambiguo.'}
    policy = active[0]
    if not row.get('match_id'):
        return {'decision': 'REVIEW_REQUIRED', 'modality': 'REVIEW_REQUIRED', 'reason': 'Falta asociación inequívoca; la política no identifica el partido.'}
    return {'decision': 'APPROVED', 'modality': policy['modality'], 'policy_id': policy['id'],
            'rights_status': policy['rights_status'], 'attribution': policy['attribution'],
            'evidence_url': policy['evidence_url'], 'rights_verified_at': policy['verified_at'],
            'review_at': policy['review_at'], 'reason': 'Uso cubierto por política documental vigente.'}


def attach_policies(conn, rows):
    if not rows or not any('video_url' in row for row in rows):
        return rows
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='highlight_rights_policies'").fetchone():
        return rows
    policies = [dict(row) for row in conn.execute('SELECT * FROM highlight_rights_policies ORDER BY id DESC LIMIT 1001')]
    # Never silently truncate the policy set and potentially miss a block.
    for row in rows:
        row['_rights_policy'] = {'decision': 'REVIEW_REQUIRED', 'modality': 'REVIEW_REQUIRED', 'reason': 'Demasiadas políticas para resolver con seguridad.'} if len(policies) > 1000 else resolve_policy(row, policies)
    return rows


def policy_snapshot(db_path):
    path = Path(db_path).resolve()
    if not path.is_file():
        return {'state': 'NOT_INITIALIZED', 'items': []}
    try:
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=.3)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA query_only=ON')
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='highlight_rights_policies'").fetchone():
                return {'state': 'NOT_INITIALIZED', 'items': []}
            rows = [dict(row) for row in conn.execute('SELECT id,source,scope_kind,scope_value,channels_json,modality,evidence_url,basis,attribution,commercial_use,verified_at,review_at,revoked_at FROM highlight_rights_policies ORDER BY id DESC LIMIT 100')]
            return {'state': 'RECORDED', 'items': rows}
    except (sqlite3.Error, OSError):
        return {'state': 'READ_UNAVAILABLE', 'items': []}
