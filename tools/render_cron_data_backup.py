#!/usr/bin/env python3
"""Stateless daily Data Vault backup caller for the NeMeSiS web service."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ENDPOINT = "/api/automation/data-backup/run"
TIMEOUT_SECONDS = 90


def now_labels():
    utc_now = datetime.now(timezone.utc)
    madrid_now = utc_now.astimezone(ZoneInfo("Europe/Madrid"))
    return utc_now.isoformat(timespec="seconds"), madrid_now.isoformat(timespec="seconds")


def validated_base_url(value):
    parsed = urllib.parse.urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http","https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("INVALID_PUBLIC_BASE_URL")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def emit(payload):
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def main():
    utc_now, madrid_now = now_labels()
    base_raw = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    secret = (os.environ.get("AUTOMATION_SECRET") or "").strip()
    if not base_raw or not secret:
        emit({"ok":False,"event":"DATA_BACKUP_CONFIG_ERROR","error":"MISSING_PUBLIC_BASE_URL" if not base_raw else "MISSING_AUTOMATION_SECRET","utc_now":utc_now,"madrid_now":madrid_now})
        return 2
    try:
        base = validated_base_url(base_raw)
    except ValueError:
        emit({"ok":False,"event":"DATA_BACKUP_CONFIG_ERROR","error":"INVALID_PUBLIC_BASE_URL","utc_now":utc_now,"madrid_now":madrid_now})
        return 2
    target = base + ENDPOINT
    req = urllib.request.Request(target, data=b"{}", headers={
        "User-Agent":"NeMeSiS-SHARK-PRO-Data-Backup-Cron/V1",
        "X-NeMeSiS-Cron-Runner":"render-cron-backup",
        "X-Automation-Secret":secret,
        "Accept":"application/json",
        "Content-Type":"application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            status=int(response.status)
            try: body=json.loads(response.read(24000).decode("utf-8",errors="replace") or "{}")
            except Exception: body={}
            ok=status==200 and body.get("ok") is not False
            emit({"ok":ok,"event":"DATA_BACKUP_RESPONSE","http_status":status,"backup_created":bool(body.get("backup_created")),"status":str(body.get("status") or ("OK" if ok else "ERROR"))[:80],"utc_now":utc_now,"madrid_now":madrid_now})
            return 0 if ok else 5
    except urllib.error.HTTPError as exc:
        emit({"ok":False,"event":"DATA_BACKUP_HTTP_ERROR","http_status":int(exc.code),"error":"AUTOMATION_SECRET_REJECTED" if int(exc.code)==403 else "HTTP_ERROR","utc_now":utc_now,"madrid_now":madrid_now})
        return 3 if int(exc.code)==403 else 5
    except Exception as exc:
        emit({"ok":False,"event":"DATA_BACKUP_NETWORK_ERROR","error":type(exc).__name__,"utc_now":utc_now,"madrid_now":madrid_now})
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
