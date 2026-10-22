"""Provider diagnostics preserve unknown storage through their direct consumers."""
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

from engines import api_sports_provider_engine as provider


def _unknown(state="READ_UNAVAILABLE"):
    return {
        "ok": False,
        "read_state": state,
        "read_error": "storage_busy",
        "api_sports_configured": True,
        "api_sports_provider_available": True,
        "api_sports_cache_enabled": True,
        "api_sports_credit_guard_enabled": True,
        "provider_active": "api-sports/api-football",
        "fixtures_cached": None,
        "live_cached": None,
        "events_cached": None,
        "stats_cached": None,
        "tables_detected": None,
        "last_sync": "",
        "last_error": "",
        "usage_guard": provider.usage_guard(),
    }


def _sports_summary(storage_status="ready"):
    return {
        "storage_status": storage_status,
        "valid_matches_today": [{"id": "synthetic-confirmed-match"}],
        "valid_matches_total": 1,
        "raw_matches_count": 1,
        "last_sync": "2026-10-22T10:00:00Z",
    }


@pytest.mark.parametrize("state", ["READ_UNAVAILABLE", "NOT_INITIALIZED", "NOT_REQUESTED"])
def test_sports_context_keeps_unknown_cache_and_independent_match_evidence(app_module, monkeypatch, state):
    monkeypatch.setattr(app_module, "get_api_sports_status", lambda _db: _unknown(state))
    with app_module.app.test_request_context("/directo"):
        result = app_module.get_v932_real_sports_value_context(_sports_summary())
    assert result["cache_status"] == "unknown"
    assert result["cached_fixtures"] is None and result["cached_live"] is None
    assert result["provider_read_state"] == state
    assert result["provider_configured"] and result["provider_available"]
    assert result["real_matches_available"] and result["valid_matches_count"] == 1
    assert result["last_safe_sync"] == "2026-10-22T10:00:00Z"


@pytest.mark.parametrize("fixtures,live,expected", [(0, 0, "empty"), (7, 2, "available")])
@pytest.mark.parametrize("legacy", [False, True])
def test_sports_context_preserves_verified_zero_and_existing_counts(app_module, monkeypatch, fixtures, live, expected, legacy):
    status = {**_unknown(), "ok": True, "read_state": "READY", "fixtures_cached": fixtures, "live_cached": live}
    if legacy:
        status.pop("read_state")
    monkeypatch.setattr(app_module, "get_api_sports_status", lambda _db: status)
    with app_module.app.test_request_context("/directo"):
        result = app_module.get_v932_real_sports_value_context(_sports_summary())
    assert result["cache_status"] == expected
    assert result["cached_fixtures"] == fixtures and result["cached_live"] == live
    assert result["provider_read_state"] == "READY"


@pytest.mark.parametrize("storage_status", ["database_locked", "route_not_required"])
def test_skipped_status_read_is_not_reported_as_empty(app_module, monkeypatch, storage_status):
    def forbidden(_db):
        pytest.fail("This request must not read provider storage")
    monkeypatch.setattr(app_module, "get_api_sports_status", forbidden)
    with app_module.app.test_request_context("/directo"):
        result = app_module.get_v932_real_sports_value_context(_sports_summary(storage_status))
    assert result["provider_read_state"] == "NOT_REQUESTED"
    assert result["cache_status"] == "unknown"
    assert result["cached_fixtures"] is None and result["cached_live"] is None


def test_admin_json_uses_one_snapshot_for_counts_and_explanation(app_module, monkeypatch):
    reads = []
    snapshot = _unknown()
    def read(db):
        reads.append(db)
        return dict(snapshot)
    def second_read(_db=None):
        pytest.fail("Formatting the explanation must not read storage again")
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "get_api_sports_status", read)
    monkeypatch.setattr(provider, "get_api_sports_status", second_read)
    with app_module.app.test_request_context("/api/admin/api-sports/status"):
        response = app_module.api_admin_api_sports_status()
    body = response.get_json()
    assert len(reads) == 1
    assert body["provider"] == body["state"]["status"] == snapshot
    assert body["provider"]["fixtures_cached"] is None
    assert body["dry_run"]["fixtures"]["dry_run"] and body["dry_run"]["live"]["dry_run"]


def test_admin_json_denies_access_before_reading_status(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "is_admin_session", lambda: False)
    def forbidden(_db):
        pytest.fail("Unauthenticated diagnostics must not read provider storage")
    monkeypatch.setattr(app_module, "get_api_sports_status", forbidden)
    with app_module.app.test_request_context("/api/admin/api-sports/status"):
        response = app_module.app.make_response(app_module.api_admin_api_sports_status())
    assert response.status_code == 403


@pytest.mark.parametrize("state", ["READY", "READ_UNAVAILABLE", "NOT_INITIALIZED", "NOT_REQUESTED"])
def test_admin_audit_distinguishes_unchecked_storage_from_verified_zero(state):
    root = Path(__file__).resolve().parents[1]
    env = Environment(
        loader=ChoiceLoader([
            DictLoader({"base.html": "{% block content %}{% endblock %}"}),
            FileSystemLoader(root / "templates"),
        ]),
        autoescape=select_autoescape(),
    )
    status = _unknown(state)
    if state == "READY":
        status.update(ok=True, fixtures_cached=0, live_cached=0, tables_detected=[], read_error="")
    html = env.get_template("admin_api_sports_audit.html").render(
        status=status, dry_fixtures={}, dry_live={}, v850_live_summary={}, v850_live_state={},
    )
    assert ">None<" not in html and ">null<" not in html
    if state == "READY":
        assert "<dt>Lectura de caché local</dt><dd>Comprobada</dd>" in html
        assert "<span>Fixtures cacheados</span>\n      <strong>0</strong>" in html
        assert "<span>Live cacheado</span>\n      <strong>0</strong>" in html
        assert "<dd>Sin tablas API detectadas</dd>" in html
    else:
        assert html.count("<strong>Sin comprobar</strong>") == 2
        assert "<dd>Sin error registrado</dd>" not in html
        assert "<dd>Sin sync visible</dd>" not in html
        assert "<dd>Sin tablas API detectadas</dd>" not in html
        assert "<dd>Sin comprobar; vuelve a intentarlo</dd>" in html


def test_runtime_distinguishes_local_read_failure_from_provider_error(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_api_sports_status", lambda _db: _unknown())
    with app_module.app.test_request_context("/api/runtime-version"):
        result = app_module.v822_runtime_stability_snapshot()
    assert result["api_sports_read_state"] == "READ_UNAVAILABLE"
    assert result["api_sports_read_error"] == "storage_busy"
    assert result["api_sports_configured"] is True
    assert result["last_error"] == ""


@pytest.mark.parametrize("state", ["READY", "READ_UNAVAILABLE", "NOT_INITIALIZED", "NOT_REQUESTED"])
def test_full_runtime_does_not_announce_no_errors_when_storage_was_not_read(app_module, monkeypatch, state):
    snapshot = _unknown(state)
    if state == "READY":
        snapshot.update(ok=True, fixtures_cached=0, live_cached=0, tables_detected=[], read_error="")
    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)
    monkeypatch.setattr(app_module, "get_api_sports_status", lambda _db: snapshot)
    with app_module.app.test_request_context("/api/runtime-version"):
        response = app_module.api_runtime_version()
    body = response.get_json()
    assert body["runtime_stability"]["api_sports_read_state"] == state
    assert body["last_error"] == ""
    assert body["last_error_state"]["active"] is False
    assert body["last_error_state"]["status"] == (
        "Sin errores registrados" if state == "READY" else "Estado local sin comprobar"
    )
