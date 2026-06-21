from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V843_PRODUCT_TEAM_COMMERCIAL_READY_FINAL_REVIEW"
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v843_runtime.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v843-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
response = client.get("/api/runtime-version")
data = response.get_json(silent=True) or {}
required = [
    "has_v843_commercial_product_review",
    "has_v842_spanish_text_logo_qa",
    "has_v841_product_team_polish",
    "has_v840_pc_video_fix",
    "has_v818_automation",
]
missing = [flag for flag in required if not data.get(flag)]
payload = {
    "ok": response.status_code == 200 and data.get("app_version") == VERSION and data.get("version_txt") == VERSION and not missing,
    "status": response.status_code,
    "app_version": data.get("app_version"),
    "version_txt": data.get("version_txt"),
    "missing_flags": missing,
    "db_path": data.get("db_path"),
    "automation_secret_configured": data.get("automation_secret_configured"),
    "telegram_configured": data.get("telegram_configured"),
    "api_football_configured": data.get("api_football_configured"),
    "the_odds_configured": data.get("the_odds_configured"),
    "static_app_css_hash": data.get("static_app_css_hash"),
    "static_app_css_size": data.get("static_app_css_size"),
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
