"""Lossless, content-addressed storage for repeated statistics responses.

Legacy history rows remain readable. Every new reference retains the EXACT UTF-8
JSON text, not just the displayed metric. Callers own transactions; readers never
initialize schema. Rewriting old rows is an explicit offline operation, never a
side effect of importing this module or opening a page.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import zlib

TABLE = "statistics_payload_blobs_v1"
MARKER = "__nemesis_stats_payload_v1__"
PREFIX = '{"' + MARKER + '":'
MAX_RAW = 1024 * 1024
MIN_RAW = 256


class PayloadStorageError(ValueError):
    """Closed diagnostic codes; never include provider contents."""


def ensure_schema(conn: sqlite3.Connection) -> None:
    if not conn.in_transaction:
        raise PayloadStorageError("CALLER_TRANSACTION_REQUIRED")
    conn.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE}(
        digest TEXT PRIMARY KEY CHECK(length(digest)=64),
        raw_bytes INTEGER NOT NULL CHECK(raw_bytes>0 AND raw_bytes<={MAX_RAW}),
        payload_z BLOB NOT NULL) WITHOUT ROWID''')


def _decode(blob, size, digest):
    if (type(size) is not int or not 0 < size <= MAX_RAW
            or not isinstance(blob, bytes) or not 0 < len(blob) <= MAX_RAW + 1024
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise PayloadStorageError("INVALID_BLOB_CONTRACT")
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(blob, size + 1)
        if (len(raw) != size or not inflater.eof or inflater.unused_data
                or inflater.unconsumed_tail or hashlib.sha256(raw).hexdigest() != digest):
            raise PayloadStorageError("BLOB_INTEGRITY_MISMATCH")
        return raw.decode("utf-8")
    except (zlib.error, UnicodeError) as exc:
        raise PayloadStorageError("BLOB_DECODE_REJECTED") from exc


def read_payload(conn: sqlite3.Connection, text):
    """Hydrate a compact row, or return a legacy value without any DB write."""
    if not isinstance(text, str) or MARKER not in text:
        return text
    try:
        ref = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise PayloadStorageError("INVALID_REFERENCE") from exc
    if not isinstance(ref, dict) or MARKER not in ref:
        return text
    if "team" in ref and "statistics" in ref:
        return text  # A provider field must not accidentally become a reference.
    if (set(ref) != {MARKER, "bytes"}
            or not isinstance(ref[MARKER], str) or not re.fullmatch(r"[0-9a-f]{64}", ref[MARKER])
            or type(ref["bytes"]) is not int or not 0 < ref["bytes"] <= MAX_RAW):
        raise PayloadStorageError("INVALID_REFERENCE")
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone():
        raise PayloadStorageError("REFERENCE_STORE_MISSING")
    row = conn.execute(f"SELECT raw_bytes,payload_z FROM {TABLE} WHERE digest=?", (ref[MARKER],)).fetchone()
    if row is None:
        raise PayloadStorageError("REFERENCE_TARGET_MISSING")
    if row[0] != ref["bytes"]:
        raise PayloadStorageError("REFERENCE_SIZE_MISMATCH")
    return _decode(row[1], row[0], ref[MARKER])


def store_payload(conn: sqlite3.Connection, text: str) -> str:
    """Store once, preserving original serialization, including whitespace/order."""
    if not conn.in_transaction:
        raise PayloadStorageError("CALLER_TRANSACTION_REQUIRED")
    if not isinstance(text, str):
        raise PayloadStorageError("JSON_TEXT_REQUIRED")
    # Repacking an already compact row must validate its target, never nest refs.
    hydrated = read_payload(conn, text)
    if hydrated != text:
        return text
    raw = text.encode("utf-8")
    if not MIN_RAW <= len(raw) <= MAX_RAW:
        return text  # No truncation or dropped provider fields at either boundary.
    digest = hashlib.sha256(raw).hexdigest()
    reference = json.dumps({MARKER: digest, "bytes": len(raw)}, separators=(",", ":"))
    encoded = zlib.compress(raw, 6)
    # Require a conservative benefit even for a first unique block, before reuse.
    if len(encoded) + len(reference.encode()) + 128 >= len(raw):
        return text
    existing = conn.execute(f"SELECT raw_bytes,payload_z FROM {TABLE} WHERE digest=?", (digest,)).fetchone()
    if existing is None:
        conn.execute(f"INSERT INTO {TABLE}(digest,raw_bytes,payload_z) VALUES(?,?,?)",
                     (digest, len(raw), encoded))
    elif _decode(existing[1], existing[0], digest) != text:
        raise PayloadStorageError("EXISTING_BLOB_MISMATCH")
    return reference


def rewrite_history_batch(conn: sqlite3.Connection, *, after_rowid=0, limit=100,
                          deadline=None, reverse=False) -> dict:
    """Explicit, reversible, bounded migration in the caller's transaction.

    No commits, DELETE, DROP, VACUUM, external calls or scheduled execution.
    Only payload_json changes; every other value, row ID and timestamp is kept.
    A failed batch rolls back its changes and newly inserted blobs together.
    """
    if not conn.in_transaction:
        raise PayloadStorageError("CALLER_TRANSACTION_REQUIRED")
    if (type(after_rowid) is not int or after_rowid < 0 or type(limit) is not int
            or not 1 <= limit <= 1000 or type(reverse) is not bool):
        raise PayloadStorageError("INVALID_BATCH_BOUNDS")
    def check():
        if deadline is not None and time.monotonic() >= deadline:
            raise PayloadStorageError("MIGRATION_BUDGET_EXHAUSTED")
    check()
    conn.execute("SAVEPOINT statistics_payload_batch")
    try:
        ensure_schema(conn)
        rows = conn.execute('''SELECT rowid,payload_json FROM api_football_match_stats_history
                               WHERE rowid>? ORDER BY rowid LIMIT ?''', (after_rowid, limit)).fetchall()
        changed = 0
        for rowid, raw in rows:
            check()
            replacement = read_payload(conn, raw) if reverse else store_payload(conn, raw) if isinstance(raw, str) else raw
            if replacement != raw:
                if read_payload(conn, replacement) != read_payload(conn, raw):
                    raise PayloadStorageError("MIGRATION_ROUNDTRIP_MISMATCH")
                conn.execute("UPDATE api_football_match_stats_history SET payload_json=? WHERE rowid=?",
                             (replacement, rowid))
                changed += 1
        check()
        conn.execute("RELEASE statistics_payload_batch")
    except BaseException:
        # SQLITE_FULL/INTERRUPT may already abort the outer transaction.
        # Its savepoint is then gone; preserve the original SQLite error.
        if conn.in_transaction:
            conn.execute("ROLLBACK TO statistics_payload_batch")
            conn.execute("RELEASE statistics_payload_batch")
        raise
    return {"scanned": len(rows), "changed": changed,
            "last_rowid": rows[-1][0] if rows else after_rowid, "reverse": bool(reverse)}
