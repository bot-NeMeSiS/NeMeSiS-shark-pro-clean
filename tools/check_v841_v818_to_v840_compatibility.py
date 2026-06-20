from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str((ROOT / "data" / "v841_compat.db").resolve()))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v841-secret")

import app as nemesis  # noqa: E402

client = nemesis.app.test_client()
runtime = client.get("/api/runtime-version").get_json(silent=True) or {}
required = [
    "has_v818_automation",
    "has_v819_dedup",
    "has_v820_crests",
    "has_v821_hotfix",
    "has_v822_stability",
    "has_v825_shark_identity",
    "has_v830_bottom_nav_fix",
    "has_v838_full_product_architecture",
    "has_v839_real_chatgpt_review",
    "has_v840_pc_video_fix",
]
missing = [flag for flag in required if not runtime.get(flag)]
no_secret = client.get("/api/automation/master-tick?dry_run=1")
health = client.get("/api/automation/health-check?secret=codex-v841-secret")

payload = {
    "ok": not missing and no_secret.status_code == 403 and health.status_code == 200,
    "missing_flags": missing,
    "master_tick_without_secret": no_secret.status_code,
    "health_check_with_secret": health.status_code,
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
