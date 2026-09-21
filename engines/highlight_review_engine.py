"""Explicit, audited media review. Reads are read-only; writes require admin/CSRF at the route."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from engines.highlight_url_engine import public_https_url, safe_embed_url, review_fingerprint
from engines.sportsdb_highlights_engine import classify_stored_highlight, ensure_sportsdb_highlights_schema


class ReviewError(ValueError):
    pass


def review_snapshot(db_path, limit=40):
    result = {'state': 'NOT_SYNCED', 'items': [], 'runs': [], 'counts': {}, 'sample_limit': limit}
    path = Path(db_path).resolve()
    if not path.is_file():
        return result
    try:
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA query_only=ON')
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='sportsdb_match_highlights'").fetchone()
            if not exists:
                return result
            result['counts']['stored'] = conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0]
            records = conn.execute('SELECT * FROM sportsdb_match_highlights ORDER BY updated_at DESC, id LIMIT ?', (max(1, min(int(limit), 100)),)).fetchall()
            for record in records:
                raw = dict(record)
                item = classify_stored_highlight(raw)
                result['items'].append({
                    'id': raw['id'], 'title': raw.get('title') or 'Resumen del partido',
                    'match_id': raw.get('match_id') or '', 'event_date': raw.get('event_date') or '',
                    'source': raw.get('source') or 'Sin fuente', 'decision': item['decision'],
                    'reason': item['reason'], 'video_url': public_https_url(raw.get('video_url')),
                    'review_token': review_fingerprint(raw), 'attribution': raw.get('attribution') or '',
                    'rights_status': raw.get('rights_status') or 'UNKNOWN_RIGHTS',
                    'can_display': bool(item.get('show_block')),
                })
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='sportsdb_highlight_runs'").fetchone():
                # Do not render historical errors: legacy versions could store a provider URL/key.
                for row in conn.execute('SELECT started_at,finished_at,status,highlights_found,linked_matches FROM sportsdb_highlight_runs ORDER BY started_at DESC LIMIT 3'):
                    result['runs'].append(dict(row))
            result['state'] = 'RECORDED' if result['counts']['stored'] else 'NO_LINKS_RECORDED'
    except (sqlite3.Error, OSError, ValueError):
        result['state'] = 'READ_UNAVAILABLE'
        result['items'] = []
    return result


def decide_highlight(db_path, highlight_id, values, *, actor):
    action = str(values.get('decision') or '')
    if action not in {'LINK_ONLY', 'EMBED', 'BLOCKED', 'REVIEW_REQUIRED'}:
        raise ReviewError('Decisión no válida.')
    if not actor:
        raise ReviewError('Falta la identidad de revisión.')
    evidence = public_https_url(values.get('evidence_url'))
    attribution = str(values.get('attribution') or '').strip()[:500]
    basis = str(values.get('basis') or '').strip()[:1500]
    rights = str(values.get('rights_status') or '').upper()
    approval = action in {'LINK_ONLY', 'EMBED'}
    if approval and (not evidence or not attribution or not basis or values.get('confirmed') != '1'):
        raise ReviewError('La autorización exige evidencia, atribución, fundamento y confirmación expresa de uso comercial en la app.')
    if approval and rights not in {'OWNED', 'LICENSED', 'PROVIDER_ALLOWED', 'OPEN_LICENSE_ALLOWED', 'ATTRIBUTION_REQUIRED'}:
        raise ReviewError('Selecciona la base de derechos verificada.')
    ensure_sportsdb_highlights_schema(db_path)
    with closing(sqlite3.connect(db_path, timeout=3)) as conn:
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM sportsdb_match_highlights WHERE id=?', (highlight_id,)).fetchone()
            if row is None:
                raise ReviewError('El enlace ya no existe.')
            raw = dict(row)
            if review_fingerprint(raw) != str(values.get('review_token') or ''):
                raise ReviewError('El enlace o su revisión han cambiado. Recarga antes de decidir.')
            if approval and not public_https_url(raw.get('video_url')):
                raise ReviewError('La URL no es un enlace HTTPS válido.')
            if approval and not raw.get('match_id'):
                raise ReviewError('Falta una asociación inequívoca con el partido; no se puede publicar.')
            if approval:
                if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='matches'").fetchone() or not conn.execute('SELECT 1 FROM matches WHERE id=?', (raw['match_id'],)).fetchone():
                    raise ReviewError('El partido asociado ya no existe; revisa la asociación.')
            embed = safe_embed_url(raw.get('video_url')) if action == 'EMBED' else ''
            if action == 'EMBED' and not embed:
                raise ReviewError('Este enlace solo admite apertura externa; no hay reproductor compatible.')
            now = datetime.now(ZoneInfo('Europe/Madrid')).isoformat(timespec='seconds')
            chosen_rights = rights if approval else action
            conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_highlight_reviews(
                id INTEGER PRIMARY KEY AUTOINCREMENT, highlight_id TEXT NOT NULL,
                actor TEXT NOT NULL, decision TEXT NOT NULL, evidence_url TEXT,
                basis TEXT, previous_json TEXT NOT NULL, created_at TEXT NOT NULL)''')
            previous = {key: raw.get(key) for key in ('video_url','embed_url','match_id','rights_status','commercial_use_status','attribution','rights_verified_at','embed_policy','allowed_channels_json')}
            conn.execute('INSERT INTO sportsdb_highlight_reviews(highlight_id,actor,decision,evidence_url,basis,previous_json,created_at) VALUES (?,?,?,?,?,?,?)',
                         (highlight_id, str(actor)[:120], action, evidence, basis, json.dumps(previous, ensure_ascii=False), now))
            conn.execute('''UPDATE sportsdb_match_highlights SET rights_status=?,rights_note=?,
                commercial_use_status=?,attribution=?,attribution_required=1,
                rights_verified_at=?,official_source_verified=?,embed_policy=?,embed_url=?,
                client_status=?,status=?,updated_at=?,allowed_channels_json='["APP"]' WHERE id=?''',
                (chosen_rights, chosen_rights, 'ALLOWED' if approval else 'UNKNOWN', attribution,
                 now, int(approval and values.get('official') == '1'), action, embed,
                 'AUTHORIZED' if approval else action, 'READY' if approval else action, now, highlight_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {'ok': True, 'highlight_id': highlight_id, 'decision': action}
