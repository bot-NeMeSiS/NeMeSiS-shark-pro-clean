"""Internal, read-only inspection of a provider-scoped match archive.

Requires an explicit local DB path. Does not call providers, create a DB, run
migrations, backfill timestamps, alter historical data or expose a web endpoint.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.match_record_archive import PROVIDER, SECTIONS, decode_observation, utc_stamp


def inspect_archive(db_path, fixture_id, *, section=None, as_of=None, include_payload=False):
    fid = str(fixture_id)
    if not re.fullmatch(r"[0-9]{1,24}", fid) or (section is not None and section not in SECTIONS):
        raise ValueError("Use an API-Football fixture ID and a supported section")
    cutoff = utc_stamp(as_of) if as_of is not None else None
    path = Path(db_path).expanduser().resolve()
    result = {"provider": PROVIDER, "fixture_id": fid, "as_of": cutoff,
              "state": "NOT_INITIALIZED", "observations": 0, "sections": {},
              "network_calls": 0, "writes": 0, "clock_semantics": "NEMESIS_RECEIPT_NOT_PROVIDER_TIME"}
    if not path.is_file():
        return {**result, "state": "DATABASE_NOT_FOUND"}
    try:
        with closing(sqlite3.connect(path.as_uri()+"?mode=ro", uri=True, timeout=.3)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='match_record_observations'").fetchone():
                return result
            params, where = [PROVIDER, fid], "provider=? AND fixture_id=?"
            if cutoff:
                where += " AND received_at<=?"; params.append(cutoff)
            if section:
                where += " AND section=?"; params.append(section)
            result["observations"] = conn.execute("SELECT COUNT(*) FROM match_record_observations WHERE "+where,params).fetchone()[0]
            for key in ([section] if section else sorted(SECTIONS)):
                row = conn.execute("SELECT * FROM match_record_observations WHERE "+where+
                    " AND section=? ORDER BY received_at DESC,id DESC LIMIT 1",[*params,key]).fetchone()
                if row is None:
                    continue
                item = decode_observation(row)
                value = {"received_at":item["received_at"],"context":item["context"],
                         "state":"EMPTY_RECEIVED" if item["payload"] == [] else "OBSERVED"}
                if include_payload:
                    value["payload"] = item["payload"]
                result["sections"][key] = value
            result["state"] = "OBSERVATIONS_AVAILABLE" if result["observations"] else "NO_OBSERVATIONS_AT_CUTOFF"
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='match_record_archive_gaps'").fetchone():
                result["current_archive_gaps"] = [dict(row) for row in conn.execute(
                    "SELECT section,reason,first_at,last_at,count FROM match_record_archive_gaps WHERE provider=? AND fixture_id IN (?, '*') LIMIT 64",(PROVIDER,fid))]
                result["gap_scope"] = "CURRENT_ARCHIVE_HEALTH_NOT_AS_OF_DATA"
            return result
    except (sqlite3.Error,ValueError,TypeError,KeyError):
        return {**result, "state":"READ_UNAVAILABLE", "sections":{}}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",required=True,help="Existing local SQLite file (read-only)")
    parser.add_argument("--fixture",required=True,help="API-Football ID, NOT local match ID")
    parser.add_argument("--section",choices=sorted(SECTIONS))
    parser.add_argument("--as-of",help="Aware ISO timestamp: limit to data already received")
    parser.add_argument("--include-payload",action="store_true",help="Include internal provider JSON; not for redistribution")
    args=parser.parse_args(argv)
    try:
        result=inspect_archive(args.db,args.fixture,section=args.section,as_of=args.as_of,include_payload=args.include_payload)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result["state"] in {"READ_UNAVAILABLE","DATABASE_NOT_FOUND"} else 0


if __name__=="__main__":
    raise SystemExit(main())
