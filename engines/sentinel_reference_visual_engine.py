"""V899 reference visual QA wrapper for Autonomous Company Sentinel."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engines.browser_visual_qa_engine import run_browser_visual_qa
from engines.product_gap_engine import build_product_gap_report
from engines.reference_image_manifest_engine import build_reference_manifest
from engines.sentinel_reference_qa_engine import build_reference_gap_report


SENTINEL_REFERENCE_VISUAL_VERSION = "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL"


def run_reference_visual_scan(
    root: str | Path,
    visual_result: dict[str, Any] | None = None,
    browser_available: bool = False,
    browser_result: dict[str, Any] | None = None,
    run_browser: bool = False,
    base_url: str = "http://127.0.0.1:5000",
) -> dict[str, Any]:
    manifest = build_reference_manifest(root, write=True)
    if run_browser and browser_result is None:
        browser_result = run_browser_visual_qa(root, base_url=base_url)
        browser_available = bool(browser_result.get("browser_available"))
    gap_report = build_product_gap_report(root, manifest, browser_result or {"browser_available": browser_available}, write=True)
    result = build_reference_gap_report(root, visual_result=visual_result, browser_available=bool(browser_available))
    result["manifest"] = manifest
    result["reference_manifest_path"] = str(Path(root) / "reference_images" / "reference_manifest.json")
    result["product_gap_report"] = gap_report
    result["reference_gap_report_v899"] = gap_report.get("gaps", [])
    result["codex_prompts"] = gap_report.get("codex_prompts", [])
    result["issues"] = (result.get("issues") or []) + (gap_report.get("issues") or [])
    result["browser_result"] = browser_result or {"browser_available": browser_available}
    result["engine_version"] = SENTINEL_REFERENCE_VISUAL_VERSION
    result["worker_area"] = "reference_visual"
    return result
