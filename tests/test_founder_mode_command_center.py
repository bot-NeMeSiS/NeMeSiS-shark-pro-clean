from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _admin_session(client):
    with client.session_transaction() as session:
        session["user_id"] = "admin-user"
        session["user_name"] = "Admin"
        session["user_role"] = "ADMIN"
        session["membership"] = "ADMIN"


def _sample_founder_snapshot() -> dict:
    return {
        "contract": "NEMESIS-FOUNDER-COMMAND-CENTER-V1",
        "version": "TEST",
        "generated_at_madrid": "2026-07-29T12:00:00+02:00",
        "mode": "read_only",
        "production_modified": False,
        "dangerous_actions_executed": False,
        "database_written": False,
        "external_calls": 0,
        "telegram_sent": False,
        "stripe_called": False,
        "business_kpis": {
            "users_total": 10,
            "free": 7,
            "pro": 2,
            "elite": 1,
            "paid_total": 3,
            "conversion_registered_to_paid": "30.0%",
            "conversion_state": "PARTIALLY_VERIFIED",
            "checkout_started": 2,
            "payments_confirmed": 1,
            "mrr": None,
            "mrr_state": "NO_CERTIFICADO",
        },
        "customer_overview": {
            "registered": 10,
            "active_events": 4,
            "pro_interest": 2,
            "support_items": 1,
            "privacy_state": "PARTIALLY_VERIFIED",
            "user_intelligence_controls": {"transparent": True, "disable": True, "delete": True, "export": True},
        },
        "beta_control": {
            "state": "PARTIAL",
            "users_total": 10,
            "feedback_open": 1,
            "tickets_open": 0,
            "support_health": 92,
            "next_action": "Revisar beta cerrada.",
            "href": "/admin/beta-center",
        },
        "operations_summary": [
            {"key": "render", "label": "Render", "status": "NOT_CERTIFIED", "evidence_state": "BLOQUEADO_POR_ACCESO", "summary": "Produccion no consultada.", "source": "Operations Center", "href": "/admin/operations-center", "next_action": "Certificar read-only."},
            {"key": "sentinel", "label": "Sentinel", "status": "READY", "evidence_state": "CONFIRMADO", "summary": "Sentinel disponible.", "source": "Operations Center", "href": "/admin/sentinel-autopilot", "next_action": "Mantener vigilancia."},
        ],
        "release_readiness": {"status": "PARTIAL", "score": 8.4, "missing": ["Render productivo"], "report": {}},
        "top100": {"total": 100, "completed": None, "state": "NO_CERTIFICADO", "summary": "Plan definido.", "priorities": {"P1": 20, "P2": 60}, "report": {}},
        "roadmap": {"current_sprint": "Beta privada", "next_sprint": "Certificacion", "completed": ["Sports Core"]},
        "reports": [{"name": "FOUNDER_MODE_REPORT.md", "path": "reports/FOUNDER_MODE_REPORT.md", "available": True, "state": "CONFIRMADO", "updated_at_madrid": "2026-07-29T12:00:00+02:00"}],
        "action_platform": {"contract": "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1", "state": "PARTIALLY_VERIFIED", "summary": {"body": "Resumen Action Platform."}, "guardrails": {"external_calls": 0, "telegram_sends": 0}, "href": "/smart-home"},
        "developer_center": {"href": "/admin/developer-center", "state": "REUTILIZADO"},
        "company_board": {"href": "/admin/company-board", "state": "REUTILIZADO"},
        "operations_center": {"href": "/admin/operations-center", "state": "REUTILIZADO"},
        "company_intelligence": {"state": "PARTIALLY_VERIFIED", "next_actions": [{"title": "Beta", "action": "Revisar evidencia.", "state": "PARTIALLY_VERIFIED"}], "priorities": [], "href": "/admin/company-intelligence"},
        "guardrails": ["solo lectura", "sin deploy", "sin push", "sin Telegram real", "sin Stripe"],
        "next_action": "Revisar beta cerrada.",
    }


def test_founder_dashboard_routes_are_admin_protected(client):
    assert client.get("/admin/founder-dashboard").status_code == 302
    api = client.get("/api/admin/founder-dashboard")
    assert api.status_code == 403
    assert api.get_json()["error"] == "Acceso admin requerido."


def test_founder_dashboard_renders_read_only_center(client, app_module, monkeypatch):
    _admin_session(client)
    monkeypatch.setattr(app_module, "dashboard_data", lambda *args, **kwargs: {})
    monkeypatch.setattr(app_module, "founder_command_center_snapshot", _sample_founder_snapshot)

    response = client.get("/admin/founder-dashboard")

    assert response.status_code == 200
    assert "Panel fundador".encode("utf-8") in response.data
    assert "Centro de mando de empresa".encode("utf-8") in response.data
    assert b"Beta Control" in response.data
    assert "Resumen operativo".encode("utf-8") in response.data
    assert "Exportación de informes".encode("utf-8") in response.data
    assert b"data-founder-mode=\"read-only\"" in response.data

    template = (ROOT / "templates" / "admin_founder_dashboard.html").read_text(encoding="utf-8")
    assert "<form" not in template.lower()
    assert "method=\"post\"" not in template.lower()
    assert "data-v939-action" not in template
    assert "data-v938-action" not in template

def test_founder_api_returns_read_only_contract(client, app_module, monkeypatch):
    _admin_session(client)
    monkeypatch.setattr(app_module, "founder_command_center_snapshot", _sample_founder_snapshot)

    response = client.get("/api/admin/company-command-center")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    founder = payload["founder"]
    assert founder["contract"] == "NEMESIS-FOUNDER-COMMAND-CENTER-V1"
    assert founder["production_modified"] is False
    assert founder["dangerous_actions_executed"] is False
    assert founder["database_written"] is False
    assert founder["external_calls"] == 0
    assert founder["telegram_sent"] is False
    assert founder["stripe_called"] is False


def test_founder_snapshot_composes_existing_surfaces_without_dangerous_actions(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "v938_operations_snapshot", lambda: {
        "systems": [
            {"id": "render", "status": "NOT_CERTIFIED", "evidence_state": "BLOQUEADO_POR_ACCESO", "summary": "No external read.", "source": "runtime externo", "next_action": "Certificar."},
            {"id": "sentinel", "status": "READY", "evidence_state": "CONFIRMADO", "summary": "Ready.", "source": "engines", "next_action": "Vigilar."},
        ],
        "operations_sections": {},
        "release_1_gate": {"status": "PARTIAL", "score": 8.4, "missing_for_ready": ["Render"]},
        "global_score": {"overall_score": 8.4},
    })
    monkeypatch.setattr(app_module, "v939_company_intelligence_bundle", lambda: {
        "product": {"funnel": {"registered": 10, "active": 2, "pro_interest": 1, "checkout_started": 1}, "conversion_registered_to_paid": {"value": 30, "state": "PARTIALLY_VERIFIED"}, "certification_state": "PARTIALLY_VERIFIED"},
        "business": {"memberships": {"FREE": 7, "PRO": 2, "ELITE": 1}, "payment_event_counts": {"payments_confirmed": 1}, "mrr": None},
        "company": {"executive_summary": {"certification_state": "PARTIALLY_VERIFIED"}, "next_actions": [], "priorities": []},
    })
    monkeypatch.setattr(app_module, "v808_support_center_context", lambda: {"open_feedback": 1, "open_tickets": 0, "health": 92})
    monkeypatch.setattr(app_module, "build_action_platform_snapshot", lambda user=None: {"contract": "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1", "certification_state": "INSUFFICIENT_DATA", "summary": {}, "guardrails": {"external_calls": 0}})
    monkeypatch.setattr(app_module, "build_product_roadmap", lambda root: {"current_sprint": "Beta", "next_sprint": "Certificacion", "completed": []})
    monkeypatch.setattr(app_module, "_founder_report_metadata", lambda name: {"name": name, "path": f"reports/{name}", "available": True, "state": "CONFIRMADO"})
    monkeypatch.setattr(app_module, "_founder_top100_progress", lambda: {"total": 100, "completed": None, "state": "NO_CERTIFICADO", "summary": "Plan", "priorities": {"P1": 20, "P2": 60}})

    snapshot = app_module.founder_command_center_snapshot()

    assert snapshot["contract"] == "NEMESIS-FOUNDER-COMMAND-CENTER-V1"
    assert snapshot["business_kpis"]["users_total"] == 10
    assert snapshot["business_kpis"]["pro"] == 2
    assert snapshot["business_kpis"]["elite"] == 1
    assert snapshot["release_readiness"]["status"] == "PARTIAL"
    assert snapshot["action_platform"]["contract"] == "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1"
    assert snapshot["production_modified"] is False
    assert snapshot["dangerous_actions_executed"] is False
    assert snapshot["database_written"] is False
    assert snapshot["external_calls"] == 0
    assert snapshot["telegram_sent"] is False
    assert snapshot["stripe_called"] is False