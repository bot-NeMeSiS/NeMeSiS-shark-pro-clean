from pathlib import Path
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
zip_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "release_output" / "NeMeSiS_SHARK_PRO_V841_REFERENCE_PRODUCT_TEAM_FINAL_POLISH_AND_SOURCE_SANITY_RENDER_READY.zip"
if not zip_path.is_absolute():
    zip_path = ROOT / zip_path

forbidden_tokens = [
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    "release_output/",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-wal",
    ".db-shm",
    ".log",
    ".zip",
    ".mp4",
    ".env",
]

hits = []
with zipfile.ZipFile(zip_path) as zf:
    names = zf.namelist()
    for name in names:
        lower = name.lower()
        if lower.endswith(".env.example") or lower.endswith(".env.render.clean"):
            continue
        for token in forbidden_tokens:
            if token in lower or lower.endswith(token):
                hits.append(name)
                break

payload = {
    "ok": not hits,
    "zip": str(zip_path),
    "file_count": len(names),
    "forbidden_count": len(hits),
    "forbidden_sample": hits[:20],
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
