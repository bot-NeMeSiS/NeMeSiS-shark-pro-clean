from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

VERSION = "V842_SPANISH_TEXT_LOGOS_BRAND_IDENTITY_FINAL_QA"
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v842_runtime.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v842-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
response = client.get("/api/runtime-version")
data = response.get_json(silent=True) or {}

required_flags = [
    "has_v842_spanish_text_logo_qa",
    "has_v841_product_team_polish",
    "has_v840_pc_video_fix",
    "has_v839_real_chatgpt_review",
    "has_v838_full_product_architecture",
    "has_v837_reference_photo_qa",
    "has_v836_autonomous_qa",
    "has_v830_bottom_nav_fix",
    "has_v825_shark_identity",
    "has_v818_automation",
]

missing = [flag for flag in required_flags if not data.get(flag)]
payload = {
    "ok": response.status_code == 200
    and data.get("app_version") == VERSION
    and data.get("version_txt") == VERSION
    and not missing,
    "status": response.status_code,
    "app_version": data.get("app_version"),
    "version_txt": data.get("version_txt"),
    "missing_flags": missing,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
