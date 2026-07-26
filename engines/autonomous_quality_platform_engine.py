"""Controlled quality workflow for V939; autonomy stops before risky actions."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from engines.company_intelligence_engine import madrid_now_iso
from engines.recovery_simulator_engine import build_recovery_simulator_snapshot
from engines.version_regression_engine import build_version_regression_snapshot


QUALITY_FLOW = ("DETECT", "CLASSIFY", "EVIDENCE", "PRIORITIZE", "TASK", "CODEX_PROMPT", "APPROVAL", "FIX", "VERIFY", "CLOSE", "LEARN")
SAFE_AUTO_FIX_CATEGORIES = {
    "regenerate_report",
    "mark_internal_issue",
    "detect_mojibake",
    "create_safe_fallback_proposal",
    "update_internal_status",
    "create_codex_prompt",
    "create_checklist",
}
APPROVAL_REQUIRED_CATEGORIES = {
    "code",
    "routes",
    "authentication",
    "database",
    "payments",
    "telegram_send",
    "external_api",
    "deploy",
    "push",
    "delete",
    "secrets",
}


def classify_quality_action(category: str) -> dict[str, Any]:
    normalized = str(category or "").strip().lower()
    if normalized in SAFE_AUTO_FIX_CATEGORIES:
        return {"category": normalized, "policy": "SAFE_INTERNAL_ONLY", "approval_required": False, "execution_enabled": False}
    return {
        "category": normalized,
        "policy": "APPROVAL_REQUIRED",
        "approval_required": True,
        "execution_enabled": False,
    }


def build_quality_task(priority: dict[str, Any], app_version: str) -> dict[str, Any]:
    area = str(priority.get("area") or "unknown")
    state = str(priority.get("state") or "REQUIRES_REVIEW")
    identifier = hashlib.sha256(f"{app_version}|{area}|{state}".encode("utf-8")).hexdigest()[:20]
    return {
        "task_id": f"v939-{identifier}",
        "area": area,
        "priority": priority.get("priority") or "P3",
        "state": state,
        "evidence": priority.get("evidence"),
        "action": priority.get("action") or "Recopilar evidencia.",
        "approval_required": True,
        "automatic_fix_executed": False,
    }


def generate_quality_codex_prompt(task: dict[str, Any], app_version: str) -> str:
    return "\n".join((
        f"NeMeSiS SHARK PRO {app_version}",
        f"Tarea: {task.get('task_id', '')}",
        f"Area: {task.get('area', '')}",
        f"Prioridad: {task.get('priority', '')}",
        f"Estado de evidencia: {task.get('state', '')}",
        f"Accion: {task.get('action', '')}",
        "Confirma o refuta primero. No despliegues, no escribas DB real, no envies Telegram y no ejecutes pagos.",
        "Presenta cambio minimo, tests, impacto, rollback y aprobacion necesaria.",
    ))


def build_autonomous_quality_snapshot(
    root: str | Path,
    db_path: str | Path,
    app_version: str,
    company_snapshot: dict[str, Any],
    environment: str = "local",
) -> dict[str, Any]:
    priorities = list(company_snapshot.get("priorities") or [])
    tasks = [build_quality_task(priority, app_version) for priority in priorities]
    for task in tasks:
        task["codex_prompt"] = generate_quality_codex_prompt(task, app_version)
    regression = build_version_regression_snapshot(root, app_version)
    recovery = build_recovery_simulator_snapshot(root, db_path, app_version, environment)
    return {
        "ok": True,
        "version": app_version,
        "generated_at_madrid": madrid_now_iso(),
        "environment": environment,
        "flow": list(QUALITY_FLOW),
        "integrations": ["Continuous Sentinel", "Sentinel Workflow", "Visual Worker", "AutoPilot", "Operations Center", "Company Intelligence", "Regression Engine", "Recovery Simulator"],
        "tasks": tasks,
        "task_count": len(tasks),
        "regressions": regression,
        "recovery": recovery,
        "safe_auto_fix_categories": sorted(SAFE_AUTO_FIX_CATEGORIES),
        "approval_required_categories": sorted(APPROVAL_REQUIRED_CATEGORIES),
        "automatic_code_changes": False,
        "automatic_push": False,
        "automatic_deploy": False,
        "automatic_telegram": False,
        "automatic_payments": False,
        "automatic_database_changes": False,
        "automatic_weight_changes": False,
        "actions_executed": [],
        "production_modified": False,
    }

