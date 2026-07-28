"""Evidence-first Decision Engine for NeMeSiS SHARK PRO.

The Decision Engine organizes existing evidence. It does not predict, generate
picks, call AI, query providers, write databases, send Telegram messages or
invent missing facts. Every answer keeps provenance, evidence, freshness,
quality and limitations attached to the source that produced it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1
from typing import Any, Iterable, Mapping

from engines.match_intelligence_engine import MATCH_INTELLIGENCE_CONTRACT
from engines.shark_intelligence_platform_engine import SHARK_INTELLIGENCE_PLATFORM_CONTRACT
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_intelligence_gateway_engine import SPORTS_INTELLIGENCE_GATEWAY_CONTRACT
from engines.sports_knowledge_layer_engine import SPORTS_KNOWLEDGE_LAYER_CONTRACT
from engines.sports_platform_contracts import EVIDENCE_STATES
from engines.user_intelligence_platform_engine import USER_INTELLIGENCE_PLATFORM_CONTRACT


DECISION_ENGINE_CONTRACT = "NEMESIS-DECISION-ENGINE-EVIDENCE-FIRST-V1"
DECISION_EVIDENCE_CONTRACT = "NEMESIS-DECISION-EVIDENCE-ITEM-V1"
DECISION_QUESTION_CONTRACT = "NEMESIS-DECISION-QUESTION-ANSWER-V1"

DECISION_QUESTIONS = (
    "what_we_know",
    "what_we_do_not_know",
    "what_evidence_exists",
    "what_evidence_is_missing",
    "what_changed",
    "which_sources_align",
    "which_sources_disagree",
    "data_quality",
    "confidence",
)

FUTURE_CONSUMERS = (
    "telegram",
    "bankroll",
    "company_os",
    "player_center",
    "team_center",
    "competition_center",
    "match_center",
)


def _text(value: Any, limit: int = 260) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _state(value: Any) -> str:
    candidate = _text(value, 80).upper().replace(" ", "_").replace("-", "_")
    return candidate if candidate in EVIDENCE_STATES else "REQUIRES_REVIEW"


def _first_present(*values: Any, limit: int = 180) -> str:
    for value in values:
        text = _text(value, limit)
        if text:
            return text
    return ""


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _list_text(value: Any, limit: int = 8) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = []
    result: list[str] = []
    for item in values:
        text = _text(item, 220)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _stable_id(*parts: Any) -> str:
    raw = "|".join(_text(part, 160) for part in parts).encode("utf-8", errors="ignore")
    return "DEC-" + sha1(raw).hexdigest()[:12].upper()


def _quality_label(state: str, evidence_count: int) -> str:
    if state == "VERIFIED" and evidence_count:
        return "Evidencia confirmada"
    if state == "PARTIALLY_VERIFIED" or evidence_count:
        return "Evidencia parcial"
    if state == "STALE":
        return "Evidencia desactualizada"
    if state == "NOT_CONFIGURED":
        return "No configurado"
    if state == "BLOCKED_BY_ACCESS":
        return "Bloqueado por acceso"
    if state == "INSUFFICIENT_DATA":
        return "Datos insuficientes"
    return "Requiere revision"


@dataclass(frozen=True)
class DecisionEvidenceItem:
    evidence_id: str
    topic: str
    value: str
    source: str
    source_contract: str
    source_type: str
    provenance: str
    evidence: tuple[str, ...]
    freshness: str
    quality: str
    certification_state: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _evidence_item(
    topic: Any,
    value: Any,
    *,
    source: Any,
    source_contract: Any,
    source_type: Any,
    provenance: Any = "",
    evidence: Iterable[Any] = (),
    freshness: Any = "",
    quality: Any = "",
    certification_state: Any = "REQUIRES_REVIEW",
    limitations: Iterable[Any] = (),
) -> dict[str, Any]:
    evidence_items = tuple(_text(item, 220) for item in evidence if _text(item, 220))
    state = _state(certification_state)
    if not _text(value) or not evidence_items:
        state = "INSUFFICIENT_DATA" if state == "REQUIRES_REVIEW" else state
    quality_text = _first_present(quality, _quality_label(state, len(evidence_items)), limit=140)
    item = DecisionEvidenceItem(
        evidence_id=_stable_id(source_contract, topic, value, evidence_items),
        topic=_text(topic, 120) or "unknown",
        value=_text(value, 360) or "No disponible",
        source=_text(source, 140) or "upstream_snapshot",
        source_contract=_text(source_contract, 160) or "No disponible",
        source_type=_text(source_type, 80) or "snapshot",
        provenance=_text(provenance, 180) or "No disponible",
        evidence=evidence_items,
        freshness=_text(freshness, 140) or "No disponible",
        quality=quality_text,
        certification_state=state,
        limitations=tuple(_text(item, 220) for item in limitations if _text(item, 220)),
    )
    return item.to_dict()


def _source_header(name: str, contract: str, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "contract": contract,
        "present": bool(snapshot),
        "state": _state(
            snapshot.get("certification_state")
            or _mapping(snapshot.get("data_quality")).get("state")
            or snapshot.get("state")
            or ("PARTIALLY_VERIFIED" if snapshot else "INSUFFICIENT_DATA")
        ),
        "freshness": _first_present(
            snapshot.get("freshness"),
            snapshot.get("last_sync"),
            snapshot.get("updated_at"),
            _mapping(snapshot.get("freshness")).get("label"),
            _mapping(snapshot.get("evidence")).get("updated_at"),
            "No disponible",
        ),
        "limitations": _list_text(snapshot.get("limitations") or snapshot.get("missing_information")),
    }


def _source_contracts(inputs: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    expected = {
        "sports_core": SPORTS_DOMAIN_MODEL_CONTRACT,
        "sports_knowledge": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "sports_graph": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "match_intelligence": MATCH_INTELLIGENCE_CONTRACT,
        "shark": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "gateway": SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
        "user_intelligence": USER_INTELLIGENCE_PLATFORM_CONTRACT,
    }
    names = {
        "sports_core": "Sports Core",
        "sports_knowledge": "Sports Knowledge",
        "sports_graph": "Sports Graph",
        "match_intelligence": "Match Intelligence",
        "shark": "SHARK",
        "gateway": "Sports Intelligence Gateway",
        "user_intelligence": "User Intelligence",
    }
    return [
        _source_header(names[key], contract, _mapping(inputs.get(key)))
        for key, contract in expected.items()
    ]


def _extract_claims(source_key: str, contract: str, snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if not snapshot:
        claims.append(
            _evidence_item(
                source_key,
                "No disponible",
                source=source_key,
                source_contract=contract,
                source_type="snapshot",
                evidence=(),
                certification_state="INSUFFICIENT_DATA",
                limitations=["Snapshot no recibido por Decision Engine."],
            )
        )
        return claims

    if source_key == "gateway":
        for item in _items(snapshot.get("evidence_registry"))[:10]:
            claims.append(
                _evidence_item(
                    item.get("data_type") or item.get("source_id") or "source_evidence",
                    item.get("evidence") or item.get("quality") or "No disponible",
                    source="Sports Intelligence Gateway",
                    source_contract=contract,
                    source_type="source_evidence",
                    provenance=item.get("provenance"),
                    evidence=[item.get("source_id"), item.get("evidence")],
                    freshness=item.get("freshness"),
                    quality=item.get("quality"),
                    certification_state=item.get("certification_state"),
                    limitations=item.get("limitations") or [],
                )
            )
        for item in _items(snapshot.get("compliance"))[:10]:
            claims.append(
                _evidence_item(
                    "source_compliance",
                    item.get("state"),
                    source="Sports Intelligence Gateway",
                    source_contract=contract,
                    source_type="source_compliance",
                    provenance=item.get("source_id"),
                    evidence=[item.get("source_id"), "commercial_use_allowed=" + str(item.get("commercial_use_allowed"))],
                    freshness="No disponible",
                    quality="Compliance",
                    certification_state="VERIFIED" if item.get("connection_allowed") else "REQUIRES_REVIEW",
                    limitations=item.get("missing_requirements") or [],
                )
            )
        return claims

    if source_key == "shark":
        for item in _items(snapshot.get("claims"))[:12]:
            claims.append(
                _evidence_item(
                    item.get("id") or item.get("title") or "shark_claim",
                    item.get("body") or item.get("title"),
                    source="SHARK Intelligence",
                    source_contract=contract,
                    source_type="claim",
                    provenance=item.get("source"),
                    evidence=item.get("evidence") or [],
                    freshness=_mapping(item.get("freshness")).get("label") or item.get("freshness"),
                    quality=_mapping(item.get("quality")).get("label") or item.get("quality"),
                    certification_state=item.get("certification_state"),
                    limitations=item.get("limitations") or [],
                )
            )
        return claims

    if source_key == "match_intelligence":
        conclusions = _mapping(snapshot.get("conclusions"))
        for key, value in conclusions.items():
            claims.append(
                _evidence_item(
                    key,
                    value,
                    source="Match Intelligence",
                    source_contract=contract,
                    source_type="conclusion",
                    provenance=snapshot.get("source") or "match_intelligence_snapshot",
                    evidence=[key, value],
                    freshness=snapshot.get("freshness") or snapshot.get("updated_at"),
                    quality=snapshot.get("quality") or "Decision evidence",
                    certification_state=snapshot.get("certification_state") or "PARTIALLY_VERIFIED",
                    limitations=snapshot.get("limitations") or [],
                )
            )
        for item in _items(snapshot.get("evidence"))[:8]:
            claims.append(
                _evidence_item(
                    item.get("kind") or item.get("category") or "match_evidence",
                    item.get("label") or item.get("claim") or item.get("value"),
                    source="Match Intelligence",
                    source_contract=contract,
                    source_type="evidence",
                    provenance=item.get("source"),
                    evidence=[item.get("label") or item.get("claim") or item.get("value")],
                    freshness=item.get("freshness") or item.get("observed_at"),
                    quality=item.get("quality"),
                    certification_state=item.get("state") or item.get("certification_state"),
                    limitations=item.get("limitations") or [],
                )
            )
        return claims

    generic_items = (
        _items(snapshot.get("evidence"))
        + _items(snapshot.get("signals"))
        + _items(snapshot.get("facts"))
        + _items(snapshot.get("modules"))
        + _items(snapshot.get("relationships"))
    )
    for item in generic_items[:16]:
        claims.append(
            _evidence_item(
                item.get("id") or item.get("key") or item.get("kind") or item.get("relationship") or source_key,
                item.get("value") or item.get("label") or item.get("name") or item.get("state") or item.get("target") or item.get("contract"),
                source=source_key,
                source_contract=contract,
                source_type="snapshot_item",
                provenance=item.get("source") or item.get("provenance"),
                evidence=[item.get("evidence") or item.get("contract") or item.get("source") or item.get("relationship")],
                freshness=item.get("freshness") or item.get("updated_at"),
                quality=item.get("quality") or item.get("data_quality"),
                certification_state=item.get("certification_state") or item.get("state"),
                limitations=item.get("limitations") or [],
            )
        )

    if not claims:
        claims.append(
            _evidence_item(
                source_key,
                snapshot.get("contract") or "Snapshot presente",
                source=source_key,
                source_contract=contract,
                source_type="contract_presence",
                provenance=snapshot.get("source") or source_key,
                evidence=[snapshot.get("contract") or contract],
                freshness=snapshot.get("updated_at") or snapshot.get("generated_at_madrid"),
                quality="Contract evidence",
                certification_state=snapshot.get("certification_state") or "PARTIALLY_VERIFIED",
                limitations=snapshot.get("limitations") or [],
            )
        )
    return claims


def collect_decision_evidence(
    *,
    sports_core: Mapping[str, Any] | None = None,
    sports_knowledge: Mapping[str, Any] | None = None,
    sports_graph: Mapping[str, Any] | None = None,
    match_intelligence: Mapping[str, Any] | None = None,
    shark: Mapping[str, Any] | None = None,
    gateway: Mapping[str, Any] | None = None,
    user_intelligence: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    inputs = {
        "sports_core": _mapping(sports_core),
        "sports_knowledge": _mapping(sports_knowledge),
        "sports_graph": _mapping(sports_graph),
        "match_intelligence": _mapping(match_intelligence),
        "shark": _mapping(shark),
        "gateway": _mapping(gateway),
        "user_intelligence": _mapping(user_intelligence),
    }
    contracts = {
        "sports_core": SPORTS_DOMAIN_MODEL_CONTRACT,
        "sports_knowledge": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "sports_graph": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "match_intelligence": MATCH_INTELLIGENCE_CONTRACT,
        "shark": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "gateway": SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
        "user_intelligence": USER_INTELLIGENCE_PLATFORM_CONTRACT,
    }
    evidence: list[dict[str, Any]] = []
    for key, snapshot in inputs.items():
        evidence.extend(_extract_claims(key, contracts[key], snapshot))
    return evidence


def _known_items(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in evidence
        if item.get("certification_state") in {"VERIFIED", "PARTIALLY_VERIFIED"}
        and item.get("value") != "No disponible"
    ]


def _unknown_items(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unknowns = [
        item
        for item in evidence
        if item.get("certification_state") in {"INSUFFICIENT_DATA", "NOT_CERTIFIED", "NOT_CONFIGURED", "BLOCKED_BY_ACCESS", "REQUIRES_REVIEW", "STALE"}
        or item.get("value") == "No disponible"
    ]
    return unknowns


def compare_source_claims(
    source_claims: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare explicit claim records only when the caller supplies them."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in _items(list(source_claims or [])):
        claim_key = _text(raw.get("claim_key") or raw.get("topic") or raw.get("id"), 120)
        value = _text(raw.get("value") or raw.get("normalized_value"), 220)
        source = _text(raw.get("source") or raw.get("provider"), 120)
        if not claim_key or not value or not source:
            continue
        grouped.setdefault(claim_key, []).append(
            {
                "source": source,
                "value": value,
                "evidence": _text(raw.get("evidence"), 220) or "No disponible",
                "freshness": _text(raw.get("freshness"), 120) or "No disponible",
                "quality": _text(raw.get("quality"), 120) or "REQUIRES_REVIEW",
                "limitations": _list_text(raw.get("limitations")),
            }
        )
    alignments: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    for claim_key, items in sorted(grouped.items()):
        values = sorted(set(item["value"] for item in items))
        if len(items) < 2:
            continue
        if len(values) == 1:
            alignments.append(
                {
                    "claim_key": claim_key,
                    "value": values[0],
                    "sources": sorted(item["source"] for item in items),
                    "evidence": [item["evidence"] for item in items],
                    "freshness": [item["freshness"] for item in items],
                    "quality": [item["quality"] for item in items],
                    "limitations": sorted({limitation for item in items for limitation in item["limitations"]}),
                    "certification_state": "PARTIALLY_VERIFIED",
                }
            )
        else:
            discrepancies.append(
                {
                    "claim_key": claim_key,
                    "values": values,
                    "sources": items,
                    "certification_state": "REQUIRES_REVIEW",
                    "limitations": ["Las fuentes no coinciden; requiere revision humana antes de usar el dato."],
                }
            )
    return {
        "alignments": alignments,
        "discrepancies": discrepancies,
        "insufficient_comparison_data": not alignments and not discrepancies,
    }


def _changed_items(current: list[dict[str, Any]], previous: Mapping[str, Any] | None = None) -> dict[str, Any]:
    previous_items = _items(_mapping(previous).get("evidence_items"))
    if not previous_items:
        return {
            "state": "INSUFFICIENT_DATA",
            "items": [],
            "limitations": ["No previous Decision Engine snapshot was supplied."],
        }
    previous_ids = {item.get("evidence_id") for item in previous_items}
    current_ids = {item.get("evidence_id") for item in current}
    added = [item for item in current if item.get("evidence_id") not in previous_ids]
    removed = [item for item in previous_items if item.get("evidence_id") not in current_ids]
    return {
        "state": "PARTIALLY_VERIFIED",
        "items": [
            {"change": "added", **item} for item in added[:10]
        ]
        + [
            {"change": "removed", **item} for item in removed[:10]
        ],
        "limitations": [] if added or removed else ["No evidence-level change detected."],
    }


def _confidence(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    if not evidence:
        return {
            "level": "INSUFFICIENT_DATA",
            "score": 0,
            "basis": "No evidence items were supplied.",
            "limitations": ["Decision Engine cannot infer confidence without evidence."],
        }
    verified = sum(1 for item in evidence if item.get("certification_state") == "VERIFIED")
    partial = sum(1 for item in evidence if item.get("certification_state") == "PARTIALLY_VERIFIED")
    stale = sum(1 for item in evidence if item.get("certification_state") == "STALE")
    blocked = sum(1 for item in evidence if item.get("certification_state") in {"BLOCKED_BY_ACCESS", "INSUFFICIENT_DATA", "REQUIRES_REVIEW"})
    score = max(0, min(100, round(((verified * 1.0 + partial * 0.55) / max(1, len(evidence))) * 100) - stale * 8 - blocked * 4))
    if score >= 75:
        level = "HIGH_EVIDENCE_CONFIDENCE"
    elif score >= 45:
        level = "PARTIAL_EVIDENCE_CONFIDENCE"
    else:
        level = "LOW_EVIDENCE_CONFIDENCE"
    return {
        "level": level,
        "score": score,
        "basis": f"{verified} verified, {partial} partially verified, {stale} stale, {blocked} requiring review.",
        "limitations": ["Confidence measures evidence completeness only; it is not a prediction or pick confidence."],
    }


def _answer(question: str, items: list[dict[str, Any]], *, limitations: Iterable[Any] = ()) -> dict[str, Any]:
    return {
        "contract": DECISION_QUESTION_CONTRACT,
        "question": question,
        "items": items,
        "count": len(items),
        "provenance": "Decision Engine organizes upstream snapshots only.",
        "evidence": [item.get("evidence_id") for item in items[:12] if item.get("evidence_id")],
        "freshness": "Derived from upstream evidence items.",
        "quality": "Evidence organization, not prediction.",
        "limitations": [_text(item, 220) for item in limitations if _text(item, 220)],
    }


def build_decision_engine_snapshot(
    *,
    sports_core: Mapping[str, Any] | None = None,
    sports_knowledge: Mapping[str, Any] | None = None,
    sports_graph: Mapping[str, Any] | None = None,
    match_intelligence: Mapping[str, Any] | None = None,
    shark: Mapping[str, Any] | None = None,
    gateway: Mapping[str, Any] | None = None,
    user_intelligence: Mapping[str, Any] | None = None,
    source_claims: Iterable[Mapping[str, Any]] | None = None,
    previous_snapshot: Mapping[str, Any] | None = None,
    observed_at_madrid: Any = "",
) -> dict[str, Any]:
    """Build the evidence-first decision snapshot from existing contracts."""

    inputs = {
        "sports_core": _mapping(sports_core),
        "sports_knowledge": _mapping(sports_knowledge),
        "sports_graph": _mapping(sports_graph),
        "match_intelligence": _mapping(match_intelligence),
        "shark": _mapping(shark),
        "gateway": _mapping(gateway),
        "user_intelligence": _mapping(user_intelligence),
    }
    evidence = collect_decision_evidence(**inputs)
    known = _known_items(evidence)
    unknown = _unknown_items(evidence)
    comparison = compare_source_claims(source_claims)
    changes = _changed_items(evidence, previous_snapshot)
    confidence = _confidence(evidence)
    missing_evidence = [
        {
            "topic": item.get("topic"),
            "source": item.get("source"),
            "source_contract": item.get("source_contract"),
            "reason": item.get("value") if item.get("value") == "No disponible" else item.get("certification_state"),
            "limitations": item.get("limitations") or ["Evidence is incomplete or requires review."],
        }
        for item in unknown[:20]
    ]
    quality_items = [
        {
            "topic": item.get("topic"),
            "source": item.get("source"),
            "quality": item.get("quality"),
            "certification_state": item.get("certification_state"),
            "freshness": item.get("freshness"),
            "limitations": item.get("limitations"),
        }
        for item in evidence[:30]
    ]
    answers = {
        "what_we_know": _answer("¿Qué sabemos?", known[:20], limitations=[]),
        "what_we_do_not_know": _answer("¿Qué no sabemos?", unknown[:20], limitations=["Unknowns remain unavailable until upstream evidence changes."]),
        "what_evidence_exists": _answer("¿Qué evidencia existe?", evidence[:30], limitations=[]),
        "what_evidence_is_missing": {
            **_answer("¿Qué evidencia falta?", [], limitations=["Missing evidence is derived from incomplete or unavailable upstream facts."]),
            "items": missing_evidence,
            "count": len(missing_evidence),
        },
        "what_changed": {
            **_answer("¿Qué ha cambiado?", changes["items"], limitations=changes["limitations"]),
            "change_state": changes["state"],
        },
        "which_sources_align": {
            **_answer("¿Qué fuentes coinciden?", comparison["alignments"], limitations=[] if comparison["alignments"] else ["No hay comparativa multi-fuente suficiente."]),
            "comparison_state": "PARTIALLY_VERIFIED" if comparison["alignments"] else "INSUFFICIENT_DATA",
        },
        "which_sources_disagree": {
            **_answer("¿Qué fuentes discrepan?", comparison["discrepancies"], limitations=[] if comparison["discrepancies"] else ["No hay discrepancias demostradas con los datos recibidos."]),
            "comparison_state": "REQUIRES_REVIEW" if comparison["discrepancies"] else "INSUFFICIENT_DATA",
        },
        "data_quality": _answer("¿Qué calidad tiene cada dato?", quality_items, limitations=["Quality belongs to evidence state, not sporting prediction."]),
        "confidence": {
            **_answer("¿Qué confianza tiene?", [], limitations=confidence["limitations"]),
            "level": confidence["level"],
            "score": confidence["score"],
            "basis": confidence["basis"],
        },
    }
    return {
        "contract": DECISION_ENGINE_CONTRACT,
        "decision_evidence_contract": DECISION_EVIDENCE_CONTRACT,
        "decision_question_contract": DECISION_QUESTION_CONTRACT,
        "source_contracts": _source_contracts(inputs),
        "questions": list(DECISION_QUESTIONS),
        "answers": answers,
        "evidence_items": evidence,
        "known_count": len(known),
        "unknown_count": len(unknown),
        "source_alignment": comparison,
        "changes": changes,
        "confidence": confidence,
        "future_integrations": [
            {
                "consumer": consumer,
                "state": "PREPARED_NOT_ENABLED",
                "contract": DECISION_ENGINE_CONTRACT,
                "automatic_actions": False,
                "approval_required": True,
            }
            for consumer in FUTURE_CONSUMERS
        ],
        "guardrails": {
            "external_calls": 0,
            "database_writes": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "picks_created": 0,
            "predictions_created": 0,
            "automatic_actions": 0,
            "fake_data_created": 0,
        },
        "observed_at_madrid": _text(observed_at_madrid, 100),
        "production_modified": False,
    }


def decision_engine_snapshot() -> dict[str, Any]:
    """Static metadata for registry and checks."""

    return {
        "contract": DECISION_ENGINE_CONTRACT,
        "decision_evidence_contract": DECISION_EVIDENCE_CONTRACT,
        "decision_question_contract": DECISION_QUESTION_CONTRACT,
        "questions": list(DECISION_QUESTIONS),
        "consumes": [
            SPORTS_DOMAIN_MODEL_CONTRACT,
            SPORTS_KNOWLEDGE_LAYER_CONTRACT,
            SPORTS_GRAPH_FOUNDATION_CONTRACT,
            MATCH_INTELLIGENCE_CONTRACT,
            SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
            SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
            USER_INTELLIGENCE_PLATFORM_CONTRACT,
        ],
        "future_integrations": list(FUTURE_CONSUMERS),
        "guardrails": {
            "external_calls": 0,
            "database_writes": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "generative_ai_calls": 0,
            "picks_created": 0,
            "predictions_created": 0,
            "automatic_actions": 0,
        },
    }
