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

import zipfile
zip_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
forbidden_tokens = [".git/", ".venv/", "venv/", "__pycache__/", ".pytest_cache/", "release_output/", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".env"]
with zipfile.ZipFile(zip_arg) as z:
    names = z.namelist()
forbidden = []
for n in names:
    low = n.lower()
    if low.endswith('.zip') or any(tok in low for tok in forbidden_tokens):
        if low not in ['.env.example', '.env.render.clean']:
            forbidden.append(n)
ok({"ok": not forbidden, "zip": str(zip_arg), "forbidden_count": len(forbidden), "sample": forbidden[:20]})
