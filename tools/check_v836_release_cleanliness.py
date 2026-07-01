#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "release_output", "releases"}
FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip", ".mp4", ".mov", ".avi", ".mkv")


def latest_zip() -> Path | None:
    candidates = sorted((ROOT / "release_output").glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    candidates += sorted((ROOT.parent / "releases").glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True) if (ROOT.parent / "releases").exists() else []
    return candidates[0] if candidates else None


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_zip()
    if not target or not target.exists():
        print(json.dumps({"ok": False, "error": "zip_not_found"}, ensure_ascii=False, indent=2))
        return 1
    bad = []
    with zipfile.ZipFile(target) as zf:
        for name in zf.namelist():
            parts = Path(name).parts
            lower = name.lower()
            if any(part in FORBIDDEN_PARTS for part in parts) or lower.endswith(FORBIDDEN_SUFFIXES):
                bad.append(name)
    print(json.dumps({"ok": not bad, "zip": str(target), "forbidden_count": len(bad), "sample": bad[:20]}, ensure_ascii=False, indent=2))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
