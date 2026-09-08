"""Offline regressions for bounded admin reads and bootstrap presentation."""
from pathlib import Path

import pytest

from engines import codex_daily_automation_engine as daily
from engines import project_operating_system_engine as operating


def test_source_inventory_prunes_before_entering_generated_directories(tmp_path, monkeypatch):
    (tmp_path / 'engines').mkdir()
    (tmp_path / 'engines/active.py').write_text('pass')
    (tmp_path / '.tmp_reference_review').mkdir()
    (tmp_path / '.venv').mkdir()
    scan = operating.os.scandir

    def guarded(path):
        assert Path(path).name not in {'.venv', '.tmp_reference_review'}
        return scan(path)

    monkeypatch.setattr(operating.os, 'scandir', guarded)
    assert [p.relative_to(tmp_path).as_posix() for p in operating._iter_files(tmp_path)] == ['engines/active.py']


def test_source_inventory_retains_real_sources_and_evidence_policy(tmp_path):
    (tmp_path / 'reports').mkdir()
    (tmp_path / 'reports/evidence.md').write_text('QA')
    (tmp_path / 'unknown_module.py').write_text('pass')
    assert {p.name for p in operating._iter_files(tmp_path)} == {'unknown_module.py'}
    assert {p.name for p in operating._iter_files(tmp_path, include_evidence=True)} == {'unknown_module.py', 'evidence.md'}


def test_interactive_audit_is_explicitly_partial(tmp_path, monkeypatch):
    (tmp_path / '.venv').mkdir()
    (tmp_path / '.venv/temp.py').write_text('QA')
    (tmp_path / 'tmp').mkdir()
    (tmp_path / 'tmp/browser.data').write_text('QA')
    (tmp_path / 'app.py').write_text('pass')
    scan = daily.os.scandir

    def guarded(path):
        assert Path(path).name not in {'.venv', 'tmp'}
        return scan(path)

    monkeypatch.setattr(daily.os, 'scandir', guarded)
    result = daily.audit_tree(tmp_path, interactive=True)
    assert result['scope'] == 'INTERACTIVE_SOURCE_ONLY'
    assert result['complete'] is False
    assert result['excluded_directories'] == ['.venv', 'tmp']
    assert result['total_files'] == 1


def test_full_cli_audit_still_detects_generated_files(tmp_path):
    (tmp_path / '.venv').mkdir()
    (tmp_path / '.venv/temp.py').write_text('QA')
    result = daily.audit_tree(tmp_path)
    assert result['complete'] is True
    assert result['safe_trash'][0]['path'] == '.venv/temp.py'


def test_interactive_report_does_not_invent_cleanliness(tmp_path):
    (tmp_path / 'requirements.txt').write_text('pytest')
    result = daily.build_daily_report(tmp_path, interactive=True)
    assert result['cleanliness']['score'] is None
    assert 'No evaluado' in result['cleanliness']['status']


def test_interactive_real_failure_is_not_hidden(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise OSError('QA_UNREADABLE')
    monkeypatch.setattr(daily, 'classify_path', broken)
    (tmp_path / 'app.py').write_text('pass')
    with pytest.raises(OSError, match='QA_UNREADABLE'):
        daily.audit_tree(tmp_path, interactive=True)


def test_bootstrap_uses_auth_spacing_and_keeps_safety_contract():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates/admin_bootstrap.html').read_text(encoding='utf-8')
    assert 'hero compact auth-hero' in template
    assert '{% if blocked %}' in template
    assert 'action="/admin-bootstrap"' in template
    assert 'href="/admin-login"' in template
    base = (root / 'templates/base.html').read_text(encoding='utf-8')
    assert 'data-local-safe-banner="true"' in base


@pytest.mark.parametrize('route', ['/admin/company-audit', '/admin/codex-automation', '/admin/telegram', '/admin/api-sports-audit', '/admin/sentinel-workflow', '/admin/visual-worker', '/admin/sentinel-autopilot'])
@pytest.mark.parametrize('role', [None, 'PRO'])
def test_pending_admin_pages_keep_authorization_before_work(app_module, tmp_path, monkeypatch, route, role):
    monkeypatch.setattr(app_module, 'DB_PATH', str(tmp_path / 'permissions.sqlite'))
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', None)
    monkeypatch.setattr(app_module, '_SEEDING_DB_PATH', None)
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', True)
    app_module.seed_core()
    def forbidden(*args, **kwargs):
        pytest.fail('Unauthorized request reached data, sync or job boundary')
    monkeypatch.setattr(daily, 'build_daily_report', forbidden)
    for name in ('dashboard_data', 'build_company_audit_summary', 'get_api_sports_status', 'run_continuous_sentinel_cycle', 'run_visual_company_worker', '_v888_build_autopilot_scan'):
        monkeypatch.setattr(app_module, name, forbidden)
    with app_module.app.test_client() as client:
        if role:
            with client.session_transaction() as session:
                session.update(user_id='qa-only', user_role=role, membership=role)
        response = client.get(route)
    assert response.status_code in (302, 303)
    assert '/admin-login' in response.location
