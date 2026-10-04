"""Bounded SportsDB calls within an existing sync, not a new worker.

No persistent payload cache: an old response must never refresh a live clock.
Official docs (verified 2026-10-01): /documentation, Premium highlights limit 50,
optional league filter `l`. Limits below are per operation, NOT account-wide.
"""
from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import json
import time
import urllib.error

_CURRENT = ContextVar('sportsdb_request_budget', default=None)


class SportsDBStopped(RuntimeError):
    """Closed reason only; never includes a URL, key or provider body."""


def closed_error(exc):
    from engines.cron_request_budget import CronTimeBudget
    if isinstance(exc, CronTimeBudget):
        return "TIME_BUDGET"
    if isinstance(exc, SportsDBStopped):
        return str(exc) if str(exc) in {'TIME_BUDGET', 'REQUEST_BUDGET', 'MEDIA_BUDGET', 'MALFORMED', 'PROVIDER_ERROR', 'RATE_LIMIT', 'ACCESS_DENIED', 'NETWORK'} else 'PROVIDER_ERROR'
    code = getattr(exc, 'code', None)
    if code == 429:
        return 'RATE_LIMIT'
    if code in (401, 403):
        return 'ACCESS_DENIED'
    if isinstance(exc, (json.JSONDecodeError, UnicodeError, ValueError, TypeError)):
        return 'MALFORMED'
    return 'NETWORK'


def request_timeout(default=12):
    """Transport timeout is capped by the remaining cooperative deadline."""
    scope = _CURRENT.get()
    if scope is None:
        return default
    remaining = scope.remaining()
    if remaining < .1:
        raise SportsDBStopped('TIME_BUDGET')
    return min(float(default), 4.0, remaining)


class SportsDBBudget:
    def __init__(self, *, max_calls=12, max_seconds=18, clock=None, before_call=None):
        self.clock = clock or time.monotonic
        self.max_calls = max(1, min(int(max_calls), 20))
        self.deadline = self.clock() + max(1, min(float(max_seconds), 20))
        self.calls = 0
        self.cache_hits = 0
        self.cache = {}
        self.stopped = ''
        self._token = None
        self.before_call = before_call

    def remaining(self):
        return max(0., self.deadline - self.clock())

    def __enter__(self):
        self._token = _CURRENT.set(self)
        return self

    def __exit__(self, *args):
        _CURRENT.reset(self._token)

    def call(self, version, endpoint, params, fetch):
        if self.stopped:
            raise SportsDBStopped(self.stopped)
        if self.remaining() < .1:
            self.stopped = 'TIME_BUDGET'
            raise SportsDBStopped(self.stopped)
        key = (version, endpoint, tuple(sorted((params or {}).items())))
        if key in self.cache:
            self.cache_hits += 1
            return deepcopy(self.cache[key])
        if self.calls >= self.max_calls:
            self.stopped = 'REQUEST_BUDGET'
            raise SportsDBStopped(self.stopped)
        if self.before_call:
            self.before_call()
        self.calls += 1
        try:
            result = fetch()
            if not isinstance(result, dict):
                raise SportsDBStopped('MALFORMED')
            if result.get('error') or result.get('errors'):
                raise SportsDBStopped('PROVIDER_ERROR')
            self.cache[key] = deepcopy(result)
            return result
        except Exception as exc:
            reason = closed_error(exc)
            self.stopped = reason
            raise SportsDBStopped(reason) from None

    def metrics(self):
        return {'external_calls': self.calls, 'cache_hits': self.cache_hits,
                'request_limit': self.max_calls, 'stop_reason': self.stopped,
                'budget_scope': 'THIS_OPERATION_NOT_ACCOUNT_QUOTA'}


def fetch_feed(*, v1, v2, today, leagues, live_enabled, limit, prioritize,
               slug, collect, priority_external_ids=None, budget=None):
    """Prioritize live acquisition before league fanout, retaining latest-live precedence."""
    events, live, errors = [], [], []
    scope = budget or SportsDBBudget(max_calls=10)
    limit = max(1, min(int(limit), 1500))

    def take(version, endpoint, params=None):
        fetch = (lambda: v1(endpoint, params)) if version == 1 else (lambda: v2(endpoint))
        return scope.call(version, endpoint, params, fetch)

    def rows(payload, label):
        return [(item, {'key': slug(item.get('strLeague') or label),
                        'name': item.get('strLeague') or 'Soccer',
                        'country': item.get('strCountry') or ''}) for item in collect(payload)]

    with scope:
        try:
            events.extend(rows(take(1, 'eventsday.php', {'d': today, 's': 'Soccer'}), 'sportsdb-day'))
            if live_enabled:
                live.extend(rows(take(2, 'livescore/soccer'), 'sportsdb-live'))
            for league in leagues:
                if len(events) >= limit:
                    break
                payload = take(1, 'eventsnextleague.php', {'id': league['id']})
                events.extend((item, league) for item in collect(payload))
        except SportsDBStopped as exc:
            errors.append(str(exc))
    selected = prioritize(events + live, limit=limit, priority_external_ids=priority_external_ids)
    return selected, errors, scope.calls
