from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
app = (ROOT/'app.py').read_text(encoding='utf-8')
engine = (ROOT/'engines/api_football_live_tracker_engine.py').read_text(encoding='utf-8')
le = (ROOT/'engines/live_experience_engine.py').read_text(encoding='utf-8')
base = (ROOT/'templates/base.html').read_text(encoding='utf-8')
client = (ROOT/'templates/client_app_center.html').read_text(encoding='utf-8')
calendar = (ROOT/'templates/calendar.html').read_text(encoding='utf-8')
live = (ROOT/'templates/live.html').read_text(encoding='utf-8')
css = (ROOT/'static/app.css').read_text(encoding='utf-8')
version = (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
checks = []
def ok(name, cond, detail=''):
    checks.append((name, bool(cond), detail))
ok('version_v811', version == 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL', version)
ok('app_version_v811', "APP_VERSION = 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL'" in app)
ok('lifecycle_helpers', 'match_is_stale_without_result' in app and 'Resultado pendiente' in app)
ok('api_window_sync', 'sync_api_football_match_window' in engine and 'API_FOOTBALL_MATCH_WINDOW_CACHE_SECONDS' in engine)
ok('dashboard_sync', 'ensure_client_match_lifecycle_fresh' in app and 'client_lifecycle_sync' in app)
ok('upcoming_filters_past', 'get_upcoming_matches ya no deja que partidos de madrugada' in app)
ok('results_today', 'WHERE match_date>=? AND match_date<=?' in app and 'is_result_pending' in app)
ok('field_state', 'def _field_state' in engine and 'dangerous_attacks_available' in engine and 'corners_available' in engine)
ok('live_experience_field', 'live_field_headline' in le and 'live_field_chips' in le)
ok('base_dedupe_shark', 'un único SHARK flotante' in base and 'data-v811-shell="true"' in base)
ok('topbar_reference', '.v811-top-actions' in css and '.v811-client-appbar' in css)
ok('swimming_shark', 'v811SharkFloat' in css and '.v810-big-shark-decoration' in css)
ok('client_lifecycle_strip', 'v811-lifecycle-strip' in client)
ok('calendar_results_link', '/calendar?lane=results' in calendar)
ok('live_field_chips_template', 'v811-field-chips' in live)
ok('report_exists', (ROOT/'reports/V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL_REPORT.md').exists())
failed = [x for x in checks if not x[1]]
for name, cond, detail in checks:
    print(('OK' if cond else 'FAIL'), name, detail)
if failed:
    raise SystemExit(1)
print('V811 client lifecycle/live field/reference UI check OK')
