"""Offline evidence for navigation failures; no application or browser is started."""
import json
from types import SimpleNamespace

import pytest

from tools import run_production_quality_browser_gate as gate


BASE = "https://release-qa.invalid"
TARGET = "/calendario?lane=finished"
MESSAGE = "browser details must stay private: https://example.invalid/?token=private"
DURATIONS = {"capture_images": 2.0, "click": 5.0, "wait_for_url": 13.0, "read_destination": 3.0}
ORIGINAL_KEYS = {"href", "found", "final_path", "final_query", "final_url", "pass", "error"}
PREPARATION = [
    ("goto", BASE, {"wait_until": "domcontentloaded", "timeout": 30_000}),
    ("locator", f'[data-nav-zone="client-bottom"] a[href="{TARGET}"]'),
    ("count",),
    ("is_visible",),
]
STAGE_CALLS = [
    ("capture_images",),
    ("click", {"timeout": 10_000}),
    ("wait_for_url", {"wait_until": "domcontentloaded", "timeout": 30_000}),
    ("read_destination",),
]


class JourneyPage:
    def __init__(self, *, fail_at="", count=1, visible=True, destination=BASE + TARGET):
        self.fail_at = fail_at
        self.link_count = count
        self.visible = visible
        self.destination = destination
        self.calls = []
        self.elapsed = 0.0

    def step(self, name, *details):
        self.calls.append((name, *details))
        self.elapsed += DURATIONS.get(name, 0.0) / 1000
        if name == self.fail_at:
            raise TimeoutError(MESSAGE)

    def goto(self, url, **kwargs):
        self.step("goto", url, kwargs)

    def locator(self, selector):
        self.step("locator", selector)
        return self

    @property
    def first(self):
        return self

    def count(self):
        self.step("count")
        return self.link_count

    def is_visible(self):
        self.step("is_visible")
        return self.visible

    def click(self, **kwargs):
        self.step("click", kwargs)

    def wait_for_url(self, predicate, **kwargs):
        self.step("wait_for_url", kwargs)
        assert predicate(BASE + TARGET)
        assert not predicate(BASE + "/calendario?lane=today")

    @property
    def url(self):
        self.step("read_destination")
        return self.destination


def run_journey(monkeypatch, page, paths=(TARGET,)):
    monkeypatch.setattr(gate, "time", SimpleNamespace(perf_counter=lambda: page.elapsed))
    monkeypatch.setattr(gate, "_remember_image_failures", lambda current: current.step("capture_images"))
    return gate._click_journey(page, BASE, "client-bottom", paths)


@pytest.mark.parametrize("failed_stage", ["", *DURATIONS])
def test_stage_evidence_preserves_outcomes_calls_and_timeout_budgets(monkeypatch, failed_stage):
    page = JourneyPage(fail_at=failed_stage)
    result, = run_journey(monkeypatch, page)
    completed = len(DURATIONS) if not failed_stage else list(DURATIONS).index(failed_stage) + 1
    assert page.calls == PREPARATION + STAGE_CALLS[:completed]
    assert page._sentinel_phase == "QA_NAVIGATION"
    assert result["failed_stage"] == failed_stage
    assert result["stage_elapsed_ms"] == dict(list(DURATIONS.items())[:completed])
    assert {key: result[key] for key in ORIGINAL_KEYS} == {
        "href": TARGET,
        "found": True,
        "final_path": "" if failed_stage else "/calendario",
        "final_query": "" if failed_stage else "lane=finished",
        "final_url": "" if failed_stage else BASE + TARGET,
        "pass": not failed_stage,
        "error": "TimeoutError" if failed_stage else "",
    }
    assert set(result) == ORIGINAL_KEYS | {"failed_stage", "stage_elapsed_ms"}
    assert "token=private" not in json.dumps(result)


@pytest.mark.parametrize("count,visible", [(0, True), (1, False)])
def test_missing_or_hidden_link_remains_failed_without_invented_stage_timings(monkeypatch, count, visible):
    page = JourneyPage(count=count, visible=visible)
    result, = run_journey(monkeypatch, page)
    assert page.calls == PREPARATION[:3 if count == 0 else 4]
    assert result == {
        "href": TARGET, "found": False, "final_path": "", "final_query": "", "final_url": "",
        "pass": False, "error": "", "failed_stage": "", "stage_elapsed_ms": {},
    }


@pytest.mark.parametrize("destination,expected_error", [
    (BASE + "/calendario?lane=today", ""),
    ("https://[", "ValueError"),
])
def test_wrong_or_unparseable_final_destination_still_fails(monkeypatch, destination, expected_error):
    page = JourneyPage(destination=destination)
    result, = run_journey(monkeypatch, page)
    assert page.calls == PREPARATION + STAGE_CALLS
    assert result["pass"] is False
    assert result["final_url"] == destination
    assert result["error"] == expected_error
    assert result["failed_stage"] == ("read_destination" if expected_error else "")
    assert result["stage_elapsed_ms"] == DURATIONS


@pytest.mark.parametrize("stage", ["goto", "locator", "count", "is_visible"])
def test_preparation_failures_still_propagate(monkeypatch, stage):
    page = JourneyPage(fail_at=stage)
    with pytest.raises(TimeoutError, match="browser details must stay private"):
        run_journey(monkeypatch, page)
    assert page.calls == PREPARATION[:[call[0] for call in PREPARATION].index(stage) + 1]


def test_each_journey_records_only_its_own_elapsed_times(monkeypatch):
    page = JourneyPage()
    results = run_journey(monkeypatch, page, paths=(TARGET, TARGET))
    assert len(results) == 2
    assert results[0] == results[1]
    assert all(result["pass"] and result["stage_elapsed_ms"] == DURATIONS for result in results)
    assert results[0]["stage_elapsed_ms"] is not results[1]["stage_elapsed_ms"]
    assert page.calls == (PREPARATION + STAGE_CALLS) * 2
