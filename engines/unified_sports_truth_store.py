"""SQLite repository for Unified Sports Truth. Ingestors own transactions.

Public reads never create schemas, mutate records, or contact providers.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import threading

from engines.snapshot_copy_engine import clone_snapshot
from engines.unified_sports_truth_engine import (
    GROUPS, _json, _present, instant, provider_name, evidence_from_row,
    resolve_match, legacy_projection, adapt_section,
)

_STORE_REVISIONS = OrderedDict()
_CACHE_LOCK = threading.RLock()

# Latest-decision receipts are a bounded cache, not a second unbounded archive.
# match_record_archive owns historical raw observations; this store keeps only
# the current resolvable evidence needed by Unified Sports Truth.
MAX_RECEIPT_BYTES = 256 * 1024
MIN_FREE_DISK_BYTES = 128 * 1024 * 1024


def _disk_free_bytes(conn):
    """Free bytes for persistent SQLite; in-memory QA has no filesystem reserve."""
    try:
        for _seq, name, filename in conn.execute("PRAGMA database_list").fetchall():
            if name != "main":
                continue
            if not filename:
                return None
            try:
                return int(shutil.disk_usage(Path(filename).resolve().parent).free)
            except (OSError, TypeError, ValueError):
                return -1
    except sqlite3.Error:
        return -1
    return -1


def _encode_bounded_receipt(receipt):
    """Prefer full evidence, compact diagnostics first, never truncate factual values."""
    encoded = json.dumps(receipt, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) <= MAX_RECEIPT_BYTES:
        return encoded
    compact = clone_snapshot(receipt)
    compact["raw"] = {}
    compact["raw_compacted"] = True
    encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    return encoded if len(encoded.encode("utf-8")) <= MAX_RECEIPT_BYTES else None


def _receipt_capacity_available(conn, encoded_size):
    free = _disk_free_bytes(conn)
    if free is None:  # in-memory/local QA only
        return True
    if free < 0:  # persistent capacity could not be verified
        return False
    return free - int(encoded_size) >= MIN_FREE_DISK_BYTES

def ensure_schema(conn):
    # execute, never executescript: caller retains transaction ownership.
    conn.execute("""CREATE TABLE IF NOT EXISTS sports_truth_receipts (
        match_id TEXT NOT NULL, provider TEXT NOT NULL, evidence_json TEXT NOT NULL,
        observed_at TEXT, PRIMARY KEY(match_id,provider))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sports_truth_mappings (
        entity_type TEXT NOT NULL, provider TEXT NOT NULL, provider_id TEXT NOT NULL,
        canonical_id TEXT NOT NULL, proof TEXT NOT NULL,
        PRIMARY KEY(entity_type,provider,provider_id))""")
    conn.execute("CREATE INDEX IF NOT EXISTS sports_truth_provider_id ON sports_truth_mappings(provider_id)")
    conn.execute("CREATE TABLE IF NOT EXISTS sports_truth_generation (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL)")
    conn.execute("INSERT OR IGNORE INTO sports_truth_generation VALUES(1,0)")


def invalidate_changed_store(conn, cache_key):
    """Detect committed ingest in other workers, with bounded local metadata."""
    try:
        row = conn.execute("SELECT revision FROM sports_truth_generation WHERE id=1").fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return
        raise
    if not row:
        return
    revision = row[0]
    with _CACHE_LOCK:
        previous = _STORE_REVISIONS.get(cache_key)
        _STORE_REVISIONS[cache_key] = revision
        _STORE_REVISIONS.move_to_end(cache_key)
        while len(_STORE_REVISIONS) > 32:
            _STORE_REVISIONS.popitem(last=False)
    if previous != revision:
        from engines.v934_realtime_sports_engine import invalidate_realtime_cache
        invalidate_realtime_cache(cache_key)


def bind_identity(conn, entity_type, provider, provider_id, canonical_id, *, proof):
    """Only explicit, unique mappings; a conflicting mapping is never replaced."""
    if entity_type not in {"match", "team", "competition", "player"} or not all((provider_id, canonical_id, proof)):
        return False
    ensure_schema(conn)
    key = (entity_type, provider_name(provider), str(provider_id))
    prior = conn.execute("SELECT canonical_id FROM sports_truth_mappings WHERE entity_type=? AND provider=? AND provider_id=?", key).fetchone()
    if prior and prior[0] != str(canonical_id):
        return False
    inserted = conn.execute("INSERT OR IGNORE INTO sports_truth_mappings VALUES(?,?,?,?,?)", (*key, str(canonical_id), str(proof)))
    if inserted.rowcount:
        conn.execute("UPDATE sports_truth_generation SET revision=revision+1 WHERE id=1")
    return True


def persist_receipt(conn, match_id, row, *, provider=None):
    ensure_schema(conn)
    receipt = evidence_from_row(row, provider=provider)
    observed = receipt["groups"]["state"]["observed_at"]
    prior = conn.execute("SELECT observed_at,evidence_json FROM sports_truth_receipts WHERE match_id=? AND provider=?", (str(match_id), receipt["provider"])).fetchone()
    if prior:
        previous = _json(prior[1])
        for group, fields in GROUPS.items():
            incoming = receipt["groups"][group]
            old = previous.get("groups", {}).get(group) or {}
            has_group = any(_present(receipt["values"].get(field)) for field in fields) or incoming.get("state") != "AVAILABLE"
            had_group = any(_present(previous.get("values", {}).get(field)) for field in fields) or old.get("state", "AVAILABLE") != "AVAILABLE"
            older = had_group and instant(old.get("observed_at")) and (not instant(incoming.get("observed_at")) or instant(incoming["observed_at"]) < instant(old["observed_at"]))
            if not has_group or older:
                receipt["groups"][group] = clone_snapshot(old)
                if group in previous.get("raw", {}):
                    receipt["raw"][group] = clone_snapshot(previous["raw"][group])
                for field in fields:
                    receipt["values"][field] = clone_snapshot(previous.get("values", {}).get(field))
                if group == "state":
                    receipt["values"]["_status_signals"] = clone_snapshot(previous.get("values", {}).get("_status_signals", {}))
        observed = receipt["groups"]["state"].get("observed_at")

    # Never let this latest-decision cache compete with /data recovery headroom.
    # Raw diagnostics are expendable because the append-only match_record_archive
    # retains authorized provider history. Factual normalized values are never
    # silently truncated: an oversized receipt simply is not persisted.
    encoded = _encode_bounded_receipt(receipt)
    if encoded is None or not _receipt_capacity_available(conn, len(encoded.encode("utf-8"))):
        return False

    # Identity mappings are written only after the receipt is known to be safe to
    # store; a rejected oversized/low-disk receipt must not mutate canonical IDs.
    if receipt["provider_id"] and not bind_identity(conn, "match", receipt["provider"], receipt["provider_id"], match_id, proof="EXPLICIT_INGEST_TARGET"):
        return False
    if provider is not None:
        for kind, fields in (("team", ("home_team_id", "away_team_id")), ("competition", ("competition_id",))):
            for field in fields:
                identifier = receipt["values"].get(field)
                if _present(identifier):
                    bind_identity(conn, kind, receipt["provider"], identifier, f"{receipt['provider']}:{kind}:{identifier}", proof="NAMESPACED_PROVIDER_ID")
        for player in row.get("players") or []:
            identifier = player.get("id") or player.get("player_id") if isinstance(player, dict) else None
            if identifier:
                bind_identity(conn, "player", receipt["provider"], identifier, f"{receipt['provider']}:player:{identifier}", proof="NAMESPACED_PROVIDER_ID")

    if not prior or prior[1] != encoded:
        conn.execute("INSERT OR REPLACE INTO sports_truth_receipts VALUES(?,?,?,?)",
                     (str(match_id), receipt["provider"], encoded, observed))
        conn.execute("UPDATE sports_truth_generation SET revision=revision+1 WHERE id=1")
    return True

def persist_api_section(conn, fixture_id, group, payload, *, observed_at, availability="AVAILABLE"):
    """Persist an already authorized section, resolving only explicit local IDs."""
    if group not in GROUPS:
        return False
    ensure_schema(conn)
    mapping = conn.execute("SELECT canonical_id FROM sports_truth_mappings WHERE entity_type='match' AND provider='api_football' AND provider_id=?", (str(fixture_id),)).fetchone()
    if not mapping:
        # Deep sync has its own explicit fixture index. Never assume that an
        # external ID equals a local ID or another provider's event ID.
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='api_football_fixture_index'").fetchone()
        if exists:
            mapping = conn.execute("SELECT internal_match_id FROM api_football_fixture_index WHERE fixture_id=?", (str(fixture_id),)).fetchone()
    if not mapping or not mapping[0]:
        return False
    existing = conn.execute("SELECT evidence_json FROM sports_truth_receipts WHERE match_id=? AND provider='api_football'", (str(mapping[0]),)).fetchone()
    context = _json(existing[0]).get("values", {}) if existing else {}
    raw_payload = payload
    payload = adapt_section(group, payload, context)
    if group == "stats" and isinstance(payload, dict) and not payload.get("available") and availability == "AVAILABLE":
        has_values = isinstance(raw_payload, list) and any(s.get("value") is not None for b in raw_payload if isinstance(b, dict) for s in b.get("statistics", []) if isinstance(s, dict))
        availability = "UNRESOLVED_IDENTITY" if has_values else "EMPTY_CONFIRMED"
    return bool(persist_receipt(conn, mapping[0], {"source": "api_football", "external_id": str(fixture_id),
        group: payload, "last_synced_at": observed_at, "coverage": {group: availability},
        "raw_json": json.dumps({group: raw_payload}, ensure_ascii=False), "context_status": context.get("status")}, provider="api_football"))


def rehome_receipts(conn, old_id, new_id):
    """Move latest truth after exact-identity dedupe without increasing storage."""
    if str(old_id) == str(new_id):
        return True
    ensure_schema(conn)
    old_rows = conn.execute(
        "SELECT provider,evidence_json,observed_at FROM sports_truth_receipts WHERE match_id=?",
        (str(old_id),),
    ).fetchall()
    for provider, encoded, observed in old_rows:
        previous = conn.execute(
            "SELECT observed_at,evidence_json FROM sports_truth_receipts WHERE match_id=? AND provider=?",
            (str(new_id), provider),
        ).fetchone()
        if not previous:
            # Primary-key rewrite keeps the same evidence bytes and does not
            # allocate a second latest receipt.
            conn.execute(
                "UPDATE sports_truth_receipts SET match_id=? WHERE match_id=? AND provider=?",
                (str(new_id), str(old_id), provider),
            )
            continue

        incoming, retained = _json(encoded), _json(previous[1])
        for group, fields in GROUPS.items():
            a, b = incoming.get("groups", {}).get(group, {}), retained.get("groups", {}).get(group, {})
            available = any(_present(incoming.get("values", {}).get(field)) for field in fields) or a.get("state") != "AVAILABLE"
            retained_available = any(_present(retained.get("values", {}).get(field)) for field in fields) or b.get("state", "AVAILABLE") != "AVAILABLE"
            older = retained_available and instant(b.get("observed_at")) and (not instant(a.get("observed_at")) or instant(a["observed_at"]) < instant(b["observed_at"]))
            if not available or older:
                incoming["groups"][group] = clone_snapshot(b)
                for field in fields:
                    incoming["values"][field] = clone_snapshot(retained.get("values", {}).get(field))
                if group in retained.get("raw", {}):
                    incoming["raw"][group] = clone_snapshot(retained["raw"][group])
                if group == "state":
                    incoming["values"]["_status_signals"] = clone_snapshot(retained.get("values", {}).get("_status_signals", {}))

        bounded = _encode_bounded_receipt(incoming)
        if bounded is not None:
            old_bytes = len(str(encoded).encode("utf-8"))
            target_bytes = len(str(previous[1]).encode("utf-8"))
            merged_bytes = len(bounded.encode("utf-8"))
            net_growth = max(0, merged_bytes - old_bytes - target_bytes)
            if net_growth and not _receipt_capacity_available(conn, net_growth):
                bounded = None

        if bounded is None:
            # Never replace coherent truth with an arbitrary keeper merely
            # because a merged deep section is too large. Pick the most recent
            # whole receipt that itself fits the bounded cache.
            candidates = []
            for candidate in (incoming, retained):
                candidate_encoded = _encode_bounded_receipt(candidate)
                if candidate_encoded is None:
                    continue
                state_clock = instant((candidate.get("groups", {}).get("state") or {}).get("observed_at"))
                candidates.append((state_clock or datetime.min.replace(tzinfo=timezone.utc), candidate_encoded, candidate))
            if candidates:
                _clock, bounded, selected = max(candidates, key=lambda item: item[0])
                observed = (selected.get("groups", {}).get("state") or {}).get("observed_at")
            else:
                bounded = None
                observed = previous[0]
        else:
            observed = incoming["groups"]["state"].get("observed_at")

        # Delete the duplicate first. The replacement cannot consume more net
        # bytes than the two rows that existed before this exact-identity merge.
        conn.execute(
            "DELETE FROM sports_truth_receipts WHERE match_id=? AND provider=?",
            (str(old_id), provider),
        )
        if bounded is not None:
            conn.execute(
                "UPDATE sports_truth_receipts SET evidence_json=?,observed_at=? WHERE match_id=? AND provider=?",
                (bounded, observed, str(new_id), provider),
            )

    conn.execute("UPDATE sports_truth_mappings SET canonical_id=?, proof='EXISTING_EXACT_FIXTURE_DEDUPE' WHERE entity_type='match' AND canonical_id=?", (str(new_id), str(old_id)))
    bind_identity(conn, "match", "local_cache", old_id, new_id, proof="EXISTING_ROUTE_ALIAS")
    # Covers legacy/partial states where a receipt lacked a provider row above.
    conn.execute("DELETE FROM sports_truth_receipts WHERE match_id=?", (str(old_id),))
    conn.execute("UPDATE sports_truth_generation SET revision=revision+1 WHERE id=1")
    return True

def project_rows(conn, rows, *, now=None, tables=None, cache=None):
    """One bulk read per table per batch. Never write or migrate on public reads."""
    if not rows:
        return rows
    evaluated = instant(now) or datetime.now(timezone.utc)
    if cache is not None:
        signatures = [hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest() for row in rows]
        pending = [i for i, key in enumerate(signatures) if key not in cache or not (instant(cache[key]["evaluated_at"]) <= evaluated < instant(cache[key]["valid_until"]))]
        if pending:
            projected = project_rows(conn, [rows[i] for i in pending], now=evaluated, tables=tables)
            for i, result in zip(pending, projected):
                cache[signatures[i]] = result["unified_sports_truth"]
        return [legacy_projection(row, clone_snapshot(cache[key])) for row, key in zip(rows, signatures)]
    tables = tables if tables is not None else {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    ids = [str(r.get("id") or r.get("match_id") or "") for r in rows]
    by_id = {key: [] for key in ids}
    # Bound SQL parameter count for large calendar/history batches.
    for start in range(0, len(ids), 400):
        chunk = ids[start:start+400]
        placeholders = ",".join("?" for _ in chunk)
        if "sports_truth_receipts" in tables:
            for key, encoded in conn.execute(f"SELECT match_id,evidence_json FROM sports_truth_receipts WHERE match_id IN ({placeholders})", chunk):
                receipt = _json(encoded)
                if isinstance(receipt, dict) and "values" in receipt:
                    by_id[key].append(receipt)
        if "api_football_live_snapshots" in tables:
            cur = conn.execute(f"SELECT * FROM api_football_live_snapshots WHERE match_id IN ({placeholders})", chunk)
            names = [c[0] for c in cur.description]
            for values in cur:
                raw = dict(zip(names, values))
                by_id[str(raw["match_id"])].append(evidence_from_row(raw, provider="api_football"))
    result = []
    for row, key in zip(rows, ids):
        receipts = by_id[key]
        base = evidence_from_row(row)
        # A merged legacy row may contain odds from a different observation.
        # Its explicit odds clock is independent from the football receipt.
        receipts = receipts + [base]
        # Only explicitly persisted mappings may unify entity IDs. Collect the
        # selected providers' IDs below in bulk, never match names fuzzily.
        by_id[key] = receipts
    provider_ids = {str(r["values"].get(field)) for receipts in by_id.values() for r in receipts
                    for field in ("home_team_id", "away_team_id", "competition_id") if _present(r["values"].get(field))}
    for receipts in by_id.values():
        for receipt in receipts:
            players = receipt["values"].get("players")
            if isinstance(players, list):
                provider_ids.update(str(p.get("id") or p.get("player_id")) for p in players if isinstance(p, dict) and (p.get("id") or p.get("player_id")))
    mappings = {}
    if "sports_truth_mappings" in tables and provider_ids:
        identifiers = sorted(provider_ids)
        for start in range(0, len(identifiers), 400):
            chunk = identifiers[start:start+400]
            placeholders = ",".join("?" for _ in chunk)
            for kind, provider, identifier, canonical in conn.execute(f"SELECT entity_type,provider,provider_id,canonical_id FROM sports_truth_mappings WHERE provider_id IN ({placeholders})", chunk):
                mappings[kind, provider, identifier] = canonical
    for row, key in zip(rows, ids):
        receipts = by_id[key]
        for receipt in receipts:
            receipt["entity_mappings"] = {field: mappings.get((kind, receipt["provider"], str(receipt["values"].get(field))))
                                          for kind, fields in (("team", ("home_team_id", "away_team_id")), ("competition", ("competition_id",))) for field in fields}
            receipt["player_mappings"] = {identifier: canonical for (kind, provider, identifier), canonical in mappings.items() if kind == "player" and provider == receipt["provider"]}
        result.append(legacy_projection(row, resolve_match(key, receipts, now=evaluated)))
    return result
