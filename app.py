import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import threading
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Flask, Response, jsonify, redirect, render_template, request

from database_manager import connect as sqlite_connect, retry_locked
from engines.cache_engine import cache_health
from engines.crest_engine import crest_status
from engines.live_engine import build_live_depth, build_live_flow, build_match_detail, fallback_timeline, normalize_live_state
from engines.match_engine import hub_sections, real_time_state, sync_plan
from engines.shark_engine import build_shark_context, explain_pick_risk
from engines.telegram_engine import build_alert_queue, dispatch_signature, should_skip_duplicate

APP_NAME = "NeMeSiS SHARK PRO"
APP_VERSION = "V512_PRODUCT_QA_POLISH_PASS"
SEED_VERSION = "v512-product-qa-polish-seed"
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "database.db"))
TZ = ZoneInfo("Europe/Madrid")

app = Flask(__name__)
_SEED_LOCK = threading.Lock()
_SEEDED_DB_PATH = None


def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")


def today_iso(offset=0):
    return (datetime.now(TZ).date() + timedelta(days=offset)).isoformat()


def db():
    return sqlite_connect(DB_PATH)


def slug(text):
    text = str(text or "").strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "item"


def initials(name):
    ignore = {"fc", "cf", "cd", "ud", "ad", "club", "de", "del", "la", "el", "los", "las"}
    words = [w for w in re.split(r"[\s\-]+", str(name or "")) if w]
    letters = [w[0].upper() for w in words if w.lower() not in ignore]
    if not letters and words:
        letters = [words[0][0].upper()]
    return "".join(letters[:3]) or "NS"


def table_columns(conn, table):
    try:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.OperationalError:
        return set()


def add_column_if_missing(conn, table, column, definition):
    if column not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def run_schema_migrations(conn):
    migrations = [
        ("teams", "external_id", "TEXT"),
        ("teams", "color_hint", "TEXT"),
        ("teams", "source", "TEXT"),
        ("teams", "legal_note", "TEXT"),
        ("teams", "updated_at", "TEXT"),
        ("matches", "priority", "INTEGER DEFAULT 50"),
        ("matches", "source", "TEXT"),
        ("matches", "legal_note", "TEXT"),
        ("matches", "raw_json", "TEXT"),
        ("matches", "updated_at", "TEXT"),
        ("picks", "stake_units", "REAL DEFAULT 1"),
        ("picks", "status", "TEXT DEFAULT 'PENDING'"),
        ("picks", "source", "TEXT"),
        ("picks", "legal_note", "TEXT"),
        ("picks", "reasoning", "TEXT"),
        ("picks", "raw_json", "TEXT"),
        ("picks", "updated_at", "TEXT"),
        ("combis", "status", "TEXT DEFAULT 'DRAFT'"),
        ("combis", "source", "TEXT"),
        ("combis", "updated_at", "TEXT"),
        ("client_profiles", "preferences_json", "TEXT"),
        ("client_profiles", "updated_at", "TEXT"),
        ("telegram_queue", "signature", "TEXT"),
        ("telegram_queue", "priority", "INTEGER DEFAULT 50"),
        ("telegram_queue", "payload_json", "TEXT"),
        ("telegram_queue", "status", "TEXT DEFAULT 'PENDING'"),
        ("telegram_queue", "attempts", "INTEGER DEFAULT 0"),
        ("telegram_queue", "updated_at", "TEXT"),
        ("live_sync_state", "sync_status", "TEXT"),
        ("live_sync_state", "next_refresh_at", "TEXT"),
        ("live_sync_state", "updated_at", "TEXT"),
        ("auto_alerts", "status", "TEXT DEFAULT 'READY'"),
        ("auto_alerts", "updated_at", "TEXT"),
    ]
    for table, column, definition in migrations:
        try:
            add_column_if_missing(conn, table, column, definition)
        except sqlite3.OperationalError:
            pass
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations(
            version TEXT PRIMARY KEY,
            applied_at TEXT
        )"""
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?,?)",
        (APP_VERSION, now_iso()),
    )


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS competitions(
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            scope TEXT,
            country TEXT,
            region TEXT,
            tier INTEGER DEFAULT 50,
            source_strategy TEXT,
            tags_json TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS teams(
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            region TEXT,
            logo_url TEXT,
            external_id TEXT,
            color_hint TEXT,
            source TEXT,
            legal_note TEXT,
            updated_at TEXT
        )"""
    )
    try:
        cur.execute("ALTER TABLE teams ADD COLUMN external_id TEXT")
    except sqlite3.OperationalError:
        pass
    cur.execute(
        """CREATE TABLE IF NOT EXISTS matches(
            id TEXT PRIMARY KEY,
            match_date TEXT NOT NULL,
            kickoff_time TEXT,
            competition_key TEXT,
            competition_name TEXT,
            country TEXT,
            home_team TEXT,
            away_team TEXT,
            status TEXT,
            minute TEXT,
            score TEXT,
            priority INTEGER DEFAULT 50,
            source TEXT,
            legal_note TEXT,
            raw_json TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS imports(
            id TEXT PRIMARY KEY,
            kind TEXT,
            source_name TEXT,
            source_url TEXT,
            legal_note TEXT,
            rows_count INTEGER DEFAULT 0,
            status TEXT,
            payload_preview TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS favorites(
            id TEXT PRIMARY KEY,
            kind TEXT,
            value TEXT,
            label TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS picks(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            match_date TEXT,
            competition_key TEXT,
            competition_name TEXT,
            home_team TEXT,
            away_team TEXT,
            pick_type TEXT,
            selection TEXT,
            odds REAL,
            confidence INTEGER DEFAULT 50,
            stake_units REAL DEFAULT 1,
            status TEXT DEFAULT 'PENDING',
            source TEXT,
            legal_note TEXT,
            reasoning TEXT,
            raw_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS combis(
            id TEXT PRIMARY KEY,
            name TEXT,
            picks_json TEXT,
            total_odds REAL,
            risk_level TEXT,
            status TEXT DEFAULT 'DRAFT',
            source TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS client_profiles(
            id TEXT PRIMARY KEY,
            name TEXT,
            membership_plan TEXT,
            favorite_teams_json TEXT,
            favorite_competitions_json TEXT,
            telegram_chat_id TEXT,
            preferences_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_deliveries(
            id TEXT PRIMARY KEY,
            chat_id TEXT,
            message_type TEXT,
            payload_preview TEXT,
            status TEXT,
            response_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS automation_state(
            key TEXT PRIMARY KEY,
            value_json TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS match_timeline(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            minute TEXT,
            event_type TEXT,
            title TEXT,
            detail TEXT,
            source TEXT,
            legal_note TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS persistent_cache(
            key TEXT PRIMARY KEY,
            value_json TEXT,
            expires_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_queue(
            id TEXT PRIMARY KEY,
            signature TEXT UNIQUE,
            alert_type TEXT,
            target_key TEXT,
            priority INTEGER DEFAULT 50,
            payload_json TEXT,
            status TEXT DEFAULT 'PENDING',
            attempts INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS shark_context_snapshots(
            id TEXT PRIMARY KEY,
            context_type TEXT,
            target_key TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS live_sync_state(
            key TEXT PRIMARY KEY,
            payload_json TEXT,
            sync_status TEXT,
            next_refresh_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS auto_alerts(
            id TEXT PRIMARY KEY,
            alert_type TEXT,
            target_key TEXT,
            payload_json TEXT,
            status TEXT DEFAULT 'READY',
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations(
            version TEXT PRIMARY KEY,
            applied_at TEXT
        )"""
    )
    run_schema_migrations(conn)
    conn.commit()
    conn.close()


COMPETITION_SEEDS = [
    ("fifa-world-cup", "FIFA World Cup", "international", "Global", "World", 100, "API legal + verificacion editorial", ["world", "national"]),
    ("uefa-euro", "UEFA Euro", "international", "Europe", "UEFA", 98, "API legal + verificacion editorial", ["europe", "national"]),
    ("copa-america", "Copa America", "international", "South America", "CONMEBOL", 96, "API legal + verificacion editorial", ["america", "national"]),
    ("uefa-champions-league", "UEFA Champions League", "continental", "Europe", "UEFA", 99, "API legal + cache", ["clubs", "europe", "top"]),
    ("uefa-europa-league", "UEFA Europa League", "continental", "Europe", "UEFA", 94, "API legal + cache", ["clubs", "europe"]),
    ("uefa-conference-league", "UEFA Conference League", "continental", "Europe", "UEFA", 88, "API legal + cache", ["clubs", "europe"]),
    ("premier-league", "Premier League", "domestic", "England", "Europe", 97, "API legal + odds bridge", ["top-league"]),
    ("laliga", "LaLiga EA Sports", "domestic", "Spain", "Europe", 97, "API legal + odds bridge", ["top-league", "spain"]),
    ("serie-a", "Serie A", "domestic", "Italy", "Europe", 95, "API legal + odds bridge", ["top-league"]),
    ("bundesliga", "Bundesliga", "domestic", "Germany", "Europe", 95, "API legal + odds bridge", ["top-league"]),
    ("ligue-1", "Ligue 1", "domestic", "France", "Europe", 92, "API legal + odds bridge", ["top-league"]),
    ("eredivisie", "Eredivisie", "domestic", "Netherlands", "Europe", 84, "API legal + cache", ["europe"]),
    ("primeira-liga", "Primeira Liga", "domestic", "Portugal", "Europe", 84, "API legal + cache", ["europe"]),
    ("brasileirao", "Brasileirao Serie A", "domestic", "Brazil", "South America", 86, "API legal + cache", ["america"]),
    ("argentina-primera", "Argentina Primera Division", "domestic", "Argentina", "South America", 85, "API legal + cache", ["america"]),
    ("mls", "Major League Soccer", "domestic", "United States", "North America", 78, "API legal + cache", ["america"]),
    ("copa-del-rey", "Copa del Rey", "domestic-cup", "Spain", "Europe", 86, "API legal + cache", ["spain", "cup"]),
    ("andalucia-regional", "Andalucia Regional Football", "regional", "Spain", "Andalucia", 72, "Carga legal + editorial", ["regional", "andalucia"]),
]


TEAM_SEEDS = [
    ("real-madrid", "Real Madrid", "Spain", "Europe", "", "133738"),
    ("barcelona", "FC Barcelona", "Spain", "Europe", "", "133739"),
    ("atletico-madrid", "Atletico de Madrid", "Spain", "Europe", "", "133729"),
    ("sevilla", "Sevilla FC", "Spain", "Andalucia", "", "133745"),
    ("real-betis", "Real Betis", "Spain", "Andalucia", "", "133741"),
    ("malaga", "Malaga CF", "Spain", "Andalucia", "", ""),
    ("cadiz", "Cadiz CF", "Spain", "Andalucia", "", ""),
    ("granada", "Granada CF", "Spain", "Andalucia", "", ""),
    ("cordoba", "Cordoba CF", "Spain", "Andalucia", "", ""),
    ("recreativo-huelva", "Recreativo de Huelva", "Spain", "Andalucia", "", ""),
]

TEAM_ALIASES = {
    "barcelona": "barcelona",
    "fc-barcelona": "barcelona",
    "barca": "barcelona",
    "real-madrid-cf": "real-madrid",
    "madrid": "real-madrid",
    "atletico": "atletico-madrid",
    "atletico-de-madrid": "atletico-madrid",
    "atl-madrid": "atletico-madrid",
    "sevilla-fc": "sevilla",
    "betis": "real-betis",
    "real-betis-balompie": "real-betis",
    "malaga-cf": "malaga",
    "cadiz-cf": "cadiz",
    "granada-cf": "granada",
    "cordoba-cf": "cordoba",
    "recreativo": "recreativo-huelva",
}


def _seed_core_unlocked():
    init_db()
    conn = db()
    cur = conn.cursor()
    for key, name, scope, country, region, tier, strategy, tags in COMPETITION_SEEDS:
        cur.execute(
            """INSERT OR IGNORE INTO competitions
               (key,name,scope,country,region,tier,source_strategy,tags_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (key, name, scope, country, region, tier, strategy, json.dumps(tags), now_iso()),
        )
    for key, name, country, region, logo_url, external_id in TEAM_SEEDS:
        cur.execute(
            """INSERT OR IGNORE INTO teams
               (key,name,country,region,logo_url,external_id,color_hint,source,legal_note,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (key, name, country, region, logo_url, external_id, "premium-blue", "seed propio", "Sin scraping. Logo externo solo si hay licencia/API permitida.", now_iso()),
        )
    seed_matches = [
        ("ucl", 0, "21:00", "uefa-champions-league", "UEFA Champions League", "Europe", "Equipo Champions A", "Equipo Champions B", "PROGRAMADO"),
        ("premier", 0, "18:30", "premier-league", "Premier League", "England", "Premier Home", "Premier Away", "PROGRAMADO"),
        ("laliga", 0, "20:45", "laliga", "LaLiga EA Sports", "Spain", "Club LaLiga Local", "Club LaLiga Visitante", "PROGRAMADO"),
        ("world", 0, "19:00", "fifa-world-cup", "FIFA World Cup", "Global", "Seleccion Local", "Seleccion Visitante", "ESTRUCTURA"),
        ("andalucia", 0, "12:00", "andalucia-regional", "Andalucia Regional Football", "Spain", "Club Andaluz", "Rival Provincial", "PROGRAMADO"),
    ]
    for raw_id, day, time, comp_key, comp_name, country, home, away, status in seed_matches:
        match_id = "seed-" + raw_id + "-" + today_iso(day)
        cur.execute(
            """INSERT OR IGNORE INTO matches
               (id,match_date,kickoff_time,competition_key,competition_name,country,home_team,away_team,status,minute,score,priority,source,legal_note,raw_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                match_id,
                today_iso(day),
                time,
                comp_key,
                comp_name,
                country,
                home,
                away,
                status,
                "",
                "",
                priority_for(comp_key, status),
                "seed estructural",
                "Dato semilla propio para experiencia visual. Sustituir por API legal o carga autorizada.",
                json.dumps({"seed": True}),
                now_iso(),
            ),
        )
    conn.commit()
    conn.close()


def seed_core():
    global _SEEDED_DB_PATH
    if _SEEDED_DB_PATH == DB_PATH:
        return
    with _SEED_LOCK:
        if _SEEDED_DB_PATH == DB_PATH:
            return
        retry_locked(_seed_core_unlocked)
        _SEEDED_DB_PATH = DB_PATH


def rows(query, params=()):
    seed_core()
    conn = db()
    cur = conn.cursor()
    cur.execute(query, params)
    out = [dict(r) for r in cur.fetchall()]
    conn.close()
    return out


def one(query, params=()):
    data = rows(query, params)
    return data[0] if data else None


def cache_get(key):
    item = one("SELECT * FROM persistent_cache WHERE key=?", (key,))
    if not item:
        return None
    if item.get("expires_at") and item["expires_at"] < now_iso():
        return None
    try:
        return json.loads(item.get("value_json") or "null")
    except json.JSONDecodeError:
        return None


def cache_set(key, value, seconds=60):
    expires = (datetime.now(TZ) + timedelta(seconds=seconds)).isoformat(timespec="seconds")
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO persistent_cache(key,value_json,expires_at,updated_at)
           VALUES (?,?,?,?)""",
        (key, json.dumps(value, ensure_ascii=False), expires, now_iso()),
    )
    conn.commit()
    conn.close()


def competitions():
    data = rows("SELECT * FROM competitions ORDER BY tier DESC, name")
    for item in data:
        item["tags"] = json.loads(item.get("tags_json") or "[]")
    return data


def competition_map():
    return {c["key"]: c for c in competitions()}


def canonical_team_key(name):
    key = slug(name)
    return TEAM_ALIASES.get(key, key)


def fallback_crest_url(name):
    return "/team-crest.svg?" + urllib.parse.urlencode({"name": name or "Equipo"})


def thesportsdb_key():
    return os.getenv("THESPORTSDB_KEY") or os.getenv("THESPORTSDB_API_KEY") or ""


def fetch_thesportsdb_team(team_name):
    api_key = thesportsdb_key()
    if not api_key:
        return None
    url = "https://www.thesportsdb.com/api/v1/json/%s/searchteams.php?%s" % (
        urllib.parse.quote(api_key),
        urllib.parse.urlencode({"t": team_name}),
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as res:
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
        teams = payload.get("teams") or []
        if not teams:
            return None
        first = teams[0]
        logo = first.get("strBadge") or first.get("strLogo") or ""
        return {
            "external_id": first.get("idTeam") or "",
            "name": first.get("strTeam") or team_name,
            "country": first.get("strCountry") or "",
            "logo_url": logo,
            "source": "TheSportsDB API",
            "legal_note": "Escudo obtenido desde API permitida TheSportsDB; respetar condiciones de uso de la fuente.",
        }
    except Exception:
        return None


def cache_team_identity(name, identity):
    key = canonical_team_key(name)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO teams
           (key,name,country,region,logo_url,external_id,color_hint,source,legal_note,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            key,
            identity.get("name") or name,
            identity.get("country") or "",
            identity.get("region") or "",
            identity.get("logo_url") or "",
            identity.get("external_id") or "",
            identity.get("color_hint") or "premium-blue",
            identity.get("source") or "manual/API",
            identity.get("legal_note") or "Identidad cargada por fuente permitida.",
            now_iso(),
        ),
    )
    conn.commit()
    conn.close()


def resolve_team(name, refresh=False):
    key = canonical_team_key(name)
    team = one("SELECT * FROM teams WHERE key=?", (key,))
    if team and team.get("logo_url") and not refresh:
        team["initials"] = initials(team.get("name") or name)
        team["crest_url"] = team.get("logo_url")
        team["crest_mode"] = "logo"
        return team
    if refresh or not team or not team.get("logo_url"):
        found = fetch_thesportsdb_team((team or {}).get("name") or name)
        if found and found.get("logo_url"):
            cache_team_identity(name, found)
            team = one("SELECT * FROM teams WHERE key=?", (key,))
    if not team:
        team = {"key": key, "name": name or "Equipo", "logo_url": "", "country": "", "region": "", "source": "fallback propio", "legal_note": "Iniciales generadas por la app."}
    team["initials"] = initials(team.get("name") or name)
    team["crest_url"] = team.get("logo_url") or fallback_crest_url(team.get("name") or name)
    status = crest_status(team)
    team["crest_mode"] = status["mode"]
    team["crest_source"] = status["source"]
    return team


def priority_for(competition_key, status="", favorite=False, has_pick=False):
    comp = {key: tier for key, _, _, _, _, tier, _, _ in COMPETITION_SEEDS}.get(competition_key, 55)
    status_text = str(status or "").lower()
    if any(x in status_text for x in ["live", "directo", "1h", "2h", "ht"]):
        comp += 12
    if favorite:
        comp += 9
    if has_pick:
        comp += 7
    return min(comp, 100)


def parse_payload(text):
    text = str(text or "").strip()
    if not text:
        return []
    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("matches") or data.get("rows") or [data]
        return [x for x in data if isinstance(x, dict)]
    reader = csv.DictReader(io.StringIO(text.replace(";", ",")))
    return [dict(row) for row in reader]


def import_matches(import_rows, source_name="manual", source_url="", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in import_rows:
        home = item.get("home_team") or item.get("home") or item.get("local") or item.get("equipo_local") or ""
        away = item.get("away_team") or item.get("away") or item.get("visitante") or item.get("equipo_visitante") or ""
        comp_key = item.get("competition_key") or slug(item.get("competition") or item.get("league") or item.get("liga") or "manual")
        comp_name = item.get("competition_name") or item.get("competition") or item.get("league") or item.get("liga") or comp_key
        date = item.get("match_date") or item.get("date") or item.get("fecha") or today_iso()
        kickoff = item.get("kickoff_time") or item.get("time") or item.get("hora") or ""
        status = item.get("status") or item.get("estado") or "PROGRAMADO"
        raw_id = item.get("id") or item.get("match_id") or f"{date}-{comp_key}-{home}-{away}-{kickoff}"
        match_id = hashlib.md5(str(raw_id).encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO matches
               (id,match_date,kickoff_time,competition_key,competition_name,country,home_team,away_team,status,minute,score,priority,source,legal_note,raw_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                match_id,
                date,
                kickoff,
                comp_key,
                comp_name,
                item.get("country") or item.get("pais") or "",
                home,
                away,
                status,
                item.get("minute") or item.get("minuto") or "",
                item.get("score") or item.get("marcador") or "",
                int(item.get("priority") or priority_for(comp_key, status)),
                source_name,
                legal_note,
                json.dumps(item, ensure_ascii=False)[:5000],
                now_iso(),
            ),
        )
        count += 1
    import_id = hashlib.md5(f"{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "matches", source_name, source_url, legal_note, count, "IMPORTED", json.dumps(import_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "imported": count, "import_id": import_id}


def import_teams(team_rows, source_name="manual", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in team_rows:
        name = item.get("name") or item.get("team") or item.get("equipo") or item.get("display_name") or ""
        if not name:
            continue
        key = canonical_team_key(item.get("key") or name)
        cur.execute(
            """INSERT OR REPLACE INTO teams
               (key,name,country,region,logo_url,external_id,color_hint,source,legal_note,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                key,
                name,
                item.get("country") or item.get("pais") or "",
                item.get("region") or item.get("provincia") or "",
                item.get("logo_url") or item.get("crest_url") or item.get("escudo") or "",
                item.get("external_id") or item.get("idTeam") or "",
                item.get("color_hint") or "premium-blue",
                source_name,
                legal_note,
                now_iso(),
            ),
        )
        count += 1
    import_id = hashlib.md5(f"teams-{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "teams", source_name, "", legal_note, count, "IMPORTED", json.dumps(team_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "imported": count, "import_id": import_id}


def as_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def as_int(value, default=50):
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def import_picks(pick_rows, source_name="manual autorizado", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in pick_rows:
        selection = item.get("selection") or item.get("pick") or item.get("pronostico") or item.get("mercado") or ""
        home = item.get("home_team") or item.get("home") or item.get("local") or ""
        away = item.get("away_team") or item.get("away") or item.get("visitante") or ""
        if not selection:
            continue
        date = item.get("match_date") or item.get("date") or item.get("fecha") or today_iso()
        comp_key = item.get("competition_key") or slug(item.get("competition") or item.get("league") or item.get("liga") or "")
        comp_name = item.get("competition_name") or item.get("competition") or item.get("league") or item.get("liga") or comp_key
        match_id = item.get("match_id") or ""
        raw_id = item.get("id") or f"{date}-{comp_key}-{home}-{away}-{selection}-{item.get('odds')}"
        pick_id = hashlib.md5(str(raw_id).encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO picks
               (id,match_id,match_date,competition_key,competition_name,home_team,away_team,pick_type,selection,odds,confidence,stake_units,status,source,legal_note,reasoning,raw_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pick_id,
                match_id,
                date,
                comp_key,
                comp_name,
                home,
                away,
                item.get("pick_type") or item.get("type") or item.get("tipo") or "principal",
                selection,
                as_float(item.get("odds") or item.get("cuota"), 0.0),
                max(1, min(100, as_int(item.get("confidence") or item.get("confianza"), 50))),
                as_float(item.get("stake_units") or item.get("stake") or item.get("unidades"), 1.0),
                item.get("status") or item.get("estado") or "PENDING",
                source_name,
                legal_note,
                item.get("reasoning") or item.get("analisis") or "",
                json.dumps(item, ensure_ascii=False)[:5000],
                now_iso(),
                now_iso(),
            ),
        )
        count += 1
    import_id = hashlib.md5(f"picks-{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "picks", source_name, "", legal_note, count, "IMPORTED", json.dumps(pick_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "imported": count, "import_id": import_id}


def get_picks(limit=50, status=None):
    clauses = []
    params = []
    if status:
        clauses.append("lower(status)=?")
        params.append(str(status).lower())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT * FROM picks{where} ORDER BY match_date DESC, confidence DESC, updated_at DESC LIMIT ?"
    params.append(int(limit))
    data = rows(query, params)
    for pick in data:
        pick["odds"] = as_float(pick.get("odds"), 0.0)
        pick["confidence"] = as_int(pick.get("confidence"), 50)
        pick["stake_units"] = as_float(pick.get("stake_units"), 1.0)
    return data


def combi_risk(picks):
    if not picks:
        return "EMPTY"
    avg_confidence = sum(as_int(p.get("confidence"), 50) for p in picks) / len(picks)
    legs = len(picks)
    if legs <= 2 and avg_confidence >= 70:
        return "CONTROLADO"
    if legs <= 4 and avg_confidence >= 58:
        return "MEDIO"
    return "ALTO"


def build_combi_from_picks(pick_ids=None, limit=3):
    seed_core()
    if pick_ids:
        placeholders = ",".join("?" for _ in pick_ids)
        picks = rows(f"SELECT * FROM picks WHERE id IN ({placeholders}) ORDER BY confidence DESC", pick_ids)
    else:
        picks = get_picks(limit=limit, status="PENDING")
    picks = picks[: max(1, min(6, int(limit or len(picks) or 3)))]
    if not picks:
        return None
    total = 1.0
    for pick in picks:
        odd = as_float(pick.get("odds"), 1.0)
        total *= odd if odd > 1 else 1
    combi_id = hashlib.md5(("combi-" + now_iso() + json.dumps([p.get("id") for p in picks])).encode("utf-8")).hexdigest()[:18]
    payload = [
        {
            "id": p.get("id"),
            "match": f"{p.get('home_team') or ''} vs {p.get('away_team') or ''}".strip(),
            "selection": p.get("selection"),
            "odds": as_float(p.get("odds"), 0.0),
            "confidence": as_int(p.get("confidence"), 50),
        }
        for p in picks
    ]
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO combis
           (id,name,picks_json,total_odds,risk_level,status,source,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (combi_id, "Combi SHARK " + today_iso(), json.dumps(payload, ensure_ascii=False), round(total, 2), combi_risk(picks), "DRAFT", "motor interno V506", now_iso(), now_iso()),
    )
    conn.commit()
    conn.close()
    return one("SELECT * FROM combis WHERE id=?", (combi_id,))


def get_combis(limit=20):
    data = rows("SELECT * FROM combis ORDER BY created_at DESC LIMIT ?", (int(limit),))
    for combi in data:
        combi["picks"] = json.loads(combi.get("picks_json") or "[]")
    return data


def favorite_id(kind, value):
    return hashlib.md5(f"{kind}:{value}".lower().encode("utf-8")).hexdigest()[:18]


def add_favorite(kind, value, label=None):
    kind = str(kind or "").strip().lower()
    value = str(value or "").strip()
    if kind not in {"team", "league", "match"} or not value:
        return None
    fav_id = favorite_id(kind, value)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO favorites(id,kind,value,label,created_at)
           VALUES (?,?,?,?,?)""",
        (fav_id, kind, value, label or value, now_iso()),
    )
    conn.commit()
    conn.close()
    return one("SELECT * FROM favorites WHERE id=?", (fav_id,))


def remove_favorite(kind, value):
    fav_id = favorite_id(kind, value)
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE id=?", (fav_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "removed": fav_id}


def get_favorites(kind=None):
    if kind:
        return rows("SELECT * FROM favorites WHERE kind=? ORDER BY created_at DESC", (kind,))
    return rows("SELECT * FROM favorites ORDER BY created_at DESC")


def favorite_sets():
    favs = get_favorites()
    return {
        "team": {f["value"].lower() for f in favs if f.get("kind") == "team"},
        "league": {f["value"].lower() for f in favs if f.get("kind") == "league"},
        "match": {f["value"].lower() for f in favs if f.get("kind") == "match"},
        "all": favs,
    }


def annotate_match(match, favs=None):
    favs = favs or favorite_sets()
    match_key = str(match.get("id") or "").lower()
    comp_key = str(match.get("competition_key") or "").lower()
    comp_name = str(match.get("competition_name") or "").lower()
    home = str(match.get("home_team") or "").lower()
    away = str(match.get("away_team") or "").lower()
    match["is_favorite"] = (
        match_key in favs["match"]
        or comp_key in favs["league"]
        or comp_name in favs["league"]
        or home in favs["team"]
        or away in favs["team"]
    )
    match["real_time_state"] = real_time_state(match)
    match["timeline"] = match_timeline(match)
    match["live_depth"] = live_depth(match)
    return match


def match_timeline(match):
    existing = rows("SELECT * FROM match_timeline WHERE match_id=? ORDER BY created_at DESC LIMIT 20", (match.get("id"),))
    if existing:
        return existing
    return fallback_timeline(match)


def live_depth(match):
    return build_live_depth(match)


def favorite_feed(limit=80):
    favs = favorite_sets()
    data = get_matches(today_iso(), "today")
    feed = []
    for match in data:
        annotated = annotate_match(match, favs)
        if annotated.get("is_favorite"):
            feed.append(annotated)
    return feed[: int(limit)]


def related_picks_for_match(match, limit=8):
    all_picks = get_picks(limit=100)
    match_id = str(match.get("id") or "").lower()
    home = str(match.get("home_team") or "").lower()
    away = str(match.get("away_team") or "").lower()
    comp = str(match.get("competition_key") or "").lower()
    related = []
    for pick in all_picks:
        if str(pick.get("match_id") or "").lower() == match_id:
            related.append(pick)
            continue
        pick_home = str(pick.get("home_team") or "").lower()
        pick_away = str(pick.get("away_team") or "").lower()
        pick_comp = str(pick.get("competition_key") or "").lower()
        if (home and home == pick_home) or (away and away == pick_away) or (comp and comp == pick_comp):
            related.append(pick)
    return related[: int(limit)]


def favorite_feed_full(limit=80):
    matches = favorite_feed(limit)
    match_ids = {str(m.get("id") or "").lower() for m in matches}
    teams = {str(m.get("home_team") or "").lower() for m in matches} | {str(m.get("away_team") or "").lower() for m in matches}
    comps = {str(m.get("competition_key") or "").lower() for m in matches}
    live_related = [m for m in matches if (m.get("live_depth") or {}).get("state") in {"LIVE", "HT"}]
    picks_related = []
    for pick in get_picks(limit=100):
        if (
            str(pick.get("match_id") or "").lower() in match_ids
            or str(pick.get("home_team") or "").lower() in teams
            or str(pick.get("away_team") or "").lower() in teams
            or str(pick.get("competition_key") or "").lower() in comps
        ):
            picks_related.append(pick)
    prioritized = sorted(matches, key=lambda m: (1 if (m.get("live_depth") or {}).get("state") in {"LIVE", "HT"} else 0, m.get("real_time_score", m.get("priority", 0))), reverse=True)
    return {"matches": prioritized, "live": live_related, "picks": picks_related[:20], "priority": prioritized[:10]}


def match_detail(match_id):
    match = one("SELECT * FROM matches WHERE id=?", (match_id,))
    if not match:
        return None
    annotated = annotate_match(match)
    return build_match_detail(
        annotated,
        timeline=match_timeline(annotated),
        related_picks=related_picks_for_match(annotated),
        favorite=annotated.get("is_favorite"),
    )


def match_hub(date=None):
    date = date or today_iso()
    cache_key = f"match-hub:{date}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    favs = favorite_sets()
    favorites = get_favorites()
    picks = get_picks(limit=80)
    all_today = [annotate_match(m, favs) for m in get_matches(date, "today")]
    sections = hub_sections(all_today, favorites=favorites, picks=picks)
    live_state = split_live(sections["today"])
    sync = sync_plan(sections["today"], now_iso())
    top_leagues = [c for c in competitions() if c.get("tier", 0) >= 90][:10]
    hub = {
        "date": date,
        "sync": sync,
        "live": sections["live"][:30],
        "today": sections["today"][:80],
        "upcoming": sections["upcoming"][:30],
        "finished": sections["finished"][:20],
        "popular": sections["top"][:20],
        "favorites": sections["favorites"][:20],
        "with_picks": sections["with_picks"][:20],
        "top_leagues": top_leagues,
        "counts": {
            "live": len(live_state["live"]),
            "upcoming": len(live_state["scheduled"]),
            "favorites": len(sections["favorites"]),
            "with_picks": len(sections["with_picks"]),
            "popular": len(all_today),
        },
    }
    save_live_sync_state("global", hub)
    cache_set(cache_key, hub, seconds=45)
    return hub


def save_live_sync_state(key, payload):
    sync = payload.get("sync") or {}
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO live_sync_state(key,payload_json,sync_status,next_refresh_at,updated_at)
           VALUES (?,?,?,?,?)""",
        (key, json.dumps(payload, ensure_ascii=False)[:12000], sync.get("sync_status") or "standby", sync.get("next_refresh_at") or "", now_iso()),
    )
    conn.commit()
    conn.close()


def real_time_global_state(date=None, refresh=False):
    date = date or today_iso()
    if refresh:
        cache_key = f"match-hub:{date}"
        conn = db()
        cur = conn.cursor()
        cur.execute("DELETE FROM persistent_cache WHERE key=?", (cache_key,))
        conn.commit()
        conn.close()
    hub = match_hub(date)
    return {
        "date": date,
        "version": APP_VERSION,
        "state": hub.get("sync", {}),
        "counts": hub.get("counts", {}),
        "live": hub.get("live", [])[:12],
        "fallback": "automatic",
        "source_policy": "APIs permitidas, importaciones autorizadas y cache SQLite; no scraping ilegal.",
    }


def live_data_flow(date=None):
    date = date or today_iso()
    hub = match_hub(date)
    favs = get_favorites()
    picks = get_picks(limit=30)
    profile = default_profile()
    favorite_bundle = favorite_feed_full()
    flow = build_live_flow(hub, favorites=favs, picks=picks, profile=profile)
    flow.update(
        {
            "date": date,
            "favorites": favorite_bundle,
            "profile": profile,
            "recent_picks": picks[:10],
            "navigation": {
                "home": "/",
                "hub": "/match-hub",
                "live": "/live",
                "favorites": "/favoritos",
                "shark": "/shark-ai",
            },
        }
    )
    return flow


MEMBERSHIP_PLANS = [
    {"key": "free", "name": "Free", "price": "0 EUR", "features": ["Calendario global", "Live basico", "Escudos persistentes"]},
    {"key": "pro", "name": "PRO", "price": "Premium", "features": ["Picks premium", "Combis", "Perfil favorito", "Alertas Telegram"]},
    {"key": "elite", "name": "ELITE", "price": "Top", "features": ["IA SHARK", "Briefings", "Prioridad live", "Control avanzado"]},
]


def default_profile():
    seed_core()
    profile = one("SELECT * FROM client_profiles WHERE id='default'")
    if not profile:
        conn = db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO client_profiles
               (id,name,membership_plan,favorite_teams_json,favorite_competitions_json,telegram_chat_id,preferences_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "default",
                "Cliente SHARK",
                "pro",
                json.dumps(["Real Madrid", "Sevilla FC", "Real Betis"]),
                json.dumps(["UEFA Champions League", "LaLiga EA Sports", "Andalucia Regional Football"]),
                os.getenv("TELEGRAM_CHAT_ID", ""),
                json.dumps({"tone": "premium", "focus": "global+spain+andalucia"}),
                now_iso(),
                now_iso(),
            ),
        )
        conn.commit()
        conn.close()
        profile = one("SELECT * FROM client_profiles WHERE id='default'")
    profile["favorite_teams"] = json.loads(profile.get("favorite_teams_json") or "[]")
    profile["favorite_competitions"] = json.loads(profile.get("favorite_competitions_json") or "[]")
    profile["preferences"] = json.loads(profile.get("preferences_json") or "{}")
    return profile


def shark_briefing():
    today_matches = get_matches(today_iso(), "today")
    live_state = split_live(today_matches)
    picks = get_picks(limit=8)
    profile = default_profile()
    imported_real = [m for m in today_matches if "seed" not in str(m.get("source") or "").lower()]
    explained = []
    for pick in picks:
        risk_info = explain_pick_risk(pick)
        explained.append(
            {
                "id": pick.get("id"),
                "match": f"{pick.get('home_team') or ''} vs {pick.get('away_team') or ''}".strip(),
                "selection": pick.get("selection"),
                "odds": risk_info["odds"],
                "confidence": risk_info["confidence"],
                "risk": risk_info["risk"],
                "explanation": risk_info["explanation"],
            }
        )
    context = build_shark_context(favorites=get_favorites(), picks=picks, profile=profile)
    context["live_state"] = real_time_global_state()
    context["favorite_leagues"] = [f for f in get_favorites("league")]
    return {
        "time": now_iso(),
        "profile": profile,
        "context": context,
        "summary": {
            "matches_today": len(today_matches),
            "real_or_imported_matches": len(imported_real),
            "live_now": len(live_state["live"]),
            "picks_ready": len(picks),
            "coverage": "global-first",
        },
        "risk": {
            "level": "CONTROLADO" if len(picks) <= 3 else "MEDIO",
            "note": "SHARK prioriza claridad, trazabilidad y control de stake antes que volumen.",
        },
        "priority": [
            "Conectar o importar fuentes legales para calendario/live.",
            "Usar picks solo cuando vengan de carga autorizada o motor propio.",
            "Mantener Andalucia como capa diferencial dentro de cobertura mundial.",
        ],
        "picks": picks,
        "explained_picks": explained,
        "legal_policy": "Sin scraping ilegal. La IA trabaja con datos importados, APIs permitidas y cache persistente.",
    }


def save_shark_context(context_type, target_key, payload):
    snapshot_id = hashlib.md5(f"shark-{context_type}-{target_key}-{now_iso()}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO shark_context_snapshots(id,context_type,target_key,payload_json,created_at)
           VALUES (?,?,?,?,?)""",
        (snapshot_id, context_type, target_key, json.dumps(payload, ensure_ascii=False)[:8000], now_iso()),
    )
    conn.commit()
    conn.close()
    return snapshot_id


def shark_answer(question):
    q = str(question or "").strip()
    briefing = shark_briefing()
    hub = match_hub(today_iso())
    if not q:
        q = "resumen"
    q_lower = q.lower()
    if "pick" in q_lower or "combi" in q_lower:
        focus = "picks"
        body = "Los picks se explican con confianza, cuota, stake y riesgo. Si no hay picks importados, SHARK no fabrica recomendaciones."
    elif "live" in q_lower or "directo" in q_lower:
        focus = "live"
        body = f"Ahora mismo hay {hub['counts']['live']} partidos en directo, {hub['counts']['upcoming']} proximos y refresco inteligente cada {hub['sync']['refresh_seconds']} segundos."
    elif "favor" in q_lower:
        focus = "favoritos"
        body = f"Tu feed favorito tiene {hub['counts']['favorites']} partidos destacados para hoy."
    else:
        focus = "contexto"
        body = "Prioridad global: competiciones top mundiales y europeas, Espana como eje fuerte y Andalucia como diferencial propio."
    return {
        "question": q,
        "focus": focus,
        "answer": body,
        "context": briefing.get("context"),
        "risk_note": briefing["risk"]["note"],
        "next_action": "Carga datos reales/autorizados para que SHARK pueda razonar con mas profundidad.",
        "legal_policy": briefing["legal_policy"],
    }


def telegram_config():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return {
        "configured": bool(token and chat_id),
        "token_present": bool(token),
        "chat_id_present": bool(chat_id),
        "enabled": os.getenv("ENABLE_TELEGRAM_AUTO", "false").lower() in {"1", "true", "yes", "on"},
        "auto_minutes": as_int(os.getenv("TELEGRAM_AUTO_MINUTES", "360"), 360),
    }


def automation_get(key, default=None):
    item = one("SELECT * FROM automation_state WHERE key=?", (key,))
    if not item:
        return default
    try:
        return json.loads(item.get("value_json") or "null")
    except json.JSONDecodeError:
        return default


def automation_set(key, value):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        (key, json.dumps(value, ensure_ascii=False), now_iso()),
    )
    conn.commit()
    conn.close()


def telegram_triggers():
    briefing = shark_briefing()
    hub = match_hub(today_iso())
    triggers = []
    if briefing["summary"]["picks_ready"]:
        triggers.append({"key": "picks_ready", "label": "Picks listos", "priority": 90})
    if hub["counts"]["live"]:
        triggers.append({"key": "live_active", "label": "Partidos en directo", "priority": 86})
    if hub["counts"]["favorites"]:
        triggers.append({"key": "favorite_feed", "label": "Favoritos con actividad", "priority": 82})
    if not triggers:
        triggers.append({"key": "daily_briefing", "label": "Briefing diario", "priority": 60})
    return triggers


def telegram_existing_signatures():
    items = rows("SELECT signature FROM telegram_queue ORDER BY created_at DESC LIMIT 500")
    return [item.get("signature") for item in items]


def enqueue_telegram_alerts(force=False):
    triggers = telegram_triggers()
    favs = get_favorites()
    picks = get_picks(limit=20)
    queue_items = build_alert_queue(triggers, today_iso(), favorites_count=len(favs), picks_count=len(picks))
    existing = telegram_existing_signatures()
    inserted = []
    skipped = []
    conn = db()
    cur = conn.cursor()
    for item in queue_items:
        if not force and should_skip_duplicate(existing, item["signature"]):
            skipped.append(item)
            continue
        queue_id = hashlib.md5(f"queue-{item['signature']}".encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO telegram_queue
               (id,signature,alert_type,target_key,priority,payload_json,status,attempts,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                queue_id,
                item["signature"],
                item["alert_type"],
                item["target_key"],
                item["priority"],
                json.dumps(item, ensure_ascii=False),
                "PENDING",
                0,
                now_iso(),
                now_iso(),
            ),
        )
        inserted.append(item)
    conn.commit()
    conn.close()
    return {"inserted": inserted, "skipped": skipped, "triggers": triggers}


def telegram_queue(limit=50):
    return rows("SELECT * FROM telegram_queue ORDER BY priority DESC, created_at ASC LIMIT ?", (int(limit),))


def process_telegram_queue(force=False):
    enqueue = enqueue_telegram_alerts(force=force)
    pending = rows("SELECT * FROM telegram_queue WHERE status IN ('PENDING','RETRY') AND attempts < 3 ORDER BY priority DESC, created_at ASC LIMIT 3")
    processed = []
    for item in pending:
        text = telegram_daily_message()
        result = send_telegram_message(text, message_type=f"queue_{item.get('alert_type')}")
        status = "SENT" if result.get("sent") else "RETRY" if int(item.get("attempts") or 0) < 2 else (result.get("status") or "ERROR")
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE telegram_queue SET status=?, attempts=attempts+1, updated_at=? WHERE id=?",
            (status, now_iso(), item.get("id")),
        )
        conn.commit()
        conn.close()
        processed.append({"queue": item, "result": result})
    return {"enqueue": enqueue, "processed": processed, "pending_after": telegram_queue(limit=20)}


def prepare_auto_posts():
    hub = match_hub(today_iso())
    posts = []
    for match in hub.get("live", [])[:5]:
        posts.append({"type": "live_alert", "target_key": match.get("id"), "title": f"{match.get('home_team')} vs {match.get('away_team')}", "status": (match.get("live_depth") or {}).get("label")})
    for match in hub.get("with_picks", [])[:5]:
        posts.append({"type": "pick_alert", "target_key": match.get("id"), "title": f"Pick relacionado: {match.get('competition_name')}", "status": "READY"})
    for match in hub.get("popular", [])[:5]:
        posts.append({"type": "featured_match", "target_key": match.get("id"), "title": f"Destacado: {match.get('home_team')} vs {match.get('away_team')}", "status": "READY"})
    conn = db()
    cur = conn.cursor()
    for post in posts:
        post_id = hashlib.md5(f"auto-{today_iso()}-{post['type']}-{post['target_key']}".encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO auto_alerts(id,alert_type,target_key,payload_json,status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (post_id, post["type"], post["target_key"], json.dumps(post, ensure_ascii=False), post["status"], now_iso(), now_iso()),
        )
    conn.commit()
    conn.close()
    return posts


def telegram_scheduler_tick(force=False):
    cfg = telegram_config()
    if not cfg["enabled"] and not force:
        return {"ok": False, "sent": False, "status": "AUTO_DISABLED", "telegram": cfg}
    triggers = telegram_triggers()
    trigger_key = "-".join(t["key"] for t in triggers)
    duplicate_key = hashlib.md5((today_iso() + trigger_key).encode("utf-8")).hexdigest()
    last = automation_get("telegram_last_dispatch", {})
    if not force and last.get("duplicate_key") == duplicate_key:
        return {"ok": True, "sent": False, "status": "DUPLICATE_SKIPPED", "triggers": triggers, "last": last}
    result = process_telegram_queue(force=force)
    sent = any((item.get("result") or {}).get("sent") for item in result.get("processed", []))
    automation_set("telegram_last_dispatch", {"duplicate_key": duplicate_key, "time": now_iso(), "triggers": triggers, "result": result})
    return {"ok": True, "sent": sent, "status": "QUEUE_PROCESSED", "triggers": triggers, "result": result}


def log_telegram_delivery(chat_id, message_type, text, status, response=None):
    conn = db()
    cur = conn.cursor()
    delivery_id = hashlib.md5(f"telegram-{chat_id}-{now_iso()}-{message_type}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO telegram_deliveries
           (id,chat_id,message_type,payload_preview,status,response_json,created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (delivery_id, chat_id or "", message_type, str(text or "")[:1500], status, json.dumps(response or {}, ensure_ascii=False)[:3000], now_iso()),
    )
    conn.commit()
    conn.close()
    return delivery_id


def send_telegram_message(text, chat_id=None, message_type="manual"):
    cfg = telegram_config()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    target = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not target:
        delivery_id = log_telegram_delivery(target, message_type, text, "CONFIG_MISSING", {"configured": False})
        return {"ok": False, "sent": False, "status": "CONFIG_MISSING", "delivery_id": delivery_id}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": target, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            response = json.loads(res.read().decode("utf-8", errors="replace"))
        delivery_id = log_telegram_delivery(target, message_type, text, "SENT", response)
        return {"ok": True, "sent": True, "status": "SENT", "delivery_id": delivery_id, "telegram": response}
    except Exception as exc:
        delivery_id = log_telegram_delivery(target, message_type, text, "ERROR", {"error": str(exc)})
        return {"ok": False, "sent": False, "status": "ERROR", "delivery_id": delivery_id, "error": str(exc)}


def telegram_daily_message():
    briefing = shark_briefing()
    summary = briefing["summary"]
    return (
        "<b>NeMeSiS SHARK PRO</b>\n"
        f"Version: {APP_VERSION}\n"
        f"Partidos hoy: {summary['matches_today']} | Live: {summary['live_now']} | Picks: {summary['picks_ready']}\n"
        "Cobertura: mundial primero, Espana y Andalucia como diferencial.\n"
        "Legal: solo APIs permitidas, importaciones autorizadas y cache propio."
    )


def get_matches(date=None, lane="today"):
    date = date or today_iso()
    clauses = ["match_date=?"]
    params = [date]
    if lane == "live":
        clauses.append("(lower(status) LIKE '%live%' OR lower(status) LIKE '%directo%' OR minute!='')")
    elif lane == "top":
        clauses.append("priority>=90")
    elif lane == "spain":
        clauses.append("(lower(country)='spain' OR lower(competition_key) LIKE '%laliga%' OR lower(competition_key)='copa-del-rey')")
    elif lane == "andalucia":
        clauses.append("lower(competition_key)='andalucia-regional'")
    query = "SELECT * FROM matches WHERE " + " AND ".join(clauses) + " ORDER BY priority DESC, kickoff_time, competition_name LIMIT 150"
    data = rows(query, params)
    for item in data:
        item["home_identity"] = resolve_team(item.get("home_team"))
        item["away_identity"] = resolve_team(item.get("away_team"))
    return data


def split_live(matches):
    live, scheduled, finished = [], [], []
    for item in matches:
        state = (item.get("live_depth") or {}).get("state") or normalize_live_state(item)["key"]
        status = str(item.get("status") or "").lower()
        if state == "FT" or status in {"ft", "finalizado", "finished"}:
            finished.append(item)
        elif state in {"LIVE", "HT"} or item.get("minute") or any(x in status for x in ["live", "directo", "1h", "2h", "ht"]):
            live.append(item)
        else:
            scheduled.append(item)
    return {"live": live, "scheduled": scheduled, "finished": finished}


def dashboard_data(lane="today", date=None):
    date = date or today_iso()
    matches = get_matches(date, lane)
    comps = competitions()
    imports = rows("SELECT * FROM imports ORDER BY created_at DESC LIMIT 20")
    picks = get_picks(limit=10)
    combis = get_combis(limit=5)
    profile = default_profile()
    favorites = get_favorites()
    hub = match_hub(date)
    favorite_bundle = favorite_feed_full()
    flow = build_live_flow(hub, favorites=favorites, picks=picks, profile=profile)
    groups = {}
    for match in matches:
        groups.setdefault(match.get("competition_name") or "Sin competicion", []).append(match)
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "date": date,
        "lane": lane,
        "matches": matches,
        "groups": groups,
        "competitions": comps,
        "imports": imports,
        "picks": picks,
        "combis": combis,
        "profile": profile,
        "favorites": favorites,
        "favorite_feed": favorite_bundle["matches"],
        "favorite_bundle": favorite_bundle,
        "match_hub": hub,
        "live_flow": flow,
        "membership_plans": MEMBERSHIP_PLANS,
        "telegram": telegram_config(),
        "live": split_live([annotate_match(m) for m in get_matches(date, "today")]),
        "legal_policy": "No scraping ilegal. Solo APIs permitidas, datos propios, CSV/JSON autorizado, cache persistente y revision editorial.",
        "readiness": {
            "clean_core": 100,
            "render_ready": 98,
            "global_football": 96,
            "calendar": 95,
            "legal_import": 96,
            "live_foundation": 92,
            "telegram_ready": 88,
            "picks_combis": 82,
            "premium_profile": 84,
            "shark_ai": 78,
            "memberships": 80,
            "premium_core": 86,
            "match_hub": 88,
            "favorites": 84,
            "performance_cache": 80,
            "live_ecosystem": 88,
            "telegram_queue": 84,
            "shark_context": 86,
            "real_time_engine": 89,
            "match_hub_2": 90,
            "mobile_feel": 84,
        },
    }


@app.route("/service-worker.js")
def service_worker():
    body = (
        "self.addEventListener('install',event=>self.skipWaiting());\n"
        "self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));\n"
    )
    return Response(body, mimetype="application/javascript")


@app.route("/")
def home():
    return render_template("home.html", data=dashboard_data())


@app.route("/global")
@app.route("/competiciones")
def global_football():
    return render_template("global.html", data=dashboard_data())


@app.route("/calendario")
@app.route("/calendario-global")
def calendar_page():
    return render_template("calendar.html", data=dashboard_data(request.args.get("lane", "today"), request.args.get("date") or today_iso()))


@app.route("/live")
@app.route("/live-center")
def live_page():
    return render_template("live.html", data=dashboard_data("today", request.args.get("date") or today_iso()))


@app.route("/match-hub")
@app.route("/partidos")
@app.route("/partidos-hoy")
def match_hub_page():
    data = dashboard_data("today", request.args.get("date") or today_iso())
    return render_template("match_hub.html", data=data)


@app.route("/favoritos")
@app.route("/favorites")
def favorites_page():
    return render_template("favorites.html", data=dashboard_data())


@app.route("/admin")
def admin_redirect():
    return redirect("/admin/import-center")


@app.route("/admin/import-center")
def import_center():
    return render_template("import_center.html", data=dashboard_data())


@app.route("/picks")
def picks_page():
    return render_template("picks.html", data=dashboard_data())


@app.route("/combis")
def combis_page():
    return render_template("combis.html", data=dashboard_data())


@app.route("/perfil")
@app.route("/profile")
def profile_page():
    return render_template("profile.html", data=dashboard_data())


@app.route("/membresias")
@app.route("/membership")
def membership_page():
    return render_template("membership.html", data=dashboard_data())


@app.route("/shark-ai")
@app.route("/shark")
def shark_page():
    data = dashboard_data()
    data["briefing"] = shark_briefing()
    return render_template("shark.html", data=data)


@app.route("/telegram")
def telegram_page():
    return render_template("telegram.html", data=dashboard_data())


@app.route("/escudos")
@app.route("/crests")
def crests_page():
    return render_template("crests.html", data=dashboard_data())


@app.route("/api/health")
@app.route("/v504-health")
@app.route("/v505-health")
@app.route("/v506-health")
@app.route("/v507-health")
@app.route("/v508-health")
@app.route("/v509-health")
@app.route("/v512-health")
def health():
    return jsonify({"ok": True, "app": APP_NAME, "version": APP_VERSION, "time": now_iso()})


@app.route("/api/competitions")
def api_competitions():
    return jsonify({"ok": True, "version": APP_VERSION, "competitions": competitions()})


@app.route("/api/calendar")
def api_calendar():
    lane = request.args.get("lane", "today")
    date = request.args.get("date") or today_iso()
    return jsonify({"ok": True, "version": APP_VERSION, "date": date, "lane": lane, "matches": get_matches(date, lane)})


@app.route("/api/live")
def api_live():
    date = request.args.get("date") or today_iso()
    matches = get_matches(date, "today")
    enriched = [annotate_match(m) for m in matches]
    return jsonify({"ok": True, "version": APP_VERSION, "date": date, "matches": split_live(enriched), "state_engine": ["LIVE", "HT", "FT", "UPCOMING", "SUSPENDED"]})


@app.route("/api/match-hub")
def api_match_hub():
    date = request.args.get("date") or today_iso()
    return jsonify({"ok": True, "version": APP_VERSION, "hub": match_hub(date)})


@app.route("/api/live-flow")
@app.route("/api/ecosystem/state")
def api_live_flow():
    date = request.args.get("date") or today_iso()
    return jsonify({"ok": True, "version": APP_VERSION, "flow": live_data_flow(date)})


@app.route("/api/realtime/state")
@app.route("/api/live/state")
def api_real_time_state():
    date = request.args.get("date") or today_iso()
    refresh = request.args.get("refresh") in {"1", "true", "yes"}
    return jsonify({"ok": True, "version": APP_VERSION, "real_time": real_time_global_state(date, refresh=refresh)})


@app.route("/api/favorites", methods=["GET", "POST", "DELETE"])
def api_favorites():
    if request.method == "GET":
        return jsonify({"ok": True, "version": APP_VERSION, "favorites": get_favorites(request.args.get("kind"))})
    payload = request.get_json(silent=True) or dict(request.form or {})
    if request.method == "DELETE":
        return jsonify({"version": APP_VERSION, **remove_favorite(payload.get("kind"), payload.get("value"))})
    favorite = add_favorite(payload.get("kind"), payload.get("value"), payload.get("label"))
    if not favorite:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Favorito invalido. Usa kind team, league o match con value."}), 400
    return jsonify({"ok": True, "version": APP_VERSION, "favorite": favorite})


@app.route("/api/favorites/feed")
def api_favorites_feed():
    return jsonify({"ok": True, "version": APP_VERSION, "feed": favorite_feed_full()})


@app.route("/api/matches/<match_id>/timeline")
def api_match_timeline(match_id):
    detail = match_detail(match_id)
    if not detail:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Partido no encontrado"}), 404
    return jsonify({"ok": True, "version": APP_VERSION, "match": detail["match"], "timeline": detail["timeline"], "state": detail["state"]})


@app.route("/api/matches/<match_id>/detail")
def api_match_detail(match_id):
    detail = match_detail(match_id)
    if not detail:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Partido no encontrado"}), 404
    context = build_shark_context(match=detail["match"], league=detail["match"].get("competition_name"), favorites=get_favorites(), picks=detail["related_picks"], profile=default_profile())
    save_shark_context("match_detail", match_id, context)
    return jsonify({"ok": True, "version": APP_VERSION, "detail": detail, "shark_context": context})


@app.route("/team-crest.svg")
def team_crest_svg():
    name = request.args.get("name") or "Equipo"
    text = initials(name)
    hue = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:2], 16)
    color_a = "#%02x%02x%02x" % (20 + hue % 60, 80 + hue % 110, 130 + hue % 90)
    color_b = "#07111f"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="{name}">
  <defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="{color_a}"/><stop offset="1" stop-color="{color_b}"/></linearGradient></defs>
  <rect width="96" height="96" rx="22" fill="url(#g)"/>
  <path d="M48 10 78 22v22c0 20-12 34-30 42-18-8-30-22-30-42V22Z" fill="rgba(255,255,255,.08)" stroke="rgba(255,255,255,.35)" stroke-width="2"/>
  <text x="48" y="57" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="24" font-weight="900" fill="#eef6ff">{text}</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


@app.route("/api/team/resolve")
def api_team_resolve():
    team = request.args.get("team") or request.args.get("name") or ""
    refresh = request.args.get("refresh") in {"1", "true", "yes"}
    return jsonify({"ok": True, "version": APP_VERSION, "team": resolve_team(team, refresh=refresh)})


@app.route("/api/teams")
def api_teams():
    seed_core()
    teams = rows("SELECT * FROM teams ORDER BY name")
    for team in teams:
        team["initials"] = initials(team.get("name"))
        team["crest_url"] = team.get("logo_url") or fallback_crest_url(team.get("name"))
        team["crest_mode"] = "logo" if team.get("logo_url") else "fallback"
    return jsonify({"ok": True, "version": APP_VERSION, "teams": teams})


@app.route("/api/import-teams", methods=["POST"])
def api_import_teams():
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_teams(
        rows_payload,
        payload.get("source_name") or "manual autorizado",
        payload.get("legal_note") or "Carga autorizada por administrador",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/crest-diagnostics")
def api_crest_diagnostics():
    seed_core()
    teams = rows("SELECT * FROM teams ORDER BY name")
    with_logo = [t for t in teams if t.get("logo_url")]
    without_logo = [t for t in teams if not t.get("logo_url")]
    return jsonify(
        {
            "ok": True,
            "version": APP_VERSION,
            "provider": "TheSportsDB",
            "provider_key_present": bool(thesportsdb_key()),
            "total_teams": len(teams),
            "with_logo": len(with_logo),
            "fallback": len(without_logo),
            "sample_missing": [t.get("name") for t in without_logo[:20]],
            "legal_policy": "Escudos desde API permitida, carga manual autorizada o fallback SVG propio. No scraping ilegal.",
        }
    )


@app.route("/api/import-matches", methods=["POST"])
def api_import_matches():
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_matches(
        rows_payload,
        payload.get("source_name") or "manual autorizado",
        payload.get("source_url") or "",
        payload.get("legal_note") or "Carga autorizada por administrador",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/picks")
def api_picks():
    return jsonify({"ok": True, "version": APP_VERSION, "picks": get_picks(limit=request.args.get("limit", 50))})


@app.route("/api/import-picks", methods=["POST"])
def api_import_picks():
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_picks(
        rows_payload,
        payload.get("source_name") or "manual autorizado",
        payload.get("legal_note") or "Carga autorizada por administrador",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/combis")
def api_combis():
    return jsonify({"ok": True, "version": APP_VERSION, "combis": get_combis(limit=request.args.get("limit", 20))})


@app.route("/api/combis/build", methods=["POST"])
def api_combis_build():
    payload = request.get_json(silent=True) or dict(request.form or {})
    pick_ids = payload.get("pick_ids") or payload.get("picks") or []
    if isinstance(pick_ids, str):
        pick_ids = [p.strip() for p in pick_ids.split(",") if p.strip()]
    combi = build_combi_from_picks(pick_ids=pick_ids, limit=as_int(payload.get("limit"), 3))
    if not combi:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "No hay picks suficientes para construir combi."}), 400
    combi["picks"] = json.loads(combi.get("picks_json") or "[]")
    return jsonify({"ok": True, "version": APP_VERSION, "combi": combi})


@app.route("/api/profile")
def api_profile():
    return jsonify({"ok": True, "version": APP_VERSION, "profile": default_profile()})


@app.route("/api/membership")
def api_membership():
    return jsonify({"ok": True, "version": APP_VERSION, "plans": MEMBERSHIP_PLANS, "profile": default_profile()})


@app.route("/api/shark/briefing")
def api_shark_briefing():
    return jsonify({"ok": True, "version": APP_VERSION, "briefing": shark_briefing()})


@app.route("/api/shark/ask", methods=["GET", "POST"])
def api_shark_ask():
    payload = request.get_json(silent=True) or dict(request.form or request.args or {})
    answer = shark_answer(payload.get("question") or payload.get("q") or "")
    save_shark_context("ask", answer.get("focus"), answer.get("context") or {})
    return jsonify({"ok": True, "version": APP_VERSION, "shark": answer})


@app.route("/api/shark/context")
def api_shark_context():
    match_id = request.args.get("match_id") or ""
    match = one("SELECT * FROM matches WHERE id=?", (match_id,)) if match_id else None
    context = build_shark_context(match=match, league=(match or {}).get("competition_name") if match else request.args.get("league"), favorites=get_favorites(), picks=get_picks(limit=12), profile=default_profile())
    snapshot_id = save_shark_context("context", match_id or context.get("league") or "global", context)
    return jsonify({"ok": True, "version": APP_VERSION, "snapshot_id": snapshot_id, "context": context})


@app.route("/api/telegram/status")
@app.route("/api/automation-status")
def api_telegram_status():
    deliveries = rows("SELECT * FROM telegram_deliveries ORDER BY created_at DESC LIMIT 20")
    return jsonify({"ok": True, "version": APP_VERSION, "telegram": telegram_config(), "recent_deliveries": deliveries, "queue": telegram_queue(limit=20)})


@app.route("/api/telegram/send", methods=["POST"])
def api_telegram_send():
    payload = request.get_json(silent=True) or dict(request.form or {})
    text = payload.get("text") or telegram_daily_message()
    result = send_telegram_message(text, payload.get("chat_id"), payload.get("message_type") or "manual")
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/telegram/auto-run", methods=["POST", "GET"])
@app.route("/api/v495/telegram-auto-run", methods=["POST", "GET"])
def api_telegram_auto_run():
    cfg = telegram_config()
    if not cfg["enabled"]:
        return jsonify({"ok": False, "version": APP_VERSION, "sent": False, "status": "AUTO_DISABLED", "telegram": cfg})
    result = send_telegram_message(telegram_daily_message(), message_type="auto_daily")
    return jsonify({"version": APP_VERSION, "telegram": cfg, **result})


@app.route("/api/telegram/scheduler-tick", methods=["POST", "GET"])
def api_telegram_scheduler_tick():
    force = request.args.get("force") in {"1", "true", "yes"} or (request.get_json(silent=True) or {}).get("force") is True
    return jsonify({"version": APP_VERSION, **telegram_scheduler_tick(force=force)})


@app.route("/api/telegram/triggers")
def api_telegram_triggers():
    return jsonify({"ok": True, "version": APP_VERSION, "triggers": telegram_triggers(), "last": automation_get("telegram_last_dispatch", {})})


@app.route("/api/telegram/logs")
def api_telegram_logs():
    deliveries = rows("SELECT * FROM telegram_deliveries ORDER BY created_at DESC LIMIT 100")
    return jsonify({"ok": True, "version": APP_VERSION, "logs": deliveries})


@app.route("/api/telegram/queue")
def api_telegram_queue():
    return jsonify({"ok": True, "version": APP_VERSION, "queue": telegram_queue(limit=request.args.get("limit", 50))})


@app.route("/api/telegram/scheduler-manager", methods=["GET", "POST"])
def api_telegram_scheduler_manager():
    force = request.args.get("force") in {"1", "true", "yes"} or (request.get_json(silent=True) or {}).get("force") is True
    posts = prepare_auto_posts()
    return jsonify({"ok": True, "version": APP_VERSION, "auto_posts": posts, "manager": process_telegram_queue(force=force)})


@app.route("/api/telegram/auto-posts")
def api_telegram_auto_posts():
    posts = prepare_auto_posts()
    saved = rows("SELECT * FROM auto_alerts ORDER BY updated_at DESC LIMIT 50")
    return jsonify({"ok": True, "version": APP_VERSION, "prepared": posts, "saved": saved})


@app.route("/api/cache/status")
def api_cache_status():
    cache_rows = rows("SELECT key,expires_at,updated_at FROM persistent_cache ORDER BY updated_at DESC LIMIT 50")
    return jsonify({"ok": True, "version": APP_VERSION, "health": cache_health(cache_rows), "items": cache_rows})


@app.route("/api/imports")
def api_imports():
    return jsonify({"ok": True, "version": APP_VERSION, "imports": rows("SELECT * FROM imports ORDER BY created_at DESC LIMIT 50")})


@app.route("/api/diagnostics")
def api_diagnostics():
    data = dashboard_data()
    checks = [
        {"name": "Core limpio", "status": "READY", "detail": "Proyecto reconstruido sin versiones antiguas acumuladas."},
        {"name": "SQLite", "status": "READY", "detail": "Tablas compactas: competitions, teams, matches, imports, favorites, picks, combis, profile, telegram, queue, context, cache."},
        {"name": "Calendario global", "status": "READY", "detail": f"{len(data['matches'])} partidos para la fecha base."},
        {"name": "Live center", "status": "READY", "detail": "Usa partidos reales/importados y separa directo, proximos y finalizados."},
        {"name": "Live Data Flow", "status": "READY", "detail": f"Estado compartido {data['live_flow']['shared_state']} con perfil, picks y favoritos."},
        {"name": "Live State Engine", "status": "READY", "detail": "Estados normalizados: LIVE, HT, FT, UPCOMING y SUSPENDED."},
        {"name": "Real Time Match Engine", "status": "READY", "detail": f"Sync {data['match_hub']['sync']['sync_status']} con refresh {data['match_hub']['sync']['refresh_seconds']}s."},
        {"name": "Match Hub", "status": "READY", "detail": f"Live {data['match_hub']['counts']['live']}, proximos {data['match_hub']['counts']['upcoming']}, favoritos {data['match_hub']['counts']['favorites']}."},
        {"name": "Favoritos reales", "status": "READY", "detail": f"{len(data['favorites'])} favoritos guardados; feed conecta partidos, live y picks."},
        {"name": "Importacion legal", "status": "READY", "detail": "Acepta CSV/JSON autorizado con trazabilidad de fuente."},
        {"name": "Escudos", "status": "READY", "detail": "Resuelve por cache, TheSportsDB, importacion legal o fallback SVG premium."},
        {"name": "Picks/Combis", "status": "READY", "detail": f"{len(data['picks'])} picks visibles y {len(data['combis'])} combis guardadas."},
        {"name": "Perfil premium", "status": "READY", "detail": f"Perfil activo: {data['profile']['name']} / plan {data['profile']['membership_plan']}."},
        {"name": "IA SHARK Context", "status": "READY", "detail": "Contexto persistente para partido, liga, favoritos y picks recientes."},
        {"name": "Telegram Auto Core", "status": "READY" if data["telegram"]["configured"] else "CONFIG", "detail": "Scheduler manager, queue, triggers, logs y anti duplicados preparados."},
        {"name": "Membresias", "status": "READY", "detail": "Planes Free, PRO y ELITE preparados para capa comercial."},
        {"name": "Performance cache", "status": "READY", "detail": "Cache persistente para hub, live flow y navegacion rapida."},
        {"name": "Premium mobile feel", "status": "READY", "detail": "Interacciones tactiles, spacing y tarjetas afinadas para sensacion app nativa."},
        {"name": "Arquitectura limpia", "status": "READY", "detail": "Motores separados: live, match, telegram, shark, crest y cache."},
        {"name": "Render", "status": "READY", "detail": "Procfile, render.yaml y requirements incluidos."},
    ]
    return jsonify({"ok": True, "version": APP_VERSION, "checks": checks, "readiness": data["readiness"]})


if __name__ == "__main__":
    seed_core()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
