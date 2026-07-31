from __future__ import annotations

from pathlib import Path

from engines.project_operating_system_engine import build_product_roadmap
from engines.sports_platform_contracts import build_sports_platform_contract_registry

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "NEMESIS-GO-TO-MARKET-OFFICE-V1"


def _admin_session(client):
    with client.session_transaction() as session:
        session["user_id"] = "admin-go-to-market"
        session["user_name"] = "Admin Go To Market"
        session["user_role"] = "ADMIN"
        session["membership"] = "ADMIN"


def test_go_to_market_snapshot_is_read_only_and_evidence_based(app_module):
    snapshot = app_module.go_to_market_office_snapshot()
    assert snapshot["contract"] == CONTRACT
    assert snapshot["mode"] == "read_only"
    assert snapshot["production_modified"] is False
    assert snapshot["deploy_executed"] is False
    assert snapshot["push_executed"] is False
    assert snapshot["campaigns_launched"] is False
    assert snapshot["stripe_connected"] is False
    assert snapshot["telegram_sent"] is False
    assert snapshot["external_calls"] == 0

    required = {
        "git", "qa", "browser_qa", "render", "telegram", "stripe", "backups", "restore",
        "observability", "cron", "master_tick", "security", "privacy", "support", "documentation",
        "landing", "faq", "company_platform",
    }
    checks = {item["key"]: item for item in snapshot["checklist"]}
    assert required.issubset(checks)
    for item in checks.values():
        assert item["status"] in {"PASS", "PARTIAL", "BLOCKED"}
        assert item["evidence"]
        assert item["limitation"]

    for score in snapshot["readiness"]:
        assert isinstance(score["score"], int)
        assert 0 <= score["score"] <= 100
        assert score["explanation"]


def test_go_to_market_top20_comes_from_top100_and_is_not_executed(app_module):
    snapshot = app_module.go_to_market_office_snapshot()
    assert 1 <= len(snapshot["top20_release_actions"]) <= 20
    for item in snapshot["top20_release_actions"]:
        assert item["source"] == "reports/TOP_100_IMPROVEMENTS.md"
        assert item["status"] == "Pendiente"
        assert item["priority"] in {"P1", "P2"}
        assert item["title"]
        assert item["user_value"]
        assert item["business_value"]
        assert item["dependencies"]


def test_go_to_market_route_is_admin_protected_and_renders(client, app_module, monkeypatch):
    blocked = client.get("/admin/go-to-market-office")
    assert blocked.status_code == 302
    assert "/admin-login" in blocked.headers["Location"]

    _admin_session(client)
    monkeypatch.setattr(app_module, "dashboard_data", lambda *args, **kwargs: {})
    response = client.get("/admin/go-to-market-office")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert CONTRACT in html
    assert 'data-go-to-market-mode="read-only"' in html
    assert "Launch Checklist" in html
    assert "Top 20 acciones" in html
    assert "None" not in html
    assert "undefined" not in html


def test_go_to_market_aliases_and_template_are_safe():
    import app as app_module

    routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert {"/admin/go-to-market-office", "/admin/launch-office", "/admin/release-office"}.issubset(routes)

    template = (ROOT / "templates" / "admin_go_to_market_office.html").read_text(encoding="utf-8")
    assert "<form" not in template.lower()
    assert 'method="post"' not in template.lower()
    assert 'data-go-to-market-mode="read-only"' in template
    assert "Sin Stripe" in template
    assert "Sin Telegram" in template


def test_go_to_market_registered_in_contracts_and_roadmap():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    assert capabilities["go_to_market_office"]["contract"] == CONTRACT
    assert capabilities["go_to_market_office"]["state"] in {"INTEGRATED", "CONTRACT_READY"}

    roadmap = build_product_roadmap(ROOT)
    modules = {item["name"]: item for item in roadmap["modules"]}
    assert modules["Go To Market Office"]["state"] in {"COMPLETED", "IN_PROGRESS"}


def test_go_to_market_reports_exist_after_generation():
    for report in [
        "reports/GO_TO_MARKET_OFFICE_REPORT.md",
        "reports/BETA_MANAGEMENT_REPORT.md",
        "reports/COMMERCIAL_READINESS_FINAL.md",
        "reports/CUSTOMER_SUCCESS_REPORT.md",
        "reports/MARKETING_FOUNDATION_REPORT.md",
        "reports/LAUNCH_CHECKLIST_FINAL.md",
        "reports/TOP20_RELEASE_ACTIONS.md",
    ]:
        assert (ROOT / report).is_file()
