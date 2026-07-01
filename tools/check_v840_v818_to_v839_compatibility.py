from pathlib import Path
import json, os, sys, re
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V840_PC_VIDEO_LAYOUT_TEXT_NAV_FIX_FINAL"
def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
def ok(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload.get("ok") else 1)

os.environ.setdefault('DB_PATH', str(ROOT/'data'/'v840_compat.db'))
os.environ.setdefault('AUTOMATION_SECRET','codex-v840-secret')
import app as nemesis
c=nemesis.app.test_client(); data=c.get('/api/runtime-version').get_json() or {}
required=['has_v818_automation','has_v819_dedup','has_v820_crests','has_v821_hotfix','has_v822_stability','has_v825_shark_identity','has_v830_bottom_nav_fix','has_v838_full_product_architecture','has_v839_real_chatgpt_review']
missing=[k for k in required if not data.get(k)]
mt=c.get('/api/automation/master-tick?dry_run=1').status_code
health=c.get('/api/automation/health-check?secret=codex-v840-secret').status_code
ok({'ok':not missing and mt==403 and health==200,'missing':missing,'master_tick_no_secret':mt,'health':health})
