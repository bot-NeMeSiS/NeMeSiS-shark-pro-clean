"""Nested jobs cannot extend their containing HTTP request deadline."""
import pytest

from engines.cron_request_budget import CronRequestBudget, CronTimeBudget, request_timeout


def test_inner_job_cannot_restart_parent_deadline():
    now = [0.0]
    with CronRequestBudget(seconds=16, clock=lambda: now[0]):
        now[0] = 15.5
        with CronRequestBudget(seconds=12, clock=lambda: now[0]) as child:
            assert request_timeout(6) == .5
            now[0] = 16
            with pytest.raises(CronTimeBudget, match='TIME_BUDGET'):
                request_timeout(6)
            assert child.deferred
    assert request_timeout(6) == 6


def test_child_can_be_shorter_and_restores_parent_after_exception():
    parent_clock = [100.0]
    child_clock = [0.0]
    with CronRequestBudget(seconds=16, clock=lambda: parent_clock[0]):
        with pytest.raises(ValueError):
            with CronRequestBudget(seconds=2, clock=lambda: child_clock[0]):
                assert request_timeout(6) == 2
                child_clock[0] = 1.5
                assert request_timeout(6) == .5
                raise ValueError('test')
        assert request_timeout(6) == 4


def test_three_nested_jobs_honor_oldest_deadline():
    now = [0.0]
    with CronRequestBudget(seconds=2, clock=lambda: now[0]):
        with CronRequestBudget(seconds=8, clock=lambda: now[0]):
            with CronRequestBudget(seconds=12, clock=lambda: now[0]):
                now[0] = 1.75
                assert request_timeout(6) == .25
                now[0] = 1.8
                with pytest.raises(CronTimeBudget):
                    request_timeout(6)
