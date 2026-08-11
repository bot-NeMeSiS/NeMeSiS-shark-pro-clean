#!/usr/bin/env python3
"""Validate the Growth & Revenue OS without commercial side effects."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DB_PATH", str(ROOT / "tmp" / "nemesis_growth_revenue_check.sqlite"))
os.environ.setdefault("SECRET_KEY", "growth-revenue-check-secret")
os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY"):
    os.environ[key] = ""

import app as app_module  # noqa: E402
from engines.growth_revenue_os_engine import GROWTH_REVENUE_OS_CONTRACT  # noqa: E402
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402


REPORTS = [
    ROOT / "reports" / "NEMESIS_GROWTH_REVENUE_OS_REPORT.md",
    ROOT / "reports" / "GROWTH_FUNNEL_SPEC.md",
    ROOT / "reports" / "RESPONSIBLE_MARKETING_POLICY.md",
    ROOT / "reports" / "FOUNDER_REVENUE_BRIEF_SPEC.md",
    ROOT / "reports" / "CUSTOMER_ACQUISITION_ROADMAP.md",
]
FORBIDDEN_ENGINE_RE = re.compile(
    r"\b(requests\.|urlopen|stripe\.|create_checkout_session|send_telegram|telegram_scheduler_tick|subprocess\.run|git\s+push|deploy)\b",
    re.IGNORECASE,
)
MISLEADING_RE = re.compile(
    r"(garantizad[oa]s?|dinero facil|beneficio seguro|100%|sin riesgo|testimonio ficticio|partner oficial)",
    re.IGNORECASE,
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8", errors="replace")


def build_result() -> dict:
    failures: list[str] = []
    founder = app_module.founder_command_center_snapshot()
    snapshot = founder.get("growth_revenue") or {}

    if snapshot.get("contract") != GROWTH_REVENUE_OS_CONTRACT:
        failures.append("contract_mismatch")
    if snapshot.get("mode") != "founder_controlled_read_only":
        failures.append("not_founder_controlled_read_only")
    if len(snapshot.get("roles") or []) != 10:
        failures.append("growth_roles_not_10")
    if len(snapshot.get("funnel") or []) != 11:
        failures.append("funnel_not_11_stages")

    guardrails = snapshot.get("guardrails") or {}
    expected_false = [
        "campaigns_published",
        "mass_messages_sent",
        "telegram_sent",
        "stripe_called",
        "ad_spend",
        "price_changes",
        "affiliate_activation",
        "production_modified",
        "push_executed",
        "deploy_executed",
        "fake_metrics",
        "fake_testimonials",
        "fake_partners",
    ]
    for key in expected_false:
        if guardrails.get(key) is not False:
            failures.append(f"unsafe_guardrail:{key}")
    if guardrails.get("external_calls") != 0:
        failures.append("external_calls_not_zero")

    level5 = next((item for item in snapshot.get("automation_levels") or [] if item.get("level") == 5), {})
    if level5.get("allowed") is not False or level5.get("human_approval_required") is not True:
        failures.append("automation_level_5_not_blocked")
    if (snapshot.get("paid_ads") or {}).get("spend_allowed") is not False:
        failures.append("paid_ads_spend_allowed")
    if (snapshot.get("content_factory") or {}).get("automatic_publication") is not False:
        failures.append("content_factory_auto_publish_allowed")

    engine_text = read("engines/growth_revenue_os_engine.py")
    if FORBIDDEN_ENGINE_RE.search(engine_text):
        failures.append("forbidden_call_in_growth_engine")
    claim_surface = "`n".join(
        line
        for line in engine_text.splitlines()
        if '"required":' not in line and '"blocked":' not in line
    )
    if MISLEADING_RE.search(claim_surface):
        failures.append("misleading_marketing_claim")

    template = read("templates/admin_founder_dashboard.html")
    if 'id="growth-revenue"' not in template:
        failures.append("founder_growth_panel_missing")
    else:
        growth_slice = template.split('id="growth-revenue"', 1)[1].split('id="beta-control"', 1)[0]
        if "<form" in growth_slice.lower() or 'method="post"' in growth_slice.lower():
            failures.append("growth_panel_contains_write_form")
        if "INSUFFICIENT_REAL_DATA" not in growth_slice:
            failures.append("growth_panel_hides_insufficient_data")

    missing_reports = [str(path.relative_to(ROOT)) for path in REPORTS if not path.is_file()]
    if missing_reports:
        failures.append("missing_reports:" + ",".join(missing_reports))

    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item.get("key"): item for item in registry.get("capabilities") or []}
    if (capabilities.get("growth_revenue_os") or {}).get("contract") != GROWTH_REVENUE_OS_CONTRACT:
        failures.append("contract_registry_missing_growth")

    roadmap = build_product_roadmap(ROOT)
    modules = {item.get("name"): item for item in roadmap.get("modules") or []}
    if "Growth & Revenue OS" not in modules:
        failures.append("roadmap_missing_growth")

    return {
        "ok": not failures,
        "contract": GROWTH_REVENUE_OS_CONTRACT,
        "status": snapshot.get("status"),
        "readiness_score": snapshot.get("readiness_score"),
        "roles": len(snapshot.get("roles") or []),
        "funnel_stages": len(snapshot.get("funnel") or []),
        "top20_revenue_actions": len(snapshot.get("top20_revenue_actions") or []),
        "reports": [str(path.relative_to(ROOT)) for path in REPORTS],
        "external_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "ad_spend": False,
        "campaigns_published": False,
        "failures": failures,
        "decision": "PASS LOCAL" if not failures else "BLOCKED",
    }


def main() -> int:
    result = build_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
