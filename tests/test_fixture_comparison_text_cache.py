"""Bounded text work preserves main4b semantics and fresh fixture evidence."""
import re
import sys
import json
import math
import time
from copy import deepcopy
from datetime import datetime, timedelta
from contextlib import contextmanager
from types import ModuleType
import unicodedata

import pytest

from engines import competition_read_model as competition
from engines import fixture_identity_read_model as identity


def published_normalized(value):
    """Uncached main4b expression; deliberately separate from the new helper."""
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()).strip("-")


def published_name_forms(value):
    """Main4b algorithm, retaining the real current alias/category functions."""
    key = identity.provider_team_identity_key(identity.spanish_team_name(value))
    key = re.sub(r"\b(?:f c|c f|c d|u d|s d|a c|s c)\b",
                 lambda match: match.group(0).replace(" ", ""), key)
    category, key = identity._category(key)
    tokens = tuple(key.split())
    changed = True
    while tokens and changed:
        changed = False
        for designator in identity._CLUB_DESIGNATORS:
            size = len(designator)
            if tokens[:size] == designator:
                tokens, changed = tokens[size:], True
                break
            if tokens[-size:] == designator:
                tokens, changed = tokens[:-size], True
                break
    full = " ".join(tokens)
    short_tokens = tokens
    while short_tokens and short_tokens[0] in identity._PREFIXES:
        short_tokens = short_tokens[1:]
    short = " ".join(short_tokens)
    if full in identity._UNKNOWN or short in identity._UNKNOWN or len(short) < 2:
        return None
    return category, full, short


@pytest.fixture(autouse=True)
def empty_text_caches():
    competition._normalized_short_text.cache_clear()
    identity._short_name_forms.cache_clear()
    yield
    competition._normalized_short_text.cache_clear()
    identity._short_name_forms.cache_clear()


TEXT = [None, False, True, 0, 1, -12, 12.5, float("inf"), float("nan"), {}, [],
        "", "  ", "N/A", "FC", "C.F. B", "Real Deportivo Atlético QA C.F.",
        "Synthetic U23 Women FC", "QA II", "QA III", "QA reserves", "QA Men",
        "Andalucía", "Atlético", "Łódź", "İstanbul", "Æther", "F.C. São-Paulo",
        "Europa League", "Champions League", "QA-" * 50, "QA-" * 600,
        "A\u0301", "\ud800", "\x00", "中", "🦈"]
TEXT += ["QA " + chr(point) + " Atlético C.F. U19" for point in range(0, 0x110000, 4093)]


@pytest.mark.parametrize("value", TEXT)
def test_normalization_is_exact_for_cold_and_repeated_text(value):
    expected = published_normalized(value)
    assert competition.normalized(value) == expected
    assert competition.normalized(value) == expected


@pytest.mark.parametrize("value", TEXT)
def test_name_forms_match_published_algorithm_cold_and_warm(value):
    expected = published_name_forms(value)
    assert identity._name_forms(value) == expected
    assert identity._name_forms(value) == expected
    if expected is not None:
        assert type(expected) is tuple and type(expected[0]) is frozenset


def test_custom_input_conversion_is_still_executed_each_time():
    class Changing:
        def __init__(self):
            self.calls = []

        def __bool__(self):
            self.calls.append("bool")
            return True

        def __str__(self):
            self.calls.append("str")
            return "Current text " + str(len(self.calls))

    actual, expected = Changing(), Changing()
    for _ in range(3):
        assert competition.normalized(actual) == published_normalized(expected)
    assert actual.calls == expected.calls == ["bool", "str"] * 3


@pytest.mark.parametrize("method", ("__bool__", "__str__"))
def test_custom_conversion_errors_are_not_hidden_by_a_warm_cache(method):
    class Broken:
        def __bool__(self):
            if method == "__bool__":
                raise RuntimeError("synthetic current bool failure")
            return True

        def __str__(self):
            raise RuntimeError("synthetic current string failure")

    competition.normalized("Current text")
    with pytest.raises(RuntimeError):
        competition.normalized(Broken())
    with pytest.raises(RuntimeError):
        published_normalized(Broken())


def test_alias_resolution_precedes_cached_comparison_forms(monkeypatch):
    aliases = {"current alias": "Real Synthetic One FC"}
    calls = []

    def current_alias(value):
        calls.append(value)
        return aliases[value]

    monkeypatch.setattr(identity, "spanish_team_name", current_alias)
    first = identity._name_forms("current alias")
    assert identity._name_forms("current alias") == first
    assert identity._short_name_forms.cache_info().hits == 1
    aliases["current alias"] = "Synthetic Two Women U23 FC"
    changed = identity._name_forms("current alias")
    assert changed != first
    assert {"gender:female", "age:23"} <= changed[0]
    assert calls == ["current alias"] * 3


def test_long_text_bypasses_both_caches():
    value = "Synthetic " * 60
    assert competition.normalized(value) == published_normalized(value)
    assert identity._name_forms(value) == published_name_forms(value)
    assert competition._normalized_short_text.cache_info().currsize == 0
    assert identity._short_name_forms.cache_info().currsize == 0


def test_both_text_caches_have_fixed_entry_limits():
    for number in range(4400):
        competition.normalized("Synthetic competition " + str(number))
        identity._name_forms("Synthetic team " + str(number))
    for cache, limit in ((competition._normalized_short_text, 2048),
                         (identity._short_name_forms, 4096)):
        assert cache.cache_info().maxsize == limit
        assert cache.cache_info().currsize == limit


@pytest.mark.parametrize("field,value", (
    ("home_team_id", "synthetic-current-id"),
    ("home_canonical_team_id", "synthetic-current-canonical"),
    ("home_gender", "female"),
    ("competition_id", "synthetic-current-league"),
    ("source", "synthetic-current-provider"),
    ("raw_json", '{"fixture":{"id":999999}}'),
))
def test_warm_text_never_reuses_mutable_fixture_proof(app_module, monkeypatch, field, value):
    from tests.test_calendar_facet_batch_counts import _pair
    from tests.test_v957_calendar_fixture_deduplication import _prepare, _summary
    app = app_module
    rows = _pair(app)
    summary = _summary(rows)
    operation = _prepare(app, monkeypatch, summary)
    assert operation.snapshot.select_rows(rows).count == 1
    assert operation.snapshot.select_rows(rows).count == 1
    rows[1][field] = value
    assert operation.snapshot.context_for(rows[1]).state == "UNKNOWN_IDENTITY_CHANGED"
    assert operation.snapshot.select_rows(rows).count == 2


@contextmanager
def published_text_work(monkeypatch):
    """Restore both old pure functions and their already-imported bindings."""
    replacements = ((competition.normalized, published_normalized),
                    (identity._name_forms, published_name_forms))
    with monkeypatch.context() as control:
        for module in list(sys.modules.values()):
            if not isinstance(module, ModuleType):
                continue
            for name, value in list(vars(module).items()):
                for current, published in replacements:
                    if value is current:
                        control.setattr(module, name, published)
        yield


@pytest.mark.parametrize("size", (384, 2048))
def test_dense_calendar_complete_context_and_fresh_checks_match_main4b(app_module, monkeypatch, size):
    from engines import fixture_snapshot_read_model as snapshot
    from tests.test_calendar_facet_batch_counts import _unique_primary
    from tests.test_v957_calendar_fixture_deduplication import _prepare, _summary
    from tests.test_calendar_live_display_names import _same_calendar_tree
    from test_client_view_preparation import same_evaluation
    from zoneinfo import ZoneInfo
    app = app_module
    rows = []
    for number in range(size):
        row = _unique_primary(app, number, home="Synthetic comparison home " + str(number))
        start = datetime.fromisoformat(row["kickoff_iso"]) + timedelta(days=(1, 2, 5, 10)[number % 4] - 1)
        raw = json.loads(row["raw_json"])
        raw["fixture"]["date"] = start.isoformat()
        row.update(kickoff_iso=start.isoformat(), match_date=start.date().isoformat(), raw_json=json.dumps(raw))
        rows.append(row)
    rows += [dict(row, id="copy-" + row["id"], match_id="copy-" + row["id"]) for row in rows[:size // 12]]
    summary = _summary(rows)
    original = deepcopy(summary)
    results, measurements = [], []
    original_project = snapshot.project_fixture_identity
    calls = []

    def observe_projection(*args, **kwargs):
        calls.append(1)
        return original_project(*args, **kwargs)

    with app.app.test_request_context("/calendar?lane=week"):
        operation = _prepare(app, monkeypatch, summary)
        monkeypatch.setattr(snapshot, "project_fixture_identity", observe_projection)
        # ABBA ordering reduces order bias; these are component measurements,
        # never a cold/global production benchmark or a wall-time test gate.
        for label in ("candidate", "published", "published", "candidate"):
            competition._normalized_short_text.cache_clear()
            identity._short_name_forms.cache_clear()
            calls.clear()

            def evaluate():
                started_at = datetime.now(ZoneInfo("UTC"))
                started = time.perf_counter()
                result = app.v940_calendar_context(summary, "week", app.today_iso(), fixture_operation=operation)
                elapsed = time.perf_counter() - started
                window = (started_at, datetime.now(ZoneInfo("UTC")))
                return result, elapsed, window

            if label == "published":
                with published_text_work(monkeypatch):
                    result, seconds, window = evaluate()
            else:
                result, seconds, window = evaluate()
            results.append(result)
            measurements.append({"label": label, "seconds": seconds, "window": window,
                                 "fresh_identity_calls": len(calls),
                                 "comparison_form_cache": identity._short_name_forms.cache_info()._asdict()})
    elapsed = math.ceil((measurements[-1]["window"][1] - measurements[0]["window"][0]).total_seconds()) + 1
    for result, measured in zip(results, measurements):
        generated = result["sports_metrics"].pop("generated_at_madrid")
        same_evaluation(generated, generated, (measured["window"], measured["window"]))
    for result, measured in zip(results[1:], measurements[1:]):
        _same_calendar_tree(results[0], result, (measurements[0]["window"], measured["window"]), elapsed)
    assert len({item["fresh_identity_calls"] for item in measurements}) == 1
    assert measurements[0]["fresh_identity_calls"] > len(rows)
    assert results[0]["counts"]["visible"] == size * 3 // 4
    assert summary == original
    corrupted = deepcopy(results[-1])
    corrupted["matches"][0]["home_score"] = 99
    with pytest.raises(AssertionError):
        _same_calendar_tree(results[0], corrupted, (measurements[0]["window"], measurements[-1]["window"]), elapsed)
    corrupted = deepcopy(results[-1])
    corrupted["counts"]["visible"] += 1
    with pytest.raises(AssertionError):
        _same_calendar_tree(results[0], corrupted, (measurements[0]["window"], measurements[-1]["window"]), elapsed)
    for item in measurements:
        item.pop("window")
    print("TEXT_WORK_ABBA_COMPONENT " + json.dumps({"source_rows": len(rows), "visible": size * 3 // 4,
          "complete_context_equal": True, "measurements": measurements, "production_claim": False}))


def test_bounded_cache_retained_memory_observation():
    import tracemalloc
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    try:
        for number in range(4400):
            value = ("Synthetic team " + str(number) + " Atlético C.F. ").ljust(120, "x")
            competition.normalized(value)
            identity._name_forms(value)
        current, peak = tracemalloc.get_traced_memory()
        print("TEXT_WORK_MEMORY_OBSERVATION " + json.dumps({"net_traced_bytes": current - before,
              "process_traced_peak_bytes": peak, "scope": "synthetic bounded text cache, not Render RSS",
              "normalization_entries": competition._normalized_short_text.cache_info().currsize,
              "form_entries": identity._short_name_forms.cache_info().currsize}))
    finally:
        if not was_tracing:
            tracemalloc.stop()
