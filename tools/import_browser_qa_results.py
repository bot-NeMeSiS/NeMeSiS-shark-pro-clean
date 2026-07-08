from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V913_BROWSER_QA_EXECUTION_STATUS_TRUTH_AND_RUNTIME_CLEANUP_FINAL"
MADRID_TZ = ZoneInfo("Europe/Madrid")
VALID_QUEUE_STATUSES = {
    "BLOCKED_NO_SCREENSHOT",
    "READY_FOR_CODEX",
    "FIXABLE_SAFE",
    "FIXED_BY_V913",
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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def comparison_items(comparison: dict) -> list[dict]:
    items = comparison.get("comparisons") or comparison.get("items") or []
    return items if isinstance(items, list) else []


def build_queue_from_comparison(comparison: dict) -> dict:
    items: list[dict] = []
    for index, item in enumerate(comparison_items(comparison), start=1):
        route = str(item.get("route") or "browser")
        screenshot = str(item.get("screenshot_path") or item.get("screenshot") or "")
        reference = str(item.get("reference_used") or item.get("reference") or "")
        has_screenshot = bool(screenshot)
        classification = str(item.get("classification") or "")
        if not has_screenshot:
            status = "BLOCKED_NO_SCREENSHOT"
            safe_fix_type = "WAIT_FOR_SCREENSHOT"
        elif classification in {"RESOLVED_VISUALLY"}:
            status = "NEEDS_HUMAN_VISUAL_REVIEW"
            safe_fix_type = "HUMAN_VISUAL_REVIEW"
        else:
            status = "READY_FOR_CODEX"
            safe_fix_type = "SCREENSHOT_BASED_UI_REVIEW"
        notes = item.get("notes") if isinstance(item.get("notes"), list) else []
        items.append({
            "id": f"V913-{index:03d}",
            "route": route,
            "device": "mobile" if "mobile" in str(item.get("profile") or item.get("device") or "") else "desktop",
            "screenshot": screenshot,
            "reference": reference,
            "gap": "; ".join(str(note) for note in notes) if notes else str(item.get("gap") or "Captura real pendiente."),
            "severity": "high" if route.startswith("/admin") or route in {"/app", "/calendar", "/live", "/picks"} else "medium",
            "safe_fix_type": safe_fix_type,
            "codex_prompt": str(item.get("codex_prompt") or f"Captura y compara {route} antes de aplicar cambios visuales."),
            "status": status if status in VALID_QUEUE_STATUSES else "BLOCKED_NO_SCREENSHOT",
            "v913_status": status if status in VALID_QUEUE_STATUSES else "BLOCKED_NO_SCREENSHOT",
            "v913_evidence": "Captura real disponible." if has_screenshot else "Sin screenshot real importado.",
            "v913_needs_browser_recheck": not has_screenshot,
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
        "v913_visual_queue_total": len(items),
        "v913_visual_queue_blocked": len(blocked),
        "v913_visual_queue_ready": len(ready),
    }


def build_outbox(queue: dict, status: dict, comparison: dict) -> str:
    blocked = [item for item in queue.get("items", []) if item.get("status") == "BLOCKED_NO_SCREENSHOT"]
    ready = [item for item in queue.get("items", []) if item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE"}]
    lines = [
        "# Codex Outbox - V913 Browser QA Truth",
        "",
        "pixel_perfect_claim: false",
        f"generated_at_madrid: {now_madrid()}",
        f"browser_qa_status: {status.get('browser_qa_status') or comparison.get('browser_qa_status') or 'BROWSER_QA_UNAVAILABLE'}",
        f"screenshots_captured: {status.get('screenshots_captured') or comparison.get('screenshots_captured') or 0}",
        f"visual_queue_total: {queue.get('queue_count', 0)}",
        f"visual_queue_blocked: {queue.get('blocked_no_screenshot_count', 0)}",
        f"visual_queue_ready: {queue.get('ready_for_codex_count', 0)}",
        "",
        "## V913_BROWSER_QA_EXECUTION_REQUIRED",
    ]
    if blocked:
        lines.append("- Ejecutar Browser QA real o importar resultados antes de cerrar gaps visuales.")
        lines.append("- Comando local: `.\\.venv\\Scripts\\python.exe tools\\run_browser_reference_qa.py --base-url https://bot-apuestas-crgf.onrender.com --output reports/browser_qa_render --mobile --desktop --write-json`")
        lines.append("- Importar resultados: `.\\.venv\\Scripts\\python.exe tools\\import_browser_qa_results.py --input reports/browser_qa_render --update-runtime-data`")
    else:
        lines.append("- No hay items bloqueados por falta de screenshot.")
    lines.extend(["", "## V913_READY_FOR_CODEX_WITH_SCREENSHOTS"])
    if ready:
        for item in ready:
            lines.extend([
                f"- `{item.get('route')}` `{item.get('device')}`",
                f"  - Captura: `{item.get('screenshot')}`",
                f"  - Referencia: `{item.get('reference')}`",
                f"  - Prompt: {item.get('codex_prompt')}",
            ])
    else:
        lines.append("- Sin prompts visuales accionables porque no hay screenshots reales.")
    lines.extend(["", "## V913_BLOCKED_NO_SCREENSHOT"])
    for item in blocked:
        lines.append(f"- `{item.get('route')}` `{item.get('device')}` -> {item.get('gap')}")
    lines.extend([
        "",
        "## V913_RUNTIME_STATUS_FIXES",
        "- Runtime V913 expone estado real de Browser QA, cola visual y siguiente accion.",
        "- Estados V910 historicos se mantienen como auditoria; V913 publica resumen propio veraz.",
        "",
        "## V913_SAFE_FIXES_APPLIED",
        "- Cola visual normalizada a estados permitidos.",
        "- Outbox evita prompts visuales falsos sin captura.",
        "- Importador seguro creado para resultados externos.",
        "",
        "## V913_DANGEROUS_REQUIRES_APPROVAL",
        "- Sin acciones peligrosas ejecutadas.",
        "- No tocar pagos, DB, usuarios, Telegram real, secretos ni deploy sin aprobacion.",
        "",
        "## ARCHIVED_OBSOLETE_PROMPTS",
        "- Prompts visuales sin screenshot quedan archivados como no accionables hasta Browser QA real.",
    ])
    return "\n".join(lines) + "\n"


def build_reference_gap_update(existing: dict, status: dict, comparison: dict, queue: dict) -> dict:
    if not isinstance(existing, dict):
        existing = {}
    screenshots = int(status.get("screenshots_captured") or comparison.get("screenshots_captured") or 0)
    items = queue.get("items") if isinstance(queue, dict) else []
    if not isinstance(items, list):
        items = []
    existing["v913_browser_qa_import_status"] = {
        "version": VERSION,
        "updated_at_madrid": now_madrid(),
        "browser_qa_status": status.get("browser_qa_status") or comparison.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
        "screenshots_captured": screenshots,
        "reference_comparisons": int(comparison.get("reference_comparisons") or len(comparison_items(comparison))),
        "visual_queue_total": len(items),
        "visual_queue_blocked": len([item for item in items if isinstance(item, dict) and item.get("status") == "BLOCKED_NO_SCREENSHOT"]),
        "visual_queue_ready": len([item for item in items if isinstance(item, dict) and item.get("status") in {"READY_FOR_CODEX", "FIXABLE_SAFE"}]),
        "pixel_perfect_claim_allowed": False,
        "classification": "BROWSER_QA_IMPORTED_WITH_SCREENSHOTS" if screenshots else "BROWSER_QA_REQUIRED_BEFORE_PIXEL_CLAIM",
    }
    existing["v913_reference_gap_items"] = [
        {
            "route": item.get("route"),
            "device": item.get("device"),
            "status": item.get("status"),
            "screenshot": item.get("screenshot"),
            "reference": item.get("reference"),
            "v913_needs_browser_recheck": item.get("status") == "BLOCKED_NO_SCREENSHOT",
        }
        for item in items
        if isinstance(item, dict)
    ]
    return existing


def import_browser_qa_results(input_dir: Path, update_runtime_data: bool) -> dict:
    input_dir = input_dir.resolve()
    if not str(input_dir).startswith(str(ROOT.resolve())):
        return {"ok": False, "status": "UNSAFE_INPUT_PATH", "input": str(input_dir)}
    result_path = input_dir / "browser_qa_result.json"
    comparison_path = input_dir / "reference_comparison.json"
    fallback_comparison_path = input_dir / "browser_reference_comparison.json"
    if not result_path.exists() and not comparison_path.exists() and not fallback_comparison_path.exists():
        payload = {
            "ok": True,
            "version": VERSION,
            "status": "NO_BROWSER_QA_RESULTS_TO_IMPORT",
            "input": str(input_dir),
            "updated_runtime_data": False,
            "generated_at_madrid": now_madrid(),
            "note": "No se encontraron resultados Browser QA; release no falla.",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload
    status = read_json(result_path, {})
    comparison = read_json(comparison_path if comparison_path.exists() else fallback_comparison_path, {})
    status["version"] = VERSION
    status.setdefault("browser_qa_status", comparison.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE")
    status.setdefault("screenshots_captured", comparison.get("screenshots_captured") or 0)
    comparison["version"] = VERSION
    comparison["engine_version"] = VERSION
    comparison["pixel_perfect_claim"] = False
    queue = build_queue_from_comparison(comparison)
    runtime_dir = ROOT / "data" / "runtime" / "autonomous_company_sentinel"
    if update_runtime_data:
        write_json(runtime_dir / "browser_qa_status.json", status)
        write_json(runtime_dir / "browser_reference_comparison.json", comparison)
        write_json(runtime_dir / "visual_fix_queue.json", queue)
        gap_path = runtime_dir / "reference_gap_report.json"
        write_json(gap_path, build_reference_gap_update(read_json(gap_path, {}), status, comparison, queue))
        outbox_path = runtime_dir / "outbox" / "codex_outbox.md"
        outbox_path.parent.mkdir(parents=True, exist_ok=True)
        outbox_path.write_text(build_outbox(queue, status, comparison), encoding="utf-8")
    payload = {
        "ok": True,
        "version": VERSION,
        "status": "IMPORTED_BROWSER_QA_RESULTS" if int(status.get("screenshots_captured") or 0) else "IMPORTED_NO_SCREENSHOTS",
        "input": str(input_dir),
        "updated_runtime_data": bool(update_runtime_data),
        "screenshots_captured": int(status.get("screenshots_captured") or 0),
        "reference_comparisons": int(comparison.get("reference_comparisons") or len(comparison_items(comparison))),
        "visual_queue_total": queue.get("queue_count", 0),
        "visual_queue_blocked": queue.get("blocked_no_screenshot_count", 0),
        "visual_queue_ready": queue.get("ready_for_codex_count", 0),
        "pixel_perfect_claim_allowed": False,
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
