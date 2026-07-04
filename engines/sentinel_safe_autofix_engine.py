"""V892 safe autofix planner for Autonomous Company Sentinel."""
from __future__ import annotations

from typing import Any

from engines.sentinel_autofix_planner_engine import build_autofix_plan


SENTINEL_SAFE_AUTOFIX_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"


def build_safe_autofix_plan(issues: list[dict[str, Any]]) -> dict[str, Any]:
    plan = build_autofix_plan(issues)
    plan["engine_version"] = SENTINEL_SAFE_AUTOFIX_VERSION
    plan["safe_policy"] = {
        "default_apply": False,
        "env_required": "AUTONOMOUS_SENTINEL_AUTOFIX=1",
        "dangerous_requires_codex": True,
    }
    return plan
