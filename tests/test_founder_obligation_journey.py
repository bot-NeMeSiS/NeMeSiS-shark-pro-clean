"""Founder obligation forms over owned SQLite and the original LOCAL SAFE App.

These are bookkeeping records only. No provider, charge, notification or external
request is made. Run with tools/check_local_candidate.py.
"""
from contextlib import closing
import os
import sqlite3
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from engines import founder_os_engine as founder
from browser_http_server import owned_http_server
from test_v1000_actual_admin_navigation import actual_admin, _Document, _get, _post


def _rows(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            "SELECT * FROM founder_obligations ORDER BY id")]


def _record(path):
    return founder.save_obligation(path, {
        "label": "Obligación original QA", "provider_key": "render", "amount": "0",
        "currency": "EUR", "cadence": "monthly", "due_date": "2027-01-15",
        "auto_renew": "1", "payment_status": "PENDING", "notes": "Nota original QA",
    })["obligation"]


def _form(response):
    document = _Document(response.get_data(as_text=True)).root
    return document, document.first("form", {"data-obligation-form": None})


def _token(client):
    document, form = _form(_get(client, "/admin/founder-os"))
    return form.first("input", {"name": "csrf_token"}).attrs["value"]


@pytest.mark.parametrize("editing", [False, True])
def test_rejected_save_preserves_fields_and_error_without_url_or_session_payload(actual_admin, editing):
    _module, client, path, _name, _cookie = actual_admin
    existing = _record(path) if editing else {}
    before = _rows(path)
    payload = {"id": existing.get("id", ""), "label": "   ", "provider_key": "thesportsdb",
        "plan": 'QA-PRIVATE-PLAN-"<&', "amount": "27.50", "currency": "EUR",
        "cadence": "yearly", "due_date": "2027-04-12", "payment_status": "UNKNOWN",
        "auto_renew": "1", "notes": 'QA-PRIVATE-NOTE-</textarea><script>alert(1)</script>',
        "csrf_token": _token(client)}
    response = _post(client, "/admin/founder-os/obligations/save", payload)
    assert response.status_code == 422
    assert "Location" not in response.headers
    assert "no-store" in response.headers.get("Cache-Control", "")
    assert "founder-os.css" in response.get_data(as_text=True)
    document, form = _form(response)
    error = document.first(attrs={"data-obligation-error": None})
    assert error is not None and error.attrs.get("role") == "alert"
    assert "necesita un nombre" in error.text()
    assert document.first("details", {"class": "founder-os-editor", "open": None}) is not None
    for name in ("id", "label", "plan", "amount", "currency", "due_date"):
        assert form.first("input", {"name": name}).attrs["value"] == payload[name]
    for name in ("provider_key", "cadence", "payment_status"):
        select = form.first("select", {"name": name})
        assert select.first("option", {"selected": None}).attrs["value"] == payload[name]
    assert form.first("input", {"name": "auto_renew", "checked": None}) is not None
    assert form.first("textarea", {"name": "notes"}).text() == payload["notes"]
    assert "<script>alert(1)</script>" not in response.get_data(as_text=True)
    with client.session_transaction(base_url="http://127.0.0.1") as session:
        assert "QA-PRIVATE" not in repr(dict(session))
    assert _rows(path) == before


def test_missing_paid_record_is_not_reported_as_success(actual_admin):
    _module, client, path, _name, _cookie = actual_admin
    _record(path)
    before = _rows(path)
    response = _post(client, "/admin/founder-os/obligations/absent-qa/paid", {"csrf_token": _token(client)})
    assert response.status_code == 409
    assert "Location" not in response.headers
    assert "No se confirmó el cambio" in response.get_data(as_text=True)
    assert _rows(path) == before


def test_native_edit_and_new_links_load_distinct_modes_without_writes(actual_admin):
    _module, client, path, _name, _cookie = actual_admin
    existing = _record(path)
    before = _rows(path)
    response = _get(client, "/admin/founder-os")
    document, _ = _form(response)
    edit = document.first("a", {"data-edit-obligation": None})
    assert edit is not None and "edit=" in edit.attrs["href"]
    editing = _get(client, edit.attrs["href"])
    assert editing.status_code == 200
    document, form = _form(editing)
    assert form.first("input", {"name": "id"}).attrs["value"] == existing["id"]
    assert form.first("input", {"name": "label"}).attrs["value"] == existing["label"]
    assert float(form.first("input", {"name": "amount"}).attrs["value"]) == 0
    assert "Guardar cambios" in form.text()
    cancel = document.first("a", {"data-obligation-reset": None})
    assert cancel is not None and "hidden" not in cancel.attrs
    cleared = _get(client, cancel.attrs["href"])
    document, form = _form(cleared)
    assert form.first("input", {"name": "id"}).attrs["value"] == ""
    assert form.first("input", {"name": "label"}).attrs["value"] == ""
    assert "Guardar obligación" in form.text()
    assert document.first("details", {"class": "founder-os-editor", "open": None}) is not None
    assert _rows(path) == before


def test_unknown_edit_id_and_forged_success_query_do_not_claim_a_change(actual_admin):
    _module, client, path, _name, _cookie = actual_admin
    _record(path)
    before = _rows(path)
    unknown = _get(client, "/admin/founder-os?edit=missing-qa")
    assert unknown.status_code == 404
    assert "Obligación no encontrada" in unknown.get_data(as_text=True)
    forged = _get(client, "/admin/founder-os?billing=paid&reason=QA-PRIVATE-NOTE")
    document, _ = _form(forged)
    assert document.first(attrs={"data-obligation-notice": None}) is None
    assert "QA-PRIVATE-NOTE" not in forged.get_data(as_text=True)
    assert _rows(path) == before


def test_real_save_edit_and_paid_feedback_preserve_csrf_and_record_identity(actual_admin):
    module, client, path, _name, _cookie = actual_admin
    payload = {"label": "Nueva obligación QA", "amount": "12.50", "cadence": "monthly",
        "due_date": "2027-01-15", "csrf_token": _token(client)}
    denied = _post(client, "/admin/founder-os/obligations/save", {**payload, "csrf_token": "invalid"})
    assert denied.status_code == 403 and _rows(path) == []
    created = _post(client, "/admin/founder-os/obligations/save", payload)
    assert created.status_code == 302 and urlsplit(created.location).path == "/admin/founder-os"
    row = _rows(path)[0]
    page = _get(client, created.location)
    document, _ = _form(page)
    assert "Obligación guardada" in document.first(attrs={"data-obligation-notice": None}).text()
    assert _Document(_get(client, "/admin/founder-os").get_data(as_text=True)).root.first(
        attrs={"data-obligation-notice": None}) is None
    changed = _post(client, "/admin/founder-os/obligations/save", {
        **payload, "id": row["id"], "label": "Obligación corregida QA"})
    assert changed.status_code == 302
    assert len(_rows(path)) == 1 and _rows(path)[0]["id"] == row["id"]
    before = _rows(path)
    paid_denied = _post(client, f"/admin/founder-os/obligations/{row['id']}/paid", {"csrf_token": "invalid"})
    assert paid_denied.status_code == 403 and _rows(path) == before
    paid = _post(client, f"/admin/founder-os/obligations/{row['id']}/paid", {"csrf_token": _token(client)})
    assert paid.status_code == 302
    document, _ = _form(_get(client, paid.location))
    assert "marcada como pagada" in document.first(attrs={"data-obligation-notice": None}).text()
    assert _rows(path)[0]["payment_status"] == "PAID"
    assert _rows(path)[0]["due_date"] == "2027-02-15"
    visitor = module.app.test_client()
    assert _get(visitor, "/admin/founder-os?edit=" + row["id"]).status_code == 302
    response = _post(visitor, "/admin/founder-os/obligations/save", {"label": "Forbidden QA"})
    assert response.status_code in {302, 403}
    assert len(_rows(path)) == 1


@pytest.fixture
def obligation_http(actual_admin):
    module, _client, path, cookie_name, cookie = actual_admin
    existing = _record(path)
    with owned_http_server(module.app) as server:
        yield f"http://127.0.0.1:{server.server_port}", cookie_name, cookie, path, existing


@pytest.mark.parametrize("width,javascript", [(390, True), (1440, True), (390, False)])
def test_browser_cancel_edit_then_create_never_overwrites_original(obligation_http, tmp_path, width, javascript):
    base, cookie_name, cookie, path, existing = obligation_http
    with sync_playwright() as playwright:
        launch = {"headless": True, "args": ["--no-sandbox", "--accept-lang=es-ES,es"]}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            launch["executable_path"] = os.environ["NEMESIS_QA_CHROMIUM"]
        browser = playwright.chromium.launch(**launch)
        context = browser.new_context(viewport={"width": width, "height": 900}, locale="es-ES",
            timezone_id="Europe/Madrid", reduced_motion="reduce", service_workers="block",
            java_script_enabled=javascript)
        context.add_cookies([{"name": cookie_name, "value": cookie, "url": base, "httpOnly": True}])
        external, errors, requests = [], [], []
        def boundary(route):
            requests.append((route.request.method, urlsplit(route.request.url).path))
            if route.request.url.startswith(base + "/"):
                route.continue_()
            else:
                external.append(route.request.url)
                route.abort()
        context.route("**/*", boundary)
        page = context.new_page()
        page.set_default_timeout(7000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            assert page.goto(base + "/admin/founder-os?new=1#founder-obligation-editor", wait_until="load").status == 200
            assert page.locator("[data-obligation-reset]").is_hidden()
            page.locator("[data-edit-obligation]").click()
            form = page.locator("[data-obligation-form]")
            assert form.locator('[name="id"]').input_value() == existing["id"]
            assert form.locator('[name="label"]').input_value() == existing["label"]
            if javascript:
                assert form.locator('[name="label"]').evaluate("el => el === document.activeElement")
            form.locator('[name="label"]').fill("   ")
            form.locator('[name="notes"]').fill("QA preserved draft")
            with page.expect_response(lambda response: urlsplit(response.url).path == "/admin/founder-os/obligations/save") as rejected:
                form.locator('button[type="submit"]').click()
            assert rejected.value.status == 422
            page.wait_for_url(base + "/admin/founder-os/obligations/save#founder-obligation-editor", wait_until="load")
            error = page.locator("[data-obligation-error]")
            assert error.is_visible()
            assert page.locator('link[href*="founder-os.css"]').count() == 1
            assert page.evaluate("[...document.styleSheets].some(sheet => sheet.href?.includes('founder-os.css') && sheet.cssRules.length > 0)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert form.locator('[name="notes"]').input_value() == "QA preserved draft"
            assert form.locator('[name="id"]').input_value() == existing["id"]
            if javascript:
                assert error.evaluate("el => el === document.activeElement"), page.evaluate("document.activeElement.outerHTML.slice(0, 400)")
                if width == 390:
                    page.screenshot(path=str(tmp_path / "founder-obligation-rejected-mobile.png"))
            page.locator("[data-obligation-reset]").click()
            assert page.locator("[data-obligation-reset]").is_hidden()
            assert form.locator('[name="id"]').input_value() == ""
            assert form.locator('[name="label"]').input_value() == ""
            assert form.locator('[name="notes"]').input_value() == ""
            assert not form.locator('[name="auto_renew"]').is_checked()
            if javascript:
                assert form.locator('[name="label"]').evaluate("el => el === document.activeElement")
                if width == 1440:
                    page.screenshot(path=str(tmp_path / "founder-obligation-new-desktop.png"))
            form.locator('[name="label"]').fill("Nueva obligación desde navegador QA")
            with page.expect_response(lambda response: urlsplit(response.url).path == "/admin/founder-os/obligations/save") as saved:
                form.locator('button[type="submit"]').click()
            assert saved.value.status == 302
            page.wait_for_url(base + "/admin/founder-os#billing")
            assert page.locator("[data-obligation-notice]").is_visible()
            rows = _rows(path)
            assert len(rows) == 2
            original = next(row for row in rows if row["id"] == existing["id"])
            assert original["label"] == existing["label"] and original["notes"] == existing["notes"]
            assert original["amount"] == 0
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert not external and not errors
            assert [url for method, url in requests if method == "POST"] == [
                "/admin/founder-os/obligations/save", "/admin/founder-os/obligations/save"]
        finally:
            context.close()
            browser.close()
