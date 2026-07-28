#!/usr/bin/env python3
"""Static and pure-runtime gate for NeMeSiS Decision Engine."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.decision_engine import (
    DECISION_ENGINE_CONTRACT,
    build_decision_engine_snapshot,
    decision_engine_snapshot,
)
from engines.project_operating_system_engine import build_developer_center_snapshot, clear_project_snapshot_cache
from engines.sentinel_autopilot_engine import build_decision_engine_contract_snapshot
from engines.sports_intelligence_gateway_engine import build_sports_intelligence_gateway_snapshot
from engines.sports_platform_contracts import build_sports_platform_contract_registry


def _module_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8").lstrip("\ufeff")
    tree = ast.parse(source)
    return {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    gateway = build_sports_intelligence_gateway_snapshot(
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
    snapshot = build_decision_engine_snapshot(
        sports_core={"contract": "SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1", "source": "domain_snapshot"},
        sports_knowledge={"contract": "SPORTS-KNOWLEDGE-LAYER-V1", "evidence": [{"kind": "form", "label": "Forma disponible", "source": "knowledge"}]},
        sports_graph={"contract": "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1", "relationships": [{"relationship": "team_has_match", "target": "match-1", "source": "graph"}]},
        match_intelligence={"contract": "MATCH-INTELLIGENCE-EVIDENCE-V1", "conclusions": {"phase": "En juego"}, "certification_state": "PARTIALLY_VERIFIED"},
        shark={"contract": "SHARK-INTELLIGENCE-PLATFORM-V1", "claims": [{"id": "state", "body": "Dato con evidencia parcial.", "source": "match_intelligence", "evidence": ["phase"], "certification_state": "PARTIALLY_VERIFIED"}]},
        gateway=gateway,
        user_intelligence={"contract": "USER-INTELLIGENCE-PLATFORM-V1", "signals": [{"key": "team", "label": "Club Norte", "state": "VERIFIED", "source": "first-party"}]},
        source_claims=[
            {"claim_key": "score", "source": "provider-a", "value": "1-0", "evidence": "cache-a", "quality": "VERIFIED"},
            {"claim_key": "score", "source": "provider-b", "value": "1-0", "evidence": "cache-b", "quality": "VERIFIED"},
            {"claim_key": "minute", "source": "provider-a", "value": "68", "evidence": "cache-a", "quality": "VERIFIED"},
            {"claim_key": "minute", "source": "provider-b", "value": "70", "evidence": "cache-b", "quality": "VERIFIED"},
        ],
        observed_at_madrid="2026-07-28T10:10:00+02:00",
    )
    metadata = decision_engine_snapshot()
    sentinel = build_decision_engine_contract_snapshot(ROOT, version)
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    clear_project_snapshot_cache()
    developer = build_developer_center_snapshot(ROOT, version, {})
    roadmap = {item["name"]: item for item in developer["roadmap"]["modules"]}
    imports = _module_imports(ROOT / "engines" / "decision_engine.py")
    source = (ROOT / "engines" / "decision_engine.py").read_text(encoding="utf-8")

    require(snapshot["contract"] == DECISION_ENGINE_CONTRACT, "contract")
    require(set(snapshot["questions"]) == {
        "what_we_know",
        "what_we_do_not_know",
        "what_evidence_exists",
        "what_evidence_is_missing",
        "what_changed",
        "which_sources_align",
        "which_sources_disagree",
        "data_quality",
        "confidence",
    }, "questions")
    require(snapshot["answers"]["what_we_know"]["count"] > 0, "known")
    require(snapshot["answers"]["what_evidence_exists"]["count"] > 0, "evidence_exists")
    require(snapshot["answers"]["which_sources_align"]["count"] == 1, "source_alignment")
    require(snapshot["answers"]["which_sources_disagree"]["count"] == 1, "source_discrepancy")
    require(snapshot["confidence"]["score"] >= 0, "confidence_score")
    for answer in snapshot["answers"].values():
        require(bool(answer.get("provenance")), "answer_provenance")
        require(bool(answer.get("freshness")), "answer_freshness")
        require(bool(answer.get("quality")), "answer_quality")
        require("limitations" in answer, "answer_limitations")
    require(snapshot["guardrails"]["external_calls"] == 0, "external_calls")
    require(snapshot["guardrails"]["database_writes"] == 0, "database_writes")
    require(snapshot["guardrails"]["telegram_sends"] == 0, "telegram_sends")
    require(snapshot["guardrails"]["stripe_calls"] == 0, "stripe_calls")
    require(snapshot["guardrails"]["generative_ai_calls"] == 0, "generative_ai")
    require(snapshot["guardrails"]["picks_created"] == 0, "picks")
    require(snapshot["guardrails"]["predictions_created"] == 0, "predictions")
    require(snapshot["guardrails"]["automatic_actions"] == 0, "automatic_actions")
    require(metadata["guardrails"]["external_calls"] == 0, "metadata_external")
    require(sentinel["validation_result"] == "PASS", "sentinel")
    require((capabilities.get("decision_engine") or {}).get("state") == "INTEGRATED", "registry")
    require(roadmap["Decision Engine"]["state"] == "COMPLETED", "roadmap")
    require({"sqlite3", "requests", "urllib", "flask", "stripe", "openai", "bs4", "selenium", "playwright"} & imports == set(), "unsafe_imports")
    require(".commit(" not in source, "commit_call")
    require("urlopen(" not in source and "Session(" not in source, "network_call")

    result = {
        "ok": not failures,
        "contract": DECISION_ENGINE_CONTRACT,
        "known_count": snapshot["known_count"],
        "unknown_count": snapshot["unknown_count"],
        "alignments": len(snapshot["source_alignment"]["alignments"]),
        "discrepancies": len(snapshot["source_alignment"]["discrepancies"]),
        "confidence": snapshot["confidence"],
        "sentinel": sentinel["validation_result"],
        "registry": (capabilities.get("decision_engine") or {}).get("state"),
        "roadmap": roadmap.get("Decision Engine", {}).get("state"),
        "guardrails": snapshot["guardrails"],
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
