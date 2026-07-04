"""V892 reference visual QA wrapper for Autonomous Company Sentinel."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engines.sentinel_reference_qa_engine import build_reference_gap_report


SENTINEL_REFERENCE_VISUAL_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"


def run_reference_visual_scan(root: str | Path, visual_result: dict[str, Any] | None = None, browser_available: bool = False) -> dict[str, Any]:
    result = build_reference_gap_report(root, visual_result=visual_result, browser_available=browser_available)
    result["engine_version"] = SENTINEL_REFERENCE_VISUAL_VERSION
    result["worker_area"] = "reference_visual"
    return result
