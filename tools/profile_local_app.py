"""Bounded /app profiling on a new LOCAL SAFE database, never a real database."""
from __future__ import annotations

import argparse
from collections import Counter
import cProfile
from datetime import datetime, timedelta
import functools
import hashlib
import json
import os
from pathlib import Path
import pstats
import re
import sqlite3
import sys
import tempfile
import time
import uuid
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, choices=(120, 600), default=600)
    parser.add_argument('--label', choices=('before', 'after'), required=True)
    parser.add_argument('--no-profile', action='store_true', help='HTTP wall time, without cProfile/SQL instrumentation')
    parser.add_argument('--dataset', type=Path, help='Replay a previously recorded local QA match dataset')
    parser.add_argument('--timeline-baseline', action='store_true', help='QA comparison: use individual timeline reads')
    args = parser.parse_args()
    out = ROOT / 'data/local_dev' / ('app-profile-' + args.label + '-' + uuid.uuid4().hex)
    out.mkdir(parents=True)
    os.environ['TMP'] = os.environ['TEMP'] = str(out)
    tempfile.tempdir = str(out)
    from tools.local_desktop.run_sentinel_local import prepare
    module, _, blocked = prepare(db_name=out.name + '.sqlite')
    if args.timeline_baseline:
        module._prefetch_home_timelines = lambda matches: None
    from tools.local_desktop.run_local_desktop import insert_row
    now = datetime.now(ZoneInfo('Europe/Madrid')).replace(microsecond=0)
    leagues = [('4335','LaLiga EA Sports','Spain'),('4328','Premier League','England'),
               ('4331','Bundesliga','Germany'),('4334','Ligue 1','France'),
               ('4332','Serie A','Italy'),('qa-unmapped','Liga QA','Unknown')]
    with sqlite3.connect(module.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        base = dict(conn.execute("SELECT * FROM matches WHERE id='local-match-2'").fetchone())
        for i in range(args.count):
            league_id, name, country = leagues[i % len(leagues)]
            kickoff = now + timedelta(days=(i % 7)-1, minutes=(i*17)%1440)
            status = 'FT' if kickoff < now else 'NS'
            row = {**base, 'id':f'profile-qa-{i}', 'external_id':f'profile-qa-{i}',
                   'home_team':f'Local QA {i}', 'away_team':f'Visitante QA {i}',
                   'competition_id':league_id,'competition_key':league_id,
                   'competition_name':name,'league_name':name,'country':country,
                   'kickoff_iso':kickoff.isoformat(),'match_date':kickoff.date().isoformat(),
                   'kickoff_time':kickoff.strftime('%H:%M'),'match_time':kickoff.strftime('%H:%M'),
                   'status':status,'home_score':2 if status=='FT' else None,
                   'away_score':1 if status=='FT' else None,'score':'2-1' if status=='FT' else '',
                   'home_team_id':f'profile-home-{i}','away_team_id':f'profile-away-{i}',
                   'source':'SIMULATED_QA','updated_at':now.isoformat()}
            insert_row(conn,'matches',row)
        if args.dataset:
            dataset_path = args.dataset.resolve()
            assert dataset_path.is_relative_to(ROOT/'data/local_dev')
            recorded = json.loads(dataset_path.read_text(encoding='utf-8'))
            assert recorded['environment'] == 'SIMULATED_QA'
            assert len(recorded['matches']) == args.count + 3
            for row in recorded['matches']:
                assert str(row['id']).startswith(('local-match-', 'profile-qa-'))
                insert_row(conn,'matches',row)
        dataset = {'environment':'SIMULATED_QA','matches':[dict(row) for row in conn.execute('SELECT * FROM matches ORDER BY id')]}
        assert len(dataset['matches']) == args.count + 3
    encoded = json.dumps(dataset, sort_keys=True, ensure_ascii=False)
    (out/'dataset.json').write_text(encoded,encoding='utf-8')
    module.invalidate_v934_realtime_cache()
    client = module.app.test_client()
    client.get('/local-safe/login/client?token='+os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
    names = ('build_sports_home_sections','sort_matches_by_sports_relevance',
             'sports_relevance_profile','sports_competition_priority','normalized_label',
             'get_picks','_normalized_sports_favorites','_dedupe_sports_matches',
             '_sports_match_favorite','_sports_top_team_hits','professionalize_identity',
             'match_timeline','get_favorites','canonical_match_status','render_template',
             'dumps','loads')
    collections = []
    original_sort = module.sort_matches_by_sports_relevance
    @functools.wraps(original_sort)
    def observed_sort(matches, *pos, **kw):
        collections.append({'count':len(matches or []),'surface':kw.get('surface',pos[0] if pos else 'home')})
        return original_sort(matches,*pos,**kw)
    module.sort_matches_by_sports_relevance = observed_sort
    sql = []
    original_connect = sqlite3.connect
    def traced_connect(*pos, **kw):
        conn = original_connect(*pos,**kw)
        conn.set_trace_callback(lambda query: sql.append(re.sub(r"'(?:[^']|'')*'",'?',query)))
        return conn
    if not args.no_profile:
        sqlite3.connect = traced_connect
    report = {'environment':'SIMULATED_QA','instrumented':not args.no_profile,'timeline_baseline':args.timeline_baseline,'dataset_matches':args.count+3,
              'dataset_sha256':hashlib.sha256(encoded.encode()).hexdigest(),'samples':[]}
    try:
        for index in range(3):
            sql.clear(); collections.clear()
            profiler = cProfile.Profile()
            start = time.perf_counter()
            if not args.no_profile:
                profiler.enable()
            response = client.get('/app')
            profiler.disable()
            duration = time.perf_counter()-start
            stats = pstats.Stats(profiler).stats if not args.no_profile else {}
            if not args.no_profile:
                profiler.dump_stats(str(out / f'request-{index}.pstats'))
            functions = {}
            for (_, _, name), (_, calls, own, cumulative, _) in stats.items():
                if name in names:
                    functions[name] = {'calls':calls,'self_seconds':round(own,6),'cumulative_seconds':round(cumulative,6)}
            counts = Counter(sql)
            report['samples'].append({'cache':'cold' if index==0 else 'warm','seconds':duration,
                'http':response.status_code,'functions':functions,'ranked_collections':list(collections),
                'sql_total':len(sql),'sql_unique':len(counts),
                'repeated_sql':[{'query':q,'count':n} for q,n in counts.most_common(15) if n>1],
                'response_bytes':len(response.data)})
            report['samples'][-1]['hot_functions'] = [
                {'function':name,'file':Path(filename).name,'line':line,'calls':calls,
                 'self_seconds':round(own,6),'cumulative_seconds':round(cumulative,6)}
                for (filename,line,name),(_,calls,own,cumulative,_) in
                sorted(stats.items(),key=lambda item:item[1][3],reverse=True)[:55]]
            assert response.status_code==200
    finally:
        sqlite3.connect = original_connect
        module.sort_matches_by_sports_relevance = original_sort
        report['boundary_events'] = blocked
        (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'matches':report['dataset_matches'],'seconds':[round(s['seconds'],3) for s in report['samples']],
                      'sql':[s['sql_total'] for s in report['samples']],'boundary_events':blocked}))


if __name__ == '__main__':
    main()
