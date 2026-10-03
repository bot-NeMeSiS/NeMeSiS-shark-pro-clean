"""Persistent sports memory. Writes belong to sync jobs; views are SQLite-only.

Provider IDs are scoped by entity type. Cross-provider links require explicit
identity evidence; names alone never merge teams, players or competitions.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing
from engines.match_sync_engine import IMPORTANT_COMPETITIONS

FINAL = {"ft", "finished", "final", "finalizado", "match finished", "archived", "aet", "pen"}
KINDS = {"competition", "season", "team", "player", "coach", "stadium", "referee", "match"}
DETAILS = {"lineups", "events", "statistics", "odds", "picks", "highlights"}


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
    raw = str(value or "local").lower().replace("-", "_")
    return {"sportsdb": "thesportsdb", "the sports db": "thesportsdb", "odds": "the_odds_api", "odds_api": "the_odds_api", "the odds api": "the_odds_api"}.get(raw, raw)


def entity(conn, kind, source, external_id, facts=None, canonical_id=None):
    source = provider_name(source)
    if kind not in KINDS or not source or not str(external_id or "").strip():
        raise ValueError("Entity requires kind, source and ID")
    external_id = str(external_id)
    row = conn.execute("SELECT canonical_id FROM sports_history_ids WHERE kind=? AND source=? AND external_id=?", (kind, source, external_id)).fetchone()
    if row and canonical_id and row[0] != canonical_id:
        raise ValueError("Conflicting canonical identity; manual review required")
    target = row[0] if row else canonical_id or key(kind, source, external_id)
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
    return row[0] if row else ""


def link_entities(conn, source_id, relation, target_id, source, facts=None):
    """Persist one verified relationship without inferring identities by name."""
    relation = str(relation or "").strip()
    source = provider_name(source)
    source_id = str(source_id or "").strip()
    target_id = str(target_id or "").strip()
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
            query = """SELECT l.target_id,l.source,l.facts,l.observed_at,e.kind
                       FROM sports_history_entity_links l
                       JOIN sports_history_entities e ON e.id=l.target_id
                       WHERE l.source_id=? AND l.relation=?"""
            params = [canonical, str(relation or "")]
            if target_kind:
                query += " AND e.kind=?"
                params.append(target_kind)
            query += " ORDER BY l.observed_at DESC,l.target_id"
            result = []
            for target_id, provenance, link_facts, observed_at, kind_value in conn.execute(query, tuple(params)):
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


def ingest_match(conn, item):
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
    known = conn.execute("SELECT id FROM sports_history_matches WHERE competition=? AND season=? AND home=? AND away=? AND kickoff=?", (competition, season, *teams, kickoff)).fetchall() if "T" in kickoff and season and item.get("home_team_id") and item.get("away_team_id") else []
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
    rows = conn.execute("SELECT * FROM sports_history_matches WHERE (home=? OR away=?) AND competition=? AND season=? ORDER BY kickoff DESC,id", (team, team, competition, season)).fetchall()
    names = [col[0] for col in conn.execute("SELECT * FROM sports_history_matches LIMIT 0").description]
    rows = [dict(zip(names, row)) for row in rows]
    if before:
        rows = [r for r in rows if r["kickoff"] and r["kickoff"] < before]
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
    result.update(coverage="complete" if complete else "partial", expected_played=expected, missing=missing, coverage_conflict=expected is not None and expected < len(usable), unscored=len(finals) - len(usable), coherent=result["played"] == result["wins"] + result["draws"] + result["losses"], home=totals([r for r in usable if r["home"] == team]), away=totals([r for r in usable if r["away"] == team]), windows={str(n): totals(usable[:n]) for n in (5, 10, 20)}, last_matches=usable[:20])
    streak = 0
    for outcome in result["form"]:
        if outcome != result["form"][0]:
            break
        streak += 1
    result["streak"] = {"outcome": result["form"][0] if result["form"] else None, "length": streak, "coverage": result["coverage"]}
    return result


def backfill_page(conn, source, scope, page, fetch, ingest, *, budget, timestamp, ttl=86400):
    """One explicit provider page, charged before fetching. No view calls this.

    Persistent daily per-source attempt count survives retries and restarts.
    BEGIN IMMEDIATE serializes reservations between workers. Fetch callback must
    represent exactly one HTTP call, with automatic retries disabled.
    """
    source = provider_name(source)
    if not isinstance(budget, int) or budget < 0 or ttl <= 0:
        raise ValueError("Backfill budget and TTL must be valid")
    if conn.in_transaction:
        raise ValueError("Backfill requires a dedicated idle connection")
    conn.execute("BEGIN IMMEDIATE")
    old = conn.execute("SELECT status,cache_until FROM sports_history_backfill WHERE source=? AND scope=? AND page=?", (source, scope, str(page))).fetchone()
    if old and old[1] > timestamp:
        conn.rollback()
        return {"status": "cached" if old[0] == "success" else old[0], "calls": 0}
    day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
    used = conn.execute("SELECT COUNT(*) FROM sports_history_call_ledger WHERE source=? AND substr(attempted_at,1,10)=?", (source, day)).fetchone()[0]
    if used >= budget:
        conn.rollback()
        return {"status": "budget_exhausted", "calls": 0}
    stamp = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    conn.execute("INSERT INTO sports_history_call_ledger(source,scope,page,attempted_at) VALUES(?,?,?,?)", (source, scope, str(page), stamp))
    conn.execute("INSERT INTO sports_history_backfill VALUES(?,?,?,'running',1,?,?) ON CONFLICT(source,scope,page) DO UPDATE SET status='running',attempts=CASE WHEN substr(sports_history_backfill.updated_at,1,10)=substr(excluded.updated_at,1,10) THEN sports_history_backfill.attempts+1 ELSE 1 END,cache_until=excluded.cache_until,updated_at=excluded.updated_at", (source, scope, str(page), timestamp + ttl, stamp))
    conn.commit()
    try:
        data = fetch(scope, page)
        with conn:
            for item in data:
                ingest(conn, item)
            conn.execute("UPDATE sports_history_backfill SET status='success' WHERE source=? AND scope=? AND page=?", (source, scope, str(page)))
    except Exception:
        conn.rollback()
        with conn:
            conn.execute("UPDATE sports_history_backfill SET status='error' WHERE source=? AND scope=? AND page=?", (source, scope, str(page)))
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
        "api_football_events_deep": ("events", "api_football"),
        "api_football_lineups_deep": ("lineups", "api_football"),
        "api_football_match_stats_history": ("statistics", "api_football"),
        "football_odds_history": ("odds", "local"),
        "football_shark_signals_history": ("picks", "internal"),
    }
    processed = unlinked = 0
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
            candidates = conn.execute("SELECT id FROM sports_history_matches WHERE internal_id=? AND internal_id<>''", (internal,)).fetchall() if internal else []
            if not candidates and external:
                candidates = conn.execute("SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source=? AND external_id=?", (source, external)).fetchall()
            if len(candidates) != 1:
                unlinked += 1
                continue
            if kind == "lineups" and row.get("player_id"):
                row["canonical_player_id"] = entity(conn, "player", source, row["player_id"], {"name": row.get("player_name"), "position": row.get("position"), "number": row.get("number")})
            stored = persist_detail(conn, candidates[0][0], kind, source, str(row.get("id") or key(row)), row,
                                    retention_permitted=row.get("retention_permitted") in (True, 1))
            processed += int(stored)
    return dict(processed=processed, unlinked=unlinked)


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


def history_summary(db_path):
    try:
        with closing(read_connection(db_path)) as conn:
            sources = [dict(source=r[0], linked_ids=r[1]) for r in conn.execute("SELECT source,COUNT(*) FROM sports_history_ids GROUP BY source")]
            scopes = [dict(team=r[0], competition=r[1], season=r[2], **team_metrics(conn, *r)) for r in conn.execute("SELECT DISTINCT home,competition,season FROM sports_history_matches UNION SELECT DISTINCT away,competition,season FROM sports_history_matches LIMIT 100")]
            jobs = [dict(source=r[0], scope=r[1], page=r[2], status=r[3], calls=r[4], updated_at=r[5]) for r in conn.execute("SELECT source,scope,page,status,attempts,updated_at FROM sports_history_backfill ORDER BY updated_at DESC LIMIT 30")]
            ids = [dict(kind=r[0], source=r[1], external_id=r[2], canonical_id=r[3]) for r in conn.execute("SELECT kind,source,external_id,canonical_id FROM sports_history_ids LIMIT 100")]
            last = conn.execute("SELECT MAX(updated_at) FROM sports_history_matches").fetchone()[0]
            consumption = [dict(source=r[0], day=r[1], calls=r[2]) for r in conn.execute("SELECT source,substr(attempted_at,1,10),COUNT(*) FROM sports_history_call_ledger GROUP BY source,substr(attempted_at,1,10) ORDER BY attempted_at DESC LIMIT 30")]
            return dict(available=True, sources=sources, scopes=scopes, jobs=jobs, ids=ids, consumption=consumption, last_sync=last, external_calls=0)
    except sqlite3.OperationalError:
        return dict(available=False, sources=[], scopes=[], jobs=[], ids=[], last_sync=None, external_calls=0)


def match_history(db_path, internal_id):
    try:
        with closing(read_connection(db_path)) as conn:
            candidates = conn.execute("SELECT id,home,away,competition,season,kickoff FROM sports_history_matches WHERE internal_id=? OR id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)", (str(internal_id), str(internal_id), str(internal_id))).fetchall()
            row = candidates[0] if len(candidates) == 1 else None
            if not row:
                return {}
            match_id, home, away, competition, season, kickoff = row
            if not kickoff or "T" not in kickoff or not season:
                return {}
            previous = [r[0] for r in conn.execute("SELECT DISTINCT season FROM sports_history_matches WHERE competition=? AND (home=? OR away=?) AND season<>? AND season<>'' ORDER BY season DESC", (competition,home,away,season))]
            return dict(home=team_metrics(conn, home, competition, season, before=kickoff), away=team_metrics(conn, away, competition, season, before=kickoff), h2h=team_metrics(conn, home, competition, season, opponent=away, before=kickoff), previous_seasons=[dict(season=s, home=team_metrics(conn,home,competition,s,before=kickoff),away=team_metrics(conn,away,competition,s,before=kickoff)) for s in previous[:10]], details=match_details(conn,match_id), entities=[entity_card(conn,identifier) for identifier in (match_id,competition,home,away)], season=season, competition=competition, external_calls=0)
    except sqlite3.OperationalError:
        return {}


def historical_match_detail(db_path, identifier):
    """Keep an archived Match Center reachable after a provider window shrinks."""
    try:
        with closing(read_connection(db_path)) as conn:
            cursor = conn.execute("SELECT * FROM sports_history_matches WHERE id=? OR internal_id=? OR id IN (SELECT canonical_id FROM sports_history_ids WHERE kind='match' AND source='nemesis_internal' AND external_id=?)", (str(identifier), str(identifier), str(identifier)))
            rows = cursor.fetchall()
            if len(rows) != 1:
                return None
            match = dict(zip([column[0] for column in cursor.description], rows[0]))
            home = entity_card(conn,match['home'])['facts']
            away = entity_card(conn,match['away'])['facts']
            competition = entity_card(conn,match['competition'])['facts']
            facts = entity_card(conn,match['id'])['facts']
            venue = entity_card(conn,facts.get('stadium_id','')).get('facts',{})
            return {'match': dict(id=match['internal_id'] or match['id'], canonical_history_id=match['id'],
                                  home_team=home.get('name'), away_team=away.get('name'),
                                  home_team_id=match['home'], away_team_id=match['away'],
                                  home_logo=home.get('logo'), away_logo=away.get('logo'),
                                  league_name=competition.get('name'), competition_id=match['competition'],
                                  season=match['season'], kickoff_iso=match['kickoff'], match_date=match['kickoff'][:10],
                                  status=match['status'], home_score=match['home_score'], away_score=match['away_score'],
                                  venue=venue.get('name'), source='sports_history', updated_at=match['updated_at']),
                    'historical_archive': True, 'external_calls': 0}
    except sqlite3.OperationalError:
        return None

