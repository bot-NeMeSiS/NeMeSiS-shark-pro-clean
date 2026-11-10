"""Owned Chromium checks of real Home Jinja, cards, CSS and motion script.

All browser requests are fulfilled locally or aborted. No Flask HTTP server,
provider, API, account mutation or production clock is exercised here. Fixed
NOW belongs to the existing pure canonical fixture builder; only page.clock
and an explicitly simulated browser visibility signal control presentation.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from test_app_navigation_browser import browser
from test_home_canonical_consistency import NOW, data_for, row


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://home.invalid"
ROUTES = ("/", "/app")
WIDTHS = (1440, 390)
FEATURED = "[data-home-featured]"
SLIDE = "[data-home-featured-slide]"
CARD = "[data-v934-match-id]"
STORAGE_KEYS = {
    "nemesis.motion.paused.v1", "nemesis.motion.marine.v1",
    "nemesis.shark.discovery.v1", "nemesis.motion.storage-check",
}
OWNED_LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
    '<rect width="64" height="64" fill="#17304b"/>'
    '<text x="12" y="38" fill="white">QA</text></svg>'
)


def _rows(slides):
    if slides == 0:
        return []
    if slides == 1:
        return [row("owned-live-one", "LIVE")]
    return [row("owned-live-" + str(index), "LIVE") for index in range(2)]


def _markup(a, path, slides, *, rows=None, language='es'):
    from flask import render_template

    rows = _rows(slides) if rows is None else rows
    data = data_for(rows)
    before = deepcopy(data)
    user = None if path == "/" else {
        "id": "owned-home-browser", "name": "María", "role": "FREE",
        "membership": "FREE",
    }
    with a.app.test_request_context(
        path, base_url=ORIGIN, headers={"Accept-Language": language},
    ):
        markup = render_template(
            "home.html" if path == "/" else "client_app_center.html",
            data=data, current_user=user,
            greeting={"label": "Buenos días", "name": "María"},
            evidence_origin="SIMULATED_QA",
        )
    assert data == before
    # Keep the actual script under test, icon/localization renderers and JSON.
    # Unrelated PWA, telemetry and realtime polling are outside this UI test.
    keep = ("platform-motion.js", "ui-localization.js", "v930-icons.js")
    markup = re.sub(
        r"<script\b([^>]*)>.*?</script>",
        lambda match: match.group(0) if (
            "application/json" in match[1]
            or any(name in match[1] for name in keep)
        ) else "",
        markup, flags=re.S | re.I,
    )
    return markup, {item["id"] for item in rows}


@contextmanager
def _screen(browser, a, path, width, slides=2, *, javascript=True, rows=None, language='es'):
    markup, owned_ids = _markup(a, path, slides, rows=rows, language=language)
    context = browser.new_context(
        viewport={"width": width, "height": 1000},
        java_script_enabled=javascript, reduced_motion="no-preference",
        locale={"es": "es-ES", "en": "en-GB", "fr": "fr-FR"}[language], timezone_id="Europe/Madrid", service_workers="block",
    )
    # Observe browser storage calls, without replacing any application function.
    # Existing optional decoration may use its established keys; carousel state
    # must not introduce another persistent or transient Storage key.
    context.add_init_script("""(() => {
      window.__ownedHomeStorage = [];
      ['getItem', 'setItem', 'removeItem'].forEach(name => {
        const original = Storage.prototype[name];
        Storage.prototype[name] = function (key, ...args) {
          window.__ownedHomeStorage.push({method:name, key:String(key)});
          return original.call(this, key, ...args);
        };
      });
    })();""")
    page = context.new_page()
    trace = {"calls": [], "external": [], "api": [], "errors": [], "console": []}
    page.on("pageerror", lambda error: trace["errors"].append(str(error)))
    page.on("console", lambda message: trace["console"].append(message.text)
            if message.type == "error" else None)
    if javascript:
        # Pause before loading application JS, so every later timer boundary is
        # explicit. This never patches Python/App datetime or fixture clocks.
        page.clock.install(time=NOW)
        page.clock.pause_at(NOW + timedelta(seconds=1))

    def serve(route):
        request = route.request
        url = urlsplit(request.url)
        trace["calls"].append((request.method, request.url))
        if url.netloc != "home.invalid":
            trace["external"].append(request.url)
            route.abort()
            return
        if url.path.startswith("/api/"):
            trace["api"].append(request.url)
            route.abort()
            return
        if url.path == path:
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=markup)
            return
        asset = (ROOT / url.path.lstrip("/")).resolve()
        if (url.path.startswith("/static/") and asset.is_relative_to(ROOT / "static")
                and asset.is_file()):
            route.fulfill(
                status=200,
                content_type=mimetypes.guess_type(str(asset))[0] or "application/octet-stream",
                body=asset.read_bytes(),
            )
            return
        if url.path.startswith("/asset/"):
            route.fulfill(status=200, content_type="image/svg+xml", body=OWNED_LOGO)
            return
        if url.path.endswith(".webmanifest"):
            route.fulfill(status=200, content_type="application/manifest+json",
                          body=json.dumps({"name": "Owned Home", "start_url": "/"}))
            return
        # Native fixture navigation ends at an owned destination, never a server.
        route.fulfill(status=200, content_type="text/html; charset=utf-8",
                      body="<!doctype html><title>Owned destination</title><p>SIMULATED_QA</p>")

    context.route("**/*", serve)
    try:
        response = page.goto(ORIGIN + path, wait_until="networkidle")
        assert response.status == 200
        if javascript and slides > 1:
            page.locator(FEATURED).wait_for(state="visible")
            assert page.locator(FEATURED).get_attribute("data-home-featured-ready") == "true"
        yield page, trace, owned_ids
    finally:
        context.close()


def _visible_id(page):
    visible = page.locator(FEATURED + " " + SLIDE + ":visible")
    assert visible.count() == 1
    return visible.locator(CARD).get_attribute("data-v934-match-id")


@pytest.mark.parametrize('path', ROUTES)
@pytest.mark.parametrize('width', [320, 390, 1440])
def test_mixed_seven_visual_receipt_keeps_each_phase_truth(browser, app_module, path, width, tmp_path):
    fixtures = [row('visual-live-' + str(i), 'LIVE') for i in range(3)]
    fixtures += [row('visual-today-' + str(i)) for i in range(4)]
    with _screen(browser, app_module, path, width, rows=fixtures) as screen:
        page, trace, _ = screen
        root = page.locator(FEATURED)
        assert root.get_attribute('aria-label') == 'Grandes partidos de hoy'
        assert root.locator(SLIDE).count() == 7
        root.locator('[data-home-featured-toggle]').click()
        root.screenshot(path=str(tmp_path / ('mixed-' + str(width) + '-live.png')))
        while not _visible_id(page).startswith('visual-today-'):
            root.locator('[data-home-featured-next]').click()
        page.clock.run_for(250)
        visible = root.locator(SLIDE + ':visible')
        assert visible.locator('[data-v934-score]').inner_text() == 'VS'
        assert visible.locator('[data-match-kickoff-clock]').count() == 1
        zone = visible.locator('[data-match-kickoff-zone]')
        assert zone.inner_text() == 'Madrid'
        assert zone.evaluate('node => getComputedStyle(node).whiteSpace') == 'nowrap'
        assert zone.evaluate('node => node.scrollWidth <= node.clientWidth + 1')
        root.screenshot(path=str(tmp_path / ('mixed-' + str(width) + '-today.png')))
        _assert_clean(page, trace)


@pytest.mark.parametrize('path', ROUTES)
@pytest.mark.parametrize('width', [320, 390, 768, 1440])
@pytest.mark.parametrize('count', [7, 8, 12])
def test_mixed_today_carousel_preserves_bounded_unique_fixtures_and_native_links(
    browser, app_module, path, width, count,
):
    fixtures = [row('mixed-live-' + str(i), 'LIVE') for i in range(3)]
    fixtures += [row('mixed-today-' + str(i)) for i in range(count - 3)]
    expected_ids = {item['id'] for item in fixtures}
    with _screen(browser, app_module, path, width, rows=fixtures) as screen:
        page, trace, _ = screen
        root = page.locator(FEATURED)
        ids = page.locator(CARD).evaluate_all(
            'nodes => nodes.map(node => node.dataset.v934MatchId)')
        assert len(ids) == len(set(ids)) == count
        assert set(ids) == expected_ids
        featured_ids = root.locator(CARD).evaluate_all(
            'nodes => nodes.map(node => node.dataset.v934MatchId)')
        assert len(featured_ids) == min(8, count)
        assert any(identity.startswith('mixed-live-') for identity in featured_ids)
        assert any(identity.startswith('mixed-today-') for identity in featured_ids)
        root.locator('[data-home-featured-toggle]').click()
        assert root.locator('[data-home-featured-toggle]').get_attribute('aria-pressed') == 'true'
        seen = []
        for index in range(len(featured_ids)):
            identity = _visible_id(page)
            seen.append(identity)
            hidden = root.locator(SLIDE + '[hidden]')
            assert hidden.count() == len(featured_ids) - 1
            assert hidden.evaluate_all('nodes => nodes.every(node => node.inert)')
            link = root.locator(SLIDE + ':visible a[href="/match/' + identity + '"]')
            assert link.count() == 1 and link.is_visible()
            page.clock.run_for(9000)
            assert _visible_id(page) == identity
            next_button = root.locator('[data-home-featured-next]')
            next_button.focus()
            page.keyboard.press('Enter')
        assert seen == featured_ids
        assert _visible_id(page) == featured_ids[0]
        _assert_clean(page, trace)
        target = featured_ids[0]
        root.locator(SLIDE + ':visible a[href="/match/' + target + '"]').click()
        page.wait_for_url(ORIGIN + '/match/' + target)
        _assert_clean(page, trace)


def _assert_clean(page, trace, *, javascript=True):
    assert not trace["external"], trace
    assert not trace["api"], trace
    assert not trace["errors"], trace
    assert not trace["console"], trace
    assert all(method == "GET" and urlsplit(url).netloc == "home.invalid"
               for method, url in trace["calls"])
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    if javascript:
        calls = page.evaluate("window.__ownedHomeStorage || []")
        assert all(call["key"] in STORAGE_KEYS for call in calls), calls


def _arm_auto_by_native_mouse_exit(page):
    root = page.locator(FEATURED)
    root.scroll_into_view_if_needed()
    page.clock.run_for(100)  # Let the actual IntersectionObserver see this root.
    page.evaluate("document.activeElement.blur()")
    box = root.bounding_box()
    assert box
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.move(1, 1)
    assert root.locator("[data-home-featured-toggle]").get_attribute("aria-pressed") == "false"


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("slides", [0, 1, 2])
@pytest.mark.parametrize("javascript", [False, True])
def test_actual_ssr_keeps_empty_single_and_two_card_controls(
    browser, app_module, path, width, slides, javascript,
):
    with _screen(browser, app_module, path, width, slides, javascript=javascript) as screen:
        page, trace, owned_ids = screen
        cards = page.locator(CARD)
        ids = cards.evaluate_all("nodes => nodes.map(node => node.dataset.v934MatchId)")
        assert len(ids) == len(set(ids)) == slides
        assert set(ids).issubset(owned_ids)
        assert "cached-expired" not in ids
        assert page.locator(FEATURED).count() == int(bool(slides))
        assert page.locator(FEATURED + " " + SLIDE).count() == slides
        assert page.locator("[data-home-featured-controls]:visible").count() == int(
            javascript and slides == 2)
        # Preserve surrounding FREE/+18 copy; this is not an age-gate assertion.
        assert page.locator("body").get_attribute("data-ns-plan") == "FREE"
        assert "+18" in page.locator(".v933-legal-footer").inner_text()
        if slides:
            assert page.locator(FEATURED + " .v933-legal-footer").count() == 0
            first = _visible_id(page)
            if slides == 1:
                assert first == "owned-live-one"
            hidden = page.locator(FEATURED + " " + SLIDE + "[hidden]")
            assert hidden.count() == slides - 1
            assert page.locator(FEATURED + " [data-v934-pick-id]").count() == 0
            if javascript and slides == 2:
                assert hidden.evaluate_all("nodes => nodes.every(node => node.inert)")
            _assert_clean(page, trace, javascript=javascript)
            if not javascript:
                # First card and the fallback for the hidden second fixture are
                # both native links; JavaScript is unnecessary for navigation.
                if slides == 2:
                    second = hidden.locator(CARD).get_attribute("data-v934-match-id")
                    link = page.locator(FEATURED + ' noscript a[href="/match/' + second + '"]')
                    assert link.is_visible()
                    target = second
                else:
                    target = first
                    link = page.locator(FEATURED + ' a[href="/match/' + target + '"]').last
                link.focus()
                page.keyboard.press("Enter")
                page.wait_for_url(ORIGIN + "/match/" + target)
        _assert_clean(page, trace, javascript=javascript)


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("width", WIDTHS)
def test_nine_second_rotation_then_manual_keyboard_keeps_the_exact_fixture_link(
    browser, app_module, path, width,
):
    with _screen(browser, app_module, path, width) as screen:
        page, trace, _ = screen
        root = page.locator(FEATURED)
        ids = root.locator(CARD).evaluate_all("nodes => nodes.map(node => node.dataset.v934MatchId)")
        page.evaluate("window.__ownedSlides = Array.from(document.querySelectorAll('[data-home-featured-slide]'))")
        _arm_auto_by_native_mouse_exit(page)
        assert _visible_id(page) == ids[0]
        page.clock.run_for(8999)
        assert _visible_id(page) == ids[0]
        page.clock.run_for(1)
        assert _visible_id(page) == ids[1]
        assert root.locator("[data-home-featured-status]").inner_text() == ""
        toggle = root.locator("[data-home-featured-toggle]")
        toggle.click()
        assert toggle.get_attribute("aria-pressed") == "true"
        page.clock.run_for(18000)
        assert _visible_id(page) == ids[1]
        root.locator("[data-home-featured-next]").click()
        assert _visible_id(page) == ids[0]
        previous = root.locator("[data-home-featured-prev]")
        previous.focus()
        page.keyboard.press("Enter")
        assert _visible_id(page) == ids[1]
        assert previous.evaluate("node => node === document.activeElement")
        assert root.locator("[data-home-featured-status]").inner_text() == "Partido 2 de 2"
        page.clock.run_for(18000)
        assert _visible_id(page) == ids[1]
        assert page.evaluate("window.__ownedSlides.every((node, index) => node === document.querySelectorAll('[data-home-featured-slide]')[index])")
        # From the first control, native reverse Tab reaches the visible card's
        # final link, never an action in the hidden/inert card.
        previous.focus()
        page.keyboard.press("Shift+Tab")
        focused = page.locator(":focus")
        assert focused.get_attribute("href") == "/match/" + ids[1]
        assert focused.evaluate("node => !node.closest('[hidden],[inert]')")
        _assert_clean(page, trace)
        page.keyboard.press("Enter")
        page.wait_for_url(ORIGIN + "/match/" + ids[1])
        _assert_clean(page, trace)


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("width", WIDTHS)
def test_native_pointer_gesture_cannot_change_target_at_the_timer_boundary(
    browser, app_module, path, width,
):
    with _screen(browser, app_module, path, width) as screen:
        page, trace, _ = screen
        _arm_auto_by_native_mouse_exit(page)
        identity = _visible_id(page)
        page.clock.run_for(8990)
        link = page.locator(FEATURED + " " + SLIDE + ':visible a[href="/match/' + identity + '"]').last
        box = link.bounding_box()
        assert box
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.clock.run_for(30)
        assert _visible_id(page) == identity
        assert link.get_attribute("href") == "/match/" + identity
        _assert_clean(page, trace)
        page.mouse.up()
        page.wait_for_url(ORIGIN + "/match/" + identity)
        _assert_clean(page, trace)


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("width", WIDTHS)
def test_browser_visibility_and_reduced_motion_pause_without_removing_manual_access(
    browser, app_module, path, width,
):
    with _screen(browser, app_module, path, width) as screen:
        page, trace, _ = screen
        _arm_auto_by_native_mouse_exit(page)
        first = _visible_id(page)
        # Deterministic, owned-document visibility event, not a production
        # property or clock patch. Restoring visibility must not resume a latch.
        page.evaluate("""() => {
          Object.defineProperty(document, 'hidden', {configurable:true, get:() => true});
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.clock.run_for(27000)
        assert _visible_id(page) == first
        page.evaluate("""() => {
          delete document.hidden;
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.clock.run_for(18000)
        assert _visible_id(page) == first
        toggle = page.locator("[data-home-featured-toggle]")
        assert toggle.get_attribute("aria-pressed") == "true"
        page.emulate_media(reduced_motion="reduce")
        expect(toggle).to_be_disabled()
        page.locator("[data-home-featured-next]").click()
        second = _visible_id(page)
        assert second != first
        assert toggle.get_attribute("aria-pressed") == "true"
        page.clock.run_for(27000)
        assert _visible_id(page) == second
        page.emulate_media(reduced_motion="no-preference")
        expect(toggle).to_be_enabled()
        page.clock.run_for(18000)
        assert _visible_id(page) == second
        page.locator("[data-home-featured-prev]").click()
        assert _visible_id(page) == first
        assert page.locator(FEATURED + ' ' + SLIDE + ':visible a[href="/match/' + first + '"]').last.is_visible()
        _assert_clean(page, trace)


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("width", WIDTHS)
def test_interrupted_dom_pointer_can_resume_only_after_visible_explicit_play(
    browser, app_module, path, width,
):
    with _screen(browser, app_module, path, width) as screen:
        page, trace, _ = screen
        _arm_auto_by_native_mouse_exit(page)
        root = page.locator(FEATURED)
        first = _visible_id(page)
        identities = root.locator(CARD).evaluate_all(
            "nodes => nodes.map(node => node.dataset.v934MatchId)")
        hrefs = root.locator('a[href^="/match/"]').evaluate_all(
            "nodes => nodes.map(node => node.getAttribute('href'))")
        toggle = root.locator("[data-home-featured-toggle]")
        # Explicit DOM simulation of an interrupted gesture: no pointerup or
        # pointercancel is delivered. This is not an OS/tab-switch gesture test.
        toggle.dispatch_event("pointerdown", {
            "bubbles": True, "pointerId": 73, "pointerType": "mouse",
            "isPrimary": True, "button": 0, "buttons": 1,
        })
        # Reuse the owned-document visibility signal of the existing check;
        # neither App clocks nor production visibility functions are replaced.
        page.evaluate("""() => {
          Object.defineProperty(document, 'hidden', {configurable:true, get:() => true});
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        assert toggle.get_attribute("aria-pressed") == "true"
        page.clock.run_for(18000)
        assert _visible_id(page) == first
        page.evaluate("""() => {
          delete document.hidden;
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        page.clock.run_for(18000)
        assert _visible_id(page) == first
        assert toggle.get_attribute("aria-pressed") == "true"
        toggle.focus()
        page.keyboard.press("Enter")
        assert toggle.get_attribute("aria-pressed") == "false"
        status = root.locator("[data-home-featured-status]")
        play_announcement = status.inner_text()
        assert play_announcement.strip()
        # Native focus exit and mouse enter/leave establish a fresh full delay,
        # without manufacturing a pointerup to clear the interrupted gesture.
        _arm_auto_by_native_mouse_exit(page)
        page.clock.run_for(8999)
        assert _visible_id(page) == first
        page.clock.run_for(1)
        second = _visible_id(page)
        assert second != first and second in identities
        assert root.locator(CARD).evaluate_all(
            "nodes => nodes.map(node => node.dataset.v934MatchId)") == identities
        assert root.locator('a[href^="/match/"]').evaluate_all(
            "nodes => nodes.map(node => node.getAttribute('href'))") == hrefs
        link = root.locator(SLIDE + ':visible a[href="/match/' + second + '"]').last
        assert link.is_visible() and link.get_attribute("href") == "/match/" + second
        assert status.get_attribute("aria-live") == "polite"
        assert status.inner_text() == play_announcement
        _assert_clean(page, trace)


def _rich_featured_rows():
    fixtures = [row('owned-short', 'LIVE'), row('owned-long', 'LIVE')]
    fixtures[0].update(home_team='QA Local', away_team='QA Visitante')
    fixtures[1].update(
        home_team='Club Deportivo de la Ciudad de Nombre Muy Largo para la Prueba',
        away_team='Unión Deportiva Visitante de Nombre Completo para la Prueba')
    for fixture in fixtures:
        fixture.update(home_logo='', away_logo='', home_score=0, away_score=0,
                       client_live_minute=None)
    return fixtures


@pytest.mark.parametrize('path', ROUTES)
@pytest.mark.parametrize('width', [360, 390, 768, 1440])
def test_professional_feature_keeps_controls_and_height_stable_with_long_real_fields(
    browser, app_module, path, width,
):
    fixtures = _rich_featured_rows()
    expected_names = {item['id']: [item['home_team'], item['away_team']] for item in fixtures}
    with _screen(browser, app_module, path, width, rows=fixtures) as screen:
        page, trace, _ = screen
        root = page.locator(FEATURED)
        root.scroll_into_view_if_needed()
        buttons = root.locator('[data-home-featured-controls] button')
        assert buttons.count() == 3
        for button in buttons.all():
            box = button.bounding_box()
            assert box and box['width'] >= 44 and box['height'] >= 44
            assert box['x'] >= -1 and box['x'] + box['width'] <= width + 1

        def assert_visible_fixture(identity):
            visible = root.locator(SLIDE + ':visible')
            assert visible.count() == 1
            expect(visible.locator(CARD)).to_have_attribute('data-v934-match-id', identity)
            names = visible.locator('.v933-match-teams strong')
            assert names.all_text_contents() == expected_names[identity]
            for name in names.all():
                assert name.evaluate('node => node.scrollHeight <= node.clientHeight + 1')
                assert name.evaluate('node => getComputedStyle(node).webkitLineClamp') in ('none', 'unset')
            assert visible.locator('[data-v934-score]').inner_text() == '0 - 0'
            assert visible.locator('[data-v934-minute]:visible').count() == 0
            assert visible.locator('a[href="/match/' + identity + '"]').count() == 1
            assert root.locator(SLIDE + '[hidden]').evaluate_all('nodes => nodes.every(node => node.inert)')

        def geometry():
            # Read one coordinate frame atomically. A native click can scroll
            # the page; that must not be mistaken for motion inside the feature.
            # Page/scroll coordinates are diagnostic only, not pass conditions.
            return root.evaluate("""node => {
              const feature = node.getBoundingClientRect();
              const control = node.querySelector('[data-home-featured-controls] button').getBoundingClientRect();
              return {
                height: feature.height,
                control_offset_y: control.y - feature.y,
                control_page_y: control.y + window.scrollY,
                root_page_y: feature.y + window.scrollY,
                scroll_y: window.scrollY,
              };
            }""")

        # Equal live kickoff times use the canonical ID tie-breaker, not the
        # input list's order: owned-long precedes owned-short.
        assert root.locator(CARD).evaluate_all(
            "nodes => nodes.map(node => node.dataset.v934MatchId)") == ['owned-long', 'owned-short']
        assert_visible_fixture('owned-long')
        counter = root.locator('[data-home-featured-counter]')
        expect(counter).to_be_visible()
        assert counter.inner_text() == '1 / 2'
        # The max of the actual slide heights reserves only this pair's space.
        page.wait_for_function("""() => {
          const track = document.querySelector('.home-match-featured-slides');
          return parseFloat(track.style.getPropertyValue('--home-featured-min-height')) > 0;
        }""")
        before = geometry()
        assert before['height'] > 0
        root.locator('[data-home-featured-next]').click()
        during = geometry()
        page.clock.run_for(250)
        after = geometry()
        assert abs(before['height'] - during['height']) <= 1, (before, during)
        assert abs(before['control_offset_y'] - during['control_offset_y']) <= 1, (before, during)
        assert abs(before['height'] - after['height']) <= 1, (before, after)
        assert abs(before['control_offset_y'] - after['control_offset_y']) <= 1, (before, after)
        assert_visible_fixture('owned-short')
        expect(counter).to_be_visible()
        assert counter.inner_text() == '2 / 2'
        root.locator('[data-home-featured-prev]').click()
        page.clock.run_for(250)
        restored = geometry()
        assert abs(restored['height'] - before['height']) <= 1, (before, restored)
        assert abs(restored['control_offset_y'] - before['control_offset_y']) <= 1, (before, restored)
        assert_visible_fixture('owned-long')
        assert counter.inner_text() == '1 / 2'
        _assert_clean(page, trace)


@pytest.mark.parametrize('path', ROUTES)
@pytest.mark.parametrize('language,labels', [
    ('es', ('Anterior', 'Siguiente', 'Pausar', 'Reanudar', 'Avance automático pausado', 'Avance automático activado')),
    ('en', ('Previous', 'Next', 'Pause', 'Resume', 'Automatic advance paused', 'Automatic advance enabled')),
    ('fr', ('Précédent', 'Suivant', 'Pause', 'Reprendre', 'Défilement automatique en pause', 'Défilement automatique activé')),
])
def test_featured_icon_controls_keep_nodes_and_explicit_localized_accessible_state(
    browser, app_module, path, language, labels,
):
    with _screen(browser, app_module, path, 390, language=language) as screen:
        page, trace, _ = screen
        root = page.locator(FEATURED)
        previous = root.locator('[data-home-featured-prev]')
        next_button = root.locator('[data-home-featured-next]')
        toggle = root.locator('[data-home-featured-toggle]')
        assert page.locator('html').get_attribute('lang') == language
        expect(previous).to_have_attribute('aria-label', labels[0])
        expect(next_button).to_have_attribute('aria-label', labels[1])
        expect(toggle).to_have_attribute('aria-label', labels[2])
        page.evaluate("""() => {
          const toggle = document.querySelector('[data-home-featured-toggle]');
          window.__ownedFeaturedIconNodes = Array.from(toggle.querySelectorAll('svg,g,span'));
        }""")
        page.keyboard.press('Tab')
        previous.focus()
        assert previous.evaluate("node => node.matches(':focus-visible')")
        assert previous.evaluate("node => getComputedStyle(node, '::after').visibility") == 'visible'
        assert previous.evaluate("node => getComputedStyle(node).outlineStyle") != 'none'
        previous.evaluate('node => node.blur()')
        previous.hover()
        assert previous.evaluate("node => getComputedStyle(node, '::after').visibility") == 'visible'
        page.mouse.move(1, 1)
        assert previous.evaluate("node => getComputedStyle(node, '::after').visibility") == 'hidden'
        # Arrow focus latches pause. Explicit Play then Pause exercises both
        # existing icon groups without rebuilding the button or its children.
        expect(toggle).to_have_attribute('aria-pressed', 'true')
        expect(toggle).to_have_attribute('aria-label', labels[3])
        toggle.click()
        expect(toggle).to_have_attribute('aria-label', labels[2])
        assert root.locator('[data-home-featured-status]').inner_text() == labels[5]
        toggle.click()
        expect(toggle).to_have_attribute('aria-label', labels[3])
        assert root.locator('[data-home-featured-status]').inner_text() == labels[4]
        assert toggle.get_attribute('data-home-featured-tooltip') == labels[3]
        assert page.evaluate("""() => {
          const nodes = document.querySelector('[data-home-featured-toggle]').querySelectorAll('svg,g,span');
          return window.__ownedFeaturedIconNodes.every((node, index) => node === nodes[index]);
        }""")
        _assert_clean(page, trace)


@pytest.mark.parametrize('path', ROUTES)
def test_actual_entry_is_finite_noninitial_and_manual_changes_honor_all_motion_permissions(
    browser, app_module, path,
):
    with _screen(browser, app_module, path, 390) as screen:
        page, trace, _ = screen
        root = page.locator(FEATURED)
        first = _visible_id(page)
        assert root.locator(SLIDE + ':visible').evaluate('node => node.getAnimations().length') == 0
        root.locator('[data-home-featured-next]').click()
        visible = root.locator(SLIDE + ':visible')
        assert _visible_id(page) != first
        animations = visible.evaluate("""node => node.getAnimations().map(animation => ({
          name: animation.animationName,
          duration: animation.effect.getTiming().duration,
          frames: animation.effect.getKeyframes().map(frame => ({opacity:frame.opacity,transform:frame.transform}))
        }))""")
        assert len(animations) == 1 and animations[0]['name'] == 'home-featured-enter'
        assert animations[0]['duration'] == 200
        assert animations[0]['frames'][0]['opacity'] == '0'
        assert animations[0]['frames'][-1]['opacity'] == '1'
        page.clock.run_for(100)
        y = visible.evaluate("node => new DOMMatrix(getComputedStyle(node).transform).m42")
        assert 0 <= y <= 4
        page.emulate_media(reduced_motion='reduce')
        expect(root.locator('[data-home-featured-toggle]')).to_be_disabled()
        root.locator('[data-home-featured-next]').click()
        assert _visible_id(page) == first
        assert root.locator(SLIDE + ':visible').evaluate('node => node.getAnimations().length') == 0
        assert root.locator(SLIDE + ':visible').get_attribute('data-home-featured-enter') == 'false'
        page.emulate_media(reduced_motion='no-preference')
        global_toggle = page.locator('[data-motion-preferences] [data-motion-toggle]')
        expect(global_toggle).to_be_enabled()
        preferences = page.locator('[data-motion-preferences]')
        if preferences.get_attribute('open') is None:
            preferences.locator('summary').click()
        expect(global_toggle).to_be_visible()
        global_toggle.click()
        expect(global_toggle).to_have_attribute('aria-pressed', 'true')
        root.locator('[data-home-featured-next]').click()
        assert _visible_id(page) != first
        assert root.locator(SLIDE + ':visible').evaluate('node => node.getAnimations().length') == 0
        global_toggle.click()
        expect(global_toggle).to_have_attribute('aria-pressed', 'false')
        unchanged = _visible_id(page)
        page.mouse.move(1, 1)
        page.evaluate('document.activeElement.blur()')
        page.clock.run_for(18000)
        assert _visible_id(page) == unchanged
        _assert_clean(page, trace)


@pytest.mark.parametrize('path', ROUTES)
def test_second_nine_second_cycle_does_not_gain_another_timer(browser, app_module, path):
    with _screen(browser, app_module, path, 390) as screen:
        page, trace, _ = screen
        _arm_auto_by_native_mouse_exit(page)
        ids = page.locator(FEATURED + ' ' + CARD).evaluate_all(
            'nodes => nodes.map(node => node.dataset.v934MatchId)')
        for current, following in ((ids[0], ids[1]), (ids[1], ids[0])):
            page.clock.run_for(8999)
            assert _visible_id(page) == current
            page.clock.run_for(1)
            assert _visible_id(page) == following
        assert page.locator('[data-home-featured-status]').inner_text() == ''
        _assert_clean(page, trace)


@pytest.mark.parametrize('slides', [1, 2])
def test_featured_badge_reflects_same_card_favorite_control_including_static_feature(
    browser, app_module, slides,
):
    # Owned DOM-boundary test, not an API/authentication test: the unchanged
    # real handler sets this attribute only after its accepted server response.
    with _screen(browser, app_module, '/app', 390, slides=slides) as screen:
        page, trace, _ = screen
        card = page.locator(FEATURED + ' ' + SLIDE + ':visible')
        button = card.locator('.fav-star[data-kind="match"]')
        badge = card.locator('[data-home-featured-favorite]')
        identity = card.locator(CARD).get_attribute('data-v934-match-id')
        assert button.get_attribute('data-value') == identity
        expect(badge).to_be_hidden()
        button.evaluate("node => node.setAttribute('aria-pressed', 'true')")
        expect(badge).to_be_visible()
        button.evaluate("node => node.setAttribute('aria-pressed', 'false')")
        expect(badge).to_be_hidden()
        assert button.get_attribute('data-value') == identity
        assert card.locator('a[href="/match/' + identity + '"]').count() == 1
        _assert_clean(page, trace)
