"""Actual LOCAL SAFE App/auth/router/admin templates over owned SQLite only.

Run through tools/check_local_candidate.py (the original process boundary).
No auth, router, renderer, provider or business-engine replacement is used.
Browser requests are served by this very WSGI App on loopback; only external
browser resources are blocked. The only successful POST is the real local login.
"""
from contextlib import closing
from html.parser import HTMLParser
import os
from pathlib import Path
import sqlite3
import threading
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS = (
    "/admin/dashboard", "/admin/matches", "/admin/realtime-center", "/admin/picks",
    "/admin/telegram/command-center", "/admin/users", "/admin/memberships", "/admin/payments",
    "/admin/shark-center", "/admin/data-center", "/admin/automation-center", "/admin/sentinel-issues",
    "/admin/highlights-center", "/admin/system", "/admin/final-release", "/admin/dashboard#master-audit-title",
)
GROUPS = ("Deporte y contenido", "Clientes y planes", "Operación y seguridad", "Sistema")
TOKEN_BASE = "http://127.0.0.1"


class _Node:
    def __init__(self, tag="document", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def all(self, tag=None, attrs=None):
        found = []
        for child in self.children:
            if not isinstance(child, _Node):
                continue
            if (tag is None or child.tag == tag) and all(
                    key in child.attrs and (value is None or child.attrs[key] == value)
                    for key, value in (attrs or {}).items()):
                found.append(child)
            found.extend(child.all(tag, attrs))
        return found

    def first(self, tag=None, attrs=None):
        return next(iter(self.all(tag, attrs)), None)

    def text(self):
        return "".join(child.text() if isinstance(child, _Node) else child for child in self.children)


class _Document(HTMLParser):
    """Small stdlib HTML tree for assertions over the actual HTTP response."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _get(client, url, *, follow_redirects=False):
    return client.get(url, base_url=TOKEN_BASE, follow_redirects=follow_redirects,
                      environ_overrides={"REMOTE_ADDR": "127.0.0.1"})


def _post(client, url, data):
    return client.post(url, base_url=TOKEN_BASE, data=data, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})


@pytest.fixture
def actual_admin(app_module, tmp_path, monkeypatch):
    assert Path(app_module.__file__).resolve() == ROOT / "app.py"
    assert app_module.local_safe_mode_enabled()
    original = Path(app_module.DB_PATH).resolve()
    path = tmp_path / "v1000-owned-admin.sqlite"
    assert original.is_relative_to(ROOT / "data/local_dev")
    assert path.resolve().is_relative_to(ROOT / "data/local_dev")
    with closing(sqlite3.connect(original.as_uri() + "?mode=ro", uri=True)) as source:
        with closing(sqlite3.connect(path)) as target:
            source.backup(target)
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", str(path))
    from engines.founder_os_engine import ensure_founder_os_schema
    ensure_founder_os_schema(path)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM founder_alerts")
        conn.execute("DELETE FROM founder_obligations")
        conn.execute("""INSERT INTO founder_alerts
            (id,fingerprint,severity,category,title,message,status,last_seen_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            ("v1000-owned-alert", "v1000-owned-fingerprint", "HIGH", "SYNTHETIC_QA",
             "QA: evidencia pendiente de revisión", "Alerta sintética retenida para verificar presentación.",
             "OPEN", "2026-10-26T17:30:00Z"))
    client = app_module.app.test_client()
    login = _get(client, "/admin-login")
    assert login.status_code == 200
    soup = _Document(login.get_data(as_text=True)).root
    token = soup.first("meta", {"name": "csrf-token"}).attrs["content"]
    response = _post(client, "/admin-login", {
        "login": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"],
        "csrf_token": token, "next": "/admin/founder-os",
    })
    assert response.status_code == 302, response.get_data(as_text=True)[:300]
    assert urlsplit(response.location).path == "/admin/founder-os"
    cookie_name = app_module.app.config.get("SESSION_COOKIE_NAME", "session")
    cookie = client.get_cookie(cookie_name, domain="127.0.0.1")
    assert cookie is not None
    with client.session_transaction(base_url=TOKEN_BASE) as session:
        assert session.get("user_role") == "ADMIN"
        actor_id = session["user_id"]
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT role FROM users WHERE id=?", (actor_id,)).fetchone()[0] == "ADMIN"
    return app_module, client, path, cookie_name, cookie.value


def test_actual_login_and_all_sixteen_destinations_preserve_every_href(actual_admin):
    module, client, path, _name, _value = actual_admin
    for href in DESTINATIONS:
        response = _get(client, href.split("#", 1)[0], follow_redirects=True)
        assert response.status_code == 200, (href, response.status_code)
        assert response.request.path != "/admin-login", href
        assert all(urlsplit(previous.location).path.startswith("/admin/")
                   for previous in response.history), href
        soup = _Document(response.get_data(as_text=True)).root
        nav = soup.first(attrs={"data-v1000-admin-directory": None})
        assert nav is not None, href
        assert {a.attrs["href"] for a in nav.all("a", {"data-v1000-admin-destination": None})} == set(DESTINATIONS)
        assert len(nav.all("a", {"data-v1000-admin-destination": None})) == 16
        assert [s.first("span").text().strip() for s in nav.all("summary")] == list(GROUPS)
        assert soup.first(attrs={"data-master-storage-lock": None}) is not None
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT status FROM founder_alerts WHERE id='v1000-owned-alert'").fetchone()[0] == "OPEN"
        assert conn.execute("SELECT COUNT(*) FROM founder_obligations").fetchone()[0] == 0


def test_actual_founder_prioritizes_attention_and_keeps_dated_evidence_and_unknown_cost(actual_admin):
    _module, client, path, _name, _value = actual_admin
    response = _get(client, "/admin/founder-os")
    assert response.status_code == 200
    soup = _Document(response.get_data(as_text=True)).root
    founder = soup.first(attrs={"data-founder-os": "true"})
    ids = [s.attrs.get("id") for s in founder.children if isinstance(s, _Node) and s.tag == "section"]
    assert ids.index("inbox") < ids.index("overview")
    assert "QA: evidencia pendiente de revisión" in soup.first(attrs={"id": "inbox"}).text()
    assert soup.first(attrs={"data-v1000-founder-reading": None}).first("time", {"datetime": None}) is not None
    cost = next(a for a in soup.first(attrs={"id": "overview"}).all("article") if "Coste conocido/mes" in a.text())
    assert cost.first("strong").text().strip() == "No registrado"
    form = soup.first("form", {"action": "/admin/founder-os/alerts/v1000-owned-alert/ack"})
    assert form.first("input", {"name": "csrf_token"}) is not None
    denied = _post(client, "/admin/founder-os/alerts/v1000-owned-alert/ack", {})
    assert denied.status_code == 403
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT status FROM founder_alerts WHERE id='v1000-owned-alert'").fetchone()[0] == "OPEN"


def test_anonymous_session_does_not_gain_admin_from_grouped_links(actual_admin):
    module, _client, _path, _name, _value = actual_admin
    visitor = module.app.test_client()
    for href in DESTINATIONS:
        response = _get(visitor, href.split("#", 1)[0])
        assert response.status_code in {302, 403}, (href, response.status_code)
        if response.status_code == 302:
            assert urlsplit(response.location).path == "/admin-login"


def test_actual_unavailable_founder_read_does_not_turn_into_zero_incidents(actual_admin):
    _module, client, path, _name, _value = actual_admin
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE founder_alerts")
    response = _get(client, "/admin/founder-os")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    document = _Document(html).root
    assert "Sin recuento confirmado" in html
    assert "No equivale a cero incidencias" in html
    assert "0 alertas abiertas en el registro consultado" not in html
    assert document.first(attrs={"data-master-storage-lock": None}) is not None
    assert document.first(attrs={"id": "systems"}) is not None
    assert document.first("a", {"href": "/admin/backups"}) is not None


@pytest.fixture
def actual_http(actual_admin):
    from werkzeug.serving import make_server
    module, client, path, cookie_name, cookie = actual_admin
    server = make_server("127.0.0.1", 0, module.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", cookie_name, cookie, path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("width", [320, 390, 1440])
def test_actual_admin_browser_groups_disclosures_keyboard_and_founder_density(actual_http, tmp_path, width):
    from playwright.sync_api import sync_playwright
    base, cookie_name, cookie, path = actual_http
    requests = []
    errors = []
    with sync_playwright() as playwright:
        launch = {"headless": True, "args": ["--no-sandbox"]}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            launch["executable_path"] = os.environ["NEMESIS_QA_CHROMIUM"]
        browser = playwright.chromium.launch(**launch)
        context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
        try:
            context.add_cookies([{"name": cookie_name, "value": cookie, "url": base, "httpOnly": True}])
            page = context.new_page()
            page.set_default_timeout(10000)
            def guard(route):
                requests.append((route.request.method, urlsplit(route.request.url).path))
                if route.request.url.startswith(base + "/"):
                    route.continue_()
                else:
                    route.abort()
            page.route("**/*", guard)
            page.on("pageerror", lambda error: errors.append(str(error)))
            result = page.goto(base + "/admin/founder-os", wait_until="networkidle")
            assert result.status == 200
            assert page.locator(".founder-os h1").inner_text() == "Control fundador"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert page.locator("#inbox").bounding_box()["y"] < page.locator("#overview").bounding_box()["y"]
            if width > 980:
                nav = page.locator("[data-v1000-admin-directory]")
                assert nav.is_visible()
                assert set(nav.locator("a").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")) == set(DESTINATIONS)
                summary = nav.locator("summary").first
                summary.focus()
                page.keyboard.press("Enter")
                assert not nav.locator("details").first.get_attribute("open")
                page.keyboard.press("Space")
                assert nav.locator("details").first.get_attribute("open") is not None
                page.locator(".v1000-admin-shortcuts [data-open-explore]").click()
            else:
                page.locator(".v933-admin-mobile-header [data-open-explore]").click()
            dialog = page.locator("#app-navigation-dialog")
            assert dialog.is_visible()
            assert [text.strip() for text in dialog.locator("[data-explore-group] h3").all_text_contents()] == list(GROUPS)
            links = dialog.locator("[data-explore-item]").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")
            assert set(DESTINATIONS) <= set(links)
            assert {"/admin/backups", "/admin/operations-center", "/admin/founder-os"} <= set(links)
            dialog.locator("[data-explore-query]").fill("usuarios")
            assert dialog.locator("[data-explore-item]:visible").count() == 1
            assert dialog.locator("[data-explore-item]:visible").get_attribute("href") == "/admin/users"
            dialog.locator("[data-explore-query]").fill("clientes")
            assert set(dialog.locator("[data-explore-item]:visible").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")) == {"/admin/users", "/admin/memberships", "/admin/payments"}
            dialog.locator("[data-explore-query]").fill("incidencias")
            assert dialog.locator("[data-explore-item]:visible").count() == 1
            assert dialog.locator("[data-explore-item]:visible").get_attribute("href") == "/admin/sentinel-issues"
            page.keyboard.press("Escape")
            assert not dialog.is_visible()
            page.screenshot(path=str(tmp_path / f"actual-admin-{width}.png"))
            assert not errors
            assert all(method == "GET" for method, _ in requests), requests
        finally:
            context.close()
            browser.close()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT status FROM founder_alerts WHERE id='v1000-owned-alert'").fetchone()[0] == "OPEN"


def test_actual_admin_explore_without_javascript_keeps_every_destination(actual_http):
    from playwright.sync_api import sync_playwright
    base, cookie_name, cookie, _path = actual_http
    with sync_playwright() as playwright:
        launch = {"headless": True, "args": ["--no-sandbox"]}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            launch["executable_path"] = os.environ["NEMESIS_QA_CHROMIUM"]
        browser = playwright.chromium.launch(**launch)
        context = browser.new_context(viewport={"width": 390, "height": 900}, java_script_enabled=False)
        try:
            context.add_cookies([{"name": cookie_name, "value": cookie, "url": base}])
            page = context.new_page()
            page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort())
            result = page.goto(base + "/admin/explorar", wait_until="networkidle")
            assert result.status == 200
            links = page.locator("[data-app-explore] [data-explore-item]").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")
            assert set(DESTINATIONS) <= set(links)
            assert page.locator("[data-app-explore] [data-explore-group]:visible").count() == 4
            for query, expected in (("clientes", {"/admin/users", "/admin/memberships", "/admin/payments"}), ("incidencias", {"/admin/sentinel-issues"})):
                result = page.goto(base + "/admin/explorar?q=" + query, wait_until="networkidle")
                assert result.status == 200
                assert set(page.locator("[data-explore-item]:visible").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")) == expected
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        finally:
            context.close()
            browser.close()
