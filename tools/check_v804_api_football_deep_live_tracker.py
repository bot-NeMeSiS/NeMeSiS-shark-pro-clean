from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8', errors='ignore')

checks = []

def ok(name, cond):
    checks.append((name, bool(cond)))

app = read('app.py')
engine = read('engines/api_football_live_tracker_engine.py')
live_exp = read('engines/live_experience_engine.py')
live_tpl = read('templates/live.html')
match_tpl = read('templates/match_detail.html')
css = read('static/app.css')
env = read('.env.render.clean')

ok('version_v804_or_newer', ('V804_API_FOOTBALL_LIVE_DEEP_TRACKER_PRESSURE_FIELD_FINAL' in app or 'V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION' in app or 'V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION' in app or 'V807_ADMIN_CLIENT_REFERENCE_NAVIGATION_COMMAND_CENTER_REAL_DATA_FINAL' in app or 'V808_FULL_ECOSYSTEM_REFERENCE_UI_ADMIN_CLIENT_FINAL_PERFECTION' in app or 'V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL', 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH' in app or 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL' in app) and ('V804_API_FOOTBALL_LIVE_DEEP_TRACKER_PRESSURE_FIELD_FINAL' in read('VERSION.txt') or 'V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION' in read('VERSION.txt') or 'V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION' in read('VERSION.txt') or 'V807_ADMIN_CLIENT_REFERENCE_NAVIGATION_COMMAND_CENTER_REAL_DATA_FINAL' in read('VERSION.txt') or 'V808_FULL_ECOSYSTEM_REFERENCE_UI_ADMIN_CLIENT_FINAL_PERFECTION' in read('VERSION.txt') or 'V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL', 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH' in read('VERSION.txt') or 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL' in read('VERSION.txt')))
ok('detail_sync_function', 'def sync_api_football_fixture_detail' in engine and 'API_FOOTBALL_LIVE_DETAIL_CACHE_SECONDS' in engine)
ok('detail_sync_imported', 'sync_api_football_fixture_detail' in app)
ok('match_detail_uses_deep_sync', 'detail_force_refresh' in app and 'sync_api_football_fixture_detail(DB_PATH, match_id' in app)
ok('match_endpoint', '/api/live-tracker/match/<match_id>' in app)
ok('expanded_stat_keys', 'expected_goals' in engine and 'dangerous_attacks' in engine and 'passes_pct' in engine)
ok('stat_cards_payload', 'stat_cards' in engine and '_stat_cards' in engine)
ok('game_flow_payload', 'game_flow' in engine and '_game_flow' in engine)
ok('no_fake_ball_still', 'ball_position_available' in engine and 'False' in engine and 'no se inventa' in engine)
ok('live_experience_enriched', 'live_stat_cards' in live_exp and 'live_game_flow_phase' in live_exp and 'live_dangerous_attacks_available' in live_exp)
ok('live_template_stats', 'v804-stat-ribbon' in live_tpl and 'Ataques peligrosos no disponibles' in live_tpl)
ok('match_template_stats', 'v804-stat-comparison' in match_tpl and 'Actualizar tracker' in match_tpl)
ok('css_v804', 'V804 · API-Football live deep tracker' in css)
ok('env_flags', 'API_FOOTBALL_LIVE_DETAIL_CACHE_SECONDS=75' in env and 'API_FOOTBALL_LIVE_DETAIL_AUTO_SYNC=true' in env)
ok('report', (ROOT/'reports/V804_API_FOOTBALL_LIVE_DEEP_TRACKER_PRESSURE_FIELD_FINAL_REPORT.md').exists())

failed = [name for name, value in checks if not value]
print({
    'ok': not failed,
    'total': len(checks),
    'passed': len(checks)-len(failed),
    'failed': failed,
})
raise SystemExit(1 if failed else 0)
