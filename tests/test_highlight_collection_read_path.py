"""Public catalogue reads stay bounded to persisted media and preserve rights.

Fixtures are synthetic, with real Flask hooks/templates and isolated SQLite.
No provider access, startup migrations, production users or external playback.
"""
import json
import socket
import sqlite3
import time
from contextlib import closing

import pytest


PUBLIC_COLLECTIONS = (
    "/highlights",
    "/resumenes",
    "/resumenes-partidos",
    "/api/client/highlights",
    "/api/client/highlights/content-center",
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Public media reads must not call a provider")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)


def configure(app_module, monkeypatch, path, role=None, *, user=None):
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "APP_INITIALIZED", False)
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", "")
    calls = []

    def forbidden(*_args, **_kwargs):
        calls.append("unrelated_startup_or_sports_work")
        raise AssertionError("Media GET must not initialize or build a sports dashboard")

    for name in (
        "initialize_once", "seed_core", "dashboard_data",
        "build_v764_dynamic_competition_mode",
    ):
        monkeypatch.setattr(app_module, name, forbidden)
    client = app_module.app.test_client()
    if user is not None:
        # Use the application's login-session format, including the persisted
        # revocation version. Authorization still reads the real fixture DB.
        with app_module.app.test_request_context("/resumenes"):
            app_module.set_login_session(user)
            signed_in = dict(app_module.session)
        with client.session_transaction() as session:
            session.update(signed_in)
    elif role:
        # Absent/corrupt storage cannot authenticate this old cookie. Supplying
        # a version also prevents the TESTING-only legacy identity fallback.
        with client.session_transaction() as session:
            session.update(user_id="synthetic-unverifiable", user_role=role,
                           membership=role, auth_version=0)
    return client, calls


def account(app_module, path, role):
    if role is None:
        return None
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE users(
            id TEXT PRIMARY KEY, name TEXT, username TEXT, email TEXT,
            password_hash TEXT, auth_version INTEGER NOT NULL DEFAULT 0,
            role TEXT, membership TEXT, created_at TEXT
        )""")
        user_id = "synthetic-highlight-" + role.lower()
        conn.execute("""INSERT INTO users
            (id,name,username,email,password_hash,auth_version,role,membership,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""", (
            user_id, "Synthetic highlight account", user_id,
            user_id + "@example.invalid",
            app_module.generate_password_hash("synthetic-highlight-password"),
            3, role, role, "2026-10-01T00:00:00Z",
        ))
        conn.commit()
        return dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


def settings(path, enabled=True):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE automation_state(key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT)")
        conn.execute("INSERT INTO automation_state VALUES(?,?,?)", (
            "admin_control.settings.highlights_enabled",
            json.dumps({"revision": 1, "value": enabled}),
            "2026-10-01T00:00:00Z",
        ))


def catalogue(path):
    from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema

    settings(path)
    ensure_sportsdb_highlights_schema(path)
    with sqlite3.connect(path) as conn:
        # Review owns this optional column; the fixture represents a stored
        # LINK_ONLY decision without running a real approval operation.
        conn.execute("ALTER TABLE sportsdb_match_highlights ADD COLUMN embed_policy TEXT DEFAULT 'LEGACY'")
        conn.executemany("""INSERT INTO sportsdb_match_highlights
            (id,match_id,title,video_url,rights_status,commercial_use_status,
             embed_policy,source,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?)""", (
            ("approved", "match-synthetic", "Synthetic authorized recap",
             "https://www.youtube.com/watch?v=ALLOWED_QA1", "LICENSED", "ALLOWED",
             "LINK_ONLY", "Synthetic QA", "2026-10-01T20:00:00Z"),
            ("review", "match-synthetic", "Synthetic unreviewed recap",
             "https://www.youtube.com/watch?v=REVIEW_QA01", "UNKNOWN_RIGHTS", "UNKNOWN",
             "REVIEW_REQUIRED", "Synthetic QA", "2026-10-01T21:00:00Z"),
        ))


@pytest.mark.parametrize("route", PUBLIC_COLLECTIONS)
@pytest.mark.parametrize("role", [None, "PRO"])
@pytest.mark.parametrize("storage", ["absent", "corrupt"])
def test_missing_or_corrupt_collection_storage_never_initializes_or_claims_empty(
    app_module, monkeypatch, tmp_path, route, role, storage,
):
    path = tmp_path / "media.sqlite"
    if storage == "corrupt":
        path.write_bytes(b"NOT A SQLITE DATABASE")
    before = path.read_bytes() if path.exists() else None
    client, calls = configure(app_module, monkeypatch, path, role)

    response = client.get(route)

    assert calls == []
    # Existing settings default when storage is absent; the catalogue still
    # reports an unknown read. Corrupt settings take the established 503 path.
    assert response.status_code == (503 if storage == "corrupt" else 200)
    if route.startswith("/api/"):
        payload = response.get_json()
        if storage == "corrupt":
            assert payload["ok"] is False
            assert payload["status"] == "READ_UNAVAILABLE"
            assert payload["disabled"] is None
        else:
            center = payload["content_center"]
            assert center["read_ok"] is False
            assert center["read_state"] == "NO_DATABASE"
            assert center["counts"]["videos"] is None
    else:
        html = response.get_data(as_text=True)
        if storage == "corrupt":
            assert "No se pudo comprobar" in html
        else:
            assert 'data-highlights-state="unavailable"' in html
        assert 'data-highlights-state="empty"' not in html
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize("route", PUBLIC_COLLECTIONS)
def test_paused_collection_does_not_read_media_or_run_startup(
    app_module, monkeypatch, tmp_path, route,
):
    path = tmp_path / "media.sqlite"
    settings(path, enabled=False)
    before = path.read_bytes()
    client, calls = configure(app_module, monkeypatch, path)
    monkeypatch.setattr(app_module, "sportsdb_highlights_summary", lambda *_a, **_k: pytest.fail("Paused catalogue read"))

    response = client.get(route)

    assert calls == []
    assert response.status_code == 200
    if route.startswith("/api/"):
        assert response.get_json()["status"] == "DISABLED_BY_ADMIN"
    else:
        assert "Resúmenes temporalmente ocultos" in response.get_data(as_text=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize("route", PUBLIC_COLLECTIONS)
@pytest.mark.parametrize("role", [None, "PRO", "ADMIN"])
def test_public_collection_uses_one_catalogue_read_and_preserves_rights(
    app_module, monkeypatch, tmp_path, route, role,
):
    path = tmp_path / "media.sqlite"
    catalogue(path)
    user = account(app_module, path, role)
    before = path.read_bytes()
    client, calls = configure(app_module, monkeypatch, path, user=user)
    original = app_module.sportsdb_highlights_summary
    reads = []

    def counted(db_path):
        reads.append(db_path)
        return original(db_path)

    monkeypatch.setattr(app_module, "sportsdb_highlights_summary", counted)

    with client:
        response = client.get(route)
        identity = app_module.current_session_user()
        if user is not None:
            assert identity is not None and identity["id"] == user["id"]
            assert identity["role"] == role
            assert app_module.is_admin_session() is (role == "ADMIN")
            assert app_module.session["auth_version"] == user["auth_version"]
        else:
            assert identity is None

    assert calls == []
    assert reads == [str(path)]
    assert response.status_code == 200
    if route.startswith("/api/"):
        center = response.get_json()["content_center"]
        assert center["read_ok"] is True and center["read_state"] == "VERIFIED"
        assert [item["id"] for item in center["available"]] == ["approved"]
        assert center["counts"]["stored"] == 2
        assert center["counts"]["stored_linked_records"] == 2
        assert center["counts"]["stored_unlinked_records"] == 0
        assert center["playback_verified"] is False
        assert center["available"][0]["can_embed"] is False
    else:
        html = response.get_data(as_text=True)
        assert 'data-highlight-id="approved"' in html
        assert 'data-highlight-id="review"' not in html
        assert "Synthetic unreviewed recap" not in html
        assert 'href="/resumen/approved"' in html
        assert "<iframe" not in html
    assert path.read_bytes() == before


@pytest.mark.parametrize("route", ["/resumenes", "/api/client/highlights"])
def test_readable_settings_and_missing_catalogue_remain_unknown(
    app_module, monkeypatch, tmp_path, route,
):
    path = tmp_path / "media.sqlite"
    settings(path)
    before = path.read_bytes()
    client, calls = configure(app_module, monkeypatch, path)

    response = client.get(route)

    assert calls == []
    assert response.status_code == 200
    if route.startswith("/api/"):
        center = response.get_json()["content_center"]
        assert center["read_ok"] is False
        assert center["read_state"] == "CATALOGUE_NOT_INITIALIZED"
        assert center["counts"]["videos"] is None
        assert center["counts"]["pending"] is None
    else:
        assert 'data-highlights-state="unavailable"' in response.get_data(as_text=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize("route", ["/resumenes", "/api/client/highlights"])
def test_verified_empty_catalogue_is_a_real_empty_selection(
    app_module, monkeypatch, tmp_path, route,
):
    from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema

    path = tmp_path / "media.sqlite"
    settings(path)
    ensure_sportsdb_highlights_schema(path)
    before = path.read_bytes()
    client, calls = configure(app_module, monkeypatch, path)

    response = client.get(route)

    assert calls == []
    assert response.status_code == 200
    if route.startswith("/api/"):
        center = response.get_json()["content_center"]
        assert center["read_ok"] is True
        assert center["counts"]["videos"] == 0
        assert center["counts"]["stored"] == 0
        assert center["playback_verified"] is False
    else:
        assert 'data-highlights-state="empty"' in response.get_data(as_text=True)
    assert path.read_bytes() == before


@pytest.mark.parametrize("route", ["/resumenes", "/api/client/highlights"])
def test_exclusive_database_lock_returns_bounded_unknown_without_startup(
    app_module, monkeypatch, tmp_path, route,
):
    path = tmp_path / "media.sqlite"
    catalogue(path)
    before = path.read_bytes()
    client, calls = configure(app_module, monkeypatch, path)
    lock = sqlite3.connect(path)
    try:
        lock.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        response = client.get(route)
        elapsed = time.monotonic() - started
    finally:
        lock.rollback()
        lock.close()

    assert calls == []
    assert response.status_code == 503
    # The settings reader has a short SQLite busy timeout. A catalogue GET must
    # not fall through to the multi-second startup or provider retry paths.
    assert elapsed < 3.0
    if route.startswith("/api/"):
        assert response.get_json()["status"] == "READ_UNAVAILABLE"
    else:
        assert "No se pudo comprobar" in response.get_data(as_text=True)
    assert path.read_bytes() == before
