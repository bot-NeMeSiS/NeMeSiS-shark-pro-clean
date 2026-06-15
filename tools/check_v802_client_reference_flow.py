#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V802_CLIENT_REFERENCE_FLOW_LINKED_EXPERIENCE_PERFECTION'
checks = []

def require(path, text, label):
    data = (ROOT / path).read_text(encoding='utf-8')
    ok = text in data
    checks.append((label, ok))
    return ok

require('VERSION.txt', VERSION, 'version file')
require('app.py', f"APP_VERSION = '{VERSION}'", 'app version')
require('templates/base.html', 'data-v802-shell="true"', 'base shell marker')
require('templates/partials/client_flow_bar.html', 'v802-client-flow', 'client flow partial')
require('templates/calendar.html', 'v802-calendar-command', 'calendar command summary')
require('templates/calendar.html', 'v802-league-groups', 'calendar league groups')
require('templates/calendar.html', 'v802-focus-strip', 'calendar focus strip')
require('templates/live.html', 'v802-live-command', 'live linked command')
require('templates/picks.html', 'v802-pick-command', 'picks reading command')
require('templates/match_detail.html', 'v802-match-command', 'match linked command')
require('static/app.css', 'V802_CLIENT_REFERENCE_FLOW_LINKED_EXPERIENCE_PERFECTION', 'css marker')
require('app.py', '_calendar_league_collections', 'league group helper')
require('app.py', '_calendar_selected_summary', 'selected summary helper')
require('app.py', '"league_groups": _calendar_league_collections(league_shortcuts)', 'calendar league_groups data')
require('app.py', '"highlight_matches": sorted_matches[:6]', 'calendar highlight matches data')

for path in ['templates/calendar.html','templates/live.html','templates/picks.html','templates/match_detail.html','templates/home.html']:
    require(path, '{% include "partials/client_flow_bar.html" %}', f'{path} includes flow')

# Guardrail: new V802 templates must not introduce fake values like example odds or fake ROI.
for path in ['templates/calendar.html','templates/live.html','templates/picks.html','templates/match_detail.html','templates/partials/client_flow_bar.html']:
    data = (ROOT / path).read_text(encoding='utf-8').lower()
    bad = [token for token in ['mock', 'demo', 'roi 95', '1.85 fijo', 'fake'] if token in data]
    checks.append((f'{path} no fake markers', not bad))

failed = [label for label, ok in checks if not ok]
if failed:
    print('V802 check FAIL')
    for label in failed:
        print('-', label)
    sys.exit(1)
print('V802 check OK')
print(f'{len(checks)} checks passed')
