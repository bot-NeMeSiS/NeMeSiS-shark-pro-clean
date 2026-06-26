from pathlib import Path
from zipfile import ZipFile

ZIP = Path("release_output/NeMeSiS_SHARK_PRO_V850_LIVE_CRESTS_API_SPORTS_MATCH_DETAIL_FINAL_RENDER_READY.zip")
FORBIDDEN = (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/", ".db", ".sqlite", ".sqlite3", ".log", ".zip", ".mp4", ".mov", ".avi")


def main():
    assert ZIP.exists(), f"No existe {ZIP}"
    with ZipFile(ZIP) as zf:
        names = zf.namelist()
    forbidden = [name for name in names if any(token in name or name.endswith(token) for token in FORBIDDEN)]
    assert not forbidden, forbidden[:20]
    print({"zip": str(ZIP), "forbidden_count": 0, "files": len(names)})


if __name__ == "__main__":
    main()
