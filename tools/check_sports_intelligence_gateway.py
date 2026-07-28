#!/usr/bin/env python3
"""Static and pure-runtime gate for Sports Intelligence Gateway."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.project_operating_system_engine import build_developer_center_snapshot, clear_project_snapshot_cache
from engines.sentinel_autopilot_engine import build_sports_intelligence_gateway_contract_snapshot
from engines.sports_intelligence_gateway_engine import (
    SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
    build_sports_intelligence_gateway_snapshot,
    sports_intelligence_gateway_snapshot,
)
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
    snapshot = build_sports_intelligence_gateway_snapshot(
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
            },
            {
                "source_id": "pending-source",
                "name": "Pending Source",
                "source_type": "RSS",
                "state": "REGISTERED",
                "commercial_use_allowed": False,
            },
        ],
        observed_at_madrid="2026-07-28T10:05:00+02:00",
    )
    metadata = sports_intelligence_gateway_snapshot()
    sentinel = build_sports_intelligence_gateway_contract_snapshot(ROOT, version)
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    clear_project_snapshot_cache()
    developer = build_developer_center_snapshot(ROOT, version, {})
    roadmap = {item["name"]: item for item in developer["roadmap"]["modules"]}
    imports = _module_imports(ROOT / "engines" / "sports_intelligence_gateway_engine.py")
    source = (ROOT / "engines" / "sports_intelligence_gateway_engine.py").read_text(encoding="utf-8")

    require(snapshot["contract"] == SPORTS_INTELLIGENCE_GATEWAY_CONTRACT, "contract")
    require(snapshot["summary"]["registered_sources"] == 2, "registered_sources")
    require(snapshot["summary"]["approved_sources"] == 1, "approved_sources")
    require(snapshot["summary"]["pending_sources"] == 1, "pending_sources")
    require(snapshot["summary"]["connected_sources"] == 0, "connected_sources")
    require(snapshot["legal_policy"]["must_register_before_use"] is True, "register_before_use")
    require(snapshot["legal_policy"]["must_approve_before_use"] is True, "approve_before_use")
    require(snapshot["legal_policy"]["mass_scraping_allowed"] is False, "mass_scraping")
    require(snapshot["legal_policy"]["robots_bypass_allowed"] is False, "robots_bypass")
    require(snapshot["legal_policy"]["paywall_bypass_allowed"] is False, "paywall_bypass")
    require(snapshot["legal_policy"]["protected_image_reuse_allowed"] is False, "image_rights")
    require(snapshot["data_contract"]["provenance_required"] is True, "provenance")
    require(snapshot["data_contract"]["freshness_required"] is True, "freshness")
    require(snapshot["data_contract"]["evidence_required"] is True, "evidence")
    require(snapshot["data_contract"]["quality_required"] is True, "quality")
    require(snapshot["data_contract"]["limitations_required"] is True, "limitations")
    require(snapshot["guardrails"]["external_calls"] == 0, "external_calls")
    require(snapshot["guardrails"]["database_writes"] == 0, "database_writes")
    require(snapshot["guardrails"]["telegram_sends"] == 0, "telegram_sends")
    require(snapshot["guardrails"]["stripe_calls"] == 0, "stripe_calls")
    require(snapshot["guardrails"]["provider_connections_enabled"] == 0, "provider_connections")
    require(metadata["guardrails"]["external_calls"] == 0, "metadata_external_calls")
    require(sentinel["validation_result"] == "PASS", "sentinel")
    require((capabilities.get("sports_intelligence_gateway") or {}).get("state") == "INTEGRATED", "registry")
    require(roadmap["Sports Intelligence Gateway"]["state"] == "COMPLETED", "roadmap")
    require({"sqlite3", "requests", "urllib", "flask", "stripe", "openai", "bs4", "selenium", "playwright"} & imports == set(), "unsafe_imports")
    require(".commit(" not in source, "commit_call")
    require("urlopen(" not in source and "Session(" not in source, "network_call")

    result = {
        "ok": not failures,
        "contract": SPORTS_INTELLIGENCE_GATEWAY_CONTRACT,
        "registered_sources": snapshot["summary"]["registered_sources"],
        "approved_sources": snapshot["summary"]["approved_sources"],
        "pending_sources": snapshot["summary"]["pending_sources"],
        "connected_sources": snapshot["summary"]["connected_sources"],
        "sentinel": sentinel["validation_result"],
        "registry": (capabilities.get("sports_intelligence_gateway") or {}).get("state"),
        "roadmap": roadmap.get("Sports Intelligence Gateway", {}).get("state"),
        "guardrails": snapshot["guardrails"],
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
