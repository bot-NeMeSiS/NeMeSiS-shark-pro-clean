"""Read-only fixture selection over intact, caller-prepared observations.

Prepare after the caller's final clone/normalization. The only reference read is
at preparation; filtering, grouping, selection, counters and polling associations
never read SQL or call providers. Unknown canonical evidence stays separate unless
one exact provider-native fixture is independently verified; that basis is explicit.
"""
from __future__ import annotations
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from engines.canonical_competition_context import ObservationContext, prepare_context
from engines.fixture_identity_read_model import native_observation_candidates, project_fixture_identity, provider_fixture_groups
from engines.snapshot_copy_engine import clone_snapshot

_IDENTITY_CHANGED = ObservationContext("UNKNOWN_IDENTITY_CHANGED")
_IDENTITY_LIMIT = ObservationContext("UNKNOWN_IDENTITY_LIMIT")

def preserve_match_observations(matches):
    """Freeze every supplied occurrence before any legacy merge can lose it."""
    return tuple(matches or ())

def _match_id(row):
    if not isinstance(row, Mapping):
        return ""
    value=row.get("id") or row.get("match_id") or row.get("external_id") or ""
    if type(value) not in {str, int} or (type(value) is int and value.bit_length() > 850):
        return ""
    if isinstance(value, str) and len(value) > 256:
        return ""
    return str(value).strip()

@dataclass(frozen=True)
class FixtureSelection:
    rows: tuple
    groups: tuple
    count: int
    raw_rows: tuple
    fixture_ids: Mapping
    confirmed_count: int
    unresolved_observations: int
    identity_basis: tuple
    native_fixture_groups: int

@dataclass(frozen=True)
class PreparedFixtureSnapshot:
    cohorts: Mapping
    context: object
    _kickoff_for: object = field(repr=False, compare=False)
    _identity_at_prepare: Mapping = field(repr=False, compare=False)

    def context_for(self, row):
        """Use this accessor for current rows; context stores preparation evidence."""
        return self._checked_identity(row)[0]

    def _checked_identity(self, row):
        entry = self._identity_at_prepare.get(id(row))
        if entry is None or entry[0] is not row:
            return self.context.for_row(row), None
        projected = project_fixture_identity(row, kickoff_for=self._kickoff_for)
        if entry[1] is None or projected is None:
            return _IDENTITY_LIMIT, None
        if entry[1] != projected[1]:
            return _IDENTITY_CHANGED, None
        return self.context.for_row(row), projected

    @property
    def identity_coverage(self):
        states=Counter(self.context_for(row).state for values in self.cohorts.values() for row in values)
        return MappingProxyType({"observations":sum(len(values) for values in self.cohorts.values()),
                                 "resolved":states.get("RESOLVED",0),
                                 "unresolved":sum(count for state,count in states.items() if state!="RESOLVED"),
                                 "states":MappingProxyType(dict(states)),
                                 "queried_keys":len(self.context.queried_keys),
                                 "lookup_calls":self.context.lookup_calls})

    def select(self, cohort, *, predicate=None, rank_for=None, limit=None):
        return self.select_rows(self.cohorts[cohort],predicate=predicate,rank_for=rank_for,limit=limit)

    def count_rows(self, rows):
        """Cardinality only; it never returns canonical/native proof or a winner.

        Freeze the supplied occurrences exactly as selection does. An empty
        cohort has no group, and one occurrence has one group for every identity
        state. Still perform that occurrence's fresh C3 check on every call;
        no context or identity result is cached between count consumers.
        Native grouping metadata (and its parser errors) is not evaluated for a
        singleton. Larger cohorts retain the complete original selection path.
        """
        originals = preserve_match_observations(rows)
        if not originals:
            return 0
        if len(originals) == 1:
            row = originals[0]
            # Preserve selection's initial ID access before the identity check.
            if isinstance(row, Mapping):
                _match_id(row)
            self._checked_identity(row)
            return 1
        return self.select_rows(originals).count

    def select_rows(self, rows, *, predicate=None, rank_for=None, limit=None):
        if limit is not None and (type(limit) is not int or limit<0):
            raise ValueError("presentation limit must be a nonnegative integer")
        # Repeated occurrences of the exact same object across summary lanes are
        # one supplied observation. Equal copied dictionaries are not conflated.
        eligible=[]
        seen_objects=set()
        for row in preserve_match_observations(rows):
            repeated = isinstance(row, Mapping) and _match_id(row) and id(row) in seen_objects
            if repeated or (predicate is not None and not predicate(row)):
                continue
            seen_objects.add(id(row))
            eligible.append(row)
        checked={id(row):self._checked_identity(row) for row in eligible}
        current_context=lambda row:checked[id(row)][0]
        current_identity=lambda row:checked[id(row)][1]
        groups=provider_fixture_groups(eligible,kickoff_for=self._kickoff_for,
                                       context_for=current_context,with_evidence=True,
                                       identity_for=current_identity)
        positions={id(row):position for position,row in enumerate(eligible)}
        ranked=[]
        for group,basis,native_key in groups:
            candidates=native_observation_candidates(group,native_key,identity_for=current_identity)
            winner=(max(candidates,key=lambda row: (rank_for(row),-positions[id(row)]))
                    if rank_for and len(candidates)>1 else candidates[0])
            ranked.append((positions[id(winner)],winner,tuple(group),basis,native_key))
        ranked.sort(key=lambda item:item[0])
        count=len(ranked)
        chosen=ranked if limit is None else ranked[:limit]
        fixture_ids={}
        for _position,_winner,group,_basis,_native_key in ranked:
            ids=tuple(sorted({_match_id(row) for row in group if _match_id(row)}))
            representative=ids[0] if ids else ""
            for identifier in ids:
                fixture_ids[identifier]=representative
        confirmed=sum(1 for _position,_winner,group,basis,_native_key in ranked
                      if basis == "CANONICAL_COMPETITION" and all(current_context(row).state=="RESOLVED" for row in group))
        unresolved=sum(1 for row in eligible if current_context(row).state!="RESOLVED")
        return FixtureSelection(tuple(item[1] for item in chosen),
                                tuple(item[2] for item in chosen),count,tuple(eligible),
                                MappingProxyType(fixture_ids),confirmed,unresolved,
                                tuple(item[3] for item in chosen),
                                sum(item[3] == "PROVIDER_NATIVE_FIXTURE" for item in ranked))

def prepare_fixture_snapshot(cohorts, read_competitions, *, kickoff_for, max_keys=500):
    """Freeze full cohorts and resolve references once; no fixture rows are fused."""
    if not isinstance(cohorts,Mapping):
        raise ValueError("cohorts must be a mapping")
    original={name:preserve_match_observations(values) for name,values in cohorts.items()}
    projected={id(row):project_fixture_identity(row,kickoff_for=kickoff_for)
               for values in original.values() for row in values}
    safe_inputs={name:tuple(projected[id(row)][0] if projected[id(row)] is not None else None for row in values)
                 for name,values in original.items()}
    context=prepare_context(safe_inputs,read_competitions,max_keys=max_keys)
    # Bind the historical outcomes back to original occurrences, not projected
    # dictionaries; neither payloads nor the reader callback are retained.
    anchors={id(row):(row,context.at(name,position)) for name,values in original.items()
             for position,row in enumerate(values)}
    context=replace(context,_anchors=MappingProxyType(anchors))
    identity={id(row):(row,projected[id(row)][1] if projected[id(row)] is not None else None)
              for values in original.values() for row in values}
    return PreparedFixtureSnapshot(MappingProxyType(original),context,kickoff_for,MappingProxyType(identity))

def clone_and_prepare_fixture_snapshot(cohorts, read_competitions, *, kickoff_for,
                                       normalize=None,max_keys=500):
    """Clone ordinary source data first, then bind context to the actual rows."""
    actual=clone_snapshot(cohorts)
    if normalize is not None:
        actual={name:tuple(normalize(row) for row in values) for name,values in actual.items()}
    return prepare_fixture_snapshot(actual,read_competitions,kickoff_for=kickoff_for,max_keys=max_keys)
