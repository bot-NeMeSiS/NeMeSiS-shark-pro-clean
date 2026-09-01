"""Read-only browser gate for the deployed NeMeSiS release."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PUBLIC_NAV = ("/", "/calendar", "/live", "/picks", "/track-record", "/shark")
MOBILE_NAV = ("/", "/calendar", "/live", "/picks", "/cliente-login")
CRITICAL_PAGES = ("/", "/calendar", "/live", "/picks", "/shark", "/track-record")
ENTITY_PATH_PREFIXES = ("/match/", "/team/", "/competition/", "/player/")
MOJIBAKE = re.compile(r"(?:Actualizaci\?n|Ã.|Â.|â€|�)")
TECHNICAL_COPY = re.compile(
    r"\b(?:traceback|stack trace|raw log|debug mode|internal confidence|engine contract|payload)\b",
    re.IGNORECASE,
)


def _request_json(base_url: str, path: str) -> tuple[dict[str, Any], int]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NeMeSiS-Production-Quality-Sentinel/1.0", "Cache-Control": "no-cache"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
    except Exception:
        return {}, 0
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}
    return payload if isinstance(payload, dict) else {}, status


def _sports_truth(payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    live = [item for item in payload.get("live") or [] if isinstance(item, dict)]
    terminal = {"FT", "FINISHED", "CANCELLED", "POSTPONED", "ABANDONED"}
    false_live = [
        item
        for item in live
        if str(item.get("status") or "").upper() in terminal
        or item.get("is_live") is not True
        or item.get("is_stale") is True
    ]
    counts_match = int((payload.get("counts") or {}).get("live") or 0) == len(live)
    passed = payload.get("no_external_calls") is True and not false_live and counts_match
    return passed, {
        "live": len(live),
        "false_live": len(false_live),
        "live_counter_consistent": counts_match,
        "no_external_calls": payload.get("no_external_calls") is True,
    }


def _visual_asset_contract(resources: list[str]) -> tuple[bool, dict[str, Any]]:
    brand_shark = any("nemesis-shark-brand.svg" in value for value in resources)
    atmospheric_shark = any("nemesis-shark-atmosphere.svg" in value for value in resources)
    legacy_shark = any("shark-logo.svg" in value for value in resources)
    return brand_shark and atmospheric_shark and not legacy_shark, {
        "brand_shark_loaded": brand_shark,
        "atmospheric_shark_loaded": atmospheric_shark,
        "legacy_shark_loaded": legacy_shark,
    }

def build_post_deploy_result(
    *,
    expected_sha: str,
    actual_sha: str,
    checks: dict[str, str],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    normalized = {key: str(value or "NOT_RUN").upper() for key, value in checks.items()}
    failed = [key for key, value in normalized.items() if value == "FAIL"]
    missing = [key for key, value in normalized.items() if value not in {"PASS", "FAIL"}]
    if failed:
        result = "REGRESSION_DETECTED"
    elif missing:
        result = "BLOCKED"
    else:
        result = "PRODUCTION_CERTIFIED"
    return {
        "result": result,
        "expected_sha": expected_sha,
        "actual_sha": actual_sha,
        "checks": normalized,
        "failed_checks": failed,
        "missing_checks": missing,
        "rollback_recommended": bool(failed),
        "evidence": evidence,
        "read_only": True,
        "production_mutations": 0,
        "telegram_sends": 0,
        "stripe_actions": 0,
        "new_external_service_cost": 0,
    }


def _click_journey(page: Any, base_url: str, zone: str, paths: tuple[str, ...]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in paths:
        page.goto(base_url, wait_until="domcontentloaded", timeout=30_000)
        locator = page.locator(f'[data-nav-zone="{zone}"] a[href="{path}"]').first
        found = locator.count() == 1 and locator.is_visible()
        final_path = ""
        error = ""
        if found:
            try:
                locator.click(timeout=10_000)
                page.wait_for_load_state("domcontentloaded", timeout=30_000)
                final_path = urllib.parse.urlparse(page.url).path
            except Exception as exc:
                error = type(exc).__name__
        results.append({
            "href": path,
            "found": found,
            "final_path": final_path,
            "pass": found and final_path == path and not error,
            "error": error,
        })
    return results


def _page_evidence(page: Any, base_url: str, path: str) -> dict[str, Any]:
    started = time.perf_counter()
    response = page.goto(
        urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
        wait_until="networkidle",
        timeout=45_000,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    metrics = page.evaluate(
        """() => ({
          overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
          brokenImages: [...document.images].filter((img) => img.complete && img.naturalWidth === 0).map((img) => img.currentSrc || img.src),
          text: document.body ? document.body.innerText : '',
          shell: Boolean(document.querySelector('[data-v933-surface]')),
          cssVersioned: [...document.querySelectorAll('link[rel="stylesheet"]')].some((link) => /app\\.css\\?v=/.test(link.href)),
          resources: performance.getEntriesByType('resource').map((entry) => entry.name),
          temporalCards: document.querySelectorAll('[data-match-temporal-context]').length,
          relevantMatchCards: document.querySelectorAll('[data-v934-match-card], [data-v934-pick-card]').length,
          missingTemporalCards: [...document.querySelectorAll('[data-v934-match-card], [data-v934-pick-card]')]
            .filter((card) => !card.querySelector('[data-match-temporal-context]')).length,
          temporalLabels: [...document.querySelectorAll('[data-match-temporal-context]')]
            .map((node) => (node.textContent || '').trim()).filter(Boolean).slice(0, 30),
          temporalValues: [...document.querySelectorAll('[data-match-temporal-context]')].map((node) => {
            const owner = node.closest('[data-match-id], [data-v934-match-id]');
            return {
              matchId: owner ? (owner.getAttribute('data-match-id') || owner.getAttribute('data-v934-match-id') || '') : '',
              datetime: node.getAttribute('datetime') || '',
              label: (node.textContent || '').trim(),
            };
          }).filter((item) => item.matchId),
        })"""
    )
    text = str(metrics.pop("text", ""))
    metrics.update({
        "path": path,
        "http": response.status if response else 0,
        "elapsed_ms": elapsed_ms,
        "mojibake": sorted(set(MOJIBAKE.findall(text)))[:20],
        "technical_copy": sorted(set(TECHNICAL_COPY.findall(text)))[:20],
    })
    return metrics

def _discover_entity_paths(page: Any, base_url: str) -> tuple[str, ...]:
    """Follow at most one real link per sports entity without provider calls."""
    discovered: list[str] = []
    pending = ["/", "/calendar", "/picks", "/shark"]
    visited: set[str] = set()
    while pending and len(discovered) < len(ENTITY_PATH_PREFIXES):
        source_path = pending.pop(0)
        if source_path in visited:
            continue
        visited.add(source_path)
        page.goto(
            urllib.parse.urljoin(base_url.rstrip("/") + "/", source_path.lstrip("/")),
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        hrefs = page.locator("a[href]").evaluate_all(
            "nodes => nodes.map((node) => node.getAttribute('href') || '')"
        )
        for prefix in ENTITY_PATH_PREFIXES:
            if any(value.startswith(prefix) for value in discovered):
                continue
            match = next((value for value in hrefs if value.startswith(prefix)), "")
            if match:
                discovered.append(match)
                pending.append(match)
    return tuple(discovered)
def run_gate(
    base_url: str,
    expected_sha: str,
    output_dir: Path,
    browser_executable: str = "",
) -> dict[str, Any]:
    runtime, runtime_http = _request_json(base_url, "/api/runtime-version")
    health, health_http = _request_json(base_url, "/api/health")
    sports, sports_http = _request_json(base_url, "/api/realtime/sports")
    sports_pass, sports_evidence = _sports_truth(sports)
    output_dir.mkdir(parents=True, exist_ok=True)

    console_errors: list[str] = []
    page_errors: list[str] = []
    playwright_module = __import__("playwright.sync_api", fromlist=["sync_playwright"])
    with playwright_module.sync_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": True}
        if browser_executable:
            launch_options["executable_path"] = str(Path(browser_executable).resolve())
        browser = playwright.chromium.launch(**launch_options)
        desktop = browser.new_context(viewport={"width": 1366, "height": 768})
        desktop_page = desktop.new_page()
        desktop_page.on("console", lambda msg: console_errors.append(msg.text[:500]) if msg.type == "error" else None)
        desktop_page.on("pageerror", lambda exc: page_errors.append(str(exc)[:500]))
        topbar = _click_journey(desktop_page, base_url, "public-desktop", PUBLIC_NAV)
        entity_paths = _discover_entity_paths(desktop_page, base_url)
        audited_paths = tuple(dict.fromkeys((*CRITICAL_PAGES, *entity_paths)))
        pages = [_page_evidence(desktop_page, base_url, path) for path in audited_paths]
        desktop_page.goto(base_url, wait_until="networkidle", timeout=45_000)
        desktop_page.screenshot(path=str(output_dir / "home_desktop.png"), full_page=False)
        desktop.close()

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=1,
        )
        mobile_page = mobile.new_page()
        mobile_page.on("console", lambda msg: console_errors.append(msg.text[:500]) if msg.type == "error" else None)
        mobile_page.on("pageerror", lambda exc: page_errors.append(str(exc)[:500]))
        mobile_nav = _click_journey(mobile_page, base_url, "client-bottom", MOBILE_NAV)
        mobile_page.goto(base_url, wait_until="networkidle", timeout=45_000)
        mobile_layout = mobile_page.evaluate(
            """() => {
              const nav = document.querySelector('[data-nav-zone="client-bottom"]');
              const links = nav ? [...nav.querySelectorAll('a')] : [];
              return {
                visible: Boolean(nav && getComputedStyle(nav).display !== 'none'),
                targets: links.map((a) => ({width: a.getBoundingClientRect().width, height: a.getBoundingClientRect().height})),
                overflow: document.documentElement.scrollWidth > window.innerWidth + 2,
              };
            }"""
        )
        mobile_page.screenshot(path=str(output_dir / "home_mobile.png"), full_page=False)
        mobile.close()

        protection_context = browser.new_context(viewport={"width": 1366, "height": 768})
        protection = protection_context.new_page()
        protection.goto(
            urllib.parse.urljoin(base_url.rstrip("/") + "/", "admin/dashboard"),
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        admin_final_path = urllib.parse.urlparse(protection.url).path
        protection_context.close()
        browser.close()

    broken_images = [image for item in pages for image in item.get("brokenImages") or []]
    overflow = [item["path"] for item in pages if item.get("overflow")]
    mojibake = [value for item in pages for value in item.get("mojibake") or []]
    technical_copy = [value for item in pages for value in item.get("technical_copy") or []]
    resources = [value for item in pages for value in item.get("resources") or []]
    visual_assets_pass, visual_asset_evidence = _visual_asset_contract(resources)
    performance_pass = all(
        item.get("elapsed_ms", 99_999) <= (8_000 if item["path"] == "/shark" else 5_000)
        for item in pages
    )
    routes_pass = all(item.get("http") == 200 for item in pages)
    topbar_pass = all(item.get("pass") is True for item in topbar)
    mobile_pass = (
        all(item.get("pass") is True for item in mobile_nav)
        and mobile_layout.get("visible") is True
        and mobile_layout.get("overflow") is False
        and all(item.get("height", 0) >= 44 for item in mobile_layout.get("targets") or [])
    )
    visual_pass = all(item.get("shell") and item.get("cssVersioned") for item in pages) and visual_assets_pass
    temporal_missing = sum(int(item.get("missingTemporalCards") or 0) for item in pages)
    temporal_observed = sum(int(item.get("temporalCards") or 0) for item in pages)
    temporal_by_match: dict[str, set[str]] = {}
    for page_item in pages:
        for temporal in page_item.get("temporalValues") or []:
            match_id = str(temporal.get("matchId") or "").strip()
            instant = str(temporal.get("datetime") or "").strip()
            if match_id and instant:
                temporal_by_match.setdefault(match_id, set()).add(instant)
    temporal_conflicts = {
        match_id: sorted(instants)
        for match_id, instants in temporal_by_match.items()
        if len(instants) > 1
    }
    temporal_pass = temporal_missing == 0 and not temporal_conflicts and routes_pass
    browser_clean = not console_errors and not page_errors and not broken_images and not overflow and not mojibake and not technical_copy
    actual_sha = str(runtime.get("git_commit_hint") or "")
    checks = {
        "health": "PASS" if health_http == 200 and bool(health) else "FAIL",
        "sha_alignment": "PASS" if runtime_http == 200 and actual_sha == expected_sha else "FAIL",
        "logs_recent": "PASS" if int(runtime.get("sentinel_active_issues_count") or 0) == 0 and not console_errors and not page_errors else "FAIL",
        "critical_routes": "PASS" if routes_pass and browser_clean else "FAIL",
        "topbar_click_journey": "PASS" if topbar_pass else "FAIL",
        "mobile_nav": "PASS" if mobile_pass else "FAIL",
        "sports_truth": "PASS" if sports_http == 200 and sports_pass else "FAIL",
        "temporal_context": "PASS" if temporal_pass else "FAIL",
        "performance_sample": "PASS" if performance_pass else "FAIL",
        "critical_visual_surfaces": "PASS" if visual_pass else "FAIL",
        "client_admin_protection": "PASS" if admin_final_path == "/admin-login" else "FAIL",
    }
    evidence = {
        "runtime_http": runtime_http,
        "health_http": health_http,
        "sports_http": sports_http,
        "topbar_clicks": topbar,
        "mobile_clicks": mobile_nav,
        "mobile_layout": mobile_layout,
        "pages": pages,
        "sports": sports_evidence,
        "temporal_context": {
            "contract": "MATCH-TEMPORAL-CONTEXT-V1",
            "observed": temporal_observed,
            "missing": temporal_missing,
            "madrid_time": True,
            "cross_surface_consistent": not temporal_conflicts,
            "conflicts": temporal_conflicts,
            "external_provider_calls": 0,
            "entity_paths": list(entity_paths),
        },
        "admin_final_path": admin_final_path,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "broken_images": broken_images,
        "overflow": overflow,
        "mojibake": mojibake,
        "technical_copy": technical_copy,
        "visual_assets": visual_asset_evidence,
        "health_fields": sorted(health)[:40],
    }
    return build_post_deploy_result(
        expected_sha=expected_sha,
        actual_sha=actual_sha,
        checks=checks,
        evidence=evidence,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "verify"), required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--report-path", default="reports/PRODUCTION_QUALITY_SENTINEL.json")
    parser.add_argument("--output-dir", default="reports/production_quality_sentinel")
    parser.add_argument("--browser-executable", default="")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_sha):
        raise SystemExit("expected SHA must be a full lowercase 40-character commit")
    parsed = urllib.parse.urlparse(args.base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("base URL must be public HTTPS")
    if args.mode == "dry-run":
        result = {
            "result": "DRY_RUN_PASS",
            "network_requests": 0,
            "production_mutations": 0,
            "telegram_sends": 0,
            "stripe_actions": 0,
        }
    else:
        result = run_gate(
            args.base_url,
            args.expected_sha,
            Path(args.output_dir),
            args.browser_executable,
        )
    target = Path(args.report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "failed_checks": result.get("failed_checks", [])}, indent=2))
    return 0 if result["result"] in {"DRY_RUN_PASS", "PRODUCTION_CERTIFIED"} else 1


if __name__ == "__main__":
    sys.exit(main())
