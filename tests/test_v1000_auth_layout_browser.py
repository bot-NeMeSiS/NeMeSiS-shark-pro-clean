"""Visual login proof through real guarded App/password/CSRF/redirects.

No real accounts, provider requests, route/authentication/template mocks, or
production writes. Invoke through the original check_local_candidate supervisor.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import threading
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server


@pytest.fixture
def auth_server(monkeypatch, tmp_path):
    a = sys.modules.get("app")
    assert a is not None and a.local_safe_mode_enabled()
    assert Path(a.__file__).resolve() == Path(__file__).resolve().parents[1] / "app.py"
    assert tmp_path.resolve().is_relative_to(Path(a.LOCAL_SAFE_DATA_DIR).resolve())
    database = tmp_path / "owned-auth-layout.sqlite"
    monkeypatch.setattr(a, "DB_PATH", str(database))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    monkeypatch.setitem(a.app.config, "TESTING", False)
    a.seed_core()
    token, password = secrets.token_hex(12), secrets.token_urlsafe(30)
    users = {}
    with sqlite3.connect(database) as conn:
        for mode, role in (("client", "FREE"), ("admin", "ADMIN")):
            ident = "owned-auth-" + mode + "-" + token
            email = ident + "@example.invalid"
            users[mode] = {"id": ident, "email": email}
            conn.execute("""INSERT INTO users
                (id,name,username,email,password_hash,role,membership,membership_source,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""", (ident, "Owned synthetic " + mode, ident, email,
                generate_password_hash(password), role, role, "LOCAL_SAFE_QA", datetime.now(timezone.utc).isoformat()))
    server = make_server("127.0.0.1", 0, a.app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield a, database, f"http://127.0.0.1:{server.server_port}", users, password
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _inspect(page):
    return page.evaluate("""() => {
      const visible=e=>!!e.getClientRects().length;
      const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
      const sample=e=>{const s=getComputedStyle(e);return {box:rect(e),background:s.backgroundColor,
        backgroundImage:s.backgroundImage,opacity:s.opacity,backdropFilter:s.backdropFilter,border:s.borderTopStyle}};
      const form=document.querySelector('.auth-card');
      return {viewport:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+2,
        layout:document.querySelector('[data-auth-layout]')?.getAttribute('data-auth-layout')||null,
        card:sample(form),side:[...document.querySelectorAll('.auth-side')].map(sample),
        hero:[...document.querySelectorAll('.auth-hero')].map(sample),
        inputs:[...form.querySelectorAll('input:not([type=hidden])')].map(e=>({name:e.name,type:e.type,
          autocomplete:e.autocomplete,checked:e.checked,...sample(e)})),
        csrf:!!form.querySelector('input[name=csrf_token]')?.value,
        action:form.getAttribute('action'),method:form.method,
        button:rect(form.querySelector('button[type=submit]')),
        errors:[...form.querySelectorAll('.notice.danger')].filter(visible).map(e=>e.textContent.trim()),
        links:[...form.querySelectorAll('a[href]')].map(e=>({href:e.getAttribute('href'),text:e.textContent.trim(),box:rect(e)}))};
    }""")


@pytest.mark.parametrize("mode", ["client", "admin"])
@pytest.mark.parametrize("width,height", [(320, 800), (390, 844), (834, 1112), (1440, 1000)])
def test_real_login_layout_preserves_password_csrf_session_and_safe_return(auth_server, tmp_path, mode, width, height):
    a, _database, origin, users, password = auth_server
    route = "/cliente-login" if mode == "client" else "/admin-login"
    destination = "/favoritos" if mode == "client" else "/admin/control-center"
    capture_only = os.environ.get("NEMESIS_AUTH_CAPTURE_BASELINE") == "1"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ["NEMESIS_QA_CHROMIUM"])
        context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
        external = []
        def boundary(request):
            if request.request.url.startswith(origin + "/"):
                request.continue_()
            else:
                external.append(request.request.url.split("?")[0])
                request.abort()
        context.route("**/*", boundary)
        page = context.new_page()
        page_errors, http_errors = [], []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("response", lambda response: http_errors.append((urlsplit(response.url).path, response.status)) if response.status >= 400 else None)
        native_reduced_transparency = page.evaluate("matchMedia('(prefers-reduced-transparency: reduce)').matches")
        cdp = context.new_cdp_session(page)
        cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-transparency", "value": "no-preference"}]})
        observations = []
        try:
            response = page.goto(origin + route + "?next=" + destination, wait_until="networkidle")
            assert response.status == 200
            first = _inspect(page)
            first["phase"] = "normal"
            first["native_reduced_transparency"] = native_reduced_transparency
            first["emulated_transparency"] = "no-preference"
            observations.append(first)
            (tmp_path / f"auth-{mode}-{width}.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8")
            page.screenshot(path=str(tmp_path / f"auth-{mode}-{width}-normal.png"), full_page=True)
            assert first["csrf"] and first["method"] == "post"
            assert not first["overflow"]
            assert [item["autocomplete"] for item in first["inputs"][:2]] == ["username", "current-password"]
            remember = next(item for item in first["inputs"] if item["type"] == "checkbox")
            assert remember["checked"] is (mode == "client")
            assert first["card"]["opacity"] == "1"
            if not capture_only:
                assert first["layout"] == "v1000"
                assert page.locator('[data-ns-assistant], .ns-assistant-launcher, #ns-assistant-dialog').count() == 0
                assert first["card"]["box"]["w"] <= 460
                if width >= 834:
                    assert 400 <= first["card"]["box"]["w"] <= 460
                assert not first["side"] and not first["hero"]
                assert first["card"]["background"] == "rgb(7, 21, 37)"
                assert all(item["background"].startswith("rgb(") for item in first["inputs"][:2])
                assert first["card"]["backdropFilter"] == "none"
            csrf = page.locator('.auth-card input[name="csrf_token"]').input_value()
            rejected = context.request.post(origin + route, form={"csrf_token": "owned-invalid-token", "login": users[mode]["email"], "password": password})
            assert rejected.status == 403
            fields = page.locator('.auth-card input[name="login"]')
            fields.fill(users[mode]["email"])
            page.locator('.auth-card input[name="password"]').fill(secrets.token_urlsafe(25))
            page.locator('.auth-card button[type="submit"]').click()
            page.wait_for_load_state("networkidle")
            assert page.url.split("?")[0] == origin + route
            error = _inspect(page)
            error["phase"] = "invalid-password"
            observations.append(error)
            assert len(error["errors"]) == 1 and not error["overflow"]
            page.screenshot(path=str(tmp_path / f"auth-{mode}-{width}-error.png"), full_page=True)
            if not capture_only:
                assert page.locator('[data-ns-assistant], .ns-assistant-launcher, #ns-assistant-dialog').count() == 0
                page.emulate_media(forced_colors="active")
                forced = _inspect(page)
                forced["phase"] = "forced-colors"
                observations.append(forced)
                assert not forced["overflow"] and forced["card"]["opacity"] == "1"
                assert forced["card"]["border"] == "solid"
                page.emulate_media(forced_colors="none")
                cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-transparency", "value": "reduce"}]})
                reduced = _inspect(page)
                reduced["phase"] = "reduced-transparency"
                observations.append(reduced)
                assert reduced["card"]["background"].startswith("rgb(")
                cdp.send("Emulation.setEmulatedMedia", {"features": []})
            page.locator('.auth-card input[name="login"]').fill(users[mode]["email"])
            page.locator('.auth-card input[name="password"]').fill(password)
            page.locator('.auth-card input[name="password"]').focus()
            assert page.locator('.auth-card input[name="password"]').evaluate("e=>document.activeElement===e")
            page.locator('.auth-card button[type="submit"]').click()
            # Authenticated sports views can keep polling. Their native HTML
            # readiness, not an absence of all network traffic, proves return.
            page.wait_for_url(origin + destination, wait_until="domcontentloaded")
            page.locator("main#main-content").wait_for(state="attached")
            cookies = context.cookies()
            session_cookie = next(row["value"] for row in cookies if row["name"] == a.app.config["SESSION_COOKIE_NAME"])
            session = a.app.session_interface.get_signing_serializer(a.app).loads(session_cookie)
            assert session["user_id"] == users[mode]["id"]
            assert session["auth_session_id"]
            assert not external, external
            assert not page_errors, page_errors
            assert not http_errors, http_errors
            (tmp_path / f"auth-{mode}-{width}.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            cdp.detach()
            context.close()
            browser.close()


def test_real_selected_plan_keeps_existing_registration_and_return_fields(auth_server):
    a, _database, _origin, _users, _password = auth_server
    client = a.app.test_client()
    response = client.get("/cliente-login?plan=ELITE&next=/favoritos", base_url="http://127.0.0.1")
    assert response.status_code == 200
    class Controls(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_login, self.inputs, self.links = False, {}, []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "form":
                self.in_login = attrs.get("action") == "/cliente-login"
            if self.in_login and tag == "input":
                self.inputs[attrs.get("name")] = attrs.get("value")
            if tag == "a":
                self.links.append(attrs.get("href", ""))
        def handle_endtag(self, tag):
            if tag == "form":
                self.in_login = False
    controls = Controls()
    controls.feed(response.get_data(as_text=True))
    assert controls.inputs["next"] == "/favoritos"
    assert controls.inputs["plan"] == "ELITE"
    assert controls.inputs["csrf_token"]
    assert any(urlsplit(href).path == "/registro" and parse_qs(urlsplit(href).query) == {"plan": ["ELITE"], "next": ["/favoritos"]} for href in controls.links)
