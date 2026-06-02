from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.blueprint_migration_engine import guess_route_group, build_route_summary


def test_route_group_guessing():
    assert guess_route_group('/admin/data-center') == 'admin'
    assert guess_route_group('/admin-login') == 'admin'
    assert guess_route_group('/telegram/webhook') == 'telegram'
    assert guess_route_group('/picks') == 'shark_picks'
    assert guess_route_group('/live') == 'football'


def test_route_summary_is_safe_without_app_file(tmp_path):
    missing = tmp_path / 'missing_app.py'
    summary = build_route_summary(missing)
    assert summary['ok'] is True
    assert summary['total_routes'] == 0
