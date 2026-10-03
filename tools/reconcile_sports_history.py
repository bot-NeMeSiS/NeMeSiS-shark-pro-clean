"""Apply an explicit reviewed ID link, retaining source data and audit evidence."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engines.sports_history_engine import ensure_schema
from engines.sports_history_reconciliation import reconcile_identity


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    parser.add_argument('--kind',required=True,choices=['team','competition','player','stadium','referee'])
    parser.add_argument('--source',required=True)
    parser.add_argument('--external-id',required=True)
    parser.add_argument('--canonical-id',required=True)
    parser.add_argument('--evidence',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(dict(status='preview',kind=args.kind,source=args.source,external_id=args.external_id,target=args.canonical_id,external_calls=0)))
        return 0
    if not Path(args.database).is_file():
        parser.error('Select an existing database')
    conn=sqlite3.connect(args.database)
    try:
        ensure_schema(conn)
        with conn:
            result=reconcile_identity(conn,args.kind,args.source,args.external_id,args.canonical_id,args.evidence)
        print(json.dumps(result))
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
