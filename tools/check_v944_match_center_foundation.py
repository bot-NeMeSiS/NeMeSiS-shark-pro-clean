#!/usr/bin/env python3
"""Local static gate for the V944 Match Center foundation sprint."""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
SPRINT = "V944_MATCH_CENTER_FOUNDATION_PHASE_1_FINAL"
BASE_RUNTIME = "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")


def validate_browser_evidence(path: Path, fingerprint: str) -> tuple[dict, list[str]]:
    from tools.run_v944_match_center_browser_qa import PROFILES, SCENARIOS, observation_failures, screenshot_failures
    failures = []
    if not path.is_file():
        return {}, ["Browser QA result missing"]
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("schema") != "V944-RENDERED-EVIDENCE-1":
            failures.append("Browser QA evidence schema missing")
        if result.get("source_fingerprint") != fingerprint:
            failures.append("Browser QA evidence belongs to another source tree")
        if result.get("status") != "PASS" or result.get("production_modified") is not False:
            failures.append("Browser QA did not pass in isolation")
        if result.get("evidence_origin") != "SIMULATED_QA" or result.get("external_calls") != 0 or result.get("blocked_attempts") != []:
            failures.append("Browser QA isolation evidence incomplete")
        captures = result.get("captures", [])
        expected = {(s, p) for s in SCENARIOS for p in PROFILES}
        if len(captures) != 6 or result.get("screenshots_captured") != 6 or {(r.get("scenario"), r.get("profile")) for r in captures} != expected:
            failures.append("Browser QA evidence is incomplete")
        for row in captures:
            failures.extend(f"{row.get('scenario')}/{row.get('profile')}: {e}" for e in observation_failures(row))
            failures.extend(screenshot_failures(path.parent, row))
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        return {}, [f"Browser QA evidence invalid: {type(exc).__name__}"]
    return result, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-result", type=Path)
    args = parser.parse_args()
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    app_source = read("app.py")
    engine = read("engines/match_context_engine.py")
    template = read("templates/match_detail.html")
    components = read("templates/components/v944_match_center.html")
    browser_result_path = (
        ROOT
        / "browser_qa"
        / "V944_MATCH_CENTER_FOUNDATION"
        / "browser_qa_result.json"
    )

    require(read("VERSION.txt").strip() == BASE_RUNTIME, "VERSION.txt was modified")
    require(read("APP_VERSION").strip() == BASE_RUNTIME, "APP_VERSION was modified")
    require(
        f"APP_VERSION = '{BASE_RUNTIME}'" in app_source,
        "app.py runtime was modified",
    )
    require(
        'MATCH_CENTER_CONTRACT = "MATCH-CENTER-LIFECYCLE-STORY-V1"' in engine,
        "approved Match Center contract missing",
    )
    require("class MatchContext:" in engine, "MatchContext model missing")
    require("def build_match_context(" in engine, "MatchContext builder missing")
    require(
        'data-v944-match-center-foundation="phase-1"' in template,
        "Match Center shell marker missing",
    )
    require(
        template.count("data-v944-match-center-foundation") == 1,
        "duplicate Match Center shell detected",
    )
    require(
        template.count("match_context") >= 10,
        "shell regions do not share MatchContext",
    )
    require(
        not (ROOT / "static" / "v944-match-center.js").exists(),
        "unexpected V944 JavaScript layer detected",
    )

    expected_components = (
        "MatchHeader",
        "ScoreWidget",
        "MatchStory",
        "Timeline",
        "StatsPanel",
        "SharkPanel",
        "TelegramPanel",
        "BankrollPanel",
        "CompetitionPanel",
        "QuickActions",
    )
    expected_states = (
        "loading",
        "ready",
        "partial",
        "finished",
        "error",
        "offline",
        "unknown",
    )
    for name in expected_components:
        require(name in engine and name in components, f"component missing: {name}")
    for state in expected_states:
        require(f'"{state}"' in engine, f"canonical state missing: {state}")

    for relative in (
        "templates/match_detail.html",
        "templates/components/v944_match_center.html",
    ):
        try:
            Environment().parse(read(relative))
        except Exception as exc:
            failures.append(f"Jinja invalid in {relative}: {exc}")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from engines.sentinel_autopilot_engine import (
        build_v944_match_center_foundation_contract_snapshot,
        detect_product_quality_contract_issues,
    )

    contract = build_v944_match_center_foundation_contract_snapshot(
        ROOT,
        BASE_RUNTIME,
    )
    require(contract.get("validation_result") == "PASS", "Sentinel contract failed")
    require(contract.get("production_certified") is False, "local gate claimed production")
    issues = [
        item
        for item in detect_product_quality_contract_issues(ROOT, BASE_RUNTIME)
        if item.get("id") == "V944-MATCH-CENTER-FOUNDATION-CONTRACT"
    ]
    require(not issues, "healthy foundation opened an AutoPilot issue")

    from tools.run_v944_match_center_browser_qa import source_fingerprint
    browser_result, browser_failures = validate_browser_evidence(
        args.browser_result or browser_result_path, source_fingerprint(),
    )
    failures.extend(browser_failures)

    result = {
        "sprint": SPRINT,
        "base_runtime": BASE_RUNTIME,
        "runtime_modified": False,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "contract": contract,
        "browser_qa": {
            "status": browser_result.get("status"),
            "screenshots": browser_result.get("screenshots_captured", 0),
            "profiles": browser_result.get("profiles", []),
        },
        "production_modified": False,
        "production_certified": False,
        "external_calls": 0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
