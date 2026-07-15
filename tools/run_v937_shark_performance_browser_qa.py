from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ROUTES = (("home", "/"), ("calendar", "/calendar"), ("live", "/live"), ("picks", "/picks"), ("shark", "/shark"))
PROFILES = (("desktop_1440x900", 1440, 900), ("mobile_390x844", 390, 844))


def run(base_url: str, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    captures: list[dict] = []
    browser_errors: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for profile, width, height in PROFILES:
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                page_errors: list[str] = []
                console_errors: list[str] = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

                for name, route in ROUTES:
                    response = page.goto(f"{base_url.rstrip('/')}{route}", wait_until="load", timeout=15_000)
                    state = page.evaluate(
                        """() => ({
                            path: window.location.pathname,
                            h1: (document.querySelector('h1')?.textContent || '').trim(),
                            overflow_x: document.documentElement.scrollWidth > window.innerWidth + 2,
                            internal_error_visible: /Internal Server Error|Traceback|FileNotFoundError/i.test(document.body?.innerText || ''),
                            shark_page_marker: window.location.pathname === '/shark'
                                && (document.querySelector('h1')?.textContent || '').trim() === 'SHARK'
                        })"""
                    )
                    screenshot = output / f"{profile}_{name}.png"
                    page.screenshot(path=str(screenshot), full_page=False)
                    captures.append(
                        {
                            "profile": profile,
                            "route": route,
                            "status": response.status if response else None,
                            "server_timing": response.headers.get("server-timing") if response else None,
                            "shark_cache": response.headers.get("x-nemesis-shark-cache") if response else None,
                            "state": state,
                            "screenshot": screenshot.relative_to(ROOT).as_posix(),
                        }
                    )

                if page_errors or console_errors:
                    browser_errors.append(
                        {"profile": profile, "page_errors": page_errors, "console_errors": console_errors}
                    )
                context.close()
        finally:
            browser.close()

    failures = [
        item
        for item in captures
        if item["status"] != 200
        or item["state"]["overflow_x"]
        or item["state"]["internal_error_visible"]
        or (item["route"] == "/shark" and not item["state"]["shark_page_marker"])
    ]
    payload = {
        "ok": not failures and not browser_errors,
        "base_url": base_url,
        "captures": len(captures),
        "failures": failures,
        "browser_errors": browser_errors,
        "results": captures,
    }
    (output / "qa.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Reduced Browser QA for the V937 SHARK performance hotfix.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5097")
    parser.add_argument("--output", default="reports/browser_qa_v937_shark_hotfix")
    args = parser.parse_args()
    payload = run(args.base_url, ROOT / args.output)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
