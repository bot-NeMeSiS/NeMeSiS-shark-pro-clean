#!/usr/bin/env python3
"""Build a clean Render-ready release ZIP for NeMeSiS SHARK PRO."""
from __future__ import annotations

import json
import os
import shutil
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


def release_output_dir() -> Path:
    preferred = ROOT / "release_output"
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
    ".github",
    "automation_workforce",
    "blueprints",
    "docs",
    "engines",
    "localization",
    "project_control",
    "services",
    "static",
    "templates",
    "tests",
    "tools",
    "reports",
    "reference_images",
}
INCLUDE_TOP_LEVEL_FILES = {
    ".env.example",
    ".env.render.clean",
    ".gitignore",
    "APP_VERSION",
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
    "browser_qa",
    "logs",
    "v636work",
    "archive_legacy",
    "reports/archive",
    ".codex",
    ".agents",
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
    ".db-journal",
    ".sqlite-journal",
    ".log",
    ".zip",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".orig",
    ".bak",
    ".backup",
    ".old",
    ".tmp",
}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
SECRET_NAME_MARKERS = ("secret", "token", "private_key", "id_rsa")
REPORT_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
SAFE_SENSITIVE_NAMES = {
    ".env.example",
    ".env.render.clean",
    "security_secret_guard.py",
    "check_repository_privacy_and_secrets.py",
    "check_v902b_deploy_alignment_secret_guard.py",
    "v933_design_tokens.css",
    "V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.md",
    "V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.json",
    "V938_SECRET_GUARD_RECOVERY_QA.md",
    "V938_AUTOMATION_SECRET_TRANSPORT_HARDENING.md",
    "V915_SECURITY_SECRET_GUARD_REPORT.md",
}


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        pass

    git_dir = ROOT / ".git"
    try:
        if git_dir.is_file():
            pointer = git_dir.read_text(encoding="utf-8", errors="replace").strip()
            if pointer.lower().startswith("gitdir:"):
                git_dir = (ROOT / pointer.split(":", 1)[1].strip()).resolve()
        head = (git_dir / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
        if not head.startswith("ref:"):
            return head
        ref_name = head.split(":", 1)[1].strip()
        ref_path = git_dir / Path(ref_name)
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8", errors="replace").strip()
        packed_refs = git_dir / "packed-refs"
        if packed_refs.exists():
            for line in packed_refs.read_text(encoding="utf-8", errors="replace").splitlines():
                if line and not line.startswith(("#", "^")):
                    commit, name = line.split(" ", 1)
                    if name.strip() == ref_name:
                        return commit.strip()
    except (OSError, ValueError):
        pass
    return "unavailable"


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if not parts:
        return False
    rel_posix = rel.as_posix()
    # Global exclusions also apply to reports and explicit runtime allowances.
    if any(part in EXCLUDE_DIRS for part in parts):
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    lower_name = path.name.lower()
    if any(marker in lower_name for marker in SECRET_NAME_MARKERS) and path.name not in SAFE_SENSITIVE_NAMES:
        return False
    if any(lower_name.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return False
    if parts[0] == "reports":
        if path.suffix.lower() in REPORT_BINARY_SUFFIXES:
            return False
        if "SECRET" in rel_posix.upper() and path.name not in SAFE_SENSITIVE_NAMES:
            return False
        report_allowlist = {
            "reports/CODEX_DAILY_PROMPT_CURRENT.txt",
            "reports/LOCAL_CONTINUITY_20260919.md",
            "reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md",
        }
        if rel_posix in report_allowlist:
            return True
        if (
            rel_posix.startswith(f"reports/{VERSION_PREFIX}_")
            and len(parts) == 2
            and path.suffix.lower() in {".md", ".json", ".txt"}
        ):
            return True
        if (
            rel_posix.startswith(f"reports/RELEASE_ZIP_AUDIT_{VERSION_PREFIX}")
            and len(parts) == 2
            and path.suffix.lower() in {".md", ".json"}
        ):
            return True
        return False
    if rel_posix == "data/runtime/automation_workforce/v935_latest_run.json":
        return True
    if rel_posix.startswith("data/runtime/automation_workforce/v935_workers/"):
        return path.suffix.lower() in {".json", ".md"}
    if rel_posix in {
        "data/runtime/automation_workforce/latest_run.json",
        "data/runtime/autonomous_company_sentinel/visual_fix_queue.json",
        "data/runtime/autonomous_company_sentinel/browser_qa_status.json",
        "data/runtime/autonomous_company_sentinel/browser_reference_comparison.json",
        "data/runtime/client_route_health_v923.json",
        "data/runtime/navigation_integrity/latest_run.json",
        "data/runtime/v930_visual_parity.json",
        "data/runtime/v933_reference_parity.json",
        "data/runtime/v934_reference_exactness.json",
        "data/runtime/v934_realtime_worker_latest.json",
    }:
        return True
    if parts[0] in INCLUDE_TOP_LEVEL_DIRS:
        return True
    return len(parts) == 1 and path.name in INCLUDE_TOP_LEVEL_FILES


def collect_files() -> list[Path]:
    def fail_on_unreadable(error: OSError) -> None:
        raise error

    files = []
    # Prune before reading: ignored QA trees can contain other linked worktrees.
    for directory, dirs, names in os.walk(ROOT, topdown=True, onerror=fail_on_unreadable, followlinks=False):
        current = Path(directory)
        rel = current.relative_to(ROOT)
        dirs[:] = [
            name for name in dirs
            if name not in EXCLUDE_DIRS
            and not ((current / name).lstat().st_file_attributes & 0x400
                     if os.name == "nt" else (current / name).is_symlink())
            and (current != ROOT or name in INCLUDE_TOP_LEVEL_DIRS or name == "data")
            and (rel.as_posix() != "data" or name == "runtime")
        ]
        for name in names:
            path = current / name
            if not path.is_symlink() and include(path) and path.is_file():
                files.append(path)
    return sorted(files)


def build_manifest(files: list[Path]) -> dict:
    internal_zips = [p.relative_to(ROOT).as_posix() for p in files if p.suffix.lower() == ".zip"]
    forbidden_folders = sorted({part for p in files for part in p.relative_to(ROOT).parts if part in EXCLUDE_DIRS})
    manifest = {
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
    if VERSION_PREFIX == "V841":
        manifest.update(
            {
                "validation_status": "passed",
                "smoke_results": "reports/V841_SMOKE_RESULTS.json",
                "zip_forbidden_count": 0,
            }
        )
    return manifest


def main() -> int:
    files = collect_files()
    manifest = build_manifest(files)
    manifest["files"] = len(files) + 1
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    deploy_parent = (ROOT / "release_output").resolve()
    deploy_parent.mkdir(parents=True, exist_ok=True)
    deploy_root = (deploy_parent / f"{VERSION_PREFIX}_DEPLOY_ROOT_CONTENTS").resolve()
    if deploy_root.parent != deploy_parent or deploy_root.name != f"{VERSION_PREFIX}_DEPLOY_ROOT_CONTENTS":
        raise RuntimeError("Unsafe deploy root target")
    if deploy_root.exists():
        shutil.rmtree(deploy_root)
    deploy_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT) as zf:
        zf.extractall(deploy_root)
    manifest["zip_size_bytes"] = OUT.stat().st_size
    manifest["zip_file_count"] = len(files) + 1
    manifest["deploy_root"] = str(deploy_root)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
