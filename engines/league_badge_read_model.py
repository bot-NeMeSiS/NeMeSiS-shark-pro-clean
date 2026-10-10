"""Safe badge references and read-only access to already-cached league profiles.

No network access, schema creation, download or cache write occurs here.
"""
from collections.abc import Mapping
import sqlite3
from urllib.parse import urlsplit

from engines.crest_engine import normalize_logo_key


def badge_url(value):
    text = str(value or '').strip()
    if not text or len(text) > 2048 or any(ord(c) < 32 for c in text) or '\\' in text:
        return ''
    try:
        parsed = urlsplit(text)
        if parsed.username or parsed.password:
            return ''
        if parsed.scheme == 'https' and parsed.hostname:
            return text
        if not parsed.scheme and not parsed.netloc and parsed.path.startswith('/static/') and '..' not in parsed.path.split('/'):
            return text
    except ValueError:
        pass
    return ''


def match_badge(match):
    # Never use a generic match logo, home badge or event artwork as a league badge.
    for key in ('competition_logo', 'league_logo', 'competition_logo_url', 'league_logo_url'):
        candidate = badge_url(match.get(key))
        if candidate:
            return candidate
    for key in ('league', 'competition'):
        item = match.get(key)
        if isinstance(item, Mapping):
            for field in ('logo_url', 'logo', 'badge_url', 'strBadge'):
                candidate = badge_url(item.get(field))
                if candidate:
                    return candidate
    return ''


def cached_profile_badge(conn, *, name='', country='', provider='', league_id=''):
    """Find a SportsDB badge by its scoped ID or unambiguous name + country.

    IDs from other providers cannot be interpreted as SportsDB IDs. With no
    profile or a missing/locked table, callers keep their visible fallback.
    """
    if conn is None:
        return ''
    try:
        family = normalize_logo_key(provider)
        if league_id and 'sportsdb' in family:
            rows = conn.execute('SELECT league_name,country,badge_url,logo_url FROM sportsdb_league_profiles WHERE sportsdb_league_id=? LIMIT 2', (str(league_id),)).fetchall()
        elif name and country:
            rows = conn.execute('SELECT league_name,country,badge_url,logo_url FROM sportsdb_league_profiles WHERE league_name=? COLLATE NOCASE OR alternate_name=? COLLATE NOCASE LIMIT 10', (str(name), str(name))).fetchall()
        else:
            return ''
        if country:
            # Same localization as the canonical competition surface; pure, no IO.
            from engines.spanish_localization_engine import spanish_country_name
            expected = normalize_logo_key(spanish_country_name(country))
            rows = [row for row in rows if normalize_logo_key(spanish_country_name(row[1])) == expected]
        if len(rows) == 1:
            return badge_url(rows[0][2]) or badge_url(rows[0][3])
    except (sqlite3.Error, TypeError, ValueError):
        pass
    return ''
