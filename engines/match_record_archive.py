"""Append-only receipts of already fetched match data. No HTTP or public feed.

Ingestors own the connection and commit/rollback. A receipt is when NeMeSiS
observed a response, NOT the provider's publication time. Current cache rows
remain independent. Archive exhaustion is explicit and never deletes history.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import zlib

PROVIDER = "api_football"
SECTIONS = frozenset({"fixture", "statistics", "events", "lineups", "players"})
MAX_RAW_BYTES = 512 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024  # Encoded payload+context budget, NOT SQLite disk size.
MAX_OBSERVATIONS = 100_000
MAX_GAP_KEYS = 1024
MIN_FREE_DISK_BYTES = 128 * 1024 * 1024  # Preserve room for the live DB, WAL and normal app writes.
CONTEXT_KEYS = ("match_id", "internal_match_id", "league_id", "league_name", "season",
                "kickoff_iso", "home_team_id", "away_team_id", "home_team", "away_team",
                "elapsed", "status_at_receipt", "fixture_received_at")
SECRET_KEY = re.compile(r"password|secret|token|authorization|api.?key|headers", re.I)


class ArchivePayloadError(ValueError):
    """Invalid or oversized untrusted JSON; never include original data in errors."""


def utc_stamp(value=None):
    value = datetime.now(timezone.utc) if value is None else value
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware receipt timestamp is required")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _exists(conn, table):
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def _disk_free_bytes(conn):
    """Best-effort free bytes for the filesystem holding SQLite main, never its path."""
    try:
        for _, name, filename in conn.execute("PRAGMA database_list").fetchall():
            if name == "main" and filename:
                return int(shutil.disk_usage(Path(filename).resolve().parent).free)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return None
    return None


def ensure_match_record_schema(conn):
    """Called only during ingestion. No executescript or implicit/explicit commit."""
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    conn.execute('''CREATE TABLE IF NOT EXISTS match_record_observations(
        id INTEGER PRIMARY KEY, provider TEXT NOT NULL, fixture_id TEXT NOT NULL,
        section TEXT NOT NULL, received_at TEXT NOT NULL, payload_hash TEXT NOT NULL,
        context_json TEXT NOT NULL, payload_z BLOB NOT NULL, raw_bytes INTEGER NOT NULL,
        UNIQUE(provider,fixture_id,section,received_at,payload_hash))''')
    conn.execute('''CREATE INDEX IF NOT EXISTS idx_match_record_lookup
        ON match_record_observations(provider,fixture_id,section,received_at DESC,id DESC)''')
    conn.execute('''CREATE INDEX IF NOT EXISTS idx_match_record_history
        ON match_record_observations(provider,fixture_id,received_at DESC,id DESC)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS match_record_archive_budget(
        id INTEGER PRIMARY KEY CHECK(id=1),byte_count INTEGER NOT NULL DEFAULT 0,
        row_count INTEGER NOT NULL DEFAULT 0)''')
    conn.execute('''INSERT OR IGNORE INTO match_record_archive_budget(id,byte_count,row_count)
        SELECT 1,COALESCE(SUM(length(payload_z)+length(CAST(context_json AS BLOB))),0),COUNT(*)
        FROM match_record_observations WHERE NOT EXISTS
        (SELECT 1 FROM match_record_archive_budget WHERE id=1)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS match_record_archive_gaps(
        provider TEXT NOT NULL,fixture_id TEXT NOT NULL,section TEXT NOT NULL,reason TEXT NOT NULL,
        first_at TEXT NOT NULL,last_at TEXT NOT NULL,count INTEGER NOT NULL,
        PRIMARY KEY(provider,fixture_id,section,reason))''')


def _row(cursor):
    value = cursor.fetchone()
    return dict(zip((c[0] for c in cursor.description), value)) if value is not None else {}


class ArchiveStateError(ValueError):
    """Archive accounting is not verifiable; never repair it by guessing."""


def _validated_budget(conn):
    """Validate stored types/ranges, not a reconciliation of every archived row.

    INTEGER affinity does not guarantee an integer in SQLite. A negative,
    fractional, text or missing counter cannot authorize another append or be
    presented as trustworthy capacity. Reads never rebuild damaged accounting.
    """
    budget = _row(conn.execute("SELECT byte_count,row_count FROM match_record_archive_budget WHERE id=1"))
    if not budget or any(type(budget.get(key)) is not int or budget[key] < 0
                         for key in ("byte_count", "row_count")):
        raise ArchiveStateError("Archive capacity is not verifiable")
    return budget


def _context(conn, fid, stamp):
    # Provider-specific tables only: never match an unrelated local/external ID.
    candidates = []
    for table, clock in (("api_football_live_snapshots", "last_synced_at"),
                         ("api_football_fixture_index", "last_seen_at")):
        if not _exists(conn, table):
            continue
        r = _row(conn.execute(f"SELECT * FROM {table} WHERE fixture_id=? LIMIT 1", (fid,)))
        if not r:
            continue
        try:
            observed = utc_stamp(r.get(clock)) if r.get(clock) else None
        except (ValueError, TypeError):
            observed = None
        # Never attach a later context/minute to an earlier receipt.
        if not observed or observed > stamp:
            continue
        ctx = {k: r.get(k) for k in CONTEXT_KEYS if k in r}
        ctx.update(status_at_receipt=r.get("status_short") or r.get("status"),
                   fixture_received_at=observed)
        candidates.append((observed, ctx))
    return max(candidates, key=lambda item: item[0])[1] if candidates else {}


def _clean_json(value):
    budget = {"nodes": 0, "bytes": 0}

    def visit(obj, depth=0):
        budget["nodes"] += 1
        if depth > 20 or budget["nodes"] > 20_000:
            raise ArchivePayloadError("JSON structure limit")
        if isinstance(obj, dict):
            out = {}
            for key, item in obj.items():
                if not isinstance(key, str):
                    raise ArchivePayloadError("Non-string JSON key")
                if SECRET_KEY.search(key):
                    continue
                budget["bytes"] += len(key.encode("utf-8"))
                if budget["bytes"] > MAX_RAW_BYTES:
                    raise ArchivePayloadError("Payload limit")
                out[key] = visit(item, depth+1)
            return out
        if isinstance(obj, (list, tuple)):
            if len(obj) > 2000:
                raise ArchivePayloadError("Array limit")
            return [visit(item, depth+1) for item in obj]
        if isinstance(obj, str):
            budget["bytes"] += len(obj.encode("utf-8"))
            if budget["bytes"] > MAX_RAW_BYTES:
                raise ArchivePayloadError("Payload limit")
            return obj
        if type(obj) is float and not math.isfinite(obj):
            raise ArchivePayloadError("Non-finite number")
        if obj is None or type(obj) in (int, float, bool):
            return obj
        raise ArchivePayloadError("Non-JSON object")

    return visit(value)


def _gap(conn, fid, section, stamp, reason):
    key = (PROVIDER, fid, section, reason)
    if not conn.execute('''SELECT 1 FROM match_record_archive_gaps
            WHERE provider=? AND fixture_id=? AND section=? AND reason=?''', key).fetchone():
        count = conn.execute("SELECT COUNT(*) FROM match_record_archive_gaps").fetchone()[0]
        if count >= MAX_GAP_KEYS:
            fid = "*"  # Bounded aggregate for further fixtures, not a fabricated match.
    conn.execute('''INSERT INTO match_record_archive_gaps VALUES(?,?,?,?,?,?,1)
        ON CONFLICT(provider,fixture_id,section,reason) DO UPDATE SET
        first_at=min(first_at,excluded.first_at),last_at=max(last_at,excluded.last_at),
        count=match_record_archive_gaps.count+1''', (PROVIDER,fid,section,reason,stamp,stamp))
    return {"stored": False, "reason": reason}


def record_observation(conn, fixture_id, section, payload, *, received_at=None, context=None):
    """Record a response using the existing ingest connection, without committing.

    Empty successful arrays are retained; malformed responses are a gap, not
    zero-valued statistics. Repeated payloads at distinct receipts remain history.
    A retry with identical time/content/context is idempotent. No pruning.
    """
    fid = str(fixture_id).strip()
    if section not in SECTIONS or not re.fullmatch(r"[0-9]{1,24}", fid):
        raise ValueError("Unsupported provider-scoped identity")
    stamp = utc_stamp(received_at)
    if not _exists(conn, "match_record_observations"):
        ensure_match_record_schema(conn)
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    if section == "fixture":
        if not isinstance(payload, dict) or not isinstance(payload.get("fixture"), dict):
            return _gap(conn,fid,section,stamp,"INVALID_PAYLOAD")
        if str(payload["fixture"].get("id")) != fid:
            return _gap(conn,fid,section,stamp,"IDENTITY_MISMATCH")
    elif not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        return _gap(conn,fid,section,stamp,"INVALID_PAYLOAD")
    try:
        clean = _clean_json(payload)
        raw = json.dumps(clean,ensure_ascii=False,sort_keys=True,separators=(",", ":"),allow_nan=False).encode("utf-8")
        if len(raw) > MAX_RAW_BYTES:
            return _gap(conn,fid,section,stamp,"PAYLOAD_LIMIT")
        ctx = _context(conn,fid,stamp) if context is None else {k:v for k,v in context.items() if k in CONTEXT_KEYS}
        ctx_raw = json.dumps(_clean_json(ctx),ensure_ascii=False,sort_keys=True,separators=(",", ":"),allow_nan=False).encode("utf-8")
        if len(ctx_raw) > 8192:
            return _gap(conn,fid,section,stamp,"CONTEXT_LIMIT")
    except (ValueError,TypeError,OverflowError,UnicodeError,RecursionError):
        return _gap(conn,fid,section,stamp,"INVALID_OR_OVERSIZED_PAYLOAD")
    envelope = json.dumps([PROVIDER,fid,section,stamp],separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(envelope+b"\x00"+raw+b"\x00"+ctx_raw).hexdigest()
    identity = (PROVIDER,fid,section,stamp,digest)
    if conn.execute('''SELECT 1 FROM match_record_observations
            WHERE provider=? AND fixture_id=? AND section=? AND received_at=? AND payload_hash=?''', identity).fetchone():
        return {"stored": False, "reason": "DUPLICATE_RECEIPT"}
    try:
        _validated_budget(conn)
    except ArchiveStateError:
        return _gap(conn,fid,section,stamp,"ARCHIVE_BUDGET_UNVERIFIABLE")
    zipped = zlib.compress(raw,6)
    size = len(zipped)+len(ctx_raw)
    disk_free = _disk_free_bytes(conn)
    if disk_free is not None and disk_free - size < MIN_FREE_DISK_BYTES:
        return _gap(conn,fid,section,stamp,"DISK_RESERVE_REACHED")
    conn.execute("SAVEPOINT match_record_insert")
    try:
        changed = conn.execute('''UPDATE match_record_archive_budget
            SET byte_count=byte_count+?,row_count=row_count+1
            WHERE id=1 AND byte_count+?<=? AND row_count<?''',
            (size,size,MAX_ARCHIVE_BYTES,MAX_OBSERVATIONS)).rowcount
        if not changed:
            conn.execute("RELEASE match_record_insert")
            return _gap(conn,fid,section,stamp,"ARCHIVE_CAP_REACHED")
        conn.execute('''INSERT INTO match_record_observations
            (provider,fixture_id,section,received_at,payload_hash,context_json,payload_z,raw_bytes)
            VALUES(?,?,?,?,?,?,?,?)''', (*identity,ctx_raw.decode("utf-8"),zipped,len(raw)))
        conn.execute("RELEASE match_record_insert")
    except BaseException:
        conn.execute("ROLLBACK TO match_record_insert")
        conn.execute("RELEASE match_record_insert")
        raise
    return {"stored": True, "reason": "RECORDED", "received_at": stamp}


def decode_observation(row):
    """Bounded, integrity-checked decoding for internal analysis, not a public API."""
    data = dict(row)
    compressed = data["payload_z"]
    if not isinstance(compressed, bytes) or len(compressed) > MAX_RAW_BYTES+1024:
        raise ArchivePayloadError("Invalid compressed payload size")
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(compressed, MAX_RAW_BYTES+1)
        context = data["context_json"].encode("utf-8")
        if len(raw) > MAX_RAW_BYTES or len(context)>8192 or not inflater.eof or inflater.unused_data:
            raise ArchivePayloadError("Invalid archived payload")
        envelope = json.dumps([data["provider"],data["fixture_id"],data["section"],data["received_at"]],separators=(",", ":")).encode("utf-8")
        if len(raw) != data["raw_bytes"] or hashlib.sha256(envelope+b"\x00"+raw+b"\x00"+context).hexdigest() != data["payload_hash"]:
            raise ArchivePayloadError("Archive integrity mismatch")
        payload, context = json.loads(raw), json.loads(context)
    except (zlib.error,UnicodeError,KeyError,TypeError,ValueError) as exc:
        raise ArchivePayloadError("Invalid archived payload") from exc
    return {"provider":data["provider"], "fixture_id":data["fixture_id"], "section":data["section"],
            "received_at":data["received_at"], "payload":payload, "context":context, "id":data["id"]}


def archive_health(conn):
    """Read-only operational totals; never a claim that match coverage is complete."""
    try:
        if not _exists(conn, "match_record_archive_budget"):
            return {"state":"NOT_INITIALIZED", "coverage_complete":False}
        budget = _validated_budget(conn)
        gaps = conn.execute("SELECT COALESCE(SUM(count),0) FROM match_record_archive_gaps").fetchone()[0]
        disk_free = _disk_free_bytes(conn)
        disk_guard_state = ("UNKNOWN" if disk_free is None else
                            "LOW" if disk_free < MIN_FREE_DISK_BYTES else "OK")
        return {"state":"GAPS_RECORDED" if gaps else "OBSERVATIONS_STORED" if budget["row_count"] else "EMPTY",
                "observations":budget["row_count"], "encoded_bytes":budget["byte_count"],
                "encoded_byte_limit":MAX_ARCHIVE_BYTES, "row_limit":MAX_OBSERVATIONS,
                "gap_count":gaps, "coverage_complete":False,
                "disk_free_bytes":disk_free, "disk_reserve_bytes":MIN_FREE_DISK_BYTES,
                "disk_guard_state":disk_guard_state,
                "size_scope":"ENCODED_PAYLOAD_AND_CONTEXT_NOT_SQLITE_FILE"}
    except (sqlite3.Error, ArchiveStateError):
        return {"state":"READ_UNAVAILABLE", "coverage_complete":False}
