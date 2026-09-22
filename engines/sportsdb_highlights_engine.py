import hashlib
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import contextmanager

from engines.highlight_url_engine import public_https_url, safe_embed_url

from engines.content_rights_engine import classify_media_asset
from engines.video_highlights_engine import classify_match_video

TZ = ZoneInfo('Europe/Madrid')

RIGHTS_STATES = {
    'OWNED', 'LICENSED', 'PROVIDER_ALLOWED', 'OPEN_LICENSE_ALLOWED',
    'ATTRIBUTION_REQUIRED', 'REVIEW_REQUIRED', 'BLOCKED', 'UNKNOWN_RIGHTS',
}
APPROVED_RIGHTS_STATES = {
    'OWNED', 'LICENSED', 'PROVIDER_ALLOWED', 'OPEN_LICENSE_ALLOWED',
    'ATTRIBUTION_REQUIRED',
}
COMMERCIAL_ALLOWED_STATES = {
    'ALLOWED', 'COMMERCIAL_ALLOWED', 'LICENSED_COMMERCIAL',
    'PROVIDER_TERMS_ALLOWED',
}


def _now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def _today():
    return datetime.now(TZ).date()


@contextmanager
def _connect(db_path):
    conn = sqlite3.connect(db_path, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _rows(conn, sql, args=()):
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _one(conn, sql, args=()):
    row = conn.execute(sql, args).fetchone()
    return dict(row) if row else None


def _table_exists(conn, table):
    return bool(_one(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)))


def _cols(conn, table):
    if not _table_exists(conn, table):
        return set()
    return {r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_sportsdb_highlights_schema(db_path):
    with _connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_match_highlights(
            id TEXT PRIMARY KEY,
            sportsdb_event_id TEXT,
            match_id TEXT,
            event_date TEXT,
            league_id TEXT,
            league_name TEXT,
            home_team TEXT,
            away_team TEXT,
            title TEXT,
            video_url TEXT,
            embed_url TEXT,
            thumbnail_url TEXT,
            source TEXT DEFAULT 'TheSportsDB',
            provider TEXT DEFAULT 'YouTube',
            status TEXT DEFAULT 'REVIEW_REQUIRED',
            client_status TEXT DEFAULT 'REVIEW_REQUIRED',
            rights_status TEXT DEFAULT 'UNKNOWN_RIGHTS',
            commercial_use_status TEXT DEFAULT 'UNKNOWN',
            attribution TEXT DEFAULT '',
            attribution_required INTEGER DEFAULT 0,
            rights_verified_at TEXT DEFAULT '',
            official_source_verified INTEGER DEFAULT 0,
            geo_restriction_status TEXT DEFAULT 'UNKNOWN',
            thumbnail_rights_status TEXT DEFAULT 'UNKNOWN_RIGHTS',
            thumbnail_commercial_use_status TEXT DEFAULT 'UNKNOWN',
            thumbnail_attribution TEXT DEFAULT '',
            rights_note TEXT DEFAULT 'UNKNOWN_RIGHTS',
            raw_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_match_enrichment(
            id TEXT PRIMARY KEY,
            match_id TEXT UNIQUE,
            sportsdb_event_id TEXT,
            event_date TEXT,
            enrichment_status TEXT,
            has_highlight INTEGER DEFAULT 0,
            has_event_detail INTEGER DEFAULT 0,
            highlight_count INTEGER DEFAULT 0,
            summary_text TEXT,
            payload_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_highlight_runs(
            id TEXT PRIMARY KEY,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            days_back INTEGER DEFAULT 3,
            highlights_found INTEGER DEFAULT 0,
            linked_matches INTEGER DEFAULT 0,
            errors TEXT
        )''')
        cols = _cols(conn, 'sportsdb_match_highlights')
        if 'allowed_channels_json' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN allowed_channels_json TEXT DEFAULT ''")
        if 'embed_policy' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN embed_policy TEXT DEFAULT 'LEGACY'")
        if 'embed_url' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN embed_url TEXT DEFAULT ''")
        if 'rights_note' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN rights_note TEXT DEFAULT ''")
        if 'client_status' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN client_status TEXT DEFAULT 'REVIEW_REQUIRED'")
        if 'rights_status' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN rights_status TEXT DEFAULT 'UNKNOWN_RIGHTS'")
        if 'commercial_use_status' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN commercial_use_status TEXT DEFAULT 'UNKNOWN'")
        if 'attribution' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN attribution TEXT DEFAULT ''")
        if 'attribution_required' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN attribution_required INTEGER DEFAULT 0")
        if 'rights_verified_at' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN rights_verified_at TEXT DEFAULT ''")
        if 'official_source_verified' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN official_source_verified INTEGER DEFAULT 0")
        if 'geo_restriction_status' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN geo_restriction_status TEXT DEFAULT 'UNKNOWN'")
        if 'thumbnail_rights_status' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN thumbnail_rights_status TEXT DEFAULT 'UNKNOWN_RIGHTS'")
        if 'thumbnail_commercial_use_status' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN thumbnail_commercial_use_status TEXT DEFAULT 'UNKNOWN'")
        if 'thumbnail_attribution' not in cols:
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN thumbnail_attribution TEXT DEFAULT ''")
        conn.commit()
    return {'ok': True, 'schema': 'sportsdb_highlights'}


def _api_key():
    return (os.getenv('THESPORTSDB_KEY') or os.getenv('THESPORTSDB_API_KEY') or '').strip()


def _fetch_json(url, timeout=6):
    req = urllib.request.Request(url, headers={'User-Agent': 'NeMeSiS-SHARK-PRO/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        payload = res.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError('response_too_large')
        return json.loads(payload.decode('utf-8'))


def _sportsdb_v1(endpoint, params=None):
    key = _api_key()
    if not key:
        return {}
    url = 'https://www.thesportsdb.com/api/v1/json/%s/%s' % (urllib.parse.quote(key), endpoint.lstrip('/'))
    if params:
        url += '?' + urllib.parse.urlencode(params)
    return _fetch_json(url)


def _as_list(payload):
    if not isinstance(payload, dict):
        return []
    for key in ('eventshighlights', 'highlights', 'events', 'tv', 'results'):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    for value in payload.values():
        if isinstance(value, list):
            return value
    return []


def _norm(value):
    return ''.join(ch for ch in str(value or '').lower() if ch.isalnum())


def _event_id(item):
    raw = item.get('idEvent') or item.get('id') or item.get('event_id') or (str(item.get('strEvent') or '') + str(item.get('dateEvent') or ''))
    return str(raw or '')


def _video_url(item):
    return item.get('strVideo') or item.get('strYoutube') or item.get('strURL') or item.get('url') or item.get('video') or ''


def _youtube_embed_url(url):
    """Strict, canonical external player URL; never requests a video."""
    return safe_embed_url(url)


def _thumb(item):
    return item.get('strThumb') or item.get('strPoster') or item.get('thumbnail') or item.get('strFanart') or ''


def _title(item):
    return item.get('strEvent') or item.get('strTitle') or item.get('title') or 'Resumen del partido'


def _home_away(item):
    home = item.get('strHomeTeam') or ''
    away = item.get('strAwayTeam') or ''
    if (not home or not away) and ' vs ' in str(item.get('strEvent') or ''):
        parts = str(item.get('strEvent')).split(' vs ', 1)
        home = home or parts[0].strip()
        away = away or parts[1].strip()
    return home, away


def _rights_status(item):
    raw = str(item.get('rights_status') or item.get('rights_note') or 'UNKNOWN_RIGHTS').strip().upper()
    return raw if raw in RIGHTS_STATES else 'UNKNOWN_RIGHTS'


def classify_stored_highlight(item, *, channel='APP'):
    """Apply the canonical fail-closed rights decision to persisted metadata."""
    row = dict(item or {})
    rights_status = _rights_status(row)
    commercial = str(row.get('commercial_use_status') or 'UNKNOWN').strip().upper()
    geo_status = str(row.get('geo_restriction_status') or 'UNKNOWN').strip().upper()
    original_url = str(row.get('video_url') or row.get('original_url') or '').strip()
    embed_url = str(row.get('embed_url') or '').strip()
    if row.get('embed_policy') in {'LINK_ONLY', 'BLOCKED', 'REVIEW_REQUIRED'} or geo_status in {'BLOCKED', 'RESTRICTED', 'GEO_BLOCKED'}:
        embed_url = ''
    try:
        channels = json.loads(row.get('allowed_channels_json') or '[]')
        if not isinstance(channels, list):
            channels = ['NONE']
    except (ValueError, TypeError):
        channels = ['NONE']
    decision = classify_match_video({
        **row,
        'content_type': 'video',
        'source': row.get('source') or row.get('provider'),
        'original_url': original_url,
        'embed_url': embed_url,
        'thumbnail_url': row.get('thumbnail_url'),
        'rights_status': rights_status,
        'commercial_use_status': commercial,
        'attribution': row.get('attribution'),
        'attribution_required': bool(row.get('attribution_required')),
        'rights_verified_at': row.get('rights_verified_at'),
        'official_source_verified': bool(row.get('official_source_verified')),
        'geo_restriction_status': geo_status,
        'channel': channel,
        'allowed_channels': channels,
    })
    thumbnail = classify_media_asset({
        'content_type': 'thumbnail',
        'source': row.get('source') or row.get('provider'),
        'image_url': row.get('thumbnail_url'),
        'rights_status': row.get('thumbnail_rights_status') or 'UNKNOWN_RIGHTS',
        'commercial_use_status': row.get('thumbnail_commercial_use_status') or 'UNKNOWN',
        'attribution': row.get('thumbnail_attribution') or '',
        'rights_verified_at': row.get('rights_verified_at'),
    }, channel=channel)
    return {
        **row,
        **decision,
        'video_url': public_https_url(original_url),
        'thumbnail_url': thumbnail.get('asset_url') if thumbnail.get('can_display') else '',
        'thumbnail_rights': thumbnail,
        'geo_restriction_status': geo_status,
        'geo_restricted': geo_status in {'BLOCKED', 'RESTRICTED', 'GEO_BLOCKED'},
    }


def _visible_highlights(items):
    classified = [classify_stored_highlight(item) for item in (items or [])]
    return classified, [item for item in classified if item.get('show_block')]


def _find_match(conn, item):
    """No cross-provider numeric IDs, substring matching or arbitrary first match."""
    cols = _cols(conn, 'matches')
    if 'id' not in cols:
        return None
    sid = str(item.get('idEvent') or item.get('event_id') or '').strip()
    if sid and 'external_id' in cols:
        candidates = _rows(conn, 'SELECT * FROM matches WHERE external_id=? OR external_id=?', (sid, 'sportsdb-' + sid))
        qualified = []
        for row in candidates:
            source = _norm(row.get('source') or row.get('provider'))
            if str(row.get('external_id')) == 'sportsdb-' + sid or 'sportsdb' in source:
                qualified.append(row)
        if len(qualified) == 1:
            home, away = _home_away(item)
            row = qualified[0]
            if home and away and (_norm(home), _norm(away)) != (_norm(row.get('home_team')), _norm(row.get('away_team'))):
                return None
            return row['id']
        if qualified:
            return None
    needed = {'home_team', 'away_team', 'match_date'}
    if not needed <= cols:
        return None
    date = str(item.get('dateEvent') or item.get('date') or '')[:10]
    home, away = _home_away(item)
    if not date or not home or not away:
        return None
    candidates = _rows(conn, 'SELECT * FROM matches WHERE substr(match_date,1,10)=? LIMIT 501', (date,))
    if len(candidates) > 500:
        return None
    matched = []
    for row in candidates:
        if (_norm(row.get('home_team')), _norm(row.get('away_team'))) != (_norm(home), _norm(away)):
            continue
        league = str(item.get('idLeague') or '')
        # Numeric league IDs are provider-scoped too. Names may disambiguate across sources.
        source = _norm(row.get('source') or row.get('provider'))
        row_league = str(row.get('league_id') or '')
        if league and row_league and 'sportsdb' in source and league != row_league:
            continue
        name = _norm(item.get('strLeague'))
        row_name = _norm(row.get('competition_name') or row.get('league_name'))
        if name and row_name and name != row_name:
            continue
        matched.append(row['id'])
    return matched[0] if len(matched) == 1 else None


def _upsert_highlight(conn, item):
    now = _now()
    sid = _event_id(item)
    date_value = (item.get('dateEvent') or item.get('date') or '')[:10]
    home, away = _home_away(item)
    video = public_https_url(_video_url(item))
    embed = _youtube_embed_url(video)
    if not video:
        return None
    hid = hashlib.md5(('sportsdb-highlight:' + (sid or video)).encode()).hexdigest()[:22]
    match_id = _find_match(conn, item) or ''
    provider = 'YouTube' if 'youtu' in video.lower() else 'Video'
    existing = _one(conn, 'SELECT * FROM sportsdb_match_highlights WHERE id=?', (hid,)) or {}
    # Approval belongs to a specific media URL and event, never to a mutable event slot.
    changed = bool(existing and (
        existing.get('video_url') != video or str(existing.get('match_id') or '') != str(match_id)
    ))
    if changed:
        existing = {key: value for key, value in existing.items() if key in {'created_at'}}
    rights_status = _rights_status(existing)
    commercial = str(existing.get('commercial_use_status') or 'UNKNOWN').strip().upper()
    attribution = str(existing.get('attribution') or '').strip()
    attribution_required = int(bool(existing.get('attribution_required')))
    rights_verified_at = str(existing.get('rights_verified_at') or '')
    official_source_verified = int(bool(existing.get('official_source_verified')))
    geo_restriction_status = str(existing.get('geo_restriction_status') or 'UNKNOWN').strip().upper()
    embed_policy = str(existing.get('embed_policy') or 'LEGACY')
    if embed_policy == 'LINK_ONLY':
        embed = ''
    approved = rights_status in APPROVED_RIGHTS_STATES and commercial in COMMERCIAL_ALLOWED_STATES
    if rights_status == 'ATTRIBUTION_REQUIRED' and not attribution:
        approved = False
    status = 'READY' if video and approved else ('REVIEW_REQUIRED' if video else 'NO_VIDEO')
    client_status = 'AUTHORIZED' if approved else status
    created_at = existing.get('created_at') or now
    conn.execute('''INSERT INTO sportsdb_match_highlights
        (id,sportsdb_event_id,match_id,event_date,league_id,league_name,home_team,away_team,title,video_url,embed_url,thumbnail_url,source,provider,status,client_status,rights_status,commercial_use_status,attribution,attribution_required,rights_verified_at,official_source_verified,geo_restriction_status,rights_note,raw_json,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          sportsdb_event_id=excluded.sportsdb_event_id,
          match_id=excluded.match_id,
          event_date=excluded.event_date,
          league_id=excluded.league_id,
          league_name=excluded.league_name,
          home_team=excluded.home_team,
          away_team=excluded.away_team,
          title=excluded.title,
          video_url=excluded.video_url,
          embed_url=excluded.embed_url,
          thumbnail_url=excluded.thumbnail_url,
          source=excluded.source,
          provider=excluded.provider,
          status=excluded.status,
          client_status=excluded.client_status,
          rights_status=excluded.rights_status,
          rights_note=excluded.rights_note,
          commercial_use_status=excluded.commercial_use_status,
          attribution=excluded.attribution,
          attribution_required=excluded.attribution_required,
          rights_verified_at=excluded.rights_verified_at,
          official_source_verified=excluded.official_source_verified,
          geo_restriction_status=excluded.geo_restriction_status,
          raw_json=excluded.raw_json,
          updated_at=excluded.updated_at''', (
        hid, sid, match_id, date_value, str(item.get('idLeague') or ''), item.get('strLeague') or '', home, away,
        _title(item), video, embed, _thumb(item), 'TheSportsDB', provider,
        status, client_status, rights_status, commercial, attribution, attribution_required,
        rights_verified_at, official_source_verified, geo_restriction_status, rights_status,
        json.dumps(item, ensure_ascii=False), created_at, now))
    conn.execute("UPDATE sportsdb_match_highlights SET embed_policy=?,allowed_channels_json=? WHERE id=?", (embed_policy, existing.get('allowed_channels_json') or '', hid))
    if changed or (existing and existing.get('thumbnail_url') != _thumb(item)):
        conn.execute("UPDATE sportsdb_match_highlights SET thumbnail_rights_status='UNKNOWN_RIGHTS', thumbnail_commercial_use_status='UNKNOWN', thumbnail_attribution='' WHERE id=?", (hid,))
    return {
        'id': hid,
        'match_id': match_id,
        'sportsdb_event_id': sid,
        'rights_status': rights_status,
        'client_status': client_status,
    }


def _summary_for_match(conn, match):
    stored = _rows(conn, 'SELECT * FROM sportsdb_match_highlights WHERE match_id=? ORDER BY updated_at DESC LIMIT 5', (match.get('id'),))
    _classified, highlights = _visible_highlights(stored)
    score = match.get('score') or ''
    status = match.get('status') or ''
    comp = match.get('competition_name') or match.get('league_name') or 'Competición'
    line = f"{match.get('home_team','Local')} vs {match.get('away_team','Visitante')} · {comp}"
    if score:
        line += f" · marcador {score}"
    if highlights:
        line += f" · {len(highlights)} resumen(es)/highlight(s) guardados desde TheSportsDB."
    else:
        line += " · sin resumen disponible todavía en TheSportsDB."
    if status:
        line += f" Estado: {status}."
    return line, highlights


def rebuild_match_enrichment(db_path, limit=300):
    ensure_sportsdb_highlights_schema(db_path)
    with _connect(db_path) as conn:
        if not _table_exists(conn, 'matches'):
            return {'ok': False, 'error': 'No existe tabla matches'}
        cols = _cols(conn, 'matches')
        select = ','.join([c for c in ['id','external_id','match_date','competition_name','league_name','home_team','away_team','score','status'] if c in cols])
        if not select:
            return {'ok': False, 'error': 'Tabla matches sin columnas compatibles'}
        matches = _rows(conn, f"SELECT {select} FROM matches ORDER BY match_date DESC LIMIT ?", (int(limit or 300),))
        now = _now()
        updated = 0
        for m in matches:
            summary, highlights = _summary_for_match(conn, m)
            eid = m.get('external_id') or ''
            enrich_id = hashlib.md5(('sportsdb-enrich:' + str(m.get('id'))).encode()).hexdigest()[:22]
            conn.execute('''INSERT OR REPLACE INTO sportsdb_match_enrichment
                (id,match_id,sportsdb_event_id,event_date,enrichment_status,has_highlight,has_event_detail,highlight_count,summary_text,payload_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (
                enrich_id, m.get('id'), eid.replace('sportsdb-', ''), str(m.get('match_date') or '')[:10],
                'READY' if highlights else 'PENDING_HIGHLIGHT', 1 if highlights else 0, 1 if eid else 0, len(highlights),
                summary, json.dumps({'highlights': highlights[:3]}, ensure_ascii=False), now, now))
            updated += 1
        conn.commit()
    return {'ok': True, 'updated': updated}


def sync_sportsdb_highlights(db_path, days_back=5, limit=250, force=False):
    """Bounded metadata sync. No automatic publication, binaries or Telegram."""
    import uuid
    import time
    ensure_sportsdb_highlights_schema(db_path)
    if not _api_key():
        return {'ok': False, 'sin_key': True, 'state': 'NOT_CONFIGURED', 'external_calls': 0, 'error': 'Falta la clave de TheSportsDB.'}
    try:
        days = max(0, min(int(days_back), 7))
        maximum = max(1, min(int(limit), 300))
        budget = max(0, min(int(os.getenv('THESPORTSDB_HIGHLIGHTS_DAILY_CALL_BUDGET', '8')), 24))
    except (ValueError, TypeError):
        return {'ok': False, 'state': 'INVALID_LIMIT', 'external_calls': 0}
    run_id, start = uuid.uuid4().hex[:22], _now()
    with _connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS sportsdb_highlight_requests(id TEXT PRIMARY KEY, run_id TEXT, madrid_date TEXT, requested_at TEXT)')
        last = _one(conn, 'SELECT started_at FROM sportsdb_highlight_runs ORDER BY started_at DESC LIMIT 1') or {}
        try:
            age = (datetime.now(TZ) - datetime.fromisoformat(last.get('started_at') or '')).total_seconds()
        except (ValueError, TypeError):
            age = 99999
        if age < 300:
            return {'ok': True, 'skipped': True, 'state': 'RECENT_RUN', 'external_calls': 0}
        conn.execute('INSERT INTO sportsdb_highlight_runs(id,started_at,status,days_back) VALUES (?,?,?,?)', (run_id, start, 'RUNNING', days))
    found = linked = calls = 0
    errors = []
    deadline = time.monotonic() + 18
    for delta in range(days + 1):
        if time.monotonic() >= deadline:
            errors.append('TIME_BUDGET_REACHED')
            break
        with _connect(db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            used = conn.execute('SELECT COUNT(*) FROM sportsdb_highlight_requests WHERE madrid_date=?', (_today().isoformat(),)).fetchone()[0]
            if used >= budget:
                errors.append('DAILY_BUDGET_REACHED')
                break
            conn.execute('INSERT INTO sportsdb_highlight_requests VALUES (?,?,?,?)', (uuid.uuid4().hex, run_id, _today().isoformat(), _now()))
        date = (_today() - timedelta(days=delta)).isoformat()
        calls += 1
        try:
            payload = _sportsdb_v1('eventshighlights.php', {'d': date, 's': 'Soccer'})
            if not isinstance(payload, dict) or payload.get('error') or payload.get('errors'):
                raise ValueError('provider_payload')
            if not any(key in payload and (payload[key] is None or isinstance(payload[key], list)) for key in ('eventshighlights','highlights','events','tv','results')):
                raise ValueError('provider_shape')
            # The read above completed before this short write transaction begins.
            with _connect(db_path) as conn:
                for item in _as_list(payload)[:max(0, maximum-found)]:
                    if not isinstance(item, dict):
                        continue
                    saved = _upsert_highlight(conn, item)
                    if saved:
                        found += 1
                        linked += bool(saved.get('match_id'))
            if found >= maximum:
                break
        except Exception as exc:
            # Never persist raw exception strings: V1 request URLs contain the API key.
            code = getattr(exc, 'code', None)
            errors.append('PROVIDER_HTTP_' + str(code) if isinstance(code, int) else 'PROVIDER_REQUEST_FAILED')
            break
    try:
        enrich = rebuild_match_enrichment(db_path, limit=maximum)
    except Exception:
        enrich = {}
        errors.append('ENRICHMENT_FAILED')
    state = 'OK' if not errors else ('PARTIAL' if found else 'ERROR')
    with _connect(db_path) as conn:
        conn.execute('UPDATE sportsdb_highlight_runs SET finished_at=?,status=?,highlights_found=?,linked_matches=?,errors=? WHERE id=?',
                     (_now(), state, found, linked, '; '.join(errors), run_id))
    return {'ok': not errors, 'state': state, 'run_id': run_id, 'days_back': days,
            'highlights_found': found, 'linked_matches': linked, 'external_calls': calls,
            'enrichment_updated': enrich.get('updated', 0), 'errors': errors,
            'rights_auto_approved': 0, 'downloads_video': False}


def sportsdb_highlights_for_match(db_path, match_id):
    """Compatibility entry point: reads never prepare storage or call providers."""
    from engines.highlight_read_model import read_highlights_for_match
    return read_highlights_for_match(db_path, match_id)


def sportsdb_highlights_summary(db_path):
    """Stored observations, not a readiness score or a live-playback certificate."""
    from engines.highlight_read_model import read_highlights_summary
    return read_highlights_summary(db_path)
