from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")
ENGINE_VERSION = "V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL"

REFERENCE_BY_ROUTE = {
    "/": "reference_images/client",
    "/app": "reference_images/client",
    "/calendar": "reference_images/calendar",
    "/live": "reference_images/live",
    "/picks": "reference_images/picks",
    "/shark": "reference_images/shark",
    "/telegram": "reference_images/telegram",
    "/profile": "reference_images/profile",
    "/admin-login": "reference_images/admin",
    "/admin/dashboard": "reference_images/admin",
    "/admin/autonomous-company-sentinel": "reference_images/admin",
    "/admin/sentinel-issues": "reference_images/admin",
    "/admin/sentinel-codex-outbox": "reference_images/admin",
    "/admin/not-found-events": "reference_images/admin",
}


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        pass
    return default


def _reference_for_route(root: Path, route: str) -> str:
    folder = root / REFERENCE_BY_ROUTE.get(route, "reference_images")
    if folder.exists():
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            found = sorted(folder.glob(pattern))
            if found:
                return found[0].relative_to(root).as_posix()
    return ""


def _score_capture(capture: dict[str, Any], browser_available: bool) -> tuple[int, str, list[str]]:
    if not browser_available:
        return 0, "NEEDS_BROWSER_QA", ["No hay captura real disponible."]
    if capture.get("error"):
        return 2, "STILL_PENDING", [str(capture.get("error"))[:220]]
    score = 7
    notes: list[str] = []
    status = int(capture.get("status") or 0)
    if status in {301, 302, 303, 307, 308, 401, 403}:
        score -= 1
        notes.append("Ruta protegida o redirigida de forma segura.")
    elif status != 200:
        score -= 3
        notes.append(f"Estado HTTP inesperado: {status}.")
    if capture.get("overflow_x"):
        score -= 2
        notes.append("Posible scroll horizontal detectado.")
    if capture.get("screenshot"):
        score += 1
        notes.append("Captura real disponible.")
    status_label = "RESOLVED_VISUALLY" if score >= 8 else "IMPROVED_NEEDS_REVIEW" if score >= 5 else "STILL_PENDING"
    return max(0, min(10, score)), status_label, notes


def build_browser_reference_comparison(
    root: str | Path,
    *,
    qa_payload: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(root)
    qa_payload = qa_payload or _load_json(base / "reports" / "V906_browser_qa" / "browser_reference_qa_report.json", {})
    manifest = _load_json(base / "reference_images" / "reference_manifest.json", {})
    browser_available = bool(qa_payload.get("browser_available"))
    captures = [item for item in qa_payload.get("screenshots", []) if isinstance(item, dict)]
    comparisons: list[dict[str, Any]] = []
    for capture in captures:
        route = str(capture.get("route") or "")
        score, status, notes = _score_capture(capture, browser_available)
        reference = _reference_for_route(base, route)
        comparisons.append({
            "route": route,
            "profile": capture.get("profile") or capture.get("device") or "",
            "screenshot_path": capture.get("screenshot") or "",
            "reference_used": reference,
            "visual_gap_score": score,
            "classification": status,
            "browser_qa_status": "CAPTURED" if browser_available and capture.get("screenshot") else "BROWSER_QA_UNAVAILABLE",
            "addressed_by_v904": route in {"/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/admin/dashboard"},
            "addressed_by_v905": route in {"/", "/admin-login"} or "V905" in str(capture.get("screenshot") or ""),
            "needs_v906_followup": status not in {"RESOLVED_VISUALLY"},
            "notes": notes,
            "codex_prompt": (
                "Revisa la captura real de NeMeSiS SHARK PRO sin inventar datos.\n"
                f"Ruta: {route}\n"
                f"Captura: {capture.get('screenshot') or 'No disponible'}\n"
                f"Referencia: {reference or 'Sin referencia especifica'}\n"
                f"Gap observado: {', '.join(notes) or 'Comparacion visual pendiente'}\n"
                "Objetivo: acercar la pantalla a la referencia manteniendo estados seguros, cliente/admin separados y sin tocar secretos."
            ),
        })

    target_routes = sorted(set(REFERENCE_BY_ROUTE) | {str(item.get("route") or "") for item in captures if item.get("route")})
    captured_routes = {str(item.get("route") or "") for item in captures}
    for route in target_routes:
        if route in captured_routes:
            continue
        comparisons.append({
            "route": route,
            "profile": "pending",
            "screenshot_path": "",
            "reference_used": _reference_for_route(base, route),
            "visual_gap_score": 0,
            "classification": "NEEDS_BROWSER_QA",
            "browser_qa_status": "BROWSER_QA_UNAVAILABLE",
            "addressed_by_v904": route in {"/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/admin/dashboard"},
            "addressed_by_v905": route in {"/"},
            "needs_v906_followup": True,
            "notes": ["Captura real pendiente."],
            "codex_prompt": f"Captura y compara {route} contra referencias reales antes de declarar cierre visual.",
        })

    resolved = [item for item in comparisons if item["classification"] == "RESOLVED_VISUALLY"]
    pending = [item for item in comparisons if item["classification"] in {"STILL_PENDING", "NEEDS_BROWSER_QA", "IMPROVED_NEEDS_REVIEW"}]
    payload = {
        "ok": True,
        "engine_version": ENGINE_VERSION,
        "generated_at_madrid": _now(),
        "browser_qa_status": "CAPTURED" if browser_available else "BROWSER_QA_UNAVAILABLE",
        "reference_manifest_count": manifest.get("reference_count") or len(manifest.get("references", []) or []),
        "screenshots_captured": len([item for item in captures if item.get("screenshot")]),
        "reference_comparisons": len(comparisons),
        "visual_gaps_resolved": len(resolved),
        "visual_gaps_pending": len(pending),
        "pixel_perfect_claim": False,
        "comparisons": comparisons,
    }
    runtime_path = base / "data" / "runtime" / "autonomous_company_sentinel" / "browser_reference_comparison.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "browser_reference_comparison.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
