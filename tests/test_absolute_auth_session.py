"""Real Flask cookie serialization with synthetic identities, no external services."""

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie

from flask import Flask, session
import pytest

from engines.auth_session_engine import AbsoluteAuthSessionInterface


def _application(*, remember=True, expiry=None, session_id="qa-device-session"):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="synthetic-cookie-key-for-local-qa-only",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    app.session_interface = AbsoluteAuthSessionInterface()
    value = expiry if expiry is not None else (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(timespec="seconds")

    @app.post("/login")
    def login():
        session.clear()
        session.permanent = remember
        session.update(user_id="qa-user", auth_session_id=session_id, auth_session_expires_at=value, auth_version=0)
        return "signed in"

    @app.get("/account")
    def account():
        session["membership"] = "FREE"
        return "account"

    @app.post("/logout")
    def logout():
        session.clear()
        return "signed out"

    return app, value


def _cookie(response):
    jar = SimpleCookie()
    jar.load(response.headers["Set-Cookie"])
    return jar["session"]


def test_persistent_cookie_uses_same_absolute_instant_and_preserves_flags():
    app, value = _application()
    response = app.test_client().post("/login", base_url="https://localhost")
    cookie = _cookie(response)
    assert parsedate_to_datetime(cookie["expires"]) == datetime.fromisoformat(value)
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"


def test_mutating_membership_does_not_extend_cookie_or_signed_session_identity():
    app, value = _application()
    client = app.test_client()
    first = client.post("/login", base_url="https://localhost")
    for _ in range(5):
        later = client.get("/account", base_url="https://localhost")
        assert _cookie(later)["expires"] == _cookie(first)["expires"]
        with client.session_transaction(base_url="https://localhost") as state:
            assert state["auth_session_id"] == "qa-device-session"
            assert state["auth_session_expires_at"] == value


def test_browser_session_option_does_not_set_expiry():
    app, _ = _application(remember=False)
    response = app.test_client().post("/login", base_url="https://localhost")
    assert _cookie(response)["expires"] == ""


@pytest.mark.parametrize("value", ["invalid", "", "2030-01-01T00:00:00", "999999-01-01T00:00:00+00:00"])
def test_malformed_authenticated_expiry_does_not_get_a_new_sliding_lifetime(value):
    app, _ = _application(expiry=value)
    response = app.test_client().post("/login", base_url="https://localhost")
    assert parsedate_to_datetime(_cookie(response)["expires"]).year == 1970


def test_missing_authenticated_session_identity_expires_cookie():
    app, _ = _application(session_id="")
    response = app.test_client().post("/login", base_url="https://localhost")
    assert parsedate_to_datetime(_cookie(response)["expires"]).year == 1970


def test_cookie_cannot_outlive_configured_lifetime_even_with_far_future_auth_field():
    app, _ = _application(expiry="2099-01-01T00:00:00+00:00")
    before = datetime.now(timezone.utc)
    response = app.test_client().post("/login", base_url="https://localhost")
    assert parsedate_to_datetime(_cookie(response)["expires"]) <= before + timedelta(hours=12, seconds=1)


def test_logout_deletes_cookie_instead_of_renewing_it():
    app, _ = _application()
    client = app.test_client()
    client.post("/login", base_url="https://localhost")
    response = client.post("/logout", base_url="https://localhost")
    assert _cookie(response).value == ""
    assert _cookie(response)["max-age"] == "0"
