#!/usr/bin/env python3
"""Static security and polish checks for V729."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
APP = ROOT / "app.py"
BASE = ROOT / "templates" / "base.html"


def main() -> int:
    app_text = APP.read_text(encoding="utf-8", errors="replace")
    base_text = BASE.read_text(encoding="utf-8", errors="replace") if BASE.exists() else ""
    root_html = sorted(p.name for p in ROOT.glob("*.html"))
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip() if (ROOT / "VERSION.txt").exists() else ""
    version_ok = version.startswith(("V729_", "V730_", "V731_", "V732_", "V733_", "V734_", "V735_", "V736_", "V737_", "V738_", "V739_", "V740_", "V741_", "V742_", "V743_", "V744_", "V745_", "V746_", "V747_"))
    checks = {
        "version_v729_or_later": version_ok,
        "secure_secret_key_used": "app.secret_key = secure_secret_key()" in app_text,
        "no_random_secret_fallback": "secrets.token_hex(32)" not in app_text.split("app = Flask", 1)[-1].split("SEED_LOCK", 1)[0],
        "csrf_helpers_imported": "generate_csrf_token" in app_text and "validate_csrf" in app_text,
        "csrf_enforced": "def enforce_security_guards" in app_text and "validate_csrf(session" in app_text,
        "csrf_meta_present": 'meta name="csrf-token"' in base_text,
        "post_forms_auto_injected": "apply_security_headers_and_csrf" in app_text and "method=" in app_text,
        "rate_limit_present": "rate_limit_status" in app_text and "security_rate_limit_for_request" in app_text,
        "login_events_recorded": "security_event_for_auth(\"login_attempt\"" in app_text,
        "registration_events_recorded": "security_event_for_auth(\"registration_attempt\"" in app_text,
        "security_headers_present": "X-Content-Type-Options" in app_text and "X-Frame-Options" in app_text,
        "root_html_duplicates": len(root_html) == 0,
    }
    report = {
        "ok": all(checks.values()),
        "checks": checks,
        "root_html_files": root_html,
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "V729_SECURITY_CHECK.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    lines = ["# V729+ Security Check", "", f"- Versión: `{version}`", f"- Resultado: {'OK' if report['ok'] else 'FAIL'}", "", "## Checks"]
    for name, ok in checks.items():
        lines.append(f"- {'✅' if ok else '❌'} `{name}`")
    if root_html:
        lines += ["", "## HTML en raíz", *[f"- `{name}`" for name in root_html]]
    (REPORTS / "V729_SECURITY_CHECK.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
