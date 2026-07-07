from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.browser_reference_comparison_engine import build_browser_reference_comparison
from tools.check_browser_qa_environment import detect_browser_qa_environment


VERSION = "V907_BROWSER_QA_ENABLEMENT_FIRST_SCREENSHOT_GAP_FIX_FINAL"
PUBLIC_ROUTES = ["/", "/cliente-login", "/registro"]
CLIENT_ROUTES = ["/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/profile", "/support"]
ADMIN_SAFE_ROUTES = ["/admin-login"]
ADMIN_PROTECTED_ROUTES = [
    "/admin/dashboard",
    "/admin/autonomous-company-sentinel",
    "/admin/sentinel-issues",
    "/admin/sentinel-codex-outbox",
    "/admin/not-found-events",
    "/admin/telegram/command-center",
]


def _now_label() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat()


def _status_paths(output: Path) -> tuple[Path, Path, Path]:
    runtime_dir = ROOT / "data" / "runtime" / "autonomous_company_sentinel"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    return (
        output / "browser_reference_qa_report.json",
        runtime_dir / "browser_qa_status.json",
        runtime_dir / "reference_gap_report.json",
    )


def _write_markdown_status(payload: dict, output: Path) -> None:
    report = ROOT / "reports" / "V907_BROWSER_QA_STATUS.md"
    status = payload.get("browser_qa_status") or ("CAPTURED" if payload.get("browser_available") else "BROWSER_QA_UNAVAILABLE")
    lines = [
        "# V907 Browser QA Status",
        "",
        f"- Version: {payload.get('version', VERSION)}",
        f"- Status: {status}",
        f"- Playwright available: {payload.get('playwright_available', payload.get('browser_available', False))}",
        f"- Browsers available: {payload.get('browsers_available', payload.get('browser_available', False))}",
        f"- Screenshots captured: {payload.get('screenshots_captured', 0)}",
        f"- Output: `{output.as_posix()}`",
        f"- Reason: {payload.get('reason') or 'Sin error'}",
        "",
        "No se declara pixel-perfect sin capturas reales comparadas.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_reference_gap_status(comparison: dict) -> None:
    _, _, gap_path = _status_paths(ROOT / "reports" / "V907_browser_qa")
    try:
        existing = json.loads(gap_path.read_text(encoding="utf-8-sig", errors="replace")) if gap_path.exists() else {}
    except Exception:
        existing = {}
    comparisons = comparison.get("comparisons") or []
    existing["v907_browser_reference_status"] = {
        "version": VERSION,
        "browser_qa_status": comparison.get("browser_qa_status"),
        "screenshots_captured": comparison.get("screenshots_captured", 0),
        "reference_comparisons": comparison.get("reference_comparisons", 0),
        "visual_gaps_resolved": comparison.get("visual_gaps_resolved", 0),
        "visual_gaps_pending": comparison.get("visual_gaps_pending", 0),
        "pixel_perfect_claim": False,
        "updated_at_madrid": _now_label(),
    }
    existing["v907_browser_gap_report"] = comparisons
    compatibility_status = {
        "version": VERSION,
        "browser_qa_status": comparison.get("browser_qa_status"),
        "screenshots_captured": comparison.get("screenshots_captured", 0),
        "reference_comparisons": comparison.get("reference_comparisons", 0),
        "visual_gaps_resolved": comparison.get("visual_gaps_resolved", 0),
        "visual_gaps_pending": comparison.get("visual_gaps_pending", 0),
        "pixel_perfect_claim": False,
        "updated_by": "V907 browser QA enablement",
        "updated_at_madrid": _now_label(),
    }
    existing["v906_browser_status"] = compatibility_status
    existing["v906_browser_reference_status"] = compatibility_status
    existing["v906_browser_gap_report"] = comparisons
    existing["v905_final_reference_gap_status"] = compatibility_status
    gap_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_outbox(comparison: dict) -> None:
    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    outbox.parent.mkdir(parents=True, exist_ok=True)
    comparisons = comparison.get("comparisons") or []
    captured = [item for item in comparisons if item.get("screenshot_path")]
    pending = [item for item in comparisons if item.get("classification") != "RESOLVED_VISUALLY"]
    admin = [item for item in pending if str(item.get("route") or "").startswith("/admin")]
    client_mobile = [item for item in pending if item.get("profile") and "mobile" in str(item.get("profile"))]
    picks_live = [item for item in pending if item.get("route") in {"/picks", "/live", "/calendar"}]
    shark_telegram = [item for item in pending if item.get("route") in {"/shark", "/telegram", "/admin/telegram/command-center"}]

    def prompt_block(items: list[dict], limit: int = 8) -> list[str]:
        if not items:
            return ["- Sin prompts activos en esta sección."]
        lines: list[str] = []
        for item in items[:limit]:
            lines.extend([
                f"## Ruta {item.get('route')}",
                "",
                f"- Captura actual: `{item.get('screenshot_path') or 'pendiente'}`",
                f"- Referencia usada: `{item.get('reference_used') or 'pendiente'}`",
                f"- Clasificación: {item.get('classification')}",
                f"- Gap: {'; '.join(item.get('notes') or ['Pendiente de Browser QA'])}",
                "- Archivos probables: `templates/`, `static/app.css`, `templates/partials/`",
                "- Restricciones: no inventar datos, no tocar secretos, no pagos, no Telegram real.",
                "- Validaciones: Browser QA, Sentinel, smoke Flask, sin overflow y sin mojibake.",
                "",
                "```text",
                str(item.get("codex_prompt") or "Revisar pantalla con captura real antes de tocar visual."),
                "```",
                "",
            ])
        return lines

    lines = [
        "# Codex Outbox - V907 Browser QA",
        "",
        "pixel_perfect_claim: false",
        f"generated_at_madrid: {_now_label()}",
        f"screenshots_captured: {comparison.get('screenshots_captured', 0)}",
        f"reference_comparisons: {comparison.get('reference_comparisons', 0)}",
        f"visual_gaps_resolved: {comparison.get('visual_gaps_resolved', 0)}",
        f"visual_gaps_pending: {comparison.get('visual_gaps_pending', 0)}",
        "",
        "# V907_BROWSER_QA_FINDINGS",
        f"- Browser QA status: {comparison.get('browser_qa_status')}",
        f"- Capturas reales: {len(captured)}",
        f"- Pendientes: {len(pending)}",
        "",
        "# SCREENSHOT_BASED_VISUAL_PROMPTS",
        *prompt_block([item for item in pending if item.get("screenshot_path")]),
        "# ADMIN_SCREENSHOT_PROMPTS",
        *prompt_block(admin),
        "# CLIENT_MOBILE_SCREENSHOT_PROMPTS",
        *prompt_block(client_mobile),
        "# PICKS_LIVE_CALENDAR_SCREENSHOT_PROMPTS",
        *prompt_block(picks_live),
        "# SHARK_TELEGRAM_SCREENSHOT_PROMPTS",
        *prompt_block(shark_telegram),
        "# PENDING_BROWSER_QA",
        *prompt_block([item for item in pending if not item.get("screenshot_path")]),
        "# PENDING_HUMAN_VISUAL_REVIEW",
        "- Revisión humana visual requerida para cualquier gap que necesite criterio de referencia/pixel real.",
        "# ARCHIVED_STATIC_PROMPTS",
        "- Prompts estáticos anteriores quedan archivados si no tienen captura asociada o si no se reproducen con Browser QA.",
    ]
    outbox.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_payload(output: Path, payload: dict, comparison: dict | None = None) -> dict:
    report_path, status_path, _ = _status_paths(output)
    payload["version"] = VERSION
    payload["browser_qa_status"] = payload.get("browser_qa_status") or ("CAPTURED" if payload.get("browser_available") else "BROWSER_QA_UNAVAILABLE")
    payload["write_json"] = True
    if comparison:
        payload["comparison_summary"] = {
            "reference_comparisons": comparison.get("reference_comparisons"),
            "visual_gaps_resolved": comparison.get("visual_gaps_resolved"),
            "visual_gaps_pending": comparison.get("visual_gaps_pending"),
        }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown_status(payload, output)
    return payload


def _unavailable_payload(output: Path, reason: str, env: dict | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "version": VERSION,
        "generated_at_madrid": _now_label(),
        "browser_available": False,
        "playwright_available": bool((env or {}).get("playwright_available")),
        "browsers_available": bool((env or {}).get("browsers_available")),
        "can_capture": False,
        "browser_qa_status": (env or {}).get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE",
        "recommended_install_command": (env or {}).get("recommended_install_command") or "",
        "reason": reason,
        "screenshots": [],
        "screenshots_captured": 0,
        "routes_captured": [],
        "desktop_routes": [],
        "mobile_routes": [],
        "issues": [{
            "title": "BROWSER_QA_UNAVAILABLE",
            "area": "reference_visual",
            "severity": "low",
            "source": "browser_reference_qa_v907",
            "route": "browser",
            "evidence": reason,
            "recommendation": "Instalar Playwright/Chromium o ejecutar Browser QA en un entorno con navegador disponible.",
        }],
        "note": "No se declara pixel-perfect ni equivalencia visual exacta sin capturas reales.",
    }
    comparison = build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
    _write_reference_gap_status(comparison)
    _write_outbox(comparison)
    _write_payload(output, payload, comparison)
    return payload


def run_browser_reference_qa(
    *,
    base_url: str,
    output: Path,
    desktop: bool,
    mobile: bool,
    admin_safe: bool,
    no_login_required: bool,
    timeout: int,
    write_json: bool = True,
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    env = detect_browser_qa_environment()
    if not env.get("can_capture"):
        return _unavailable_payload(output, str(env.get("reason") or env.get("browser_qa_status") or "BROWSER_QA_UNAVAILABLE"), env)

    routes = PUBLIC_ROUTES + CLIENT_ROUTES + ADMIN_SAFE_ROUTES
    if admin_safe or no_login_required:
        routes += ADMIN_PROTECTED_ROUTES
    routes = list(dict.fromkeys(routes))

    devices = []
    if desktop:
        devices.append(("desktop", {"width": 1440, "height": 900}))
    if mobile:
        devices.append(("mobile", {"width": 390, "height": 844}))
    if not devices:
        devices.append(("desktop", {"width": 1440, "height": 900}))

    captures: list[dict] = []
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                for device, viewport in devices:
                    device_dir = output / device
                    device_dir.mkdir(parents=True, exist_ok=True)
                    page = browser.new_page(viewport=viewport)
                    for route in routes:
                        safe_name = (route.strip("/") or "home").replace("/", "__").replace("-", "_")
                        shot = device_dir / f"{safe_name}.png"
                        item = {
                            "device": device,
                            "profile": f"{device}_{viewport['width']}x{viewport['height']}",
                            "route": route,
                            "url": base_url.rstrip("/") + route,
                            "screenshot": str(shot.relative_to(ROOT)),
                        }
                        try:
                            response = page.goto(item["url"], wait_until="networkidle", timeout=timeout)
                            scroll_width = page.evaluate("document.documentElement.scrollWidth")
                            inner_width = page.evaluate("window.innerWidth")
                            body_text = page.locator("body").inner_text(timeout=3000)[:1000]
                            item.update({
                                "status": response.status if response else None,
                                "overflow_x": bool(scroll_width and inner_width and scroll_width > inner_width + 2),
                                "scroll_width": scroll_width,
                                "inner_width": inner_width,
                                "body_text_sample": body_text,
                            })
                            page.screenshot(path=str(shot), full_page=True)
                        except Exception as exc:
                            item["error"] = f"{exc.__class__.__name__}: {str(exc)[:220]}"
                        captures.append(item)
                    page.close()
            finally:
                browser.close()
    except Exception as exc:
        return _unavailable_payload(output, f"Playwright instalado, pero navegador no disponible: {exc.__class__.__name__}: {str(exc)[:240]}", env)

    payload = {
        "ok": True,
        "version": VERSION,
        "generated_at_madrid": _now_label(),
        "browser_available": True,
        "playwright_available": True,
        "browsers_available": True,
        "browser_qa_status": "CAPTURED",
        "base_url": base_url,
        "screenshots": captures,
        "screenshots_captured": len([item for item in captures if item.get("screenshot") and not item.get("error")]),
        "routes_captured": sorted({item["route"] for item in captures if item.get("screenshot") and not item.get("error")}),
        "desktop_routes": [item["route"] for item in captures if item.get("device") == "desktop"],
        "mobile_routes": [item["route"] for item in captures if item.get("device") == "mobile"],
        "overflow_issues": [item for item in captures if item.get("overflow_x")],
        "note": "Capturas locales; no prueban produccion Render.",
    }
    comparison = build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
    _write_reference_gap_status(comparison)
    _write_outbox(comparison)
    if write_json:
        _write_payload(output, payload, comparison)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="V907 real browser screenshot/reference QA.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--output", default="reports/V907_browser_qa")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--admin-safe", action="store_true")
    parser.add_argument("--no-login-required", action="store_true")
    parser.add_argument("--timeout", type=int, default=15000)
    parser.add_argument("--timeout-ms", type=int)
    parser.add_argument("--write-json", action="store_true")
    args = parser.parse_args()
    payload = run_browser_reference_qa(
        base_url=args.base_url,
        output=ROOT / args.output,
        desktop=bool(args.desktop or not args.mobile),
        mobile=bool(args.mobile),
        admin_safe=bool(args.admin_safe),
        no_login_required=bool(args.no_login_required),
        timeout=int(args.timeout_ms or args.timeout),
        write_json=True,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
