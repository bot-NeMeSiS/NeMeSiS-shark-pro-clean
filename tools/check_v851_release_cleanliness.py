from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = "NeMeSiS_SHARK_PRO_V851_LOGO_BRAND_HEADER_MOBILE_PC_FIX_RENDER_READY.zip"
FORBIDDEN_PARTS = {".git", ".venv", "venv", "env", "__pycache__", "release_output"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".log", ".mp4", ".mov", ".avi"}


def main():
    zip_path = ROOT / "release_output" / ZIP_NAME
    assert zip_path.exists(), f"missing {zip_path}"
    bad = []
    with ZipFile(zip_path) as zf:
        names = zf.namelist()
        for name in names:
            parts = set(Path(name).parts)
            suffix = Path(name).suffix.lower()
            if parts & FORBIDDEN_PARTS or suffix in FORBIDDEN_SUFFIXES:
                bad.append(name)
            if name.lower().endswith(".zip"):
                bad.append(name)
    assert not bad, "\n".join(bad[:50])
    print("V851 release cleanliness OK")


if __name__ == "__main__":
    main()
