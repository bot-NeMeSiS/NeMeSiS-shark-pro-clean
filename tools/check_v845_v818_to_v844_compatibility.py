from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / "app.py").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
required = [
    "/api/automation/master-tick",
    "/api/automation/health-check",
    "telegram_quality_filter_engine",
    "V844 TELEGRAM TOP PICK QUALITY CARDS FILTER START",
    "data-v830-shell",
    "V842 SPANISH TEXT LOGOS BRAND IDENTITY FINAL QA START",
    "V843 PRODUCT TEAM COMMERCIAL READY FINAL REVIEW START",
]
missing = [item for item in required if item not in app + css + base]
print({"ok": not missing, "missing": missing})
raise SystemExit(0 if not missing else 1)
