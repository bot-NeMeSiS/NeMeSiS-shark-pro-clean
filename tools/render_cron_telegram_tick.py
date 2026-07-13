#!/usr/bin/env python3
"""Simple Render Cron runner for NeMeSiS SHARK PRO Telegram automation.

This script intentionally uses only Python's standard library so Render Cron can
run it with a simple command:

    python tools/render_cron_telegram_tick.py

It reads PUBLIC_BASE_URL and AUTOMATION_SECRET from the Cron Job environment and
calls the existing protected endpoint /api/automation/telegram/tick. It never
prints the full secret.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ENDPOINT = "/api/automation/telegram/tick"


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def safe_target_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}{ENDPOINT}?runner=render_cron"


def print_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def compact_response(body: str) -> dict:
    try:
        data = json.loads(body or "{}")
    except Exception:
        return {"raw": (body or "")[:800]}
    modules = data.get("modules") or ((data.get("result") or {}).get("modules") if isinstance(data.get("result"), dict) else {}) or {}
    return {
        "ok": data.get("ok"),
        "status": data.get("status"),
        "sent_count": data.get("sent_count", data.get("sent", 0)),
        "sent": data.get("sent", 0),
        "inserted": data.get("inserted", 0),
        "processed": data.get("processed", 0),
        "deduped_or_skipped": data.get("skipped", 0),
        "failed": data.get("failed", 0),
        "modules": sorted(modules.keys()) if isinstance(modules, dict) else [],
        "discard_reasons": data.get("discard_reasons") or [],
        "errors": data.get("errors") or [],
    }


def main() -> int:
    public_base_url = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    automation_secret = (os.environ.get("AUTOMATION_SECRET") or "").strip()
    utc_now, madrid_now = now_labels()

    if not public_base_url:
        print_event({
            "ok": False,
            "error": "MISSING_PUBLIC_BASE_URL",
            "message": "Falta PUBLIC_BASE_URL en el Environment del Cron Job.",
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 2

    if not automation_secret:
        print_event({
            "ok": False,
            "error": "MISSING_AUTOMATION_SECRET",
            "message": "Falta AUTOMATION_SECRET en el Environment del Cron Job.",
            "utc_now": utc_now,
            "madrid_now": madrid_now,
            "target": safe_target_url(public_base_url),
            "secret_status": "MISSING",
        })
        return 2

    url = safe_target_url(public_base_url)
    safe_target = url
    print_event({
        "ok": True,
        "event": "CRON_TICK_START",
        "target": safe_target,
        "secret_status": "PRESENT_MASKED",
        "utc_now": utc_now,
        "madrid_now": madrid_now,
    })

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NeMeSiS-SHARK-PRO-Render-Cron/753",
            "X-NeMeSiS-Cron-Runner": "render-cron",
            "X-Automation-Secret": automation_secret,
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            status = int(response.status)
            body_bytes = response.read(20000)
            body = body_bytes.decode("utf-8", errors="replace")
            compact = compact_response(body)
            print_event({
                "ok": status == 200,
                "event": "CRON_TICK_RESPONSE",
                "status": status,
                "target": safe_target,
                "utc_now": utc_now,
                "madrid_now": madrid_now,
                "sent_count": compact.get("sent_count", 0),
                "modules": compact.get("modules", []),
                "sent": compact.get("sent", 0),
                "deduped": compact.get("deduped_or_skipped", 0),
                "skipped": compact.get("deduped_or_skipped", 0),
                "failed": compact.get("failed", 0),
                "compact": compact,
            })
            return 0 if status == 200 else 5
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        event = {
            "ok": False,
            "event": "CRON_TICK_HTTP_ERROR",
            "status": status,
            "target": safe_target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        }
        if status == 403:
            event["error"] = "AUTOMATION_SECRET_INVALID"
            event["message"] = "AUTOMATION_SECRET incorrecto o no coincide con el Web Service."
            print_event(event)
            return 3
        print_event(event)
        return 5
    except Exception as exc:
        print_event({
            "ok": False,
            "event": "CRON_TICK_NETWORK_ERROR",
            "error": type(exc).__name__,
            "message": str(exc),
            "target": safe_target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
