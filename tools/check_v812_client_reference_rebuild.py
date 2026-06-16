#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
version = (ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()
app = (ROOT/'app.py').read_text(encoding='utf-8')
base = (ROOT/'templates/base.html').read_text(encoding='utf-8')
client = (ROOT/'templates/client_app_center.html').read_text(encoding='utf-8')
css = (ROOT/'static/app.css').read_text(encoding='utf-8')
checks=[]
def ok(name, cond, detail=''):
    checks.append((name, bool(cond), detail))

ok('version_v812', version == 'V812_CLIENT_REFERENCE_REBUILD_REAL_LIFECYCLE_TOPBAR_SHARK_FINAL', version)
ok('app_version_v812', "APP_VERSION = 'V812_CLIENT_REFERENCE_REBUILD_REAL_LIFECYCLE_TOPBAR_SHARK_FINAL'" in app)
ok('not_upcoming_after_kickoff', 'si la hora de inicio ya pasó' in app and 'LIVE_PENDING' in app and 'not info.get("is_upcoming")' in app)
ok('body_v812_flag', 'data-v812-shell="true"' in base)
ok('client_topbar_reference', 'v812-top-actions' in base and '/calendar?lane=results' in base)
ok('single_shark_dedupe', 'mantener un único SHARK flotante' in base and 'widgets.slice(0,-1)' in base and 'fabs.slice(0,-1)' in base)
ok('client_rebuilt_template', 'v812-hero-shell' in client and 'v812-match-spotlight' in client and 'v812-route-steps' in client)
ok('passed_matches_not_next_copy', 'Lo jugado va aquí' in client and 'no se muestra como próximo' in client)
ok('css_reference_system', 'V812_CLIENT_REFERENCE_REBUILD' in css and 'v812SharkSwim' in css and '.v812-hero-shell' in css)
ok('no_fake_ball_css', '.v803-pitch::after{display:none!important}' in css)
ok('mobile_css', '@media(max-width:920px)' in css and '.bottom-nav-clean' in css)
ok('report_exists', (ROOT/'reports/V812_CLIENT_REFERENCE_REBUILD_REAL_LIFECYCLE_TOPBAR_SHARK_FINAL_REPORT.md').exists())
failed=[c for c in checks if not c[1]]
for name, passed, detail in checks:
    print(('OK' if passed else 'FAIL'), name, detail)
if failed:
    raise SystemExit(1)
print('V812 client reference rebuild check OK')
