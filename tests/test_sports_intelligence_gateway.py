from __future__ import annotations

import ast
from pathlib import Path

from engines.project_operating_system_engine import build_developer_center_snapshot, clear_project_snapshot_cache
from engines.sentinel_autopilot_engine import build_sports_intelligence_gateway_contract_snapshot
from engines.sports_intelligence_gateway_engine import (
    SOURCE_COMPLIANCE_CONTRACT,
    SOURCE_EVIDENCE_CONTRACT,
    SOURCE_HEALTH_CONTRACT,
    SOURCE_REGISTRY_CONTRACT,
    SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
    build_sports_intelligence_gateway_snapshot,
    evaluate_source_compliance,
    register_source,
    sports_intelligence_gateway_snapshot,
)
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


def test_gateway_registers_sources_without_connecting_them():
    snapshot = build_sports_intelligence_gateway_snapshot(
        [
            {
                "source_id": "official-league-feed",
                "name": "Official League Feed",
                "license": "commercial-rights-reviewed",
                "provenance": "web oficial",
                "source_type": "API",
                "state": "APPROVED",
                "coverage": "fixtures, results",
                "quality": "VERIFIED",
                "latency": "15m",
                "last_sync": "2026-07-28T10:00:00+02:00",
                "commercial_use_allowed": True,
                "attribution_required": True,
            }
        ],
        observed_at_madrid="2026-07-28T10:05:00+02:00",
    )

    assert snapshot["contract"] == SPORTS_INTELLIGENCE_GATEWAY_CONTRACT
    assert snapshot["source_registry_contract"] == SOURCE_REGISTRY_CONTRACT
    assert snapshot["source_compliance_contract"] == SOURCE_COMPLIANCE_CONTRACT
    assert snapshot["source_health_contract"] == SOURCE_HEALTH_CONTRACT
    assert snapshot["source_evidence_contract"] == SOURCE_EVIDENCE_CONTRACT
    assert snapshot["summary"] == {
        "registered_sources": 1,
        "approved_sources": 1,
        "pending_sources": 0,
        "connected_sources": 0,
        "automatic_connections": 0,
    }
    assert snapshot["compliance"][0]["connection_allowed"] is True
    assert snapshot["sources"][0]["connection_enabled"] is False
    assert snapshot["health"][0]["external_probe_performed"] is False
    assert snapshot["guardrails"]["provider_connections_enabled"] == 0
    assert snapshot["guardrails"]["external_calls"] == 0
    assert snapshot["guardrails"]["database_writes"] == 0
    assert snapshot["guardrails"]["telegram_sends"] == 0
    assert snapshot["guardrails"]["stripe_calls"] == 0


def test_gateway_blocks_sources_without_commercial_rights_or_attribution_review():
    source = register_source(
        {
            "source_id": "unknown-feed",
            "name": "Unknown Feed",
            "source_type": "RSS",
            "state": "REGISTERED",
            "coverage": "No disponible",
            "quality": "REQUIRES_REVIEW",
            "commercial_use_allowed": False,
        }
    )
    compliance = evaluate_source_compliance(source)

    assert compliance["contract"] == SOURCE_COMPLIANCE_CONTRACT
    assert compliance["state"] == "PENDING_APPROVAL"
    assert compliance["connection_allowed"] is False
    assert compliance["requires_human_approval"] is True
    assert "commercial_use_allowed" in compliance["missing_requirements"]
    assert "attribution_required" in compliance["missing_requirements"]
    assert "mass_scraping" in compliance["blocked_practices"]
    assert "paywall_bypass" in compliance["blocked_practices"]
    assert "protected_image_reuse" in compliance["blocked_practices"]


def test_gateway_requires_provenance_freshness_evidence_quality_and_limitations():
    snapshot = build_sports_intelligence_gateway_snapshot(
        [{"source_id": "open-data-sample", "source_type": "OPEN_DATA", "state": "REGISTERED"}],
        observed_at_madrid="2026-07-28T10:05:00+02:00",
    )

    data_contract = snapshot["data_contract"]
    evidence = snapshot["evidence_registry"][0]

    assert data_contract["provenance_required"] is True
    assert data_contract["freshness_required"] is True
    assert data_contract["evidence_required"] is True
    assert data_contract["quality_required"] is True
    assert data_contract["limitations_required"] is True
    assert data_contract["no_fake_data"] is True
    assert evidence["contract"] == SOURCE_EVIDENCE_CONTRACT
    assert evidence["provenance"] == "No disponible"
    assert evidence["freshness"] == "No disponible"
    assert evidence["evidence"] == "No disponible"
    assert evidence["certification_state"] in {"REQUIRES_REVIEW", "INSUFFICIENT_DATA"}


def test_gateway_registry_developer_center_and_sentinel_are_updated():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    sentinel = build_sports_intelligence_gateway_contract_snapshot(ROOT, VERSION)
    clear_project_snapshot_cache()
    developer = build_developer_center_snapshot(ROOT, VERSION, {})
    roadmap = {item["name"]: item for item in developer["roadmap"]["modules"]}

    assert capabilities["sports_intelligence_gateway"]["state"] == "INTEGRATED"
    assert capabilities["sports_intelligence_gateway"]["contract"] == SPORTS_INTELLIGENCE_GATEWAY_CONTRACT
    assert sentinel["validation_result"] == "PASS"
    assert roadmap["Sports Intelligence Gateway"]["state"] == "COMPLETED"


def test_gateway_engine_is_read_only_and_has_no_provider_connectors():
    metadata = sports_intelligence_gateway_snapshot()
    imports = _module_imports(ROOT / "engines" / "sports_intelligence_gateway_engine.py")
    source = (ROOT / "engines" / "sports_intelligence_gateway_engine.py").read_text(encoding="utf-8")

    assert metadata["guardrails"]["external_calls"] == 0
    assert metadata["guardrails"]["database_writes"] == 0
    assert metadata["guardrails"]["provider_connections_enabled"] == 0
    assert {"sqlite3", "requests", "urllib", "flask", "stripe", "openai", "bs4", "selenium", "playwright"} & imports == set()
    assert ".commit(" not in source
    assert "urlopen(" not in source
    assert "Session(" not in source
