from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8', errors='ignore')

checks = []

def ok(name, cond):
    checks.append((name, bool(cond)))

app = read('app.py')
engine = read('engines/api_football_live_tracker_engine.py')
live_tpl = read('templates/live.html')
match_tpl = read('templates/match_detail.html')
css = read('static/app.css')
env = read('.env.render.clean')

ok('version_v803_or_newer', 'V803_API_FOOTBALL_LIVE_TRACKER_REFERENCE_EXPERIENCE' in app or 'V804_API_FOOTBALL_LIVE_DEEP_TRACKER_PRESSURE_FIELD_FINAL' in app or 'V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION' in app or 'V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION' in app or 'V807_ADMIN_CLIENT_REFERENCE_NAVIGATION_COMMAND_CENTER_REAL_DATA_FINAL' in app)
ok('engine_exists', (ROOT/'engines/api_football_live_tracker_engine.py').exists())
ok('api_football_live_fixtures', 'fixtures' in engine and 'live' in engine and 'all' in engine)
ok('api_football_events', 'fixtures/events' in engine)
ok('api_football_statistics', 'fixtures/statistics' in engine)
ok('cache_seconds', 'API_FOOTBALL_LIVE_CACHE_SECONDS' in engine and 'api_football_live_sync_state' in engine)
ok('deep_limit', 'API_FOOTBALL_LIVE_DEEP_LIMIT' in engine)
ok('no_fake_ball', 'ball_position_available' in engine and 'False' in engine)
ok('live_page_integrated', 'sync_api_football_live_tracker(DB_PATH' in app and 'api_football_live_tracker' in app)
ok('match_detail_integrated', 'live_tracker_for_match(DB_PATH' in app)
ok('api_endpoints', '/api/live-tracker' in app and '/api/live-tracker/status' in app)
ok('template_provider_strip', 'v803-live-provider-strip' in live_tpl)
ok('template_field', 'v803-live-field' in live_tpl and 'Balón exacto no disponible' in live_tpl)
ok('detail_tracker', 'v803-match-live-tracker' in match_tpl and 'no se simula' in match_tpl)
ok('css_v803', 'V803 · API-Football Pro live tracker' in css)
ok('env_flags', 'ENABLE_API_FOOTBALL_LIVE_TRACKER=true' in env and 'API_FOOTBALL_LIVE_DEEP_LIMIT=8' in env)
ok('report', (ROOT/'reports/V803_API_FOOTBALL_LIVE_TRACKER_REFERENCE_EXPERIENCE_REPORT.md').exists())

failed = [name for name, value in checks if not value]
print({
    'ok': not failed,
    'total': len(checks),
    'passed': len(checks)-len(failed),
    'failed': failed,
})
raise SystemExit(1 if failed else 0)
