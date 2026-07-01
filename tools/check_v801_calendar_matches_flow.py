#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = 'V801_CALENDAR_MATCHES_REFERENCE_FLOW_REAL_DATA_PERFECTION'

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def require(cond, msg):
    if not cond:
        raise SystemExit(f'FAIL: {msg}')

version = (ROOT / 'VERSION.txt').read_text(encoding='utf-8-sig').strip()
app = read('app.py')
base = read('templates/base.html')
calendar = read('templates/calendar.html')
css = read('static/app.css')

ALLOWED_VERSIONS = ['V801_CALENDAR_MATCHES_REFERENCE_FLOW_REAL_DATA_PERFECTION', 'V802_CLIENT_REFERENCE_FLOW_LINKED_EXPERIENCE_PERFECTION', 'V803_API_FOOTBALL_LIVE_TRACKER_REFERENCE_EXPERIENCE', 'V804_API_FOOTBALL_LIVE_DEEP_TRACKER_PRESSURE_FIELD_FINAL', 'V805_API_FOOTBALL_LIVE_OPERATIONS_CLIENT_PERFECTION']
require(version in ALLOWED_VERSIONS, f'VERSION inesperada: {version}')
require(any(f"APP_VERSION = '{v}'" in app for v in ALLOWED_VERSIONS), 'APP_VERSION no coincide')
require('data-v801-shell="true"' in base, 'base sin data-v801-shell')

for token in [
    'def _calendar_important_shortcuts',
    'def _calendar_day_chips',
    '"day_groups": day_groups',
    '"league_shortcuts"',
    '"today": today_count',
    '"week": _calendar_safe_count',
    'IMPORTANT_COMPETITIONS',
    'with_pick',
    'uefa',
    'national',
]:
    require(token in app, f'app.py sin {token}')

for token in [
    'v801-day-rail',
    'v801-calendar-search',
    'v801-league-rail',
    'Ligas importantes',
    'day_groups',
    'calendar.get(\'source_summary\')',
    '/match/{{ m.get(\'id\') }}',
    '/match/{{ m.get(\'id\') }}#shark',
    'No hay partidos para este filtro',
    'La app no inventa calendario',
]:
    require(token in calendar, f'templates/calendar.html sin {token}')

for token in [
    'V801 CALENDAR',
    '.v801-day-rail',
    '.v801-calendar-search',
    '.v801-league-rail',
    '.v801-agenda-row',
    '.v801-row-actions',
]:
    require(token in css, f'CSS sin {token}')

fake_tokens = ['98.72%', '1.237', '812', '65.7%', 'G E G P G', 'Pick generado', 'Hoy traemos 3 selecciones']
for rel in ['templates/calendar.html', 'templates/home.html', 'templates/live.html', 'templates/picks.html']:
    text = read(rel)
    for token in fake_tokens:
        require(token not in text, f'{rel} conserva dato ficticio visible: {token}')

for token in ['DB_PATH', 'AUTOMATION_SECRET', '/api/automation/telegram/tick', 'render_cron_telegram_tick.py']:
    require(token in app or token in ''.join(p.read_text(encoding='utf-8', errors='ignore') for p in [ROOT / 'tools' / 'render_cron_telegram_tick.py']), f'referencia crítica perdida: {token}')

print('V801 calendar matches flow real-data perfection check OK')
