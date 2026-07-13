#!/usr/bin/env python3
"""Render Cron runner for NeMeSiS SHARK PRO highlights/results sync.

Command for Render Cron:
    python tools/render_cron_highlights_sync.py

Environment required:
    PUBLIC_BASE_URL=https://your-app.onrender.com
    AUTOMATION_SECRET=<same secret as Web Service>

Optional:
    HIGHLIGHTS_DAYS_BACK=7
    HIGHLIGHTS_LIMIT=300
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

ENDPOINT = "/api/automation/highlights/sync"


def now_labels() -> tuple[str, str]:
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def target_url(base_url: str) -> str:
    query = urllib.parse.urlencode({
        "days_back": os.environ.get("HIGHLIGHTS_DAYS_BACK", "7"),
        "limit": os.environ.get("HIGHLIGHTS_LIMIT", "300"),
        "runner": "render_cron_highlights",
    })
    return f"{base_url.rstrip('/')}{ENDPOINT}?{query}"


def safe_url(base_url: str) -> str:
    return target_url(base_url)


def print_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main() -> int:
    base_url = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    secret = (os.environ.get("AUTOMATION_SECRET") or "").strip()
    utc_now, madrid_now = now_labels()
    if not base_url:
        print_event({"ok": False, "error": "MISSING_PUBLIC_BASE_URL", "utc_now": utc_now, "madrid_now": madrid_now})
        return 2
    if not secret:
        print_event({"ok": False, "error": "MISSING_AUTOMATION_SECRET", "target": safe_url(base_url), "utc_now": utc_now, "madrid_now": madrid_now})
        return 2
    url = target_url(base_url)
    safe = safe_url(base_url)
    print_event({"ok": True, "event": "HIGHLIGHTS_SYNC_START", "target": safe, "utc_now": utc_now, "madrid_now": madrid_now})
    req = urllib.request.Request(url, headers={
        "User-Agent": "NeMeSiS-SHARK-PRO-Highlights-Cron/769",
        "X-NeMeSiS-Cron-Runner": "render-cron-highlights",
        "X-Automation-Secret": secret,
        "Accept": "application/json,text/plain,*/*",
    }, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            body = res.read(24000).decode("utf-8", errors="replace")
            print_event({"ok": int(res.status) == 200, "event": "HIGHLIGHTS_SYNC_RESPONSE", "status": int(res.status), "target": safe, "body": body, "utc_now": utc_now, "madrid_now": madrid_now})
            return 0 if int(res.status) == 200 else 5
    except urllib.error.HTTPError as exc:
        body = exc.read(12000).decode("utf-8", errors="replace") if exc.fp else ""
        status = int(exc.code)
        print_event({"ok": False, "event": "HIGHLIGHTS_SYNC_HTTP_ERROR", "status": status, "target": safe, "body": body, "utc_now": utc_now, "madrid_now": madrid_now})
        return 3 if status == 403 else 5
    except Exception as exc:
        print_event({"ok": False, "event": "HIGHLIGHTS_SYNC_NETWORK_ERROR", "error": type(exc).__name__, "message": str(exc), "target": safe, "utc_now": utc_now, "madrid_now": madrid_now})
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
