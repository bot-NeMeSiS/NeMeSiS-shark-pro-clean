"""V899 optional browser visual QA.

Uses Playwright only when available. Missing browser support is reported as a
safe issue and never blocks release by itself.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


BROWSER_VISUAL_QA_VERSION = "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL"
MADRID_TZ = ZoneInfo("Europe/Madrid")

DEFAULT_ROUTES = [
    "/", "/cliente-login", "/registro", "/app", "/calendar", "/calendario", "/partidos",
    "/live", "/directo", "/picks", "/shark", "/profile", "/telegram", "/support",
    "/track-record", "/combis", "/mercados", "/favorites", "/admin-login",
    "/admin/autonomous-company-sentinel", "/admin/sentinel-issues", "/admin/sentinel-codex-outbox",
    "/admin/not-found-events", "/admin/telegram/command-center", "/admin/visual-worker",
    "/admin/sentinel-autopilot", "/admin/users", "/admin/memberships", "/admin/payments",
    "/admin/data-center", "/ruta-inventada", "/dashboard", "/admin-panel", "/directos",
    "/manifest.json", "/service-worker.js",
]


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def browser_output_dirs(root: str | Path) -> tuple[Path, Path]:
    base = Path(root)
    return (
        base / "reports" / "V899_screenshots",
        base / "data" / "runtime" / "autonomous_company_sentinel" / "screenshots" / "v899",
    )


def run_browser_visual_qa(
    root: str | Path,
    *,
    base_url: str = "http://127.0.0.1:5000",
    timeout_ms: int = 12000,
    routes: list[str] | None = None,
) -> dict[str, Any]:
    reports_dir, runtime_dir = browser_output_dirs(root)
    reports_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:
        payload = {
            "ok": True,
            "version": BROWSER_VISUAL_QA_VERSION,
            "generated_at_madrid": _now(),
            "browser_available": False,
            "reason": f"Playwright no disponible: {exc.__class__.__name__}",
            "screenshots": [],
            "issues": [{
                "title": "BROWSER_QA_UNAVAILABLE",
                "area": "reference_visual",
                "severity": "low",
                "source": "browser_visual_qa",
                "route": "browser",
                "evidence": f"Playwright no disponible: {exc.__class__.__name__}",
                "recommendation": "Ejecutar browser QA en un entorno con Playwright instalado.",
                "tags": ["browser_qa", "reference_gap"],
            }],
            "note": "No se declara equivalencia visual exacta sin capturas reales.",
        }
        (runtime_dir / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (reports_dir / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload

    captures: list[dict[str, Any]] = []
    viewports = {
        "desktop_1440x900": {"width": 1440, "height": 900},
        "mobile_390x844": {"width": 390, "height": 844},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for profile, viewport in viewports.items():
                page = browser.new_page(viewport=viewport)
                for route in routes or DEFAULT_ROUTES:
                    url = base_url.rstrip("/") + route
                    safe = (route.strip("/") or "home").replace("/", "_").replace("-", "_")
                    path = reports_dir / f"{profile}_{safe}.png"
                    runtime_path = runtime_dir / f"{profile}_{safe}.png"
                    item: dict[str, Any] = {"profile": profile, "route": route, "url": url, "screenshot": str(path)}
                    try:
                        response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                        scroll_width = page.evaluate("document.documentElement.scrollWidth")
                        inner_width = page.evaluate("window.innerWidth")
                        item.update({
                            "status": response.status if response else None,
                            "overflow_x": bool(scroll_width and inner_width and scroll_width > inner_width + 2),
                            "scroll_width": scroll_width,
                            "inner_width": inner_width,
                        })
                        page.screenshot(path=str(path), full_page=True)
                        page.screenshot(path=str(runtime_path), full_page=True)
                    except Exception as exc:
                        item["error"] = f"{exc.__class__.__name__}: {str(exc)[:220]}"
                    captures.append(item)
                page.close()
        finally:
            browser.close()
    payload = {
        "ok": True,
        "version": BROWSER_VISUAL_QA_VERSION,
        "generated_at_madrid": _now(),
        "browser_available": True,
        "screenshots": captures,
        "overflow_issues": [item for item in captures if item.get("overflow_x")],
        "note": "Capturas locales; no prueban produccion Render.",
    }
    (runtime_dir / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (reports_dir / "browser_reference_qa_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
