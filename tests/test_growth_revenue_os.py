from __future__ import annotations

from pathlib import Path

from engines.growth_revenue_os_engine import (
    GROWTH_REVENUE_OS_CONTRACT,
    build_growth_revenue_os_snapshot,
)
from engines.project_operating_system_engine import build_product_roadmap
from engines.sports_platform_contracts import build_sports_platform_contract_registry


ROOT = Path(__file__).resolve().parents[1]


def _sample_snapshot():
    return build_growth_revenue_os_snapshot(
        product_snapshot={
            "funnel": {"registered": 12, "active": 4, "pro_interest": 2, "checkout_started": 1},
            "users": {"memberships": {"FREE": 10, "PRO": 1, "ELITE": 1}},
            "conversion_registered_to_paid": {"value": 16.67, "state": "PARTIALLY_VERIFIED"},
        },
        revenue_snapshot={
            "memberships": {"FREE": 10, "PRO": 1, "ELITE": 1},
            "payment_event_counts": {"payments_confirmed": 0},
            "mrr": None,
        },
        beta_snapshot={"state": "PARTIAL"},
        support_snapshot={"open_feedback": 1, "open_tickets": 0},
        top100_snapshot={"total": 100},
        roadmap_snapshot={"current_sprint": "LRM-001"},
        app_version="TEST",
        now_madrid="2026-08-12T10:00:00+02:00",
    )


def test_growth_revenue_os_is_evidence_first_and_founder_controlled():
    snapshot = _sample_snapshot()

    assert snapshot["contract"] == GROWTH_REVENUE_OS_CONTRACT
    assert snapshot["mode"] == "founder_controlled_read_only"
    assert len(snapshot["roles"]) == 10
    assert len(snapshot["funnel"]) == 11
    assert snapshot["guardrails"]["external_calls"] == 0
    assert snapshot["guardrails"]["campaigns_published"] is False
    assert snapshot["guardrails"]["mass_messages_sent"] is False
    assert snapshot["guardrails"]["telegram_sent"] is False
    assert snapshot["guardrails"]["stripe_called"] is False
    assert snapshot["guardrails"]["ad_spend"] is False
    assert snapshot["guardrails"]["fake_metrics"] is False

    stages = {item["label"]: item for item in snapshot["funnel"]}
    assert stages["DISCOVERY"]["evidence_state"] == "INSUFFICIENT_REAL_DATA"
    assert stages["REGISTRATION"]["evidence_state"] == "PARTIALLY_VERIFIED"
    assert stages["PRO / ELITE"]["value"] == 2
    assert snapshot["founder_revenue_brief"]["mrr"] == "No certificado"
    assert snapshot["founder_revenue_brief"]["main_channels"] == "Sin atribucion real"


def test_growth_automation_levels_never_allow_publish_or_spend():
    snapshot = _sample_snapshot()

    level5 = next(item for item in snapshot["automation_levels"] if item["level"] == 5)
    assert level5["allowed"] is False
    assert level5["human_approval_required"] is True
    assert snapshot["paid_ads"]["spend_allowed"] is False
    assert snapshot["content_factory"]["automatic_publication"] is False
    assert snapshot["content_factory"]["founder_only_can_approve"] is True


def test_growth_registry_and_roadmap_are_integrated():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    assert capabilities["growth_revenue_os"]["contract"] == GROWTH_REVENUE_OS_CONTRACT
    assert capabilities["growth_revenue_os"]["state"] in {"INTEGRATED", "CONTRACT_READY"}

    roadmap = build_product_roadmap(ROOT)
    modules = {item["name"]: item for item in roadmap["modules"]}
    assert modules["Growth & Revenue OS"]["state"] in {"COMPLETED", "IN_PROGRESS"}


def test_founder_dashboard_template_contains_growth_center_without_write_controls():
    template = (ROOT / "templates" / "admin_founder_dashboard.html").read_text(encoding="utf-8")
    assert 'id="growth-revenue"' in template
    growth_slice = template.split('id="growth-revenue"', 1)[1].split('id="beta-control"', 1)[0]
    assert "Growth & Revenue OS" in growth_slice
    assert "INSUFFICIENT_REAL_DATA" in growth_slice
    assert "<form" not in growth_slice.lower()
    assert "method=\"post\"" not in growth_slice.lower()
