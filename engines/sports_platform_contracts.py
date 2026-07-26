"""Safe contracts for the next NeMeSiS sports platform integrations.

This module prepares boundaries only. It does not fetch provider data, persist
memory, publish Telegram messages, call SHARK, or mutate sports entities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


EVIDENCE_STATES = (
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "NOT_CERTIFIED",
    "NOT_CONFIGURED",
    "STALE",
    "BLOCKED_BY_ACCESS",
    "HYPOTHESIS",
    "INSUFFICIENT_DATA",
    "REQUIRES_REVIEW",
)

SPORTS_PLATFORM_CONTRACT = "NEMESIS-SPORTS-PLATFORM-CONTRACTS-V1"


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _state(value: Any) -> str:
    candidate = _text(value, 40).upper()
    return candidate if candidate in EVIDENCE_STATES else "REQUIRES_REVIEW"


@dataclass(frozen=True)
class EvidenceReference:
    source: str
    source_type: str
    observed_at_madrid: str
    state: str
    reference: str
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SportsEntityReference:
    entity_type: str
    entity_id: str
    label: str
    source: str
    evidence_state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SportsMemoryRecord:
    event_type: str
    entity: SportsEntityReference
    observed_at_madrid: str
    source: str
    evidence_state: str
    payload: dict[str, Any]
    persistence_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SportsGraphEdge:
    source_entity: SportsEntityReference
    relationship: str
    target_entity: SportsEntityReference
    evidence: EvidenceReference
    persistence_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AssistantContextEnvelope:
    consumer: str
    match_context: dict[str, Any]
    match_intelligence: dict[str, Any]
    sports_metrics: dict[str, Any]
    evidence_state: str
    limitations: tuple[str, ...]
    external_action_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_entity_reference(
    entity_type: Any,
    entity_id: Any,
    label: Any,
    *,
    source: Any,
    evidence_state: Any = "REQUIRES_REVIEW",
) -> SportsEntityReference:
    """Build a non-persistent reference to a real entity identifier."""

    normalized_type = _text(entity_type, 40).lower()
    normalized_id = _text(entity_id, 120)
    normalized_label = _text(label, 160)
    normalized_source = _text(source, 120)
    state = _state(evidence_state)
    if not normalized_type or not normalized_id or not normalized_source:
        state = "INSUFFICIENT_DATA"
    return SportsEntityReference(
        entity_type=normalized_type or "unknown",
        entity_id=normalized_id,
        label=normalized_label or "Entidad sin etiqueta confirmada",
        source=normalized_source or "Fuente no identificada",
        evidence_state=state,
    )


def build_sports_memory_record(
    event_type: Any,
    entity: SportsEntityReference,
    *,
    observed_at_madrid: Any,
    source: Any,
    evidence_state: Any,
    payload: Mapping[str, Any] | None = None,
) -> SportsMemoryRecord:
    """Prepare a memory event without storing it or inferring missing facts."""

    event = _text(event_type, 80)
    observed_at = _text(observed_at_madrid, 80)
    normalized_source = _text(source, 120)
    state = _state(evidence_state)
    if not event or not entity.entity_id or not observed_at or not normalized_source:
        state = "INSUFFICIENT_DATA"
    return SportsMemoryRecord(
        event_type=event or "unknown",
        entity=entity,
        observed_at_madrid=observed_at,
        source=normalized_source or "Fuente no identificada",
        evidence_state=state,
        payload=_mapping(payload),
    )


def build_sports_graph_edge(
    source_entity: SportsEntityReference,
    relationship: Any,
    target_entity: SportsEntityReference,
    evidence: EvidenceReference,
) -> SportsGraphEdge:
    """Prepare an evidence-backed edge without writing a graph."""

    relation = _text(relationship, 80).lower()
    if not relation:
        raise ValueError("relationship_required")
    if not source_entity.entity_id or not target_entity.entity_id:
        raise ValueError("entity_identity_required")
    return SportsGraphEdge(
        source_entity=source_entity,
        relationship=relation,
        target_entity=target_entity,
        evidence=evidence,
    )


def build_assistant_context(
    consumer: Any,
    *,
    match_context: Mapping[str, Any] | None = None,
    match_intelligence: Mapping[str, Any] | None = None,
    sports_metrics: Mapping[str, Any] | None = None,
    evidence_state: Any = "REQUIRES_REVIEW",
    limitations: list[str] | tuple[str, ...] | None = None,
) -> AssistantContextEnvelope:
    """Create the shared read-only envelope for SHARK or Telegram."""

    normalized_consumer = _text(consumer, 40).lower()
    if normalized_consumer not in {"shark", "telegram"}:
        raise ValueError("unsupported_consumer")
    context = _mapping(match_context)
    intelligence = _mapping(match_intelligence)
    metrics = _mapping(sports_metrics)
    state = _state(evidence_state)
    if not context and not intelligence and not metrics:
        state = "INSUFFICIENT_DATA"
    return AssistantContextEnvelope(
        consumer=normalized_consumer,
        match_context=context,
        match_intelligence=intelligence,
        sports_metrics=metrics,
        evidence_state=state,
        limitations=tuple(_text(item) for item in (limitations or []) if _text(item)),
    )


def build_sports_platform_contract_registry(project_root: str | Path) -> dict[str, Any]:
    """Describe implemented and prepared boundaries using file evidence only."""

    root = Path(project_root).resolve()

    def exists(relative: str) -> bool:
        return (root / relative).is_file()

    capabilities = [
        {
            "key": "sports_domain_model",
            "name": "Unified Sports Domain Model",
            "contract": "SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1",
            "state": "INTEGRATED" if exists("engines/sports_domain_model_engine.py") else "PENDING",
            "implementation": "engines/sports_domain_model_engine.py",
        },
        {
            "key": "sports_metrics",
            "name": "Sports Data Contract",
            "contract": "sports-metrics-v1",
            "state": "INTEGRATED" if exists("app.py") else "NOT_AVAILABLE",
            "implementation": "app.py",
        },
        {
            "key": "match_context",
            "name": "Match Context",
            "contract": "MATCH-CENTER-LIFECYCLE-STORY-V1",
            "state": "INTEGRATED" if exists("engines/match_context_engine.py") else "NOT_AVAILABLE",
            "implementation": "engines/match_context_engine.py",
        },
        {
            "key": "match_intelligence_core",
            "name": "Match Intelligence Engine",
            "contract": "MATCH-INTELLIGENCE-EVIDENCE-V1",
            "state": "INTEGRATED"
            if exists("engines/match_intelligence_engine.py")
            and exists("engines/match_context_engine.py")
            else "PENDING",
            "implementation": (
                "engines/match_intelligence_engine.py + "
                "engines/match_context_engine.py"
            ),
        },
        {
            "key": "live_story",
            "name": "Live Story Engine",
            "contract": "MATCH-CENTER-LIFECYCLE-STORY-V1",
            "state": "INTEGRATED" if exists("engines/match_live_story_engine.py") else "PENDING",
            "implementation": "engines/match_live_story_engine.py",
        },
        {
            "key": "match_center_intelligence",
            "name": "Match Center Intelligence",
            "contract": "MATCH-CENTER-LIFECYCLE-STORY-V1",
            "state": "INTEGRATED"
            if all(
                exists(path)
                for path in (
                    "engines/match_context_engine.py",
                    "engines/match_live_story_engine.py",
                    "engines/api_football_live_tracker_engine.py",
                    "templates/components/v944_match_center.html",
                    "tests/test_sports_core_match_center_intelligence.py",
                )
            )
            else "PENDING",
            "implementation": (
                "engines/match_context_engine.py + engines/match_live_story_engine.py + "
                "engines/api_football_live_tracker_engine.py"
            ),
        },
        {
            "key": "live_center",
            "name": "Live Center Foundation",
            "contract": "LIVE-CENTER-CONTEXT-V1",
            "state": "FOUNDATION_READY"
            if exists("engines/match_context_engine.py") and exists("engines/match_live_story_engine.py")
            else "PENDING",
            "implementation": "engines/match_context_engine.py + engines/match_live_story_engine.py",
        },
        {
            "key": "shark_context",
            "name": "SHARK Context",
            "contract": "SHARK-CONTEXT-ENVELOPE-V1",
            "state": "CONTRACT_READY" if exists("engines/shark_context_presentation_engine.py") else "PENDING",
            "implementation": "engines/shark_context_presentation_engine.py",
        },
        {
            "key": "telegram_assistant",
            "name": "Telegram Assistant",
            "contract": "TELEGRAM-ASSISTANT-CONTEXT-V1",
            "state": "CONTRACT_READY" if exists("engines/telegram_intelligence_engine.py") else "PENDING",
            "implementation": "engines/telegram_intelligence_engine.py",
        },
        {
            "key": "team_center",
            "name": "Team Center Foundation",
            "contract": "SPORTS-ENTITY-CENTER-CONTEXT-V1",
            "state": "CONTRACT_READY",
            "implementation": "engines/sports_platform_contracts.py",
        },
        {
            "key": "competition_center",
            "name": "Competition Center Foundation",
            "contract": "SPORTS-ENTITY-CENTER-CONTEXT-V1",
            "state": "CONTRACT_READY",
            "implementation": "engines/sports_platform_contracts.py",
        },
        {
            "key": "player_center",
            "name": "Player Center Foundation",
            "contract": "SPORTS-ENTITY-CENTER-CONTEXT-V1",
            "state": "CONTRACT_READY",
            "implementation": "engines/sports_platform_contracts.py",
        },
        {
            "key": "sports_memory",
            "name": "Sports Memory",
            "contract": "SPORTS-MEMORY-RECORD-V1",
            "state": "CONTRACT_READY",
            "implementation": "engines/sports_platform_contracts.py",
        },
        {
            "key": "sports_graph",
            "name": "Sports Graph",
            "contract": "SPORTS-GRAPH-EDGE-V1",
            "state": "CONTRACT_READY",
            "implementation": "engines/sports_platform_contracts.py",
        },
    ]
    return {
        "contract": SPORTS_PLATFORM_CONTRACT,
        "capabilities": capabilities,
        "guardrails": {
            "external_calls": False,
            "database_writes": False,
            "telegram_sends": False,
            "shark_calls": False,
            "automatic_learning": False,
            "automatic_deploy": False,
        },
        "future_entities": ["team", "player", "competition", "market", "user"],
        "canonical_entities": ["match", "team", "competition", "player", "timeline_event", "evidence", "freshness"],
        "evidence_states": list(EVIDENCE_STATES),
    }
