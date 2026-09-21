"""Paired, isolated local benchmark. Never measures or touches production."""
from pathlib import Path
import os, sys, socket, tempfile, json, time, random, statistics, importlib.util, copy, re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline-root', type=Path, required=True)
parser.add_argument('--candidate-root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
ROOT = args.candidate_root.resolve()
BASE = args.baseline_root.resolve()
OUT = args.output_dir.resolve(); OUT.mkdir(parents=True, exist_ok=True)
assert (ROOT / 'app.py').is_file() and (BASE / 'engines/v934_realtime_sports_engine.py').is_file()
sys.path.insert(0, str(ROOT)); os.chdir(ROOT)
TEMP = tempfile.TemporaryDirectory(prefix='nemesis-local-benchmark-')
os.environ.update(DB_PATH=str(Path(TEMP.name)/'qa.sqlite'),SECRET_KEY='performance-qa-only',
 ADMIN_EMAIL='qa@example.test',ADMIN_PASSWORD='synthetic-test-password',AUTOMATION_SECRET='local-synthetic-only',
 BACKGROUND_JOBS_ENABLED='false',AUTO_GENERATE_PICKS='false',AUTO_SEND_TELEGRAM_PICKS='false')
attempts = []
def block(*a, **k):
 attempts.append('NETWORK_BLOCKED'); raise AssertionError('benchmark cannot use a network')
socket.socket.connect = block; socket.create_connection = block
import app
from engines import v934_realtime_sports_engine as candidate
from engines.snapshot_copy_engine import clone_snapshot
spec=importlib.util.spec_from_file_location('baseline_realtime', str(BASE / 'engines/v934_realtime_sports_engine.py'))
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
app.app.config.update(TESTING=True);app.init_db()
now=datetime.now(ZoneInfo('Europe/Madrid'))
with app.db() as conn:
 cols={r[1] for r in conn.execute('pragma table_info(matches)')}
 for i in range(200):
  date=now-timedelta(minutes=40) if i<10 else now+timedelta(hours=2,minutes=i)
  row={'id':f'perf-qa-{i}','external_id':f'qa-{i}', 'home_team':f'Local QA {i}','away_team':f'Visitante QA {i}',
   'competition_name':'Spanish La Liga','competition_key':'soccer_spain_la_liga','sport_key':'soccer_spain_la_liga','country':'Spain',
   'match_date':date.date().isoformat(),'kickoff_time':date.strftime('%H:%M'),'match_time':date.strftime('%H:%M'),
   'kickoff_iso':date.isoformat(),'source':'TheSportsDB API','status':'LIVE' if i<10 else 'NS','minute':'40' if i<10 else '',
   'home_score':0 if i<10 else None,'away_score':1 if i<10 else None,'last_synced_at':now.isoformat(),'updated_at':now.isoformat(),'priority':90}
  row={k:v for k,v in row.items() if k in cols}
  conn.execute('INSERT INTO matches ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
 conn.commit()
def use(module):
 app.cached_v934_realtime_snapshot=module.cached_realtime_snapshot
 app.build_v934_realtime_snapshot=module.build_realtime_snapshot
 app.invalidate_v934_realtime_cache=module.invalidate_realtime_cache
 app.v934_realtime_cache_status=module.realtime_cache_status
client=app.app.test_client()
records={}
route_counts={}
rng=random.Random(814)
for path in ['/', '/calendar', '/live', '/picks', '/api/realtime/sports']:
 records[path]={'baseline': [],'candidate': []}; route_counts[path]={}
 for label, module in [('baseline',baseline),('candidate',candidate)]:
  use(module);module.invalidate_realtime_cache()
  for _ in range(2):
   assert client.get(path).status_code==200
 for _ in range(15):
  order=[('baseline',baseline),('candidate',candidate)];rng.shuffle(order)
  for label,module in order:
   use(module)
   started=time.perf_counter(); response=client.get(path);ms=(time.perf_counter()-started)*1000
   assert response.status_code==200
   records[path][label].append(round(ms,3))
   if response.is_json:
    counts=response.get_json().get('counts')
   else:
    counts=sorted(set(re.findall(r'data-sports-(?:matches-today|live-confirmed|picks-ready)="[0-9]+"', response.get_data(as_text=True))))
   route_counts[path][label]=counts
 assert route_counts[path]['baseline']==route_counts[path]['candidate']
use(candidate)
with app.app.test_request_context('/live'):
 summary=app.get_public_home_sports_summary()
assert baseline.build_realtime_snapshot(summary,now)==candidate.build_realtime_snapshot(summary,now)
assert clone_snapshot(summary)==copy.deepcopy(summary)
copy_samples={'deepcopy':[],'clone_snapshot':[]}
for _ in range(35):
 order=[('deepcopy',copy.deepcopy),('clone_snapshot',clone_snapshot)];rng.shuffle(order)
 for label, fn in order:
  t=time.perf_counter();fn(summary);copy_samples[label].append(round((time.perf_counter()-t)*1000,3))

def metrics(samples):
 values=sorted(samples)
 return {'n':len(values),'median_ms':round(statistics.median(values),3),
         'p95_sample_ms':values[min(len(values)-1,__import__('math').ceil(.95*len(values))-1)],
         'min_ms':values[0],'max_ms':values[-1],'raw_ms':samples}
result={'scope':'SIMULATED_QA_LOCAL_FLASK_TEST_CLIENT','fixture_rows':200,'input_live_rows':10,
 'production':False,'baseline_module':str(BASE / 'engines/v934_realtime_sports_engine.py'),'external_network_attempts':len(attempts),'python':sys.version.split()[0],
 'route_counts_equal':True,'snapshot_output_equal_at_fixed_clock':True,
 'routes':{path:{label:metrics(values) for label,values in rows.items()} for path,rows in records.items()},
 'copy':{label:metrics(values) for label,values in copy_samples.items()},
 'limitations':['Local hardware and synthetic database, no mobile network/browser or cron concurrency.',
  '15 paired warm requests per route; empirical p95 is descriptive, not a production percentile.',
  'CI distribution omits optional modules; full GitHub CI must validate the repository.',
  'Only candidate engine functions are switched; cache/SQL/template/application behavior otherwise retained.',
  'Timings have no cProfile overhead. No change to TTLs, server worker configuration or CSS.']}
assert attempts==[]
(OUT/'paired-request-benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
for path,rows in result['routes'].items():
 b=rows['baseline']['median_ms'];c=rows['candidate']['median_ms'];print(path,b,c,round(100*(b-c)/b,1),'%')
print('copy', {k:v['median_ms'] for k,v in result['copy'].items()})
TEMP.cleanup()
