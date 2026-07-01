from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ['V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION', 'V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION', 'V807_ADMIN_CLIENT_REFERENCE_NAVIGATION_COMMAND_CENTER_REAL_DATA_FINAL', 'V808_FULL_ECOSYSTEM_REFERENCE_UI_ADMIN_CLIENT_FINAL_PERFECTION', 'V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL', 'V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH', 'V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL']

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
build = read('tools/build_clean_release.py')

ok('version_v805_or_newer', any(v in read('VERSION.txt') for v in VERSIONS) and any(v in app for v in VERSIONS))
ok('quality_summary_function', 'def live_tracker_quality_summary' in engine and 'fixtures_with_dangerous_attacks' in engine)
ok('quality_payload_function', 'def _tracker_quality_payload' in engine and 'ball_position_policy' in engine)
ok('no_fake_ball_policy', 'ball_position_available' in engine and 'False' in engine and 'No se inventa posición exacta del balón' in engine)
ok('app_imports_quality', 'live_tracker_quality_summary' in app)
ok('live_page_quality_context', 'api_football_live_quality' in app and 'live_tracker_quality_summary(DB_PATH)' in app)
ok('quality_endpoint', '/api/live-tracker/quality' in app)
ok('status_endpoint_quality', 'status["quality"] = live_tracker_quality_summary(DB_PATH)' in app)
ok('admin_context_quality', 'api_football_quality' in app)
ok('live_experience_quality_labels', 'live_data_quality_label' in live_exp and 'live_tracker_ready_label' in live_exp)
ok('live_template_quality_board', 'v805-live-quality-board' in live_tpl and 'Calidad de directo' in live_tpl)
ok('live_template_evidence_chips', 'v805-evidence-chips' in live_tpl and 'live_data_evidence' in live_tpl)
ok('match_template_quality_line', 'v805-match-quality-line' in match_tpl and 'tracker_quality' in match_tpl)
ok('match_strip_live_tracker', 'Live tracker' in match_tpl and '#live-tracker' in match_tpl)
ok('css_v805', 'V805 · Live operations/client perfection' in css)
ok('build_includes_v805_reports', 'reports/V805_' in build and 'RELEASE_ZIP_AUDIT_V805' in build)
ok('report_exists', (ROOT/'reports/V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION_REPORT.md').exists())
ok('qa_exists', (ROOT/'reports/V805_LIVE_OPERATIONS_CLIENT_QA_CHECKLIST.md').exists())

# Guardrail: the new code must keep the real-data rule explicit.
for rel in ['templates/live.html', 'templates/match_detail.html', 'engines/api_football_live_tracker_engine.py']:
    data = read(rel).lower()
    bad = [token for token in ['pelota falsa', 'fake ball', 'mock live', 'ataque inventado'] if token in data]
    ok(f'{rel} no_fake_markers', not bad)

failed = [name for name, value in checks if not value]
print({'ok': not failed, 'total': len(checks), 'passed': len(checks)-len(failed), 'failed': failed})
raise SystemExit(1 if failed else 0)
