"""Compatibility facade for the evidence-backed NeMeSiS Company Board.

The public V859 functions remain available, but their data now comes from the
shared Company/Developer Operating System instead of static scores.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from engines.project_operating_system_engine import build_company_board_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Kept as contract labels for historical checks and integrations.
LEGACY_BOARD_NAMES = (
    "Product Board",
    "Client Experience Board",
    "Admin Operations Board",
    "Membership Revenue Board",
    "Data Reality Board",
    "SHARK Intelligence Board",
    "Telegram Premium Board",
    "Technical Architecture Board",
    "Visual Reference Board",
    "Render/GitHub/Release Board",
)


@dataclass(frozen=True)
class AuditBoard:
    area: str
    status: str
    score: int
    findings: list[str]
    risks: list[str]
    recommended_actions: list[str]
    next_version_focus: str
    safe_notes: list[str]
    no_fake_data_notes: list[str]
    href: str


def _legacy_status(state: str) -> str:
    return {
        "CONFIRMED": "strong",
        "PARTIALLY_VERIFIED": "ok",
        "NOT_CERTIFIED": "blocked_by_real_world",
        "BLOCKED_BY_ACCESS": "blocked_by_real_world",
        "REQUIRES_REVIEW": "needs_attention",
    }.get(str(state or "").upper(), "needs_attention")


def _structural_score(state: str) -> int:
    """Compatibility value derived only from the evidence classification."""

    return {
        "CONFIRMED": 10,
        "PARTIALLY_VERIFIED": 7,
        "NOT_CERTIFIED": 5,
        "BLOCKED_BY_ACCESS": 4,
        "REQUIRES_REVIEW": 6,
    }.get(str(state or "").upper(), 5)


def build_audit_boards(
    runtime: dict[str, Any] | None = None,
    *,
    version: str = "",
) -> list[dict[str, Any]]:
    board = build_company_board_snapshot(PROJECT_ROOT, version, runtime or {})
    risks_by_area: dict[str, list[str]] = {}
    for risk in board.get("risks") or []:
        risks_by_area.setdefault(str(risk.get("area") or "Empresa"), []).append(
            str(risk.get("title") or "Riesgo pendiente de revisión")
        )

    result = []
    for area in board.get("areas") or []:
        name = str(area.get("name") or "Área")
        state = str(area.get("state") or "REQUIRES_REVIEW")
        area_risks = risks_by_area.get(name, [])
        item = AuditBoard(
            area=name,
            status=_legacy_status(state),
            score=_structural_score(state),
            findings=[str(area.get("evidence") or "Sin evidencia local suficiente.")],
            risks=area_risks or (
                [] if state == "CONFIRMED" else ["Estado pendiente de certificación o revisión."]
            ),
            recommended_actions=[str(area.get("next_action") or "Mantener vigilancia.")],
            next_version_focus=str(area.get("next_action") or "Mantener vigilancia."),
            safe_notes=["Este board no llama proveedores ni modifica datos de producto."],
            no_fake_data_notes=["Las clasificaciones proceden de evidencia local; no son métricas comerciales."],
            href=str(area.get("href") or "/admin/company-board"),
        )
        result.append(asdict(item))
    return result


def build_company_audit_summary(
    version: str = "",
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    company = build_company_board_snapshot(PROJECT_ROOT, version, runtime or {})
    boards = build_audit_boards(runtime, version=version)
    confirmed = sum(1 for area in company.get("areas") or [] if area.get("state") == "CONFIRMED")
    total = len(company.get("areas") or [])
    structural_coverage = round((confirmed / total) * 10, 1) if total else 0
    blocked = [
        area.get("name")
        for area in company.get("areas") or []
        if area.get("state") in {"NOT_CERTIFIED", "BLOCKED_BY_ACCESS"}
    ]
    roadmap = company.get("roadmap") or {}
    return {
        "version": version,
        "global_score": structural_coverage,
        "global_score_basis": "Cobertura estructural confirmada; no es una nota comercial.",
        "global_status": company.get("state") or "REQUIRES_REVIEW",
        "audit_boards": boards,
        "top_risks": [risk.get("title") for risk in (company.get("risks") or [])],
        "next_actions": [area.get("next_action") for area in (company.get("areas") or [])],
        "blocked_by_real_world_validation": blocked,
        "priority_roadmap": [item.get("name") for item in (roadmap.get("modules") or [])],
        "secrets_exposed": False,
        "external_calls": False,
        "database_writes": False,
        "data_invention_allowed": False,
        "company_board": company,
    }