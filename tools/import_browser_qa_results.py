from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V919_BROWSER_QA_RESULTS_IMPORT_VALIDATION_AND_VISUAL_QUEUE_GATE_FINAL"
MADRID_TZ = ZoneInfo("Europe/Madrid")
VALID_QUEUE_STATUSES = {
    "BLOCKED_NO_SCREENSHOT",
    "READY_FOR_CODEX",
    "FIXABLE_SAFE",
    "FIXED_BY_V919",
    "NEEDS_HUMAN_VISUAL_REVIEW",
    "DANGEROUS_REQUIRES_APPROVAL",
}


def now_madrid() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_image(path: Path) -> bool:
    return path.exists() and path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.stat().st_size > 0


def screenshot_inventory(input_dir: Path) -> dict:
    desktop = [p for p in (input_dir / "desktop").glob("*") if valid_image(p)] if (input_dir / "desktop").exists() else []
    mobile = [p for p in (input_dir / "mobile").glob("*") if valid_image(p)] if (input_dir / "mobile").exists() else []
    other = [p for p in input_dir.glob("*.png") if valid_image(p)]
    return {
        "desktop": desktop,
        "mobile": mobile,
        "other": other,
        "valid_count": len(desktop) + len(mobile) + len(other),
    }


def comparison_items(comparison: dict) -> list[dict]:
    items = comparison.get("comparisons") or comparison.get("items") or []
    return items if isinstance(items, list) else []


def resolve_screenshot(input_dir: Path, raw: str) -> str:
    if not raw:
        return ""
    candidates = [
        (ROOT / raw).resolve(),
        (input_dir / raw).resolve(),
        (input_dir / Path(raw).name).resolve(),
    ]
    for candidate in candidates:
        try:
            if ROOT.resolve() in candidate.parents and valid_image(candidate):
                return candidate.relative_to(ROOT).as_posix()
        except Exception:
            continue
    return ""


def build_queue_from_comparison(comparison: dict, input_dir: Path) -> dict:
    items: list[dict] = []
    for index, item in enumerate(comparison_items(comparison), start=1):
        route = str(item.get("route") or "browser")
        screenshot = resolve_screenshot(input_dir, str(item.get("screenshot_path") or item.get("screenshot") or ""))
        reference = str(item.get("reference_used") or item.get("reference") or "")
        has_screenshot = bool(screenshot)
        classification = str(item.get("classification") or "")
        if not has_screenshot:
            status = "BLOCKED_NO_SCREENSHOT"
            safe_fix_type = "WAIT_FOR_SCREENSHOT"
        elif classification == "RESOLVED_VISUALLY":
            status = "NEEDS_HUMAN_VISUAL_REVIEW"
            safe_fix_type = "HUMAN_VISUAL_REVIEW"
        else:
            status = "READY_FOR_CODEX"
            safe_fix_type = "SCREENSHOT_BASED_UI_REVIEW"
        notes = item.get("notes") if isinstance(item.get("notes"), list) else []
        items.append({
            "id": f"V919-{index:03d}",
            "route": route,
            "device": "mobile" if "mobile" in str(item.get("profile") or item.get("device") or "") else "desktop",
            "screenshot": screenshot,
            "screenshot_path": screenshot,
            "reference": reference,
            "gap": "; ".join(str(note) for note in notes) if notes else str(item.get("gap") or "Captura real pendiente."),
            "severity": "high" if route.startswith("/admin") or route in {"/app", "/calendar", "/live", "/picks"} else "medium",
            "safe_fix_type": safe_fix_type,
            "codex_prompt": str(item.get("codex_prompt") or f"Captura y compara {route} antes de aplicar cambios visuales."),
            "status": status if status in VALID_QUEUE_STATUSES else "BLOCKED_NO_SCREENSHOT",
            "v919_status": status if status in VALID_QUEUE_STATUSES else "BLOCKED_NO_SCREENSHOT",
            "v919_evidence": "Screenshot real validado." if has_screenshot else "Sin screenshot real validado.",
            "v919_needs_browser_recheck": not has_screenshot,
        })
    blocked = [item for item in items if item["status"] == "BLOCKED_NO_SCREENSHOT"]
    ready = [item for item in items if item["status"] in {"READY_FOR_CODEX", "FIXABLE_SAFE"}]
    return {
        "version": VERSION,
        "generated_at_madrid": now_madrid(),
        "items": items,
        "queue_count": len(items),
        "blocked_no_screenshot_count": len(blocked),
        "ready_for_codex_count": len(ready),
        "pixel_perfect_claim_allowed": False,
        "browser_qa_required": bool(blocked),
        "v919_visual_queue_total": len(items),
        "v919_visual_queue_blocked": len(blocked),
        "v919_visual_queue_ready": len(ready),
        "v919_valid_screenshots_count": len([item for item in items if item.get("screenshot_path")]),
    }


def build_outbox(queue: dict, status: dict) -> str:
    blocked = [item for item in queue.get("items", []) if item.get("status") == "BLOCKED_NO_SCREENSHOT"]
    ready = [item for item in queue.get("items", []) if item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE"}]
    lines = [
        "# Codex Outbox - V919 Browser QA Evidence Gate",
        "",
        "pixel_perfect_claim: false",
        f"generated_at_madrid: {now_madrid()}",
        f"browser_qa_status: {status.get('browser_qa_status') or 'BROWSER_QA_UNAVAILABLE'}",
        f"v919_import_status: {status.get('v919_import_status')}",
        f"valid_screenshots_count: {status.get('screenshots_captured') or 0}",
        f"visual_queue_total: {queue.get('queue_count', 0)}",
        f"visual_queue_blocked: {queue.get('blocked_no_screenshot_count', 0)}",
        f"visual_queue_ready: {queue.get('ready_for_codex_count', 0)}",
        "",
    ]
    if ready:
        lines.append("## V919_SCREENSHOT_CONFIRMED_PROMPTS")
        for item in ready:
            lines.extend([
                f"- `{item.get('route')}` `{item.get('device')}`",
                f"  - Screenshot: `{item.get('screenshot_path')}`",
                f"  - Reference: `{item.get('reference')}`",
                f"  - Prompt: {item.get('codex_prompt')}",
            ])
        lines.append("")
        lines.append("## V919_READY_FOR_CODEX")
        lines.append("- Items above have screenshot evidence and may be reviewed by Codex.")
    else:
        lines.extend([
            "## V919_BROWSER_QA_REQUIRED",
            "- No visual item has real screenshot evidence.",
            "- Execute Browser QA locally or through GitHub Actions before visual fixes.",
            "",
            "## V919_RESULTS_FOUND_BUT_NO_SCREENSHOTS",
            "- Browser QA JSON files exist, but no valid desktop/mobile screenshot files were found.",
            "",
            "## V919_BLOCKED_NO_SCREENSHOT",
        ])
        for item in blocked:
            lines.append(f"- `{item.get('route')}` `{item.get('device')}` -> {item.get('gap')}")
        lines.extend([
            "",
            "## V919_NEXT_ACTION_RUN_BROWSER_QA",
            "- Run Browser QA and upload/import artifacts containing real screenshots.",
        ])
    lines.extend([
        "",
        "## ARCHIVED_OBSOLETE_PROMPTS",
        "- JSON-only visual prompts remain archived until Browser QA screenshots exist.",
        "",
        "## V919_DANGEROUS_REQUIRES_APPROVAL",
        "- No dangerous automatic action was executed.",
        "- Do not touch payments, DB, users, real Telegram, secrets or deploy without approval.",
    ])
    return "\n".join(lines) + "\n"


def update_gap_report(existing: dict, status: dict, comparison: dict, queue: dict) -> dict:
    if not isinstance(existing, dict):
        existing = {}
    items = queue.get("items") if isinstance(queue, dict) else []
    if not isinstance(items, list):
        items = []
    existing["v919_browser_qa_import_status"] = {
        "version": VERSION,
        "updated_at_madrid": now_madrid(),
        "browser_qa_status": status.get("browser_qa_status") or comparison.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
        "import_status": status.get("v919_import_status") or "unknown",
        "valid_screenshots_count": int(status.get("screenshots_captured") or 0),
        "desktop_screenshots_count": int(status.get("desktop_screenshots_count") or 0),
        "mobile_screenshots_count": int(status.get("mobile_screenshots_count") or 0),
        "reference_comparisons": int(comparison.get("reference_comparisons") or len(comparison_items(comparison))),
        "visual_queue_total": len(items),
        "visual_queue_blocked": len([item for item in items if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT"]),
        "visual_queue_ready": len([item for item in items if isinstance(item, dict) and item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE"}]),
        "pixel_perfect_claim_allowed": False,
        "classification": "RESULTS_WITH_SCREENSHOTS" if int(status.get("screenshots_captured") or 0) else "RESULTS_WITHOUT_SCREENSHOTS",
    }
    existing["v919_reference_gap_items"] = [
        {
            "route": item.get("route"),
            "device": item.get("device"),
            "status": item.get("status"),
            "screenshot_path": item.get("screenshot_path"),
            "reference": item.get("reference"),
            "v919_needs_browser_recheck": item.get("status") == "BLOCKED_NO_SCREENSHOT",
        }
        for item in items
        if isinstance(item, dict)
    ]
    return existing


def import_browser_qa_results(input_dir: Path, update_runtime_data: bool) -> dict:
    input_dir = input_dir.resolve()
    root = ROOT.resolve()
    if root not in input_dir.parents and input_dir != root:
        return {"ok": False, "status": "UNSAFE_INPUT_PATH", "input": str(input_dir)}
    result_path = input_dir / "browser_qa_result.json"
    comparison_path = input_dir / "reference_comparison.json"
    fallback_comparison_path = input_dir / "browser_reference_comparison.json"
    json_found = result_path.exists() or comparison_path.exists() or fallback_comparison_path.exists()
    if not json_found:
        payload = {
            "ok": True,
            "version": VERSION,
            "status": "NO_RESULTS_FOUND",
            "input": str(input_dir),
            "updated_runtime_data": False,
            "generated_at_madrid": now_madrid(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload

    status = read_json(result_path, {})
    comparison = read_json(comparison_path if comparison_path.exists() else fallback_comparison_path, {})
    inventory = screenshot_inventory(input_dir)
    valid_count = int(inventory["valid_count"])
    status.update({
        "version": VERSION,
        "browser_qa_status": status.get("browser_qa_status") or comparison.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
        "screenshots_captured": valid_count,
        "desktop_screenshots_count": len(inventory["desktop"]),
        "mobile_screenshots_count": len(inventory["mobile"]),
        "v919_import_status": "VALID_SCREENSHOTS_IMPORTED" if valid_count else "NO_VALID_SCREENSHOTS_TO_IMPORT",
        "pixel_perfect_claim_allowed": False,
    })
    comparison.update({
        "version": VERSION,
        "engine_version": VERSION,
        "screenshots_captured": valid_count,
        "desktop_screenshots_count": len(inventory["desktop"]),
        "mobile_screenshots_count": len(inventory["mobile"]),
        "pixel_perfect_claim": False,
    })
    queue = build_queue_from_comparison(comparison, input_dir)
    runtime_dir = ROOT / "data" / "runtime" / "autonomous_company_sentinel"
    if update_runtime_data:
        write_json(runtime_dir / "browser_qa_status.json", status)
        write_json(runtime_dir / "browser_reference_comparison.json", comparison)
        write_json(runtime_dir / "visual_fix_queue.json", queue)
        gap_path = runtime_dir / "reference_gap_report.json"
        write_json(gap_path, update_gap_report(read_json(gap_path, {}), status, comparison, queue))
        outbox_path = runtime_dir / "outbox" / "codex_outbox.md"
        outbox_path.parent.mkdir(parents=True, exist_ok=True)
        outbox_path.write_text(build_outbox(queue, status), encoding="utf-8")
    payload = {
        "ok": True,
        "version": VERSION,
        "status": "IMPORTED_BROWSER_QA_RESULTS" if valid_count else "NO_VALID_SCREENSHOTS_TO_IMPORT",
        "input": str(input_dir),
        "updated_runtime_data": bool(update_runtime_data),
        "results_json_found": bool(result_path.exists()),
        "reference_comparison_found": bool(comparison_path.exists() or fallback_comparison_path.exists()),
        "screenshots_captured": valid_count,
        "desktop_screenshots_count": len(inventory["desktop"]),
        "mobile_screenshots_count": len(inventory["mobile"]),
        "reference_comparisons": int(comparison.get("reference_comparisons") or len(comparison_items(comparison))),
        "visual_queue_total": queue.get("queue_count", 0),
        "visual_queue_blocked": queue.get("blocked_no_screenshot_count", 0),
        "visual_queue_ready": queue.get("ready_for_codex_count", 0),
        "pixel_perfect_claim_allowed": False,
        "next_required_action": "run_browser_qa_or_upload_artifacts" if not valid_count else "review_ready_visual_queue",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Browser QA screenshots/comparison results into runtime state.")
    parser.add_argument("--input", default="reports/browser_qa_render")
    parser.add_argument("--update-runtime-data", action="store_true")
    args = parser.parse_args()
    payload = import_browser_qa_results(ROOT / args.input, bool(args.update_runtime_data))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
