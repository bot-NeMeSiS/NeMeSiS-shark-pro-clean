from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "NeMeSiS_SHARK_PRO_V852_REAL_VIDEO_PRODUCT_PERFECTION_LIVE_PICKS_VISUAL_QA_FINAL_RENDER_READY.zip"
BAD_PARTS = {".git", ".venv", "venv", "env", "__pycache__", "release_output"}
BAD_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".log", ".mp4", ".mov", ".avi", ".zip"}


def main():
    zip_path = ROOT / "release_output" / ZIP_NAME
    assert zip_path.exists(), zip_path
    bad = []
    with ZipFile(zip_path) as zf:
        for name in zf.namelist():
            p = Path(name)
            if set(p.parts) & BAD_PARTS or p.suffix.lower() in BAD_SUFFIXES:
                bad.append(name)
    assert not bad, "\n".join(bad[:50])
    print("V852 release cleanliness OK")


if __name__ == "__main__":
    main()
