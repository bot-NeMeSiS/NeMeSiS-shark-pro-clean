from __future__ import annotations

from pathlib import Path

from engines.product_review_system_engine import (
    EXECUTIVE_BOARD_CENTER_CONTRACT,
    EXECUTIVE_BOARD_CONTRACT,
    EXECUTIVE_DIRECTOR_DEFINITIONS,
    EXECUTIVE_REQUIRED_PROPOSAL_FIELDS,
    EXECUTIVE_VOTE_LEVELS,
    STRATEGIC_DECISION_CONTRACT,
    build_executive_board_snapshot,
)
from engines.project_operating_system_engine import build_product_roadmap
from engines.sports_platform_contracts import build_sports_platform_contract_registry

ROOT = Path(__file__).resolve().parents[1]


def _admin_session(client):
    with client.session_transaction() as session:
        session["user_id"] = "admin-executive-board"
        session["user_name"] = "Admin Executive"
        session["user_role"] = "ADMIN"
        session["membership"] = "ADMIN"


def _sample_board():
    candidate = {
        "id": "EBD-001",
        "source_id": "PRS-001",
        "title": "UX: simplificar primer valor",
        "evidence": "Evidencia local de prueba.",
        "module": "UX",
        "screen": "Home",
        "route": "/",
        "component": "hero",
        "impact_user": "Mejora claridad.",
        "impact_business": "Mejora conversion responsable.",
        "priority": "P2",
        "estimated_cost": "Bajo",
        "dependencies": ["Product Review System", "aprobacion humana"],
        "risk": "Bajo",
        "proposal": "Revisar jerarquia con evidencia.",
        "status": "Pendiente",
        "approved": False,
        "requires_human_approval": True,
        "automatic_execution_allowed": False,
        "selection_score": 81,
        "selection_explanation": ["prioridad P2: 55"],
        "board_classification": "ALTA",
        "votes": [
            {"director": item["name"], "classification": "ALTA" if item["name"] in {"Head of UX", "CEO"} else "BAJA", "supports": item["name"] in {"Head of UX", "CEO"}, "rejects": False, "reason": "fixture"}
            for item in EXECUTIVE_DIRECTOR_DEFINITIONS
        ],
        "supporters": ["Head of UX", "CEO"],
        "rejecters": [],
        "vote_counts": {"CRITICA": 0, "ALTA": 2, "MEDIA": 0, "BAJA": 10, "DESCARTADA": 0},
    }
    directors = [
        {
            **item,
            "contract": f"NEMESIS-EXECUTIVE-DIRECTOR-{item['key'].upper().replace('_', '-')}-V1",
            "state": "CON_EVIDENCIA" if item["name"] in {"Head of UX", "CEO"} else "SIN_HALLAZGOS_DIRECTOS",
            "score": 95,
            "score_explanation": ["Base 100 menos evidencia."],
            "last_review_madrid": "2026-07-31T10:00:00+02:00",
            "what_works": ["Funciona con evidencia."],
            "what_does_not_work": ["No hay bloqueo."],
            "should_improve": ["Revisar cuando se apruebe."],
            "risks": ["Riesgo bajo."],
            "opportunities": ["Mejora claridad."],
            "supported_candidates": ["EBD-001"] if item["name"] in {"Head of UX", "CEO"} else [],
            "rejected_candidates": [],
            "findings_count": 1 if item["name"] in {"Head of UX", "CEO"} else 0,
            "votes_given": 1,
        }
        for item in EXECUTIVE_DIRECTOR_DEFINITIONS
    ]
    return {
        "contract": EXECUTIVE_BOARD_CONTRACT,
        "center_contract": EXECUTIVE_BOARD_CENTER_CONTRACT,
        "decision_contract": STRATEGIC_DECISION_CONTRACT,
        "version": "TEST",
        "generated_at_madrid": "2026-07-31T10:00:00+02:00",
        "environment": "local_filesystem_read_only",
        "status": "PASS_WITH_STRATEGIC_REVIEW",
        "board_score": 95,
        "board_score_explanation": ["Explicado por directores."],
        "director_count": len(EXECUTIVE_DIRECTOR_DEFINITIONS),
        "directors_expected": len(EXECUTIVE_DIRECTOR_DEFINITIONS),
        "directors": directors,
        "area_health": [{"key": "ux", "label": "Estado UX", "score": 95, "state": "PASS", "evidence": "fixture"}],
        "product_scores": [{"key": "ux", "label": "UX", "score": 95, "state": "PASS", "justification": "Media explicada.", "evidence": ["EBD-001"]}],
        "proposal_count": 1,
        "proposal_summary": {"P0": 0, "P1": 0, "P2": 1, "P3": 0, "total": 1},
        "decision_matrix": [candidate],
        "top_10_improvements": [candidate],
        "backlog_updates": [{"id": "EBD-001", "source_id": "PRS-001", "top100_status": "Pendiente", "master_roadmap_status": "Pendiente", "living_roadmap_status": "Pendiente", "documentation": ["reports/EXECUTIVE_DECISION_MATRIX.md"], "human_approval_required": True}],
        "source_contracts": {"product_review_system": "NEMESIS-PRODUCT-REVIEW-SYSTEM-V1"},
        "guardrails": {"generative_ai_calls": 0, "external_calls": 0, "database_writes": 0, "telegram_sends": 0, "stripe_calls": 0, "chatbot_created": False, "production_modified": False, "automatic_execution": False, "automatic_decisions": False, "automatic_push": False, "automatic_deploy": False, "commit_created": False},
        "no_chatbot": True,
        "no_generative_ai": True,
        "no_automatic_decisions": True,
        "automatic_execution_allowed": False,
        "production_modified": False,
        "deploy_executed": False,
        "push_executed": False,
        "executive_summary": "Fixture seguro.",
        "next_action": "Revision humana.",
    }


def test_executive_board_snapshot_has_12_directors_and_contracts():
    snapshot = build_executive_board_snapshot(ROOT, "TEST")
    assert snapshot["contract"] == EXECUTIVE_BOARD_CONTRACT
    assert snapshot["center_contract"] == EXECUTIVE_BOARD_CENTER_CONTRACT
    assert snapshot["decision_contract"] == STRATEGIC_DECISION_CONTRACT
    assert snapshot["director_count"] == 12
    assert snapshot["directors_expected"] == len(EXECUTIVE_DIRECTOR_DEFINITIONS)
    assert 0 <= snapshot["board_score"] <= 100
    assert snapshot["board_score_explanation"]
    assert snapshot["no_chatbot"] is True
    assert snapshot["no_generative_ai"] is True
    assert snapshot["no_automatic_decisions"] is True


def test_executive_board_candidates_are_evidence_first_and_not_executable():
    snapshot = build_executive_board_snapshot(ROOT, "TEST")
    assert len(snapshot["top_10_improvements"]) <= 10
    for candidate in snapshot["decision_matrix"]:
        assert all(candidate.get(field) for field in EXECUTIVE_REQUIRED_PROPOSAL_FIELDS)
        assert candidate["priority"] in {"P0", "P1", "P2", "P3"}
        assert candidate["approved"] is False
        assert candidate["requires_human_approval"] is True
        assert candidate["automatic_execution_allowed"] is False
        assert candidate["evidence"]
        assert candidate["impact_user"]
        assert candidate["impact_business"]


def test_executive_board_votes_are_independent_and_valid():
    snapshot = build_executive_board_snapshot(ROOT, "TEST")
    for candidate in snapshot["decision_matrix"]:
        assert len(candidate["votes"]) == len(EXECUTIVE_DIRECTOR_DEFINITIONS)
        for vote in candidate["votes"]:
            assert vote["classification"] in EXECUTIVE_VOTE_LEVELS
            assert vote["director"]
            assert vote["reason"]
        assert candidate["board_classification"] in EXECUTIVE_VOTE_LEVELS
        assert "supporters" in candidate
        assert "rejecters" in candidate


def test_executive_board_product_scores_are_explained():
    snapshot = build_executive_board_snapshot(ROOT, "TEST")
    labels = {item["label"] for item in snapshot["product_scores"]}
    assert {"Arquitectura", "Producto", "UX", "Mobile", "Sports Core", "SHARK", "Seguridad", "Operaciones", "Comercial", "Release Readiness"}.issubset(labels)
    for score in snapshot["product_scores"]:
        assert isinstance(score["score"], int)
        assert 0 <= score["score"] <= 100
        assert score["justification"]


def test_executive_board_registered_in_platform_and_roadmap():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    assert capabilities["executive_board"]["state"] == "INTEGRATED"

    roadmap = build_product_roadmap(ROOT)
    modules = {item["name"]: item for item in roadmap["modules"]}
    assert modules["Executive Board"]["state"] == "COMPLETED"


def test_executive_board_routes_are_admin_protected(client):
    assert client.get("/admin/executive-board").status_code == 302
    assert client.get("/admin/strategic-board").status_code == 302
    assert client.get("/admin/product-governance").status_code == 302


def test_executive_board_center_renders_read_only_panel(client, app_module, monkeypatch):
    _admin_session(client)
    monkeypatch.setattr(app_module, "dashboard_data", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "build_executive_board_snapshot", lambda *args, **kwargs: _sample_board())

    response = client.get("/admin/executive-board")

    assert response.status_code == 200
    assert b"Executive Board Center" in response.data
    assert b"data-executive-board-mode=\"read-only\"" in response.data
    assert b"Matriz de decisiones" in response.data
    assert b"Top 10" in response.data

    template = (ROOT / "templates" / "admin_executive_board_center.html").read_text(encoding="utf-8")
    assert "<form" not in template.lower()
    assert "method=\"post\"" not in template.lower()
