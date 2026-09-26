#!/usr/bin/env python3
"""Stateless coordinator for the existing NeMeSiS Render Cron service.

The runner owns all production recurrence and keeps no local state:

1. Telegram/sports automation tick.
2. Continuous Evolution tick on the persistent web service.
3. Data Vault backup only inside the daily UTC maintenance window.

The web service owns backup dedupe and persistent storage. The runner uses only
PUBLIC_BASE_URL and AUTOMATION_SECRET, emits one sanitized JSON
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
BACKUP_ENDPOINT = "/api/automation/data-backup/run"
READINESS_ENDPOINT = "/api/runtime-version"
TELEGRAM_TIMEOUT_SECONDS = 45
CONTINUOUS_EVOLUTION_TIMEOUT_SECONDS = 90
BACKUP_TIMEOUT_SECONDS = 90
BACKUP_WINDOW_START_MINUTE_UTC = 2 * 60 + 30
BACKUP_WINDOW_END_MINUTE_UTC = 4 * 60 + 30
READINESS_TIMEOUT_SECONDS = 8
READINESS_ATTEMPTS = 6
READINESS_BACKOFF_SECONDS = 5
TRANSIENT_READINESS_HTTP = {502, 503, 504}
CONTINUOUS_VALID_RESULTS = {"RUN", "SKIPPED_NOT_DUE", "SKIPPED_ALREADY_RUNNING"}
BACKUP_VALID_RESULTS = {"PASS", "OK", "SKIPPED_ALREADY_DONE", "SKIPPED_ALREADY_RUNNING"}


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def backup_due(utc_now: str) -> bool:
    """Allow several cron attempts; the web service dedupes the successful day."""
    try:
        current = datetime.fromisoformat(str(utc_now).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return False
    minute = current.hour * 60 + current.minute
    return BACKUP_WINDOW_START_MINUTE_UTC <= minute < BACKUP_WINDOW_END_MINUTE_UTC


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
    raw_current_sync = raw.get("current_sync") if isinstance(raw.get("current_sync"), dict) else {}
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
        "provider_access_is_current": bool(raw.get("provider_access_is_current")),
        "provider_access_freshness": safe_label(raw.get("provider_access_freshness"), secret),
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
            "is_current": bool(raw_access.get("is_current")),
            "freshness": safe_label(raw_access.get("freshness"), secret),
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
        "current_sync": {
            "source_scope": safe_label(raw_current_sync.get("source_scope"), secret, "MATCH_WINDOW_PRIMARY_FALLBACK"),
            "selected_source": safe_label(raw_current_sync.get("selected_source"), secret),
            "api_football_primary": {
                "state": safe_label((raw_current_sync.get("api_football_primary") or {}).get("state"), secret),
                "used": bool((raw_current_sync.get("api_football_primary") or {}).get("used")),
                "data_contributed": bool((raw_current_sync.get("api_football_primary") or {}).get("data_contributed")),
                "cache_reused": bool((raw_current_sync.get("api_football_primary") or {}).get("cache_reused")),
                "reason_code": safe_label((raw_current_sync.get("api_football_primary") or {}).get("reason_code"), secret),
                "failure_class": safe_label((raw_current_sync.get("api_football_primary") or {}).get("failure_class"), secret, ""),
                "ok": (raw_current_sync.get("api_football_primary") or {}).get("ok") if isinstance((raw_current_sync.get("api_football_primary") or {}).get("ok"), bool) else None,
                "configured": (raw_current_sync.get("api_football_primary") or {}).get("configured") if isinstance((raw_current_sync.get("api_football_primary") or {}).get("configured"), bool) else None,
                "enabled": (raw_current_sync.get("api_football_primary") or {}).get("enabled") if isinstance((raw_current_sync.get("api_football_primary") or {}).get("enabled"), bool) else None,
                "external_calls": safe_count((raw_current_sync.get("api_football_primary") or {}).get("external_calls")),
                "fixtures_count": safe_count((raw_current_sync.get("api_football_primary") or {}).get("fixtures_count")),
                "error_present": bool((raw_current_sync.get("api_football_primary") or {}).get("error_present")),
            },
            "sportsdb_fallback": {
                "state": safe_label((raw_current_sync.get("sportsdb_fallback") or {}).get("state"), secret),
                "data_contributed": bool((raw_current_sync.get("sportsdb_fallback") or {}).get("data_contributed")),
                "reason_code": safe_label((raw_current_sync.get("sportsdb_fallback") or {}).get("reason_code"), secret),
                "ok": (raw_current_sync.get("sportsdb_fallback") or {}).get("ok") if isinstance((raw_current_sync.get("sportsdb_fallback") or {}).get("ok"), bool) else None,
                "used": bool((raw_current_sync.get("sportsdb_fallback") or {}).get("used")),
                "processed": safe_count((raw_current_sync.get("sportsdb_fallback") or {}).get("processed")),
                "external_calls": safe_count((raw_current_sync.get("sportsdb_fallback") or {}).get("external_calls")),
                "stale_reconciliation_candidates": safe_count((raw_current_sync.get("sportsdb_fallback") or {}).get("stale_reconciliation_candidates")),
                "stale_reconciliation_observed": safe_count((raw_current_sync.get("sportsdb_fallback") or {}).get("stale_reconciliation_observed")),
                "error_present": bool((raw_current_sync.get("sportsdb_fallback") or {}).get("error_present")),
            },
            "live_refresh": {
                "state": safe_label((raw_current_sync.get("live_refresh") or {}).get("state"), secret),
                "reason_code": safe_label((raw_current_sync.get("live_refresh") or {}).get("reason_code"), secret),
                "ok": (raw_current_sync.get("live_refresh") or {}).get("ok") if isinstance((raw_current_sync.get("live_refresh") or {}).get("ok"), bool) else None,
                "external_calls": safe_count((raw_current_sync.get("live_refresh") or {}).get("external_calls")),
                "fixtures_count": safe_count((raw_current_sync.get("live_refresh") or {}).get("fixtures_count")),
                "error_present": bool((raw_current_sync.get("live_refresh") or {}).get("error_present")),
            },
            "odds_refresh": {
                "state": safe_label((raw_current_sync.get("odds_refresh") or {}).get("state"), secret),
                "reason_code": safe_label((raw_current_sync.get("odds_refresh") or {}).get("reason_code"), secret),
                "ok": (raw_current_sync.get("odds_refresh") or {}).get("ok") if isinstance((raw_current_sync.get("odds_refresh") or {}).get("ok"), bool) else None,
                "processed": safe_count((raw_current_sync.get("odds_refresh") or {}).get("processed")),
                "external_calls": safe_count((raw_current_sync.get("odds_refresh") or {}).get("external_calls")),
                "error_present": bool((raw_current_sync.get("odds_refresh") or {}).get("error_present")),
            },
        },
        "data_freshness": {
            "state": safe_label(raw_freshness.get("state"), secret, "NOT_ESTABLISHED"),
            "entity_timestamps_evaluated": bool(raw_freshness.get("entity_timestamps_evaluated")),
            "scope": safe_label(raw_freshness.get("scope"), secret, "MATCH_ROWS_CANONICAL_PROVIDER_CLOCKS"),
            "total": safe_count(raw_freshness.get("total")),
            "fresh": safe_count(raw_freshness.get("fresh")),
            "observed": safe_count(raw_freshness.get("observed")),
            "stale": safe_count(raw_freshness.get("stale")),
            "not_established": safe_count(raw_freshness.get("not_established")),
            "reason": safe_label(raw_freshness.get("reason"), secret, ""),
            "stale_samples": [
                {
                    "fixture_id": safe_label(item.get("fixture_id"), secret, ""),
                    "home_team": safe_label(item.get("home_team"), secret, ""),
                    "away_team": safe_label(item.get("away_team"), secret, ""),
                    "competition": safe_label(item.get("competition"), secret, ""),
                    "provider": safe_label(item.get("provider"), secret, ""),
                    "provider_observed_at": safe_label(item.get("provider_observed_at"), secret, ""),
                    "freshness_seconds": safe_count(item.get("freshness_seconds")),
                    "stale_reason": safe_label(item.get("stale_reason"), secret, ""),
                    "status_canonical": safe_label(item.get("status_canonical"), secret, ""),
                }
                for item in list(raw_freshness.get("stale_samples") or [])[:5]
                if isinstance(item, dict)
            ],
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


def wait_for_web_ready(base_url: str) -> dict:
    """Wait briefly for the web service during an atomic Render deploy.

    This probe is read-only and carries no automation secret. Side-effecting
    ticks only start after the web service answers successfully, which avoids
    turning a normal deploy overlap into a failed cron run.
    """
    started = time.perf_counter()
    last_http = None
    last_result = "WEB_NOT_READY"
    for attempt in range(1, READINESS_ATTEMPTS + 1):
        request = urllib.request.Request(
            f"{base_url}{READINESS_ENDPOINT}",
            headers={
                "User-Agent": "NeMeSiS-SHARK-PRO-Master-Cron-Readiness/V1",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=READINESS_TIMEOUT_SECONDS) as response:
                http_status = int(response.status)
                if 200 <= http_status < 300:
                    return {
                        "readiness_status": "PASS",
                        "readiness_http": http_status,
                        "readiness_result": "WEB_READY",
                        "readiness_attempts": attempt,
                        "readiness_duration_ms": max(
                            0, round((time.perf_counter() - started) * 1000)
                        ),
                    }
                last_http = http_status
                last_result = f"HTTP_{http_status}"
                if http_status not in TRANSIENT_READINESS_HTTP:
                    break
        except urllib.error.HTTPError as exc:
            last_http = int(exc.code)
            last_result = f"HTTP_{last_http}"
            if last_http not in TRANSIENT_READINESS_HTTP:
                break
        except Exception as exc:
            reason = getattr(exc, "reason", None)
            is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(
                reason, (TimeoutError, socket.timeout)
            )
            last_result = "TIMEOUT" if is_timeout else type(exc).__name__

        if attempt < READINESS_ATTEMPTS:
            time.sleep(READINESS_BACKOFF_SECONDS)

    return {
        "readiness_status": "FAIL",
        "readiness_http": last_http,
        "readiness_result": last_result,
        "readiness_attempts": READINESS_ATTEMPTS,
        "readiness_duration_ms": max(
            0, round((time.perf_counter() - started) * 1000)
        ),
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


def backup_tick(base_url: str, secret: str) -> dict:
    started = time.perf_counter()
    request = urllib.request.Request(
        f"{base_url}{BACKUP_ENDPOINT}",
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
        with urllib.request.urlopen(request, timeout=BACKUP_TIMEOUT_SECONDS) as response:
            http_status = int(response.status)
            payload = decode_json(response.read(30000))
            if payload is None:
                return request_error_result("backup", started, "INVALID_JSON_RESPONSE", http_status)
            candidate = payload.get("status") or payload.get("result")
            result = safe_label(candidate, secret, "PASS" if payload.get("ok") is not False else "FAIL")
            ok = http_status == 200 and payload.get("ok") is not False and result in BACKUP_VALID_RESULTS
            return {
                "backup_http": http_status,
                "backup_status": "PASS" if ok else "FAIL",
                "backup_result": result,
                "backup_created": bool(payload.get("backup_created")),
                "backup_duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            }
    except urllib.error.HTTPError as exc:
        return request_error_result("backup", started, f"HTTP_{int(exc.code)}", int(exc.code))
    except Exception as exc:
        reason = getattr(exc, "reason", None)
        is_timeout = isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(reason, (TimeoutError, socket.timeout))
        return request_error_result("backup", started, "TIMEOUT" if is_timeout else type(exc).__name__)


def skipped_backup() -> dict:
    return {
        "backup_http": None,
        "backup_status": "PASS",
        "backup_result": "SKIPPED_NOT_DUE",
        "backup_created": False,
        "backup_duration_ms": 0,
    }


def overall_status(telegram: dict, continuous: dict, backup: dict) -> str:
    successful = sum(
        item.get(key) == "PASS"
        for item, key in ((telegram, "telegram_status"), (continuous, "continuous_status"))
    )
    base = "PASS" if successful == 2 else "PARTIAL" if successful == 1 else "FAIL"
    if backup.get("backup_status") == "FAIL" and base == "PASS":
        return "PARTIAL"
    return base


def isolated_tick(call, prefix: str, base_url: str, secret: str) -> dict:
    started = time.perf_counter()
    try:
        return call(base_url, secret)
    except Exception as exc:
        return request_error_result(prefix, started, type(exc).__name__)


def readiness_failure(readiness: dict, utc_now: str, madrid_now: str) -> dict:
    reason = safe_label(readiness.get("readiness_result"), "", "WEB_NOT_READY")
    return {
        "runner": RUNNER_NAME,
        "web_readiness": readiness,
        "telegram_status": "NOT_EXECUTED",
        "continuous_evolution_status": "NOT_EXECUTED",
        "backup_status": "NOT_EXECUTED",
        "telegram": {
            "telegram_http": None,
            "telegram_status": "NOT_EXECUTED",
            "telegram_result": reason,
            "telegram_duration_ms": 0,
        },
        "continuous_evolution": {
            "continuous_http": None,
            "continuous_status": "NOT_EXECUTED",
            "continuous_result": reason,
            "continuous_duration_ms": 0,
        },
        "backup": {
            "backup_http": None,
            "backup_status": "NOT_EXECUTED",
            "backup_result": reason,
            "backup_created": False,
            "backup_duration_ms": 0,
        },
        "overall": "FAIL",
        "timestamp_madrid": madrid_now,
        "timestamp_utc": utc_now,
        "duration_ms": safe_count(readiness.get("readiness_duration_ms")),
    }


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
        "backup": {
            "backup_http": None,
            "backup_status": "NOT_EXECUTED",
            "backup_result": error,
            "backup_created": False,
            "backup_duration_ms": 0,
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

    readiness = wait_for_web_ready(base_url)
    if readiness.get("readiness_status") != "PASS":
        payload = readiness_failure(readiness, utc_now, madrid_now)
        payload["duration_ms"] = max(0, round((time.perf_counter() - started) * 1000))
        print_event(payload)
        return 2

    telegram = isolated_tick(telegram_tick, "telegram", base_url, automation_secret)
    continuous = isolated_tick(continuous_evolution_tick, "continuous", base_url, automation_secret)
    backup = isolated_tick(backup_tick, "backup", base_url, automation_secret) if backup_due(utc_now) else skipped_backup()
    overall = overall_status(telegram, continuous, backup)
    print_event({
        "runner": RUNNER_NAME,
        "web_readiness": readiness,
        "telegram_status": telegram.get("telegram_status"),
        "continuous_evolution_status": continuous.get("continuous_status"),
        "backup_status": backup.get("backup_status"),
        "telegram": telegram,
        "continuous_evolution": continuous,
        "backup": backup,
        "overall": overall,
        "timestamp_madrid": madrid_now,
        "timestamp_utc": utc_now,
        "duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
    })
    return {"PASS": 0, "PARTIAL": 1, "FAIL": 2}[overall]


if __name__ == "__main__":
    raise SystemExit(main())
