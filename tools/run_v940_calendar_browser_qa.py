#!/usr/bin/env python3
"""Focused, read-only Playwright QA for the V940 Calendar experience."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
MADRID = ZoneInfo("Europe/Madrid")
PROFILES = {
    "desktop_1366x768": {"width": 1366, "height": 768, "is_mobile": False},
    "mobile_390x844": {"width": 390, "height": 844, "is_mobile": True},
}
SCENARIOS = {
    "collection": "/calendar?lane=week",
    "reversible_empty_search": "/calendar?lane=week&q=__v940_no_match__",
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


def madrid_now() -> str:
    return datetime.now(MADRID).replace(microsecond=0).isoformat()


def inspect_page(page, base_url: str) -> dict:
    base_host = urlparse(base_url).netloc
    return page.evaluate(
        """({baseHost}) => {
          const root = document.querySelector('[data-v940-calendar-experience]');
          const visibleText = (root ? root.innerText : document.body.innerText).replace(/\\s+/g, ' ').trim();
          const cardCount = document.querySelectorAll('[data-v934-match-card="true"]').length;
          const canonicalCardCount = document.querySelectorAll('[data-v939-match-card-spec="canonical-v1"]').length;
          const context = document.querySelector('[data-v940-calendar-context]');
          const actionNodes = Array.from(document.querySelectorAll(
            '[data-v940-calendar-command] button, [data-v940-calendar-command] a, [data-v940-calendar-command] input, [data-v940-calendar-command] select'
          ));
          const smallTargets = actionNodes.filter((node) => {
            const rect = node.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && (rect.width < 32 || rect.height < 32);
          }).map((node) => ({
            tag: node.tagName,
            text: (node.innerText || node.getAttribute('aria-label') || node.name || '').trim(),
            width: Math.round(node.getBoundingClientRect().width),
            height: Math.round(node.getBoundingClientRect().height),
          }));
          return {
            base_host: baseHost,
            title: document.title,
            root_count: document.querySelectorAll('[data-v940-calendar-experience]').length,
            command_count: document.querySelectorAll('[data-v940-calendar-command]').length,
            context_count: document.querySelectorAll('[data-v940-calendar-context]').length,
            index_count: document.querySelectorAll('[data-v940-calendar-index]').length,
            collection_count: document.querySelectorAll('[data-v940-calendar-collection]').length,
            client_sidebar_count: document.querySelectorAll('.ns-client-sidebar').length,
            mobile_bottom_nav_count: document.querySelectorAll('.bottom-nav, .v933-mobile-bottom-nav').length,
            admin_nav_count: document.querySelectorAll('.ns-admin-sidebar, [data-admin-sidebar]').length,
            card_count: cardCount,
            canonical_card_count: canonicalCardCount,
            horizontal_overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
            document_width: document.documentElement.scrollWidth,
            viewport_width: window.innerWidth,
            context_position: context ? getComputedStyle(context).position : '',
            active_filter_count: Number(
              document.querySelector('[data-v940-calendar-filters-active]')?.getAttribute('data-v940-calendar-filters-active') || 0
            ),
            has_reset_action: Boolean(document.querySelector('.v940-calendar-reset')),
            unsafe_literal_visible: /\\b(?:None|null|undefined)\\b/.test(visibleText),
            small_command_targets: smallTargets,
            search_present: Boolean(document.querySelector('[data-v940-calendar-search]')),
            visible_text_length: visibleText.length,
          };
        }""",
        {"baseHost": base_host},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5094")
    parser.add_argument(
        "--output",
        default=str(ROOT / "browser_qa" / "V940_CALENDAR"),
    )
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for profile_name, profile in PROFILES.items():
            context = browser.new_context(
                viewport={"width": profile["width"], "height": profile["height"]},
                device_scale_factor=1,
                is_mobile=profile["is_mobile"],
                has_touch=profile["is_mobile"],
                locale="es-ES",
                timezone_id="Europe/Madrid",
            )
            for scenario_name, route in SCENARIOS.items():
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

                def record_response(response) -> None:
                    if response.status >= 500:
                        server_errors.append({"status": response.status, "url": response.url})

                def record_request(request) -> None:
                    host = urlparse(request.url).netloc.lower()
                    if host and host != urlparse(args.base_url).netloc.lower():
                        external_requests.append(request.url)
                    if any(token in host for token in BLOCKED_PROVIDER_HOSTS):
                        provider_requests.append(request.url)

                page.on("response", record_response)
                page.on("request", record_request)
                url = urljoin(args.base_url.rstrip("/") + "/", route.lstrip("/"))
                response = page.goto(url, wait_until="networkidle", timeout=30_000)
                page.wait_for_timeout(350)
                anchor_navigation_ok = None
                back_restore_ok = None
                restore_before = 0
                restore_after = 0
                if scenario_name == "collection":
                    index_links = page.locator("[data-v940-scroll-link]")
                    if index_links.count():
                        index_links.first.click()
                        page.wait_for_timeout(150)
                        anchor_navigation_ok = page.evaluate(
                            "window.location.hash.startsWith('#v940-day-')"
                        )
                    card_links = page.locator("[data-v934-match-card] a")
                    if card_links.count() >= 6:
                        target = card_links.nth(5)
                        target.scroll_into_view_if_needed()
                        page.wait_for_timeout(150)
                        restore_before = int(page.evaluate("window.scrollY"))
                        target.evaluate(
                            """node => {
                              window.addEventListener('click', event => event.preventDefault(), {once: true, capture: true});
                              node.click();
                            }"""
                        )
                        page.goto(urljoin(args.base_url.rstrip("/") + "/", "support"), wait_until="networkidle")
                        page.go_back(wait_until="networkidle")
                        page.wait_for_timeout(650)
                        restore_after = int(page.evaluate("window.scrollY"))
                        back_restore_ok = restore_before > 0 and abs(restore_after - restore_before) <= 160
                    page.evaluate("window.scrollTo(0, 0)")
                    page.keyboard.press("/")
                    search_focused = page.evaluate(
                        "document.activeElement === document.querySelector('[data-v940-calendar-search]')"
                    )
                else:
                    search_focused = False
                page.evaluate(
                    """() => {
                      if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
                      window.scrollTo(0, 0);
                    }"""
                )
                page.wait_for_timeout(120)

                metrics = inspect_page(page, args.base_url)
                screenshot = output / f"{profile_name}__{scenario_name}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                failures: list[str] = []

                if response is None or response.status != 200:
                    failures.append(f"http_status={response.status if response else 'none'}")
                if metrics["root_count"] != 1:
                    failures.append("calendar_root_not_unique")
                if metrics["command_count"] != 1:
                    failures.append("command_surface_not_unique")
                if metrics["context_count"] != 1:
                    failures.append("calendar_context_not_unique")
                if metrics["collection_count"] != 1:
                    failures.append("calendar_collection_not_unique")
                if metrics["client_sidebar_count"] > 1 or metrics["mobile_bottom_nav_count"] > 1:
                    failures.append("client_navigation_duplicated")
                if metrics["admin_nav_count"]:
                    failures.append("admin_navigation_mixed_into_client")
                if metrics["horizontal_overflow"]:
                    failures.append("horizontal_overflow")
                if metrics["context_position"] != "sticky":
                    failures.append("calendar_context_not_sticky")
                if metrics["card_count"] != metrics["canonical_card_count"]:
                    failures.append("non_canonical_match_card")
                if metrics["unsafe_literal_visible"]:
                    failures.append("unsafe_literal_visible")
                if console_errors:
                    failures.append("console_errors")
                if page_errors:
                    failures.append("page_errors")
                if server_errors:
                    failures.append("server_5xx")
                if provider_requests:
                    failures.append("provider_call_during_render")
                if scenario_name == "collection" and not search_focused:
                    failures.append("search_shortcut_failed")
                if metrics["index_count"] and anchor_navigation_ok is not True:
                    failures.append("day_index_navigation_failed")
                if metrics["card_count"] >= 6 and back_restore_ok is not True:
                    failures.append("match_return_context_not_restored")
                if scenario_name == "reversible_empty_search":
                    if metrics["active_filter_count"] < 1:
                        failures.append("active_filter_not_visible")
                    if not metrics["has_reset_action"]:
                        failures.append("reset_action_missing")
                if profile["is_mobile"] and metrics["small_command_targets"]:
                    failures.append("small_mobile_command_target")

                results.append(
                    {
                        "profile": profile_name,
                        "scenario": scenario_name,
                        "route": route,
                        "url": url,
                        "http_status": response.status if response else None,
                        "screenshot": screenshot.relative_to(ROOT).as_posix(),
                        "metrics": metrics,
                        "console_errors": console_errors,
                        "page_errors": page_errors,
                        "server_errors": server_errors,
                        "external_request_count": len(set(external_requests)),
                        "provider_requests": sorted(set(provider_requests)),
                        "search_shortcut_focused": search_focused,
                        "anchor_navigation_ok": anchor_navigation_ok,
                        "back_restore_ok": back_restore_ok,
                        "restore_scroll_before": restore_before,
                        "restore_scroll_after": restore_after,
                        "failures": failures,
                        "status": "PASS" if not failures else "FAIL",
                    }
                )
                page.close()
            context.close()
        browser.close()

    failures = [
        {"profile": item["profile"], "scenario": item["scenario"], "failures": item["failures"]}
        for item in results
        if item["failures"]
    ]
    payload = {
        "version": "V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL",
        "generated_at_madrid": madrid_now(),
        "base_url": args.base_url,
        "read_only": True,
        "production_modified": False,
        "pixel_perfect_claim": False,
        "screenshots_captured": len(results),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "results": results,
    }
    result_path = output / "browser_qa_result.json"
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
