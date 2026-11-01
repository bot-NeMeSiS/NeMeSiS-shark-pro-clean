#!/usr/bin/env python3
"""Operator-only SQLite recovery for issue #327.

This tool is intentionally NOT called by Flask or Render Cron. It must run in
the web service's shell (which owns /data) to avoid the 15-second synchronous
request budget. It never modifies the source database or restores over it.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.data_vault_engine import (  # noqa: E402
    backup_dir,
    connect_readonly,
    create_sqlite_backup,
    validate_backup,
)

MIN_RESERVE = 128 * 1024 * 1024


def emit(data: dict) -> None:
    """Print operational metadata only: no SQL rows, secrets or source paths."""
    print(json.dumps(data, ensure_ascii=True, sort_keys=True), flush=True)


def estimate_bytes(source: Path) -> int:
    with closing(connect_readonly(source)) as connection:
        page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    return page_count * page_size


def storage_probe(directory: Path) -> Path:
    probe = directory
    while not probe.exists():
        if probe.parent == probe:
            raise OSError("no_existing_storage_parent")
        probe = probe.parent
    if not probe.is_dir():
        raise OSError("backup_destination_not_directory")
    return probe


def preflight(source: Path, directory: Path) -> dict:
    if not source.is_file() or source.is_symlink():
        return {"ok": False, "stage": "PREFLIGHT", "code": "SOURCE_UNAVAILABLE"}
    if directory.is_symlink():
        return {"ok": False, "stage": "PREFLIGHT", "code": "DESTINATION_SYMLINK"}
    try:
        expected = estimate_bytes(source)
        free = int(shutil.disk_usage(storage_probe(directory)).free)
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return {"ok": False, "stage": "PREFLIGHT", "code": "STORAGE_OR_DB_UNAVAILABLE"}
    if expected <= 0:
        return {"ok": False, "stage": "PREFLIGHT", "code": "EMPTY_SNAPSHOT"}
    # Keep enough space for one full backup AND a separate restore test.
    reserve = max(MIN_RESERVE, expected // 5)
    required = 2 * expected + reserve
    return {
        "ok": free >= required,
        "stage": "PREFLIGHT",
        "code": "READY" if free >= required else "INSUFFICIENT_SPACE",
        "snapshot_bytes": expected,
        "free_bytes": free,
        "required_bytes": required,
    }


def verify_and_restore_isolated(directory: Path, name: str, timeout: int) -> dict:
    # Do not accept arbitrary relative paths from command-line arguments.
    if Path(name).name != name or not name.startswith("database_") or not name.endswith(".db"):
        return {"ok": False, "code": "INVALID_BACKUP_NAME"}
    selected = directory / name
    if not selected.is_file() or selected.is_symlink():
        return {"ok": False, "code": "BACKUP_NOT_FOUND"}
    check = validate_backup(ROOT, name, directory=directory)
    if check.get("ok") is not True or check.get("validated") != 1:
        return {"ok": False, "code": "HASH_OR_INTEGRITY_FAILED"}
    required = selected.stat().st_size + max(MIN_RESERVE, selected.stat().st_size // 5)
    if shutil.disk_usage(directory).free < required:
        return {"ok": False, "code": "INSUFFICIENT_ISOLATED_RESTORE_SPACE"}
    deadline = time.monotonic() + timeout
    try:
        with tempfile.TemporaryDirectory(prefix=".isolated_restore_327_", dir=directory) as temp:
            destination_path = Path(temp) / "restoration-test.db"
            with closing(connect_readonly(selected)) as original, closing(
                sqlite3.connect(str(destination_path), timeout=15)
            ) as restored:
                def progress(_status: int, _remaining: int, _total: int) -> None:
                    if time.monotonic() >= deadline:
                        raise sqlite3.OperationalError("isolated_restore_timeout")
                original.backup(restored, pages=256, progress=progress, sleep=0.05)
                restored.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
                if restored.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    return {"ok": False, "code": "ISOLATED_INTEGRITY_FAILED"}
                source_tables = original.execute(
                    "SELECT count(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()[0]
                restored_tables = restored.execute(
                    "SELECT count(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()[0]
                if source_tables != restored_tables:
                    return {"ok": False, "code": "SCHEMA_MISMATCH"}
    except (OSError, sqlite3.Error):
        return {"ok": False, "code": "ISOLATED_RESTORE_FAILED"}
    return {"ok": True, "code": "RESTORE_VERIFIED"}


def run(args: argparse.Namespace) -> int:
    source = Path(args.db).expanduser()
    # Dedicated directory: never prune or reclaim the normal backup archive.
    directory = (Path(args.backup_dir).expanduser() if args.backup_dir
                 else backup_dir(ROOT) / "operator_327")
    if args.verify_existing:
        if not directory.is_dir() or directory.is_symlink():
            emit({"ok": False, "stage": "VERIFY", "code": "DESTINATION_UNAVAILABLE"})
            return 2
        checked = verify_and_restore_isolated(directory, args.verify_existing, args.timeout)
        emit({"stage": "VERIFY", "backup_name": args.verify_existing, **checked})
        return 0 if checked.get("ok") else 2

    check = preflight(source, directory)
    if not check["ok"] or not args.execute:
        emit({**check, "execute_requested": bool(args.execute), "backup_created": False})
        return 0 if check["ok"] else 2

    # Double-check just before a write; no retention of other backups.
    check = preflight(source, directory)
    if not check["ok"]:
        emit({**check, "backup_created": False})
        return 2
    try:
        version_path = ROOT / "VERSION.txt"
        version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "OPERATOR_327"
        result = create_sqlite_backup(
            source,
            ROOT,
            version,
            backup_type="operator_recovery_327",
            created_by="render_web_shell",
            directory=directory,
            max_files=0,
            snapshot_timeout=float(args.timeout),
        )
    except (OSError, sqlite3.Error, ValueError):
        emit({"ok": False, "stage": "BACKUP", "code": "SNAPSHOT_FAILED", "backup_created": False})
        return 2
    name = result.get("backup_file", "")
    if result.get("ok") is not True or result.get("backup_created") is not True or not name:
        emit({
            "ok": False,
            "stage": str(result.get("failure_stage") or "BACKUP")[:36],
            "code": "BACKUP_INCOMPLETE",
            "backup_created": bool(result.get("backup_created")),
        })
        return 2
    restored = verify_and_restore_isolated(directory, name, args.timeout)
    emit({
        "ok": bool(restored.get("ok")),
        "stage": "COMPLETE" if restored.get("ok") else "ISOLATED_RESTORE",
        "code": restored.get("code"),
        "backup_created": True,
        "backup_name": name,
        "sha256": result.get("sha256"),
        "snapshot_bytes": check["snapshot_bytes"],
        "isolated_restore_ok": bool(restored.get("ok")),
    })
    return 0 if restored.get("ok") else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe manual SQLite backup and isolated restore for #327")
    parser.add_argument("--db", default=os.getenv("DB_PATH", "/data/database.db"))
    parser.add_argument("--backup-dir", default=None, help="Dedicated destination (default: operator_327)")
    parser.add_argument("--timeout", type=int, default=900, help="Shell-only budget in seconds (60-3600)")
    parser.add_argument("--execute", action="store_true", help="Create the backup; without it, read-only preflight")
    parser.add_argument("--verify-existing", default=None, help="Recheck a named operator_327 backup, without creating one")
    args = parser.parse_args()
    if not 60 <= args.timeout <= 3600:
        parser.error("--timeout must be between 60 and 3600 seconds")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
