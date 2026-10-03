"""Preview or explicitly run one SportsDB season through the existing adapter."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engines.sports_history_backfill import run_season_backfill, season_request


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True)
    parser.add_argument('--league-id',required=True)
    parser.add_argument('--season',required=True)
    parser.add_argument('--max-calls-per-day',type=int,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    if args.max_calls_per_day < 0:
        parser.error('Budget must be non-negative')
    request=season_request(args.league_id,args.season)
    if not args.execute:
        print(json.dumps(dict(status='preview',request=request,budget=args.max_calls_per_day,external_calls=0)))
        return 0
    if not Path(args.database).is_file():
        parser.error('Select an existing database')
    result=run_season_backfill(args.database,args.league_id,args.season,budget=args.max_calls_per_day)
    print(json.dumps(result))
    return 0 if result['status'] in {'success','cached'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
