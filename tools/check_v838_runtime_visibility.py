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

os.environ.setdefault("DB_PATH", str(ROOT / "data" / "v838_check_runtime.db"))
os.environ.setdefault("AUTOMATION_SECRET", "codex-v838-secret")
import app as nemesis
client = nemesis.app.test_client()
r = client.get("/api/runtime-version")
data = r.get_json() or {}
missing = [k for k in ["has_v838_shell","has_v838_css","has_v838_full_product_architecture","has_v837_reference_photo_qa","has_v818_automation"] if not data.get(k)]
ok({"ok": r.status_code == 200 and data.get("app_version") == VERSION and data.get("version_txt") == VERSION and not missing, "status": r.status_code, "version": data.get("app_version"), "missing": missing})
