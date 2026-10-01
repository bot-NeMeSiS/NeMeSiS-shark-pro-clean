"""Allowlisted official API adapters, never general-purpose scraping or video downloads.

Metadata/docs verified 2026-10-01: https://www.thesportsdb.com/documentation
and https://www.api-football.com/documentation-v3 . Free TSDB responses may be
truncated; partial coverage is not success for missing metrics. Requests are
budgeted before network access, redirects are rejected and raw errors discarded.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import re
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from engines.postmatch_store import BudgetStopped, StaleLease

STAT_NAMES = {
    'total shots': ('shots_total', 'Tiros', 200, False),
    'shots on goal': ('shots_on_target', 'Tiros a puerta', 200, False),
    'shots off goal': ('shots_off_target', 'Tiros fuera', 200, False),
    'blocked shots': ('shots_blocked', 'Tiros bloqueados', 200, False),
    'ball possession': ('possession', 'Posesión', 100, True),
    'corner kicks': ('corners', 'Córners', 100, False),
    'fouls': ('fouls', 'Faltas', 200, False),
    'yellow cards': ('yellow_cards', 'Tarjetas amarillas', 50, False),
    'red cards': ('red_cards', 'Tarjetas rojas', 25, False),
    'offsides': ('offsides', 'Fueras de juego', 100, False),
    'goalkeeper saves': ('saves', 'Paradas', 200, False),
    'total passes': ('passes', 'Pases', 4000, False),
    'passes accurate': ('passes_accurate', 'Pases precisos', 4000, False),
}
BY_KEY = {value[0]: value for value in STAT_NAMES.values()}
REQUIRED = {'shots_total', 'shots_on_target', 'possession', 'corners', 'fouls', 'yellow_cards', 'red_cards'}


class SourceError(ValueError):
    """Closed error category. Never carry provider messages, credentials or bodies."""


def norm(value):
    text = unicodedata.normalize('NFKD', str(value or '')).casefold()
    return ''.join(c for c in text if c.isalnum())


def integer_id(value):
    raw = str(value or '').strip()
    return raw if re.fullmatch(r'[1-9][0-9]{0,14}', raw) else ''


def normalize_value(value, spec):
    if value is None or str(value).strip() in {'', '-', '—', 'null', 'None'}:
        return None
    raw = str(value).strip().rstrip('%')
    if isinstance(value, bool) or not re.fullmatch(r'\d+(?:\.\d{1,2})?', raw):
        raise SourceError('INVALID_STATISTIC')
    number = float(raw)
    if number > spec[2] or (not spec[3] and not number.is_integer()):
        raise SourceError('INVALID_STATISTIC')
    return format(number, 'g') + ('%' if spec[3] else '')


def validate_rows(rows):
    result = {}
    for row in rows:
        spec = STAT_NAMES.get(str(row.get('label') or '').strip().casefold())
        if not spec:
            continue  # No derived metrics (e.g. xG) relabelled as objective counts.
        value = {'key': spec[0], 'label': spec[1],
                 'home': normalize_value(row.get('home'), spec),
                 'away': normalize_value(row.get('away'), spec)}
        if value['home'] is None and value['away'] is None:
            continue
        if spec[0] in result and result[spec[0]] != value:
            raise SourceError('CONFLICTING_STATISTICS')
        result[spec[0]] = value
    for small, large in [('shots_on_target', 'shots_total'), ('passes_accurate', 'passes')]:
        for side in ('home', 'away'):
            left, right = result.get(small, {}).get(side), result.get(large, {}).get(side)
            if left is not None and right is not None and float(left) > float(right):
                raise SourceError('INCONSISTENT_STATISTICS')
    possession = result.get('possession', {})
    if possession.get('home') is not None and possession.get('away') is not None:
        if abs(float(possession['home'][:-1]) + float(possession['away'][:-1]) - 100) > 1:
            raise SourceError('INCONSISTENT_STATISTICS')
    return list(result.values())


def match_date(match):
    return str(match.get('match_date') or '')[:10]


def match_event(match, event):
    """Cross-source identity requires exact names AND date AND competition.

    A provider ID is not evidence that a previously mapped event is still the
    same date/team pair. Ambiguous aliases go to review rather than fuzzy match.
    """
    if not isinstance(event, dict):
        return False
    if (norm(match.get('home_team')), norm(match.get('away_team'))) != (
            norm(event.get('strHomeTeam')), norm(event.get('strAwayTeam'))):
        return False
    expected_date = match_date(match)
    observed_date = str(event.get('dateEvent') or '')[:10]
    # SportsDB UTC evening fixtures can move to the next Madrid calendar date.
    clock = event.get('strTimestamp')
    if clock:
        try:
            dt = datetime.fromisoformat(str(clock).replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)  # API timestamp documented UTC, not manual data.
            observed_date = dt.astimezone(ZoneInfo('Europe/Madrid')).date().isoformat()
        except ValueError:
            return False
    if not expected_date or observed_date != expected_date:
        return False
    source = norm(match.get('source'))
    if 'sportsdb' in source and match.get('league_id') and event.get('idLeague'):
        return str(match['league_id']) == str(event['idLeague'])
    names = [match.get('competition_name'), match.get('league_name'), match.get('league')]
    return any(norm(name) == norm(event.get('strLeague')) for name in names if name) and bool(event.get('strLeague'))


def final_scope(status):
    label = str(status or '').strip().upper()
    if label in {'FT', 'MATCH FINISHED', 'FINISHED', 'FINAL', 'FINALIZADO'}:
        return 'REGULATION'
    if label in {'AET', 'PEN', 'AFTER EXTRA TIME', 'AFTER PENALTIES'}:
        return 'INCLUDING_EXTRA_TIME'
    raise SourceError('SOURCE_NOT_FINAL')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceError('REDIRECT_BLOCKED')


class OfficialSources:
    def __init__(self, store, job, config, *, deadline, clock=time.time, transport=None):
        self.store, self.job, self.config = store, job, config
        self.deadline, self.clock = deadline, clock
        self.transport = transport or self._http
        self.calls = 0
        self.cache = {}

    @staticmethod
    def _http(request, timeout):
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            data = response.read(524289)
            if len(data) > 524288:
                raise SourceError('MALFORMED')
            return json.loads(data.decode('utf-8'))

    def request(self, provider, endpoint, params):
        allowed = {'thesportsdb': {'lookupevent.php', 'eventsday.php', 'lookupeventstats.php'},
                   'api_football': {'fixtures', 'fixtures/statistics'}}
        if provider not in self.config['sources'] or endpoint not in allowed.get(provider, set()):
            raise SourceError('SOURCE_NOT_ALLOWED')
        if self.calls >= 6 or self.clock() >= self.deadline - .5:
            raise BudgetStopped('TICK_BUDGET')
        if provider == 'thesportsdb':
            key = (os.getenv('THESPORTSDB_KEY') or os.getenv('THESPORTSDB_API_KEY') or '').strip()
            if not key:
                raise SourceError('MISSING_KEY')
            base = 'https://www.thesportsdb.com/api/v1/json/' + urllib.parse.quote(key, safe='') + '/'
            headers = {}
        else:
            from engines.api_sports_provider_engine import _provider_key, usage_guard
            key = _provider_key()
            if not key:
                raise SourceError('MISSING_KEY')
            if not usage_guard()['network_enabled'] or os.getenv('ENABLE_API_FOOTBALL_PROVIDER', 'true').lower() in {'0', 'false', 'off'}:
                raise SourceError('SOURCE_DISABLED')
            base = 'https://v3.football.api-sports.io/'
            headers = {'x-apisports-key': key}
        cache_key = (provider, endpoint, tuple(sorted(params.items())))
        if cache_key in self.cache:
            return self.cache[cache_key]
        self.store.reserve(provider, self.job, self.clock(), self.config['daily_limit'])
        self.calls += 1
        req = urllib.request.Request(base + endpoint + '?' + urllib.parse.urlencode(params),
                headers={**headers, 'Accept': 'application/json', 'User-Agent': 'NeMeSiS-Postmatch/1.0'})
        try:
            payload = self.transport(req, min(4.0, max(.1, self.deadline - self.clock())))
            if not isinstance(payload, dict):
                raise SourceError('MALFORMED')
            if payload.get('errors') or payload.get('error'):
                raw = json.dumps(payload.get('errors') or payload.get('error')).lower()[:1000]
                reason = 'RATE_LIMIT' if any(t in raw for t in ('quota','limit','429')) else 'ACCESS_DENIED'
                raise SourceError(reason)
            self.cache[cache_key] = payload
            self.store.circuit(provider, False, '', self.clock())
            return payload
        except (BudgetStopped, StaleLease):
            raise
        except Exception as exc:
            code = getattr(exc, 'code', None)
            reason = 'RATE_LIMIT' if code == 429 else 'ACCESS_DENIED' if code in {401, 403} else (
                     str(exc) if isinstance(exc, SourceError) else 'MALFORMED' if isinstance(exc, (ValueError, UnicodeError)) else 'NETWORK')
            self.store.circuit(provider, True, reason, self.clock())
            raise SourceError(reason if reason in {'RATE_LIMIT','ACCESS_DENIED','MALFORMED','REDIRECT_BLOCKED'} else 'NETWORK') from None

    def identities(self, match):
        sid, fid = '', ''
        ext, source = str(match.get('external_id') or ''), norm(match.get('source'))
        if ext.startswith('sportsdb-'):
            sid = integer_id(ext.removeprefix('sportsdb-'))
        elif 'sportsdb' in source:
            sid = integer_id(ext)
        if ext.startswith(('api-football-', 'api_football_')):
            fid = integer_id(re.sub(r'^api[-_]football[-_]', '', ext))
        elif 'apifootball' in source or 'apisports' in source:
            fid = integer_id(match.get('fixture_id') or ext)
        # Read provider-qualified persisted mappings, never interpret an arbitrary numeric local ID.
        with self.store.connection() as conn:
            for table, field in [('sportsdb_event_profiles','sportsdb_event_id'), ('api_football_live_snapshots','fixture_id')]:
                try:
                    rows = conn.execute(f'SELECT {field} FROM {table} WHERE match_id=? LIMIT 2', (str(match['id']),)).fetchall()
                except sqlite3.OperationalError as exc:
                    if 'no such table' in str(exc):
                        continue
                    raise
                if len(rows) == 1:
                    value = integer_id(rows[0][0])
                    if table.startswith('sportsdb'):
                        sid = sid or value
                    else:
                        fid = fid or value
        return sid, fid

    def sportsdb_event(self, match):
        sid, fid = self.identities(match)
        if sid:
            payload = self.request('thesportsdb', 'lookupevent.php', {'id': sid})
        else:
            # Exact dated discovery, capped by provider response and the worker's request budget.
            payload = self.request('thesportsdb', 'eventsday.php', {'d': match_date(match), 's': 'Soccer'})
        events = payload.get('events')
        if events is None:
            return None
        if not isinstance(events, list) or len(events) > 1500:
            raise SourceError('MALFORMED')
        found = [e for e in events if match_event(match, e) and
                 (not sid or str(e.get('idEvent')) == sid) and
                 (not fid or not e.get('idAPIfootball') or str(e['idAPIfootball']) == fid)]
        if len(found) > 1:
            raise SourceError('AMBIGUOUS_MATCH')
        if not found:
            if sid and events:
                raise SourceError('IDENTITY_MISMATCH')
            return None
        return found[0]

    def statistics(self, match):
        observations, reasons = [], []
        _, fid = self.identities(match)
        # Existing primary first; public metadata fallback second. Failures are isolated.
        for provider in ('api_football', 'thesportsdb'):
            if provider not in self.config['sources']:
                continue
            try:
                if provider == 'api_football':
                    if not fid:
                        reasons.append('MISSING_PROVIDER_ID'); continue
                    payload = self.request(provider, 'fixtures', {'id': fid})
                    fixtures = payload.get('response')
                    if not isinstance(fixtures, list) or len(fixtures) != 1:
                        raise SourceError('IDENTITY_MISMATCH')
                    event = fixtures[0]
                    fixture, teams, league = event.get('fixture') or {}, event.get('teams') or {}, event.get('league') or {}
                    mapped = {'strHomeTeam': (teams.get('home') or {}).get('name'), 'strAwayTeam': (teams.get('away') or {}).get('name'),
                              'dateEvent': str(fixture.get('date') or '')[:10], 'strTimestamp': fixture.get('date'),
                              'strLeague': league.get('name')}
                    if str(fixture.get('id')) != fid or not match_event(match, mapped):
                        raise SourceError('IDENTITY_MISMATCH')
                    scope = final_scope((fixture.get('status') or {}).get('short'))
                    expected_ids = {str((teams.get(side) or {}).get('id')): side for side in ('home','away')}
                    if len(expected_ids) != 2 or 'None' in expected_ids:
                        raise SourceError('IDENTITY_MISMATCH')
                    stats = self.request(provider, 'fixtures/statistics', {'fixture': fid}).get('response')
                    if not isinstance(stats, list):
                        raise SourceError('MALFORMED')
                    grouped, seen = {}, set()
                    for team in stats:
                        team_id = str((team.get('team') or {}).get('id'))
                        if team_id not in expected_ids or team_id in seen:
                            raise SourceError('IDENTITY_MISMATCH')
                        seen.add(team_id)
                        for stat in team.get('statistics') or []:
                            label = str(stat.get('type') or '').casefold()
                            row = grouped.setdefault(label, {'label': label})
                            side = expected_ids[team_id]
                            if side in row and row[side] != stat.get('value'):
                                raise SourceError('CONFLICTING_STATISTICS')
                            row[side] = stat.get('value')
                    rows, ref = validate_rows(grouped.values()), 'api-football:fixture:' + fid
                else:
                    event = self.sportsdb_event(match)
                    if not event:
                        reasons.append('NO_EVENT'); continue
                    sid = integer_id(event.get('idEvent'))
                    if not sid:
                        raise SourceError('IDENTITY_MISMATCH')
                    scope = final_scope(event.get('strStatus'))
                    stats = self.request(provider, 'lookupeventstats.php', {'id': sid}).get('eventstats')
                    if stats is None:
                        stats = []
                    if not isinstance(stats, list):
                        raise SourceError('MALFORMED')
                    if any(not isinstance(s, dict) or str(s.get('idEvent')) != sid for s in stats):
                        raise SourceError('IDENTITY_MISMATCH')
                    rows = validate_rows({'label': s.get('strStat'), 'home': s.get('intHome'), 'away': s.get('intAway')} for s in stats)
                    ref = 'thesportsdb:event:' + sid
                if rows:
                    observations.append({'source': provider, 'reference': ref, 'scope': scope, 'items': rows, 'observed_at': self.clock()})
                else:
                    reasons.append('NO_STATISTICS')
            except (SourceError, BudgetStopped) as exc:
                reasons.append(str(exc))
        return {'observations': observations, 'reasons': reasons, 'external_calls': self.calls}

    def highlights(self, match):
        from engines.highlight_url_engine import public_https_url
        if 'thesportsdb' not in self.config['sources']:
            return {'event': None, 'reasons': ['SOURCE_NOT_ALLOWED'], 'external_calls': 0}
        try:
            event = self.sportsdb_event(match)
            # Link acquisition is metadata only. Approval always remains with the existing rights guard.
            if not event or not public_https_url(event.get('strVideo')):
                return {'event': None, 'reasons': ['NO_VIDEO'], 'external_calls': self.calls}
            final_scope(event.get('strStatus'))
            return {'event': event, 'reasons': [], 'external_calls': self.calls}
        except (SourceError, BudgetStopped) as exc:
            return {'event': None, 'reasons': [str(exc)], 'external_calls': self.calls}
