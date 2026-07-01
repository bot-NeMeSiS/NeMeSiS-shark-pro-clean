from pathlib import Path
import sys
import zipfile
ROOT = Path(__file__).resolve().parents[1]
version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
zip_path = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{version}_RENDER_READY.zip"
if len(sys.argv) > 1:
    zip_path = Path(sys.argv[1])
forbidden = [".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", ".db", ".sqlite", ".log", ".zip", ".mp4", ".mov"]
hits = []
if zip_path.exists():
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if any(token in name.lower() for token in forbidden):
                hits.append(name)
print({"zip": str(zip_path), "exists": zip_path.exists(), "forbidden_count": len(hits), "sample": hits[:10]})
raise SystemExit(1 if hits or not zip_path.exists() else 0)
