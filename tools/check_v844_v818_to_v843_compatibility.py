from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / "app.py").read_text(encoding="utf-8", errors="ignore")
base = (root / "templates" / "base.html").read_text(encoding="utf-8", errors="ignore")
required = [
    "/api/automation/master-tick",
    "daily_automation_engine",
    "data-v843-shell",
    "data-v842-shell",
    "data-v830-shell",
    "telegram_scheduler_delivery",
    "process_premium_telegram_queue",
]
missing = [token for token in required if token not in app + base]
print({"ok": not missing, "missing": missing})
raise SystemExit(0 if not missing else 1)
