import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("release_output/NeMeSiS_SHARK_PRO_V844_TELEGRAM_TOP_PICK_QUALITY_CARDS_FILTER_FINAL_RENDER_READY.zip")
forbidden = (".git/", ".venv/", "venv/", "__pycache__/", ".pytest_cache/", "release_output/")
bad_suffix = (".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".mov")
findings = []
with zipfile.ZipFile(zip_path) as zf:
    for name in zf.namelist():
        low = name.lower()
        if any(part in low for part in forbidden) or low.endswith(bad_suffix):
            findings.append(name)
payload = {"ok": not findings, "zip": str(zip_path), "forbidden_count": len(findings), "findings": findings[:30]}
print(payload)
raise SystemExit(0 if payload["ok"] else 1)
