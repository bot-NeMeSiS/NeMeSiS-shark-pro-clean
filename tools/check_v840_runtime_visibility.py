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

os.environ.setdefault('DB_PATH', str(ROOT/'data'/'v840_runtime.db'))
os.environ.setdefault('AUTOMATION_SECRET','codex-v840-secret')
import app as nemesis
r=nemesis.app.test_client().get('/api/runtime-version')
data=r.get_json() or {}
required=['has_v840_pc_video_fix','has_v839_real_chatgpt_review','has_v838_full_product_architecture','has_v837_reference_photo_qa','has_v818_automation']
missing=[k for k in required if not data.get(k)]
ok({'ok':r.status_code==200 and data.get('app_version')==VERSION and data.get('version_txt')==VERSION and not missing,'status':r.status_code,'version':data.get('app_version'),'missing':missing})
