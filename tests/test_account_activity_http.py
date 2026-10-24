"""Real account/history HTTP on disposable SQLite under the guarded QA launcher.

This module does not import or initialize app at collection time. The existing
app_module fixture must run in the independent offline QA copy. Authentication,
activity SQL, local resolver, parent templates and the shared macro are real.
Unrelated account-service cards are replaced with local, explicit fixture data.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import uuid

import pytest

ROUTES = ("/mi-cuenta", "/perfil", "/actividad")
ORIGIN = "https://localhost"


class _ActivityHTML(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.component_depth = None
        self.component_state = None
        self.component_text_parts = []
        self.activity_ids = []
        self.component_tags = []
        self.component_links = []
        self.component_times = []
        self.links = []
        self._current_link = None
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "div":
            self.depth += 1
        if "data-client-activity-state" in attrs:
            self.component_depth = self.depth
            self.component_state = attrs["data-client-activity-state"]
        active = self.component_depth is not None
        if active:
            self.component_tags.append((tag, attrs))
            if "data-activity-id" in attrs:
                self.activity_ids.append(attrs["data-activity-id"])
            if tag == "time":
                self.component_times.append(attrs)
        if tag == "a":
            self._current_link = dict(attrs, text="")
            self.links.append(self._current_link)
            if active:
                self.component_links.append(self._current_link)

    def handle_endtag(self, tag):
        if tag == "a":
            self._current_link = None
        if tag == "div":
            if self.component_depth == self.depth:
                self.component_depth = None
            self.depth -= 1

    def handle_data(self, text):
        if self.component_depth is not None:
            self.component_text_parts.append(text)
        if self._current_link is not None:
            self._current_link["text"] += text

    @property
    def component_text(self):
        return " ".join(" ".join(self.component_text_parts).split())


def _source_hashes(root):
    names = ("app.py", "engines/client_activity_engine.py", "engines/auth_session_engine.py",
        "engines/security_engine.py", "templates/account_center.html", "templates/profile.html",
        "templates/activity.html", "templates/components/account_activity.html")
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


@pytest.fixture
def account_activity_http(app_module, tmp_path, monkeypatch):
    a = app_module
    source_root = Path(a.BASE_DIR).resolve()
    # Never run this focused harness against either real checkout or the sparse
    # candidate itself. The QA owner supplies the complete disposable copy.
    protected = (
        Path(r"C:\Users\aloha\.codex\worktrees\v987-postmatch-response\NeMeSiS shark pro"),
        Path(r"C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro"),
        Path(r"C:\Users\aloha\Documents\Codex\2026-10-04\referenced-chatgpt-conversation-this-is-an-8\work\Session-Cuenta-candidate-20261024"),
    )
    if source_root in {path.resolve() for path in protected}:
        pytest.fail("account activity HTTP must execute only in the independent guarded QA copy")
    if a.local_safe_mode_enabled():
        path = Path(a.LOCAL_SAFE_DATA_DIR) / ("account-activity-http-" + uuid.uuid4().hex + ".sqlite3")
    else:
        path = tmp_path / "account-activity-http.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    original_sources = _source_hashes(source_root)
    monkeypatch.setattr(a, "DB_PATH", str(path))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", str(path))
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", True)
    monkeypatch.setattr(a, "APP_INIT_ERROR", "")
    monkeypatch.setattr(a, "bootstrap_admin_from_env", lambda _conn: None)
    # Local DDL only, no seed catalogue, startup sync or provider initialization.
    a.init_db()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("account/history GET attempted startup or provider work")

    monkeypatch.setattr(a, "seed_core", forbidden)
    monkeypatch.setattr(a, "_seed_core_unlocked", forbidden)
    monkeypatch.setattr(a, "_telegram_sync_env_on_startup", forbidden, raising=False)
    monkeypatch.setattr(a, "dashboard_data", forbidden)
    monkeypatch.setattr(a, "v932_safe_dashboard_data", forbidden)
    monkeypatch.setattr(a, "get_favorites", lambda **_kw: [])
    monkeypatch.setattr(a, "build_client_alerts", lambda **_kw: [])
    monkeypatch.setattr(a, "v566_membership_ui", lambda _user: {"headline": "Plan local de prueba"})
    monkeypatch.setattr(a, "client_payments_context", lambda *_args, **_kw: {})
    monkeypatch.setattr(a, "telegram_user_state", lambda _user: {"linked": False})

    with sqlite3.connect(path) as conn:
        for identifier, name in (("activity-http-alice", "HTTP Alice"), ("activity-http-bob", "HTTP Bob")):
            conn.execute("""INSERT INTO users
                (id,name,username,email,password_hash,auth_version,role,membership,membership_source,created_at)
                VALUES(?,?,?,?,?,0,'FREE','FREE','registro',?)""",
                (identifier, name, identifier, identifier + "@example.invalid", "synthetic-unused-password", a.now_iso()))
        conn.execute("INSERT INTO teams(key,name) VALUES('activity-http-team','HTTP Equipo local')")
        conn.execute("INSERT INTO competitions(key,name) VALUES('activity-http-league','HTTP Liga local')")
        conn.execute("""INSERT INTO matches(id,match_date,home_team,away_team)
            VALUES('activity-http-match',?,'HTTP Norte','HTTP Sur')""", (a.today_iso(),))

    def insert_activity(identifier, *, user="activity-http-alice", target="team", target_id="activity-http-team",
            kind="view", date="2026-10-24T00:00:00Z", payload=None):
        with sqlite3.connect(path) as conn:
            conn.execute("INSERT INTO user_activity(id,user_id,activity_type,target_type,target_id,payload_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (identifier, user, kind, target, target_id, json.dumps(payload or {}), date))

    def seed(count, *, user="activity-http-alice", prefix="alice"):
        for number in range(count):
            insert_activity(f"{prefix}-{number:03}", user=user, date=f"2026-10-24T00:00:{number:02}Z")

    def signed_client(user_id="activity-http-alice"):
        # Real cookie/session issuance over a persisted synthetic account. Never
        # replace current_session_user or rely on TESTING's missing-user fallback.
        from flask import session
        user = a.get_user_by_id(user_id)
        assert user and "auth_version" in user
        with a.app.test_request_context("/", base_url=ORIGIN):
            a.set_login_session(user)
            login_state = dict(session)
        client = a.app.test_client()
        with client.session_transaction(base_url=ORIGIN) as state:
            state.clear()
            state.update(login_state)
            state["nemesis_local_access"] = True
            state["csrf_token"] = "synthetic-activity-http-csrf"
        return client

    def anonymous_client():
        client = a.app.test_client()
        with client.session_transaction(base_url=ORIGIN) as state:
            state["nemesis_local_access"] = True
        return client

    def dump_database():
        with sqlite3.connect(path) as conn:
            return "\n".join(conn.iterdump())

    @contextmanager
    def observe_writes():
        writes = []
        original_connect = sqlite3.connect
        operations = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_TABLE,
            sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_ALTER_TABLE}
        def authorize(operation, table, column, *_rest):
            if operation in operations:
                writes.append((operation, table, column))
            return sqlite3.SQLITE_OK
        def connect(*args, **kwargs):
            conn = original_connect(*args, **kwargs)
            conn.set_authorizer(authorize)
            return conn
        with monkeypatch.context() as context:
            context.setattr(sqlite3, "connect", connect)
            yield writes

    yield SimpleNamespace(app=a, path=path, insert=insert_activity, seed=seed,
        signed_client=signed_client, anonymous_client=anonymous_client,
        dump=dump_database, observe_writes=observe_writes)
    assert _source_hashes(source_root) == original_sources


def _get(client, route):
    response = client.get(route, base_url=ORIGIN)
    assert response.status_code == 200, (route, response.status_code, response.get_data(as_text=True)[:500])
    return response, _ActivityHTML(response.get_data(as_text=True))


def test_account_activity_routes_and_anonymous_redirects_are_real(account_activity_http):
    fixture = account_activity_http
    targets = {rule.rule: rule.endpoint for rule in fixture.app.app.url_map.iter_rules()}
    assert targets["/mi-cuenta"] == "account_center_page"
    assert targets["/perfil"] == "profile_page"
    assert targets["/actividad"] == "activity_page"
    for route in ROUTES:
        response = fixture.anonymous_client().get(route, base_url=ORIGIN)
        assert response.status_code == 302
        assert urlparse(response.location).path == "/cliente-login"
        assert "data-activity-id" not in response.get_data(as_text=True)


@pytest.mark.parametrize(("route", "shown"), (("/mi-cuenta", 7), ("/perfil", 7), ("/actividad", 20)))
def test_account_activity_http_exact_total_preview_and_growth_filter(account_activity_http, route, shown):
    fixture = account_activity_http
    fixture.seed(25)
    fixture.seed(8, user="activity-http-bob", prefix="bob-private")
    for number in range(5):
        fixture.insert(f"internal-{number}", kind="growth_returning", date="2026-11-01T00:00:00Z")
        fixture.insert(f"internal-target-{number}", target="growth_funnel", date="2026-11-01T00:00:00Z")
    response, parsed = _get(fixture.signed_client(), route + "?user_id=activity-http-bob&membership=ADMIN")
    assert parsed.component_state == "available"
    assert f"Mostrando {shown} de 25 acciones guardadas." in parsed.component_text
    assert len(parsed.activity_ids) == shown
    assert all(identifier.startswith("alice-") for identifier in parsed.activity_ids)
    assert "bob-private" not in parsed.component_text
    assert "internal" not in parsed.component_text
    assert "private" in response.headers.get("Cache-Control", "")
    assert "no-store" in response.headers.get("Cache-Control", "")
    assert "Cookie" in response.headers.get("Vary", "")


def test_activity_history_http_keyset_page_20_then_5_with_same_real_total(account_activity_http):
    fixture = account_activity_http
    fixture.seed(25)
    client = fixture.signed_client()
    _response, first = _get(client, "/actividad")
    candidates = [link for link in first.links if urlparse(link.get("href", "")).path == "/actividad" and "cursor" in parse_qs(urlparse(link.get("href", "")).query)]
    assert len(candidates) == 1
    assert "Mostrando 20 de 25" in first.component_text
    _response, second = _get(client, candidates[0]["href"])
    assert "Mostrando 5 de 25" in second.component_text
    assert len(first.activity_ids) == 20 and len(second.activity_ids) == 5
    assert not set(first.activity_ids) & set(second.activity_ids)
    assert len(set(first.activity_ids + second.activity_ids)) == 25
    assert not any("cursor" in parse_qs(urlparse(link.get("href", "")).query) for link in second.links)
    assert any(link.get("href") == "/actividad" and "más recientes" in link["text"] for link in second.links)


@pytest.mark.parametrize("route", ROUTES)
def test_account_activity_http_empty_and_query_error_are_distinct(account_activity_http, route):
    fixture = account_activity_http
    client = fixture.signed_client()
    _response, empty = _get(client, route)
    assert empty.component_state == "empty"
    assert "No hay acciones guardadas para mostrar." in empty.component_text
    with sqlite3.connect(fixture.path) as conn:
        conn.execute("DROP TABLE user_activity")
    response, unavailable = _get(client, route)
    assert unavailable.component_state == "unavailable"
    assert "No se puede confirmar el total" in unavailable.component_text
    assert "Mostrando" not in unavailable.component_text
    assert "No hay acciones guardadas" not in unavailable.component_text
    assert any(link.get("href") in ROUTES and link["text"] == "Volver a intentar" for link in unavailable.component_links)
    if route == "/mi-cuenta":
        assert "No disponible" in response.get_data(as_text=True)


@pytest.mark.parametrize("route", ROUTES)
def test_account_activity_http_local_identity_links_and_escaping(account_activity_http, route):
    fixture = account_activity_http
    dangerous = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
    with sqlite3.connect(fixture.path) as conn:
        conn.execute("UPDATE teams SET name=? WHERE key='activity-http-team'", (dangerous,))
    fixture.insert("alice-team", payload={"href": "javascript:alert(9)", "name": "Untrusted payload name"})
    fixture.insert("alice-match", target="match", target_id="activity-http-match")
    fixture.insert("alice-league", target="competition", target_id="activity-http-league")
    fixture.insert("alice-deleted", target="team", target_id="deleted-team", payload={"name": "Must not invent"})
    response, parsed = _get(fixture.signed_client(), route)
    assert "HTTP Norte — HTTP Sur" in parsed.component_text
    assert "HTTP Liga local" in parsed.component_text
    assert "Equipo no disponible." in parsed.component_text
    assert {link["href"] for link in parsed.component_links} == {
        "/team/activity-http-team", "/match/activity-http-match", "/competition/activity-http-league"}
    assert not any(tag in {"img", "script"} or "onerror" in attrs for tag, attrs in parsed.component_tags)
    assert "Untrusted payload name" not in parsed.component_text
    assert "Must not invent" not in parsed.component_text
    assert "&lt;img" in response.get_data(as_text=True)
    assert not any("javascript:" in link["href"] for link in parsed.links)


def test_activity_history_http_user_cookie_and_cursor_cannot_select_other_user(account_activity_http):
    fixture = account_activity_http
    fixture.seed(25)
    fixture.seed(3, user="activity-http-bob", prefix="bob-private")
    _response, alice = _get(fixture.signed_client(), "/actividad")
    cursor_link = next(link["href"] for link in alice.links if "cursor" in parse_qs(urlparse(link.get("href", "")).query))
    bob = fixture.signed_client("activity-http-bob")
    _response, own = _get(bob, "/actividad?user_id=activity-http-alice")
    assert "Mostrando 3 de 3" in own.component_text
    assert all(identifier.startswith("bob-private-") for identifier in own.activity_ids)
    _response, rejected = _get(bob, cursor_link)
    assert rejected.component_state == "unavailable"
    assert rejected.activity_ids == []
    assert "alice-" not in rejected.component_text


def test_activity_history_http_bad_cursor_has_clear_retry_without_false_empty(account_activity_http):
    fixture = account_activity_http
    fixture.seed(25)
    _response, parsed = _get(fixture.signed_client(), "/actividad?cursor=not-a-valid-cursor")
    assert parsed.component_state == "unavailable"
    assert "No hay acciones guardadas" not in parsed.component_text
    assert "Mostrando" not in parsed.component_text
    assert any(link.get("href") == "/actividad" and link["text"] == "Volver a intentar" for link in parsed.component_links)


def test_activity_history_http_dst_and_unknown_date_use_real_filter(account_activity_http):
    fixture = account_activity_http
    fixture.insert("dst-earlier", date="2026-10-25T02:50:00+02:00")
    fixture.insert("dst-later", date="2026-10-25T02:10:00+01:00")
    fixture.insert("unknown-date", date="not-a-date")
    _response, parsed = _get(fixture.signed_client(), "/actividad")
    assert parsed.activity_ids == ["dst-later", "dst-earlier", "unknown-date"]
    assert [time["datetime"] for time in parsed.component_times] == [
        "2026-10-25T01:10:00.000Z", "2026-10-25T00:50:00.000Z"]
    assert "Fecha no establecida" in parsed.component_text
    with fixture.app.app.test_request_context("/actividad", base_url=ORIGIN):
        expected = fixture.app.jinja_madrid_datetime_label("2026-10-25T01:10:00.000Z")
    assert expected in parsed.component_text


@pytest.mark.parametrize("route", ROUTES)
def test_account_activity_http_get_keeps_database_and_sources_unchanged(account_activity_http, route):
    fixture = account_activity_http
    fixture.seed(8)
    client = fixture.signed_client()
    before = fixture.dump()
    with fixture.observe_writes() as writes:
        _response, parsed = _get(client, route)
    assert parsed.component_state == "available"
    assert fixture.dump() == before
    assert writes == []
