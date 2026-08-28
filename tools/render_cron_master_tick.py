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
            return {
                "telegram_http": http_status,
                "telegram_status": "PASS" if ok else "FAIL",
                "telegram_result": result,
                "telegram_duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            }
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
