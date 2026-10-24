"""Real local HTTP continuity, without provider/production effects."""
import os
from http.cookies import SimpleCookie


def test_historico_is_a_real_track_record_consumer_not_a_diagnostic_write(app_module, monkeypatch):
    client = app_module.app.test_client()
    client.get('/local-safe/login/client?token=' + os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
    def forbidden(*args, **kwargs):
        raise AssertionError('Opening pick history must not write a not-found report')
    monkeypatch.setattr(app_module, 'v896_record_not_found', forbidden)
    response = client.get('/historico')
    assert response.status_code == 200
    assert b'data-v933-template="track_record"' in response.data


def test_local_quick_login_without_remember_option_keeps_browser_cookie(app_module):
    assert app_module.local_safe_mode_enabled()
    token = os.environ["NEMESIS_LOCAL_ACCESS_TOKEN"]
    for profile, target in [("client", "/app"), ("admin", "/admin/control-center"), ("founder", "/admin/founder-os")]:
        client = app_module.app.test_client()
        response = client.get("/local-safe/login/" + profile, query_string={"token": token})
        assert response.status_code == 302
        assert response.headers["Location"] == target
        jar = SimpleCookie()
        jar.load(response.headers["Set-Cookie"])
        assert not jar["session"]["expires"]
        assert not jar["session"]["max-age"]
        with client.session_transaction() as state:
            assert state.permanent is False
            assert state["nemesis_local_profile"] == profile
            assert state["auth_session_id"]
            assert state["auth_session_expires_at"]
