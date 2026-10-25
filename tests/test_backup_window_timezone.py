"""Pure backup-window tests: never import the runner, app, or job adapters."""
from __future__ import annotations

import ast
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest


ROOT = Path(os.environ.get("NEMESIS_PURE_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
MADRID = ZoneInfo("Europe/Madrid")
DATES = ("2026-01-15", "2026-07-15", "2026-03-29", "2026-10-25")
BOUNDARIES = (("04:29:59", False), ("04:30:00", True),
              ("06:29:59", True), ("06:30:00", False))


def load_backup_due(datetime_type=datetime):
    """Compile only literal window assignments and the one pure function."""
    source = ROOT / "tools" / "render_cron_master_tick.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and all(
            isinstance(target, ast.Name) and target.id.startswith("BACKUP_WINDOW_")
            for target in node.targets
        ):
            assert all(isinstance(part, (ast.Assign, ast.Name, ast.Store, ast.Constant,
                                        ast.BinOp, ast.Add, ast.Mult)) for part in ast.walk(node))
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "backup_due":
            selected.append(node)
    assert sum(isinstance(node, ast.FunctionDef) for node in selected) == 1
    namespace = {"datetime": datetime_type, "timezone": timezone, "ZoneInfo": ZoneInfo}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["backup_due"]


@pytest.mark.parametrize("day", DATES)
@pytest.mark.parametrize("clock,expected", BOUNDARIES)
def test_madrid_boundary(day, clock, expected):
    instant = datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=MADRID)
    utc_label = instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    assert load_backup_due()(utc_label) is expected


@pytest.mark.parametrize("day", DATES)
@pytest.mark.parametrize("clock,expected", BOUNDARIES)
def test_aware_input_offsets_represent_the_same_instant(day, clock, expected):
    instant = datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=MADRID)
    due = load_backup_due()
    for zone in (MADRID, timezone.utc, timezone(timedelta(hours=-5))):
        assert due(instant.astimezone(zone).isoformat()) is expected


@pytest.mark.parametrize("stamp", (
    "2026-03-29T00:59:59Z", "2026-03-29T01:00:00Z",
    "2026-10-25T00:59:59Z", "2026-10-25T01:00:00Z",
    "2026-10-25T02:30:00+02:00", "2026-10-25T02:30:00+01:00",
))
def test_dst_transition_instants_remain_outside_window(stamp):
    assert load_backup_due()(stamp) is False


@pytest.mark.parametrize("host_zone", (timezone.utc, MADRID, timezone(timedelta(hours=-5))))
@pytest.mark.parametrize("day", DATES)
@pytest.mark.parametrize("clock,expected", BOUNDARIES)
def test_naive_inputs_keep_prior_host_local_interpretation(host_zone, day, clock, expected):
    class SimulatedHostDatetime:
        @staticmethod
        def fromisoformat(value):
            parsed = datetime.fromisoformat(value)
            return parsed.replace(tzinfo=host_zone) if parsed.tzinfo is None else parsed

    instant = datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=MADRID)
    host_naive = instant.astimezone(host_zone).replace(tzinfo=None).isoformat()
    assert load_backup_due(SimulatedHostDatetime)(host_naive) is expected


@pytest.mark.parametrize("value", ("", "not-a-date", None, 0, "2026-13-01T04:30:00Z",
                                  "2026-10-25T25:00:00Z"))
def test_invalid_input_remains_false(value):
    assert load_backup_due()(value) is False


def test_original_four_summer_assertions_are_retained_and_pass():
    """Execute just the existing four assertions, without module imports."""
    source = ROOT / "tests" / "test_render_cron_master_tick.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    tests = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {"test_backup_window_is_utc_and_bounded",
                               "test_backup_window_is_madrid_and_bounded_in_summer"}]
    assert len(tests) == 1
    assert sum(isinstance(node, ast.Assert) for node in ast.walk(tests[0])) == 4
    namespace = {"master": SimpleNamespace(backup_due=load_backup_due())}
    exec(compile(ast.Module(body=tests, type_ignores=[]), str(source), "exec"), namespace)
    namespace[tests[0].name]()


def test_each_2026_day_keeps_exactly_the_two_hour_local_window():
    due = load_backup_due()
    first = datetime(2026, 1, 1)
    for offset in range(365):
        day = (first + timedelta(days=offset)).date().isoformat()
        for clock, expected in BOUNDARIES:
            instant = datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=MADRID)
            assert due(instant.astimezone(timezone.utc).isoformat()) is expected
