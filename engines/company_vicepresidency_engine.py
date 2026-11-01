"""Acting Vice President: safe, read-only decision support for Company OS.

The owner remains President. This projects the existing hourly native review and
Cron receipts; it never starts workers, sends requests or authorizes mutations.
"""
from __future__ import annotations

from typing import Any, Iterable

CONTRACT = "NEMESIS-VICEPRESIDENCY-V1"
READOUT_CONTRACT = "NEMESIS-VP-READOUT-V1"
NATIVE_CONTRACT = "NEMESIS-NATIVE-WORKFORCE-REVIEW-V1"

READ_ACTIONS = frozenset({
    "READ_VERIFIED_RECEIPTS", "COMPARE_EVIDENCE",
    "CLASSIFY_INCIDENTS", "PRIORITIZE_EXISTING_TASKS",
})
PROPOSE_ACTIONS = frozenset({
    "DRAFT_FOUNDER_BRIEF", "PREPARE_WORK_ORDER",
    "SUGGEST_VISUAL_IMPROVEMENT", "RECOMMEND_BUDGET_CHANGE",
    "RECOMMEND_COMMERCIAL_EXPERIMENT",
})
APPROVAL_ACTIONS = frozenset({
    "CREATE_PR", "EDIT_CODE", "MERGE_PR", "DEPLOY",
    "CHANGE_PRICES", "CHANGE_MEMBERSHIPS", "CHANGE_USERS",
    "ACTIVATE_PROVIDER", "INCREASE_API_BUDGET", "PUBLISH_CONTENT",
    "SEND_TELEGRAM", "DELETE_DATA", "CHANGE_SECRETS",
})
FORBIDDEN_ACTIONS = frozenset({
    "CHARGE_CARD", "REFUND_PAYMENT", "PLACE_BET",
    "BULK_SEND_TELEGRAM", "BYPASS_SECURITY", "FORCE_PUSH",
    "REPLACE_PRODUCTION_DB",
})

# Software mandates, not independent models, employees or watchers.
ADVISORS = (
    ("strategy", "Estrategia y producto", "Hoja de ruta y prioridades"),
    ("finance", "Finanzas y costes", "Ingresos verificados, costes y obligaciones"),
    ("technology", "Arquitectura", "Render, rendimiento, backups y CI"),
    ("security", "Seguridad", "Permisos, secretos y privacidad"),
    ("legal", "Cumplimiento", "Licencias, legalidad y juego responsable"),
    ("sports", "Datos deportivos", "Fuentes, frescura, directos y resultados"),
    ("shark", "SHARK y pronósticos", "Evidencia, probabilidades y riesgos"),
    ("game_ui", "Videojuegos y Game UI/UX", "HUD, escudos, accesibilidad y QA"),
    ("growth", "Marketing y ventas", "Conversión sin afirmaciones ficticias"),
    ("customers", "Clientes y soporte", "Usabilidad, confianza y retención"),
)


def _text(value: Any, limit: int = 120) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def action_policy(action: str) -> dict[str, Any]:
    """Fail closed; does not grant permissions on real HTTP routes."""
    name = _text(action, 80).upper()
    if name in READ_ACTIONS:
        category, safe = "READ_AUTO", True
    elif name in PROPOSE_ACTIONS:
        category, safe = "PROPOSE_ONLY", True
    elif name in APPROVAL_ACTIONS:
        category, safe = "FOUNDER_APPROVAL_REQUIRED", False
    elif name in FORBIDDEN_ACTIONS:
        category, safe = "FORBIDDEN_TO_AUTOMATION", False
    else:
        category, safe = "UNRECOGNIZED_DENIED", False
    return {
        "action": name, "policy": category, "may_run_safe_local_step": safe,
        "approval_required": not safe, "approval_issued": False,
        "may_change_production": False, "may_spend_money": False,
    }


def _results(receipt: Any) -> list[dict[str, Any]]:
    if not isinstance(receipt, dict) or receipt.get("contract") != NATIVE_CONTRACT:
        return []
    results = receipt.get("results")
    if not isinstance(results, list):
        return []
    return [r for r in results[:30] if isinstance(r, dict)]


def build_executive_readout(receipt: Any) -> dict[str, Any]:
    """Brief saved within an existing native review; no new job or provider."""
    valid = isinstance(receipt, dict) and receipt.get("contract") == NATIVE_CONTRACT
    rows = [r for r in _results(receipt) if r.get("executed") is True]
    fail = [r for r in rows if r.get("state") == "FAIL"]
    unknown = [r for r in rows if r.get("state") == "UNKNOWN"]
    agenda = []
    for priority, candidates, reason in (
        ("P1", fail, "STATIC_FAILURE_REQUIRES_INDEPENDENT_CHECK"),
        ("VERIFY", unknown, "MISSING_INDEPENDENT_EVIDENCE"),
    ):
        for r in candidates:
            if len(agenda) == 8:
                break
            identifier = _text(r.get("id"), 72)
            if identifier:
                agenda.append({
                    "area_id": identifier, "priority": priority, "reason": reason,
                    "suggested_action": "Contrastar en navegador o producción y proponer solución.",
                    "source": "NATIVE_STATIC_REVIEW", "approved": False,
                })
    return {
        "contract": READOUT_CONTRACT,
        "state": "STATIC_READOUT" if valid else "NO_VERIFIED_RECEIPT",
        "receipt_id": _text(receipt.get("receipt_id"), 90) if valid else "",
        "observed_at_madrid": _text(receipt.get("finished_at_madrid"), 55) if valid else "",
        "executed": len(rows),
        "static_failed": len(fail), "static_unknown": len(unknown),
        "static_passed": sum(r.get("state") == "PASS" for r in rows),
        "priorities": agenda,
        "independent_votes": 0, "production_certified": False,
        "business_execution_certified": False,
        "automatic_changes_authorized": False,
        "external_calls": 0, "paid_credits_consumed": 0,
    }


def build_vicepresidency_snapshot(
    workers: Iterable[dict[str, Any]],
    disciplines: Iterable[dict[str, Any]],
    native_review: dict[str, Any] | None,
    cron_receipt: dict[str, Any] | None,
    triads: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render existing evidence and responsibilities without side effects."""
    native = native_review if isinstance(native_review, dict) else {}
    cron = cron_receipt if isinstance(cron_receipt, dict) else {}
    triad = triads if isinstance(triads, dict) else {}
    recent = native.get("state") == "RECENT"
    receipt = native.get("receipt") if recent and isinstance(native.get("receipt"), dict) else {}
    records = [r for r in _results(receipt) if r.get("executed") is True]
    by_name = {_text(r.get("worker_name")): r for r in records}
    by_id = {_text(r.get("id")): r for r in records}
    assignments = []

    for member in list(workers)[:30]:
        if not isinstance(member, dict):
            continue
        name = _text(member.get("worker_name"))
        record = by_name.get(name, {}) if recent else {}
        executed = record.get("state") in {"PASS", "FAIL", "UNKNOWN"}
        assignments.append({
            "area": _text(member.get("area")) or name, "role": name,
            "group": "COMPANY",
            "state": "STATIC_CHECK_RECORDED" if executed else "NO_RECENT_EVIDENCE",
            "static_outcome": record.get("state") if executed else "UNVERIFIED",
            "execution_certified": False,
        })
    for expert in list(disciplines)[:15]:
        if not isinstance(expert, dict):
            continue
        key = _text(expert.get("id"), 80)
        record = by_id.get(key, {}) if recent else {}
        executed = record.get("state") in {"PASS", "FAIL", "UNKNOWN"}
        assignments.append({
            "area": _text(expert.get("name")) or key, "role": key,
            "group": "GAME_UI",
            "state": "STATIC_CHECK_RECORDED" if executed else "NO_RECENT_EVIDENCE",
            "static_outcome": record.get("state") if executed else "UNVERIFIED",
            "execution_certified": False,
        })
    readout = build_executive_readout(receipt if recent else {})
    cron_state = cron.get("state")
    if cron_state not in {
        "RECENT_RECEIPT", "STALE_RECEIPT", "NO_EVIDENCE",
        "READ_UNAVAILABLE", "CLOCK_UNVERIFIED",
    }:
        cron_state = "NO_EVIDENCE"

    return {
        "contract": CONTRACT,
        "president": {"name": "Fundador / Presidencia", "authority": "FINAL_DECISION",
                      "retains_control": True},
        "vicepresident": {
            "name": "Vicepresidencia operativa digital",
            "state": "RECENT_STATIC_COORDINATION" if recent and readout["executed"] else "AWAITING_RECENT_REVIEW",
            "mandate": "Coordinación y propuestas cuando el fundador no está, condicionadas a recibos reales.",
            "independent_agent_running": False,
            "can_delegate_safe_reviews": True,
            "can_approve_external_changes": False, "approval_boundary": "FOUNDER_ONLY",
        },
        "cron": {"state": cron_state,
                 "observed_at_madrid": _text(cron.get("last_observed_madrid"), 55),
                 "certifies_all_workers": False},
        "advisory_council": [
            {"id": key, "name": name, "mandate": focus,
             "state": "ADVISORY_ROLE_DEFINED",
             "independent_vote_recorded": False, "can_authorize": False}
            for key, name, focus in ADVISORS
        ],
        "configured_specialists": len(assignments),
        "reviewed_static_specialists": sum(
            r["state"] == "STATIC_CHECK_RECORDED" for r in assignments
        ),
        "assignments": assignments,
        "executive_readout": readout,
        "agenda": readout["priorities"],
        "crosscheck": {
            "configured_areas": min(100, max(0, triad.get("configured_areas", 0)))
            if type(triad.get("configured_areas")) is int else 0,
            "independent_votes": 0, "approval_issued": False,
            "advisory_only": True,
        },
        "permissions": {
            "safe_review": "READ_AUTO", "proposals": "PROPOSE_ONLY",
            "external_writes": "FOUNDER_APPROVAL_REQUIRED",
            "dangerous_operations": "FORBIDDEN_TO_AUTOMATION",
        },
        "safe_mode": True,
        "production_mutations": 0,
        "autonomous_agents_started": 0,
        "additional_services": 0,
        "additional_paid_calls": 0,
        "limitations": "Son funciones del software; sin recibos recientes no se acredita trabajo 24/7.",
    }
