#!/usr/bin/env python3
"""Stateless Render Cron caller for the Continuous Evolution OS web endpoint.

This runner intentionally keeps no Product Memory and writes no local state. It
only calls the existing web service, where the persistent disk is mounted.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ENDPOINT = "/api/automation/continuous-evolution/tick"


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def safe_target_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{ENDPOINT}"


def print_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def compact_response(body: str) -> dict:
    try:
        data = json.loads(body or "{}")
    except Exception:
        return {"ok": False, "status": "INVALID_JSON_RESPONSE"}
    job = data.get("job") or {}
    return {
        "ok": data.get("ok"),
        "result": data.get("result") or data.get("status"),
        "safe_mode": data.get("safe_mode"),
        "storage": data.get("storage"),
        "trigger": data.get("trigger"),
        "scheduled_for": job.get("scheduled_for"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "duration_ms": job.get("duration_ms"),
        "run_id": job.get("run_id"),
        "snapshot_id": job.get("snapshot_id"),
        "founder_brief_id": job.get("founder_brief_id"),
        "codex_ready_count": job.get("codex_ready_count", 0),
        "next_expected_run": job.get("next_expected_run"),
        "guardrail_violations": data.get("guardrail_violations", 0),
        "telegram_sent": data.get("telegram_sent", 0),
        "stripe_actions": data.get("stripe_actions", 0),
        "deploy": data.get("deploy", 0),
        "push": data.get("push", 0),
        "secrets_exposed": data.get("secrets_exposed", 0),
    }


def main() -> int:
    public_base_url = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    automation_secret = (os.environ.get("AUTOMATION_SECRET") or "").strip()
    utc_now, madrid_now = now_labels()

    if not public_base_url:
        print_event({
            "ok": False,
            "event": "CONTINUOUS_EVOLUTION_CONFIG_ERROR",
            "error": "MISSING_PUBLIC_BASE_URL",
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 2
    if not automation_secret:
        print_event({
            "ok": False,
            "event": "CONTINUOUS_EVOLUTION_CONFIG_ERROR",
            "error": "MISSING_AUTOMATION_SECRET",
            "secret_status": "MISSING",
            "utc_now": utc_now,
            "madrid_now": madrid_now,
            "target": safe_target_url(public_base_url),
        })
        return 2

    target = safe_target_url(public_base_url)
    print_event({
        "ok": True,
        "event": "CONTINUOUS_EVOLUTION_TICK_START",
        "target": target,
        "secret_status": "PRESENT_MASKED",
        "utc_now": utc_now,
        "madrid_now": madrid_now,
    })
    request = urllib.request.Request(
        target,
        data=b"{}",
        headers={
            "User-Agent": "NeMeSiS-SHARK-PRO-Continuous-Evolution-Cron/V1",
            "X-NeMeSiS-Cron-Runner": "render-cron",
            "X-Automation-Secret": automation_secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            status = int(response.status)
            compact = compact_response(response.read(30000).decode("utf-8", errors="replace"))
            ok = status == 200 and compact.get("result") in {"PASS", "PARTIAL", "SKIPPED_NOT_DUE", "SKIPPED_ALREADY_RUNNING", "SKIPPED_PAUSED"}
            print_event({
                "ok": ok,
                "event": "CONTINUOUS_EVOLUTION_TICK_RESPONSE",
                "http_status": status,
                "target": target,
                "utc_now": utc_now,
                "madrid_now": madrid_now,
                "result": compact,
            })
            return 0 if ok else 5
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read(12000).decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        compact = compact_response(body)
        print_event({
            "ok": False,
            "event": "CONTINUOUS_EVOLUTION_TICK_HTTP_ERROR",
            "http_status": status,
            "error": "AUTOMATION_SECRET_REJECTED" if status == 403 else compact.get("result") or "HTTP_ERROR",
            "target": target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
            "result": compact,
        })
        return 3 if status == 403 else 5
    except Exception as exc:
        print_event({
            "ok": False,
            "event": "CONTINUOUS_EVOLUTION_TICK_NETWORK_ERROR",
            "error": type(exc).__name__,
            "target": target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
