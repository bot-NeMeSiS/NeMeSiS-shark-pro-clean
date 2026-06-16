#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8-sig')

base = read('templates/base.html')
dash = read('templates/admin_dashboard.html')
app = read('app.py')
css = read('static/app.css')

required_base = [
    'data-v807-shell="true"',
    'v807-admin-launchpad',
    'v807_admin_groups',
    '/admin/matches-sync',
    '/admin/live-depth',
    '/admin/telegram/command-center',
    '/sports-hub',
]
required_dash = [
    'V807 · Admin Reference System',
    'v807-admin-route-catalog',
    'items|default([])|groupby',
    'no simula valores',
]
required_app = [
    'def v566_admin_items():',
    '/admin/control-center',
    '/admin/live-depth',
    '/admin/client-screen-audit',
    '/admin/data-vault',
    '/admin/real-launch',
]
required_css = [
    'V807_ADMIN_CLIENT_REFERENCE_NAVIGATION_COMMAND_CENTER_REAL_DATA_FINAL',
    '.v807-admin-launchpad',
    '.v807-admin-route-catalog',
    '.ns-authenticated:not(.ns-admin)[data-v807-shell="true"] .v798-client-rail',
]

for needle in required_base:
    assert needle in base, f'base missing {needle}'
for needle in required_dash:
    assert needle in dash, f'dashboard missing {needle}'
for needle in required_app:
    assert needle in app, f'app missing {needle}'
for needle in required_css:
    assert needle in css, f'css missing {needle}'

for fake in ['+12.4% vs ayer', '+8 vs ayer', 'En 12 ligas', '00:07:42', 'Última verificación: 16:15', 'Todos los sistemas OK']:
    assert fake not in dash, f'fake dashboard text remains: {fake}'

print('V807 admin/client reference navigation check OK')
