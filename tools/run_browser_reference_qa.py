from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "browser_qa"

ROUTES = [
    "/",
    "/cliente-login",
    "/app",
    "/calendar",
    "/live",
    "/picks",
    "/admin-login",
    "/admin/autonomous-company-sentinel",
]


def write_report(payload: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "browser_reference_qa_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional V897 browser reference QA.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--timeout-ms", type=int, default=12000)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        payload = {
            "ok": True,
            "browser_available": False,
            "reason": f"Playwright no disponible: {exc.__class__.__name__}",
            "screenshots": [],
            "note": "No se declara pixel-perfect sin capturas reales.",
        }
        write_report(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    captures: list[dict] = []
    viewports = {
        "desktop": {"width": 1440, "height": 1000},
        "mobile": {"width": 390, "height": 844},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for profile, viewport in viewports.items():
                page = browser.new_page(viewport=viewport)
                for route in ROUTES:
                    url = args.base_url.rstrip("/") + route
                    safe_name = (route.strip("/") or "home").replace("/", "_").replace("-", "_")
                    path = OUT / f"{profile}_{safe_name}.png"
                    record = {"profile": profile, "route": route, "url": url, "screenshot": str(path)}
                    try:
                        response = page.goto(url, wait_until="networkidle", timeout=args.timeout_ms)
                        width = page.evaluate("document.documentElement.scrollWidth")
                        inner = page.evaluate("window.innerWidth")
                        record.update({
                            "status": response.status if response else None,
                            "overflow_x": bool(width and inner and width > inner + 2),
                            "scroll_width": width,
                            "inner_width": inner,
                        })
                        page.screenshot(path=str(path), full_page=True)
                    except Exception as exc:
                        record.update({"error": f"{exc.__class__.__name__}: {str(exc)[:220]}"})
                    captures.append(record)
                page.close()
        finally:
            browser.close()

    payload = {
        "ok": True,
        "browser_available": True,
        "screenshots": captures,
        "overflow_issues": [item for item in captures if item.get("overflow_x")],
        "note": "Capturas locales opcionales; no prueban producción Render.",
    }
    write_report(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

