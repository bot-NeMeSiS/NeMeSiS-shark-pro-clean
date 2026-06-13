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
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ENDPOINT = "/api/automation/telegram/tick"


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def mask_secret(secret: str) -> str:
    if not secret:
        return "<missing>"
    tail = secret[-4:] if len(secret) >= 4 else "****"
    return f"***{tail}"


def masked_url(base_url: str, secret: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}{ENDPOINT}?secret={urllib.parse.quote(mask_secret(secret), safe='')}"


def target_url(base_url: str, secret: str) -> str:
    base = base_url.rstrip("/")
    query = urllib.parse.urlencode({"secret": secret})
    return f"{base}{ENDPOINT}?{query}"


def print_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


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
            "target": masked_url(public_base_url, automation_secret),
        })
        return 2

    url = target_url(public_base_url, automation_secret)
    safe_target = masked_url(public_base_url, automation_secret)
    print_event({
        "ok": True,
        "event": "CRON_TICK_START",
        "target": safe_target,
        "utc_now": utc_now,
        "madrid_now": madrid_now,
    })

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NeMeSiS-SHARK-PRO-Render-Cron/749B",
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            status = int(response.status)
            body_bytes = response.read(20000)
            body = body_bytes.decode("utf-8", errors="replace")
            print_event({
                "ok": status == 200,
                "event": "CRON_TICK_RESPONSE",
                "status": status,
                "target": safe_target,
                "utc_now": utc_now,
                "madrid_now": madrid_now,
                "body": body,
            })
            return 0 if status == 200 else 5
    except urllib.error.HTTPError as exc:
        body = exc.read(12000).decode("utf-8", errors="replace") if exc.fp else ""
        status = int(exc.code)
        event = {
            "ok": False,
            "event": "CRON_TICK_HTTP_ERROR",
            "status": status,
            "target": safe_target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
            "body": body,
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
