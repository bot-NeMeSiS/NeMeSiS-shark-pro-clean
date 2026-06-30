"""Continuous SHARK Sentinel loop.

Safe permanent inspection layer. It coordinates route/user/profile diagnostics
using the existing SHARK Sentinel engine, compares against an internal baseline,
and returns prioritized issues/prompts without code writes, deploys, secrets,
DB deletion, payment mutation, Telegram sending, or fake data.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha1
from typing import Any
from zoneinfo import ZoneInfo

from engines.shark_sentinel_engine import (
    FORBIDDEN_AUTOMATIC_ACTIONS,
    PROFILES,
    build_codex_prompts,
    build_recommended_actions,
    build_static_sentinel_summary,
    run_static_flask_inspection,
    summarize_issues_by,
)
from engines.sentinel_improvement_workflow_engine import build_workflow_from_sentinel_result


MADRID_TZ = ZoneInfo("Europe/Madrid")

CYCLES = {
    "quick": ["runtime", "admin protection", "master tick protection", "critical routes"],
    "client": ["visitor", "FREE", "PRO", "ELITE", "client navigation"],
    "admin": ["dashboard", "Company OS", "Company Audit", "Auto Improvement", "users", "payments"],
    "visual": ["visual markers", "bottom nav", "floating SHARK", "mojibake", "empty states"],
    "data": ["picks", "live", "fixtures", "odds", "safe states", "API guard"],
    "telegram": ["configuration", "dedupe", "no filler", "real-send honesty"],
    "improvement": ["priorities", "safe actions", "approval required", "Codex prompts"],
    "workflow": ["issue detection", "dedupe", "grouping", "tasks", "Codex prompts", "revalidation"],
    "full": ["quick", "client", "admin", "visual", "data", "telegram", "improvement"],
}

ISSUE_STATUSES = [
    "open",
    "acknowledged",
    "suggested",
    "safe_fixed",
    "needs_codex",
    "needs_admin_approval",
    "ignored",
    "resolved",
    "recurring",
]

ACTION_LEVELS = {
    "level_1_diagnostic": ["detectar", "reportar", "priorizar", "generar prompt"],
    "level_2_safe_internal_fix": ["limpiar cache propia", "marcar issue revisado", "regenerar reporte", "deduplicar incidencias", "recalcular score interno"],
    "level_3_approval_required": ["sync datos", "Telegram test", "archivar picks", "tocar membresias", "preparar release", "ejecutar prompt Codex", "cambios visuales/templates/CSS", "cambios DB real"],
    "level_4_forbidden_automatic": FORBIDDEN_AUTOMATIC_ACTIONS,
}

V864_VISUAL_RULES = [
    "cards_gigantes_o_pobres",
    "posible_overflow_horizontal",
    "bottom_nav_duplicada",
    "floating_shark_duplicado",
    "admin_con_navegacion_cliente",
    "section_headers_ausentes",
    "empty_states_pobres",
    "mojibake_visible",
    "cta_principal_ausente",
    "cards_sin_jerarquia",
    "mobile_safe_area_debil",
    "pc_sin_densidad_dashboard",
]


def madrid_now() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def make_run_id(mode: str) -> str:
    raw = f"{mode}:{madrid_now()}"
    return "CSL-" + sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def _normalize_mode(mode: str | None) -> str:
    mode = (mode or "quick").strip().lower()
    if mode == "diagnostic":
        return "quick"
    if mode not in CYCLES:
        return "quick"
    return mode


def _decorate_issue(issue: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "issue_id": issue.get("id") or "ISSUE",
        "run_id": run_id,
        "timestamp_madrid": issue.get("timestamp_madrid") or madrid_now(),
        "profile": issue.get("profile") or "UNKNOWN",
        "route": issue.get("route") or "",
        "screen_area": issue.get("route") or "",
        "category": issue.get("category") or "unknown",
        "severity": issue.get("severity") or "info",
        "title": issue.get("title") or "Incidencia detectada",
        "description": issue.get("description") or "",
        "evidence": issue.get("evidence") or "",
        "expected_behavior": issue.get("expected_behavior") or "",
        "actual_behavior": issue.get("actual_behavior") or "",
        "suggested_fix": issue.get("suggested_fix") or "",
        "safe_auto_fix_possible": bool(issue.get("safe_auto_fix_possible")),
        "approval_required": bool(issue.get("requires_admin_approval")),
        "codex_prompt": issue.get("codex_prompt_suggestion") or "",
        "status": "open",
        "first_seen": issue.get("timestamp_madrid") or madrid_now(),
        "last_seen": madrid_now(),
        "occurrence_count": 1,
    }


def build_continuous_sentinel_summary(version: str = "") -> dict[str, Any]:
    base = build_static_sentinel_summary(version)
    return {
        "version": version,
        "sentinel_status": "continuous_loop_ready",
        "last_cycle": None,
        "global_score": None,
        "cycles": CYCLES,
        "profiles": list(PROFILES.keys()),
        "issues_open": 0,
        "issues_critical": 0,
        "issues_recurring": 0,
        "issues_by_category": {},
        "issues_by_profile": {},
        "routes_expected": sum(len(routes) for routes in PROFILES.values()),
        "safe_actions": ACTION_LEVELS["level_2_safe_internal_fix"],
        "approval_required_actions": ACTION_LEVELS["level_3_approval_required"],
        "forbidden_automatic_actions": ACTION_LEVELS["level_4_forbidden_automatic"],
        "codex_prompts": base["codex_prompt_suggestions"],
        "next_focus": ["Ejecutar quick cycle", "Revisar issues high/critical", "Usar prompts Codex con aprobacion"],
        "history_recent": [],
        "browser_note": "browser visual QA not available locally unless Playwright is installed and run explicitly",
        "visual_rules_v864": V864_VISUAL_RULES,
        "visual_big_leap_ready": True,
        "improvement_workflow_ready": True,
        "workflow_cycle": "Detectar -> Priorizar -> Proponer -> Aplicar con Codex/Admin -> Revalidar -> Resolver",
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }


def run_continuous_sentinel_cycle(client: Any, version: str = "", mode: str = "quick", dry_run: bool = True) -> dict[str, Any]:
    mode = _normalize_mode(mode)
    run_id = make_run_id(mode)
    static_result = run_static_flask_inspection(client, version)
    issues = [_decorate_issue(issue, run_id) for issue in static_result.get("issues", [])]
    by_severity = summarize_issues_by(issues, "severity")
    by_category = summarize_issues_by(issues, "category")
    by_profile = summarize_issues_by(issues, "profile")
    high_or_critical = sum(1 for issue in issues if issue["severity"] in {"critical", "high"})
    score = max(0, round(10 - high_or_critical * 1.5 - len(issues) * 0.05, 1))
    result = {
        "run_id": run_id,
        "timestamp_madrid": madrid_now(),
        "version": version,
        "mode": mode,
        "dry_run": bool(dry_run),
        "status": "completed_diagnostic_only",
        "score": score,
        "routes_checked": static_result.get("routes_reviewed", 0),
        "profiles_checked": static_result.get("profiles", []),
        "issues": issues,
        "warnings": [
            "No browser real ejecutado en modo static.",
            "No se ejecutan acciones peligrosas.",
            "Los hallazgos de texto tecnico son candidatos a revisar, no datos inventados.",
            "Reglas visuales V864 revisadas por marcadores estaticos; browser QA es opcional.",
        ],
        "issues_by_severity": by_severity,
        "issues_by_category": by_category,
        "issues_by_profile": by_profile,
        "issues_open": len(issues),
        "issues_critical": by_severity.get("critical", 0),
        "issues_recurring": 0,
        "safe_actions": ACTION_LEVELS["level_2_safe_internal_fix"],
        "approval_required_actions": ACTION_LEVELS["level_3_approval_required"],
        "forbidden_automatic_actions": ACTION_LEVELS["level_4_forbidden_automatic"],
        "codex_prompts": build_codex_prompts(static_result.get("issues", [])),
        "recommended_actions": build_recommended_actions(static_result.get("issues", [])),
        "next_focus": ["Resolver high/critical primero", "Deduplicar issues recurrentes", "Preparar prompt Codex solo con aprobacion"],
        "comparison": {
            "against_expected_baseline": "routes/profiles/status/safety checked",
            "against_last_cycle": "no persisted previous cycle in this safe local run",
            "against_visual_reference_internal": "V864 visual rules checked by static markers only",
            "against_commercial_rules": "no fake data and no irresponsible betting claims checked",
        },
        "visual_rules_v864": V864_VISUAL_RULES,
        "visual_big_leap_ready": True,
        "improvement_workflow_ready": True,
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }
    if mode == "workflow":
        result["workflow"] = build_workflow_from_sentinel_result(result, version)
    return result
