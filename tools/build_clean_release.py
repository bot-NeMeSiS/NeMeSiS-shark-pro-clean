#!/usr/bin/env python3
"""Build a clean Render-ready release ZIP for NeMeSiS SHARK PRO."""
from __future__ import annotations

import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION.txt"
VERSION = VERSION_FILE.read_text(encoding="utf-8-sig").strip() if VERSION_FILE.exists() else "DEV"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
OUT = ROOT / ZIP_NAME
MANIFEST_PATH = ROOT / "RELEASE_MANIFEST_V723.json"

INCLUDE_TOP_LEVEL_DIRS = {
    "blueprints",
    "docs",
    "engines",
    "services",
    "static",
    "templates",
    "tests",
    "tools",
    "reports",
}
INCLUDE_TOP_LEVEL_FILES = {
    ".env.example",
    ".env.render.clean",
    ".gitignore",
    "app.py",
    "database_manager.py",
    "Procfile",
    "pytest.ini",
    "README_MASTER.md",
    "render.yaml",
    "requirements-dev.txt",
    "requirements.txt",
    "runtime.txt",
    "VERSION.txt",
    "CODEX_DAILY_AUTOMATION_GUIDE.md",
    "CHATGPT_CONTINUATION_REPORT.md",
    "V723_CODEX_AUTOMATION_TOTAL_PURGE_RELEASE_SYSTEM_REPORT.md",
    "V723_TOTAL_PURGE_AUDIT_REPORT.md",
    "RELEASE_MANIFEST_V723.json",
}
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "release",
    "releases",
    "tmp",
    "temp",
    "backups",
    "logs",
    "v636work",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-wal",
    ".db-shm",
    ".sqlite-wal",
    ".sqlite-shm",
    ".log",
    ".zip",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
SECRET_NAME_MARKERS = ("secret", "token", "private_key", "id_rsa")


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unavailable"


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if not parts:
        return False
    rel_posix = rel.as_posix()
    if parts[0] == "reports":
        return rel_posix == "reports/CODEX_DAILY_PROMPT_CURRENT.txt"
    if any(part in EXCLUDE_DIRS for part in parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    lower_name = path.name.lower()
    lower_rel = rel.as_posix().lower()
    if any(marker in lower_name for marker in SECRET_NAME_MARKERS) and path.name not in {
        ".env.example",
        ".env.render.clean",
    }:
        return False
    if any(lower_name.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return False
    if parts[0] in INCLUDE_TOP_LEVEL_DIRS:
        return True
    return len(parts) == 1 and path.name in INCLUDE_TOP_LEVEL_FILES


def collect_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and include(p))


def build_manifest(files: list[Path]) -> dict:
    return {
        "version": VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "zip": ZIP_NAME,
        "zip_path": str(OUT),
        "files": len(files),
        "git_commit": git_commit(),
        "included_top_level_dirs": sorted(INCLUDE_TOP_LEVEL_DIRS),
        "included_top_level_files": sorted(INCLUDE_TOP_LEVEL_FILES),
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "excluded_suffixes": sorted(EXCLUDE_SUFFIXES),
        "security_policy": "No incluye .git, .venv, caches, bases de datos locales, logs, ZIPs internos ni secretos reales.",
        "render_ready": True,
    }


def main() -> int:
    files = collect_files()
    manifest = build_manifest(files)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = collect_files()
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
    manifest = build_manifest(files)
    manifest["zip_size_bytes"] = OUT.stat().st_size
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
