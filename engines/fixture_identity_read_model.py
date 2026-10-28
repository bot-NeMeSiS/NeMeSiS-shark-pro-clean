"""Conservative presentation identity over verified canonical contexts.

A caller-prepared RESOLVED competition reference is mandatory across providers.
The only exception is independently verified observations of the exact same
native fixture inside one known provider. Display labels and real country text
never establish that proof. This module performs no reference reads itself.

The caller supplies its existing kickoff parser and row preference. No record is
edited, persisted, combined or fetched: a successful match selects one original
row, keeping its prices, scores, links and provenance together.

Names are compared only inside an explicit country/competition/kickoff scope and
as an ordered home/away pair. Club designators and optional Real/Deportivo prefixes
are comparison aids here, never global team identities. Category markers, strong
ID conflicts and incompatible final results remain separate. Unknown aliases and
ambiguous components deliberately stay visible; this is not a database merge or a
claim that arbitrary names identify the same club worldwide.

An existing SportsDB idAPIfootball can bridge a non-structural alias only when
both original provider payloads match their own event, ordered team and league
IDs, and at least one team is independently recognizable on the same side.
Mappings with two unknown team aliases therefore remain unresolved.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import combinations, product
import json
import hashlib
from math import isfinite
import re
from zoneinfo import ZoneInfo

from engines.competition_read_model import normalized, season_key
from engines.canonical_competition_context import _namespace as provider_family
from engines.match_sync_engine import IMPORTANT_COMPETITIONS
from engines.spanish_localization_engine import (
    provider_competition_facts,
    spanish_competition_name,
    spanish_country_name,
    spanish_team_name,
)
from engines.team_identity_engine import provider_team_identity_key
from engines.realtime_state_engine import _provider_clock, older_match_observation

_MADRID = ZoneInfo("Europe/Madrid")
_MAX_NAMES = 8
_MAX_POSTING = 64
_UNKNOWN = {"", "unknown", "desconocido", "pendiente", "tbd", "none", "null",
            "equipo", "equipo local", "equipo visitante", "local", "visitante",
            "home", "away", "competicion", "competition", "sin competicion"}
_CLUB_DESIGNATORS = (
    ("club", "de", "futbol"), ("club", "de", "football"),
    ("football", "club"), ("futbol", "club"), ("club", "deportivo"),
    ("f", "c"), ("c", "f"), ("c", "d"), ("u", "d"),
    ("s", "d"), ("a", "c"), ("s", "c"),
    ("fc",), ("cf",), ("cd",), ("ud",), ("sd",), ("ac",),
    ("sc",), ("afc",), ("club",),
)
_PREFIXES = {"real", "deportivo"}
_AGE = re.compile(r"\b(?:u|under|sub)\s*(\d{1,2})\b")
_WOMEN = re.compile(r"\b(?:w|women|woman|ladies|female|femenino|femenina|feminino|feminina)\b")
_MEN = re.compile(r"\b(?:men|male|masculino|masculina)\b")
_RESERVE = re.compile(r"\b(?:b|c|ii|iii|iv|reserves?|reservas?|youth|juvenil|juveniles|academy|academia)\b")
_TERMINAL = {"ft", "finished", "final", "finalizado", "match finished", "full time",
             "aet", "pen", "after extra time", "after penalties"}
_SPORTSDB_COMPETITIONS = {
    item["sportsdb_id"]: item for item in IMPORTANT_COMPETITIONS if item.get("sportsdb_id")
}


def _text(value):
    return "" if value is None else str(value).strip()


def _words(value):
    return normalized(value).replace("-", " ")


def _category(value):
    """Return category evidence plus the name without those same markers."""
    # These exact primitive values normalize to the empty string. Do not call
    # bool on arbitrary objects here: the original normalizer owns that behavior.
    if value is None or (type(value) in (str, int, float, bool) and not value):
        return frozenset(), ""
    text = _words(value)
    if not text:
        return frozenset(), ""
    markers = set()
    for age in _AGE.findall(text):
        markers.add("age:" + str(int(age)))
    text = _AGE.sub(" ", text)
    if _WOMEN.search(text):
        markers.add("gender:female")
    if _MEN.search(text):
        markers.add("gender:male")
    text = _WOMEN.sub(" ", _MEN.sub(" ", text))
    for reserve in _RESERVE.findall(text):
        marker = "reserves" if reserve in {"reserve", "reserves", "reserva", "reservas"} else reserve
        markers.add("category:" + marker)
    text = _RESERVE.sub(" ", text)
    return frozenset(markers), " ".join(text.split())


def _name_forms(value):
    # Reuse the existing curated provider aliases and Spanish translations.
    key = provider_team_identity_key(spanish_team_name(value))
    # Punctuation normalization makes C.F. into "c f". Recover the known
    # designator before detecting category C, so C.F. B still means reserve B.
    key = re.sub(r"\b(?:f c|c f|c d|u d|s d|a c|s c)\b",
                 lambda match: match.group(0).replace(" ", ""), key)
    category, key = _category(key)
    tokens = tuple(key.split())
    changed = True
    while tokens and changed:
        changed = False
        for designator in _CLUB_DESIGNATORS:
            size = len(designator)
            if tokens[:size] == designator:
                tokens, changed = tokens[size:], True
                break
            if tokens[-size:] == designator:
                tokens, changed = tokens[:-size], True
                break
    full = " ".join(tokens)
    short_tokens = tokens
    while short_tokens and short_tokens[0] in _PREFIXES:
        short_tokens = short_tokens[1:]
    short = " ".join(short_tokens)
    if full in _UNKNOWN or short in _UNKNOWN or len(short) < 2:
        return None
    return category, full, short


def _scoped_id(value, provider):
    text = _text(value)
    parts = text.split(":", 2)
    if len(parts) == 3 and parts[1] == "team":
        return provider_family(parts[0]), parts[2]
    return provider, text


@dataclass(frozen=True)
class _Team:
    names: tuple
    category: frozenset
    ids: dict
    canonical: str
    # One fresh _team derivation may reuse its own exact immutable source label
    # when checking that same label inside the original provider payload. These
    # are not identities, comparison fields, or a cache across rows/consumers.
    source_label: str | None = field(default=None, repr=False, compare=False)
    source_label_forms: tuple | None = field(default=None, repr=False, compare=False)


def _team(row, side, provider):
    raw = row.get(side + "_team")
    nested = raw if isinstance(raw, Mapping) else row.get(side + "_team_entity")
    nested = nested if isinstance(nested, Mapping) else {}
    label = (row.get("_raw_" + side + "_team") or nested.get("official_name")
             or nested.get("display_name") or nested.get("name") or raw
             or row.get(side + "_team_name"))
    initial = _name_forms(label)
    if initial is None:
        return None
    category = set(initial[0])
    for key in ("gender", "category", "age_group"):
        for value in (row.get(side + "_" + key), row.get(side + "_team_" + key),
                      nested.get(key), row.get(key)):
            category.update(_category(value)[0])
    names = [initial[1:]]
    aliases = row.get(side + "_team_aliases") or nested.get("aliases") or []
    if isinstance(aliases, str):
        aliases = re.split(r"[|;]", aliases)
    if isinstance(aliases, (tuple, list)):
        for alias in aliases[:_MAX_NAMES - 1]:
            forms = _name_forms(alias)
            if forms and forms[0] == initial[0] and forms[1:] not in names:
                names.append(forms[1:])
    ids = {}

    def add(value, source):
        family, identifier = _scoped_id(value, source)
        if not identifier or not family:
            return True
        if family in ids and ids[family] != identifier:
            return False
        ids[family] = identifier
        return True

    if not add(row.get(side + "_team_id") or nested.get("provider_team_id"), provider):
        return None
    supplied = row.get(side + "_provider_team_ids") or nested.get("provider_team_ids") or {}
    if isinstance(supplied, Mapping):
        for source, identifier in supplied.items():
            if not add(identifier, provider_family(source)):
                return None
    canonical = _text(row.get(side + "_canonical_team_id") or nested.get("canonical_team_id"))
    if ":team:" in canonical:
        if not add(canonical, provider):
            return None
        canonical = ""  # A provider namespace alone is not a cross-provider mapping.
    return _Team(tuple(names), frozenset(category), ids, canonical,
                 source_label=label if type(label) is str else None,
                 source_label_forms=initial if type(label) is str else None)


def _explicit_kickoff(row):
    for key in ("kickoff_iso", "commence_time", "kickoff_iso_madrid", "madrid_dt_iso"):
        if re.match(r"^\d{4}-\d{2}-\d{2}[T\s]\d{1,2}:\d{2}", _text(row.get(key))):
            return True
    day = _text(row.get("match_date"))
    clock = _text(row.get("kickoff_time") or row.get("match_time") or row.get("time"))
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}(?:$|[T\s])", day)
                and re.match(r"^\d{1,2}:\d{2}(?::\d{2})?$", clock))


def _sport(value):
    key = _words(value)
    return "football" if key in {"soccer", "association football", "football", "futbol"} else key


def _competition_label(row, value, country):
    """Existing provider league IDs outrank differences in their display labels."""
    if provider_family(row.get("source") or row.get("provider")) == "sportsdb":
        registered = _SPORTSDB_COMPETITIONS.get(_text(row.get("competition_id") or row.get("league_id")))
        if registered and _words(spanish_country_name(registered["country"])) == country:
            return _words(spanish_competition_name(registered["name"]))
    return _words(spanish_competition_name(value))


def _final_score(row):
    status = row.get("status_short") or row.get("status")
    if isinstance(status, Mapping):
        status = status.get("short") or status.get("long")
    if _words(status) not in _TERMINAL:
        return None
    home, away = row.get("home_score"), row.get("away_score")
    if home in (None, "") and away in (None, ""):
        match = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", _text(row.get("score")))
        if match:
            home, away = match.groups()
    if any(isinstance(value, bool) or not re.fullmatch(r"\d+", _text(value)) for value in (home, away)):
        return None
    return int(home), int(away)


@dataclass(frozen=True)
class _Fixture:
    position: int
    scope: tuple
    provider: str
    identifier: str
    season: str
    sport: str
    home: _Team
    away: _Team
    final_score: tuple | None
    native_id: str
    provider_ids: dict
    canonical_resolved: bool
    native_verified: bool
    native_league_id: str
    reference_key: str


def _payload_fixture_ids(row, provider, home, away, kickoff, native_id):
    """Read provider-owned event mappings, never infer them from display IDs.

    None denotes contradictory raw identity and keeps the row visible. Missing
    evidence returns an empty mapping, usable only inside a resolved canonical scope.
    A positive proof requires every provider-owned ID and the original timestamp
    to agree with the row; the source payload cannot be borrowed from another row.
    """
    raw = row.get("raw_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return {}
    if not isinstance(raw, Mapping):
        return {}
    if provider == "sportsdb" and "idEvent" in raw:
        native, league = raw.get("idEvent"), raw.get("idLeague")
        home_id, away_id = raw.get("idHomeTeam"), raw.get("idAwayTeam")
        names = raw.get("strHomeTeam"), raw.get("strAwayTeam")
        stamp, raw_season, raw_sport = raw.get("strTimestamp"), raw.get("strSeason"), raw.get("strSport")
        raw_country, raw_competition = raw.get("strCountry"), raw.get("strLeague")
    elif provider == "api-football" and isinstance(raw.get("fixture"), Mapping):
        event, league_data, teams = raw["fixture"], raw.get("league"), raw.get("teams")
        if not isinstance(league_data, Mapping) or not isinstance(teams, Mapping):
            return {}
        team_home, team_away = teams.get("home"), teams.get("away")
        if not isinstance(team_home, Mapping) or not isinstance(team_away, Mapping):
            return {}
        native, league = event.get("id"), league_data.get("id")
        home_id, away_id = team_home.get("id"), team_away.get("id")
        names = team_home.get("name"), team_away.get("name")
        stamp, raw_season, raw_sport = event.get("date"), league_data.get("season"), "football"
        raw_country, raw_competition = league_data.get("country"), league_data.get("name")
    else:
        return {}

    supplied = (
        (native, native_id),
        (league, row.get("competition_id") or row.get("league_id")),
        (home_id, home.ids.get(provider)), (away_id, away.ids.get(provider)),
    )
    if any(_text(original) and _text(stored) and _text(original) != _text(stored)
           for original, stored in supplied):
        return None
    if not all(re.fullmatch(r"[1-9]\d*", _text(original)) and _text(stored)
               for original, stored in supplied):
        return {}
    # Ordered IDs alone do not justify a row whose labels have been inverted.
    for value, team in zip(names, (home, away)):
        forms = (team.source_label_forms
                 if (type(value) is str and value == team.source_label
                     and team.source_label_forms is not None)
                 else _name_forms(value))
        if forms is None:
            return {}
        if forms[0] != team.category or not _same_names((forms[1:],), team.names):
            return None
    row_season = season_key(row.get("season"))
    row_sport = _sport(row.get("sport") or row.get("sport_name") or row.get("sport_key"))
    if ((raw_season and row_season and season_key(raw_season) != row_season)
            or (raw_sport and row_sport and _sport(raw_sport) != row_sport)):
        return None
    stored_country = row.get("country")
    country = _words(spanish_country_name(raw_country or stored_country))
    if raw_country and stored_country and country != _words(spanish_country_name(stored_country)):
        return None
    stored_competition = row.get("_raw_competition_name") or row.get("competition_name") or row.get("league_name")
    if (raw_competition and stored_competition
            and _competition_label(row, raw_competition, country) != _competition_label(row, stored_competition, country)):
        return None
    if not re.match(r"^\d{4}-\d{2}-\d{2}[T\s]\d{1,2}:\d{2}", _text(stamp)):
        return {}
    try:
        original_kickoff = datetime.fromisoformat(_text(stamp).replace("Z", "+00:00"))
    except (ValueError, TypeError, OverflowError):
        return {}
    if original_kickoff.tzinfo is None:
        if provider != "sportsdb":
            return {}
        original_kickoff = original_kickoff.replace(tzinfo=timezone.utc)
    if original_kickoff.astimezone(timezone.utc) != kickoff.astimezone(timezone.utc):
        return None
    result = {provider: _text(native)}
    if provider == "sportsdb" and re.fullmatch(r"[1-9]\d*", _text(raw.get("idAPIfootball"))):
        result["api-football"] = _text(raw["idAPIfootball"])
    return result


# One closed, bounded identity input projection is shared by the guard and matcher.
# Fields outside this view cannot influence _fixture by reading the original row.
IDENTITY_PROJECTION_LIMITS = {
    "label_chars": 1024, "scalar_chars": 256, "clock_chars": 128,
    "alias_count": _MAX_NAMES - 1, "alias_string_chars": 8192,
    "provider_id_count": 16, "namespace_chars": 128,
    "raw_json_chars": 131072, "status_depth": 4, "status_nodes": 128,
}
_STATUS_KEYS = ("key", "short", "long", "status", "state", "label", "lifecycle")
_STATUS_FIELDS = (
    "lifecycle", "v935_lifecycle", "v935_raw_lifecycle", "match_status", "fixture_status", "sports_status",
    "provider_status", "status_short", "short_status", "status_code", "status", "strStatus",
    "strProgress", "progress", "safe_status", "client_status_label", "live_status_label", "calendar_status",
)
_BASE_FIELDS = (
    "id", "match_id", "external_id", "source", "provider", "data_source", "source_name",
    "competition_key", "competition_id", "league_id", "country", "_raw_country", "season",
    "sport", "sport_name", "sport_key", "gender", "category", "age_group",
    "home_score", "away_score", "score", "result", "status_conflict",
    "is_finished", "is_live", "is_stale", "stale",
)
_LABEL_FIELDS = (
    "competition_name", "league_name", "_raw_competition_name", "client_competition",
    "calendar_competition", "competition", "league", "client_home", "client_away", "home_name", "away_name",
)
_KICKOFF_FIELDS = (
    "kickoff_iso", "commence_time", "kickoff_iso_madrid", "madrid_dt_iso", "start_time", "datetime",
    "date_time", "match_date", "date", "kickoff_time", "match_time", "time", "calendar_time", "client_time_label",
)
_CLOCK_FIELDS = ("live_updated_at", "provider_updated_at", "last_synced_at")
_ENTITY_LABELS = ("official_name", "display_name", "name")
_ENTITY_SCALARS = ("gender", "category", "age_group", "provider_team_id", "canonical_team_id")

class _IdentityLimit(ValueError):
    pass

def _identity_scalar(value, limit=256, *, identifier=False):
    if type(value) not in {str, int, float, bool, type(None)}:
        raise _IdentityLimit("unsupported identity scalar")
    if identifier and type(value) is bool:
        raise _IdentityLimit("unsupported identity identifier")
    if isinstance(value, str) and len(value) > limit:
        raise _IdentityLimit("identity scalar too long")
    if type(value) is int and value.bit_length() > 850:
        raise _IdentityLimit("identity integer too long")
    if type(value) is float and not isfinite(value):
        raise _IdentityLimit("nonfinite identity scalar")
    return value

def _identity_aliases(value):
    if value is None:
        return None
    if isinstance(value, str):
        if len(value) > IDENTITY_PROJECTION_LIMITS["alias_string_chars"]:
            raise _IdentityLimit("alias text too long")
        parts = re.split(r"[|;]", value)
        if len(parts) > IDENTITY_PROJECTION_LIMITS["alias_count"]:
            raise _IdentityLimit("too many aliases")
        if any(len(part) > IDENTITY_PROJECTION_LIMITS["label_chars"] for part in parts):
            raise _IdentityLimit("alias label too long")
        return value
    if type(value) not in {list, tuple} or len(value) > IDENTITY_PROJECTION_LIMITS["alias_count"]:
        raise _IdentityLimit("unsupported or oversized aliases")
    return tuple(_identity_scalar(alias, 1024, identifier=True) for alias in value)

def _identity_provider_ids(value):
    if value is None:
        return None
    if not isinstance(value, Mapping) or len(value) > IDENTITY_PROJECTION_LIMITS["provider_id_count"]:
        raise _IdentityLimit("unsupported or oversized provider identities")
    output = {}
    for position, (source, identifier) in enumerate(value.items()):
        if position >= IDENTITY_PROJECTION_LIMITS["provider_id_count"]:
            raise _IdentityLimit("too many provider identities")
        if not isinstance(source, str) or len(source) > 128:
            raise _IdentityLimit("unsupported provider namespace")
        output[source] = _identity_scalar(identifier, 256, identifier=True)
    return output

def _identity_entity(value):
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise _IdentityLimit("unsupported team entity")
    output = {}
    for name in _ENTITY_LABELS:
        if name in value:
            output[name] = _identity_scalar(value[name], 1024)
    for name in _ENTITY_SCALARS:
        if name in value:
            output[name] = _identity_scalar(value[name], 256, identifier=name.endswith("_id"))
    if "aliases" in value:
        output["aliases"] = _identity_aliases(value["aliases"])
    if "provider_team_ids" in value:
        output["provider_team_ids"] = _identity_provider_ids(value["provider_team_ids"])
    return output

def _identity_status(value, budget, path=()):
    budget[0] += 1
    if budget[0] > 128 or len(path) > 4:
        raise _IdentityLimit("status identity limit")
    if isinstance(value, Mapping):
        if id(value) in path:
            raise _IdentityLimit("cyclic status identity")
        return {key: _identity_status(value[key], budget, (*path, id(value)))
                for key in (*_STATUS_KEYS, "is_finished", "is_live", "is_stale", "stale") if key in value}
    return _identity_scalar(value, 256)

def _identity_payload(value, budget, *, native):
    if isinstance(value, str):
        if len(value) > IDENTITY_PROJECTION_LIMITS["raw_json_chars"]:
            raise _IdentityLimit("raw identity payload too long")
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            # Existing legacy opaque text is not provider proof; retain its
            # immutable reference, preserving the existing canonical-only path.
            return value
        value = decoded
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return None  # Non-mapping payloads contain no consumed identity fields.
    output = {}
    if native:
        for name in ("idEvent", "idAPIfootball", "idLeague", "idHomeTeam", "idAwayTeam", "strSeason", "strSport", "strCountry"):
            if name in value:
                output[name] = _identity_scalar(value[name], 256, identifier=name.startswith("id"))
        for name in ("strHomeTeam", "strAwayTeam", "strLeague"):
            if name in value:
                output[name] = _identity_scalar(value[name], 1024)
        if "strTimestamp" in value:
            output["strTimestamp"] = _identity_scalar(value["strTimestamp"], 128)
        if "league" in value:
            league = value["league"]
            if not isinstance(league, Mapping):
                raise _IdentityLimit("unsupported native league")
            output["league"] = {key: _identity_scalar(league[key], 1024 if key == "name" else 256, identifier=key == "id")
                                for key in ("id", "name", "country", "season") if key in league}
        if "teams" in value:
            teams = value["teams"]
            if not isinstance(teams, Mapping):
                raise _IdentityLimit("unsupported native teams")
            projected = {}
            for side in ("home", "away"):
                if side in teams:
                    team = teams[side]
                    if not isinstance(team, Mapping):
                        raise _IdentityLimit("unsupported native team")
                    projected[side] = {key: _identity_scalar(team[key], 1024 if key == "name" else 256, identifier=key == "id")
                                       for key in ("id", "name") if key in team}
            output["teams"] = projected
    for name in ("status", "strStatus", "strProgress", "progress", "match_status", "fixture_status"):
        if name in value:
            output[name] = _identity_status(value[name], budget)
    if "fixture" in value:
        fixture = value["fixture"]
        if not isinstance(fixture, Mapping):
            raise _IdentityLimit("unsupported native fixture")
        projected = {}
        if native:
            for name in ("id", "date"):
                if name in fixture:
                    projected[name] = _identity_scalar(fixture[name], 128 if name == "date" else 256, identifier=name == "id")
        if "status" in fixture:
            projected["status"] = _identity_status(fixture["status"], budget)
        output["fixture"] = projected
    return output

def project_fixture_identity(row, *, kickoff_for):
    """Return only bounded identity inputs and their digest, or None fail-closed.

    No price, quota, logo or arbitrary provider metadata is copied or retained.
    Valid JSON text is decoded at most to the explicit character bound; only
    consumed native/status fields survive this temporary projection.
    """
    if not isinstance(row, Mapping):
        return None
    try:
        view = {}
        for name in _BASE_FIELDS:
            if name in row:
                view[name] = _identity_scalar(row[name], 256)
        for name in _LABEL_FIELDS:
            if name in row:
                view[name] = _identity_scalar(row[name], 1024)
        for name in (*_KICKOFF_FIELDS, *_CLOCK_FIELDS):
            if name in row:
                view[name] = _identity_scalar(row[name], 128)
        for side in ("home", "away"):
            name = side + "_team"
            if name in row:
                view[name] = (_identity_entity(row[name]) if isinstance(row[name], Mapping)
                              else _identity_scalar(row[name], 1024))
            name = side + "_team_entity"
            if name in row:
                view[name] = _identity_entity(row[name])
            for suffix in ("_team_name",):
                name = side + suffix
                if name in row:
                    view[name] = _identity_scalar(row[name], 1024)
            name = "_raw_" + side + "_team"
            if name in row:
                view[name] = _identity_scalar(row[name], 1024)
            for suffix in ("_team_id", "_canonical_team_id", "_gender", "_category", "_age_group",
                           "_team_gender", "_team_category", "_team_age_group"):
                name = side + suffix
                if name in row:
                    view[name] = _identity_scalar(row[name], 256, identifier=suffix.endswith("_id"))
            name = side + "_team_aliases"
            if name in row:
                view[name] = _identity_aliases(row[name])
            name = side + "_provider_team_ids"
            if name in row:
                view[name] = _identity_provider_ids(row[name])
        budget = [0]
        for name in _STATUS_FIELDS:
            if name in row:
                view[name] = _identity_status(row[name], budget)
        for name in ("status_info", "v935_freshness", "freshness", "live_depth"):
            if name in row:
                view[name] = _identity_status(row[name], budget)
        if "fixture" in row:
            fixture = row["fixture"]
            if not isinstance(fixture, Mapping):
                raise _IdentityLimit("unsupported fixture status")
            view["fixture"] = ({"status": _identity_status(fixture["status"], budget)}
                               if "status" in fixture else {})
        for name in ("raw_json", "payload_json"):
            if name in row:
                view[name] = _identity_payload(row[name], budget, native=name == "raw_json")
        # The actual parser receives the same closed view as the matcher. It
        # cannot consume an omitted/unbounded identity field from the source row.
        try:
            kickoff = kickoff_for(view)
        except KeyError:
            raise _IdentityLimit("kickoff reads an unsupported identity field")
        except (ValueError, TypeError, OverflowError):
            kickoff = None
        if kickoff is not None and not isinstance(kickoff, datetime):
            raise _IdentityLimit("unsupported kickoff result")
        view["_evaluated_kickoff"] = kickoff
        encoded = json.dumps(view, sort_keys=True, ensure_ascii=False, allow_nan=False,
                             default=lambda value: {"datetime": value.isoformat()} if isinstance(value, datetime) else None)
        return view, hashlib.sha256(encoded.encode("utf-8")).digest()
    except (_IdentityLimit, ValueError, TypeError, OverflowError, RecursionError):
        return None


def _fixture(row, position, kickoff_for, context_for, identity_for=None):
    if not isinstance(row, Mapping):
        return None
    context = context_for(row)
    if (context.state in {"UNKNOWN_NOT_PREPARED", "UNKNOWN_IDENTITY_CHANGED", "UNKNOWN_IDENTITY_LIMIT", "CONFLICT", "AMBIGUOUS"}
            or any(issue.startswith(("CONFLICT_", "AMBIGUOUS_", "UNKNOWN_INVALID_"))
                   for issue in context.issues)):
        return None
    projected = identity_for(row) if identity_for is not None else project_fixture_identity(row, kickoff_for=kickoff_for)
    if projected is None:
        return None
    row = projected[0]
    canonical_resolved = context.state == "RESOLVED"
    provider = provider_family(row.get("source") or row.get("provider"))
    identifier = _text(row.get("id") or row.get("match_id") or row.get("external_id"))
    native_id = _text(row.get("external_id"))
    # Legacy rows sometimes repeat the app's opaque ID in external_id. That is
    # not a contradictory provider ID, nor proof of a numeric provider event.
    if native_id == identifier and not re.fullmatch(r"[1-9]\d*", native_id):
        native_id = ""
    api_identifier = re.fullmatch(r"af-(\d+)", identifier)
    if provider == "api-football" and native_id and api_identifier and native_id != api_identifier[1]:
        return None
    country = (context.country_key if canonical_resolved else
               context.country_evidence[0] if len(context.country_evidence) == 1 else "")
    competition = context.canonical_key if canonical_resolved else ""
    if (_words(identifier) in _UNKNOWN or provider in _UNKNOWN or not _explicit_kickoff(row)
            or (canonical_resolved and (country in _UNKNOWN or competition in _UNKNOWN))):
        return None
    home, away = _team(row, "home", provider), _team(row, "away", provider)
    if home is None or away is None:
        return None
    kickoff = row.get("_evaluated_kickoff")
    if not isinstance(kickoff, datetime):
        return None
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=_MADRID)
    provider_ids = _payload_fixture_ids(row, provider, home, away, kickoff, native_id)
    if provider_ids is None:
        return None
    native_verified = bool(provider in {"api-football", "sportsdb"} and native_id
                           and provider_ids.get(provider) == native_id
                           and row.get("status_conflict") is not True)
    if not canonical_resolved and not native_verified:
        return None
    return _Fixture(position, (country, competition, kickoff.astimezone(timezone.utc)),
                    provider, identifier, season_key(row.get("season")),
                    _sport(row.get("sport") or row.get("sport_name") or row.get("sport_key")), home, away,
                    _final_score(row), native_id, provider_ids, canonical_resolved,
                    native_verified, _text(row.get("competition_id") or row.get("league_id")),
                    _text(row.get("competition_key")))


def _team_conflicts(left, right):
    if left.category != right.category:
        return True
    if any(left.ids[source] != right.ids[source] for source in left.ids.keys() & right.ids.keys()):
        return True
    return bool(left.canonical and right.canonical and left.canonical != right.canonical)


def _same_names(left, right):
    # A short name can match a longer version. Two incompatible longer names
    # do not become identical merely because both reduce to the same short name.
    return any(a_full == b_full or a_full == b_short or b_full == a_short
               for a_full, a_short in left for b_full, b_short in right)


def _same_team(left, right):
    if _team_conflicts(left, right):
        return False
    if left.canonical and right.canonical:
        return True
    if left.ids.keys() & right.ids.keys():
        return True
    return _same_names(left.names, right.names)


def _compatible(left, right):
    same_native = bool(left.provider == right.provider and left.native_verified
                       and right.native_verified and left.native_id == right.native_id)
    if left.provider == right.provider and left.identifier != right.identifier and not same_native:
        return False
    if left.provider == right.provider and left.native_id and right.native_id and left.native_id != right.native_id:
        return False
    if same_native:
        if (left.native_league_id != right.native_league_id or left.scope[2] != right.scope[2]
                or (left.scope[0] and right.scope[0] and left.scope[0] != right.scope[0])
                or (left.reference_key and right.reference_key and left.reference_key != right.reference_key)
                or (left.canonical_resolved and right.canonical_resolved and left.scope[1] != right.scope[1])):
            return False
    elif not (left.canonical_resolved and right.canonical_resolved and left.scope == right.scope):
        return False
    if left.season and right.season and left.season != right.season:
        return False
    if left.sport and right.sport and left.sport != right.sport:
        return False
    if left.final_score is not None and right.final_score is not None and left.final_score != right.final_score:
        return False
    if any(left.provider_ids[source] != right.provider_ids[source]
           for source in left.provider_ids.keys() & right.provider_ids.keys()):
        return False
    for mapped, target in ((left, right), (right, left)):
        if (target.native_id and target.provider in mapped.provider_ids
                and mapped.provider_ids[target.provider] != target.native_id):
            return False
    if _team_conflicts(left.home, right.home) or _team_conflicts(left.away, right.away):
        return False
    home_matches = _same_team(left.home, right.home)
    away_matches = _same_team(left.away, right.away)
    if home_matches and away_matches:
        return True
    mapped_event = bool(left.provider_ids.keys() & right.provider_ids.keys())
    # A provider event mapping may explain the remaining alias, but cannot
    # establish home/away orientation when neither side is independently known.
    return bool(mapped_event and (home_matches or away_matches)
                and not _same_team(left.home, right.away)
                and not _same_team(left.away, right.home))


def _fixture_components(rows, kickoff_for, context_for, identity_for=None):
    fixtures = {}
    postings = defaultdict(list)
    native_postings = defaultdict(list)
    for position, row in enumerate(rows):
        fixture = _fixture(row, position, kickoff_for, context_for, identity_for)
        if fixture is None:
            continue
        fixtures[position] = fixture
        if fixture.native_verified:
            native_postings[(fixture.provider, fixture.native_id)].append(position)
        keys = {("names", home[1], away[1])
                for home, away in product(fixture.home.names, fixture.away.names)}
        if fixture.home.canonical and fixture.away.canonical:
            keys.add(("canonical", fixture.home.canonical, fixture.away.canonical))
        for source, identifier in fixture.provider_ids.items():
            keys.add(("provider-fixture", source, identifier))
        if fixture.canonical_resolved:
            for key in keys:
                postings[(*fixture.scope, fixture.home.category, fixture.away.category, key)].append(position)

    blocked = set()
    native_blocked = {}
    pairs = set()
    for positions in native_postings.values():
        if len(positions) > _MAX_POSTING:
            blocked.update(positions)
            native_blocked.update({position: "UNRESOLVED_NATIVE_OVERLOAD" for position in positions})
            continue
        candidates = tuple(combinations(positions, 2))
        # Every independently verified claimant of one native event must agree.
        # A contradictory third observation blocks that whole native cohort.
        if any(not _compatible(fixtures[left], fixtures[right]) for left, right in candidates):
            blocked.update(positions)
            native_blocked.update({position: "CONFLICT_NATIVE_OBSERVATIONS" for position in positions})
        else:
            pairs.update(candidates)
    for positions in postings.values():
        if len(positions) > _MAX_POSTING:
            blocked.update(positions)
        else:
            pairs.update(combinations(positions, 2))
    adjacency = defaultdict(set)
    for left, right in pairs:
        if left in blocked or right in blocked:
            continue
        if _compatible(fixtures[left], fixtures[right]):
            adjacency[left].add(right)
            adjacency[right].add(left)
    remaining = set(adjacency)
    groups = []
    grouped = set()
    for seed in sorted(adjacency):
        if seed not in remaining:
            continue
        component, pending = set(), [seed]
        while pending:
            current = pending.pop()
            if current not in component:
                component.add(current)
                pending.extend(adjacency[current] - component)
        remaining.difference_update(component)
        # No transitive guessing: every member must agree directly with every
        # other member. A short label bridging different clubs stays unresolved.
        if any(len(adjacency[index] & component) != len(component) - 1 for index in component):
            native_blocked.update({index: "AMBIGUOUS_FIXTURE_COMPONENT" for index in component})
            continue
        groups.append(tuple(sorted(component)))
        grouped.update(component)
    groups.extend((index,) for index in range(len(rows)) if index not in grouped)
    return sorted(groups, key=lambda group: group[0]), fixtures, native_blocked


def provider_fixture_groups(matches, *, kickoff_for, context_for, with_evidence=False, identity_for=None):
    """Return original rows grouped by the same conservative fixture proof.

    Groups follow the first occurrence in the input; members preserve their input
    order. Incomplete, overloaded or ambiguous identities are singleton groups.
    This lets presentation consumers associate each provider's existing ID with a
    chosen representative while still updating every original provider row.
    """
    rows = list(matches or ())
    components, fixtures, native_blocked = _fixture_components(rows, kickoff_for, context_for, identity_for)
    output = []
    for component in components:
        group = [rows[index] for index in component]
        native_keys = {(fixtures[index].provider, fixtures[index].native_id) for index in component
                       if index in fixtures and fixtures[index].native_verified}
        native_key = (next(iter(native_keys)) if len(native_keys) == 1
                      and all(index in fixtures and fixtures[index].native_verified for index in component) else ())
        canonical = all(context_for(row).state == "RESOLVED" for row in group)
        conflict = next((native_blocked[index] for index in component if index in native_blocked), "")
        if conflict:
            native_key = ()
        basis = conflict or ("CANONICAL_COMPETITION" if canonical else "PROVIDER_NATIVE_FIXTURE" if native_key else "UNRESOLVED")
        output.append((group, basis, native_key) if with_evidence else group)
    return output


def native_observation_candidates(group, native_key, *, identity_for=None):
    """Keep whole observations under the existing provider-clock/final policy."""
    if not native_key or len(group) < 2:
        return group
    evidence = (lambda row: identity_for(row)[0]) if identity_for is not None else (lambda row: row)
    current = [row for row in group if not any(
        other is not row and older_match_observation(evidence(other), evidence(row)) for other in group)]
    timed = [row for row in current if _provider_clock(evidence(row))[2] is not None]
    if timed:
        current = timed
    # A pathological ordering ambiguity must not silently invent a winner.
    return current or group


def unique_provider_fixtures(matches, *, kickoff_for, rank_for, context_for):
    """Select original rows for unambiguous fixture groups; maximum rank wins.

    Results keep the input order of selected rows and equal ranks prefer the first
    row. Unknown/malformed identities and ambiguous groups remain untouched. Names
    use bounded postings inside country/league/exact-time buckets, avoiding global
    quadratic comparisons; excessive collisions fail closed instead of broadening
    matching. Caller callbacks must be read-only and must not consult providers.
    """
    rows = list(matches or ())
    identities = {id(row): project_fixture_identity(row, kickoff_for=kickoff_for) for row in rows}
    identity_for = lambda row: identities[id(row)]
    positions = {id(row): position for position, row in enumerate(rows)}
    chosen = []
    for group, _basis, native_key in provider_fixture_groups(
            rows, kickoff_for=kickoff_for, context_for=context_for, with_evidence=True, identity_for=identity_for):
        candidates = native_observation_candidates(group, native_key, identity_for=identity_for)
        chosen.append(max(candidates, key=lambda row: (rank_for(row), -positions[id(row)]))
                      if len(candidates) > 1 else candidates[0])
    return sorted(chosen, key=lambda row: positions[id(row)])
