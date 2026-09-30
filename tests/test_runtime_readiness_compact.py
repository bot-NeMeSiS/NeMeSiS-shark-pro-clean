"""Compact runtime readiness must stay cheap while full certification remains available."""


def _boom(*_args, **_kwargs):
    raise AssertionError("heavy runtime certification work must not run in compact readiness mode")


def test_compact_runtime_version_skips_heavy_runtime_snapshots(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "v822_runtime_stability_snapshot", _boom)
    monkeypatch.setattr(app_module, "v902_sentinel_truth_runtime_summary", _boom)
    client = app_module.app.test_client()
    response = client.get("/api/runtime-version?compact=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["status"] == "READY"
    assert payload["version"] == app_module.APP_VERSION
    assert payload["compact"] is True
    assert len(response.data) < 1024


def test_master_cron_uses_compact_runtime_readiness():
    from tools import render_cron_master_tick as runner
    assert runner.READINESS_ENDPOINT == "/api/runtime-version?compact=1"


def test_full_runtime_version_contract_is_still_default(app_module):
    client = app_module.app.test_client()
    response = client.get("/api/runtime-version")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == app_module.APP_VERSION
    assert payload.get("compact") is not True
