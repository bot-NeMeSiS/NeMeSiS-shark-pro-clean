"""Pure, cohort-preserving canonical competition context; no SQL or fixture selection."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import islice
from types import MappingProxyType
from engines.competition_read_model import normalized
from engines.competition_reference_registry import (
    explicit_competition_reference, observation_reference_issues, catalog_reference_issues,
)
from engines.match_sync_engine import IMPORTANT_COMPETITIONS
from engines.spanish_localization_engine import provider_competition_facts, spanish_country_name

_NAMESPACE_ALIASES = {
    "sportsdb": "sportsdb",
    "thesportsdb": "sportsdb",
    "thesportsdb-api": "sportsdb",
    "thesportsdb-event-feed": "sportsdb",
    "thesportsdb-v2-livescore": "sportsdb",
    "api-football": "api-football",
    "api-sports": "api-football",
    "api-football-primary": "api-football",
    "api-football-live": "api-football",
    "odds": "odds",
    "the-odds-api": "odds",
}
_NATIVE_NAMESPACES = frozenset({"sportsdb", "api-football", "odds"})

def _namespace(value):
    """Closed provider aliases; unrelated names retain their distinct identity."""
    key = normalized(_text(value))
    return _NAMESPACE_ALIASES.get(key, key)

_COUNTRY_UNKNOWN = frozenset(normalized(x) for x in (
    "", "unknown", "desconocido", "none", "null", "tbd", "pendiente",
    "global", "n/a", "sin pais", "no disponible"))
def _text(value):
    return str(value).strip() if isinstance(value, (str, int)) and not isinstance(value, bool) else ""
def _country(value):
    key = normalized(spanish_country_name(_text(value)))
    return "" if key in _COUNTRY_UNKNOWN else key
def _pk(value):
    text = _text(value)
    return text if text and len(text) <= 256 and not any(ord(c) < 32 or ord(c) == 127 for c in text) else ""

@dataclass(frozen=True)
class ObservationContext:
    state: str
    required_keys: tuple = ()
    canonical_key: str = ""
    canonical_name: str = ""
    country_key: str = ""
    country_evidence: tuple = ()
    issues: tuple = ()

_UNKNOWN_OBJECT = ObservationContext("UNKNOWN_NOT_PREPARED")

@dataclass(frozen=True)
class ContextBatch:
    cohorts: Mapping
    queried_keys: tuple
    required_sets: tuple
    not_covered_sets: tuple
    read_state: str
    lookup_calls: int
    _anchors: Mapping = field(repr=False, compare=False)
    def at(self, cohort, position):
        return self.cohorts[cohort][position]
    def for_row(self, row):
        entry = self._anchors.get(id(row))
        return entry[1] if entry is not None and entry[0] is row else _UNKNOWN_OBJECT

@dataclass(frozen=True)
class _Spec:
    required: tuple
    countries: tuple
    issues: tuple
    namespace: str
    native_ids: tuple
    explicit_key: str
    curated_reference: object = None

def _registry_indexes(registry):
    mappings, countries = {}, {}
    for record in registry:
        if not isinstance(record, Mapping) or not _pk(record.get("key")):
            continue
        key = _pk(record["key"])
        value = _country(record.get("country"))
        if value:
            countries.setdefault(key, set()).add(value)
        for namespace, field_name in (("sportsdb", "sportsdb_id"), ("odds", "odds_key"),
                                     ("api-football", "api_football_id")):
            identifier = _text(record.get(field_name))
            if identifier:
                mappings.setdefault((namespace, identifier), set()).add(key)
    return ({key: tuple(sorted(values)) for key, values in mappings.items()},
            {key: tuple(sorted(values)) for key, values in countries.items()})

def _spec(row, mappings):
    if not isinstance(row, Mapping):
        return _Spec((), (), ("UNKNOWN_INVALID_OBSERVATION",), "", (), "")
    required, issues = set(), set()
    explicit = _pk(row.get("competition_key"))
    if explicit:
        required.add(explicit)
    elif row.get("competition_key") not in (None, ""):
        issues.add("UNKNOWN_INVALID_REFERENCE")
    namespaces = {_namespace(row.get(field_name)) for field_name in ("source", "provider")}
    namespaces.discard("")
    if len(namespaces) > 1:
        issues.add("CONFLICT_NAMESPACE")
    namespace = next(iter(namespaces)) if len(namespaces) == 1 else ""
    for name in ("competition_id", "league_id"):
        value = row.get(name)
        if value not in (None, "") and not _text(value):
            issues.add("UNKNOWN_INVALID_LEAGUE_ID")
    ids = {_text(row.get(name)) for name in ("competition_id", "league_id")}
    ids.discard("")
    if len(ids) > 1:
        issues.add("CONFLICT_LEAGUE_ID")
    reference = explicit_competition_reference(namespace, tuple(sorted(ids)), explicit)
    if reference is not None:
        issues.update(observation_reference_issues(reference, row))
    for identifier in sorted(ids):
        keys = mappings.get((namespace, identifier), ()) if namespace else ()
        if reference is not None:
            if any(key != reference.canonical_key for key in keys):
                issues.add("CONFLICT_CURATED_MAPPING")
            # Keep every declared PK in the one bounded read, including a
            # conflicting registry target. The curated relation never wins it.
            keys = tuple(sorted(set(keys) | {reference.canonical_key}))
        if not namespace:
            issues.add("UNKNOWN_NAMESPACE")
        elif not keys:
            issues.add("UNKNOWN_UNVERIFIED_ID")
        else:
            required.update(keys)
            if len(keys) > 1:
                issues.add("AMBIGUOUS_MAPPING")
            if explicit and reference is None and any(key != explicit for key in keys):
                issues.add("CONFLICT_PK_MAPPING")
    try:
        facts = provider_competition_facts(dict(row))
    except Exception:
        facts = {}
        issues.add("UNKNOWN_PAYLOAD_CONTRACT")
    countries = {_country(row.get("country")), _country(facts.get("country"))}
    countries.discard("")
    if len(countries) > 1:
        issues.add("CONFLICT_COUNTRY")
    # safe_country, display labels, match IDs and fixture tables are never reference evidence.
    return _Spec(tuple(sorted(required)), tuple(sorted(countries)), tuple(sorted(issues)),
                 namespace, tuple(sorted(ids)), explicit, reference)

def _select_sets(required_sets, max_keys):
    selected = set()
    for group in required_sets:
        extra = set(group) - selected
        if len(selected) + len(extra) <= max_keys:
            selected.update(group)
    return tuple(sorted(selected))

def prepare_context(cohorts, read_competitions, *, max_keys=500, registry=IMPORTANT_COMPETITIONS):
    """One complete cohort snapshot; at most one callback with <=500 exact PKs.

    read_competitions receives a sorted tuple of competitions.key values and must
    perform only local, read-only lookup. Return mappings, including duplicates
    when ambiguous; never manufacture missing rows. No callback is retained.
    Context resolution is not permission to fuse fixtures or replace their rows.
    A supplied real PK can verify a native league ID only through a matching
    known catalog source/external_id. The closed reviewed-reference registry can
    additionally verify one exact provider/ID/observed-key relation after reading
    both PKs and checking its documented scope. Otherwise IDs remain UNKNOWN.
    """
    if not isinstance(cohorts, Mapping) or any(not isinstance(name, str) for name in cohorts):
        raise ValueError("cohorts must map string names to observations")
    if type(max_keys) is not int or not 0 <= max_keys <= 500:
        raise ValueError("max_keys must be an integer from 0 to 500")
    original = {name: tuple(values) for name, values in cohorts.items()}
    mappings, registry_countries = _registry_indexes(registry)
    specs = {name: tuple(_spec(row, mappings) for row in values) for name, values in original.items()}
    groups = tuple(sorted({spec.required for values in specs.values() for spec in values if spec.required}))
    queried = _select_sets(groups, max_keys)
    queried_set = frozenset(queried)
    uncovered = tuple(group for group in groups if not set(group) <= queried_set)
    records, read_state, calls = {}, "NOT_REQUESTED", 0
    if queried:
        calls = 1
        try:
            result = read_competitions(queried)
            if result is None or isinstance(result, (str, bytes, Mapping)):
                raise TypeError("invalid read result")
            # Detect overrun; never silently truncate then claim a PK absent.
            data = list(islice(iter(result), 2 * len(queried) + 1))
            if len(data) > 2 * len(queried):
                read_state = "CONTRACT_INVALID"
            else:
                read_state = "OK"
                for record in data:
                    if not isinstance(record, Mapping) or _pk(record.get("key")) not in queried_set:
                        read_state = "CONTRACT_INVALID"
                        break
                    key = _pk(record["key"])
                    scope = tuple((field_name, _text(record.get(field_name))) for field_name in
                                  ("name", "sport", "sport_name", "sport_key", "gender", "category", "age_group"))
                    snapshot = (_text(record.get("name")), _country(record.get("country")),
                                _namespace(record.get("source")), _text(record.get("external_id")), scope)
                    records.setdefault(key, []).append(snapshot)
        except Exception:
            read_state = "UNAVAILABLE"
    output, anchors = {}, {}
    for name, rows in original.items():
        values = []
        for row, spec in zip(rows, specs[name]):
            issues = set(spec.issues)
            reference_keys = ((spec.curated_reference.canonical_key,)
                              if spec.curated_reference is not None else spec.required)
            if spec.curated_reference is not None and read_state == "OK":
                for ref in spec.required:
                    for _label, country, source, identifier, scope in records.get(ref, ()):
                        issues.update(catalog_reference_issues(
                            spec.curated_reference, ref, country, source, identifier, scope))
            # Read native reference evidence only after a successful exact-PK read.
            # Static mappings may explain cross-provider references; IDs themselves
            # remain namespace-scoped. Never turn labels into a PK or native proof.
            if (read_state == "OK" and len(reference_keys) == 1
                    and set(spec.required) <= queried_set):
                ref = reference_keys[0]
                references = records.get(ref, ())
                if len(references) == 1:
                    _label, _country_key, ref_namespace, ref_native_id, _scope = references[0]
                    if (spec.native_ids and ref_native_id
                            and spec.namespace == ref_namespace):
                        if any(identifier != ref_native_id for identifier in spec.native_ids):
                            issues.add("CONFLICT_REFERENCE_NATIVE_ID")
                        elif (spec.explicit_key == ref
                              and ref_namespace in _NATIVE_NAMESPACES):
                            issues.discard("UNKNOWN_UNVERIFIED_ID")
            state, key, canonical_name = "", "", ""
            country_keys = set(spec.countries)
            if spec.required and not set(spec.required) <= queried_set:
                state = "UNKNOWN_NOT_COVERED"
            elif spec.required and read_state != "OK":
                state = "UNKNOWN_READ_CONTRACT" if read_state == "CONTRACT_INVALID" else "UNKNOWN_READ_UNAVAILABLE"
            elif any(issue.startswith("CONFLICT_") for issue in issues):
                state = "CONFLICT"
            elif any(issue.startswith("AMBIGUOUS_") for issue in issues):
                state = "AMBIGUOUS"
            elif issues:
                state = "UNKNOWN"
            elif not spec.required:
                state = "UNKNOWN_NO_REFERENCE"
            elif any(len(records.get(ref, ())) > 1 for ref in spec.required):
                state = "AMBIGUOUS"
                issues.add("AMBIGUOUS_REFERENCE")
            elif any(ref not in records for ref in reference_keys):
                state = "UNKNOWN_REFERENCE_ABSENT"
            elif len(reference_keys) != 1:
                state = "CONFLICT"
                issues.add("CONFLICT_REFERENCE")
            else:
                ref = reference_keys[0]
                label, canonical_country, _reference_namespace, _reference_native_id, _scope = records[ref][0]
                country_keys.update(registry_countries.get(ref, ()))
                if canonical_country:
                    country_keys.add(canonical_country)
                if len(country_keys) > 1:
                    state = "CONFLICT"
                    issues.add("CONFLICT_COUNTRY")
                elif not label or not canonical_country:
                    state = "UNKNOWN_REFERENCE_INCOMPLETE"
                else:
                    state, key, canonical_name = "RESOLVED", ref, label
            item = ObservationContext(
                state=state, required_keys=spec.required, canonical_key=key,
                canonical_name=canonical_name,
                country_key=next(iter(country_keys)) if state == "RESOLVED" else "",
                country_evidence=tuple(sorted(country_keys)), issues=tuple(sorted(issues)))
            values.append(item)
            # Strong identity anchors prevent object-id reuse; row fields are never read again.
            anchors[id(row)] = (row, item)
        output[name] = tuple(values)
    return ContextBatch(
        MappingProxyType(output), queried, groups, uncovered, read_state, calls,
        MappingProxyType(anchors))
