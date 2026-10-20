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
    assert payload["deployment_alignment_status"] in {"aligned_local_files", "version_file_mismatch"}
    assert len(response.data) < 1024


def test_master_cron_uses_compact_runtime_readiness():
    from tools import render_cron_master_tick as runner
    assert runner.READINESS_ENDPOINT == "/api/runtime-version?compact=1"


def test_compact_identity_uses_current_platform_sha_without_database(app_module, monkeypatch):
    sha = "a" * 40
    monkeypatch.setenv("RENDER_GIT_COMMIT", sha)
    monkeypatch.setattr(app_module, "v822_runtime_stability_snapshot", _boom)
    monkeypatch.setattr(app_module, "v902_sentinel_truth_runtime_summary", _boom)
    monkeypatch.setattr(app_module, "automation_get", _boom)
    response = app_module.app.test_client().get("/api/runtime-version?compact=1")
    assert response.status_code == 200
    assert response.get_json()["git_commit_hint"] == sha
    assert isinstance(response.get_json()["version_files_match"], bool)
    assert len(response.data) < 1024


def test_compact_identity_does_not_certify_missing_or_invalid_sha(app_module, monkeypatch):
    for key in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "COMMIT_SHA"):
        monkeypatch.delenv(key, raising=False)
    client = app_module.app.test_client()
    assert client.get("/api/runtime-version?compact=1").get_json()["git_commit_hint"] == "unavailable"
    monkeypatch.setenv("RENDER_GIT_COMMIT", "private-value-not-a-commit")
    payload = client.get("/api/runtime-version?compact=1").get_json()
    assert payload["git_commit_hint"] == "unavailable"
    assert "private-value" not in str(payload)


def test_public_runtime_version_never_returns_internal_diagnostics(app_module):
    client = app_module.app.test_client()
    for query in ("", "?compact=0", "?compact=false", "?compact=no", "?compact=unexpected"):
        response = client.get("/api/runtime-version" + query)
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["version"] == app_module.APP_VERSION
        assert payload["compact"] is True
        assert set(payload) == {
            "ok", "status", "version", "runtime_checked_at_madrid", "compact",
            "git_commit_hint", "version_files_match", "deployment_alignment_status",
        }
        assert "python_file_path" not in payload
        assert "db_path" not in payload
        assert "render_service_hint" not in payload
        assert response.headers["Cache-Control"] == "private, no-store"
    head = client.head("/api/runtime-version?compact=false")
    assert head.status_code == 200
    assert head.headers["Cache-Control"] == "private, no-store"


def test_full_runtime_version_diagnostics_remain_available_to_admin(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = "pytest-runtime-diagnostics-admin"
        session["user_role"] = "ADMIN"
        session["user_name"] = "Runtime diagnostics QA"
    response = client.get("/api/runtime-version")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == app_module.APP_VERSION
    assert payload.get("compact") is not True
    assert payload.get("python_file_path")
    assert payload.get("db_path")
    assert payload.get("static_css_cache_busting") is True
    assert response.headers["Cache-Control"] == "private, no-store"


def test_automated_runtime_verifier_uses_public_identity_without_collecting_admin_fields(monkeypatch):
    from automation_workforce import runtime_verifier

    requested = []
    public_payload = {
        "ok": True,
        "status": "READY",
        "version": runtime_verifier.VERSION,
        "git_commit_hint": "a" * 40,
        "version_files_match": True,
        "deployment_alignment_status": "aligned_local_files",
        "compact": True,
    }
    monkeypatch.setattr(runtime_verifier, "fetch_runtime", lambda url: (requested.append(url) or 200, public_payload))
    monkeypatch.setattr(runtime_verifier, "write_report", lambda *_args, **_kwargs: None)

    result = runtime_verifier.run_runtime_verifier(expected_version=runtime_verifier.VERSION)

    assert result["ok"] is True
    assert result["alignment_status"] == "ALIGNED"
    assert requested == [runtime_verifier.DEFAULT_RUNTIME_URL]
    assert "compact=1" in requested[0]
    assert result["runtime_diagnostics_scope"] == "public_readiness_only"
    assert not {"db_path", "sentinel_active_issues_count", "telegram_configured"} & result.keys()
