from pathlib import Path
import json, os, sys, re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V838_FULL_PRODUCT_ARCHITECTURE_FINAL_REVIEW_AND_COMPLETION"
def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
def ok(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("ok") else 1)

os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v838_compat.db"))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v838-secret")
import app as nemesis
c = nemesis.app.test_client()
rv = c.get("/api/runtime-version").get_json() or {}
required_flags = ["has_v818_automation","has_v819_dedup","has_v820_crests","has_v821_hotfix","has_v822_stability","has_v825_shark_identity","has_v826_full_screen","has_v827_design_system","has_v830_bottom_nav_fix","has_v832_visual_workflow","has_v833_visual_completion","has_v836_autonomous_qa","has_v837_reference_photo_qa"]
missing = [f for f in required_flags if not rv.get(f)]
health = c.get("/api/automation/health-check?secret=codex-v838-secret")
ok({"ok": not missing and health.status_code == 200, "missing": missing, "health": health.status_code})
