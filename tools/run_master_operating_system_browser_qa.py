"""Read-only Browser QA for Company Board and Developer Center."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
MADRID = ZoneInfo("Europe/Madrid")
PROFILES = {
    "desktop_1366x768": {"width": 1366, "height": 768, "is_mobile": False},
    "tablet_834x1194": {"width": 834, "height": 1194, "is_mobile": False},
    "mobile_390x844": {"width": 390, "height": 844, "is_mobile": True},
}
SCENARIOS = {
    "company_board": {
        "route": "/admin/company-board",
        "root": "[data-company-board='NEMESIS-COMPANY-DEVELOPER-OS-V1']",
    },
    "developer_center": {
        "route": "/admin/developer-center",
        "root": "[data-developer-center='NEMESIS-COMPANY-DEVELOPER-OS-V1']",
    },
}
BLOCKED_PROVIDER_HOSTS = (
    "api-sports",
    "api-football",
    "thesportsdb",
    "the-odds-api",
    "api.telegram",
    "api.openai",
    "stripe.com",
)


def inspect_page(page, root_selector: str) -> dict:
    return page.evaluate(
        """rootSelector => {
          const bodyText = (document.body.innerText || "").replace(/\\s+/g, " ").trim();
          const actionNodes = Array.from(document.querySelectorAll(
            "button, input, select, .v933-action, [role='button']"
          )).filter(node => {
            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            return style.visibility !== "hidden" && style.display !== "none"
              && rect.width > 0 && rect.height > 0;
          });
          const smallTargets = actionNodes.filter(node => {
            const rect = node.getBoundingClientRect();
            return rect.width < 32 || rect.height < 32;
          }).map(node => {
            const rect = node.getBoundingClientRect();
            return {
              text: (node.innerText || node.getAttribute("aria-label") || "").trim().slice(0, 80),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            };
          });
          const textLineCount = node => {
            const range = document.createRange();
            range.selectNodeContents(node);
            return Array.from(range.getClientRects()).filter(rect => rect.width && rect.height).length;
          };
          const fragmentedLabels = Array.from(document.querySelectorAll(".v933-truth-list > div > span"))
            .filter(node => textLineCount(node) > 2)
            .map(node => (node.textContent || "").trim().slice(0, 80));
          const fragmentedChips = Array.from(document.querySelectorAll(".v933-status-chip"))
            .filter(node => textLineCount(node) > 1)
            .map(node => (node.textContent || "").trim().slice(0, 80));
          const fragmentedKpiValues = Array.from(document.querySelectorAll(".v933-kpi > div > strong"))
            .filter(node => textLineCount(node) > 1)
            .map(node => (node.textContent || "").trim().slice(0, 80));
          const fragmentedTableKeys = Array.from(document.querySelectorAll(".v933-data-table td:first-child strong"))
            .filter(node => textLineCount(node) > 2)
            .map(node => (node.textContent || "").trim().slice(0, 80));
          const clippedText = Array.from(document.querySelectorAll(
            "h1, h2, h3, p, strong, span, small, a, button, th, td"
          )).filter(node => {
            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            if (!rect.width || !rect.height || style.visibility === "hidden") return false;
            const clipped = node.scrollWidth > node.clientWidth + 1
              || node.scrollHeight > node.clientHeight + 1;
            return clipped && style.overflow === "hidden" && style.textOverflow !== "ellipsis";
          }).map(node => (node.textContent || "").trim().slice(0, 100));
          return {
            root_count: document.querySelectorAll(rootSelector).length,
            h1_count: document.querySelectorAll("main h1").length,
            admin_shell_count: document.querySelectorAll("[data-v933-shell='admin']").length,
            client_shell_count: document.querySelectorAll("[data-v933-shell='client']").length,
            client_sidebar_count: document.querySelectorAll(".ns-client-sidebar").length,
            client_bottom_nav_count: document.querySelectorAll(".bottom-nav").length,
            next_action_count: document.querySelectorAll(".v933-next-action").length,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            unsafe_literal_visible: /\\b(?:None|null|undefined)\\b/i.test(bodyText),
            mojibake_visible: /(?:Ã.|Â.|â€|�)/.test(bodyText),
            clipped_text: clippedText,
            fragmented_labels: fragmentedLabels,
            fragmented_chips: fragmentedChips,
            fragmented_kpi_values: fragmentedKpiValues,
            fragmented_table_keys: fragmentedTableKeys,
            small_targets: smallTargets,
            visible_text_length: bodyText.length,
            cls: Number(window.__nemesisQaCls || 0),
          };
        }""",
        root_selector,
    )


def run(base_url: str, output: Path, login: str, password: str) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    base_host = urlparse(base_url).netloc.lower()
    results: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for profile_name, profile in PROFILES.items():
                context = browser.new_context(
                    viewport={"width": profile["width"], "height": profile["height"]},
                    device_scale_factor=1,
                    is_mobile=profile["is_mobile"],
                    has_touch=profile["is_mobile"],
                    locale="es-ES",
                    timezone_id="Europe/Madrid",
                )
                context.add_init_script(
                    """window.__nemesisQaCls = 0;
                    new PerformanceObserver(list => {
                      for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) window.__nemesisQaCls += entry.value;
                      }
                    }).observe({type: "layout-shift", buffered: true});"""
                )
                login_page = context.new_page()
                login_page.goto(
                    urljoin(base_url, "/admin-login?next=/admin/company-board"),
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                login_page.locator("#admin-login-user").fill(login)
                login_page.locator("#admin-login-password").fill(password)
                login_page.locator("button[type='submit']").click()
                login_page.wait_for_load_state("domcontentloaded")
                authenticated = "/admin-login" not in login_page.url
                login_page.close()

                for scenario, config in SCENARIOS.items():
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    server_errors: list[dict] = []
                    external_requests: list[str] = []
                    provider_requests: list[str] = []

                    page.on(
                        "console",
                        lambda message, bucket=console_errors: (
                            bucket.append(message.text) if message.type == "error" else None
                        ),
                    )
                    page.on("pageerror", lambda error, bucket=page_errors: bucket.append(str(error)))
                    page.on(
                        "response",
                        lambda response, bucket=server_errors: (
                            bucket.append({"status": response.status, "url": response.url})
                            if response.status >= 500
                            else None
                        ),
                    )

                    def record_request(request) -> None:
                        host = urlparse(request.url).netloc.lower()
                        if host and host != base_host:
                            external_requests.append(request.url)
                        if any(token in host for token in BLOCKED_PROVIDER_HOSTS):
                            provider_requests.append(request.url)

                    page.on("request", record_request)
                    url = urljoin(base_url, config["route"])
                    response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    page.wait_for_timeout(800)
                    metrics = inspect_page(page, config["root"])
                    screenshot = output / f"{profile_name}__{scenario}.png"
                    page.screenshot(path=str(screenshot), full_page=True)

                    failures: list[str] = []
                    if not authenticated:
                        failures.append("admin_login_failed")
                    if response is None or response.status != 200:
                        failures.append(f"http_status={response.status if response else 'none'}")
                    if metrics["root_count"] != 1:
                        failures.append("page_root_not_unique")
                    if metrics["h1_count"] != 1:
                        failures.append("primary_heading_not_unique")
                    if metrics["admin_shell_count"] != 1:
                        failures.append("admin_shell_not_unique")
                    if metrics["client_shell_count"] or metrics["client_sidebar_count"]:
                        failures.append("client_navigation_mixed_into_admin")
                    if metrics["client_bottom_nav_count"]:
                        failures.append("client_bottom_navigation_mixed_into_admin")
                    if metrics["next_action_count"] != 1:
                        failures.append("next_action_not_unique")
                    if metrics["horizontal_overflow"]:
                        failures.append("horizontal_overflow")
                    if metrics["unsafe_literal_visible"]:
                        failures.append("unsafe_literal_visible")
                    if metrics["mojibake_visible"]:
                        failures.append("mojibake_visible")
                    if metrics["clipped_text"]:
                        failures.append("clipped_text")
                    if metrics["fragmented_labels"]:
                        failures.append("fragmented_truth_label")
                    if metrics["fragmented_chips"]:
                        failures.append("fragmented_status_chip")
                    if metrics["fragmented_kpi_values"]:
                        failures.append("fragmented_kpi_value")
                    if metrics["fragmented_table_keys"]:
                        failures.append("fragmented_table_key")
                    if metrics["cls"] > 0.05:
                        failures.append("layout_shift_over_budget")
                    if profile["is_mobile"] and metrics["small_targets"]:
                        failures.append("small_mobile_target")
                    if console_errors:
                        failures.append("console_errors")
                    if page_errors:
                        failures.append("page_errors")
                    if server_errors:
                        failures.append("server_5xx")
                    if provider_requests:
                        failures.append("provider_call_during_render")

                    results.append(
                        {
                            "profile": profile_name,
                            "scenario": scenario,
                            "route": config["route"],
                            "http_status": response.status if response else None,
                            "screenshot": screenshot.relative_to(ROOT).as_posix(),
                            "metrics": metrics,
                            "console_errors": console_errors,
                            "page_errors": page_errors,
                            "server_errors": server_errors,
                            "external_requests": sorted(set(external_requests)),
                            "provider_requests": sorted(set(provider_requests)),
                            "failures": failures,
                            "status": "FAIL" if failures else "PASS",
                        }
                    )
                    page.close()
                context.close()
        finally:
            browser.close()

    failures = [
        {
            "profile": result["profile"],
            "scenario": result["scenario"],
            "failures": result["failures"],
        }
        for result in results
        if result["failures"]
    ]
    payload = {
        "contract": "NEMESIS-COMPANY-DEVELOPER-OS-BROWSER-QA-V1",
        "generated_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
        "base_url": base_url,
        "read_only": True,
        "production_modified": False,
        "profiles": list(PROFILES),
        "scenarios": list(SCENARIOS),
        "screenshots_captured": len(results),
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "results": results,
    }
    (output / "browser_qa_result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5074")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "browser_qa" / "MASTER_OPERATING_SYSTEM",
    )
    args = parser.parse_args()
    login = os.getenv("QA_ADMIN_LOGIN", "").strip()
    password = os.getenv("QA_ADMIN_PASSWORD", "")
    if not login or not password:
        raise SystemExit("QA admin credentials are required through environment variables.")
    payload = run(args.base_url, args.output.resolve(), login, password)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "screenshots": payload["screenshots_captured"],
                "profiles": payload["profiles"],
                "scenarios": payload["scenarios"],
                "failures": payload["failures"],
                "production_modified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if payload["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
