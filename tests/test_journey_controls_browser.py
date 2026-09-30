"""Real Flask templates + complete stylesheet cascade, offline synthetic sessions.

No HTTP server, remote providers, Telegram delivery or production database is used.
The browser only exercises native form controls; it never submits a request.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def _inline_styles(html: str) -> str:
    """Keep every rendered stylesheet, without fetching anything over the network."""
    def replace_link(match):
        tag = match.group(0)
        href = re.search(r'\bhref=["\']([^"\']+)["\']', tag)
        if not href or not re.search(r'\brel=["\']stylesheet["\']', tag):
            return ""
        path = unquote(urlsplit(href.group(1)).path)
        assert path.startswith("/static/"), path
        source = (ROOT / path.lstrip("/")).resolve()
        assert source.is_relative_to((ROOT / "static").resolve())
        return "<style>" + source.read_text(encoding="utf-8") + "</style>"

    # App JavaScript, embedded frames and remote assets are outside this CSS gate.
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", html, flags=re.S | re.I)
    return re.sub(r"<link\b[^>]*>", replace_link, html, flags=re.I)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        options = {"headless": True}
        if os.getenv("NEMESIS_QA_CHROMIUM"):
            options["executable_path"] = os.environ["NEMESIS_QA_CHROMIUM"]
        instance = pw.chromium.launch(**options)
        yield instance
        instance.close()


@pytest.fixture
def page_html(app_module, monkeypatch):
    # No network request from Flask is allowed to turn a layout test into sync.
    import requests
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Layout regression must not call a remote provider")
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    from tools.run_v929_click_navigation_qa import _signed_sessions
    sessions = _signed_sessions(app_module.app)

    def render(path, plan="FREE", admin=False):
        client = app_module.app.test_client()
        role = "admin" if admin else "client_" + plan.lower()
        client.set_cookie(sessions["cookie_name"], sessions[role])
        response = client.get(path)
        assert response.status_code == 200
        return _inline_styles(response.get_data(as_text=True))
    return render


def _page(browser, html, width, javascript=True):
    page = browser.new_page(viewport={"width": width, "height": 844},
                            java_script_enabled=javascript, locale="es-ES")
    page.set_default_timeout(4000)
    page.route("**/*", lambda route: route.abort())
    page.set_content(html, wait_until="load")
    # The inherited shell has a 360 ms CSS entrance transition. Let it finish
    # before testing native actionability, including with scripts disabled.
    page.wait_for_timeout(450)
    return page


def _capture(page, name):
    folder = os.getenv("NEMESIS_JOURNEY_EVIDENCE_DIR")
    if folder:
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(target / (name + ".png")), full_page=True)


@pytest.mark.parametrize("width", [320, 390, 768, 1440])
@pytest.mark.parametrize("plan", ["FREE", "PRO", "ELITE"])
@pytest.mark.parametrize("javascript", [False, True])
def test_telegram_preferences_remain_operable(browser, page_html, width, plan, javascript):
    page = _page(browser, page_html("/telegram", plan), width, javascript)
    try:
        form = page.locator("[data-telegram-preferences-form]")
        assert form.count() == 1
        assert form.get_attribute("action") == "/telegram/preferencias"
        assert form.locator('input[name="csrf_token"]').get_attribute("value")
        submit = form.get_by_role("button", name="Guardar preferencias")
        assert submit.is_visible(), "Mobile CSS must not hide the preferences submit action"
        submit.scroll_into_view_if_needed()
        submit.click(trial=True)  # Actionability only; never submit or write data.
        assert submit.bounding_box()["height"] >= 44

        checks = form.locator('input[type="checkbox"]')
        assert checks.count() >= 2
        for checkbox in checks.all():
            rect = checkbox.bounding_box()
            assert 16 <= rect["width"] <= 24, rect
            assert 16 <= rect["height"] <= 24, rect
            label = checkbox.locator("xpath=ancestor::label")
            assert label.bounding_box()["height"] >= 44
            assert label.inner_text().strip()

        pause = form.locator('input[name="pause_all"]')
        initial = pause.is_checked()
        pause.focus()
        page.keyboard.press("Space")
        assert pause.is_checked() != initial
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        _capture(page, f"telegram-{plan}-{width}-js{int(javascript)}")
    finally:
        page.close()


# Each whole word should occupy only one line; break BETWEEN words, not inside.
_WORD_RECTS = r"""node => {
  const errors = [];
  const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
  for (let text = walker.nextNode(); text; text = walker.nextNode()) {
    for (const word of text.textContent.matchAll(/[\p{L}\p{N}]+/gu)) {
      const range = document.createRange();
      range.setStart(text, word.index); range.setEnd(text, word.index + word[0].length);
      const lines = new Set([...range.getClientRects()].filter(r => r.width > 0).map(r => Math.round(r.top)));
      if (lines.size > 1) errors.push(word[0]);
    }
  }
  return errors;
}"""


@pytest.mark.parametrize("width", [320, 390, 768, 1440])
def test_section_titles_and_actions_keep_whole_words(browser, page_html, width):
    page = _page(browser, page_html("/app"), width)
    try:
        header = page.locator(".ns16-featured-pick > .v933-section-header")
        assert header.count() == 1
        for element in [header.locator("h2"), header.locator("a")]:
            assert element.is_visible()
            assert element.evaluate(_WORD_RECTS) == []
        action = header.get_by_role("link", name="Combinadas")
        assert action.get_attribute("href") == "/combinadas"
        action.scroll_into_view_if_needed()
        action.click(trial=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        _capture(page, f"app-FREE-{width}")
    finally:
        page.close()


@pytest.mark.parametrize("width", [320, 390, 768, 1440])
def test_admin_preview_keeps_section_actions_readable(browser, page_html, width):
    page = _page(browser, page_html("/admin/client-preview/frame?page=telegram&plan=FREE", admin=True), width)
    try:
        assert page.locator("main.preview-shell").count() == 1
        headers = page.locator(".v933-section-header:visible")
        assert headers.count() > 0
        for header in headers.all():
            for element in header.locator("h2, a").all():
                assert element.evaluate(_WORD_RECTS) == []
        _capture(page, f"admin-preview-{width}")
    finally:
        page.close()
