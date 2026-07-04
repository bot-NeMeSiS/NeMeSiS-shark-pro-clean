"""Safe autofix planning for Autonomous Sentinel Worker."""
from __future__ import annotations

import os
from typing import Any


SAFE_AREAS = {"texts", "visual", "buttons_routes", "logos", "shark"}
DANGEROUS_AREAS = {"payments", "security", "render", "telegram", "sports", "picks", "admin", "route"}


def classify_autofix(issue: dict[str, Any]) -> dict[str, Any]:
    area = str(issue.get("area") or "").lower()
    severity = str(issue.get("severity") or "low").lower()
    safe = area in SAFE_AREAS and severity in {"low", "medium"}
    dangerous = area in DANGEROUS_AREAS or severity in {"critical", "high"}
    return {
        "issue_id": issue.get("id") or issue.get("issue_id") or "",
        "title": issue.get("title") or "Incidencia",
        "area": area,
        "severity": severity,
        "level": "SAFE_AUTOFIX" if safe and not dangerous else "DANGEROUS_REQUIRES_CODEX",
        "may_apply": bool(safe and not dangerous and os.getenv("AUTONOMOUS_SENTINEL_AUTOFIX", "0") == "1" and not os.getenv("RENDER")),
        "recommended_action": "Preparar microfix seguro local" if safe and not dangerous else "Generar prompt Codex y esperar aprobacion humana",
    }


def build_autofix_plan(issues: list[dict[str, Any]]) -> dict[str, Any]:
    plans = [classify_autofix(issue) for issue in issues]
    return {
        "autofix_apply_env": os.getenv("AUTONOMOUS_SENTINEL_AUTOFIX", "0"),
        "safe_autofix_count": sum(1 for item in plans if item["level"] == "SAFE_AUTOFIX"),
        "requires_codex_count": sum(1 for item in plans if item["level"] == "DANGEROUS_REQUIRES_CODEX"),
        "applied_changes": [],
        "dangerous_actions_executed": False,
        "plans": plans,
    }
