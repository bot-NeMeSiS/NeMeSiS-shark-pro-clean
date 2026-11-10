"""Bounded presentation QA on the actual, original LOCAL SAFE App.

Run with tools/check_local_candidate.py. The existing motion suite owns the
pulse-count, modal/history and reduced-motion contracts. A separate test below
checks owned-input focus and records native visibility only when observed.
This matrix covers the shared appearance on five widths, not production or
all application screens. It never substitutes a template, route or identity.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import pytest
from playwright.sync_api import TimeoutError as BrowserTimeoutError, sync_playwright

from browser_surface_readability import assert_surface_legible
# Imported fixtures retain the existing password + CSRF authentication flow.
from test_v1000_actual_admin_navigation import actual_admin, actual_http
from test_v1000_match_header_browser import fixture_server
from test_v1000_home_motion_browser import _browser, _preferences, _question_rows, _wait_light


ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (320, 360, 390, 768, 1440)
ASSETS = ('static/platform-motion.js', 'static/v1000-client-refinement.css')


def _collect_assets(page):
    responses = {}
    def observed(response):
        path = urlsplit(response.url).path.lstrip('/')
        if path in ASSETS:
            responses[path] = response
    page.on('response', observed)
    return responses


def _served_asset_digests(responses):
    result = {}
    for path in ASSETS:
        assert path in responses, ('Shared asset was not observed on actual HTTP', path)
        response = responses[path]
        assert response.status == 200, (path, response.status)
        digest = hashlib.sha256(response.body()).hexdigest()
        assert digest == hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path
        result[path] = digest
    return result


_FOCUS_GEOMETRY = """el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    const center = {x:r.x + r.width / 2, y:r.y + r.height / 2};
    const hit = document.elementFromPoint(center.x, center.y);
    const link = hit && hit.closest('a[href]');
    let hrefPath = null;
    if (link) {
        try {
            const url = new URL(link.getAttribute('href'), location.href);
            if ((url.protocol === 'http:' || url.protocol === 'https:') && url.origin === location.origin)
                hrefPath = url.pathname;
        } catch (_) {}
    }
    const hitElement = hit ? {tag:hit.tagName, classes:hit.getAttribute('class') || '',
        hrefPath, box:hit.getBoundingClientRect().toJSON(),
        linkBox:link ? link.getBoundingClientRect().toJSON() : null} : null;
    return {box:r.toJSON(), center, hit:el.contains(hit), focused:document.activeElement === el,
        hitElement,
        connected:el.isConnected, outline:s.outlineStyle, outlineWidth:parseFloat(s.outlineWidth),
        viewport:{width:innerWidth, height:innerHeight, scrollX, scrollY},
        documentScrollTop:document.scrollingElement && document.scrollingElement.scrollTop,
        bodyOverflow:getComputedStyle(document.body).overflowY,
        documentOverflow:getComputedStyle(document.documentElement).overflowY};
}"""


def _wait_for_focused_center(locator, page):
    """Require three stable native RAF samples without moving or mocking the page."""
    import time
    deadline = time.monotonic() + 3.0
    element = locator.element_handle(timeout=3000)
    state = None
    try:
        state = page.evaluate_handle("""el => ({element:el, observedFrames:0,
            stableFrames:0, lastRect:null, lastEligible:false})""", arg=element)
        remaining_ms = (deadline - time.monotonic()) * 1000
        if remaining_ms <= 0:
            raise BrowserTimeoutError('Native focus readiness budget exhausted before RAF sampling')
        page.wait_for_function("""state => {
            const el = state.element, r = el.getBoundingClientRect();
            const x = r.x + r.width / 2, y = r.y + r.height / 2;
            const box = {x:r.x, y:r.y, width:r.width, height:r.height};
            const eligible = Boolean(el.isConnected && document.activeElement === el
                && r.width > 0 && r.height > 0 && x >= 0 && x < innerWidth && y >= 0 && y < innerHeight
                && el.contains(document.elementFromPoint(x, y)));
            const sameBox = state.lastRect !== null
                && ['x', 'y', 'width', 'height'].every(key => state.lastRect[key] === box[key]);
            if (eligible && state.lastEligible && sameBox) state.stableFrames += 1;
            else state.stableFrames = eligible ? 1 : 0;
            state.observedFrames += 1;
            state.lastRect = box;
            state.lastEligible = eligible;
            return state.stableFrames >= 3;
        }""", arg=state, polling='raf', timeout=remaining_ms)
    except BrowserTimeoutError as error:
        geometry = element.evaluate(_FOCUS_GEOMETRY)
        if state is not None:
            geometry['readiness_frames'] = state.evaluate("""state => ({
                observed:state.observedFrames, consecutiveStable:state.stableFrames,
                requiredConsecutive:3, lastRect:state.lastRect, lastEligible:state.lastEligible})""")
        raise AssertionError('Native focus/scroll/occlusion readiness did not remain stable for '
                             '3 consecutive RAF within 3000ms: '
                             + json.dumps(geometry, sort_keys=True)) from error
    finally:
        if state is not None:
            state.dispose()


def _hit_and_keyboard_focus(locator, page, *, minimum_height=None):
    assert locator.is_visible() and locator.is_enabled()
    _wait_for_focused_center(locator, page)
    result = locator.evaluate(_FOCUS_GEOMETRY)
    assert result['focused'] and result['hit'], result
    assert result['outline'] != 'none' and result['outlineWidth'] > 0, result
    if minimum_height is not None:
        assert result['box']['height'] >= minimum_height, result
    return result


def _keyboard_light(page, wanted):
    preferences = page.locator('[data-motion-preferences]')
    summary = preferences.locator('summary')
    summary.focus()
    if preferences.get_attribute('open') is None:
        page.keyboard.press('Enter')
    assert preferences.get_attribute('open') is not None
    # Follow the actual native Tab order, rather than dispatching a synthetic event.
    summary.focus()
    page.keyboard.press('Tab')
    toggle = preferences.locator('[data-motion-toggle]')
    control = _hit_and_keyboard_focus(toggle, page, minimum_height=44)
    assert_surface_legible(toggle, (':scope',))
    page.keyboard.press('Tab')
    checkbox = preferences.locator('[data-marine-toggle]')
    _hit_and_keyboard_focus(checkbox, page)
    assert checkbox.locator('xpath=..').bounding_box()['height'] >= 44
    if checkbox.is_checked() != wanted:
        page.keyboard.press('Space')
    assert checkbox.is_checked() == wanted
    _wait_light(page, wanted)
    summary.focus()
    page.keyboard.press('Enter')
    assert preferences.get_attribute('open') is None
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_function('window.scrollY <= 1')
    return control


def _pause_existing_featured(page):
    """Use existing presentation controls so OFF/ON geometry samples stay comparable."""
    toggles = page.locator('[data-home-featured-toggle]:visible')
    for index in range(toggles.count()):
        toggle = toggles.nth(index)
        if toggle.get_attribute('aria-pressed') != 'true':
            toggle.click()
        assert toggle.get_attribute('aria-pressed') == 'true'
    page.evaluate('window.scrollTo(0, 0)')
    return toggles.count()


def _capture(page, tmp_path, label, *, content, readable, light_on, launcher):
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_function('window.scrollY <= 1')
    image = tmp_path / (label + '.png')
    # Preserve the real rendering even when a subsequent acceptance assertion fails.
    page.screenshot(path=str(image))
    assert page.locator('[data-brand-scene]').count() == 1
    assert page.locator('[data-brand-scene]').get_attribute('aria-hidden') == 'true'
    layout = page.evaluate("""selector => {
        const light = document.querySelector('[data-marine-light]');
        const style = getComputedStyle(light), lightBox = light.getBoundingClientRect();
        const ancestorStyles = [];
        for (let node = light; node; node = node.parentElement) {
            const css = getComputedStyle(node);
            ancestorStyles.push({tag:node.tagName, id:node.id, classes:String(node.className || ''),
                display:css.display, visibility:css.visibility, opacity:Number(css.opacity),
                contentVisibility:css.contentVisibility, overflowX:css.overflowX, overflowY:css.overflowY,
                box:node.getBoundingClientRect().toJSON()});
        }
        const mark = document.querySelector('[data-ns-assistant-open]');
        return {viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
            documentHeight:document.documentElement.scrollHeight,
            content:document.querySelector(selector).getBoundingClientRect().toJSON(),
            light:{running:light.classList.contains('is-running'), opacity:Number(style.opacity),
                visible:light.checkVisibility({checkOpacity:true, checkVisibilityCSS:true}),
                box:lightBox.toJSON(),
                intersectsViewport:lightBox.right > 0 && lightBox.bottom > 0 &&
                    lightBox.left < innerWidth && lightBox.top < innerHeight,
                ancestorStyles,
                pointerEvents:style.pointerEvents, animation:style.animationName,
                duration:style.animationDuration},
            launcher:mark ? mark.getBoundingClientRect().toJSON() : null};
    }""", content)
    assert layout['documentWidth'] <= layout['viewport'] + 1, layout
    assert layout['light']['running'] == light_on, layout
    assert layout['light']['opacity'] == (1 if light_on else 0), layout
    assert layout['light']['pointerEvents'] == 'none', layout
    # Ancestor visibility/opacity and positive on-screen geometry are required;
    # the retained screenshot supplies raster evidence beyond these conditions.
    assert layout['light']['visible'] == light_on, layout
    if light_on:
        assert layout['light']['box']['width'] > 0 and layout['light']['box']['height'] > 0, layout
        assert layout['light']['intersectsViewport'], layout
        assert layout['light']['animation'] != 'none', layout
    if launcher:
        mark = page.locator('[data-ns-assistant-open]')
        assert mark.count() == 1 and mark.is_visible()
        box = layout['launcher']
        assert box['width'] >= 44 and box['height'] >= 44, box
        assert box['x'] >= 0 and box['right'] <= layout['viewport'] + 1, box
        assert mark.evaluate("e => e.contains(document.elementFromPoint(e.getBoundingClientRect().x + e.getBoundingClientRect().width / 2, e.getBoundingClientRect().y + e.getBoundingClientRect().height / 2))")
        assert mark.get_attribute('aria-label')
        mark.locator('img').wait_for(state='visible')
        assert mark.locator('img').evaluate('e => e.complete && e.naturalWidth > 0')
    else:
        assert page.locator('[data-ns-assistant-open]').count() == 0
        assert layout['launcher'] is None
    surfaces = [assert_surface_legible(locator, selectors) for locator, selectors in readable]
    return {'screenshot':image.name, 'layout':layout, 'surfaces':surfaces}


def _same_layout_and_readability(off, on):
    assert abs(off['layout']['documentHeight'] - on['layout']['documentHeight']) <= 1, (off, on)
    for key in ('x', 'y', 'width', 'height'):
        assert abs(off['layout']['content'][key] - on['layout']['content'][key]) <= 1, (off, on)
        if off['layout']['launcher'] is not None:
            assert abs(off['layout']['launcher'][key] - on['layout']['launcher'][key]) <= 1, (off, on)
    assert len(off['surfaces']) == len(on['surfaces'])
    for before, after in zip(off['surfaces'], on['surfaces']):
        assert before['background'] == after['background']
        assert [(x['text'], x['contrast']) for x in before['samples']] == [
            (x['text'], x['contrast']) for x in after['samples']]


def _request_boundary_and_questions(database, before, calls, external, errors, origin):
    assert _question_rows(database) == before
    assert not external and not errors, (external, errors)
    assert all(method in ('GET', 'HEAD') or (
        method == 'POST' and path == origin + '/api/growth/funnel-event')
        for method, path in calls), calls


def _proof(capsys, tmp_path, width, surface, observations, assets, before, calls):
    report = {'schema':'OWNED_MARINE_VISUAL_POLISH_V1', 'width':width, 'surface':surface,
        'scope':'Original LOCAL_SAFE actual App/browser with owned SQLite and loopback only',
        'default_off_observed':True, 'off_on_layout_preserved':True,
        'flat_content_text_contrast_min':min(sample['contrast'] for observation in observations
            for panel in observation['surfaces'] for sample in panel['samples']),
        'served_candidate_assets':assets, 'question_rows_before':before, 'question_rows_after':before,
        'browser_external_requests':0, 'browser_unexpected_write_requests':0,
        'browser_local_telemetry_posts':sum(method == 'POST' for method, _ in calls),
        'production_observed':False, 'whole_application_certified':False,
        'coverage_limits':['Other pages and scroll positions are not certified by this matrix',
            'Existing decorated hero gradients are not assigned a flat contrast ratio',
            'Existing motion suite owns pulse, reduced-motion, modal and history; input/native visibility evidence is separate'],
        'observations':observations}
    path = tmp_path / (surface + '-' + str(width) + '-acceptance.json')
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    with capsys.disabled():
        print('OWNED_MARINE_VISUAL_POLISH_PROOF ' + json.dumps({
            key:value for key, value in report.items() if key != 'observations'},
            ensure_ascii=True, sort_keys=True), flush=True)


@pytest.mark.parametrize('width', WIDTHS)
def test_public_home_and_long_match_keep_content_and_controls_with_marine_light(
        fixture_server, tmp_path, width, capsys):
    _module, database, origin, scenarios = fixture_server
    before = _question_rows(database)
    with sync_playwright() as pw:
        browser, context, calls, external = _browser(pw, origin, width)
        page = context.new_page()
        _preferences(context, page)
        page.set_default_timeout(10000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        responses = _collect_assets(page)
        observations = []
        assets = {}
        try:
            result = page.goto(origin + '/', wait_until='networkidle')
            assert result.status == 200
            assert page.locator('[data-v1000-home]').count() == 1
            launcher = page.locator('[data-ns-assistant-open]')
            launcher.wait_for(state='visible')
            launcher.focus()  # End the existing finite discovery before comparisons.
            page.wait_for_function("!document.querySelector('[data-ns-assistant-open]').classList.contains('ns-discovery-pulse')")
            assert not page.locator('[data-marine-toggle]').is_checked()
            _wait_light(page, False)
            _pause_existing_featured(page)
            assets['home'] = _served_asset_digests(responses)
            card = page.locator('.v933-match-card:visible').first
            if card.count() == 0:
                # This owned fixture is a secondary competition. Today's
                # feature must not promote it just to fill the carousel; open
                # its real ordinary-list controls before comparing readability.
                more = page.locator('[data-home-more-leagues]').first
                assert more.count() == 1 and more.get_attribute('open') is None
                more.locator(':scope > summary').focus()
                page.keyboard.press('Enter')
                assert more.get_attribute('open') is not None
                league = more.locator('[data-home-importance="secondary"]').first
                assert league.count() == 1 and league.get_attribute('open') is None
                league.locator(':scope > summary').focus()
                page.keyboard.press('Enter')
                assert league.get_attribute('open') is not None
            assert card.count() == 1
            home_readable = [(card, ('.v933-match-teams > div:first-child strong',
                '.v933-match-teams > div:last-child strong', '.v933-match-card-header a.is-competition'))]
            primary = page.locator('.v933-hero-actions a').first
            primary_href = primary.get_attribute('href')
            assert primary_href and primary_href.startswith('/')
            launcher_href = launcher.get_attribute('href')
            assert launcher_href == '/shark'
            off = _capture(page, tmp_path, f'client-home-{width}-off', content='[data-v1000-home]',
                readable=home_readable, light_on=False, launcher=True)
            _keyboard_light(page, True)
            on = _capture(page, tmp_path, f'client-home-{width}-on', content='[data-v1000-home]',
                readable=home_readable, light_on=True, launcher=True)
            _same_layout_and_readability(off, on)
            assert primary.get_attribute('href') == primary_href
            primary.focus()
            _wait_for_focused_center(primary, page)
            assert primary.evaluate('e => document.activeElement === e')
            assert primary.evaluate('e => e.contains(document.elementFromPoint(e.getBoundingClientRect().x + e.getBoundingClientRect().width / 2, e.getBoundingClientRect().y + e.getBoundingClientRect().height / 2))')
            assert launcher.get_attribute('href') == launcher_href
            observations.extend((off, on))

            _keyboard_light(page, False)
            responses.clear()
            result = page.goto(origin + '/match/v1000-long', wait_until='networkidle')
            assert result.status == 200
            _wait_light(page, False)
            assets['match'] = _served_asset_digests(responses)
            header = page.locator('[data-match-component="MatchHeader"]')
            assert header.count() == 1
            case = next(item for item in scenarios if item[0] == 'long')
            names = [case[1], case[2]]
            assert header.locator('.v944-match-team strong').all_text_contents() == names
            header_readable = [(header, ('[data-match-side="home"] strong', '[data-match-side="home"] small',
                '[data-match-side="away"] strong', '[data-match-side="away"] small', '.v944-score-widget strong'))]
            for index, name in enumerate(names):
                team = header.locator('.v944-match-team').nth(index)
                assert team.get_attribute('href') == '/team/' + quote(name, safe='')
                assert team.locator('strong').evaluate('e => e.scrollWidth <= e.clientWidth + 2')
                assert team.locator('.v933-team-logo img').evaluate('e => e.complete && e.naturalWidth > 0')
            launcher_href = page.locator('[data-ns-assistant-open]').get_attribute('href')
            assert urlsplit(launcher_href).path == '/shark'
            assert parse_qs(urlsplit(launcher_href).query).get('match_id') == ['v1000-long']
            off = _capture(page, tmp_path, f'client-match-{width}-off', content='[data-match-component="MatchHeader"]',
                readable=header_readable, light_on=False, launcher=True)
            _keyboard_light(page, True)
            on = _capture(page, tmp_path, f'client-match-{width}-on', content='[data-match-component="MatchHeader"]',
                readable=header_readable, light_on=True, launcher=True)
            _same_layout_and_readability(off, on)
            assert page.locator('[data-ns-assistant-open]').get_attribute('href') == launcher_href
            observations.extend((off, on))
            _request_boundary_and_questions(database, before, calls, external, errors, origin)
            _proof(capsys, tmp_path, width, 'public-home-and-long-match', observations, assets, before, calls)
        finally:
            context.close()
            browser.close()


@pytest.mark.parametrize('width', WIDTHS)
def test_authenticated_admin_shared_light_keeps_opaque_readable_surfaces_and_no_launcher(
        actual_http, tmp_path, width, capsys):
    origin, cookie_name, cookie, database = actual_http
    before = _question_rows(database)
    with sync_playwright() as pw:
        browser, context, calls, external = _browser(pw, origin, width)
        context.add_cookies([{'name':cookie_name, 'value':cookie, 'url':origin, 'httpOnly':True}])
        page = context.new_page()
        _preferences(context, page)
        page.set_default_timeout(10000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        responses = _collect_assets(page)
        try:
            result = page.goto(origin + '/admin/founder-os', wait_until='networkidle')
            assert result.status == 200 and urlsplit(page.url).path == '/admin/founder-os'
            assert 'ns-admin' in page.locator('body').get_attribute('class').split()
            assert page.locator('.founder-os h1').inner_text() == 'Control fundador'
            assert page.locator('[data-ns-assistant-open]').count() == 0
            assert not page.locator('[data-marine-toggle]').is_checked()
            _wait_light(page, False)
            assets = {'admin':_served_asset_digests(responses)}
            inbox = page.locator('#inbox')
            readable = [(inbox, ('.founder-os-panel-head h2', '.founder-os-alert-content strong',
                '.founder-os-alert-content p', '.founder-os-alert-meta'))]
            off = _capture(page, tmp_path, f'admin-founder-{width}-off', content='[data-founder-os]',
                readable=readable, light_on=False, launcher=False)
            _keyboard_light(page, True)
            on = _capture(page, tmp_path, f'admin-founder-{width}-on', content='[data-founder-os]',
                readable=readable, light_on=True, launcher=False)
            _same_layout_and_readability(off, on)
            evidence_link = page.locator('.v1000-founder-actions a[href="/admin/backups"]')
            evidence_link.focus()
            _wait_for_focused_center(evidence_link, page)
            assert evidence_link.evaluate('e => document.activeElement === e')
            assert evidence_link.evaluate('e => e.contains(document.elementFromPoint(e.getBoundingClientRect().x + e.getBoundingClientRect().width / 2, e.getBoundingClientRect().y + e.getBoundingClientRect().height / 2))')
            assert page.locator('[data-ns-assistant-open]').count() == 0
            _request_boundary_and_questions(database, before, calls, external, errors, origin)
            _proof(capsys, tmp_path, width, 'authenticated-admin-founder', (off, on), assets, before, calls)
        finally:
            context.close()
            browser.close()



def test_marine_light_pauses_for_owned_input_focus_and_records_native_visibility(
        fixture_server, tmp_path, capsys):
    """Focus is exercised; a headless visibility gap must remain explicitly unknown."""
    _module, database, origin, _scenarios = fixture_server
    before = _question_rows(database)
    with sync_playwright() as pw:
        browser, context, calls, external = _browser(pw, origin, 390)
        page = context.new_page()
        _preferences(context, page)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        responses = _collect_assets(page)
        peer = None
        try:
            result = page.goto(origin + '/', wait_until='networkidle')
            assert result.status == 200
            launcher = page.locator('[data-ns-assistant-open]')
            launcher.wait_for(state='visible')
            launcher.focus()
            page.wait_for_function("!document.querySelector('[data-ns-assistant-open]').classList.contains('ns-discovery-pulse')")
            _keyboard_light(page, True)
            assets = _served_asset_digests(responses)
            # This labelled test input is outside the motion controls. It sends
            # no form and replaces no existing application component or handler.
            page.evaluate("""() => {
                const wrapper = document.createElement('div');
                wrapper.id = 'owned-marine-input-region';
                const label = document.createElement('label');
                label.htmlFor = 'owned-marine-input';
                label.textContent = 'Campo de comprobación aislado';
                const input = document.createElement('input');
                input.id = 'owned-marine-input';
                input.type = 'text';
                wrapper.append(label, input);
                document.getElementById('main-content').appendChild(wrapper);
            }""")
            field = page.get_by_label('Campo de comprobación aislado')
            field.focus()
            assert field.is_visible() and field.evaluate('e => document.activeElement === e')
            _wait_light(page, False)
            field.press_sequentially('Prueba', delay=20)
            assert field.input_value() == 'Prueba'
            _wait_light(page, False)
            checkbox = page.locator('[data-marine-toggle]')
            assert checkbox.is_checked()
            summary = page.locator('[data-motion-preferences] summary')
            summary.focus()  # A real blur, not a dispatched visibility/focus event.
            assert summary.evaluate('e => document.activeElement === e')
            _wait_light(page, True)
            assert checkbox.is_checked()

            # Use only native tab activation. Some headless Chromium builds keep
            # every page visible; those builds do not certify the hidden state.
            peer = context.new_page()
            peer.bring_to_front()
            try:
                page.wait_for_function('document.hidden === true', polling=100, timeout=1500)
            except BrowserTimeoutError:
                pass
            hidden_observed = page.evaluate('document.hidden')
            if hidden_observed:
                _wait_light(page, False)
                assert checkbox.is_checked()
                page.bring_to_front()
                page.wait_for_function('document.hidden === false', polling=100, timeout=1500)
                _wait_light(page, True)
                visibility = {'status':'VERIFIED_NATIVE_TAB_VISIBILITY',
                    'hidden_observed':True, 'hidden_pause':True, 'visible_resume':True}
            else:
                visibility = {'status':'UNVERIFIED_NATIVE_VISIBILITY', 'hidden_observed':False,
                    'reason':'Native bring_to_front did not make the App page document.hidden; no property or clock was mocked.'}
            peer.close()
            peer = None
            page.bring_to_front()
            _wait_light(page, True)
            assert checkbox.is_checked()
            _request_boundary_and_questions(database, before, calls, external, errors, origin)
            report = {'schema':'OWNED_MARINE_INPUT_NATIVE_VISIBILITY_V1',
                'scope':'Original LOCAL_SAFE App, labelled owned DOM input, native browser tabs only',
                'width':390, 'input_focus_pause':True, 'typed_value_observed':True,
                'actual_blur_resume':True, 'marine_choice_preserved':True,
                'native_visibility':visibility, 'served_candidate_assets':assets,
                'question_rows_before':before, 'question_rows_after':before,
                'browser_external_requests':0, 'browser_unexpected_write_requests':0,
                'production_observed':False, 'all_pause_modes_certified':False,
                'pause_mode_scope':'Input focus/blur and native visibility only when observed; other modes belong to separate tests'}
            (tmp_path / 'owned-input-native-visibility.json').write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
            with capsys.disabled():
                print('OWNED_MARINE_INPUT_NATIVE_VISIBILITY_PROOF ' + json.dumps(
                    report, ensure_ascii=True, sort_keys=True), flush=True)
        finally:
            if peer is not None:
                peer.close()
            context.close()
            browser.close()
