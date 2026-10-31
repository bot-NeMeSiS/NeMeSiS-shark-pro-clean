"""Offline contract for issue #327. Never touches production database."""
import sqlite3
from tools.inspect_sqlite_growth_readonly import inspect_database


def test_sqlite_growth_inventory_never_modifies_source(tmp_path):
    path = tmp_path / "sample.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE fixtures(id INTEGER PRIMARY KEY, name TEXT)")
        db.executemany("INSERT INTO fixtures(name) VALUES(?)", [("fixture",)] * 10)
    size_before = path.stat().st_size
    data_before = path.read_bytes()
    result = inspect_database(str(path))
    assert result["ok"] is True
    assert result["readonly"] is True
    assert result["writes"] == 0
    assert result["db_size_bytes"] == size_before
    assert result["allocated_bytes"] >= size_before
    assert path.read_bytes() == data_before
    if result["dbstat_available"]:
        assert any(item["name"] == "fixtures" and item["bytes"] > 0 for item in result["tables"])


def test_missing_database_does_not_create_file(tmp_path):
    path = tmp_path / "missing.db"
    assert inspect_database(str(path))["error_code"] == "DB_NOT_FOUND"
    assert not path.exists()


def test_fast_inventory_reports_capacity_without_scanning_dbstat(tmp_path):
    path = tmp_path / "fast.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE fixtures(id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO fixtures(name) VALUES('qa')")
    data_before = path.read_bytes()
    status = inspect_database(str(path), limit=0)
    assert status["ok"] is True
    assert status["readonly"] is True
    assert status["writes"] == 0
    assert status["dbstat_scanned"] is False
    assert status["tables"] == []
    assert status["disk_total_bytes"] > status["db_size_bytes"] > 0
    assert status["disk_free_bytes"] >= 0
    assert status["backup_required_bytes"] > status["allocated_bytes"]
    assert status["backup_headroom_ok"] == (
        status["disk_free_bytes"] >= status["backup_required_bytes"]
    )
    assert path.read_bytes() == data_before


def test_storage_telemetry_admin_api_requires_session_and_stays_readonly(app_module, monkeypatch, tmp_path):
    path = tmp_path / "admin-storage.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE fixtures(id INTEGER PRIMARY KEY)")
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    with app_module.app.test_request_context("/api/admin/data-vault/storage-telemetry"):
        monkeypatch.setattr(app_module, "is_admin_session", lambda: False)
        blocked, code = app_module.api_admin_data_vault_storage_telemetry()
        assert code == 403
        assert blocked.get_json()["ok"] is False
        monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
        payload = app_module.api_admin_data_vault_storage_telemetry().get_json()
    assert payload["ok"] is True
    assert payload["readonly"] is True
    assert payload["writes"] == 0
    assert payload["dbstat_scanned"] is False
    assert payload["db_size_bytes"] == path.stat().st_size
    assert "db_path" not in payload


def test_admin_vault_backup_forms_are_csrf_protected_and_do_not_claim_restoration():
    from pathlib import Path
    html = (Path(__file__).resolve().parents[1] / "templates" / "admin_data_vault.html").read_text(
        encoding="utf-8"
    )
    assert html.count('name="csrf_token" value="{{ csrf_token() }}"') == 2
    assert 'name="backup_name" required' in html
    assert "manifiesto declarado, recuperación sin certificar" in html
    assert "No prueba su restauración automáticamente." in html
    assert 'data-storage-readonly="true"' in html
