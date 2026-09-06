#!/usr/bin/env python3
"""Stateless coordinator for the existing NeMeSiS Render Cron service.

The runner performs two isolated HTTP calls and keeps no local state:

1. Telegram automation tick.
2. Continuous Evolution tick on the persistent web service.

It uses only PUBLIC_BASE_URL and AUTOMATION_SECRET, emits one sanitized JSON
record, and never puts the secret in a URL or response payload.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RUNNER_NAME = "nemesis_master_tick"
TELEGRAM_ENDPOINT = "/api/automation/telegram/tick?runner=render_cron"
CONTINUOUS_EVOLUTION_ENDPOINT = "/api/automation/continuous-evolution/tick"
TELEGRAM_TIMEOUT_SECONDS = 45
CONTINUOUS_EVOLUTION_TIMEOUT_SECONDS = 90
CONTINUOUS_VALID_RESULTS = {"RUN", "SKIPPED_NOT_DUE", "SKIPPED_ALREADY_RUNNING"}


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def print_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def validated_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("INVALID_PUBLIC_BASE_URL")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def safe_label(value: object, secret: str, fallback: str = "UNKNOWN") -> str:
    label = str(value or fallback).strip()[:120]
    if secret and secret in label:
        return "REDACTED"
    return label or fallback


def safe_count(value: object) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def sanitized_sports_pipeline(payload: dict, secret: str) -> dict:
    raw = payload.get("sports_pipeline")
    if not isinstance(raw, dict):
        return {}
    raw_quota = raw.get("quota") if isinstance(raw.get("quota"), dict) else {}
    quota = {
        key: safe_count(raw_quota.get(key))
        for key in (
            "daily_limit",
            "daily_used",
            "daily_remaining",
            "minute_limit",
            "minute_remaining",
        )
        if raw_quota.get(key) is not None
    }
    capabilities = {}
    for raw_name, raw_value in list((raw.get("capabilities") or {}).items())[:20]:
        if not isinstance(raw_value, dict):
            continue
        name = safe_label(raw_name, secret, "unknown")
        if name == "REDACTED":
            continue
        capabilities[name] = {
            "requested": bool(raw_value.get("requested")),
            "received": safe_count(raw_value.get("received")),
            "persisted": safe_count(raw_value.get("persisted")),
        }
    raw_sample = raw.get("last_sample") if isinstance(raw.get("last_sample"), dict) else {}
    raw_job = raw.get("job_execution") if isinstance(raw.get("job_execution"), dict) else {}
    raw_deep = raw.get("deep_execution") if isinstance(raw.get("deep_execution"), dict) else {}
    raw_access = raw.get("provider_access") if isinstance(raw.get("provider_access"), dict) else {}
    raw_plan = raw.get("provider_plan_observation") if isinstance(raw.get("provider_plan_observation"), dict) else {}
    raw_quota_observation = raw.get("quota_observation") if isinstance(raw.get("quota_observation"), dict) else {}
    raw_quota_values = raw_quota_observation.get("values") if isinstance(raw_quota_observation.get("values"), dict) else {}
    raw_coverage = raw.get("coverage") if isinstance(raw.get("coverage"), dict) else {}
    raw_coverage_capabilities = raw_coverage.get("capabilities") if isinstance(raw_coverage.get("capabilities"), dict) else {}
    raw_freshness = raw.get("data_freshness") if isinstance(raw.get("data_freshness"), dict) else {}
    fixture_ids = [
        safe_label(value, secret, "")
        for value in list(raw_sample.get("fixture_ids") or [])[:1]
    ]
    coverage = {}
    for raw_name, raw_value in list(raw_coverage_capabilities.items())[:20]:
        if not isinstance(raw_value, dict):
            continue
        name = safe_label(raw_name, secret, "unknown")
        if name == "REDACTED":
            continue
        coverage[name] = {
            "state": safe_label(raw_value.get("state"), secret),
            "requested": bool(raw_value.get("requested")),
            "received": safe_count(raw_value.get("received")),
            "persisted": safe_count(raw_value.get("persisted")),
            "received_scope": safe_label(raw_value.get("received_scope"), secret),
            "persisted_scope": safe_label(raw_value.get("persisted_scope"), secret),
            "observed_at": safe_label(raw_value.get("observed_at"), secret, ""),
            "reason": safe_label(raw_value.get("reason"), secret, ""),
        }
    return {
        "status": safe_label(raw.get("status"), secret),
        "deep_status": safe_label(raw.get("deep_status"), secret),
        "deep_external_calls": safe_count(raw.get("deep_external_calls")),
        "provider_authenticated": bool(raw.get("provider_authenticated")),
        "provider_plan": safe_label(raw.get("provider_plan"), secret, "INACCESSIBLE"),
        "quota": quota,
        "capabilities": capabilities,
        "last_sample": {
            "status": safe_label(raw_sample.get("status"), secret),
            "finished_at": safe_label(raw_sample.get("finished_at"), secret, ""),
            "external_calls": safe_count(raw_sample.get("external_calls")),
            "fixture_ids": [value for value in fixture_ids if value and value != "REDACTED"],
            "source": safe_label(raw_sample.get("source"), secret, "NONE"),
            "scope": safe_label(raw_sample.get("scope"), secret, "DEEP_ENRICHMENT"),
            "is_current_job": bool(raw_sample.get("is_current_job")),
            "freshness_state": safe_label(raw_sample.get("freshness_state"), secret),
        },
        "job_execution": {
            "state": safe_label(raw_job.get("state"), secret),
            "ok": raw_job.get("ok") if isinstance(raw_job.get("ok"), bool) else None,
            "started_at": safe_label(raw_job.get("started_at"), secret, ""),
            "finished_at": safe_label(raw_job.get("finished_at"), secret, ""),
            "trigger_type": safe_label(raw_job.get("trigger_type"), secret, ""),
            "external_calls": safe_count(raw_job.get("external_calls")),
            "processed": safe_count(raw_job.get("processed")),
            "scope": safe_label(raw_job.get("scope"), secret, "CURRENT_SPORTS_SYNC"),
        },
        "deep_execution": {
            "state": safe_label(raw_deep.get("state"), secret),
            "status": safe_label(raw_deep.get("status"), secret),
            "external_calls": safe_count(raw_deep.get("external_calls")),
            "scope": safe_label(raw_deep.get("scope"), secret, "CURRENT_SPORTS_SYNC"),
        },
        "provider_access": {
            "provider": safe_label(raw_access.get("provider"), secret, "API-Football"),
            "state": safe_label(raw_access.get("state"), secret, "NOT_CHECKED"),
            "configured": raw_access.get("configured") if isinstance(raw_access.get("configured"), bool) else None,
            "authenticated": raw_access.get("authenticated") if isinstance(raw_access.get("authenticated"), bool) else None,
            "checked_at": safe_label(raw_access.get("checked_at"), secret, ""),
            "source": safe_label(raw_access.get("source"), secret, "NONE"),
        },
        "provider_plan_observation": {
            "state": safe_label(raw_plan.get("state"), secret),
            "value": (
                safe_label(raw_plan.get("value"), secret, "")
                if raw_plan.get("value") is not None
                else None
            ),
            "observed_at": safe_label(raw_plan.get("observed_at"), secret, ""),
            "source": safe_label(raw_plan.get("source"), secret, "NONE"),
        },
        "quota_observation": {
            "state": safe_label(raw_quota_observation.get("state"), secret),
            "values": {
                key: safe_count(raw_quota_values.get(key))
                for key in (
                    "daily_limit",
                    "daily_used",
                    "daily_remaining",
                    "minute_limit",
                    "minute_remaining",
                )
                if raw_quota_values.get(key) is not None
            },
            "observed_at": safe_label(raw_quota_observation.get("observed_at"), secret, ""),
            "source": safe_label(raw_quota_observation.get("source"), secret, "NONE"),
            "freshness": safe_label(raw_quota_observation.get("freshness"), secret),
        },
        "coverage": {
            "provider": safe_label(raw_coverage.get("provider"), secret, "API-Football"),
            "source": safe_label(raw_coverage.get("source"), secret, "NONE"),
            "observed_at": safe_label(raw_coverage.get("observed_at"), secret, ""),
            "capabilities": coverage,
        },
        "data_freshness": {
            "state": safe_label(raw_freshness.get("state"), secret, "NOT_ESTABLISHED"),
            "entity_timestamps_evaluated": bool(raw_freshness.get("entity_timestamps_evaluated")),
            "reason": safe_label(raw_freshness.get("reason"), secret, ""),
        },
    }


def decode_json(body: bytes) -> dict | None:
    try:
        data = json.loads(body.decode("utf-8", errors="replace") or "{}")
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def request_error_result(prefix: str, started: float, error: str, http_status: int | None = None) -> dict:
    return {
        f"{prefix}_http": http_status,
        f"{prefix}_status": "FAIL",
        f"{prefix}_result": error,
        f"{prefix}_duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
    }


def telegram_tick(base_url: str, secret: str) -> dict:
    started = time.perf_counter()
    request = urllib.request.Request(
        f"{base_url}{TELEGRAM_ENDPOINT}",
        headers={
            "User-Agent": "NeMeSiS-SHARK-PRO-Master-Cron/V1",
            "X-NeMeSiS-Cron-Runner": "render-cron",
            "X-Automation-Secret": secret,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TELEGRAM_TIMEOUT_SECONDS) as response:
            http_status = int(response.status)
            payload = decode_json(response.read(30000))
            if payload is None:
                return request_error_result("telegram", started, "INVALID_JSON_RESPONSE", http_status)
            ok = http_status == 200 and payload.get("ok") is not False
            result = safe_label(payload.get("status") or payload.get("result"), secret, "PASS" if ok else "FAIL")
            response = {
                "telegram_http": http_status,
                "telegram_status": "PASS" if ok else "FAIL",
                "telegram_result": result,
                "telegram_duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            }
            pipeline = sanitized_sports_pipeline(payload, secret)
            if pipeline:
                response["sports_pipeline"] = pipeline
            return response
    except urllib.error.HTTPError as exc:
        return request_error_result("telegram", started, f"HTTP_{int(exc.code)}", int(exc.code))
    except Exception as exc:
        reason = getattr(exc, "reason", None)
        is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(reason, (TimeoutError, socket.timeout))
        return request_error_result("telegram", started, "TIMEOUT" if is_timeout else type(exc).__name__)


def continuous_evolution_tick(base_url: str, secret: str) -> dict:
    started = time.perf_counter()
    request = urllib.request.Request(
        f"{base_url}{CONTINUOUS_EVOLUTION_ENDPOINT}",
        data=b"{}",
        headers={
            "User-Agent": "NeMeSiS-SHARK-PRO-Master-Cron/V1",
            "X-NeMeSiS-Cron-Runner": "render-cron",
            "X-Automation-Secret": secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=CONTINUOUS_EVOLUTION_TIMEOUT_SECONDS) as response:
            http_status = int(response.status)
            payload = decode_json(response.read(30000))
            if payload is None:
                return request_error_result("continuous", started, "INVALID_JSON_RESPONSE", http_status)
            upstream_result = safe_label(payload.get("result") or payload.get("status"), secret)
            result = "RUN" if upstream_result == "PASS" else upstream_result
            ok = http_status == 200 and payload.get("ok") is not False and result in CONTINUOUS_VALID_RESULTS
            return {
                "continuous_http": http_status,
                "continuous_status": "PASS" if ok else "FAIL",
                "continuous_result": result,
                "continuous_duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            }
    except urllib.error.HTTPError as exc:
        return request_error_result("continuous", started, f"HTTP_{int(exc.code)}", int(exc.code))
    except Exception as exc:
        reason = getattr(exc, "reason", None)
        is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(reason, (TimeoutError, socket.timeout))
        return request_error_result("continuous", started, "TIMEOUT" if is_timeout else type(exc).__name__)


def overall_status(telegram: dict, continuous: dict) -> str:
    successful = sum(
        item.get(key) == "PASS"
        for item, key in ((telegram, "telegram_status"), (continuous, "continuous_status"))
    )
    if successful == 2:
        return "PASS"
    if successful == 1:
        return "PARTIAL"
    return "FAIL"


def isolated_tick(call, prefix: str, base_url: str, secret: str) -> dict:
    started = time.perf_counter()
    try:
        return call(base_url, secret)
    except Exception as exc:
        return request_error_result(prefix, started, type(exc).__name__)


def config_failure(error: str, utc_now: str, madrid_now: str) -> dict:
    return {
        "runner": RUNNER_NAME,
        "telegram_status": "NOT_EXECUTED",
        "continuous_evolution_status": "NOT_EXECUTED",
        "telegram": {
            "telegram_http": None,
            "telegram_status": "NOT_EXECUTED",
            "telegram_result": error,
            "telegram_duration_ms": 0,
        },
        "continuous_evolution": {
            "continuous_http": None,
            "continuous_status": "NOT_EXECUTED",
            "continuous_result": error,
            "continuous_duration_ms": 0,
        },
        "overall": "FAIL",
        "timestamp_madrid": madrid_now,
        "timestamp_utc": utc_now,
        "duration_ms": 0,
    }


def main() -> int:
    started = time.perf_counter()
    utc_now, madrid_now = now_labels()
    public_base_url = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    automation_secret = (os.environ.get("AUTOMATION_SECRET") or "").strip()

    if not public_base_url:
        payload = config_failure("MISSING_PUBLIC_BASE_URL", utc_now, madrid_now)
        payload["duration_ms"] = max(0, round((time.perf_counter() - started) * 1000))
        print_event(payload)
        return 2
    if not automation_secret:
        payload = config_failure("MISSING_AUTOMATION_SECRET", utc_now, madrid_now)
        payload["duration_ms"] = max(0, round((time.perf_counter() - started) * 1000))
        print_event(payload)
        return 2
    try:
        base_url = validated_base_url(public_base_url)
    except ValueError:
        payload = config_failure("INVALID_PUBLIC_BASE_URL", utc_now, madrid_now)
        payload["duration_ms"] = max(0, round((time.perf_counter() - started) * 1000))
        print_event(payload)
        return 2

    telegram = isolated_tick(telegram_tick, "telegram", base_url, automation_secret)
    continuous = isolated_tick(continuous_evolution_tick, "continuous", base_url, automation_secret)
    overall = overall_status(telegram, continuous)
    print_event({
        "runner": RUNNER_NAME,
        "telegram_status": telegram.get("telegram_status"),
        "continuous_evolution_status": continuous.get("continuous_status"),
        "telegram": telegram,
        "continuous_evolution": continuous,
        "overall": overall,
        "timestamp_madrid": madrid_now,
        "timestamp_utc": utc_now,
        "duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
    })
    return {"PASS": 0, "PARTIAL": 1, "FAIL": 2}[overall]


if __name__ == "__main__":
    raise SystemExit(main())
