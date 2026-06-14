import hashlib
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')


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
            status TEXT DEFAULT 'READY',
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
            conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN client_status TEXT DEFAULT 'READY'")
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


def _find_match(conn, item):
    cols = _cols(conn, 'matches')
    if not cols:
        return None
    sid = _event_id(item)
    if sid and 'external_id' in cols:
        found = _one(conn, 'SELECT id FROM matches WHERE external_id=? OR external_id=? LIMIT 1', (sid, 'sportsdb-' + sid))
        if found:
            return found.get('id')
    date_value = item.get('dateEvent') or item.get('date') or item.get('strDate') or ''
    home, away = _home_away(item)
    if not date_value or not home or not away:
        return None
    candidates = _rows(conn, '''SELECT id,home_team,away_team,match_date FROM matches
        WHERE match_date LIKE ? LIMIT 80''', (str(date_value)[:10] + '%',))
    hn, an = _norm(home), _norm(away)
    for match in candidates:
        if _norm(match.get('home_team')) == hn and _norm(match.get('away_team')) == an:
            return match.get('id')
    for match in candidates:
        text = _norm(str(match.get('home_team')) + str(match.get('away_team')))
        if hn in text and an in text:
            return match.get('id')
    return None


def _upsert_highlight(conn, item):
    now = _now()
    sid = _event_id(item)
    date_value = (item.get('dateEvent') or item.get('date') or '')[:10]
    home, away = _home_away(item)
    video = _video_url(item)
    embed = _youtube_embed_url(video)
    if not sid and not video:
        return None
    hid = hashlib.md5(('sportsdb-highlight:' + (sid or video)).encode()).hexdigest()[:22]
    match_id = _find_match(conn, item) or ''
    provider = 'YouTube' if 'youtu' in video.lower() else 'Video'
    client_status = 'EMBED_READY' if embed else ('LINK_READY' if video else 'NO_VIDEO')
    conn.execute('''INSERT OR REPLACE INTO sportsdb_match_highlights
        (id,sportsdb_event_id,match_id,event_date,league_id,league_name,home_team,away_team,title,video_url,embed_url,thumbnail_url,source,provider,status,client_status,rights_note,raw_json,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        hid, sid, match_id, date_value, str(item.get('idLeague') or ''), item.get('strLeague') or '', home, away,
        _title(item), video, embed, _thumb(item), 'TheSportsDB', provider,
        'READY' if video else 'NO_VIDEO', client_status, 'Enlace/iframe externo permitido por la plataforma; no se descarga ni se rehostea vídeo.',
        json.dumps(item, ensure_ascii=False), now, now))
    return {'id': hid, 'match_id': match_id, 'sportsdb_event_id': sid}


def _summary_for_match(conn, match):
    highlights = _rows(conn, 'SELECT * FROM sportsdb_match_highlights WHERE match_id=? ORDER BY updated_at DESC LIMIT 5', (match.get('id'),))
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
    ensure_sportsdb_highlights_schema(db_path)
    with _connect(db_path) as conn:
        highlights = _rows(conn, 'SELECT * FROM sportsdb_match_highlights WHERE match_id=? ORDER BY updated_at DESC LIMIT 8', (match_id,))
        enrich = _one(conn, 'SELECT * FROM sportsdb_match_enrichment WHERE match_id=?', (match_id,)) or {}
    return {'highlights': highlights, 'enrichment': enrich, 'summary_text': enrich.get('summary_text') or ''}


def sportsdb_highlights_summary(db_path):
    ensure_sportsdb_highlights_schema(db_path)
    with _connect(db_path) as conn:
        total = (_one(conn, 'SELECT COUNT(*) AS total FROM sportsdb_match_highlights') or {}).get('total', 0)
        linked = (_one(conn, "SELECT COUNT(*) AS total FROM sportsdb_match_highlights WHERE COALESCE(match_id,'')<>''") or {}).get('total', 0)
        enriched = (_one(conn, 'SELECT COUNT(*) AS total FROM sportsdb_match_enrichment') or {}).get('total', 0)
        with_video = (_one(conn, "SELECT COUNT(*) AS total FROM sportsdb_match_highlights WHERE COALESCE(video_url,'')<>''") or {}).get('total', 0)
        latest = _rows(conn, 'SELECT * FROM sportsdb_match_highlights ORDER BY updated_at DESC LIMIT 8')
        runs = _rows(conn, 'SELECT * FROM sportsdb_highlight_runs ORDER BY started_at DESC LIMIT 6')
    readiness = 25
    if _api_key(): readiness += 25
    if total: readiness += 20
    if linked: readiness += 20
    if enriched: readiness += 10
    return {
        'status': 'ACTIVO' if _api_key() else 'FALTA KEY',
        'key_present': bool(_api_key()),
        'readiness_score': min(readiness, 100),
        'highlights_total': total,
        'with_video': with_video,
        'linked_matches': linked,
        'enriched_matches': enriched,
        'latest_highlights': latest,
        'recent_runs': runs,
        'note': 'TheSportsDB aporta highlights de YouTube por fecha/evento; pueden estar geobloqueados porque dependen de YouTube y la fuente externa.'
    }
