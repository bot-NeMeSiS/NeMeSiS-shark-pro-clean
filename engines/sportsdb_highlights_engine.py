import hashlib
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from engines.content_rights_engine import classify_media_asset
from engines.highlight_url_engine import public_https_url, safe_embed_url
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


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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


def _fetch_json(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': 'NeMeSiS-SHARK-PRO/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode('utf-8', errors='replace'))


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
    """Return a privacy-friendly YouTube embed URL when possible; never downloads video."""
    raw = str(url or '').strip()
    if not raw:
        return ''
    try:
        parsed = urllib.parse.urlparse(raw)
        host = (parsed.netloc or '').lower().replace('www.', '')
        video_id = ''
        if host in {'youtu.be'}:
            video_id = parsed.path.strip('/').split('/')[0]
        elif 'youtube.com' in host:
            if parsed.path.startswith('/watch'):
                video_id = urllib.parse.parse_qs(parsed.query).get('v', [''])[0]
            elif parsed.path.startswith('/embed/'):
                video_id = parsed.path.split('/embed/', 1)[1].split('/')[0]
            elif parsed.path.startswith('/shorts/'):
                video_id = parsed.path.split('/shorts/', 1)[1].split('/')[0]
        video_id = ''.join(ch for ch in video_id if ch.isalnum() or ch in {'_', '-'})[:80]
        if video_id:
            return 'https://www.youtube-nocookie.com/embed/' + video_id
    except Exception:
        return ''
    return ''


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
    """Apply rights, URL and channel guards to persisted highlight metadata."""
    row = dict(item or {})
    rights_status = _rights_status(row)
    commercial = str(row.get('commercial_use_status') or 'UNKNOWN').strip().upper()
    geo_status = str(row.get('geo_restriction_status') or 'UNKNOWN').strip().upper()
    original_url = public_https_url(row.get('video_url') or row.get('original_url') or '')
    embed_url = str(row.get('embed_url') or '').strip()
    embed_policy = str(row.get('embed_policy') or 'LEGACY').strip().upper()
    if embed_policy in {'LINK_ONLY', 'BLOCKED', 'REVIEW_REQUIRED'} or geo_status in {'BLOCKED', 'RESTRICTED', 'GEO_BLOCKED'}:
        embed_url = ''
    try:
        channels = json.loads(row.get('allowed_channels_json') or '[]')
        if not isinstance(channels, list):
            channels = []
    except (ValueError, TypeError):
        channels = []
    channels = [str(value).strip().upper() for value in channels if str(value).strip()]
    requested_channel = str(channel or 'APP').strip().upper()
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
        'channel': requested_channel,
        'allowed_channels': channels,
    })
    if channels and requested_channel not in channels:
        decision = {
            **decision,
            'can_embed': False,
            'can_link': False,
            'show_block': False,
            'channel_allowed': False,
            'decision': 'BLOCKED',
            'reason': 'La licencia no autoriza esta superficie o canal.',
        }
    if not original_url:
        decision = {
            **decision,
            'can_embed': False,
            'can_link': False,
            'show_block': False,
            'decision': 'BLOCKED',
            'reason': 'La URL del vídeo no es pública y HTTPS válida.',
        }
    thumbnail = classify_media_asset({
        'content_type': 'thumbnail',
        'source': row.get('source') or row.get('provider'),
        'image_url': row.get('thumbnail_url'),
        'rights_status': row.get('thumbnail_rights_status') or 'UNKNOWN_RIGHTS',
        'commercial_use_status': row.get('thumbnail_commercial_use_status') or 'UNKNOWN',
        'attribution': row.get('thumbnail_attribution') or '',
        'rights_verified_at': row.get('rights_verified_at'),
    }, channel=requested_channel)
    return {
        **row,
        **decision,
        'video_url': original_url,
        'allowed_channels': channels,
        'thumbnail_url': thumbnail.get('asset_url') if thumbnail.get('can_display') else '',
        'thumbnail_rights': thumbnail,
        'geo_restriction_status': geo_status,
        'geo_restricted': geo_status in {'BLOCKED', 'RESTRICTED', 'GEO_BLOCKED'},
    }

def _visible_highlights(items):
    classified = [classify_stored_highlight(item) for item in (items or [])]
    return classified, [item for item in classified if item.get('show_block')]


def _find_match(conn, item):
    """Associate only an unambiguous SportsDB identity or exact dated team pair."""
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
            if item.get('dateEvent') and str(row.get('match_date') or '')[:10] != str(item['dateEvent'])[:10]:
                from engines.postmatch_sources import match_event
                if not match_event(row, item):
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
    embed = safe_embed_url(video)
    if not video:
        return None
    hid = hashlib.md5(('sportsdb-highlight:' + (sid or video)).encode()).hexdigest()[:22]
    match_id = _find_match(conn, item) or ''
    provider = 'YouTube' if 'youtu' in video.lower() else 'Video'
    existing = _one(conn, 'SELECT * FROM sportsdb_match_highlights WHERE id=?', (hid,)) or {}
    # Approval is bound to the exact content and association, not merely the event ID.
    changed = bool(existing) and any(str(existing.get(key) or '') != str(value or '') for key, value in (
        ('video_url', video), ('match_id', match_id), ('event_date', date_value),
        ('home_team', home), ('away_team', away)))
    if changed:
        revoked = {key: existing.get(key) for key in ('video_url','match_id','rights_status','commercial_use_status','rights_verified_at')}
        conn.execute("UPDATE sportsdb_match_highlights SET rights_status='REVIEW_REQUIRED',rights_note='REVIEW_REQUIRED',"
                     "commercial_use_status='UNKNOWN',rights_verified_at='',official_source_verified=0,"
                     "thumbnail_rights_status='UNKNOWN_RIGHTS',thumbnail_commercial_use_status='UNKNOWN' WHERE id=?", (hid,))
        existing = {**existing, 'rights_status':'REVIEW_REQUIRED', 'commercial_use_status':'UNKNOWN',
                    'rights_verified_at':'', 'official_source_verified':0}
        if _table_exists(conn, 'sportsdb_highlight_reviews'):
            conn.execute('INSERT INTO sportsdb_highlight_reviews(highlight_id,actor,decision,evidence_url,basis,previous_json,created_at) '
                         'VALUES(?,?,?,?,?,?,?)', (hid, 'ingestion', 'REVIEW_REQUIRED', '', 'MEDIA_IDENTITY_CHANGED', json.dumps(revoked), now))
    if existing and str(existing.get('thumbnail_url') or '') != str(_thumb(item) or ''):
        conn.execute("UPDATE sportsdb_match_highlights SET thumbnail_rights_status='UNKNOWN_RIGHTS',"
                     "thumbnail_commercial_use_status='UNKNOWN',thumbnail_attribution='' WHERE id=?", (hid,))
    rights_status = _rights_status(existing)
    commercial = str(existing.get('commercial_use_status') or 'UNKNOWN').strip().upper()
    attribution = str(existing.get('attribution') or '').strip()
    attribution_required = int(bool(existing.get('attribution_required')))
    rights_verified_at = str(existing.get('rights_verified_at') or '')
    official_source_verified = int(bool(existing.get('official_source_verified')))
    geo_restriction_status = str(existing.get('geo_restriction_status') or 'UNKNOWN').strip().upper()
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
          raw_json=excluded.raw_json,
          updated_at=excluded.updated_at''', (
        hid, sid, match_id, date_value, str(item.get('idLeague') or ''), item.get('strLeague') or '', home, away,
        _title(item), video, embed, _thumb(item), 'TheSportsDB', provider,
        status, client_status, rights_status, commercial, attribution, attribution_required,
        rights_verified_at, official_source_verified, geo_restriction_status, rights_status,
        json.dumps(item, ensure_ascii=False), created_at, now))
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
    ensure_sportsdb_highlights_schema(db_path)
    run_id = hashlib.md5(('sportsdb-highlights:' + _now()).encode()).hexdigest()[:22]
    start = _now()
    found = linked = 0
    errors = []
    if not _api_key():
        return {'ok': False, 'sin_key': True, 'error': 'Falta THESPORTSDB_API_KEY o THESPORTSDB_KEY'}
    with _connect(db_path) as conn:
        conn.execute('INSERT OR REPLACE INTO sportsdb_highlight_runs(id,started_at,finished_at,status,days_back,highlights_found,linked_matches,errors) VALUES (?,?,?,?,?,?,?,?)',
                     (run_id, start, '', 'RUNNING', int(days_back or 5), 0, 0, ''))
        conn.commit()
        for delta in range(0, int(days_back or 5) + 1):
            d = (_today() - timedelta(days=delta)).isoformat()
            try:
                payload = _sportsdb_v1('eventshighlights.php', {'d': d, 's': 'Soccer'})
                for item in _as_list(payload)[:int(limit or 250)]:
                    saved = _upsert_highlight(conn, item)
                    if saved:
                        found += 1
                        if saved.get('match_id'):
                            linked += 1
            except Exception as exc:
                errors.append(f'{d}: {exc}')
        conn.commit()
        enrich = rebuild_match_enrichment(db_path, limit=limit)
        conn.execute('UPDATE sportsdb_highlight_runs SET finished_at=?, status=?, highlights_found=?, linked_matches=?, errors=? WHERE id=?',
                     (_now(), 'OK' if not errors else 'PARTIAL', found, linked, '; '.join(errors[:5]), run_id))
        conn.commit()
    return {'ok': True, 'run_id': run_id, 'days_back': int(days_back or 5), 'highlights_found': found, 'linked_matches': linked, 'enrichment_updated': enrich.get('updated', 0), 'errors': errors[:5]}


def sportsdb_highlights_for_match(db_path, match_id):
    """Read persisted metadata only; schema creation belongs to ingestion."""
    from engines.highlight_read_model import read_highlights_for_match
    return read_highlights_for_match(db_path, match_id)


def sportsdb_highlights_summary(db_path):
    """Read persisted metadata only; schema creation belongs to ingestion."""
    from engines.highlight_read_model import read_highlights_summary
    return read_highlights_summary(db_path)


def sportsdb_highlight_by_id(db_path, highlight_id):
    from engines.highlight_read_model import read_highlight_by_id
    return read_highlight_by_id(db_path, highlight_id)


def sportsdb_highlights_map(db_path, match_ids, limit_per_match=2):
    from engines.highlight_read_model import read_highlights_map
    return read_highlights_map(db_path, match_ids, limit_per_match=limit_per_match)
