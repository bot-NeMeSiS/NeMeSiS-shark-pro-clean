#!/usr/bin/env python3
"""Protected Render Cron runner for the sports-only synchronization cycle."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ENDPOINT = "/api/automation/sports/sync"


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def print_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def compact_response(body: str) -> dict:
    try:
        data = json.loads(body or "{}")
    except (TypeError, ValueError):
        return {"ok": False, "status": "INVALID_JSON_RESPONSE"}
    return {
        "ok": bool(data.get("ok")),
        "status": data.get("status") or "UNKNOWN",
        "processed": int(data.get("processed") or 0),
        "matches_synced": int(data.get("matches_synced") or 0),
        "live_synced": int(data.get("live_synced") or 0),
        "external_calls": int(data.get("external_calls") or 0),
        "live_refresh_required": bool(data.get("live_refresh_required")),
        "next_action": data.get("next_action") or "review_runtime",
        "errors_count": int(data.get("errors_count") or 0),
        "no_telegram": data.get("no_telegram") is True,
        "no_payments": data.get("no_payments") is True,
        "no_fake_data": data.get("no_fake_data") is True,
    }


def main() -> int:
    base_url = (os.environ.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    secret = (os.environ.get("AUTOMATION_SECRET") or "").strip()
    utc_now, madrid_now = now_labels()
    if not base_url:
        print_event({
            "ok": False,
            "event": "SPORTS_SYNC_CONFIG_ERROR",
            "error": "MISSING_PUBLIC_BASE_URL",
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 2
    if not secret:
        print_event({
            "ok": False,
            "event": "SPORTS_SYNC_CONFIG_ERROR",
            "error": "MISSING_AUTOMATION_SECRET",
            "secret_status": "MISSING",
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 2

    query = urllib.parse.urlencode({"runner": "render_cron"})
    target = f"{base_url}{ENDPOINT}?{query}"
    print_event({
        "ok": True,
        "event": "SPORTS_SYNC_START",
        "target": target,
        "secret_status": "PRESENT_MASKED",
        "utc_now": utc_now,
        "madrid_now": madrid_now,
    })
    request = urllib.request.Request(
        target,
        headers={
            "User-Agent": "NeMeSiS-SHARK-PRO-Sports-Cron/V937",
            "X-NeMeSiS-Cron-Runner": "render-cron",
            "X-Automation-Secret": secret,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            status = int(response.status)
            compact = compact_response(response.read(24000).decode("utf-8", errors="replace"))
            print_event({
                "ok": status == 200 and compact.get("ok") is True,
                "event": "SPORTS_SYNC_RESPONSE",
                "http_status": status,
                "target": target,
                "utc_now": utc_now,
                "madrid_now": madrid_now,
                "result": compact,
            })
            return 0 if status == 200 and compact.get("ok") is True else 5
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        print_event({
            "ok": False,
            "event": "SPORTS_SYNC_HTTP_ERROR",
            "http_status": status,
            "error": "AUTOMATION_SECRET_REJECTED" if status == 403 else "HTTP_ERROR",
            "target": target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 3 if status == 403 else 5
    except Exception as exc:
        print_event({
            "ok": False,
            "event": "SPORTS_SYNC_NETWORK_ERROR",
            "error": type(exc).__name__,
            "target": target,
            "utc_now": utc_now,
            "madrid_now": madrid_now,
        })
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
