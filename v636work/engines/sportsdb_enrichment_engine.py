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


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _one(conn, sql, args=()):
    row = conn.execute(sql, args).fetchone()
    return dict(row) if row else None


def _rows(conn, sql, args=()):
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _table_exists(conn, table):
    return bool(_one(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)))


def _cols(conn, table):
    if not _table_exists(conn, table):
        return set()
    return {r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _api_key():
    return (os.getenv('THESPORTSDB_KEY') or os.getenv('THESPORTSDB_API_KEY') or '').strip()


def _fetch_json(url, headers=None, timeout=14):
    req = urllib.request.Request(url, headers=headers or {'User-Agent': 'NeMeSiS-SHARK-PRO/1.0'})
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


def _sportsdb_v2(path):
    key = _api_key()
    if not key:
        return {}
    url = 'https://www.thesportsdb.com/api/v2/json/' + path.strip('/')
    return _fetch_json(url, headers={'User-Agent': 'NeMeSiS-SHARK-PRO/1.0', 'X-API-KEY': key})


def _as_list(payload, preferred=()):
    if not isinstance(payload, dict):
        return []
    for key in preferred:
        if isinstance(payload.get(key), list):
            return payload.get(key) or []
    for key in ('events', 'event', 'teams', 'team', 'leagues', 'countries', 'players', 'results'):
        if isinstance(payload.get(key), list):
            return payload.get(key) or []
    for value in payload.values():
        if isinstance(value, list):
            return value
    return []


def _norm(value):
    return ''.join(ch for ch in str(value or '').lower() if ch.isalnum())


def _hash(prefix, *parts):
    raw = prefix + ':' + ':'.join(str(p or '') for p in parts)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:24]


def ensure_sportsdb_enrichment_schema(db_path):
    with _connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_data_sources(
            id TEXT PRIMARY KEY,
            source_name TEXT DEFAULT 'TheSportsDB',
            source_type TEXT,
            endpoint TEXT,
            legal_note TEXT,
            attribution TEXT,
            last_sync_at TEXT,
            payload_json TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_league_profiles(
            id TEXT PRIMARY KEY,
            sportsdb_league_id TEXT UNIQUE,
            league_name TEXT,
            alternate_name TEXT,
            sport TEXT,
            country TEXT,
            formed_year TEXT,
            badge_url TEXT,
            logo_url TEXT,
            poster_url TEXT,
            fanart_url TEXT,
            website TEXT,
            description_es TEXT,
            description_en TEXT,
            raw_json TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_team_profiles(
            id TEXT PRIMARY KEY,
            sportsdb_team_id TEXT UNIQUE,
            team_name TEXT,
            alternate_name TEXT,
            short_name TEXT,
            league_id TEXT,
            league_name TEXT,
            country TEXT,
            stadium_name TEXT,
            stadium_location TEXT,
            stadium_capacity TEXT,
            formed_year TEXT,
            badge_url TEXT,
            logo_url TEXT,
            jersey_url TEXT,
            fanart_url TEXT,
            website TEXT,
            description_es TEXT,
            description_en TEXT,
            raw_json TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_event_profiles(
            id TEXT PRIMARY KEY,
            sportsdb_event_id TEXT UNIQUE,
            match_id TEXT,
            league_id TEXT,
            league_name TEXT,
            season TEXT,
            event_date TEXT,
            event_time TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score TEXT,
            away_score TEXT,
            venue TEXT,
            country TEXT,
            status TEXT,
            round TEXT,
            poster_url TEXT,
            thumb_url TEXT,
            video_url TEXT,
            raw_json TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS sportsdb_enrichment_runs(
            id TEXT PRIMARY KEY,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            mode TEXT,
            leagues_processed INTEGER DEFAULT 0,
            teams_processed INTEGER DEFAULT 0,
            events_processed INTEGER DEFAULT 0,
            linked_matches INTEGER DEFAULT 0,
            errors TEXT
        )''')
        conn.execute('''INSERT OR REPLACE INTO sportsdb_data_sources
            (id,source_name,source_type,endpoint,legal_note,attribution,last_sync_at,payload_json)
            VALUES (?,?,?,?,?,?,?,?)''', (
            'thesportsdb-api', 'TheSportsDB', 'API deportiva', 'https://www.thesportsdb.com/documentation',
            'Datos obtenidos mediante API autorizada TheSportsDB y guardados en caché SQLite propia. No se usa scraping de webs oficiales ni terceros.',
            'Fuente: TheSportsDB', _now(), json.dumps({'version': 'V593'}, ensure_ascii=False)))
        conn.commit()
    return {'ok': True, 'schema': 'sportsdb_enrichment'}


def _match_by_event_or_names(conn, event):
    if not _table_exists(conn, 'matches'):
        return ''
    cols = _cols(conn, 'matches')
    sid = str(event.get('idEvent') or event.get('id') or '')
    if sid and 'external_id' in cols:
        found = _one(conn, "SELECT id FROM matches WHERE external_id=? OR external_id=? LIMIT 1", (sid, 'sportsdb-' + sid))
        if found:
            return found.get('id') or ''
    date_value = str(event.get('dateEvent') or event.get('date') or '')[:10]
    home = event.get('strHomeTeam') or ''
    away = event.get('strAwayTeam') or ''
    if not date_value or not home or not away or not {'id','home_team','away_team','match_date'}.issubset(cols):
        return ''
    candidates = _rows(conn, "SELECT id,home_team,away_team,match_date FROM matches WHERE match_date LIKE ? LIMIT 120", (date_value + '%',))
    hn, an = _norm(home), _norm(away)
    for match in candidates:
        if _norm(match.get('home_team')) == hn and _norm(match.get('away_team')) == an:
            return match.get('id') or ''
    for match in candidates:
        text = _norm(str(match.get('home_team')) + str(match.get('away_team')))
        if hn in text and an in text:
            return match.get('id') or ''
    return ''


def _upsert_league(conn, item):
    sid = str(item.get('idLeague') or item.get('id') or item.get('league_id') or '')
    if not sid:
        return None
    row_id = _hash('league', sid)
    conn.execute('''INSERT OR REPLACE INTO sportsdb_league_profiles
        (id,sportsdb_league_id,league_name,alternate_name,sport,country,formed_year,badge_url,logo_url,poster_url,fanart_url,website,description_es,description_en,raw_json,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        row_id, sid, item.get('strLeague') or item.get('name') or '', item.get('strLeagueAlternate') or '', item.get('strSport') or 'Soccer', item.get('strCountry') or '',
        item.get('intFormedYear') or '', item.get('strBadge') or '', item.get('strLogo') or '', item.get('strPoster') or '', item.get('strFanart1') or '', item.get('strWebsite') or '',
        item.get('strDescriptionES') or '', item.get('strDescriptionEN') or '', json.dumps(item, ensure_ascii=False), _now()))
    return sid


def _upsert_team(conn, item):
    sid = str(item.get('idTeam') or item.get('id') or item.get('team_id') or '')
    if not sid:
        return None
    row_id = _hash('team', sid)
    conn.execute('''INSERT OR REPLACE INTO sportsdb_team_profiles
        (id,sportsdb_team_id,team_name,alternate_name,short_name,league_id,league_name,country,stadium_name,stadium_location,stadium_capacity,formed_year,badge_url,logo_url,jersey_url,fanart_url,website,description_es,description_en,raw_json,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        row_id, sid, item.get('strTeam') or item.get('name') or '', item.get('strTeamAlternate') or '', item.get('strTeamShort') or '', str(item.get('idLeague') or ''),
        item.get('strLeague') or '', item.get('strCountry') or '', item.get('strStadium') or '', item.get('strStadiumLocation') or '', str(item.get('intStadiumCapacity') or ''),
        item.get('intFormedYear') or '', item.get('strBadge') or '', item.get('strLogo') or '', item.get('strEquipment') or '', item.get('strTeamFanart1') or '', item.get('strWebsite') or '',
        item.get('strDescriptionES') or '', item.get('strDescriptionEN') or '', json.dumps(item, ensure_ascii=False), _now()))
    return sid


def _upsert_event(conn, item):
    sid = str(item.get('idEvent') or item.get('id') or item.get('event_id') or '')
    if not sid:
        return None
    match_id = _match_by_event_or_names(conn, item)
    row_id = _hash('event', sid)
    conn.execute('''INSERT OR REPLACE INTO sportsdb_event_profiles
        (id,sportsdb_event_id,match_id,league_id,league_name,season,event_date,event_time,home_team,away_team,home_score,away_score,venue,country,status,round,poster_url,thumb_url,video_url,raw_json,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        row_id, sid, match_id, str(item.get('idLeague') or ''), item.get('strLeague') or '', item.get('strSeason') or '', item.get('dateEvent') or '', item.get('strTime') or item.get('strTimestamp') or '',
        item.get('strHomeTeam') or '', item.get('strAwayTeam') or '', str(item.get('intHomeScore') or ''), str(item.get('intAwayScore') or ''), item.get('strVenue') or '', item.get('strCountry') or '',
        item.get('strStatus') or item.get('strProgress') or '', str(item.get('intRound') or ''), item.get('strPoster') or '', item.get('strThumb') or '', item.get('strVideo') or '',
        json.dumps(item, ensure_ascii=False), _now()))
    return {'event_id': sid, 'match_id': match_id}


def _target_leagues(conn, limit):
    ids = []
    if _table_exists(conn, 'competitions'):
        cols = _cols(conn, 'competitions')
        ext = 'external_id' if 'external_id' in cols else None
        if ext:
            for row in _rows(conn, f"SELECT {ext} AS external_id FROM competitions WHERE COALESCE({ext},'')<>'' LIMIT ?", (int(limit or 30),)):
                raw = str(row.get('external_id') or '').replace('sportsdb-', '')
                if raw and raw.isdigit():
                    ids.append(raw)
    if _table_exists(conn, 'matches'):
        cols = _cols(conn, 'matches')
        if 'league_id' in cols:
            for row in _rows(conn, "SELECT DISTINCT league_id FROM matches WHERE COALESCE(league_id,'')<>'' LIMIT ?", (int(limit or 30),)):
                raw = str(row.get('league_id') or '').replace('sportsdb-', '')
                if raw and raw.isdigit():
                    ids.append(raw)
    # Ligas principales de fútbol en TheSportsDB como fallback prudente.
    ids.extend(['4335','4328','4331','4332','4334','4337','4338','4480','4481','4482','4483'])
    seen, out = set(), []
    for item in ids:
        if item not in seen:
            seen.add(item); out.append(item)
    return out[:int(limit or 30)]


def sync_sportsdb_max_enrichment(db_path, limit=30, include_past=True, include_next=True):
    ensure_sportsdb_enrichment_schema(db_path)
    run_id = _hash('sportsdb-max-run', _now())
    started = _now()
    leagues = teams = events = linked = 0
    errors = []
    if not _api_key():
        return {'ok': False, 'sin_key': True, 'error': 'Falta THESPORTSDB_KEY o THESPORTSDB_API_KEY'}
    with _connect(db_path) as conn:
        conn.execute('INSERT OR REPLACE INTO sportsdb_enrichment_runs(id,started_at,finished_at,status,mode,errors) VALUES (?,?,?,?,?,?)',
                     (run_id, started, '', 'RUNNING', 'max_enrichment', ''))
        conn.commit()
        # Catálogo general de ligas de fútbol.
        try:
            payload = _sportsdb_v1('search_all_leagues.php', {'s': 'Soccer'})
            for item in _as_list(payload, ('countrys', 'leagues'))[:max(50, int(limit or 30))]:
                if _upsert_league(conn, item):
                    leagues += 1
        except Exception as exc:
            errors.append('leagues: %s' % exc)
        league_ids = _target_leagues(conn, limit)
        for league_id in league_ids:
            try:
                payload = _sportsdb_v1('lookupleague.php', {'id': league_id})
                for item in _as_list(payload, ('leagues',))[:1]:
                    if _upsert_league(conn, item):
                        leagues += 1
            except Exception as exc:
                errors.append('league %s: %s' % (league_id, exc))
            try:
                payload = _sportsdb_v1('lookup_all_teams.php', {'id': league_id})
                for item in _as_list(payload, ('teams',))[:80]:
                    if _upsert_team(conn, item):
                        teams += 1
            except Exception as exc:
                errors.append('teams %s: %s' % (league_id, exc))
            if include_next:
                try:
                    payload = _sportsdb_v1('eventsnextleague.php', {'id': league_id})
                    for item in _as_list(payload, ('events',))[:30]:
                        saved = _upsert_event(conn, item)
                        if saved:
                            events += 1
                            if saved.get('match_id'):
                                linked += 1
                except Exception as exc:
                    errors.append('next %s: %s' % (league_id, exc))
            if include_past:
                try:
                    payload = _sportsdb_v1('eventspastleague.php', {'id': league_id})
                    for item in _as_list(payload, ('events',))[:30]:
                        saved = _upsert_event(conn, item)
                        if saved:
                            events += 1
                            if saved.get('match_id'):
                                linked += 1
                except Exception as exc:
                    errors.append('past %s: %s' % (league_id, exc))
        conn.execute('UPDATE sportsdb_enrichment_runs SET finished_at=?, status=?, leagues_processed=?, teams_processed=?, events_processed=?, linked_matches=?, errors=? WHERE id=?',
                     (_now(), 'OK' if not errors else 'PARTIAL', leagues, teams, events, linked, '; '.join(errors[:8]), run_id))
        conn.commit()
    return {'ok': True, 'run_id': run_id, 'leagues_processed': leagues, 'teams_processed': teams, 'events_processed': events, 'linked_matches': linked, 'errors': errors[:8]}


def sportsdb_enrichment_summary(db_path):
    ensure_sportsdb_enrichment_schema(db_path)
    with _connect(db_path) as conn:
        leagues = (_one(conn, 'SELECT COUNT(*) AS total FROM sportsdb_league_profiles') or {}).get('total', 0)
        teams = (_one(conn, 'SELECT COUNT(*) AS total FROM sportsdb_team_profiles') or {}).get('total', 0)
        events = (_one(conn, 'SELECT COUNT(*) AS total FROM sportsdb_event_profiles') or {}).get('total', 0)
        linked = (_one(conn, "SELECT COUNT(*) AS total FROM sportsdb_event_profiles WHERE COALESCE(match_id,'')<>''") or {}).get('total', 0)
        badges = (_one(conn, "SELECT COUNT(*) AS total FROM sportsdb_team_profiles WHERE COALESCE(badge_url,'')<>''") or {}).get('total', 0)
        venues = (_one(conn, "SELECT COUNT(*) AS total FROM sportsdb_team_profiles WHERE COALESCE(stadium_name,'')<>''") or {}).get('total', 0)
        top_leagues = _rows(conn, 'SELECT league_name,country,badge_url FROM sportsdb_league_profiles ORDER BY updated_at DESC LIMIT 8')
        top_teams = _rows(conn, 'SELECT team_name,league_name,country,stadium_name,badge_url FROM sportsdb_team_profiles ORDER BY updated_at DESC LIMIT 8')
        latest_events = _rows(conn, 'SELECT home_team,away_team,league_name,event_date,match_id FROM sportsdb_event_profiles ORDER BY updated_at DESC LIMIT 8')
        runs = _rows(conn, 'SELECT * FROM sportsdb_enrichment_runs ORDER BY started_at DESC LIMIT 5')
    score = 15 + (25 if _api_key() else 0) + min(20, leagues // 5) + min(20, teams // 20) + min(10, events // 20) + (10 if linked else 0)
    return {
        'status': 'ACTIVO' if _api_key() else 'FALTA KEY',
        'key_present': bool(_api_key()),
        'readiness_score': min(int(score), 100),
        'leagues_total': leagues,
        'teams_total': teams,
        'events_total': events,
        'linked_matches': linked,
        'badges_total': badges,
        'stadiums_total': venues,
        'top_leagues': top_leagues,
        'top_teams': top_teams,
        'latest_events': latest_events,
        'recent_runs': runs,
        'legal_note': 'Enriquecimiento basado en TheSportsDB API con caché SQLite propia. Sin scraping de páginas oficiales.'
    }


def sportsdb_enrichment_for_match(db_path, match):
    ensure_sportsdb_enrichment_schema(db_path)
    match_id = match.get('id') if isinstance(match, dict) else str(match or '')
    home = match.get('home_team') if isinstance(match, dict) else ''
    away = match.get('away_team') if isinstance(match, dict) else ''
    league = match.get('league_name') or match.get('competition_name') if isinstance(match, dict) else ''
    with _connect(db_path) as conn:
        event = _one(conn, 'SELECT * FROM sportsdb_event_profiles WHERE match_id=? ORDER BY updated_at DESC LIMIT 1', (match_id,)) or {}
        home_team = _one(conn, 'SELECT * FROM sportsdb_team_profiles WHERE lower(team_name)=lower(?) ORDER BY updated_at DESC LIMIT 1', (home or '',)) or {}
        away_team = _one(conn, 'SELECT * FROM sportsdb_team_profiles WHERE lower(team_name)=lower(?) ORDER BY updated_at DESC LIMIT 1', (away or '',)) or {}
        league_profile = _one(conn, 'SELECT * FROM sportsdb_league_profiles WHERE lower(league_name)=lower(?) ORDER BY updated_at DESC LIMIT 1', (league or '',)) or {}
    notes = []
    if home_team.get('stadium_name'):
        notes.append('Estadio local: %s%s.' % (home_team.get('stadium_name'), (' · ' + home_team.get('stadium_location')) if home_team.get('stadium_location') else ''))
    if event.get('venue'):
        notes.append('Sede del evento según TheSportsDB: %s.' % event.get('venue'))
    if league_profile.get('country'):
        notes.append('Competición enriquecida: %s · %s.' % (league_profile.get('league_name') or league, league_profile.get('country')))
    if home_team.get('description_es') or away_team.get('description_es'):
        notes.append('Contexto histórico de clubes disponible desde TheSportsDB.')
    available = bool(event or home_team or away_team or league_profile)
    return {
        'available': available,
        'event': event,
        'home_team': home_team,
        'away_team': away_team,
        'league': league_profile,
        'notes': notes,
        'summary': 'Datos enriquecidos desde TheSportsDB disponibles.' if available else 'Enriquecimiento TheSportsDB pendiente para este partido.',
        'legal_note': 'Fuente: TheSportsDB API. Caché propia, sin scraping.'
    }
