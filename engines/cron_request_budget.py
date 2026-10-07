"""Cooperative provider deadline for a single Cron HTTP request.

Context-local: never changes provider plans or other concurrent requests.
Reserve time for persistence and response construction below Gunicorn's 30s.
"""
from contextvars import ContextVar
import time

_CURRENT = ContextVar('cron_request_budget', default=None)


class CronTimeBudget(RuntimeError):
    def __init__(self, message='TIME_BUDGET', *, external_calls=0):
        super().__init__(message)
        self.external_calls = max(0, int(external_calls))


class CronRequestBudget:
    def __init__(self, seconds=16, clock=None):
        self.clock = clock or time.monotonic
        self.deadline = self.clock() + seconds
        self.deferred = False

    def __enter__(self):
        self.parent = _CURRENT.get()
        self.token = _CURRENT.set(self)
        return self

    def __exit__(self, *args):
        _CURRENT.reset(self.token)

    def remaining(self):
        own_remaining = max(0, self.deadline - self.clock())
        parent = getattr(self, 'parent', None)
        return min(own_remaining, parent.remaining()) if parent is not None else own_remaining


def exhausted():
    scope = _CURRENT.get()
    if scope is not None and scope.remaining() < .25:
        scope.deferred = True
        return True
    return False


def request_timeout(default):
    scope = _CURRENT.get()
    if scope is None:
        return default
    if exhausted():
        raise CronTimeBudget('TIME_BUDGET')
    return min(float(default), 4., scope.remaining())


def sqlite_busy_timeout(default_ms):
    """Keep lock contention below the Cron transport deadline, without changing other jobs."""
    scope = _CURRENT.get()
    if scope is None:
        return default_ms
    if exhausted():
        raise CronTimeBudget('TIME_BUDGET')
    return max(1, min(int(default_ms), 500, int(scope.remaining() * 1000)))
