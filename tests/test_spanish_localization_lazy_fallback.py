"""Presentation fallbacks are lazy, without caching identity or catalog values."""
from copy import deepcopy

import pytest

from engines import spanish_localization_engine as localization


HELPERS = (
    ("spanish_team_name", "SPANISH_TEAM_OVERRIDES"),
    ("spanish_country_name", "SPANISH_COUNTRY_OVERRIDES"),
)
CATALOG_CASES = [
    (function, registry, key, expected)
    for function, registry in HELPERS
    for key, expected in sorted(getattr(localization, registry).items())
]


@pytest.mark.parametrize("function,registry,key,expected", CATALOG_CASES)
def test_every_existing_override_preserves_its_exact_output(function, registry, key, expected):
    helper = getattr(localization, function)
    catalog = getattr(localization, registry)
    before = deepcopy(catalog)
    for value in (key, "  " + key.upper() + "  ", key.replace(" ", "-")):
        assert helper(value) == expected
    assert catalog == before


@pytest.mark.parametrize("function,registry", HELPERS)
def test_mapped_values_do_not_evaluate_unused_regex_fallback(function, registry, monkeypatch):
    helper = getattr(localization, function)
    original = localization._title_preserving_acronyms
    calls = []

    def observe(value):
        calls.append(value)
        return original(value)

    monkeypatch.setattr(localization, "_title_preserving_acronyms", observe)
    assert helper("  SPAIN  ") == "España"
    assert helper("México") == "México"
    assert calls == []
    # Positive control: the same observer sees real work for a missing entry.
    assert helper("Atletico Harbor") == "Atlético Harbor"
    assert calls == ["Atletico Harbor"]


@pytest.mark.parametrize("function,registry", HELPERS)
@pytest.mark.parametrize("value,expected", [
    ("Atletico Harbor", "Atlético Harbor"),
    ("Mexico City FC", "México City FC"),
    ("Copa America Regional", "Copa América Regional"),
    ("Division Norte", "División Norte"),
    ("Brasileirao Serie Z", "Brasileirão Serie Z"),
    ("Harbor U19 Women", "Harbor U19 Women"),
    ("Harbor II", "Harbor II"),
    ("Unknown_Country", "Unknown_Country"),
    (1378, "1378"),
    (1378.5, "1378.5"),
    (True, "True"),
])
def test_unmapped_values_keep_original_fallback_once(function, registry, value, expected, monkeypatch):
    raw = str(value or "").strip()
    assert localization._norm(raw) not in getattr(localization, registry)
    original = localization._title_preserving_acronyms
    calls = []

    def observe(text):
        calls.append(text)
        return original(text)

    monkeypatch.setattr(localization, "_title_preserving_acronyms", observe)
    assert getattr(localization, function)(value) == expected
    assert calls == [raw]


@pytest.mark.parametrize("function,registry", HELPERS)
@pytest.mark.parametrize("value", [None, "", " \t\r\n", False, 0, 0.0])
def test_empty_values_do_not_normalize_or_render(function, registry, value, monkeypatch):
    def unexpected(_value):
        raise AssertionError("empty value entered normalization or fallback")

    monkeypatch.setattr(localization, "_norm", unexpected)
    monkeypatch.setattr(localization, "_title_preserving_acronyms", unexpected)
    assert getattr(localization, function)(value) == ""


@pytest.mark.parametrize("function,registry", HELPERS)
def test_runtime_catalog_changes_remain_visible_without_cache(function, registry, monkeypatch):
    helper = getattr(localization, function)
    catalog = getattr(localization, registry)
    assert helper("Spain") == "España"
    monkeypatch.setitem(catalog, "spain", "Synthetic replacement")
    assert helper("Spain") == "Synthetic replacement"
    monkeypatch.setitem(catalog, "spain", "")
    assert helper("Spain") == ""
    monkeypatch.setitem(catalog, "spain", None)
    assert helper("Spain") is None
    monkeypatch.delitem(catalog, "spain")
    assert helper("Spain") == "Spain"


@pytest.mark.parametrize("function,registry", HELPERS)
def test_nonprimitive_input_is_converted_once(function, registry):
    calls = []

    class Label:
        def __bool__(self):
            calls.append("bool")
            return True

        def __str__(self):
            calls.append("str")
            return "  Spain  "

    assert getattr(localization, function)(Label()) == "España"
    assert calls == ["bool", "str"]


@pytest.mark.parametrize("function,registry", HELPERS)
def test_input_conversion_error_is_not_hidden(function, registry):
    marker = RuntimeError("synthetic label conversion failure")

    class Label:
        def __str__(self):
            raise marker

    with pytest.raises(RuntimeError) as captured:
        getattr(localization, function)(Label())
    assert captured.value is marker
