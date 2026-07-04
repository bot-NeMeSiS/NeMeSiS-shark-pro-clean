"""V892 user/admin journey wrapper for Autonomous Company Sentinel."""
from __future__ import annotations

from typing import Any

from engines.sentinel_user_journey_engine import run_user_journey_checks


SENTINEL_USER_ADMIN_JOURNEY_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"


def run_user_admin_journey_scan(flask_client: Any, mode: str = "safe_scan") -> dict[str, Any]:
    result = run_user_journey_checks(flask_client, mode=mode)
    result["engine_version"] = SENTINEL_USER_ADMIN_JOURNEY_VERSION
    result["worker_area"] = "user_admin_journey"
    return result
