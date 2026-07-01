import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v844_runtime.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v844-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
data = client.get("/api/runtime-version").get_json() or {}
required = [
    "has_v844_telegram_quality_filter",
    "has_v843_commercial_product_review",
    "has_v842_spanish_text_logo_qa",
    "has_v841_product_team_polish",
    "has_v840_pc_video_fix",
    "has_v818_automation",
]
missing = [key for key in required if not data.get(key)]
ok = data.get("app_version") == "V844_TELEGRAM_TOP_PICK_QUALITY_CARDS_FILTER_FINAL" and not missing
print({"ok": ok, "app_version": data.get("app_version"), "version_txt": data.get("version_txt"), "missing": missing})
raise SystemExit(0 if ok else 1)
