"""Sentinel Issue-to-Improvement workflow.

This module converts Continuous SHARK Sentinel diagnostics into a safe
improvement workflow. It never edits code, deploys, touches secrets, mutates
payments/users, sends Telegram, calls external APIs, or invents product data.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Any


ISSUE_LIFECYCLE = [
    "open",
    "acknowledged",
    "grouped",
    "planned",
    "codex_prompt_ready",
    "in_progress",
    "safe_fixed",
    "needs_deploy",
    "deployed_pending_validation",
    "resolved",
    "recurring",
    "ignored",
]

SAFE_ACTIONS = [
    "deduplicar incidencias",
    "recalcular prioridad",
    "marcar issue como reconocido",
    "actualizar estado",
    "regenerar reportes",
    "limpiar cache propia del Sentinel",
    "generar tarea",
    "cerrar issue si revalidación local lo confirma",
]

APPROVAL_REQUIRED_ACTIONS = [
    "cambiar app.py/templates/CSS con Codex",
    "ejecutar deploy",
    "usar credenciales reales",
    "enviar Telegram test real",
    "sincronizar proveedor real",
    "modificar datos de membresía",
    "cerrar incidencia que depende de Render real",
]

BLOCKED_ACTIONS = [
    "modificar código automáticamente",
    "hacer deploy automático",
    "tocar secretos",
    "tocar pagos reales",
    "borrar usuarios",
    "borrar DB",
    "enviar Telegram masivo",
    "inventar picks/cuotas/resultados",
]

PROMPT_TYPES = {
    "visual": "Fix visual móvil/PC",
    "route": "Fix rutas/botones",
    "admin": "Fix admin command center",
    "data": "Fix datos reales/empty states",
    "telegram": "Fix Telegram premium",
    "shark": "Fix SHARK IA",
    "membership": "Fix pagos/membresías",
    "security": "Fix security/runtime",
    "release": "Fix release/ZIP",
    "generic": "Fix producto general",
}

V883_VISUAL_WORKER_WORKFLOW = {
    "name": "SHARK Visual Worker",
    "modes": ["visual-worker", "company-worker", "full-company-qa"],
    "creates": ["issues", "grouped_issues", "improvement_tasks", "codex_prompts", "revalidation_notes"],
    "safe_actions": [
        "deduplicar incidencias",
        "generar tarea",
        "crear tarea del Visual Company Worker",
        "marcar pendiente de browser QA",
        "marcar pendiente de Render real",
    ],
    "approval_required_actions": APPROVAL_REQUIRED_ACTIONS,
    "blocked_actions": BLOCKED_ACTIONS,
    "no_auto_code": True,
    "no_auto_deploy": True,
    "no_secret_access": True,
    "no_fake_data": True,
}


@dataclass(frozen=True)
class WorkflowTask:
    task_id: str
    title: str
    category: str
    severity: str
    priority_score: int
    issues: list[dict[str, Any]]
    codex_prompt: str
    safe_fix_available: bool
    requires_codex: bool
    requires_admin_approval: bool
    checklist: list[str]


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return f"{prefix}-" + sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def _severity_weight(severity: str) -> int:
    return {
        "critical": 100,
        "high": 75,
        "medium": 45,
        "low": 20,
        "info": 8,
    }.get(str(severity or "info").lower(), 8)


def _category(issue: dict[str, Any]) -> str:
    category = str(issue.get("category") or "generic").lower()
    route = str(issue.get("route") or "")
    title = str(issue.get("title") or "").lower()
    if "admin" in route:
        return "admin"
    if "telegram" in route or "telegram" in title:
        return "telegram"
    if "shark" in route or "shark" in title:
        return "shark"
    if "payment" in route or "membership" in route or "membres" in title:
        return "membership"
    if "runtime" in route or "secret" in title or "security" in category:
        return "security"
    if "route" in category or "404" in title or "button" in title:
        return "route"
    if "data" in category or "empty" in title or "provider" in title:
        return "data"
    if "visual" in category or "mobile" in title or "overflow" in title:
        return "visual"
    return category if category in PROMPT_TYPES else "generic"


def normalize_issue(issue: dict[str, Any], version: str = "") -> dict[str, Any]:
    category = _category(issue)
    severity = str(issue.get("severity") or "info").lower()
    affected_routes = [issue.get("route")] if issue.get("route") else []
    affected_profiles = [issue.get("profile")] if issue.get("profile") else []
    issue_id = issue.get("issue_id") or issue.get("id") or _stable_id("ISSUE", category, severity, issue.get("title"), affected_routes)
    priority = _severity_weight(severity) + min(25, int(issue.get("occurrence_count") or 1) * 5)
    return {
        "issue_id": issue_id,
        "title": issue.get("title") or "Incidencia Sentinel",
        "description": issue.get("description") or issue.get("evidence") or "Incidencia detectada por Sentinel.",
        "category": category,
        "severity": severity,
        "affected_routes": affected_routes,
        "affected_profiles": affected_profiles,
        "evidence": issue.get("evidence") or "",
        "first_seen": issue.get("first_seen") or issue.get("timestamp_madrid") or "",
        "last_seen": issue.get("last_seen") or issue.get("timestamp_madrid") or "",
        "occurrence_count": int(issue.get("occurrence_count") or 1),
        "status": issue.get("status") if issue.get("status") in ISSUE_LIFECYCLE else "open",
        "priority_score": priority,
        "suggested_fix": issue.get("suggested_fix") or "Revisar con Codex usando prompt generado y validar con checks.",
        "safe_fix_available": bool(issue.get("safe_auto_fix_possible")),
        "requires_codex": True,
        "requires_admin_approval": True,
        "codex_prompt": issue.get("codex_prompt") or "",
        "linked_task_id": "",
        "revalidation_notes": "Revalidar ruta/check tras aplicar mejora.",
        "version": version,
    }


def group_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for issue in issues:
        key = f"{issue['category']}:{issue['severity']}:{','.join(issue['affected_routes'])}:{issue['title'][:64]}"
        item = grouped.setdefault(
            key,
            {
                "group_id": _stable_id("GROUP", key),
                "category": issue["category"],
                "severity": issue["severity"],
                "title": issue["title"],
                "issues": [],
                "affected_routes": set(),
                "affected_profiles": set(),
                "priority_score": 0,
                "status": "grouped",
            },
        )
        item["issues"].append(issue)
        item["affected_routes"].update(issue["affected_routes"])
        item["affected_profiles"].update(issue["affected_profiles"])
        item["priority_score"] += issue["priority_score"]
    result = []
    for item in grouped.values():
        item["affected_routes"] = sorted(item["affected_routes"])
        item["affected_profiles"] = sorted(item["affected_profiles"])
        result.append(item)
    return sorted(result, key=lambda item: item["priority_score"], reverse=True)


def suggested_next_version(version: str, groups: list[dict[str, Any]]) -> str:
    focus = groups[0]["category"].upper() if groups else "QA"
    base = "VNEXT_SENTINEL_WORKFLOW"
    if version.startswith("V") and "_" in version:
        number = version.split("_", 1)[0].lstrip("V")
        if number.isdigit():
            base = f"V{int(number) + 1}_{focus}_SENTINEL_IMPROVEMENT"
    return base + "_FINAL"


def build_codex_prompt(version: str, group: dict[str, Any]) -> str:
    prompt_type = PROMPT_TYPES.get(group["category"], PROMPT_TYPES["generic"])
    routes = ", ".join(group.get("affected_routes") or ["rutas afectadas no especificadas"])
    titles = "; ".join(issue["title"] for issue in group["issues"][:6])
    return (
        f"Actúa como equipo completo de NeMeSiS SHARK PRO. Base real: {version}. "
        f"Tipo: {prompt_type}. Rutas afectadas: {routes}. Incidencias: {titles}. "
        "Preserva V818-V864, DB_PATH, usuarios, pagos, Telegram, SHARK, API-SPORTS y seguridad. "
        "No inventes datos, no toques secretos, no hagas deploy automático. "
        "Aplica una mejora controlada, valida py_compile, compileall, checks Sentinel, smoke y ZIP limpio. "
        "Separa probado local, probado real y bloqueado con honestidad."
    )


def build_improvement_tasks(version: str, grouped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    for group in grouped:
        prompt = build_codex_prompt(version, group)
        task = WorkflowTask(
            task_id=_stable_id("TASK", group["group_id"], version),
            title=f"{PROMPT_TYPES.get(group['category'], 'Mejora producto')}: {group['title']}",
            category=group["category"],
            severity=group["severity"],
            priority_score=min(100, group["priority_score"]),
            issues=group["issues"],
            codex_prompt=prompt,
            safe_fix_available=any(issue["safe_fix_available"] for issue in group["issues"]),
            requires_codex=True,
            requires_admin_approval=True,
            checklist=[
                "Confirmar base real y rutas afectadas",
                "Aplicar cambio controlado con Codex/Admin",
                "Ejecutar checks locales",
                "Revalidar incidencia",
                "Preparar ZIP limpio si procede",
            ],
        )
        tasks.append(task.__dict__)
    return tasks


def build_workflow_from_sentinel_result(sentinel_result: dict[str, Any], version: str = "") -> dict[str, Any]:
    issues = [normalize_issue(issue, version) for issue in sentinel_result.get("issues", [])]
    grouped = group_issues(issues)
    tasks = build_improvement_tasks(version, grouped)
    return {
        "version": version,
        "workflow_status": "ready",
        "issue_lifecycle": ISSUE_LIFECYCLE,
        "open_issues": [issue for issue in issues if issue["status"] in {"open", "acknowledged", "grouped", "planned"}],
        "grouped_issues": grouped,
        "improvement_tasks": tasks,
        "suggested_next_version": suggested_next_version(version, grouped),
        "codex_prompts": [task["codex_prompt"] for task in tasks],
        "safe_actions": SAFE_ACTIONS,
        "approval_required_actions": APPROVAL_REQUIRED_ACTIONS,
        "blocked_actions": BLOCKED_ACTIONS,
        "resolved_candidates": [issue for issue in issues if issue["status"] in {"safe_fixed", "deployed_pending_validation"}],
        "recurring_issues": [issue for issue in issues if issue["occurrence_count"] > 1 or issue["status"] == "recurring"],
        "summary": {
            "issues_total": len(issues),
            "groups_total": len(grouped),
            "tasks_total": len(tasks),
            "critical_total": sum(1 for issue in issues if issue["severity"] == "critical"),
            "high_total": sum(1 for issue in issues if issue["severity"] == "high"),
            "requires_codex_total": len(tasks),
            "safe_fix_total": sum(1 for task in tasks if task["safe_fix_available"]),
        },
        "safety": {
            "no_code_writes": True,
            "no_deploy": True,
            "no_secret_access": True,
            "no_payments_mutation": True,
            "no_user_deletion": True,
            "no_real_telegram_send": True,
            "no_external_api_calls": True,
            "no_fake_data": True,
        },
        "visual_company_worker_v883": V883_VISUAL_WORKER_WORKFLOW,
    }


def build_workflow_summary(version: str = "", sentinel_result: dict[str, Any] | None = None) -> dict[str, Any]:
    sentinel_result = sentinel_result or {"issues": []}
    return build_workflow_from_sentinel_result(sentinel_result, version)


def update_issue_state(issue: dict[str, Any], status: str) -> dict[str, Any]:
    normalized = normalize_issue(issue)
    normalized["status"] = status if status in ISSUE_LIFECYCLE else "acknowledged"
    normalized["revalidation_notes"] = "Estado actualizado en workflow admin; requiere revalidación posterior."
    return normalized
