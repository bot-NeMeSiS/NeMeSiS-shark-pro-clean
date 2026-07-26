#!/usr/bin/env python3
"""Static local gate for the V940 Calendar Sports Experience."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    app_source = read("app.py")
    template = read("templates/calendar.html")
    css = read("static/v933-product.css")
    javascript = read("static/v940-calendar.js")
    specification = ROOT / "reports" / "V940_CALENDAR_SPORTS_EXPERIENCE_TECHNICAL_SPECIFICATION.md"

    require(read("VERSION.txt").strip() == VERSION, "VERSION.txt mismatch")
    require(read("APP_VERSION").strip() == VERSION, "APP_VERSION file mismatch")
    require(f"APP_VERSION = '{VERSION}'" in app_source, "app.py version mismatch")
    require("NEMESIS_CACHE_V940" in app_source, "service worker cache mismatch")
    require(
        "has_v940_nemesis_sports_experience_phase_1_foundation" in app_source,
        "runtime V940 flag missing",
    )
    require(
        "has_v939_autonomous_company_intelligence_growth_quality_platform" in app_source,
        "runtime V939 flag not preserved",
    )
    require(specification.exists(), "technical specification missing")
    require(
        app_source.count("v940_calendar_context(summary, lane, date_value)") >= 2,
        "page and API do not share v940_calendar_context",
    )
    require("get_sports_metrics_contract(summary)" in app_source, "sports-metrics-v1 consumer missing")
    require(
        'data-v940-calendar-experience="history-layers-v1"' in template,
        "Calendar root contract missing",
    )
    for marker in (
        "data-v940-calendar-command",
        "data-v940-calendar-context",
        "data-v940-calendar-index",
        "data-v940-calendar-collection",
        "data-v940-calendar-filters-active",
    ):
        require(marker in template, f"template marker missing: {marker}")
    require(template.count("{{ match_card(match, false, true) }}") == 1, "canonical match_card use mismatch")
    require(template.count("v933-match-grid") == 1, "duplicate Calendar collection detected")
    require(".v940-calendar-context {" in css and "position: sticky;" in css, "sticky context missing")
    require("@media (max-width: 800px)" in css, "mobile Calendar contract missing")
    require("window.sessionStorage" in javascript, "position memory missing")
    require("IntersectionObserver" in javascript, "current context observer missing")
    require('navigationType() !== "back_forward"' in javascript, "history-only restoration missing")
    require("fetch(" not in javascript, "Calendar JS performs a network call")
    require("XMLHttpRequest" not in javascript, "Calendar JS performs XHR")
    require("sendBeacon(" not in javascript, "Calendar JS performs beacon writes")

    try:
        Environment().parse(template)
    except Exception as exc:
        failures.append(f"Calendar Jinja invalid: {exc}")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from engines.sentinel_autopilot_engine import (
        build_v940_calendar_experience_contract_snapshot,
        detect_product_quality_contract_issues,
    )

    contract = build_v940_calendar_experience_contract_snapshot(ROOT, VERSION)
    require(contract.get("validation_result") == "PASS", "Sentinel Calendar contract failed")
    require(contract.get("production_certified") is False, "local check claimed production certification")
    v940_issues = [
        item
        for item in detect_product_quality_contract_issues(ROOT, VERSION)
        if item.get("id") == "V940-CALENDAR-EXPERIENCE-CONTRACT"
    ]
    require(not v940_issues, "healthy Calendar opens a Sentinel issue")

    result = {
        "version": VERSION,
        "check": "V940 Calendar Sports Experience",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "contract": contract,
        "production_modified": False,
        "production_certified": False,
        "external_calls": 0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
