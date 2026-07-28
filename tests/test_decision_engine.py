from __future__ import annotations

import ast
from pathlib import Path

from engines.decision_engine import (
    DECISION_ENGINE_CONTRACT,
    DECISION_QUESTION_CONTRACT,
    build_decision_engine_snapshot,
    compare_source_claims,
    decision_engine_snapshot,
)
from engines.project_operating_system_engine import build_developer_center_snapshot, clear_project_snapshot_cache
from engines.sentinel_autopilot_engine import build_decision_engine_contract_snapshot
from engines.sports_intelligence_gateway_engine import build_sports_intelligence_gateway_snapshot
from engines.sports_platform_contracts import build_sports_platform_contract_registry


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


def _module_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8").lstrip("\ufeff")
    tree = ast.parse(source)
    return {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }


def _gateway() -> dict:
    return build_sports_intelligence_gateway_snapshot(
        [
            {
                "source_id": "official-check-source",
                "name": "Official Check Source",
                "license": "commercial-rights-reviewed",
                "provenance": "official-source-contract",
                "source_type": "API",
                "state": "APPROVED",
                "coverage": "fixtures and results",
                "quality": "VERIFIED",
                "latency": "15m",
                "last_sync": "2026-07-28T10:00:00+02:00",
                "commercial_use_allowed": True,
                "attribution_required": True,
            }
        ],
        observed_at_madrid="2026-07-28T10:05:00+02:00",
    )


def _snapshot() -> dict:
    return build_decision_engine_snapshot(
        sports_core={"contract": "SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1", "source": "domain_snapshot"},
        sports_knowledge={
            "contract": "SPORTS-KNOWLEDGE-LAYER-V1",
            "evidence": [{"kind": "team_form", "label": "Forma reciente disponible", "source": "knowledge"}],
        },
        sports_graph={
            "contract": "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1",
            "relationships": [{"relationship": "team_has_match", "target": "match-1", "source": "graph"}],
        },
        match_intelligence={
            "contract": "MATCH-INTELLIGENCE-EVIDENCE-V1",
            "conclusions": {"phase": "En juego", "risk": "Datos parciales"},
            "evidence": [{"kind": "score", "label": "1-0 confirmado", "source": "provider-cache"}],
            "certification_state": "PARTIALLY_VERIFIED",
        },
        shark={
            "contract": "SHARK-INTELLIGENCE-PLATFORM-V1",
            "claims": [
                {
                    "id": "momentum",
                    "title": "Contexto",
                    "body": "El marcador existe con evidencia parcial.",
                    "source": "match_intelligence",
                    "certification_state": "PARTIALLY_VERIFIED",
                    "evidence": ["score"],
                    "freshness": {"label": "2026-07-28T10:00:00+02:00"},
                    "quality": {"label": "Evidencia parcial"},
                    "limitations": ["Sin estadisticas avanzadas."],
                }
            ],
        },
        gateway=_gateway(),
        user_intelligence={
            "contract": "USER-INTELLIGENCE-PLATFORM-V1",
            "signals": [{"key": "team", "label": "Club Norte", "state": "VERIFIED", "source": "first-party"}],
        },
        source_claims=[
            {"claim_key": "score", "source": "provider-a", "value": "1-0", "evidence": "cache-a", "quality": "VERIFIED"},
            {"claim_key": "score", "source": "provider-b", "value": "1-0", "evidence": "cache-b", "quality": "VERIFIED"},
            {"claim_key": "minute", "source": "provider-a", "value": "68", "evidence": "cache-a", "quality": "VERIFIED"},
            {"claim_key": "minute", "source": "provider-b", "value": "70", "evidence": "cache-b", "quality": "VERIFIED"},
        ],
        observed_at_madrid="2026-07-28T10:10:00+02:00",
    )


def test_decision_engine_answers_all_required_questions_with_traceability():
    snapshot = _snapshot()

    assert snapshot["contract"] == DECISION_ENGINE_CONTRACT
    assert set(snapshot["questions"]) == {
        "what_we_know",
        "what_we_do_not_know",
        "what_evidence_exists",
        "what_evidence_is_missing",
        "what_changed",
        "which_sources_align",
        "which_sources_disagree",
        "data_quality",
        "confidence",
    }
    for key, answer in snapshot["answers"].items():
        assert answer["contract"] == DECISION_QUESTION_CONTRACT
        assert answer["provenance"]
        assert answer["freshness"]
        assert answer["quality"]
        assert "limitations" in answer
    assert snapshot["answers"]["what_we_know"]["count"] > 0
    assert snapshot["answers"]["which_sources_align"]["count"] == 1
    assert snapshot["answers"]["which_sources_disagree"]["count"] == 1
    assert snapshot["confidence"]["level"] in {
        "HIGH_EVIDENCE_CONFIDENCE",
        "PARTIAL_EVIDENCE_CONFIDENCE",
        "LOW_EVIDENCE_CONFIDENCE",
    }


def test_decision_engine_never_turns_missing_inputs_into_facts():
    snapshot = build_decision_engine_snapshot(observed_at_madrid="2026-07-28T10:10:00+02:00")

    assert snapshot["contract"] == DECISION_ENGINE_CONTRACT
    assert snapshot["known_count"] == 0
    assert snapshot["unknown_count"] >= 7
    assert snapshot["answers"]["what_we_know"]["items"] == []
    assert snapshot["answers"]["what_we_do_not_know"]["count"] >= 7
    assert snapshot["confidence"]["level"] == "LOW_EVIDENCE_CONFIDENCE"
    assert snapshot["guardrails"]["fake_data_created"] == 0
    assert snapshot["guardrails"]["predictions_created"] == 0
    assert snapshot["guardrails"]["picks_created"] == 0


def test_decision_engine_compares_only_explicit_source_claims():
    comparison = compare_source_claims(
        [
            {"claim_key": "score", "source": "provider-a", "value": "1-0"},
            {"claim_key": "score", "source": "provider-b", "value": "1-0"},
            {"claim_key": "status", "source": "provider-a", "value": "LIVE"},
            {"claim_key": "status", "source": "provider-b", "value": "FT"},
        ]
    )

    assert comparison["insufficient_comparison_data"] is False
    assert comparison["alignments"][0]["claim_key"] == "score"
    assert comparison["discrepancies"][0]["claim_key"] == "status"
    assert comparison["discrepancies"][0]["certification_state"] == "REQUIRES_REVIEW"


def test_decision_engine_registry_developer_center_and_sentinel_are_updated():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    sentinel = build_decision_engine_contract_snapshot(ROOT, VERSION)
    clear_project_snapshot_cache()
    developer = build_developer_center_snapshot(ROOT, VERSION, {})
    roadmap = {item["name"]: item for item in developer["roadmap"]["modules"]}

    assert capabilities["decision_engine"]["state"] == "INTEGRATED"
    assert capabilities["decision_engine"]["contract"] == DECISION_ENGINE_CONTRACT
    assert roadmap["Decision Engine"]["state"] == "COMPLETED"
    assert sentinel["validation_result"] == "PASS"


def test_decision_engine_is_read_only_and_diagnostic_only():
    metadata = decision_engine_snapshot()
    imports = _module_imports(ROOT / "engines" / "decision_engine.py")
    source = (ROOT / "engines" / "decision_engine.py").read_text(encoding="utf-8")

    assert metadata["guardrails"]["external_calls"] == 0
    assert metadata["guardrails"]["database_writes"] == 0
    assert metadata["guardrails"]["telegram_sends"] == 0
    assert metadata["guardrails"]["stripe_calls"] == 0
    assert metadata["guardrails"]["generative_ai_calls"] == 0
    assert metadata["guardrails"]["picks_created"] == 0
    assert metadata["guardrails"]["predictions_created"] == 0
    assert metadata["guardrails"]["automatic_actions"] == 0
    assert {"sqlite3", "requests", "urllib", "flask", "stripe", "openai", "bs4", "selenium", "playwright"} & imports == set()
    assert ".commit(" not in source
    assert "urlopen(" not in source
    assert "Session(" not in source
