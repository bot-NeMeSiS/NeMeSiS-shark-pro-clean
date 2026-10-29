"""Actual card/base controls with synthetic, explicitly held HTTP outcomes.

No provider or account mutation is made. The production template and favorite
controller run in Chromium; unrelated jobs are excluded from this focused UI
fixture. The endpoint, method, payload and CSRF header are observed unchanged.
"""
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit

from flask import render_template_string
import pytest
from playwright.sync_api import expect

from test_app_navigation_browser import browser

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def favorite_page(browser, app_module):
    match = {
        "id": "favorite-shared-qa", "home_team": "Local QA", "away_team": "Visitante QA",
        "competition_name": "Liga QA", "kickoff_time": "20:30",
        "source": "SIMULATED_QA", "is_favorite": False,
    }
    with app_module.app.test_request_context("/favorite-ui-qa"):
        markup = render_template_string("""{% extends 'base.html' %}
            {% from 'components/v933_ui.html' import match_card with context %}
            {% block content %}
            <section id="favorite-primary">{{ match_card(match, true, false) }}</section>
            <section id="favorite-secondary">{{ match_card(match, true, false) }}</section>
            <section id="favorite-disabled">{{ match_card(match, true, false) }}</section>
            <section id="favorite-other-kind">{{ match_card(match, true, false) }}</section>
            <section id="favorite-other-value">{{ match_card(other, true, false) }}</section>
            {% endblock %}""", match=match, other={**match, "id": "favorite-other-qa"},
            current_user={"id": "favorite-ui-qa", "role": "FREE", "membership": "FREE"}, data={})
    markup = re.sub(
        r"<script\b[^>]*>(.*?)</script>",
        lambda entry: entry.group(0) if any(marker in entry.group(1) for marker in
            ("window.nemesisCsrfToken =", "fetch('/api/favorites'", "function nsAppEnhance()")) else "",
        markup, flags=re.S | re.I,
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
    context.add_init_script("""
        window.favoriteRequests = [];
        const originalFetch = window.fetch;
        window.fetch = function (url, options) {
          if (new URL(url, location.href).pathname === '/api/favorites') {
            window.favoriteRequests.push({method: options.method,
              payload: JSON.parse(options.body), csrf: options.headers['X-CSRF-Token']});
          }
          return originalFetch.apply(this, arguments);
        };
    """)
    page = context.new_page()
    errors, external, pending = [], [], []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def serve(route):
        url = urlsplit(route.request.url)
        if url.netloc != "favorites.invalid":
            external.append(url.netloc)
            route.abort()
        elif url.path == "/favorite-ui-qa":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=markup)
        elif url.path == "/api/favorites":
            pending.append(route)
        elif url.path.startswith("/static/"):
            asset = (ROOT / url.path.lstrip("/")).resolve()
            if asset.is_relative_to(ROOT / "static") and asset.is_file():
                route.fulfill(status=200,
                    content_type=mimetypes.guess_type(str(asset))[0] or "application/octet-stream",
                    body=asset.read_bytes())
            else:
                route.fulfill(status=404, body="No QA asset")
        else:
            route.fulfill(status=404, body="No QA endpoint")

    page.route("**/*", serve)
    page.goto("https://favorites.invalid/favorite-ui-qa")
    page.locator("#favorite-disabled .fav-star").evaluate("button => { button.disabled = true; }")
    page.locator("#favorite-other-kind .fav-star").evaluate("button => { button.dataset.kind = 'team'; }")
    try:
        yield page, pending
        assert not errors and not external, (errors, external)
    finally:
        for route in pending:
            route.abort("failed")
        context.close()


def _button(page, name):
    return page.locator(f"#favorite-{name} .fav-star")


def _finish(route, *, status=200, payload=None):
    route.fulfill(status=status, content_type="application/json",
                  body=json.dumps({"ok": True} if payload is None else payload))


def test_copies_share_pending_and_confirmed_state_without_changing_other_identities(favorite_page):
    page, pending = favorite_page
    primary = _button(page, "primary")
    secondary = _button(page, "secondary")
    protected = _button(page, "disabled")
    primary.click()
    expect(primary).to_be_disabled()
    expect(secondary).to_be_disabled()
    expect(protected).to_be_disabled()
    for name in ("other-kind", "other-value"):
        expect(_button(page, name)).to_be_enabled()
        expect(_button(page, name)).to_have_attribute("aria-pressed", "false")
    # dispatchEvent can bypass the browser's native disabled-click suppression.
    secondary.dispatch_event("click")
    protected.dispatch_event("click")
    page.evaluate("""() => {
        const late = document.getElementById('favorite-secondary').cloneNode(true);
        late.id = 'favorite-late';
        const button = late.querySelector('.fav-star');
        button.disabled = false;
        document.querySelector('main').append(late);
        button.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    }""")
    assert page.evaluate("favoriteRequests.length") == 1
    assert len(pending) == 1
    call = page.evaluate("favoriteRequests[0]")
    assert call["method"] == "POST"
    assert call["payload"] == {"kind": "match", "value": "favorite-shared-qa", "label": "Local QA vs Visitante QA"}
    assert call["csrf"] == page.locator('meta[name="csrf-token"]').get_attribute("content")
    assert call["csrf"]
    for name in ("primary", "secondary", "disabled", "late"):
        expect(_button(page, name)).to_have_attribute("aria-pressed", "false")

    _finish(pending.pop(0))
    for name in ("primary", "secondary", "disabled", "late"):
        expect(_button(page, name)).to_have_attribute("aria-pressed", "true")
        expect(_button(page, name)).to_have_attribute("title", "Quitar favorito")
    expect(primary).to_be_enabled()
    expect(secondary).to_be_enabled()
    expect(_button(page, "late")).to_be_enabled()
    expect(protected).to_be_disabled()
    expect(page.locator("#nsToastHost .ns-toast")).to_have_text("Favorito guardado.")

    # Removing through the other representation must now send DELETE.
    secondary.click()
    expect(primary).to_be_disabled()
    expect(secondary).to_be_disabled()
    assert page.evaluate("favoriteRequests[1].method") == "DELETE"
    _finish(pending.pop(0))
    for name in ("primary", "secondary", "disabled", "late"):
        expect(_button(page, name)).to_have_attribute("aria-pressed", "false")
        expect(_button(page, name)).to_have_attribute("title", "Guardar favorito")
    expect(primary).to_be_enabled()
    expect(secondary).to_be_enabled()
    expect(protected).to_be_disabled()
    expect(page.locator("#nsToastHost .ns-toast").last).to_have_text("Favorito quitado.")
    for name in ("other-kind", "other-value"):
        expect(_button(page, name)).to_have_attribute("aria-pressed", "false")
        expect(_button(page, name)).to_be_enabled()


@pytest.mark.parametrize("failure", ["http", "invalid-json", "network"])
@pytest.mark.parametrize("saved", [False, True])
def test_failed_operation_keeps_every_copy_and_restores_previous_disabled_state(favorite_page, failure, saved):
    page, pending = favorite_page
    if saved:
        page.evaluate("""() => {
          for (const name of ['primary', 'secondary', 'disabled']) {
            const button = document.querySelector('#favorite-' + name + ' .fav-star');
            button.classList.add('active'); button.setAttribute('aria-pressed', 'true');
            button.title = button.dataset.labelRemove;
          }
        }""")
    primary = _button(page, "primary")
    secondary = _button(page, "secondary")
    primary.click()
    expect(primary).to_be_disabled()
    expect(secondary).to_be_disabled()
    assert len(pending) == 1
    route = pending.pop(0)
    if failure == "http":
        _finish(route, status=503, payload={"ok": False})
    elif failure == "invalid-json":
        route.fulfill(status=200, content_type="application/json", body="{invalid")
    else:
        route.abort("failed")
    expect(primary).to_be_enabled()
    expect(secondary).to_be_enabled()
    expect(_button(page, "disabled")).to_be_disabled()
    for name in ("primary", "secondary", "disabled", "other-kind", "other-value"):
        unchanged_saved = saved and name in ("primary", "secondary", "disabled")
        expect(_button(page, name)).to_have_attribute("aria-pressed", str(unchanged_saved).lower())
        expect(_button(page, name)).to_have_attribute("title", "Quitar favorito" if unchanged_saved else "Guardar favorito")
    expect(page.locator("#nsToastHost .ns-toast")).to_have_text(
        "No se pudo actualizar el favorito. Inténtalo de nuevo.")
    assert page.evaluate("favoriteRequests.length") == 1
    assert page.evaluate("favoriteRequests[0].method") == ("DELETE" if saved else "POST")
    # A new explicit click is allowed after failure; no automatic retry occurred.
    secondary.click()
    expect(primary).to_be_disabled()
    assert page.evaluate("favoriteRequests.length") == 2
    _finish(pending.pop(0))
    expect(primary).to_have_attribute("aria-pressed", str(not saved).lower())
    expect(secondary).to_have_attribute("aria-pressed", str(not saved).lower())
    expect(_button(page, "disabled")).to_be_disabled()


def test_distinct_entities_can_finish_independently(favorite_page):
    page, pending = favorite_page
    _button(page, "primary").click()
    _button(page, "other-kind").click()
    _button(page, "other-value").click()
    assert page.evaluate("favoriteRequests.map(call => [call.payload.kind, call.payload.value])") == [
        ["match", "favorite-shared-qa"], ["team", "favorite-shared-qa"], ["match", "favorite-other-qa"]]
    expect(_button(page, "primary")).to_be_disabled()
    expect(_button(page, "other-kind")).to_be_disabled()
    expect(_button(page, "other-value")).to_be_disabled()
    first, second, third = pending
    _finish(second)
    pending.remove(second)
    expect(_button(page, "other-kind")).to_have_attribute("aria-pressed", "true")
    expect(_button(page, "other-kind")).to_be_enabled()
    expect(_button(page, "primary")).to_be_disabled()
    expect(_button(page, "primary")).to_have_attribute("aria-pressed", "false")
    _finish(third, status=503, payload={"ok": False})
    pending.remove(third)
    expect(_button(page, "other-value")).to_be_enabled()
    expect(_button(page, "other-value")).to_have_attribute("aria-pressed", "false")
    _finish(first)
    pending.remove(first)
    expect(_button(page, "primary")).to_have_attribute("aria-pressed", "true")
    expect(_button(page, "secondary")).to_have_attribute("aria-pressed", "true")
    expect(_button(page, "disabled")).to_be_disabled()
