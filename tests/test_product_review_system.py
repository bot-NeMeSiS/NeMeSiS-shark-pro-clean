from __future__ import annotations

from pathlib import Path

from engines.product_review_system_engine import (
    PRODUCT_REVIEW_CENTER_CONTRACT,
    PRODUCT_REVIEW_SYSTEM_CONTRACT,
    QUALITY_TEAM_CONTRACT,
    REQUIRED_FINDING_FIELDS,
    REVIEWER_DEFINITIONS,
    build_product_review_system_snapshot,
)
from engines.project_operating_system_engine import build_product_roadmap
from engines.sports_platform_contracts import build_sports_platform_contract_registry

ROOT = Path(__file__).resolve().parents[1]


def _admin_session(client):
    with client.session_transaction() as session:
        session["user_id"] = "admin-product-review"
        session["user_name"] = "Admin Review"
        session["user_role"] = "ADMIN"
        session["membership"] = "ADMIN"


def _sample_reviewer(name="Product Director"):
    return {
        "key": name.lower().replace(" ", "_"),
        "name": name,
        "module": "Producto",
        "responsibility": "Revisa valor e integracion del producto.",
        "contract": "NEMESIS-SAMPLE-REVIEWER-V1",
        "state": "PASS",
        "last_review_madrid": "2026-07-30T10:00:00+02:00",
        "score": 100,
        "score_explanation": ["Base 100.", "Sin hallazgos bloqueantes ni evidencia obligatoria ausente."],
        "findings_count": 0,
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "p3": 0,
        "evidence_checks": [{"key": "sample", "ok": True, "state": "VERIFIED", "evidence": "Evidencia local."}],
        "findings": [],
        "autofix_allowed": False,
        "human_approval_required": True,
    }


def _sample_snapshot():
    reviewers = [_sample_reviewer(item["name"]) for item in REVIEWER_DEFINITIONS]
    finding = {
        "id": "PRS-SAMPLE-001",
        "reviewer": "UX Reviewer",
        "module": "UX",
        "screen": "Home",
        "route": "/",
        "component": "hero",
        "evidence": "Evidencia local de prueba.",
        "priority": "P2",
        "impact_user": "Mejora claridad.",
        "impact_business": "Mejora confianza.",
        "user_impact": "Mejora claridad.",
        "business_impact": "Mejora confianza.",
        "proposal": "Revisar copy con evidencia visual.",
        "source": "test",
        "source_type": "fixture",
        "confidence": "PARTIALLY_VERIFIED",
        "limitations": "Solo fixture.",
    }
    return {
        "contract": PRODUCT_REVIEW_SYSTEM_CONTRACT,
        "center_contract": PRODUCT_REVIEW_CENTER_CONTRACT,
        "quality_team_contract": QUALITY_TEAM_CONTRACT,
        "version": "TEST",
        "generated_at_madrid": "2026-07-30T10:00:00+02:00",
        "environment": "local_filesystem_read_only",
        "status": "PASS_WITH_REVIEW_ITEMS",
        "score": 99,
        "score_explanation": ["Media de 12 revisores especializados."],
        "reviewer_count": len(reviewers),
        "reviewers_expected": len(REVIEWER_DEFINITIONS),
        "reviewers": reviewers,
        "findings": [finding],
        "findings_summary": {"P0": 0, "P1": 0, "P2": 1, "P3": 0, "total": 1},
        "roadmap_candidates": [
            {
                "id": "PRS-001",
                "reviewer": "UX Reviewer",
                "priority": "P2",
                "module": "UX",
                "screen": "Home",
                "route": "/",
                "proposal": "Revisar copy con evidencia visual.",
                "evidence": "Evidencia local de prueba.",
                "approved": False,
                "automatic_execution_allowed": False,
                "requires_human_approval": True,
            }
        ],
        "source_contracts": {"experience_platform": "NEMESIS-EXPERIENCE-PLATFORM-V1"},
        "guardrails": {
            "generative_ai_calls": 0,
            "chatbot_created": False,
            "external_calls": 0,
            "database_writes": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "production_modified": False,
            "automatic_improvements": False,
            "automatic_commits": False,
            "automatic_push": False,
            "automatic_deploy": False,
        },
        "no_generative_ai": True,
        "no_chatbot": True,
        "no_fictitious_assistants": True,
        "production_modified": False,
        "deploy_executed": False,
        "push_executed": False,
        "next_action": "Revisar hallazgos.",
    }


def test_product_review_snapshot_has_12_evidence_first_reviewers():
    snapshot = build_product_review_system_snapshot(ROOT, "TEST")

    assert snapshot["contract"] == PRODUCT_REVIEW_SYSTEM_CONTRACT
    assert snapshot["center_contract"] == PRODUCT_REVIEW_CENTER_CONTRACT
    assert snapshot["quality_team_contract"] == QUALITY_TEAM_CONTRACT
    assert snapshot["reviewer_count"] == 12
    assert snapshot["reviewers_expected"] == len(REVIEWER_DEFINITIONS)
    assert 0 <= snapshot["score"] <= 100
    assert snapshot["score_explanation"]
    assert snapshot["no_generative_ai"] is True
    assert snapshot["no_chatbot"] is True
    assert snapshot["no_fictitious_assistants"] is True

    for reviewer in snapshot["reviewers"]:
        assert reviewer["state"] in {"PASS", "PARTIAL", "REQUIRES_REVIEW"}
        assert 0 <= reviewer["score"] <= 100
        assert reviewer["score_explanation"]
        assert reviewer["evidence_checks"]
        assert reviewer["autofix_allowed"] is False
        assert reviewer["human_approval_required"] is True


def test_product_review_findings_are_complete_and_human_approved_only():
    snapshot = build_product_review_system_snapshot(ROOT, "TEST")

    for finding in snapshot["findings"]:
        assert all(finding.get(field) for field in REQUIRED_FINDING_FIELDS)
        assert finding["priority"] in {"P0", "P1", "P2", "P3"}
        assert finding.get("evidence")
        assert finding.get("proposal")

    for candidate in snapshot["roadmap_candidates"]:
        assert candidate["approved"] is False
        assert candidate["automatic_execution_allowed"] is False
        assert candidate["requires_human_approval"] is True


def test_product_review_guardrails_prevent_generation_and_execution():
    snapshot = build_product_review_system_snapshot(ROOT, "TEST")
    guardrails = snapshot["guardrails"]

    assert guardrails["generative_ai_calls"] == 0
    assert guardrails["external_calls"] == 0
    assert guardrails["database_writes"] == 0
    assert guardrails["telegram_sends"] == 0
    assert guardrails["stripe_calls"] == 0
    assert guardrails["chatbot_created"] is False
    assert guardrails["production_modified"] is False
    assert guardrails["automatic_improvements"] is False
    assert guardrails["automatic_commits"] is False
    assert guardrails["automatic_push"] is False
    assert guardrails["automatic_deploy"] is False


def test_product_review_registered_in_platform_and_roadmap():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    assert capabilities["product_review_system"]["state"] == "INTEGRATED"

    roadmap = build_product_roadmap(ROOT)
    modules = {item["name"]: item for item in roadmap["modules"]}
    assert modules["Product Review System"]["state"] == "COMPLETED"


def test_product_review_center_routes_are_admin_protected(client):
    assert client.get("/admin/product-review-center").status_code == 302
    api = client.get("/api/admin/product-review-center/summary")
    assert api.status_code == 403
    assert api.get_json()["error"] == "Acceso admin requerido."


def test_product_review_center_renders_read_only_panel(client, app_module, monkeypatch):
    _admin_session(client)
    monkeypatch.setattr(app_module, "dashboard_data", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "build_product_review_system_snapshot", lambda *args, **kwargs: _sample_snapshot())

    response = client.get("/admin/product-review-center")

    assert response.status_code == 200
    assert b"Product Review Center" in response.data
    assert b"data-product-review-mode=\"read-only\"" in response.data
    assert b"Estado del equipo de revision" in response.data
    assert b"Candidatos de roadmap" in response.data

    template = (ROOT / "templates" / "admin_product_review_center.html").read_text(encoding="utf-8")
    assert "<form" not in template.lower()
    assert "method=\"post\"" not in template.lower()


def test_product_review_api_returns_safe_snapshot(client, app_module, monkeypatch):
    _admin_session(client)
    monkeypatch.setattr(app_module, "build_product_review_system_snapshot", lambda *args, **kwargs: _sample_snapshot())

    response = client.get("/api/admin/product-review-center/summary")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    review = payload["product_review"]
    assert review["contract"] == PRODUCT_REVIEW_SYSTEM_CONTRACT
    assert review["production_modified"] is False
    assert review["deploy_executed"] is False
    assert review["push_executed"] is False
    assert review["guardrails"]["generative_ai_calls"] == 0
