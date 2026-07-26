"""Static and pure-runtime gate for MATCH-INTELLIGENCE-EVIDENCE-V1."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from engines.match_intelligence_engine import (
    MATCH_INTELLIGENCE_CONSUMERS,
    MATCH_INTELLIGENCE_CONTRACT,
    build_match_intelligence,
    match_intelligence_snapshot,
)
from engines.sentinel_autopilot_engine import (
    build_v944_match_center_foundation_contract_snapshot,
)
from engines.sports_platform_contracts import (
    build_sports_platform_contract_registry,
)


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    contract = match_intelligence_snapshot()
    empty = build_match_intelligence()
    registry = build_sports_platform_contract_registry(ROOT)
    sentinel = build_v944_match_center_foundation_contract_snapshot(ROOT, "")
    capabilities = {
        item["key"]: item for item in registry.get("capabilities") or []
    }

    require(contract.get("contract") == MATCH_INTELLIGENCE_CONTRACT, "contract")
    require(
        set(contract.get("consumers") or []) == set(MATCH_INTELLIGENCE_CONSUMERS),
        "consumers",
    )
    require(
        empty.get("certification_state") == "INSUFFICIENT_DATA",
        "empty_state",
    )
    require(empty.get("no_fake_data") is True, "no_fake_data")
    require(
        (empty.get("diagnostics") or {}).get("database_writes") == 0,
        "database_writes",
    )
    require(
        (empty.get("diagnostics") or {}).get("external_calls") == 0,
        "external_calls",
    )
    require(
        (empty.get("diagnostics") or {}).get("telegram_sends") == 0,
        "telegram_sends",
    )
    require(
        (empty.get("diagnostics") or {}).get("generative_ai_calls") == 0,
        "generative_ai_calls",
    )
    require(
        (empty.get("quality") or {}).get("numeric_confidence_score") is None,
        "invented_confidence",
    )
    require(
        (capabilities.get("match_intelligence_core") or {}).get("state")
        == "INTEGRATED",
        "platform_registry",
    )
    require(sentinel.get("validation_result") == "PASS", "sentinel_contract")

    result = {
        "ok": not failures,
        "contract": MATCH_INTELLIGENCE_CONTRACT,
        "consumers": list(MATCH_INTELLIGENCE_CONSUMERS),
        "empty_state": empty.get("certification_state"),
        "sentinel": sentinel.get("validation_result"),
        "guardrails": empty.get("diagnostics"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
