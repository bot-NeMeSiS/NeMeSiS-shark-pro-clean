"""Data Vault, backup and ownership helpers for NeMeSiS SHARK PRO."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from engines.backup_staging import (BackupInProgress, backup_directory_lock,
                                    new_workspace, recover_abandoned_workspaces,
                                    remove_workspace)

CRITICAL_TABLES = [
    "users", "matches", "picks", "favorites", "api_sync_runs",
    "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots",
    "market_forecast_snapshots",
    "pick_decisions", "pick_discards", "telegram_delivery_memory",
    "team_identity_cache", "data_memory_errors", "persistent_cache",
    "pick_grading_results", "pick_grading_runs", "telegram_queue",
]

OWNERSHIP = {
    "users": "user_personal_data",
    "favorites": "user_personal_data",
    "matches": "external_api",
    "odds_memory_snapshots": "external_api",
    "match_snapshots": "external_api",
    "live_memory_snapshots": "external_api",
    "team_identity_cache": "external_api",
    "picks": "internal",
    "pick_decisions": "internal",
    "pick_discards": "internal",
    "pick_grading_results": "derived",
    "pick_grading_runs": "derived",
    "market_forecast_snapshots": "derived",
    "telegram_delivery_memory": "system_log",
    "telegram_queue": "system_log",
    "api_sync_runs": "system_log",
    "data_memory_errors": "system_log",
    "persistent_cache": "system_cache",
}


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def sha256_file(path: str | Path, *, deadline: float | None = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            if deadline is not None and time.monotonic() >= deadline:
                raise sqlite3.OperationalError("backup_snapshot_timeout")
            h.update(chunk)
    return h.hexdigest()


def _emit_backup_stage(stage: str, status: str, *, started_at: float | None = None,
                       error_type: str = "", error_code: str = "",
                       snapshot_bytes: int | None = None,
                       compact_snapshot_bytes: int | None = None,
                       required_bytes: int | None = None,
                       free_before: int | None = None,
                       free_bytes: int | None = None,
                       reusable_page_bytes: int | None = None,
                       reason_code: str = "") -> None:
    """Write low-cardinality backup timing without paths, data, or secrets."""
    event = {"event": "data_backup_stage", "stage": str(stage), "status": str(status)}
    if started_at is not None:
        event["duration_ms"] = max(0, int((time.monotonic() - started_at) * 1000))
    if error_type:
        event["error_type"] = str(error_type)[:48]
    if error_code and error_code.startswith("SQLITE_") and error_code.replace("_", "").isalnum():
        event["error_code"] = error_code[:48]
    for key, value in (
        ("snapshot_bytes", snapshot_bytes),
        ("compact_snapshot_bytes", compact_snapshot_bytes),
        ("required_bytes", required_bytes),
        ("free_before", free_before),
        ("free_bytes", free_bytes),
        ("reusable_page_bytes", reusable_page_bytes),
    ):
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            event[key] = value
    if reason_code and reason_code.replace("_", "").isalnum() and reason_code.upper() == reason_code:
        event["reason_code"] = reason_code[:48]
    print(json.dumps(event, ensure_ascii=True, sort_keys=True), flush=True)


def _run_backup_diagnostic_stage(stage: str, operation):
    """Time a backup preflight operation without logging its inputs or result."""
    started_at = time.monotonic()
    _emit_backup_stage(stage, "started")
    try:
        result = operation()
    except Exception as exc:
        _emit_backup_stage(
            stage,
            "failed",
            started_at=started_at,
            error_type=type(exc).__name__,
            error_code=getattr(exc, "sqlite_errorname", ""),
        )
        raise
    _emit_backup_stage(stage, "finished", started_at=started_at)
    return result


def _backup_error_type(exc: Exception, *, deadline: float | None = None) -> str:
    """Classify SQLite progress-handler interrupts as the expired deadline."""
    if "timeout" in str(exc).lower():
        return "BACKUP_TIMEOUT"
    if (getattr(exc, "sqlite_errorname", "") == "SQLITE_INTERRUPT"
            and deadline is not None and time.monotonic() >= deadline):
        return "BACKUP_TIMEOUT"
    return type(exc).__name__


def backup_dir(default_root: str | Path) -> Path:
    configured = os.getenv("DATA_BACKUP_DIR")
    if configured:
        return Path(configured)
    if Path("/data").exists():
        return Path("/data/backups")
    return Path(default_root) / "data" / "backups"


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).resolve()
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def table_names(db_path: str | Path) -> list[str]:
    if not Path(db_path).exists():
        return []
    conn = None
    try:
        conn = connect_readonly(db_path)
        return [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    except Exception:
        return []
    finally:
        if conn is not None:
            conn.close()


def table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
        return int(row["total"] or 0)
    except Exception:
        return 0


def db_vault_status(db_path: str | Path, root: str | Path, app_version: str = "") -> dict:
    path = Path(db_path)
    exists = path.exists()
    tables = table_names(path)
    counts = {}
    empty = []
    present = []
    missing = []
    if exists:
        conn = None
        try:
            conn = connect_readonly(path)
            for table in CRITICAL_TABLES:
                if table in tables:
                    count = table_count(conn, table)
                    counts[table] = count
                    present.append(table)
                    if count == 0:
                        empty.append(table)
                else:
                    missing.append(table)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:300], "db_path": str(path), "exists": exists}
        finally:
            if conn is not None:
                conn.close()
    bdir = backup_dir(root)
    backups = list_backups(root)
    risk = []
    if not exists:
        risk.append("DB no encontrada.")
    if exists and path.stat().st_size < 1024 * 64:
        risk.append("La base de datos parece nueva o pequeña; revisar persistent disk antes de vender.")
    if not backups:
        risk.append("No hay backups válidos detectados.")
    return {
        "ok": exists,
        "version": app_version,
        "db_path": str(path),
        "db_path_masked": str(path).replace(str(Path.home()), "~"),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if exists else "",
        "tables": tables,
        "critical_present": present,
        "critical_missing": missing,
        "critical_empty": empty,
        "counts": counts,
        "backup_dir": str(bdir),
        "backups": backups[:20],
        "last_backup": backups[0] if backups else {},
        "risk": risk,
        "ownership": {table: OWNERSHIP.get(table, "unknown") for table in CRITICAL_TABLES},
    }


def list_backups(root: str | Path, *, directory: str | Path | None = None) -> list[dict]:
    bdir = Path(directory) if directory is not None else backup_dir(root)
    if not bdir.exists():
        return []
    items = []
    backup_files = list(bdir.glob("database_*.db")) + list(bdir.glob("nemesis_backup_*.sqlite3"))
    for db_file in sorted(backup_files, key=lambda p: p.stat().st_mtime, reverse=True):
        manifest = db_file.with_suffix(".json")
        data = {}
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        items.append({
            "name": db_file.name,
            "path": str(db_file),
            "size_bytes": db_file.stat().st_size,
            "created_at": datetime.fromtimestamp(db_file.stat().st_mtime).isoformat(timespec="seconds"),
            "sha256": data.get("sha256") or "",
            "valid": bool(data.get("valid") and data.get("sha256")),
            "manifest": manifest.name if manifest.exists() else "",
            "type": data.get("type") or "",
        })
    return items


def _sqlite_snapshot_estimate_bytes(db_path: str | Path) -> int:
    """Estimate the logical SQLite snapshot size, including WAL-visible pages."""
    path = Path(db_path)
    physical = path.stat().st_size if path.exists() else 0
    try:
        with closing(connect_readonly(path)) as conn:
            page_count = int(conn.execute("PRAGMA page_count").fetchone()[0] or 0)
            page_size = int(conn.execute("PRAGMA page_size").fetchone()[0] or 0)
        return max(physical, page_count * page_size)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return physical


def _delete_backup_item(item: dict) -> bool:
    """Delete one known backup pair. The caller decides what is safe to remove."""
    try:
        path = Path(str(item.get("path") or ""))
        if not path.name:
            return False
        path.unlink(missing_ok=True)
        path.with_suffix(".json").unlink(missing_ok=True)
        return True
    except OSError:
        return False


def delete_sqlite_backup(root: str | Path, name: str, *, directory: str | Path | None = None) -> dict:
    """Delete one listed backup safely, preserving the last verified copy.

    Manual deletion shares the directory lock with backup creation and retention,
    accepts only a direct regular backup file, and removes its manifest together.
    """
    bdir = Path(directory) if directory is not None else backup_dir(root)
    safe_name = str(name or "")
    if (not safe_name or Path(safe_name).name != safe_name
            or not (safe_name.startswith("database_") and safe_name.endswith(".db")
                    or safe_name.startswith("nemesis_backup_") and safe_name.endswith(".sqlite3"))):
        return {"ok": False, "error": "backup_not_found"}
    try:
        if not bdir.is_dir() or bdir.is_symlink():
            return {"ok": False, "error": "backup_not_found"}
        target = bdir / safe_name
        manifest = target.with_suffix(".json")
        with backup_directory_lock(bdir):
            try:
                target_info = target.lstat()
            except FileNotFoundError:
                return {"ok": False, "error": "backup_not_found"}
            if not stat.S_ISREG(target_info.st_mode) or target_info.st_nlink != 1:
                return {"ok": False, "error": "backup_unsafe_file"}
            try:
                manifest_info = manifest.lstat()
            except FileNotFoundError:
                manifest_info = None
            if manifest_info is not None and (
                    not stat.S_ISREG(manifest_info.st_mode) or manifest_info.st_nlink != 1):
                return {"ok": False, "error": "backup_unsafe_manifest"}

            listed = {item.get("name"): item for item in list_backups(root, directory=bdir)}
            item = listed.get(safe_name)
            if not item:
                return {"ok": False, "error": "backup_not_found"}
            target_verified = bool(item.get("valid") and validate_backup(root, safe_name, directory=bdir).get("ok"))
            if target_verified:
                other_verified = False
                for other_name, other in listed.items():
                    if other_name == safe_name or not other.get("valid"):
                        continue
                    other_path = bdir / str(other_name or "")
                    other_manifest = other_path.with_suffix(".json")
                    try:
                        other_info = other_path.lstat()
                        manifest_info = other_manifest.lstat()
                    except OSError:
                        continue
                    if (not stat.S_ISREG(other_info.st_mode) or other_info.st_nlink != 1
                            or not stat.S_ISREG(manifest_info.st_mode) or manifest_info.st_nlink != 1):
                        continue
                    if validate_backup(root, other_name, directory=bdir).get("ok"):
                        other_verified = True
                        break
                if not other_verified:
                    return {"ok": False, "error": "last_verified_backup"}

            # Delete database first: an interrupted operation can leave only an
            # orphan manifest, never a manifest that appears to verify a missing DB.
            target.unlink()
            manifest.unlink(missing_ok=True)
            return {"ok": True, "deleted": safe_name, "verified": target_verified}
    except BackupInProgress:
        return {"ok": False, "error": "backup_busy"}
    except OSError:
        return {"ok": False, "error": "backup_delete_failed"}


def _compact_snapshot_capacity(db_path: Path, directory: Path) -> dict:
    """Read logical allocation; VACUUM INTO changes only a new recovery file."""
    try:
        with closing(connect_readonly(db_path)) as conn:
            pages = int(conn.execute("PRAGMA page_count").fetchone()[0])
            free_pages = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
            page_size = int(conn.execute("PRAGMA page_size").fetchone()[0])
        compact_bytes = max(1, pages - free_pages) * page_size
        margin = max(64 * 1024 * 1024, compact_bytes // 10)
        available = int(shutil.disk_usage(directory).free)
        required = compact_bytes + margin
        reason = ("NO_REUSABLE_PAGES" if free_pages <= 0
                  else "INSUFFICIENT_SPACE" if available < required
                  else "READY")
        return {"ok": reason == "READY", "reason_code": reason,
                "compact_snapshot_bytes": compact_bytes,
                "reusable_page_bytes": free_pages * page_size,
                "required_bytes": required,
                "free_bytes": available, "method": "vacuum_into"}
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return {"ok": False, "reason_code": "CAPACITY_CHECK_FAILED", "method": "vacuum_into"}


def ensure_backup_capacity(
    db_path: str | Path,
    root: str | Path,
    *,
    directory: str | Path | None = None,
) -> dict:
    """Reserve enough filesystem headroom for one atomic SQLite backup.

    When space is tight, remove only known older backup pairs. A verified
    recovery copy is always preserved. Invalid/orphan backup files are safe to
    remove before verified history. The live database is never modified.
    """
    src = Path(db_path)
    bdir = Path(directory) if directory is not None else backup_dir(root)
    bdir.mkdir(parents=True, exist_ok=True)
    snapshot_bytes = max(0, _run_backup_diagnostic_stage(
        "CAPACITY_DB_ESTIMATE", lambda: _sqlite_snapshot_estimate_bytes(src)))
    margin_bytes = max(64 * 1024 * 1024, snapshot_bytes // 10)
    required_bytes = snapshot_bytes + margin_bytes

    def capacity():
        usage = shutil.disk_usage(bdir)
        return int(usage.free), int(usage.total)

    free_before, total_bytes = _run_backup_diagnostic_stage("CAPACITY_DISK_CHECK", capacity)
    result = {
        "ok": free_before >= required_bytes,
        "snapshot_bytes": snapshot_bytes,
        "required_bytes": required_bytes,
        "free_before": free_before,
        "free_after": free_before,
        "total_bytes": total_bytes,
        "removed": [],
        "preserved_verified": "",
    }
    if result["ok"]:
        return result

    backups = _run_backup_diagnostic_stage(
        "CAPACITY_BACKUP_INVENTORY", lambda: list_backups(root, directory=bdir))
    verified = None
    def find_verified_backup():
        for item in backups:
            if not item.get("valid"):
                continue
            check = _run_backup_diagnostic_stage(
                "CAPACITY_BACKUP_VERIFY",
                lambda item=item: validate_backup(root, item["name"], directory=bdir),
            )
            if check.get("ok"):
                return item
        return None

    verified = _run_backup_diagnostic_stage("CAPACITY_VERIFY_HISTORY", find_verified_backup)
    if verified is not None:
        result["preserved_verified"] = verified["name"]

    # Invalid/orphan files first; then oldest verified-history copies. The
    # newest independently verified backup is never removed for capacity.
    candidates = [item for item in reversed(backups) if not item.get("valid")]
    if verified is not None:
        candidates.extend(
            item for item in reversed(backups)
            if item.get("valid") and item["name"] != verified["name"]
        )
    def reclaim_known_backups():
        seen = set()
        for item in candidates:
            name = str(item.get("name") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            if _delete_backup_item(item):
                result["removed"].append(name)
            free_now, _ = capacity()
            result["free_after"] = free_now
            if free_now >= required_bytes:
                return True
        return False

    reclaimed = _run_backup_diagnostic_stage("CAPACITY_RECLAIM", reclaim_known_backups)
    if reclaimed:
        result["ok"] = True
        return result

    result["ok"] = False
    result["error"] = "backup_storage_insufficient"
    return result


def create_sqlite_backup(db_path: str | Path, root: str | Path, app_version: str, backup_type: str = "manual", created_by: str = "admin", *, directory: str | Path | None = None, max_files: int | None = None, snapshot_timeout: float = 15.0) -> dict:
    """Serialize capacity, crash recovery, snapshot publication and retention."""
    src = Path(db_path)
    if not src.exists():
        return {"ok": False, "backup_created": False, "error": "DB no encontrada", "db_path": str(src)}
    bdir = Path(directory) if directory is not None else backup_dir(root)
    attempt_started = time.monotonic()
    _emit_backup_stage("ATTEMPT", "started")
    try:
        bdir.mkdir(parents=True, exist_ok=True)
        lock_started = time.monotonic()
        _emit_backup_stage("LOCK", "started")
        with backup_directory_lock(bdir):
            _emit_backup_stage("LOCK", "finished", started_at=lock_started)
            recovery_started = time.monotonic()
            _emit_backup_stage("RECOVERY", "started")
            recovery = recover_abandoned_workspaces(bdir, src)
            _emit_backup_stage("RECOVERY", "finished" if not recovery["failed_count"] else "failed",
                               started_at=recovery_started,
                               error_type="recovery_failed" if recovery["failed_count"] else "")
            if recovery["failed_count"]:
                _emit_backup_stage("ATTEMPT", "failed", started_at=attempt_started,
                                   error_type="recovery_failed")
                return {"ok": False, "backup_created": False,
                        "error": "backup_temporary_recovery_failed", "failure_stage": "RECOVERY",
                        "storage": {"temporary_recovery": recovery}}
            result = _create_sqlite_backup_locked(src, root, app_version, backup_type, created_by,
                                                  directory=bdir, max_files=max_files,
                                                  snapshot_timeout=snapshot_timeout)
            result.setdefault("storage", {})["temporary_recovery"] = recovery
            _emit_backup_stage("ATTEMPT", "finished" if result.get("ok") else "failed",
                               started_at=attempt_started,
                               error_type=("backup_failed" if not result.get("ok") else ""))
            return result
    except BackupInProgress:
        _emit_backup_stage("LOCK", "skipped", started_at=lock_started)
        _emit_backup_stage("ATTEMPT", "skipped", started_at=attempt_started)
        return {"ok": True, "backup_created": False, "status": "SKIPPED_ALREADY_RUNNING"}
    except OSError as exc:
        _emit_backup_stage("PREPARATION", "failed", started_at=locals().get("lock_started"),
                           error_type=type(exc).__name__)
        _emit_backup_stage("ATTEMPT", "failed", started_at=attempt_started,
                           error_type=type(exc).__name__)
        return {"ok": False, "backup_created": False, "error": str(exc)[:300],
                "failure_stage": "PREPARATION"}


def _create_sqlite_backup_locked(db_path: str | Path, root: str | Path, app_version: str, backup_type: str, created_by: str, *, directory: Path, max_files: int | None, snapshot_timeout: float) -> dict:
    src = Path(db_path)
    if not src.exists():
        return {"ok": False, "backup_created": False, "error": "DB no encontrada", "db_path": str(src)}
    bdir = Path(directory) if directory is not None else backup_dir(root)
    bdir.mkdir(parents=True, exist_ok=True)
    capacity_started = time.monotonic()
    _emit_backup_stage("CAPACITY_PREFLIGHT", "started")
    storage = ensure_backup_capacity(src, root, directory=bdir)
    _emit_backup_stage("CAPACITY_PREFLIGHT", "finished" if storage.get("ok") else "rejected",
                       started_at=capacity_started,
                       snapshot_bytes=storage.get("snapshot_bytes"),
                       required_bytes=storage.get("required_bytes"),
                       free_before=storage.get("free_before"),
                       free_bytes=storage.get("free_after"),
                       reason_code=("READY" if storage.get("ok") else "INSUFFICIENT_SPACE"))
    compact = False
    if not storage.get("ok"):
        compact_capacity_started = time.monotonic()
        _emit_backup_stage("COMPACT_CAPACITY_PREFLIGHT", "started")
        candidate = _compact_snapshot_capacity(src, bdir)
        _emit_backup_stage("COMPACT_CAPACITY_PREFLIGHT", "finished" if candidate.get("ok") else "rejected",
                           started_at=compact_capacity_started,
                           compact_snapshot_bytes=candidate.get("compact_snapshot_bytes"),
                           required_bytes=candidate.get("required_bytes"),
                           free_bytes=candidate.get("free_bytes"),
                           reusable_page_bytes=candidate.get("reusable_page_bytes"),
                           reason_code=str(candidate.get("reason_code") or ""))
        storage["compact_candidate"] = candidate
        if not candidate.get("ok"):
            return {"ok": False, "backup_created": False,
                    "error": storage.get("error") or "backup_storage_insufficient",
                    "failure_stage": "CAPACITY", "storage": storage}
        compact = True
        storage.pop("error", None)
        storage.update(ok=True, method="vacuum_into",
                       allocated_snapshot_bytes=storage.get("snapshot_bytes"),
                       snapshot_bytes=candidate["compact_snapshot_bytes"],
                       required_bytes=candidate["required_bytes"],
                       free_after=candidate["free_bytes"])
    stamp = now_stamp() + "_" + uuid.uuid4().hex[:12]
    out = bdir / f"database_{stamp}.db"
    manifest_path = out.with_suffix(".json")
    temporary = None
    manifest_temporary = None
    workspace = None
    manifest_published = False
    published = False
    result = {}
    stage = "WORKSPACE"
    stage_started_at = None

    def advance_stage(next_stage: str) -> None:
        nonlocal stage, stage_started_at
        if stage_started_at is not None:
            _emit_backup_stage(stage, "finished", started_at=stage_started_at)
        stage = next_stage
        stage_started_at = time.monotonic()
        _emit_backup_stage(stage, "started")

    try:
        advance_stage("WORKSPACE")
        workspace = new_workspace(bdir)
        temporary = workspace / "snapshot.partial"
        temporary.touch(mode=0o600, exist_ok=False)
        deadline = time.monotonic() + max(0.01, float(snapshot_timeout))
        advance_stage("SNAPSHOT")
        if compact:
            # The source connection is read-only. No VACUUM, checkpoints or
            # deletion run against the live DB; only the destination is rebuilt.
            with closing(connect_readonly(src)) as source:
                source.execute("PRAGMA busy_timeout=50")
                last_capacity_check = [0.0]
                def compact_progress():
                    now = time.monotonic()
                    if now >= deadline:
                        return 1
                    if now - last_capacity_check[0] >= 0.05:
                        last_capacity_check[0] = now
                        if shutil.disk_usage(bdir).free < 64 * 1024 * 1024:
                            return 1
                    return 0
                source.set_progress_handler(compact_progress, 1000)
                source.execute("VACUUM INTO ?", (str(temporary),))
            actual_size = temporary.stat().st_size
            margin = max(64 * 1024 * 1024, actual_size // 10)
            if shutil.disk_usage(bdir).free < margin:
                raise sqlite3.OperationalError("backup_storage_insufficient")
        with closing(connect_readonly(src)) as source, closing(sqlite3.connect(str(temporary), timeout=15)) as dest:
            # SQLite retries BUSY/LOCKED indefinitely unless progress aborts it.
            # Keep the synchronous request below the web worker's timeout.
            source.execute("PRAGMA busy_timeout=50")
            dest.execute("PRAGMA busy_timeout=50")
            def progress(status_code, remaining, total):
                if time.monotonic() >= deadline:
                    raise sqlite3.OperationalError("backup_snapshot_timeout")
            if not compact:
                source.backup(dest, pages=256, progress=progress, sleep=0.05)
            # Keep the SQLite copy separate from verification in production
            # timings. Previously source.backup ran under INTEGRITY, making a
            # slow snapshot indistinguishable from a slow integrity_check.
            advance_stage("INTEGRITY")
            dest.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            if dest.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise sqlite3.DatabaseError("backup_integrity_check_failed")
            # Inspect the verified snapshot on this same deadline-bound connection.
            # The admin dashboard helper opens new connections and scans backup
            # history; neither is necessary to describe this snapshot.
            advance_stage("METADATA")
            tables = [row[0] for row in dest.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            counts = {}
            for table in CRITICAL_TABLES:
                if time.monotonic() >= deadline:
                    raise sqlite3.OperationalError("backup_snapshot_timeout")
                if table in tables:
                    counts[table] = int(dest.execute(
                        f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        with temporary.open("rb+") as handle:
            os.fsync(handle.fileno())
        advance_stage("HASH")
        digest = sha256_file(temporary, deadline=deadline)
        if time.monotonic() >= deadline:
            raise sqlite3.OperationalError("backup_snapshot_timeout")
        advance_stage("MANIFEST")
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "version": app_version,
            "db_path_source": str(src),
            "size_bytes": temporary.stat().st_size,
            "sha256": digest,
            "tables_included": tables,
            "records_summary": counts,
            "type": backup_type,
            "environment": "production" if str(src).startswith("/data") else "local",
            "created_by": created_by,
            "valid": True,
            "notes": "Backup SQLite verificado. No incluir en ZIP.",
            "snapshot_method": "vacuum_into" if compact else "sqlite_backup",
        }
        manifest_temporary = workspace / "manifest.json.partial"
        manifest_temporary.touch(mode=0o600, exist_ok=False)
        manifest_temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with manifest_temporary.open("rb+") as handle:
            os.fsync(handle.fileno())
        # Publish the manifest first; readers only discover the final DB name.
        advance_stage("PUBLICATION")
        os.replace(manifest_temporary, manifest_path)
        manifest_published = True
        os.replace(temporary, out)
        published = True
        if os.name != "nt":
            directory_fd = os.open(bdir, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        advance_stage("RETENTION")
        retention = apply_backup_retention(root, directory=bdir, max_files=max_files)
        result = {"ok": bool(retention.get("ok")), "backup_created": True, "backup_file": out.name, "path": str(out), "sha256": digest, "manifest": manifest_path.name, "records_summary": counts, "retention": retention, "storage": storage}
        if not result["ok"]:
            result["failure_stage"] = stage
        _emit_backup_stage(stage, "finished", started_at=stage_started_at)
        stage_started_at = None
        return result
    except Exception as exc:
        if stage_started_at is not None:
            deadline = locals().get("deadline")
            error_type = _backup_error_type(exc, deadline=deadline)
            error_code = getattr(exc, "sqlite_errorname", "")
            _emit_backup_stage(stage, "failed", started_at=stage_started_at,
                               error_type=error_type, error_code=error_code)
            stage_started_at = None
        deadline = locals().get("deadline")
        error_label = ("backup_snapshot_timeout" if _backup_error_type(exc, deadline=deadline) == "BACKUP_TIMEOUT"
                       else str(exc)[:300])
        result = {"ok": False, "backup_created": published, "error": error_label,
                  "failure_stage": stage, "storage": storage}
        if published:
            result.update(backup_file=out.name, path=str(out), manifest=manifest_path.name)
        return result
    finally:
        cleanup_started = time.monotonic()
        _emit_backup_stage("CLEANUP", "started")
        cleanup_ok = True
        if workspace is not None:
            cleanup = remove_workspace(workspace, bdir, src)
            cleanup_ok = bool(cleanup["removed"])
            storage["temporary_cleanup_ok"] = cleanup_ok
            if not cleanup_ok:
                result.update(ok=False, error=result.get("error") or "backup_temporary_cleanup_failed")
                result.setdefault("failure_stage", "CLEANUP")
        if manifest_published and not published:
            try:
                manifest_path.unlink(missing_ok=True)
            except OSError:
                cleanup_ok = False
                result.update(ok=False, error=result.get("error") or "backup_manifest_cleanup_failed")
                result.setdefault("failure_stage", "CLEANUP")
        _emit_backup_stage("CLEANUP", "finished" if cleanup_ok else "failed",
                           started_at=cleanup_started,
                           error_type=("cleanup_failed" if not cleanup_ok else ""))


def validate_backup(root: str | Path, backup_name: str = "", *, directory: str | Path | None = None) -> dict:
    backups = list_backups(root, directory=directory)
    if backup_name:
        backups = [b for b in backups if b["name"] == backup_name]
    results = []
    for item in backups:
        path = Path(item["path"])
        expected = item.get("sha256")
        actual = sha256_file(path) if path.exists() else ""
        integrity = False
        if actual and item.get("valid") and expected == actual:
            try:
                with closing(connect_readonly(path)) as conn:
                    integrity = [row[0] for row in conn.execute("PRAGMA integrity_check")] == ["ok"]
            except sqlite3.Error:
                integrity = False
        results.append({"name": item["name"], "ok": integrity, "expected": expected, "actual": actual})
    return {"ok": all(r["ok"] for r in results) if results else False, "validated": len(results), "results": results}


def apply_backup_retention(root: str | Path, *, directory: str | Path | None = None, max_files: int | None = None) -> dict:
    max_files = int(os.getenv("DATA_BACKUP_MAX_FILES", "30") or 30) if max_files is None else int(max_files)
    backups = list_backups(root, directory=directory)
    removed = []
    if len(backups) <= max_files or max_files < 1:
        return {"ok": True, "removed": removed, "kept": len(backups)}
    # A newer incomplete file must never displace the newest verified copy.
    verified = next((item for item in backups if item["valid"] and validate_backup(root, item["name"], directory=directory)["ok"]), None)
    if verified is None:
        return {"ok": False, "removed": [], "kept": len(backups), "error": "no_verified_backup_to_preserve"}
    ordered = [verified] + [item for item in backups if item["name"] != verified["name"]]
    errors = []
    for item in ordered[max_files:]:
        try:
            Path(item["path"]).unlink(missing_ok=True)
            manifest = Path(item["path"]).with_suffix(".json")
            manifest.unlink(missing_ok=True)
            removed.append(item["name"])
        except OSError as exc:
            errors.append({"name": item["name"], "error": str(exc)[:200]})
    return {"ok": not errors, "removed": removed, "kept": len(list_backups(root, directory=directory)), "errors": errors}


def restore_sqlite_backup(db_path: str | Path, root: str | Path, backup_name: str, app_version: str,
                          *, directory: str | Path | None = None, max_files: int | None = None) -> dict:
    """Explicit admin restore through SQLite, with verified staging and recovery copy."""
    target = Path(db_path)
    if not target.is_file():
        return {"ok": False, "error": "database_missing"}
    staged = None
    safety = {}
    try:
        selected = next((item for item in list_backups(root, directory=directory) if item["name"] == backup_name), None)
        if selected is None:
            return {"ok": False, "error": "backup_not_found"}
        if not validate_backup(root, backup_name, directory=directory)["ok"]:
            return {"ok": False, "error": "backup_validation_failed"}
        folder = Path(selected["path"]).parent
        handle, temporary_name = tempfile.mkstemp(prefix=".restore-", suffix=".partial", dir=folder)
        os.close(handle)
        staged = Path(temporary_name)
        shutil.copyfile(selected["path"], staged)
        # Recheck copied bytes; subsequent retention may remove the selected original.
        if sha256_file(staged) != selected["sha256"]:
            return {"ok": False, "error": "backup_validation_failed"}
        with closing(connect_readonly(staged)) as source:
            if [row[0] for row in source.execute("PRAGMA integrity_check")] != ["ok"]:
                return {"ok": False, "error": "backup_validation_failed"}
            safety = create_sqlite_backup(target, root, app_version, backup_type="pre_restore_" + backup_name,
                                           directory=folder, max_files=max_files)
            if not safety.get("ok") or safety.get("backup_created") is not True:
                return {"ok": False, "error": "safety_backup_failed", "safety": safety}
            # File replacement bypasses SQLite's WAL/locking protocol. The backup API
            # applies a transaction to the live database and existing connections.
            deadline = time.monotonic() + 15
            def progress(status, remaining, total):
                if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) and time.monotonic() >= deadline:
                    raise sqlite3.OperationalError("restore_database_busy")
            with closing(sqlite3.connect(str(target), timeout=15)) as destination:
                source.backup(destination, pages=256, progress=progress, sleep=0.05)
        return {"ok": True, "restored": backup_name, "safety_backup": safety["backup_file"]}
    except (OSError, sqlite3.Error) as exc:
        return {"ok": False, "error": "backup_restore_failed", "detail": str(exc)[:300],
                "safety_backup": safety.get("backup_file")}
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def export_table_csv(db_path: str | Path, root: str | Path, table: str) -> dict:
    if table not in CRITICAL_TABLES:
        return {"ok": False, "error": "Tabla no permitida para export seguro."}
    if not Path(db_path).exists():
        return {"ok": False, "error": "DB no encontrada."}
    out_dir = Path(root) / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"nemesis_export_{table}_{now_stamp()}.csv"
    conn = None
    try:
        conn = connect_readonly(db_path)
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            out.write_text("", encoding="utf-8")
        else:
            columns = rows[0].keys()
            with out.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
        return {"ok": True, "file": out.name, "path": str(out), "classification": OWNERSHIP.get(table, "unknown")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}
    finally:
        if conn is not None:
            conn.close()
