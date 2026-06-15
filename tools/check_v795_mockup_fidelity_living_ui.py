#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = ROOT.joinpath('VERSION.txt').read_text(encoding='utf-8-sig').strip()
assert VERSION.startswith(('V795_','V796_','V797_')), VERSION
app = ROOT.joinpath('app.py').read_text(encoding='utf-8')
assert ('V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH' in app) or ('V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH' in app) or ('V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH' in app)
base = ROOT.joinpath('templates/base.html').read_text(encoding='utf-8')
assert 'data-v795-shell="true"' in base
assert 'function v795LivingUi' in base
admin = ROOT.joinpath('templates/partials/admin_visual_system.html').read_text(encoding='utf-8')
for marker in ['v795-admin-main','v795-live-chip','v795-clock-card','v795-command-ribbon']:
    assert marker in admin, marker
css = ROOT.joinpath('static/app.css').read_text(encoding='utf-8')
for marker in ['V795 MOCKUP FIDELITY','body.ns-admin[data-v795-shell="true"] .top.ns-topbar','v795-command-ribbon','v795LivePulse']:
    assert marker in css, marker
print('check_v795_mockup_fidelity_living_ui OK')
