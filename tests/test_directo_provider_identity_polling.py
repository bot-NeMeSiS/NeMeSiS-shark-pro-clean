"""SIMULATED_QA: provider updates keep their IDs; fixture counters stay unique.

Run the real updater in Chromium with canonical states and the existing offline
component harness. No Flask import, database, provider request or production UI.
"""
from copy import deepcopy
from datetime import timedelta, timezone
from email.utils import format_datetime

import pytest

from test_directo_filter_feedback import NOW, ROOT, browser, markup, row, snapshot


PRIMARY = "af-polling-qa"
ALTERNATE = "sportsdb-polling-qa"


def observation(identifier, now=NOW, status="LIVE", **changes):
    return row(
        now, ident=identifier, status=status,
        source="api_football_live" if identifier == PRIMARY else "TheSportsDB API",
        **changes,
    )


def provider_payload(rows, now):
    payload = snapshot(rows, now)
    observations = payload["matches"]
    representative = PRIMARY if any(item["id"] == PRIMARY for item in observations) else (
        observations[0]["id"] if observations else ""
    )
    payload["provider_matches"] = deepcopy(observations)
    payload["fixture_ids"] = {item["id"]: representative for item in observations}
    payload["matches"] = [item for item in observations if item["id"] == representative]
    payload["live"] = [item for item in observations if item["is_live"]][:1]
    payload["counts"].update(matches=int(bool(observations)), live=int(bool(payload["live"])))
    return payload


@pytest.fixture
def provider_screen(browser):
    contexts = []

    def create(*, initial_status="LIVE", generic=False):
        context = browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
        contexts.append(context)
        page = context.new_page()
        page.clock.install(time=NOW)
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        context.route("**/*", lambda route: (requests.append(route.request.url), route.abort()))
        document = markup(snapshot([observation(ALTERNATE, status=initial_status)]))
        if generic:
            document = document.replace('data-v934-directo="inplace-v1"', "")
        page.set_content(document)
        page.evaluate("""() => {
          window.qa = {calls: [], transport: {}};
          window.fetch = async (url, options) => {
            qa.calls.push({url: String(url), method: options.method || 'GET'});
            return new Response(JSON.stringify(qa.transport.payload), {
              status: 200, headers: {Date: qa.transport.date}
            });
          };
        }""")
        page.add_script_tag(content=(ROOT / "static/v934-realtime.js").read_text())
        page._provider_errors, page._provider_requests = errors, requests
        return page

    yield create
    for context in contexts:
        for page in context.pages:
            assert page._provider_errors == []
            assert page._provider_requests == []
        context.close()


def deliver(page, payload, *, seconds=45, advance=45000):
    now = NOW + timedelta(seconds=seconds)
    page.evaluate("(value) => qa.transport = value", {
        "payload": payload,
        "date": format_datetime(now.astimezone(timezone.utc), usegmt=True),
    })
    page.clock.run_for(advance)
    page.wait_for_timeout(20)


def live_count(page):
    return page.locator('[data-test-kpi="live"] strong').inner_text()


@pytest.mark.parametrize("status,halftime", [("LIVE", "0"), ("HT", "1")])
def test_provider_alias_updates_in_place_but_counts_one_fixture(provider_screen, status, halftime):
    page = provider_screen(initial_status=status)
    link = page.locator(f'a[href="/match/{ALTERNATE}"]')
    link.focus()
    page.evaluate("window.originalCard = document.querySelector('[data-v934-match-card]')")
    now = NOW + timedelta(seconds=45)
    payload = provider_payload([
        observation(PRIMARY, now, status),
        observation(ALTERNATE, now, status, home_score=2, minute=17),
    ], now)

    deliver(page, payload)

    assert live_count(page) == "1"
    assert page.locator('[data-test-kpi="break"] strong').inner_text() == halftime
    assert page.locator('[data-v934-score]').inner_text() == "2 - 0"
    assert page.locator('[data-v934-minute]').inner_text() == "Min 17"
    assert page.locator('[data-canonical-live]').get_attribute("data-canonical-live") == "true"
    assert page.locator('[data-directo-refresh-list]').is_hidden()
    assert page.locator('[data-directo-notice]').is_hidden()
    assert page.locator("main").get_attribute("data-directo-visible-live-count") == "1"
    assert link.evaluate("node => node === document.activeElement")
    assert page.evaluate("originalCard === document.querySelector('[data-v934-match-card]')")
    assert page.evaluate("qa.calls") == [{"url": "/api/realtime/sports?scope=matches", "method": "GET"}]


def test_nonlive_primary_does_not_hide_confirmed_live_alternate(provider_screen):
    page = provider_screen()
    now = NOW + timedelta(seconds=45)
    payload = provider_payload([
        observation(PRIMARY, now, "NS", kickoff_time="20:00"),
        observation(ALTERNATE, now, home_score=2, minute=19),
    ], now)
    assert payload["matches"][0]["is_live"] is False
    assert payload["counts"]["live"] == 1

    deliver(page, payload)

    assert live_count(page) == "1"
    assert page.locator('[data-canonical-live]').get_attribute("data-canonical-live") == "true"
    assert page.locator('[data-v934-score]').inner_text() == "2 - 0"
    assert page.locator('[data-directo-refresh-list]').is_hidden()


def test_real_provider_omission_withdraws_only_that_observation(provider_screen):
    page = provider_screen()
    first = NOW + timedelta(seconds=45)
    deliver(page, provider_payload([
        observation(PRIMARY, first), observation(ALTERNATE, first),
    ], first))
    second = NOW + timedelta(seconds=90)
    payload = provider_payload([observation(PRIMARY, second, home_score=3)], second)

    deliver(page, payload, seconds=90)

    assert live_count(page) == "1"  # The other provider still has valid evidence.
    assert page.locator('[data-canonical-live]').get_attribute("data-canonical-live") == "false"
    assert page.locator('[data-canonical-live]').get_attribute("data-canonical-status") == "INCOMPLETE"
    assert "Fuera de la última lectura" in page.locator('[data-v934-status]').inner_text()
    assert page.locator('[data-v934-score]').inner_text() == "1 - 0"  # Never borrow primary's score.
    assert page.locator("main").get_attribute("data-directo-visible-live-count") == "0"


def test_replayed_provider_group_does_not_renew_individual_live_leases(provider_screen):
    page = provider_screen()
    first = NOW + timedelta(seconds=45)
    payload = provider_payload([observation(PRIMARY), observation(ALTERNATE)], first)
    deliver(page, payload)
    assert live_count(page) == "1"

    # The repeated payload and HTTP Date cannot extend either original lease.
    page.clock.run_for(80000)
    page.wait_for_timeout(20)

    assert live_count(page) == "0"
    assert page.locator('[data-canonical-live]').get_attribute("data-canonical-status") == "STALE"
    assert page.locator('[data-v934-minute]').is_hidden()
    assert page.locator('[data-realtime-freshness] time').get_attribute("datetime") == NOW.isoformat()
    assert page.locator('[data-v934-score]').inner_text() == "1 - 0"


@pytest.mark.parametrize("mode", ["legacy", "missing_map", "malformed_map", "cyclic_map", "generic"])
def test_optional_identity_contract_never_blocks_original_id_updates(provider_screen, mode):
    page = provider_screen(generic=mode == "generic")
    now = NOW + timedelta(seconds=45)
    payload = provider_payload([
        observation(PRIMARY, now), observation(ALTERNATE, now, home_score=2, minute=18),
    ], now)
    if mode == "legacy":
        payload["matches"] = [payload["provider_matches"][1]]
        payload.pop("provider_matches")
        payload.pop("fixture_ids")
    elif mode == "missing_map":
        payload.pop("fixture_ids")
    elif mode == "malformed_map":
        payload["fixture_ids"] = []
    elif mode == "cyclic_map":
        payload["fixture_ids"] = {PRIMARY: ALTERNATE, ALTERNATE: PRIMARY}

    # Generic bars keep their existing polling jitter (up to 49 seconds here).
    if mode == "generic":
        deliver(page, payload, seconds=50, advance=50000)
    else:
        deliver(page, payload)

    assert page.locator('[data-v934-score]').inner_text() == "2 - 0"
    assert page.locator('[data-v934-minute]').inner_text() == "Min 18"
    if mode in {"missing_map", "malformed_map", "cyclic_map"}:
        assert live_count(page) == "—"  # No guessed grouping or falsely complete count.
    elif mode == "legacy":
        assert live_count(page) == "1"
