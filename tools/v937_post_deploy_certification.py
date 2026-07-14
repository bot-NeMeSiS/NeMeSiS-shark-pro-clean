"""Read-only V937 Render deployment and sports evidence certification."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


V937 = "V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL"
try:
    MADRID = ZoneInfo("Europe/Madrid")
except Exception:  # Windows runners may not ship the IANA database.
    MADRID = datetime.now().astimezone().tzinfo
EXPECTED_CACHE = "NEMESIS_CACHE_V937"
PUBLIC_ROUTES = {
    "/": 200,
    "/calendar": 200,
    "/live": 200,
    "/picks": 200,
    "/shark": 200,
    "/telegram": 200,
    "/api/runtime-version": 200,
    "/api/health": 200,
    "/api/realtime/sports": 200,
    "/manifest.json": 200,
    "/service-worker.js": 200,
    "/ruta-inventada": 404,
}
LATENCY_TARGET_MS = {
    "/": 1000,
    "/calendar": 2000,
    "/live": 2000,
    "/picks": 2000,
    "/shark": 5000,
    "/api/runtime-version": 2000,
    "/api/realtime/sports": 2000,
}
SECRET_PATTERNS = (
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),
)


def _request(base_url: str, path: str, timeout: int = 30) -> dict[str, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NeMeSiS-V937-Post-Deploy-Certifier/1.0",
            "Accept": "application/json,text/html,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
            final_url = response.geturl()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
        final_url = exc.geturl()
    except Exception as exc:  # Network errors are reported without leaking internals.
        return {
            "path": path,
            "status": 0,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "final_url": url,
            "body": "",
            "error": type(exc).__name__,
        }
    return {
        "path": path,
        "status": status,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "final_url": final_url,
        "body": body,
        "error": None,
    }


def _json_response(base_url: str, path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    response = _request(base_url, path)
    try:
        payload = json.loads(response["body"])
    except (TypeError, json.JSONDecodeError):
        payload = {}
    return payload if isinstance(payload, dict) else {}, response


def _parse_offsets(value: str) -> list[int]:
    try:
        offsets = sorted({int(part.strip()) for part in value.split(",") if part.strip()})
    except ValueError as exc:
        raise ValueError("check offsets must be comma-separated integers") from exc
    if not offsets or offsets[0] != 0 or any(item < 0 or item > 3600 for item in offsets):
        raise ValueError("check offsets must start at 0 and stay between 0 and 3600 seconds")
    return offsets


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=MADRID)
    return parsed.astimezone(MADRID)


def _secret_found(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in SECRET_PATTERNS)


def _live_has_evidence(item: dict[str, Any]) -> bool:
    score = item.get("home_score") is not None and item.get("away_score") is not None
    minute = item.get("minute") is not None
    explicit_phase = str(item.get("status") or "").lower() in {"live", "halftime"}
    return bool(score or minute or explicit_phase)


def _wait_for_expected_runtime(
    base_url: str,
    expected_version: str,
    expected_sha: str,
    timeout_seconds: int,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    deadline = time.monotonic() + max(0, timeout_seconds)
    attempts: list[dict[str, Any]] = []
    last_payload: dict[str, Any] = {}
    while True:
        payload, response = _json_response(base_url, "/api/runtime-version")
        last_payload = payload
        attempt = {
            "status": response["status"],
            "version": payload.get("version"),
            "sha": payload.get("git_commit_hint"),
        }
        attempts.append(attempt)
        if (
            response["status"] == 200
            and payload.get("version") == expected_version
            and payload.get("git_commit_hint") == expected_sha
        ):
            return "DEPLOY_CONFIRMED", payload, attempts
        if time.monotonic() >= deadline:
            if response["status"] == 0 or response["status"] >= 500:
                return "RUNTIME_ERROR", last_payload, attempts
            if payload.get("version") == expected_version and payload.get("git_commit_hint") != expected_sha:
                return "WRONG_SHA", last_payload, attempts
            return "DEPLOY_TIMEOUT", last_payload, attempts
        time.sleep(20)


def _probe(
    base_url: str,
    label: str,
    expected_version: str,
    expected_sha: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    runtime, runtime_response = _json_response(base_url, "/api/runtime-version")
    sports, sports_response = _json_response(base_url, "/api/realtime/sports")

    if runtime_response["status"] != 200:
        errors.append("runtime_http_failure")
    if runtime.get("version") != expected_version:
        errors.append("runtime_version_mismatch")
    if runtime.get("git_commit_hint") != expected_sha:
        errors.append("runtime_sha_mismatch")
    if runtime.get("version_files_match") is not True:
        errors.append("version_files_mismatch")
    if runtime.get("deployment_alignment_status") != "aligned_local_files":
        errors.append("deployment_alignment_failure")
    if runtime.get("static_css_cache_busting") is not True:
        errors.append("css_cache_busting_disabled")
    if runtime.get("service_worker_cache_name") != EXPECTED_CACHE:
        errors.append("service_worker_cache_mismatch")
    if int(runtime.get("sentinel_active_issues_count") or 0) != 0:
        errors.append("sentinel_active_issues")

    matches = [item for item in sports.get("matches") or [] if isinstance(item, dict)]
    live = [item for item in sports.get("live") or [] if isinstance(item, dict)]
    public_stale = [item for item in matches if item.get("is_stale") is True]
    false_live = [
        item
        for item in live
        if item.get("is_stale") is True or item.get("is_live") is not True or not _live_has_evidence(item)
    ]
    if sports_response["status"] != 200:
        errors.append("sports_api_http_failure")
    if sports.get("no_external_calls") is not True:
        errors.append("sports_render_external_call_guard_missing")
    if public_stale:
        errors.append(f"public_stale_live:{len(public_stale)}")
    if false_live:
        errors.append(f"false_live:{len(false_live)}")
    if int((sports.get("counts") or {}).get("live") or 0) != len(live):
        errors.append("live_counter_mismatch")
    expected_poll = 45 if live else 180
    if int(sports.get("poll_after_seconds") or 0) != expected_poll:
        errors.append("polling_interval_mismatch")

    last_sync = _parse_timestamp(sports.get("last_safe_sync"))
    sync_age_seconds = None
    if last_sync is None:
        errors.append("sports_last_sync_missing")
    else:
        sync_age_seconds = max(0, int((datetime.now(MADRID) - last_sync).total_seconds()))
        if sync_age_seconds > 1200:
            errors.append("sports_data_stale")

    routes: list[dict[str, Any]] = []
    five_xx = 0
    for path, expected_status in PUBLIC_ROUTES.items():
        response = _request(base_url, path)
        body = response.pop("body")
        if response["status"] >= 500:
            five_xx += 1
        if response["status"] != expected_status:
            errors.append(f"route_status:{path}:{response['status']}")
        if "Traceback (most recent call last)" in body or "FileNotFoundError" in body:
            errors.append(f"unsafe_error_body:{path}")
        if _secret_found(body):
            errors.append(f"secret_pattern_exposed:{path}")
        target = LATENCY_TARGET_MS.get(path)
        if target and response["latency_ms"] > target:
            warnings.append(f"latency_target:{path}:{response['latency_ms']}ms>{target}ms")
        if response["latency_ms"] > 20000:
            errors.append(f"route_timeout_risk:{path}")
        routes.append(response)
    if five_xx:
        errors.append(f"five_xx:{five_xx}")

    home = _request(base_url, "/")
    if "app.css?v=V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL" not in home["body"]:
        errors.append("home_css_asset_version_mismatch")
    service_worker = _request(base_url, "/service-worker.js")
    if EXPECTED_CACHE not in service_worker["body"]:
        errors.append("service_worker_asset_mismatch")
    manifest, manifest_response = _json_response(base_url, "/manifest.json")
    if manifest_response["status"] != 200 or not manifest:
        errors.append("manifest_invalid")

    return {
        "label": label,
        "checked_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
        "status": "PASS" if not errors else "FAIL",
        "version": runtime.get("version"),
        "sha": runtime.get("git_commit_hint"),
        "sentinel_active_issues": int(runtime.get("sentinel_active_issues_count") or 0),
        "matches": len(matches),
        "live": len(live),
        "stale_live_diagnostic": int((sports.get("counts") or {}).get("stale_live") or 0),
        "public_stale_live": len(public_stale),
        "false_live": len(false_live),
        "poll_after_seconds": sports.get("poll_after_seconds"),
        "last_safe_sync": sports.get("last_safe_sync"),
        "sync_age_seconds": sync_age_seconds,
        "provider_status": sports.get("provider_status"),
        "five_xx": five_xx,
        "routes": routes,
        "warnings": warnings,
        "errors": errors,
    }


def _write_report(path: str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dry-run", "verify"), required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--deployment-timeout", type=int, default=900)
    parser.add_argument("--check-offsets", default="0,120,300")
    parser.add_argument("--report-path")
    args = parser.parse_args()

    offsets = _parse_offsets(args.check_offsets)
    parsed_url = urllib.parse.urlparse(args.base_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise SystemExit("base URL must be public HTTPS")
    if args.expected_version != V937:
        raise SystemExit("only the V937 release identity is allowed")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_sha):
        raise SystemExit("expected SHA must be a full lowercase 40-character commit")

    if args.mode == "dry-run":
        result = {
            "status": "DRY_RUN_PASS",
            "version": args.expected_version,
            "sha": args.expected_sha,
            "check_offsets": offsets,
            "network_requests": 0,
            "deploy_requested": False,
            "db_writes": 0,
            "telegram_sends": 0,
            "stripe_actions": 0,
        }
        if args.report_path:
            _write_report(args.report_path, result)
        print(json.dumps(result, indent=2))
        return 0

    deploy_status, runtime, attempts = _wait_for_expected_runtime(
        args.base_url,
        args.expected_version,
        args.expected_sha,
        args.deployment_timeout,
    )
    result: dict[str, Any] = {
        "status": deploy_status,
        "expected_version": args.expected_version,
        "expected_sha": args.expected_sha,
        "actual_version": runtime.get("version"),
        "actual_sha": runtime.get("git_commit_hint"),
        "deployment_attempts": attempts,
        "samples": [],
    }
    if deploy_status != "DEPLOY_CONFIRMED":
        if args.report_path:
            _write_report(args.report_path, result)
        print(json.dumps(result, indent=2))
        return 1

    observation_started = time.monotonic()
    for offset in offsets:
        wait_seconds = observation_started + offset - time.monotonic()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        sample = _probe(
            args.base_url,
            f"plus_{offset}s" if offset else "immediate",
            args.expected_version,
            args.expected_sha,
        )
        result["samples"].append(sample)
        print(json.dumps({
            "label": sample["label"],
            "status": sample["status"],
            "sha": sample["sha"],
            "public_stale_live": sample["public_stale_live"],
            "false_live": sample["false_live"],
            "five_xx": sample["five_xx"],
            "warnings": sample["warnings"],
            "errors": sample["errors"],
        }))
        if sample["errors"]:
            result["status"] = (
                "ASSET_MISMATCH"
                if any("asset" in error for error in sample["errors"])
                else "HEALTH_FAILURE"
            )
            break
    result["completed_at_madrid"] = datetime.now(MADRID).isoformat(timespec="seconds")
    if args.report_path:
        _write_report(args.report_path, result)
    print(json.dumps({"final_status": result["status"], "samples": len(result["samples"])}, indent=2))
    return 0 if result["status"] == "DEPLOY_CONFIRMED" else 1


if __name__ == "__main__":
    sys.exit(main())
