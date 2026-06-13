#!/usr/bin/env python3
"""V735 go-live certification static check.

It deliberately avoids starting Flask, external APIs, Telegram or Stripe. It checks
that the V735 operational layer is installed, versioned and safe.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_VERSION = "V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def check() -> dict:
    app = read(ROOT / "app.py")
    css = read(ROOT / "static" / "app.css")
    base = read(ROOT / "templates" / "base.html")
    version_txt = read(ROOT / "VERSION.txt").strip()
    current_version = version_txt or BASE_VERSION
    required_files = [
        "engines/go_live_engine.py",
        "templates/admin_go_live.html",
        "tools/check_v735_go_live.py",
    ]
    required_routes = [
        "/admin/go-live",
        "/admin/public-beta",
        "/admin/launch-certification",
        "/api/admin/go-live",
        "/api/admin/go-live/validation-plan",
    ]
    required_tokens = [
        "go_live_snapshot",
        "production_validation_plan",
        "v735_go_live_context",
        "admin_go_live_page",
        "api_admin_go_live",
    ]
    checks = []
    checks.append({"name": "version_txt", "ok": version_txt in {BASE_VERSION, current_version} and (version_txt.startswith("V735_") or version_txt.startswith("V736_") or version_txt.startswith("V737_") or version_txt.startswith("V738_") or version_txt.startswith("V739_") or version_txt.startswith(("V740_", "V741_", "V742_", "V743_", "V744_", "V745_", "V746_", "V747_", "V748_"))), "value": version_txt})
    checks.append({"name": "app_version", "ok": f'APP_VERSION = "{version_txt}"' in app or f'APP_VERSION = "{BASE_VERSION}"' in app})
    for rel in required_files:
        path = ROOT / rel
        checks.append({"name": f"file:{rel}", "ok": path.exists(), "size": path.stat().st_size if path.exists() else 0})
    for route in required_routes:
        checks.append({"name": f"route:{route}", "ok": route in app})
    for token in required_tokens:
        checks.append({"name": f"token:{token}", "ok": token in app})
    checks.append({"name": "admin_link_base", "ok": "/admin/go-live" in base or "/admin/go-live" in read(ROOT / "templates" / "admin_dashboard.html")})
    checks.append({"name": "css_v735", "ok": "V735 Go Live" in css or "v735" in css.lower()})
    checks.append({"name": "template_no_secret_words", "ok": "TELEGRAM_BOT_TOKEN" not in read(ROOT / "templates" / "admin_go_live.html")})
    checks.append({"name": "cron_exemptions_kept", "ok": "/api/automation/telegram/tick" in app and "/api/automation/daily/run" in app})
    checks.append({"name": "stripe_safe_audit_mode", "ok": "api_payments_stripe_webhook" in app and "record_payment_webhook_event" in app})
    failures = [item for item in checks if not item.get("ok")]
    return {
        "ok": not failures,
        "version": current_version,
        "checks_total": len(checks),
        "failures": failures,
        "checks": checks,
    }


def main() -> int:
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
