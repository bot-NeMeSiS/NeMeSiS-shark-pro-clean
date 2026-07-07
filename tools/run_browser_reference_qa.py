from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.browser_reference_comparison_engine import build_browser_reference_comparison


PUBLIC_ROUTES = ["/", "/cliente-login", "/registro"]
CLIENT_ROUTES = ["/app", "/calendar", "/live", "/picks", "/shark", "/telegram", "/profile", "/support"]
ADMIN_SAFE_ROUTES = ["/admin-login"]
ADMIN_PROTECTED_ROUTES = [
    "/admin/dashboard",
    "/admin/autonomous-company-sentinel",
    "/admin/sentinel-issues",
    "/admin/sentinel-codex-outbox",
    "/admin/not-found-events",
]


def _now_label() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat()


def _unavailable_payload(output: Path, reason: str) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "version": "V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL",
        "generated_at_madrid": _now_label(),
        "browser_available": False,
        "reason": reason,
        "screenshots": [],
        "screenshots_captured": 0,
        "desktop_routes": [],
        "mobile_routes": [],
        "issues": [{
            "title": "BROWSER_QA_UNAVAILABLE",
            "area": "reference_visual",
            "severity": "low",
            "source": "browser_reference_qa_v906",
            "route": "browser",
            "evidence": reason,
            "recommendation": "Instalar Playwright/Chromium o ejecutar Browser QA en un entorno con navegador disponible.",
        }],
        "note": "No se declara pixel-perfect ni equivalencia visual exacta sin capturas reales.",
    }
    (output / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    routes = PUBLIC_ROUTES + CLIENT_ROUTES + ADMIN_SAFE_ROUTES
    if admin_safe or no_login_required:
        routes += ADMIN_PROTECTED_ROUTES
    routes = list(dict.fromkeys(routes))
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        payload = _unavailable_payload(output, f"Playwright no disponible: {exc.__class__.__name__}")
        build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
        return payload

    devices = []
    if desktop:
        devices.append(("desktop", {"width": 1440, "height": 900}))
    if mobile:
        devices.append(("mobile", {"width": 390, "height": 844}))
    if not devices:
        devices.append(("desktop", {"width": 1440, "height": 900}))

    captures: list[dict] = []
    try:
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
                            "screenshot": str(shot),
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
        payload = _unavailable_payload(output, f"Playwright instalado, pero navegador no disponible: {exc.__class__.__name__}")
        build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
        return payload

    payload = {
        "ok": True,
        "version": "V906_REAL_BROWSER_QA_SCREENSHOT_REFERENCE_COMPARISON_FINAL",
        "generated_at_madrid": _now_label(),
        "browser_available": True,
        "base_url": base_url,
        "screenshots": captures,
        "screenshots_captured": len([item for item in captures if item.get("screenshot") and not item.get("error")]),
        "desktop_routes": [item["route"] for item in captures if item.get("device") == "desktop"],
        "mobile_routes": [item["route"] for item in captures if item.get("device") == "mobile"],
        "overflow_issues": [item for item in captures if item.get("overflow_x")],
        "note": "Capturas locales; no prueban producción Render.",
    }
    (output / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    comparison = build_browser_reference_comparison(ROOT, qa_payload=payload, output_dir=output)
    payload["comparison_summary"] = {
        "reference_comparisons": comparison.get("reference_comparisons"),
        "visual_gaps_resolved": comparison.get("visual_gaps_resolved"),
        "visual_gaps_pending": comparison.get("visual_gaps_pending"),
    }
    (output / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="V906 real browser screenshot/reference QA.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--output", default="reports/V906_browser_qa")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--admin-safe", action="store_true")
    parser.add_argument("--no-login-required", action="store_true")
    parser.add_argument("--timeout", type=int, default=15000)
    parser.add_argument("--timeout-ms", type=int)
    args = parser.parse_args()
    payload = run_browser_reference_qa(
        base_url=args.base_url,
        output=ROOT / args.output,
        desktop=bool(args.desktop or not args.mobile),
        mobile=bool(args.mobile),
        admin_safe=bool(args.admin_safe),
        no_login_required=bool(args.no_login_required),
        timeout=int(args.timeout_ms or args.timeout),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
