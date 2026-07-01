from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
required_templates = [
    "home.html",
    "client_login.html",
    "register.html",
    "client_app_center.html",
    "calendar.html",
    "live.html",
    "picks.html",
    "match_detail.html",
    "shark.html",
    "profile.html",
    "telegram.html",
    "support.html",
    "favorites.html",
    "track_record.html",
    "combis.html",
    "betting_markets.html",
    "highlights.html",
    "admin_dashboard.html",
    "admin_daily_automation.html",
    "admin_automation_center.html",
    "admin_telegram_command_center.html",
    "admin_data_center.html",
    "admin_users.html",
    "admin_memberships.html",
    "admin_payments.html",
]

missing = [name for name in required_templates if not (ROOT / "templates" / name).exists()]
logo_refs = 0
for path in (ROOT / "templates").glob("*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "shark-logo.svg" in text or "NeMeSiS SHARK PRO" in text:
        logo_refs += 1

payload = {"ok": not missing and logo_refs >= 2, "missing": missing, "logo_refs": logo_refs}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
