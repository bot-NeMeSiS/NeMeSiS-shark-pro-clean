"""Read-only persisted media views; configuration is not availability or playback.

Ingestion owns schema creation. A missing/unreadable catalogue has unknown counts,
not zero. Rights use the existing classifier. No HTTP, migration or commit occurs.
"""
from contextlib import closing, contextmanager
import os
from pathlib import Path
import sqlite3

SUMMARY_LIMIT = 250
MATCH_LIMIT = 8


class _Unavailable(Exception):
    def __init__(self, state):
        self.state = state


def _configured():
    return bool((os.getenv('THESPORTSDB_KEY') or os.getenv('THESPORTSDB_API_KEY') or '').strip())


def _table(conn, name):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


@contextmanager
def _reader(db_path):
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise _Unavailable('NO_DATABASE')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.3)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        if not _table(conn, 'sportsdb_match_highlights'):
            raise _Unavailable('CATALOGUE_NOT_INITIALIZED')
        yield conn


def _rows(conn, sql, params=()):
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _classified(items):
    # Lazy import avoids a cycle with the legacy public entry points.
    from engines.sportsdb_highlights_engine import classify_stored_highlight
    classified = [classify_stored_highlight(row) for row in items]
    return classified, [row for row in classified if row.get('show_block')]


def _summary_unavailable(state):
    return {
        'ok': False, 'read_state': state, 'status': state,
        'key_present': _configured(), 'readiness_score': None,
        'playback_verified': False, 'sample_limit': SUMMARY_LIMIT,
        'sampled_media': None, 'sample_truncated': None,
        'visible_counts_scope': 'NOT_ESTABLISHED',
        'highlights_total': None, 'stored_media_total': None, 'with_video': None,
        'stored_with_video': None, 'linked_matches': None, 'stored_linked_matches': None,
        'authorized_highlights': None, 'blocked_highlights': None, 'rights_warnings': None,
        'enriched_matches': None, 'enrichment_available': None, 'runs_available': None,
        'latest_highlights': [], 'recent_runs': [],
        'note': 'Catálogo no verificable en esta lectura. No equivale a cero vídeos ni confirma su disponibilidad.',
    }


def read_highlights_summary(db_path):
    try:
        with _reader(db_path) as conn:
            counts = conn.execute('''SELECT COUNT(*) AS total,
                SUM(CASE WHEN COALESCE(match_id,'')<>'' THEN 1 ELSE 0 END) AS linked,
                SUM(CASE WHEN COALESCE(video_url,'')<>'' THEN 1 ELSE 0 END) AS with_url
                FROM sportsdb_match_highlights''').fetchone()
            total = counts['total']
            stored = _rows(conn, 'SELECT * FROM sportsdb_match_highlights ORDER BY updated_at DESC,id LIMIT ?', (SUMMARY_LIMIT,))
            enrichment_available = _table(conn, 'sportsdb_match_enrichment')
            enriched = conn.execute('SELECT COUNT(*) FROM sportsdb_match_enrichment').fetchone()[0] if enrichment_available else None
            runs_available = _table(conn, 'sportsdb_highlight_runs')
            runs = _rows(conn, '''SELECT started_at,finished_at,status,highlights_found,linked_matches,errors
                FROM sportsdb_highlight_runs ORDER BY started_at DESC LIMIT 6''') if runs_available else []
            for run in runs:
                if run.get('errors'):
                    run['errors'] = 'Error de sincronización registrado; revisar estado desde administración.'
        classified, visible = _classified(stored)
        warnings = sum(row.get('decision') in {'REVIEW_REQUIRED', 'BLOCKED'} for row in classified)
        linked_visible = len({str(row['match_id']) for row in visible if row.get('match_id') is not None and str(row['match_id']).strip()})
        state = 'AUTHORIZED_METADATA_RECORDED' if visible else 'REVIEW_REQUIRED' if total else 'NO_LINKS_RECORDED'
        return {
            'ok': True, 'read_state': 'VERIFIED', 'status': state, 'key_present': _configured(),
            'readiness_score': None, 'playback_verified': False,
            'sample_limit': SUMMARY_LIMIT, 'sampled_media': len(stored),
            'sample_truncated': total > len(stored), 'visible_counts_scope': 'LAST_250_STORED_ROWS',
            'highlights_total': len(visible), 'stored_media_total': total, 'with_video': len(visible),
            'stored_with_video': counts['with_url'] or 0, 'linked_matches': linked_visible,
            'stored_linked_matches': counts['linked'] or 0,
            'authorized_highlights': len(visible), 'blocked_highlights': warnings, 'rights_warnings': warnings,
            'enriched_matches': enriched, 'enrichment_available': enrichment_available,
            'runs_available': runs_available, 'latest_highlights': visible[:8], 'recent_runs': runs,
            'note': 'Los totales guardados corresponden al catálogo; autorización y enlaces se evalúan en los últimos 250 registros. Una autorización registrada no verifica la reproducción externa.',
        }
    except _Unavailable as exc:
        return _summary_unavailable(exc.state)
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
        return _summary_unavailable('READ_UNAVAILABLE')


def _match_unavailable(state):
    return {'ok': False, 'read_state': state, 'highlights': [], 'all_highlights': [],
            'rights_warnings': None, 'enrichment': {}, 'enrichment_available': None,
            'summary_text': '', 'sample_limit': MATCH_LIMIT, 'playback_verified': False}


def read_highlights_for_match(db_path, match_id):
    local_id = str(match_id).strip() if match_id is not None else ''
    if not local_id:
        return _match_unavailable('MATCH_ID_MISSING')
    try:
        with _reader(db_path) as conn:
            stored = _rows(conn, 'SELECT * FROM sportsdb_match_highlights WHERE match_id=? ORDER BY updated_at DESC,id LIMIT ?', (local_id, MATCH_LIMIT))
            enrichment_available = _table(conn, 'sportsdb_match_enrichment')
            enrichments = _rows(conn, 'SELECT * FROM sportsdb_match_enrichment WHERE match_id=? LIMIT 1', (local_id,)) if enrichment_available else []
        classified, visible = _classified(stored)
        enrich = enrichments[0] if enrichments else {}
        return {
            'ok': True, 'read_state': 'VERIFIED', 'highlights': visible, 'all_highlights': classified,
            'rights_warnings': sum(row.get('decision') in {'REVIEW_REQUIRED', 'BLOCKED'} for row in classified),
            'enrichment': enrich, 'enrichment_available': enrichment_available,
            'summary_text': enrich.get('summary_text') or '', 'sample_limit': MATCH_LIMIT,
            'playback_verified': False,
        }
    except _Unavailable as exc:
        return _match_unavailable(exc.state)
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
        return _match_unavailable('READ_UNAVAILABLE')


def read_highlights_readiness(db_path):
    """Admin diagnostic; excludes row payloads/URLs, filesystem paths and API keys.

    Filesystem bytes are a point-in-time observation, not a capacity certificate.
    Zero authorized rows in a bounded sample does not prove zero in all history.
    """
    from datetime import datetime, timezone
    import shutil
    snapshot = read_highlights_summary(db_path)
    storage = {'state': 'NOT_OBSERVED', 'database_bytes': None,
               'wal_bytes': None, 'filesystem_free_bytes': None}
    try:
        path = Path(db_path).expanduser().resolve()
        if path.is_file():
            wal = Path(str(path) + '-wal')
            storage = {'state': 'OBSERVED', 'database_bytes': path.stat().st_size,
                       'wal_bytes': wal.stat().st_size if wal.is_file() else 0,
                       'filesystem_free_bytes': shutil.disk_usage(path.parent).free}
    except (OSError, TypeError, ValueError):
        storage = {'state': 'READ_UNAVAILABLE', 'database_bytes': None,
                   'wal_bytes': None, 'filesystem_free_bytes': None}
    keys = ('stored_media_total','stored_with_video','stored_linked_matches',
            'authorized_highlights','blocked_highlights','enriched_matches',
            'sample_limit','sampled_media','sample_truncated','visible_counts_scope')
    return {
        'contract': 'NEMESIS-HIGHLIGHTS-READ-DIAGNOSTIC-V1',
        'ok': snapshot['ok'], 'read_state': snapshot['read_state'],
        'catalogue_status': snapshot['status'],
        'metadata': {key: snapshot.get(key) for key in keys},
        'storage': storage, 'observed_at': datetime.now(timezone.utc).isoformat(),
        'playback_verified': False, 'production_activation_certified': False,
        'external_calls': 0,
        'remaining_checks': ['Revisar asociación y evidencia de uso del enlace concreto.',
                             'Comprobar su apertura real desde el partido correcto.',
                             'Evaluar capacidad y margen de crecimiento; los bytes no bastan.'],
    }
