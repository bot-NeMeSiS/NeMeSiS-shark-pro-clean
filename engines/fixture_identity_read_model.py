"""Conservative, presentation-only identity for supplied football fixtures.

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
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations, product
import json
import re
from zoneinfo import ZoneInfo

from engines.competition_read_model import normalized, provider_family, season_key
from engines.match_sync_engine import IMPORTANT_COMPETITIONS
from engines.spanish_localization_engine import (
    provider_competition_facts,
    spanish_competition_name,
    spanish_country_name,
    spanish_team_name,
)
from engines.team_identity_engine import provider_team_identity_key

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
    text = _words(value)
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
    return _Team(tuple(names), frozenset(category), ids, canonical)


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


def _payload_fixture_ids(row, provider, home, away, kickoff, native_id):
    """Read provider-owned event mappings, never infer them from display IDs.

    None denotes contradictory raw identity and keeps the row visible. Missing
    evidence returns an empty mapping, allowing ordinary complete-name matching.
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
        forms = _name_forms(value)
        if forms is None:
            return {}
        if forms[0] != team.category or not _same_names((forms[1:],), team.names):
            return None
    row_season = season_key(row.get("season"))
    row_sport = _sport(row.get("sport") or row.get("sport_name") or row.get("sport_key"))
    if ((raw_season and row_season and season_key(raw_season) != row_season)
            or (raw_sport and row_sport and _sport(raw_sport) != row_sport)):
        return None
    stored_country = row.get("country") or row.get("safe_country")
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


def _fixture(row, position, kickoff_for):
    if not isinstance(row, Mapping):
        return None
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
    facts = provider_competition_facts(row)
    country = _words(spanish_country_name(facts.get("country") or row.get("country") or row.get("safe_country")))
    competition = _competition_label(row,
        facts.get("name") or row.get("_raw_competition_name") or row.get("competition_name")
        or row.get("league_name") or row.get("competition_key"), country)
    if (_words(identifier) in _UNKNOWN or provider in _UNKNOWN or country in _UNKNOWN
            or competition in _UNKNOWN or not _explicit_kickoff(row)):
        return None
    home, away = _team(row, "home", provider), _team(row, "away", provider)
    if home is None or away is None:
        return None
    try:
        kickoff = kickoff_for(row)
    except (ValueError, TypeError, OverflowError):
        return None
    if not isinstance(kickoff, datetime):
        return None
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=_MADRID)
    provider_ids = _payload_fixture_ids(row, provider, home, away, kickoff, native_id)
    if provider_ids is None:
        return None
    return _Fixture(position, (country, competition, kickoff.astimezone(timezone.utc)),
                    provider, identifier, season_key(row.get("season")),
                    _sport(row.get("sport") or row.get("sport_name") or row.get("sport_key")), home, away,
                    _final_score(row), native_id, provider_ids)


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
    if left.provider == right.provider and left.identifier != right.identifier:
        return False
    if left.provider == right.provider and left.native_id and right.native_id and left.native_id != right.native_id:
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


def _fixture_components(rows, kickoff_for):
    fixtures = {}
    postings = defaultdict(list)
    for position, row in enumerate(rows):
        fixture = _fixture(row, position, kickoff_for)
        if fixture is None:
            continue
        fixtures[position] = fixture
        keys = {("names", home[1], away[1])
                for home, away in product(fixture.home.names, fixture.away.names)}
        if fixture.home.canonical and fixture.away.canonical:
            keys.add(("canonical", fixture.home.canonical, fixture.away.canonical))
        for source, identifier in fixture.provider_ids.items():
            keys.add(("provider-fixture", source, identifier))
        for key in keys:
            postings[(*fixture.scope, fixture.home.category, fixture.away.category, key)].append(position)

    blocked = set()
    pairs = set()
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
            continue
        groups.append(tuple(sorted(component)))
        grouped.update(component)
    groups.extend((index,) for index in range(len(rows)) if index not in grouped)
    return sorted(groups, key=lambda group: group[0])


def provider_fixture_groups(matches, *, kickoff_for):
    """Return original rows grouped by the same conservative fixture proof.

    Groups follow the first occurrence in the input; members preserve their input
    order. Incomplete, overloaded or ambiguous identities are singleton groups.
    This lets presentation consumers associate each provider's existing ID with a
    chosen representative while still updating every original provider row.
    """
    rows = list(matches or ())
    return [[rows[index] for index in group] for group in _fixture_components(rows, kickoff_for)]


def unique_provider_fixtures(matches, *, kickoff_for, rank_for):
    """Select original rows for unambiguous fixture groups; maximum rank wins.

    Results keep the input order of selected rows and equal ranks prefer the first
    row. Unknown/malformed identities and ambiguous groups remain untouched. Names
    use bounded postings inside country/league/exact-time buckets, avoiding global
    quadratic comparisons; excessive collisions fail closed instead of broadening
    matching. Caller callbacks must be read-only and must not consult providers.
    """
    rows = list(matches or ())
    winners = [max(group, key=lambda index: (rank_for(rows[index]), -index)) if len(group) > 1 else group[0]
               for group in _fixture_components(rows, kickoff_for)]
    return [rows[index] for index in sorted(winners)]
