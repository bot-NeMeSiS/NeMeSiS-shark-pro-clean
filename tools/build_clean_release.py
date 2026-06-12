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
VERSION_PREFIX = VERSION.split("_", 1)[0] if VERSION else "DEV"
MANIFEST_NAME = f"RELEASE_MANIFEST_{VERSION_PREFIX}.json"
MANIFEST_PATH = ROOT / MANIFEST_NAME


def release_output_dir() -> Path:
    preferred = ROOT.parent / "releases"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".codex_release_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback = ROOT / "release_output"
        fallback.mkdir(exist_ok=True)
        return fallback


OUT_DIR = release_output_dir()
OUT = OUT_DIR / ZIP_NAME

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
    "V724_SUPREME_CLIENT_VISUAL_EXPERIENCE_PRO_REPORT.md",
    "CLIENT_VISUAL_SYSTEM_V724.md",
    "V725_MADRID_TIME_RELEASE_WORKFLOW_AUTOMATION_FIX_REPORT.md",
    "MADRID_TIME_AUDIT_V725.md",
    "V726_TOTAL_PROJECT_CLEANUP_LIVE_EXPERIENCE_ORGANIZATION_REPORT.md",
    "V726_PROJECT_TREE_AUDIT.md",
    "V726_PURGE_REPORT.md",
    "V726_LIVE_EXPERIENCE_QA_REPORT.md",
    "V727_TELEGRAM_RELIABILITY_COMMAND_CENTER_REPORT.md",
    "TELEGRAM_RELIABILITY_AUDIT_V727.md",
    "TELEGRAM_RUNBOOK_V727.md",
    "V728_FINAL_CLIENT_EXPERIENCE_MADRID_TIME_LIVE_POLISH_REPORT.md",
    "V728_VISUAL_TIME_QA_REPORT.md",
    "RELEASE_MANIFEST_V723.json",
    "RELEASE_MANIFEST_V724.json",
    "RELEASE_MANIFEST_V725.json",
    "RELEASE_MANIFEST_V726.json",
    "RELEASE_MANIFEST_V727.json",
    "RELEASE_MANIFEST_V728.json",
    "V729_SECURITY_STABILITY_VISUAL_QA_FOUNDATION_REPORT.md",
    "V729_SECURITY_AUDIT.md",
    "V729_ROOT_HTML_DUPLICATES_AUDIT.md",
    "RELEASE_MANIFEST_V729.json",
    "V730_ARCHITECTURE_ROUTE_HEALTH_VISUAL_QA_FOUNDATION_REPORT.md",
    "V730_ARCHITECTURE_ROADMAP.md",
    "ROUTE_HEALTH_AUDIT_V730.md",
    "RELEASE_MANIFEST_V730.json",
    "V731_CLIENT_EXPERIENCE_QA_POLISH_FOUNDATION_REPORT.md",
    "V731_CLIENT_EXPERIENCE_QA_REPORT.md",
    "RELEASE_MANIFEST_V731.json",
    "V732_PRODUCTION_READINESS_CONTROL_CENTER_REPORT.md",
    "RELEASE_MANIFEST_V732.json",
    "V733_CLIENT_SUCCESS_ONBOARDING_SUPPORT_POLISH_REPORT.md",
    "RELEASE_MANIFEST_V733.json",
    "V734_PUBLIC_LAUNCH_TRACK_RECORD_PAYMENTS_FOUNDATION_REPORT.md",
    "V734_PUBLIC_LAUNCH_ROADMAP.md",
    "RELEASE_MANIFEST_V734.json",
    "V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION_REPORT.md",
    "V735_GO_LIVE_CHECKLIST.md",
    "RELEASE_MANIFEST_V735.json",
    "V736_GLOBAL_CLIENT_VISUAL_MEMBERSHIP_EXPERIENCE_REPORT.md",
    "V736_VISUAL_SYSTEM_QA_REPORT.md",
    "V737_NATIVE_APP_FEEL_MICROINTERACTIONS_NAVIGATION_POLISH_REPORT.md",
    "V737_APP_FEEL_QA_REPORT.md",
    "V738_FINAL_COMMERCIAL_RELEASE_CANDIDATE_POLISH_REPORT.md",
    "V738_FINAL_RELEASE_QA_REPORT.md",
    "V738_FINAL_RELEASE_CHECKLIST.md",
    "V739_SALE_READY_HOME_DATA_PRODUCTION_FIX_REPORT.md",
    "V739_SELL_READY_VALIDATION_CHECKLIST.md",
    "RELEASE_MANIFEST_V739.json",
    "V740_CLIENT_VISUAL_PICK_ANALYSIS_PERFECTION_REPORT.md",
    "V740_VISUAL_PERFECTION_QA_REPORT.md",
    "V740_VISUAL_CLIENT_SELL_READY_CHECKLIST.md",
    "RELEASE_MANIFEST_V740.json",
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
    "release_output",
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
    if len(parts) == 1 and path.name == MANIFEST_NAME:
        return True
    return len(parts) == 1 and path.name in INCLUDE_TOP_LEVEL_FILES


def collect_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and include(p))


def build_manifest(files: list[Path]) -> dict:
    internal_zips = [p.relative_to(ROOT).as_posix() for p in files if p.suffix.lower() == ".zip"]
    forbidden_folders = sorted({part for p in files for part in p.relative_to(ROOT).parts if part in EXCLUDE_DIRS})
    return {
        "version": VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "zip": ZIP_NAME,
        "zip_path": str(OUT),
        "zip_inside_project_tree": ROOT in OUT.parents,
        "output_dir": str(OUT_DIR),
        "manifest": MANIFEST_NAME,
        "files": len(files),
        "internal_zips": internal_zips,
        "has_internal_zips": bool(internal_zips),
        "forbidden_folders_included": forbidden_folders,
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
    manifest["zip_file_count"] = len(files)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
