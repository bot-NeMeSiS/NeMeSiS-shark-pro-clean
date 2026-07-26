from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


def _login_client_session(client, membership="ELITE"):
    with client.session_transaction() as session:
        session["user_id"] = f"pytest-{membership.lower()}"
        session["user_name"] = f"Cliente {membership}"
        session["username"] = f"cliente_{membership.lower()}"
        session["user_email"] = f"{membership.lower()}@example.com"
        session["user_role"] = "CLIENT"
        session["user_membership"] = membership
        session["membership"] = membership


def test_runtime_version_endpoint(client):
    response = client.get("/api/runtime-version")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["version"] == EXPECTED_VERSION


def test_public_and_client_routes_do_not_500(client):
    public_routes = [
        "/",
        "/version",
        "/login",
        "/cliente-login",
        "/admin-login",
        "/registro",
        "/sports-hub",
        "/live",
        "/calendar",
        "/picks",
        "/combis",
        "/shark",
    ]
    for path in public_routes:
        response = client.get(path, follow_redirects=False)
        assert response.status_code < 500, f"{path} devolvió {response.status_code}"

    _login_client_session(client, "ELITE")
    client_routes = ["/dashboard", "/perfil", "/telegram", "/favorites", "/picks", "/combis", "/shark"]
    for path in client_routes:
        response = client.get(path, follow_redirects=False)
        assert response.status_code < 500, f"{path} devolvió {response.status_code}"


def test_cron_endpoints_require_secret_and_accept_valid_secret(client, monkeypatch):
    test_secret = "pytest-automation-secret"
    monkeypatch.setenv("AUTOMATION_SECRET", test_secret)
    protected = [
        "/api/automation/telegram/tick",
        "/api/automation/daily/run",
    ]
    for path in protected:
        response = client.get(path)
        assert response.status_code == 403

        response = client.get(path, headers={"X-Automation-Secret": test_secret})
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["cron"] is True
        assert "diagnostics" not in payload
        assert "state_save_results" not in payload
        assert "result" not in payload


def test_internal_api_endpoints_are_protected_without_secret(client, app_module):
    registered = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    expected_internal = [
        "/api/diagnostics",
        "/api/cache/status",
        "/api/telegram/auto-run",
        "/api/scheduler/status",
        "/api/matches/diagnostics",
        "/api/v601/api-exploitation-check",
        "/api/v602/player-intelligence-check",
    ]
    checked = [path for path in expected_internal if path in registered]
    assert checked, "No se encontró ningún endpoint técnico esperado para validar protección."

    for path in checked:
        response = client.get(path)
        assert response.status_code == 403, f"{path} debería estar protegido sin secret"


def test_client_home_does_not_show_internal_version(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert not re.search(rf">\s*{re.escape(EXPECTED_VERSION)}\s*<", body)
    assert "Estado app" not in body
