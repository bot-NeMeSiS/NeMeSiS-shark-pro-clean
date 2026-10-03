"""Persistent sports memory. Writes belong to sync jobs; views are SQLite-only.

Provider IDs are scoped by entity type. Cross-provider links require explicit
identity evidence; names alone never merge teams, players or competitions.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from contextlib import closing
from engines.match_sync_engine import IMPORTANT_COMPETITIONS

FINAL = {"ft", "finished", "final", "finalizado", "match finished", "archived", "aet", "pen"}
KINDS = {"competition", "season", "team", "player", "coach", "stadium", "referee", "match"}
DETAILS = {"lineups", "events", "statistics", "odds", "picks", "highlights"}
MADRID = ZoneInfo('Europe/Madrid')


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def key(*parts):
    return hashlib.sha256(encode(parts).encode()).hexdigest()[:32]


def ensure_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sports_history_entities (
      id TEXT PRIMARY KEY, kind TEXT NOT NULL, facts TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sports_history_ids (
      kind TEXT NOT NULL, source TEXT NOT NULL, external_id TEXT NOT NULL,
      canonical_id TEXT NOT NULL REFERENCES sports_history_entities(id),
      PRIMARY KEY(kind,source,external_id));
    CREATE TABLE IF NOT EXISTS sports_history_matches (
      id TEXT PRIMARY KEY, competition TEXT NOT NULL, season TEXT NOT NULL,
      home TEXT NOT NULL, away TEXT NOT NULL, kickoff TEXT NOT NULL,
      status TEXT NOT NULL, home_score INTEGER, away_score INTEGER,
      internal_id TEXT, updated_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS sports_history_team_scope ON sports_history_matches(competition,season,home,away,kickoff);
    CREATE TABLE IF NOT EXISTS sports_history_details (
      match_id TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL,
      external_id TEXT NOT NULL, payload TEXT NOT NULL, captured_at TEXT NOT NULL,
      PRIMARY KEY(match_id,kind,source,external_id));
    CREATE TABLE IF NOT EXISTS sports_history_coverage (
      team TEXT NOT NULL, competition TEXT NOT NULL, season TEXT NOT NULL,
      expected INTEGER, verified_complete INTEGER NOT NULL DEFAULT 0,
      source TEXT NOT NULL, updated_at TEXT NOT NULL,
      PRIMARY KEY(team,competition,season));
    CREATE TABLE IF NOT EXISTS sports_history_backfill (
      source TEXT NOT NULL, scope TEXT NOT NULL, page TEXT NOT NULL,
      status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      cache_until REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
      PRIMARY KEY(source,scope,page));
    CREATE TABLE IF NOT EXISTS sports_history_call_ledger (
      id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
      scope TEXT NOT NULL, page TEXT NOT NULL, attempted_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS sports_history_call_day ON sports_history_call_ledger(source,attempted_at);
    CREATE TABLE IF NOT EXISTS sports_history_redirects (
      source_id TEXT PRIMARY KEY, target_id TEXT NOT NULL, kind TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sports_history_identity_audit (
      id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL,
      external_id TEXT NOT NULL, previous_id TEXT, target_id TEXT NOT NULL,
      evidence TEXT NOT NULL, snapshot TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sports_history_backfill_leases (
      source TEXT NOT NULL, scope TEXT NOT NULL, page TEXT NOT NULL,
      reservation_id INTEGER NOT NULL, error_code TEXT,
      PRIMARY KEY(source,scope,page));
    CREATE TABLE IF NOT EXISTS sports_history_coverage_issues (
      team TEXT NOT NULL, competition TEXT NOT NULL, season TEXT NOT NULL,
      code TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(team,competition,season));
    CREATE TABLE IF NOT EXISTS sports_history_entity_links (
      source_id TEXT NOT NULL REFERENCES sports_history_entities(id),
      relation TEXT NOT NULL,
      target_id TEXT NOT NULL REFERENCES sports_history_entities(id),
      source TEXT NOT NULL,
      facts TEXT NOT NULL DEFAULT '{}',
      observed_at TEXT NOT NULL,
      PRIMARY KEY(source_id,relation,target_id,source));
    CREATE INDEX IF NOT EXISTS sports_history_entity_links_source
      ON sports_history_entity_links(source_id,relation);
    CREATE INDEX IF NOT EXISTS sports_history_entity_links_target
      ON sports_history_entity_links(target_id,relation);
    """)
    for competition in IMPORTANT_COMPETITIONS:
        canonical = entity(conn, "competition", "canonical", competition["key"], {"name": competition["name"], "country": competition["country"]})
        for source, field in (("thesportsdb", "sportsdb_id"), ("the_odds_api", "odds_key")):
            if competition.get(field):
                entity(conn, "competition", source, competition[field], canonical_id=canonical)


def provider_name(value):
    raw = str(value or "local").strip().lower().replace("-", "_").replace(" ", "_")
    if "sportsdb" in raw:
        return "thesportsdb"
    if raw in {"odds", "odds_api", "the_odds_api"}:
        return "the_odds_api"
    if raw in {"api_football", "api_sports", "api_football_api"}:
        return "api_football"
    return raw


def entity(conn, kind, source, external_id, facts=None, canonical_id=None):
    from engines.sports_history_reconciliation import resolve
    source = provider_name(source)
    if kind not in KINDS or not source or not str(external_id or "").strip():
        raise ValueError("Entity requires kind, source and ID")
    external_id = str(external_id)
    row = conn.execute("SELECT canonical_id FROM sports_history_ids WHERE kind=? AND source=? AND external_id=?", (kind, source, external_id)).fetchone()
    existing_id = resolve(conn,row[0]) if row else None
    canonical_id = resolve(conn,canonical_id) if canonical_id else None
    if row and canonical_id and existing_id != canonical_id:
        raise ValueError("Conflicting canonical identity; manual review required")
    target = existing_id if row else canonical_id or key(kind, source, external_id)
    previous = conn.execute("SELECT kind,facts FROM sports_history_entities WHERE id=?", (target,)).fetchone()
    if canonical_id and not previous:
        raise ValueError("Explicit link must reference an existing entity")
    if previous and previous[0] != kind:
        raise ValueError("Identity type mismatch")
    merged = json.loads(previous[1]) if previous else {}
    merged.update({k: v for k, v in (facts or {}).items() if v is not None and v != ""})
    conn.execute("INSERT INTO sports_history_entities VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET facts=excluded.facts,updated_at=excluded.updated_at", (target, kind, encode(merged), now()))
    conn.execute("INSERT OR IGNORE INTO sports_history_ids VALUES(?,?,?,?)", (kind, source, external_id, target))
    return target


def entity_id(conn, kind, source, external_id):
    source = provider_name(source)
    row = conn.execute(
        "SELECT canonical_id FROM sports_history_ids WHERE kind=? AND source=? AND external_id=?",
        (str(kind or ""), source, str(external_id or "")),
    ).fetchone()
    from engines.sports_history_reconciliation import resolve
    return resolve(conn, row[0]) if row else ""


def link_entities(conn, source_id, relation, target_id, source, facts=None):
    """Persist one verified relationship without inferring identities by name."""
    relation = str(relation or "").strip()
    source = provider_name(source)
    from engines.sports_history_reconciliation import resolve
    source_id = resolve(conn, str(source_id or "").strip())
    target_id = resolve(conn, str(target_id or "").strip())
    if not source_id or not target_id or not relation or not source:
        raise ValueError("Entity link requires source, relation, target and provenance")
    present = {
        row[0]
        for row in conn.execute(
            "SELECT id FROM sports_history_entities WHERE id IN (?,?)",
            (source_id, target_id),
        )
    }
    if present != {source_id, target_id}:
        raise ValueError("Entity link requires existing canonical entities")
    conn.execute(
        """INSERT INTO sports_history_entity_links(source_id,relation,target_id,source,facts,observed_at)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(source_id,relation,target_id,source)
           DO UPDATE SET facts=excluded.facts,observed_at=excluded.observed_at""",
        (source_id, relation, target_id, source, encode(facts or {}), now()),
    )
    return {"source_id": source_id, "relation": relation, "target_id": target_id, "source": source}


def entity_profile(db_path, kind, identifier, source=None):
    """Read one canonical entity by canonical id or an exact provider-scoped id."""
    try:
        with closing(read_connection(db_path)) as conn:
            canonical = str(identifier or "").strip()
            if source:
                canonical = entity_id(conn, kind, source, identifier)
            if not canonical:
                return {}
            card = entity_card(conn, canonical)
            if card and card.get("kind") == kind:
                card["external_calls"] = 0
                return card
            return {}
    except sqlite3.OperationalError:
        return {}


def linked_entity_cards(db_path, source_kind, source_identifier, relation, *, source=None, target_kind=None):
    """Return locally persisted related entities; never calls a provider."""
    try:
        with closing(read_connection(db_path)) as conn:
            canonical = str(source_identifier or "").strip()
            if source:
                canonical = entity_id(conn, source_kind, source, source_identifier)
            if not canonical:
                return []
            from engines.sports_history_reconciliation import resolve
            canonical = resolve(conn, canonical)
            aliases = [canonical]
            aliases.extend(row[0] for row in conn.execute("SELECT source_id FROM sports_history_redirects") if resolve(conn, row[0]) == canonical)
            placeholders = ','.join('?' for _ in aliases)
            query = """SELECT l.target_id,l.source,l.facts,l.observed_at,e.kind
                       FROM sports_history_entity_links l
                       JOIN sports_history_entities e ON e.id=l.target_id
                       WHERE l.source_id IN (""" + placeholders + """) AND l.relation=?"""
            params = [*aliases, str(relation or "")]
            if target_kind:
                query += " AND e.kind=?"
                params.append(target_kind)
            query += " ORDER BY l.observed_at DESC,l.target_id"
            result, seen = [], set()
            for target_id, provenance, link_facts, observed_at, kind_value in conn.execute(query, tuple(params)):
                target_id = resolve(conn, target_id)
                if target_id in seen:
                    continue
                seen.add(target_id)
                card = entity_card(conn, target_id)
                if not card:
                    continue
                card.update(
                    relation=relation,
                    relation_source=provenance,
                    relation_facts=json.loads(link_facts or "{}"),
                    relation_observed_at=observed_at,
                    external_calls=0,
                )
                result.append(card)
            return result
    except sqlite3.OperationalError:
        return []


def team_profile(db_path, identifier, source="thesportsdb"):
    return entity_profile(db_path, "team", identifier, source=source)


def player_profile(db_path, identifier, source="thesportsdb"):
    return entity_profile(db_path, "player", identifier, source=source)


def team_roster(db_path, identifier, source="thesportsdb"):
    return linked_entity_cards(
        db_path,
        "team",
        identifier,
        "team_has_player",
        source=source,
        target_kind="player",
    )


def score(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(str(value))
        return parsed if parsed >= 0 else None
    except (ValueError, TypeError):
        return None


def confirmed_kickoff(value):
    try:
        instant = datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return instant.tzinfo is not None
    except (ValueError,TypeError):
        return False


def ingest_match(conn, item):
    from engines.sports_history_reconciliation import active_filter
    if any(not item.get(side + "_team_id") and not str(item.get(side + "_team") or "").strip() for side in ("home", "away")):
        raise ValueError("Both teams must be supplied")
    source = provider_name(item.get("provider"))
    competition = entity(conn, "competition", source, item.get("league_id") or item.get("league_name"), {"name": item.get("league_name"), "logo": item.get("competition_logo")})
    season = str(item.get("season") or "")
    entity(conn, "season", "canonical", key(competition, season), {"competition_id": competition, "label": season})
    teams = [entity(conn, "team", source, item.get(side + "_team_id") or ("unresolved:" + key(competition, item.get(side + "_team"))), {"name": item.get(side + "_team"), "logo": item.get(side + "_logo"), "identity_confirmed": bool(item.get(side + "_team_id"))}) for side in ("home", "away")]
    kickoff = str(item.get("kickoff_iso") or item.get("match_date") or "")
    try:
        dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        if dt.tzinfo:
            kickoff = dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    # Exact known identities/time only; uncertain matches remain separate.
    known = conn.execute("SELECT id FROM sports_history_matches WHERE competition=? AND season=? AND home=? AND away=? AND kickoff=? AND " + active_filter(conn), (competition, season, *teams, kickoff)).fetchall() if confirmed_kickoff(kickoff) and season and item.get("home_team_id") and item.get("away_team_id") else []
    match_id = entity(conn, "match", source, item.get("external_id") or item.get("internal_match_id"), {"round": item.get("round_name")}, canonical_id=known[0][0] if len(known) == 1 else None)
    if item.get("internal_match_id"):
        entity(conn, "match", "nemesis_internal", item["internal_match_id"], canonical_id=match_id)
    old = conn.execute("SELECT status,home_score,away_score FROM sports_history_matches WHERE id=?", (match_id,)).fetchone()
    status = str(item.get("status") or "").strip().lower()
    hs, aws = score(item.get("home_score")), score(item.get("away_score"))
    if old and old[0] in FINAL and (status not in FINAL or hs is None or aws is None):
        status, hs, aws = old
    conn.execute("INSERT INTO sports_history_matches VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET competition=excluded.competition,season=CASE WHEN excluded.season='' THEN sports_history_matches.season ELSE excluded.season END,kickoff=CASE WHEN excluded.kickoff='' THEN sports_history_matches.kickoff ELSE excluded.kickoff END,status=excluded.status,home_score=excluded.home_score,away_score=excluded.away_score,internal_id=COALESCE(NULLIF(excluded.internal_id,''),sports_history_matches.internal_id),updated_at=excluded.updated_at", (match_id, competition, season, *teams, kickoff, status, hs, aws, str(item.get("internal_match_id") or ""), now()))
    for kind, field in (("stadium", "venue"), ("referee", "referee")):
        if item.get(field):
            linked = entity(conn, kind, source, item.get(field + "_id") or item[field], {"name": item[field]})
            entity(conn, "match", source, item.get("external_id") or item.get("internal_match_id"), {kind + "_id": linked})
    for kind in DETAILS:
        supplied = item.get(kind)
        entries = supplied if isinstance(supplied, list) else [supplied] if isinstance(supplied, dict) else []
        for detail in entries:
            if not isinstance(detail, dict):
                continue
            # Payload fingerprint keeps snapshots with no provider event ID;
            # it is not an inferred match/event identity across providers.
            detail_id = str(detail.get("id") or detail.get("external_id") or key(detail))
            detail = dict(detail)
            if kind == "lineups":
                linked_players = []
                for player in detail.get("players") or detail.get("starters") or []:
                    if isinstance(player, dict) and player.get("id"):
                        canonical_player = entity(conn, "player", source, player["id"], player)
                        linked_players.append(dict(player, canonical_player_id=canonical_player))
                detail["player_links"] = linked_players
            persist_detail(conn, match_id, kind, source, detail_id, detail,
                           retention_permitted=detail.get("retention_permitted") is True)
    return match_id


def persist_detail(conn, match_id, kind, source, external_id, payload, *, retention_permitted=False):
    if kind not in DETAILS or not conn.execute("SELECT 1 FROM sports_history_matches WHERE id=?", (match_id,)).fetchone():
        raise ValueError("Unknown match or detail kind")
    if kind in {"odds", "highlights"} and not retention_permitted:
        return False
    if not source or not external_id:
        raise ValueError("Detail requires provenance and stable ID")
    conn.execute("INSERT INTO sports_history_details VALUES(?,?,?,?,?,?) ON CONFLICT(match_id,kind,source,external_id) DO UPDATE SET payload=excluded.payload,captured_at=excluded.captured_at", (match_id, kind, source, str(external_id), encode(payload), now()))
    return True


def record_coverage(conn, team, competition, season, source, expected=None, verified_complete=False):
    if expected is not None and (isinstance(expected, bool) or not isinstance(expected, int) or expected < 0):
        raise ValueError("Expected played must be a non-negative integer")
    conn.execute("INSERT INTO sports_history_coverage VALUES(?,?,?,?,?,?,?) ON CONFLICT(team,competition,season) DO UPDATE SET expected=excluded.expected,verified_complete=excluded.verified_complete,source=excluded.source,updated_at=excluded.updated_at", (team, competition, season, expected, int(verified_complete), source, now()))


def team_metrics(conn, team, competition, season, opponent=None, before=None):
    from engines.sports_history_reconciliation import active_filter, resolve
    team, competition = resolve(conn,team), resolve(conn,competition)
    opponent = resolve(conn,opponent) if opponent else None
    rows = conn.execute("SELECT * FROM sports_history_matches WHERE (home=? OR away=?) AND competition=? AND season=? AND " + active_filter(conn) + " ORDER BY kickoff DESC,id", (team, team, competition, season)).fetchall()
    names = [col[0] for col in conn.execute("SELECT * FROM sports_history_matches LIMIT 0").description]
    rows = [dict(zip(names, row)) for row in rows]
    if before:
        rows = [r for r in rows if confirmed_kickoff(r['kickoff']) and r["kickoff"] < before]
    if opponent:
        rows = [r for r in rows if opponent in (r["home"], r["away"])]
    finals = [r for r in rows if r["status"] in FINAL]
    usable = [r for r in finals if r["home_score"] is not None and r["away_score"] is not None]
    def totals(items):
        result = dict(played=len(items), wins=0, draws=0, losses=0, gf=0, ga=0, form=[])
        for r in items:
            gf, ga = (r["home_score"], r["away_score"]) if r["home"] == team else (r["away_score"], r["home_score"])
            outcome = "W" if gf > ga else "D" if gf == ga else "L"
            result[{"W": "wins", "D": "draws", "L": "losses"}[outcome]] += 1
            result["gf"] += gf
            result["ga"] += ga
            result["form"].append(outcome)
        return result
    result = totals(usable)
    evidence = conn.execute("SELECT expected,verified_complete FROM sports_history_coverage WHERE team=? AND competition=? AND season=?", (team, competition, season)).fetchone()
    expected = evidence[0] if evidence and not before and not opponent else None
    missing = max(0, expected - len(usable)) if expected is not None else None
    complete = bool(evidence and evidence[1] and expected == len(usable) and len(finals) == len(usable) and not before and not opponent)
    chronological = [row for row in usable if confirmed_kickoff(row['kickoff'])]
    result.update(coverage="complete" if complete else "partial", expected_played=expected, missing=missing, coverage_conflict=expected is not None and expected < len(usable), unscored=len(finals) - len(usable), coherent=result["played"] == result["wins"] + result["draws"] + result["losses"], home=totals([r for r in usable if r["home"] == team]), away=totals([r for r in usable if r["away"] == team]), windows={str(n): totals(chronological[:n]) for n in (5, 10, 20)}, last_matches=chronological[:20], chronology_partial=len(chronological)!=len(usable))
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sports_history_coverage_issues'").fetchone():
        issue = conn.execute('SELECT code FROM sports_history_coverage_issues WHERE team=? AND competition=? AND season=?', (team,competition,season)).fetchone()
        result['coverage_issue'] = issue[0] if issue else None
        if result['coverage_issue']:
            result['coverage'] = 'partial'
            result['coverage_conflict'] = True
    streak = 0
    chronological_form = totals(chronological)['form']
    for outcome in chronological_form:
        if outcome != chronological_form[0]:
            break
        streak += 1
    result["streak"] = {"outcome": chronological_form[0] if chronological_form else None, "length": streak, "coverage": 'partial' if result['chronology_partial'] else result["coverage"]}
    return result


def backfill_page(conn, source, scope, page, fetch, ingest, *, budget, timestamp, ttl=86400):
    """One explicit provider page, charged before fetching. No view calls this.

    Persistent daily per-source attempt count survives retries and restarts.
    BEGIN IMMEDIATE serializes reservations between workers. Fetch callback must
    represent exactly one HTTP call, with automatic retries disabled.
    """
    source = provider_name(source)
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0 or ttl <= 0:
        raise ValueError("Backfill budget and TTL must be valid")
    if conn.in_transaction:
        raise ValueError("Backfill requires a dedicated idle connection")
    conn.execute("BEGIN IMMEDIATE")
    old = conn.execute("SELECT status,cache_until FROM sports_history_backfill WHERE source=? AND scope=? AND page=?", (source, scope, str(page))).fetchone()
    if old and old[1] > timestamp:
        conn.rollback()
        return {"status": "cached" if old[0] == "success" else old[0], "calls": 0}
    madrid_midnight = datetime.fromtimestamp(timestamp, MADRID).replace(hour=0,minute=0,second=0,microsecond=0)
    day_start = madrid_midnight.astimezone(timezone.utc).isoformat()
    day_end = (madrid_midnight + timedelta(days=1)).astimezone(timezone.utc).isoformat()
    used = conn.execute("SELECT COUNT(*) FROM sports_history_call_ledger WHERE source=? AND attempted_at>=? AND attempted_at<?", (source,day_start,day_end)).fetchone()[0]
    if used >= budget:
        conn.rollback()
        return {"status": "budget_exhausted", "calls": 0}
    stamp = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    reservation = conn.execute("INSERT INTO sports_history_call_ledger(source,scope,page,attempted_at) VALUES(?,?,?,?)", (source, scope, str(page), stamp)).lastrowid
    conn.execute('''INSERT INTO sports_history_backfill_leases VALUES(?,?,?,?,NULL)
        ON CONFLICT(source,scope,page) DO UPDATE SET reservation_id=excluded.reservation_id,error_code=NULL''', (source,scope,str(page),reservation))
    conn.execute("INSERT INTO sports_history_backfill VALUES(?,?,?,'running',1,?,?) ON CONFLICT(source,scope,page) DO UPDATE SET status='running',attempts=CASE WHEN substr(sports_history_backfill.updated_at,1,10)=substr(excluded.updated_at,1,10) THEN sports_history_backfill.attempts+1 ELSE 1 END,cache_until=excluded.cache_until,updated_at=excluded.updated_at", (source, scope, str(page), timestamp + ttl, stamp))
    conn.commit()
    try:
        data = fetch(scope, page)
        conn.execute('BEGIN IMMEDIATE')
        current = conn.execute('SELECT reservation_id FROM sports_history_backfill_leases WHERE source=? AND scope=? AND page=?', (source,scope,str(page))).fetchone()
        if not current or current[0] != reservation:
            conn.rollback()
            return {'status':'superseded', 'calls':1}
        for item in data:
            ingest(conn, item)
        conn.execute("UPDATE sports_history_backfill SET status='success' WHERE source=? AND scope=? AND page=?", (source, scope, str(page)))
        conn.commit()
    except Exception:
        conn.rollback()
        with conn:
            conn.execute("UPDATE sports_history_backfill SET status='error' WHERE source=? AND scope=? AND page=? AND EXISTS (SELECT 1 FROM sports_history_backfill_leases WHERE source=? AND scope=? AND page=? AND reservation_id=?)", (source,scope,str(page),source,scope,str(page),reservation))
            conn.execute("UPDATE sports_history_backfill_leases SET error_code='fetch_or_ingest_failed' WHERE source=? AND scope=? AND page=? AND reservation_id=?", (source,scope,str(page),reservation))
        return {"status": "error", "calls": 1}
    return {"status": "success", "calls": 1}


def remember_sports_match(db_path, match, source="local"):
    """Called only from the existing daily snapshot write boundary."""
    item = dict(match)
    item.update(provider=match.get("source") or source,
                external_id=match.get("external_id") or match.get("id"),
                internal_match_id=match.get("id"),
                league_id=match.get("competition_id") or match.get("league_id"),
                league_name=match.get("league_name") or match.get("competition_name"))
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        with conn:
            return ingest_match(conn, item)
    finally:
        conn.close()


def entity_card(conn, canonical_id):
    from engines.sports_history_reconciliation import resolve
    canonical_id = resolve(conn,canonical_id)
    row = conn.execute("SELECT kind,facts,updated_at FROM sports_history_entities WHERE id=?", (canonical_id,)).fetchone()
    if not row:
        return {}
    links = [dict(source=r[0], external_id=r[1]) for r in conn.execute("SELECT source,external_id FROM sports_history_ids WHERE canonical_id=?", (canonical_id,))]
    return dict(id=canonical_id, kind=row[0], facts=json.loads(row[1]), updated_at=row[2], sources=links, coverage="partial")


def sync_existing_details(conn):
    """Archive supplied local detail rows with unambiguous match links only.

    Rights-sensitive odds and media require explicit permission on each row.
    Unlinked records remain in their original tables for later ID reconciliation.
    """
    tables = {
        "football_match_events_history": ("events", "local"),
        "football_lineups_history": ("lineups", "local"),
        "api_football_live_events": ("events", "api_football"),
        "match_timeline": ("events", "local"),
        "api_football_lineups_deep": ("lineups", "api_football"),
        "api_football_match_stats_history": ("statistics", "api_football"),
        "football_odds_history": ("odds", "local"),
        "football_shark_signals_history": ("picks", "internal"),
    }
    processed = unlinked = 0
    from engines.sports_history_reconciliation import active_filter
    for table, (kind, default_source) in tables.items():
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            continue
        cursor = conn.execute("SELECT * FROM " + table)
        columns = [column[0] for column in cursor.description]
        for raw in cursor:
            row = dict(zip(columns, raw))
            source = provider_name(row.get("provider") or row.get("source") or default_source)
            internal = str(row.get("internal_match_id") or row.get("match_id") or "")
            external = str(row.get("external_match_id") or row.get("fixture_id") or row.get("external_id") or "")
            candidates = conn.execute("SELECT id FROM sports_history_matches WHERE (internal_id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)) AND " + active_filter(conn), (internal,internal)).fetchall() if internal else []
            if not candidates and external:
                candidates = conn.execute("SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source=? AND external_id=?", (source, external)).fetchall()
            if len(candidates) != 1:
                unlinked += 1
                continue
            if kind == "lineups" and row.get("player_id"):
                row["canonical_player_id"] = entity(conn, "player", source, row["player_id"], {"name": row.get("player_name"), "position": row.get("position"), "number": row.get("number")})
                # This existing table is the approved confirmed provider lineup cache.
                if table == 'api_football_lineups_deep':
                    row['confirmed'] = True
            if kind == 'events' and str(row.get('event_type') or row.get('type') or '').lower() == 'state':
                continue
            stored = persist_detail(conn, candidates[0][0], kind, source, str(row.get("id") or key(row)), row,
                                    retention_permitted=row.get("retention_permitted") in (True, 1))
            processed += int(stored)
    return dict(processed=processed, unlinked=unlinked)


def sync_standings_coverage(conn):
    """Read actual league/season/team totals from supplied local standings.

    Never add expected totals from multiple sources. Inconsistent or incomplete
    standings remain partial, even when their played count is supplied.
    """
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='football_standings_history'").fetchone():
        return dict(processed=0, conflicts=0)
    cursor = conn.execute('SELECT * FROM football_standings_history ORDER BY snapshot_at')
    columns = [column[0] for column in cursor.description]
    latest = {}
    for raw in cursor:
        row = dict(zip(columns,raw))
        if not row.get('team_id') or not row.get('league_id') or not row.get('season'):
            continue
        source = provider_name(row.get('provider'))
        comp = entity(conn,'competition',source,row['league_id'],{'name':row.get('league_name')})
        team = entity(conn,'team',source,row['team_id'],{'name':row.get('team_name')})
        latest[(team,comp,row['season'],source)] = row
    scopes = {}
    for (team,comp,season,source), row in latest.items():
        played = score(row.get('played'))
        counts = [score(row.get(field)) for field in ('wins','draws','losses')]
        coherent = played is not None and all(value is not None for value in counts) and played == sum(value for value in counts if value is not None)
        sample = team_metrics(conn,team,comp,season)
        consistent_results = coherent and sample['played']==played and all(sample[field]==score(row.get(field)) for field in ('wins','draws','losses'))
        for supplied, computed in (('goals_for','gf'),('goals_against','ga')):
            if score(row.get(supplied)) is not None and sample[computed] != score(row[supplied]):
                consistent_results = False
        scopes.setdefault((team,comp,season),[]).append((source,played,coherent,consistent_results))
    conflicts = 0
    for scope, evidence in scopes.items():
        totals = {entry[1] for entry in evidence if entry[1] is not None}
        conflicts += int(len(totals)>1)
        expected = next(iter(totals)) if len(totals)==1 else None
        verified = expected is not None and all(entry[2] and entry[3] and entry[1]==expected for entry in evidence)
        record_coverage(conn,*scope,source=','.join(sorted(entry[0] for entry in evidence)),expected=expected,verified_complete=verified)
        issue = 'conflicting_expected_totals' if len(totals)>1 else 'incoherent_standings' if not all(entry[2] for entry in evidence) else 'standings_results_mismatch' if expected is not None and team_metrics(conn,*scope)['played']==expected and not verified else None
        conn.execute('''INSERT INTO sports_history_coverage_issues VALUES(?,?,?,?,?) ON CONFLICT(team,competition,season)
            DO UPDATE SET code=excluded.code,updated_at=excluded.updated_at''', (*scope,issue,now()))
    return dict(processed=len(scopes),conflicts=conflicts)


def match_details(conn, match_id):
    """Reusable Match Center input; only confirmed lineups are pitch-ready."""
    result = {kind: [] for kind in DETAILS}
    for kind, source, external_id, payload, captured in conn.execute("SELECT kind,source,external_id,payload,captured_at FROM sports_history_details WHERE match_id=? ORDER BY captured_at", (match_id,)):
        value = json.loads(payload)
        if kind == "lineups" and value.get("confirmed") is not True:
            continue
        result[kind].append(dict(source=source, external_id=external_id, payload=value, captured_at=captured))
    return result


def read_connection(db_path):
    return sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)


def cached_match_details(db_path, identifier):
    """Read details independently of season/kickoff coverage and without metrics."""
    from engines.sports_history_reconciliation import active_filter, resolve
    try:
        with closing(read_connection(db_path)) as conn:
            candidates = conn.execute("SELECT id FROM sports_history_matches WHERE (id=? OR internal_id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)) AND " + active_filter(conn), (resolve(conn,str(identifier)),str(identifier),str(identifier))).fetchall()
            return match_details(conn,candidates[0][0]) if len(candidates)==1 else {}
    except sqlite3.OperationalError:
        return {}


def team_history_snapshot(db_path, team_name, known_matches):
    """Resolve through persisted match relationships, never merge by team name."""
    from engines.sports_history_reconciliation import active_filter, resolve
    try:
        with closing(read_connection(db_path)) as conn:
            identities = set()
            for match in known_matches or []:
                side = next((side for side in ('home','away') if str(match.get(side+'_team') or '').casefold()==str(team_name or '').casefold()),None)
                if not side or not match.get('id'):
                    continue
                rows = conn.execute("SELECT home,away FROM sports_history_matches WHERE (internal_id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)) AND " + active_filter(conn), (str(match['id']),str(match['id']))).fetchall()
                if len(rows)==1:
                    identities.add(resolve(conn,rows[0][0 if side=='home' else 1]))
            if len(identities)!=1:
                return dict(available=False,requires_reconciliation=len(identities)>1,scopes=[],external_calls=0)
            team_id = identities.pop()
            scopes = conn.execute('SELECT DISTINCT competition,season FROM sports_history_matches WHERE (home=? OR away=?) AND season<>? AND ' + active_filter(conn) + ' ORDER BY season DESC LIMIT 30', (team_id,team_id,'')).fetchall()
            return dict(available=True,team_id=team_id,scopes=[dict(competition=comp,competition_name=entity_card(conn,comp).get('facts',{}).get('name') or 'Competición',season=season,**team_metrics(conn,team_id,comp,season)) for comp,season in scopes],external_calls=0)
    except sqlite3.OperationalError:
        return dict(available=False,requires_reconciliation=False,scopes=[],external_calls=0)


def history_summary(db_path):
    try:
        with closing(read_connection(db_path)) as conn:
            sources = [dict(source=r[0], linked_ids=r[1]) for r in conn.execute("SELECT source,COUNT(*) FROM sports_history_ids GROUP BY source")]
            scopes = [dict(team=r[0], competition=r[1], season=r[2], **team_metrics(conn, *r)) for r in conn.execute("SELECT DISTINCT home,competition,season FROM sports_history_matches UNION SELECT DISTINCT away,competition,season FROM sports_history_matches LIMIT 100")]
            jobs = [dict(source=r[0], scope=r[1], page=r[2], status=r[3], calls=r[4], updated_at=r[5]) for r in conn.execute("SELECT source,scope,page,status,attempts,updated_at FROM sports_history_backfill ORDER BY updated_at DESC LIMIT 30")]
            ids = [dict(kind=r[0], source=r[1], external_id=r[2], canonical_id=r[3]) for r in conn.execute("SELECT kind,source,external_id,canonical_id FROM sports_history_ids LIMIT 100")]
            last = conn.execute("SELECT MAX(updated_at) FROM sports_history_matches").fetchone()[0]
            conn.create_function('history_madrid_day',1,lambda value: datetime.fromisoformat(value).astimezone(MADRID).date().isoformat())
            consumption = [dict(source=r[0], day=r[1], calls=r[2]) for r in conn.execute("SELECT source,history_madrid_day(attempted_at),COUNT(*) FROM sports_history_call_ledger GROUP BY source,history_madrid_day(attempted_at) ORDER BY MAX(attempted_at) DESC LIMIT 30")]
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sports_history_backfill_leases'").fetchone():
                for job in jobs:
                    error = conn.execute('SELECT error_code FROM sports_history_backfill_leases WHERE source=? AND scope=? AND page=?', (job['source'],job['scope'],job['page'])).fetchone()
                    job['error_code'] = error[0] if error else None
            scopes = [{**scope, 'team_name': entity_card(conn,scope['team']).get('facts',{}).get('name') or scope['team'], 'competition_name': entity_card(conn,scope['competition']).get('facts',{}).get('name') or scope['competition']} for scope in scopes]
            audits = []
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sports_history_identity_audit'").fetchone():
                audits = [dict(kind=r[0], source=r[1], external_id=r[2], target_id=r[3], evidence=r[4], created_at=r[5]) for r in conn.execute('SELECT kind,source,external_id,target_id,evidence,created_at FROM sports_history_identity_audit ORDER BY created_at DESC LIMIT 30')]
            entity_counts = [dict(kind=r[0], count=r[1]) for r in conn.execute("SELECT kind,COUNT(*) FROM sports_history_entities GROUP BY kind ORDER BY kind")]
            relation_counts = [dict(relation=r[0], count=r[1]) for r in conn.execute("SELECT relation,COUNT(*) FROM sports_history_entity_links GROUP BY relation ORDER BY relation")]
            entity_sync = {}
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='automation_state'").fetchone():
                state = conn.execute("SELECT value_json,updated_at FROM automation_state WHERE key='sportsdb_entity_memory_sync'").fetchone()
                if state:
                    try:
                        entity_sync = json.loads(state[0] or "{}")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        entity_sync = {"state": "invalid"}
                    entity_sync["updated_at"] = state[1]
            return dict(available=True, sources=sources, scopes=scopes, jobs=jobs, ids=ids, consumption=consumption, reconciliations=audits, entity_counts=entity_counts, relation_counts=relation_counts, entity_sync=entity_sync, last_sync=last, external_calls=0)
    except sqlite3.OperationalError:
        return dict(available=False, sources=[], scopes=[], jobs=[], ids=[], consumption=[], entity_counts=[], relation_counts=[], entity_sync={}, last_sync=None, external_calls=0)


def match_history(db_path, internal_id):
    from engines.sports_history_reconciliation import active_filter, resolve
    try:
        with closing(read_connection(db_path)) as conn:
            candidates = conn.execute("SELECT id,home,away,competition,season,kickoff FROM sports_history_matches WHERE (internal_id=? OR id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)) AND " + active_filter(conn), (str(internal_id), resolve(conn,str(internal_id)), str(internal_id))).fetchall()
            row = candidates[0] if len(candidates) == 1 else None
            if not row:
                return {}
            match_id, home, away, competition, season, kickoff = row
            if not confirmed_kickoff(kickoff) or not season:
                return {}
            previous = [r[0] for r in conn.execute("SELECT DISTINCT season FROM sports_history_matches WHERE competition=? AND (home=? OR away=?) AND season<>? AND season<>'' ORDER BY season DESC", (competition,home,away,season))]
            return dict(home=team_metrics(conn, home, competition, season, before=kickoff), away=team_metrics(conn, away, competition, season, before=kickoff), h2h=team_metrics(conn, home, competition, season, opponent=away, before=kickoff), previous_seasons=[dict(season=s, home=team_metrics(conn,home,competition,s,before=kickoff),away=team_metrics(conn,away,competition,s,before=kickoff)) for s in previous[:10]], details=match_details(conn,match_id), entities=[entity_card(conn,identifier) for identifier in (match_id,competition,home,away)], season=season, competition=competition, external_calls=0)
    except sqlite3.OperationalError:
        return {}


def historical_match_detail(db_path, identifier):
    from engines.sports_history_reconciliation import active_filter, resolve
    """Keep an archived Match Center reachable after a provider window shrinks."""
    try:
        with closing(read_connection(db_path)) as conn:
            cursor = conn.execute("SELECT * FROM sports_history_matches WHERE (id=? OR internal_id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)) AND " + active_filter(conn), (resolve(conn,str(identifier)), str(identifier), str(identifier)))
            rows = cursor.fetchall()
            if len(rows) != 1:
                return None
            match = dict(zip([column[0] for column in cursor.description], rows[0]))
            home = entity_card(conn,match['home'])['facts']
            away = entity_card(conn,match['away'])['facts']
            competition_card = entity_card(conn,match['competition'])
            competition = competition_card['facts']
            public_competition_id = next((link['external_id'] for link in competition_card['sources'] if link['source']=='canonical'),next((link['external_id'] for link in competition_card['sources'] if link['source']=='thesportsdb'),match['competition']))
            facts = entity_card(conn,match['id'])['facts']
            venue = entity_card(conn,facts.get('stadium_id','')).get('facts',{})
            return {'match': dict(id=match['internal_id'] or match['id'], canonical_history_id=match['id'],
                                  home_team=home.get('name'), away_team=away.get('name'),
                                  home_team_id=match['home'], away_team_id=match['away'],
                                  home_logo=home.get('logo'), away_logo=away.get('logo'),
                                  league_name=competition.get('name'), competition_id=public_competition_id,
                                  season=match['season'], kickoff_iso=match['kickoff'], match_date=match['kickoff'][:10],
                                  status=match['status'], home_score=match['home_score'], away_score=match['away_score'],
                                  venue=venue.get('name'), source='sports_history', updated_at=match['updated_at']),
                    'historical_archive': True, 'external_calls': 0}
    except sqlite3.OperationalError:
        return None

