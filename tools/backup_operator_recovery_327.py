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
    BackupInProgress,
    backup_directory_lock,
    backup_dir,
    connect_readonly,
    connect_archive_readonly,
    assert_archive_standalone,
    sha256_file,
    create_sqlite_backup,
    validate_backup,
)

from tools.recovery_workspace import (  # noqa: E402
    admit_restore_root, recheck_restore_root, restore_workspace, workspace_capacity_preflight,
)
from tools.recovery_workspace_plan import WorkspacePlanError, WorkspaceRootIdentity  # noqa: E402

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


def preflight(source: Path, directory: Path, *, restore_workspace_root=None,
              restore_workspace_identity=None, app_probe_mode=None) -> dict:
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
    if restore_workspace_root is not None:
        try:
            return workspace_capacity_preflight(
                source=source, directory=directory, restore_root=restore_workspace_root,
                snapshot_bytes=expected, app_probe_mode=app_probe_mode,
                expected_identity=restore_workspace_identity)
        except WorkspacePlanError as exc:
            return {"ok": False, "stage": "PREFLIGHT", "code": "RESTORE_WORKSPACE_NOT_ADMITTED",
                    "diagnostic": str(exc)}
        except OSError:
            return {"ok": False, "stage": "PREFLIGHT", "code": "RESTORE_WORKSPACE_NOT_AVAILABLE"}
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


def verify_and_restore_isolated(directory: Path, name: str, timeout: int, *, app_probe_mode=None,
                                state_bundle=None, restore_workspace_root=None,
                                restore_workspace_identity=None) -> dict:
    started = time.monotonic()
    if restore_workspace_identity is not None and restore_workspace_root is None:
        return {"ok": False, "code": "RESTORE_WORKSPACE_IDENTITY_WITHOUT_ROOT"}
    if state_bundle is not None and app_probe_mode is None:
        return {"ok": False, "code": "STATE_REQUIRES_EXPLICIT_APP_PROBE"}
    if app_probe_mode not in (None, "read_only", "normal_boot"):
        return {"ok": False, "code": "INVALID_APP_PROBE_MODE"}
    try:
        budget = float(timeout)
    except (ValueError, TypeError, OverflowError):
        return {"ok": False, "code": "INVALID_VERIFICATION_BUDGET"}
    if isinstance(timeout, bool) or not 0 < budget < float("inf"):
        return {"ok": False, "code": "INVALID_VERIFICATION_BUDGET"}
    deadline = started + budget
    stage = "ARCHIVE_VALIDATION"
    workspace_identity = None
    workspace_observation = None

    def workspace_details():
        if workspace_observation is not None and workspace_observation.get("created") is True:
            # The helper owns this plain metadata object through its finalizer;
            # cleanup completion updates it before this function returns.
            return {"restore_workspace": workspace_observation}
        return {}

    def failed_workspace_details():
        details = workspace_details()
        if details and workspace_observation.get("cleanup_verified") is not True:
            details["workspace_may_be_preserved"] = True
        return details

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError("isolated_restore_timeout")
        if workspace_identity is not None:
            recheck_restore_root(workspace_identity, protected_paths=(directory, directory / name))

    def fingerprint(path):
        return assert_archive_standalone(path)

    if (not isinstance(name, str) or Path(name).name != name or "/" in name or "\\" in name
            or not name.startswith("database_") or not name.endswith(".db")):
        return {"ok": False, "code": "INVALID_BACKUP_NAME"}
    selected = directory / name
    if not directory.is_dir() or directory.is_symlink() or not selected.is_file() or selected.is_symlink():
        return {"ok": False, "code": "BACKUP_NOT_FOUND"}
    try:
        check_time()
        with backup_directory_lock(directory):
            check_time()
            checked = validate_backup(ROOT, name, directory=directory, deadline=deadline)
            if checked.get("ok") is not True or checked.get("validated") != 1:
                if checked.get("error") == "backup_validation_timeout":
                    return {"ok": False, "code": "VERIFICATION_TIMEOUT",
                            "failure_stage": checked.get("failure_stage", stage)}
                details = {key: checked[key] for key in ("failure_stage", "error_type", "sqlite_error_code")
                           if key in checked}
                return {"ok": False, "code": "HASH_OR_INTEGRITY_FAILED", **details}
            check_time()
            archive_identity = checked.get("file_identity")
            if archive_identity != fingerprint(selected):
                return {"ok": False, "code": "BACKUP_CHANGED_DURING_VERIFICATION", **workspace_details()}
            if state_bundle is not None:
                from tools.recovery_state_adapter import bind_verified_sqlite
                bind_verified_sqlite(state_bundle, backup_name=name,
                                     sqlite_sha256=checked["results"][0]["actual"], deadline=deadline)
            stage = "RESTORE_CAPACITY"
            if restore_workspace_root is not None:
                # No default temporary-directory discovery or fallback: this
                # is a trusted explicit operator argument, not manifest data.
                workspace_identity = admit_restore_root(
                    restore_workspace_root, protected_paths=(directory, selected))
                if restore_workspace_identity is not None and (
                        type(restore_workspace_identity) is not WorkspaceRootIdentity
                        or workspace_identity != restore_workspace_identity):
                    raise WorkspacePlanError("WORKSPACE_ROOT_CHANGED")
            required = archive_identity["size"] + max(MIN_RESERVE, archive_identity["size"] // 5)
            if app_probe_mode is not None:
                # Source/scratch plus room for a full clone journal in normal
                # boot. This is a conservative gate, never a quota increase.
                required += MIN_RESERVE
                if app_probe_mode == "normal_boot":
                    required += archive_identity["size"]
            if state_bundle is not None:
                required += state_bundle.limits.bytes
            free = shutil.disk_usage(directory if workspace_identity is None
                                     else workspace_identity.path).free
            check_time()
            if free < required:
                return {"ok": False, "code": "INSUFFICIENT_ISOLATED_RESTORE_SPACE"}
            app_probe = None
            workspace_observation = {} if workspace_identity is not None else None
            stage = "RESTORE_SNAPSHOT"
            with restore_workspace(directory, identity=workspace_identity, check_time=check_time,
                                   observation=workspace_observation) as temp:
                check_time()
                if workspace_identity is not None:
                    observed_workspace = Path(temp).lstat()
                    workspace_observation.update(
                        device=observed_workspace.st_dev, disposable_inode=observed_workspace.st_ino,
                        app_probe_requested=app_probe_mode is not None)
                destination_path = Path(temp) / "restoration-test.db"
                with closing(connect_archive_readonly(selected)) as original, closing(
                    sqlite3.connect(str(destination_path), timeout=min(.05, max(.001, deadline - time.monotonic())))
                ) as restored:
                    check_time()
                    remaining_ms = max(1, min(50, int((deadline - time.monotonic()) * 1000)))
                    original.execute(f"PRAGMA busy_timeout={remaining_ms}")
                    restored.execute(f"PRAGMA busy_timeout={remaining_ms}")
                    if (sha256_file(selected, deadline=deadline) != checked["results"][0]["actual"]
                            or fingerprint(selected) != archive_identity):
                        return {"ok": False, "code": "BACKUP_CHANGED_DURING_VERIFICATION", **workspace_details()}
                    check_time()
                    original.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
                    restored.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
                    def progress(_status: int, _remaining: int, _total: int) -> None:
                        check_time()
                    original.backup(restored, pages=256, progress=progress, sleep=.05)
                    check_time()
                    stage = "RESTORE_INTEGRITY"
                    if restored.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                        return {"ok": False, "code": "ISOLATED_INTEGRITY_FAILED"}
                    check_time()
                    stage = "RESTORE_SCHEMA"
                    query = "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
                    with closing(original.execute(query)) as left, closing(restored.execute(query)) as right:
                        while True:
                            check_time()
                            a = next(left, None)
                            b = next(right, None)
                            if a is None and b is None:
                                break
                            if a is None or b is None or tuple(a) != tuple(b):
                                return {"ok": False, "code": "SCHEMA_MISMATCH"}
                    check_time()
                    if fingerprint(selected) != archive_identity:
                        return {"ok": False, "code": "BACKUP_CHANGED_DURING_VERIFICATION", **workspace_details()}
                if app_probe_mode is not None:
                    # Same restoration, after both SQLite handles close, before
                    # its existing disposable workspace is cleaned up. The App
                    # shares this phase's deadline; it receives no extra budget.
                    stage = "ISOLATED_APP_PROBE"
                    check_time()
                    from tools.recovery_app_probe import run_app_probe
                    state_options = {} if state_bundle is None else {"state_bundle": state_bundle}
                    app_probe = run_app_probe(project_root=ROOT, restored_database=destination_path,
                                              workspace=Path(temp), deadline=deadline, mode=app_probe_mode,
                                              **state_options)
                    if fingerprint(selected) != archive_identity:
                        return {"ok": False, "code": "BACKUP_CHANGED_DURING_VERIFICATION", **workspace_details()}
                    if not app_probe.get("ok"):
                        return {"ok": False, "code": "SQLITE_RESTORED_APP_NOT_VERIFIED", "schema_match": True,
                                "sqlite_restore_verified": True, "app_probe": app_probe,
                                "full_application_recovery_certified": False, **workspace_details()}
            stage = "FINAL_CHECK"
            if fingerprint(selected) != archive_identity:
                return {"ok": False, "code": "BACKUP_CHANGED_DURING_VERIFICATION", **workspace_details()}
            finished = time.monotonic()
            if finished >= deadline:
                raise TimeoutError("isolated_restore_timeout")
            report = {"ok": True, "code": "RESTORE_VERIFIED", "sha256": checked["results"][0]["actual"],
                      "schema_match": True, "verification_duration_ms": int((finished - started) * 1000)}
            if app_probe is not None:
                report.update(code="SQLITE_RESTORE_AND_GUEST_APP_SMOKE_VERIFIED", app_probe=app_probe,
                              sqlite_restore_verified=True, full_application_recovery_certified=False)
            if workspace_observation is not None:
                # The context's audited rmdir and final identity/deadline
                # checks completed. These fields report actual observation,
                # not capacity/custody or full-platform recovery.
                workspace_observation["same_restoration_for_app"] = app_probe_mode is not None
                report.update(restore_workspace=workspace_observation,
                              full_application_recovery_certified=False)
            return report
    except WorkspacePlanError as exc:
        return {"ok": False, "code": "ISOLATED_RESTORE_WORKSPACE_NOT_VERIFIED",
                "failure_stage": stage, "diagnostic": str(exc),
                "full_application_recovery_certified": False, **failed_workspace_details()}
    except BackupInProgress:
        return {"ok": False, "code": "RECOVERY_LOCK_BUSY"}
    except TimeoutError:
        return {"ok": False, "code": "VERIFICATION_TIMEOUT", "failure_stage": stage, **failed_workspace_details()}
    except sqlite3.Error as exc:
        if getattr(exc, "sqlite_errorname", "") == "SQLITE_INTERRUPT" and time.monotonic() >= deadline:
            return {"ok": False, "code": "VERIFICATION_TIMEOUT", "failure_stage": stage, **failed_workspace_details()}
        return {"ok": False, "code": "ISOLATED_RESTORE_FAILED", "error_type": type(exc).__name__,
                "sqlite_error_code": getattr(exc, "sqlite_errorname", ""), **failed_workspace_details()}
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "code": "ISOLATED_RESTORE_FAILED", "error_type": type(exc).__name__,
                **failed_workspace_details()}


def run(args: argparse.Namespace, *, state_plan=None, sqlite_set_plan=None) -> int:
    source = Path(args.db).expanduser()
    # Dedicated directory: never prune or reclaim the normal backup archive.
    directory = (Path(args.backup_dir).expanduser() if args.backup_dir
                 else backup_dir(ROOT) / "operator_327")
    if sqlite_set_plan is not None:
        if state_plan is not None:
            emit({"ok": False, "stage": "PREFLIGHT", "code": "CONFLICTING_RECOVERY_PLANS",
                  "backup_created": False})
            return 2
        from tools.recovery_sqlite_set_operator import run_set_operation
        result = run_set_operation(plan=sqlite_set_plan, source=source, directory=directory,
            restore_root=(Path(args.restore_workspace_root).expanduser()
                          if getattr(args, "restore_workspace_root", None) is not None else None),
            timeout=args.timeout, app_probe_mode=getattr(args, "app_probe_mode", None),
            project_root=ROOT, execute=args.execute, verify_existing=args.verify_existing)
        emit(result)
        return 0 if result.get("ok") is True else 2
    # A plan is supplied only by a separately reviewed code/data invocation.
    # main() supplies none; no CLI flag or manifest can enable state capture.
    if state_plan is not None and args.verify_existing:
        emit({"ok": False, "stage": "PREFLIGHT", "code": "STATE_VERIFY_EXISTING_NOT_ADMITTED"})
        return 2
    workspace_options = {}
    requested_workspace = getattr(args, "restore_workspace_root", None)
    if requested_workspace is not None:
        try:
            requested_workspace = Path(requested_workspace).expanduser()
            workspace_binding = admit_restore_root(
                requested_workspace, protected_paths=(source, directory))
        except (OSError, ValueError, TypeError) as exc:
            emit({"ok": False, "stage": "PREFLIGHT", "code": "RESTORE_WORKSPACE_NOT_ADMITTED",
                  "diagnostic": str(exc) if isinstance(exc, WorkspacePlanError) else type(exc).__name__,
                  "backup_created": False})
            return 2
        workspace_options = {"restore_workspace_root": requested_workspace,
                             "restore_workspace_identity": workspace_binding}
    preflight_options = ({} if not workspace_options else
                         {**workspace_options, "app_probe_mode": getattr(args, "app_probe_mode", None)})
    if args.verify_existing:
        if not directory.is_dir() or directory.is_symlink():
            emit({"ok": False, "stage": "VERIFY", "code": "DESTINATION_UNAVAILABLE"})
            return 2
        checked = verify_and_restore_isolated(directory, args.verify_existing, args.timeout,
                                              app_probe_mode=getattr(args, "app_probe_mode", None),
                                              **workspace_options)
        emit({"stage": "VERIFY", "backup_name": args.verify_existing, **checked})
        return 0 if checked.get("ok") else 2

    if state_plan is not None:
        from tools.recovery_state_adapter import operator_preflight, validate_operator_plan, HandoffError
        try:
            # Validate the code-supplied binding before even the SQLite-only
            # read preflight. This does not create a plan from CLI/data.
            validate_operator_plan(plan=state_plan, source=source, directory=directory,
                                   app_probe_mode=getattr(args, "app_probe_mode", None),
                                   verify_existing=args.verify_existing)
        except (HandoffError, OSError, ValueError, TypeError):
            emit({"ok": False, "stage": "PREFLIGHT", "code": "STATE_PLAN_NOT_ADMITTED", "backup_created": False})
            return 2
    check = preflight(source, directory, **preflight_options)
    if state_plan is not None:
        try:
            check = operator_preflight(plan=state_plan, source=source, directory=directory,
                                       app_probe_mode=getattr(args, "app_probe_mode", None),
                                       verify_existing=args.verify_existing, storage=check,
                                       **workspace_options)
        except (HandoffError, OSError, ValueError, TypeError):
            emit({"ok": False, "stage": "PREFLIGHT", "code": "STATE_PLAN_NOT_ADMITTED", "backup_created": False})
            return 2
    if not check["ok"] or not args.execute:
        emit({**check, "execute_requested": bool(args.execute), "backup_created": False})
        return 0 if check["ok"] else 2

    # Double-check just before a write; no retention of other backups.
    check = preflight(source, directory, **preflight_options)
    if state_plan is not None:
        try:
            check = operator_preflight(plan=state_plan, source=source, directory=directory,
                                       app_probe_mode=getattr(args, "app_probe_mode", None),
                                       verify_existing=args.verify_existing, storage=check,
                                       **workspace_options)
        except (HandoffError, OSError, ValueError, TypeError):
            emit({"ok": False, "stage": "PREFLIGHT", "code": "STATE_PLAN_NOT_ADMITTED",
                  "backup_created": False})
            return 2
    if not check["ok"]:
        emit({**check, "backup_created": False})
        return 2
    state_handoff = None
    state_bundle = None
    try:
        version_path = ROOT / "VERSION.txt"
        version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "OPERATOR_327"
        def capture_sqlite(**deadline_cap):
            return create_sqlite_backup(
                source,
                ROOT,
                version,
                backup_type="operator_recovery_327",
                created_by="render_web_shell",
                directory=directory,
                max_files=0,
                preserve_existing_backups=True,
                snapshot_timeout=float(args.timeout),
                **deadline_cap,
            )
        if state_plan is None:
            result = capture_sqlite()
        else:
            from tools.recovery_state_adapter import capture_with_state, public_state_receipt, public_sqlite_disposition
            # One aggregate phase A: state copy -> ONE SQLite -> state recheck
            # -> state publication. Substeps do not restart this deadline.
            capture_deadline = time.monotonic() + float(args.timeout)
            state_handoff = capture_with_state(plan=state_plan, source=source,
                                               create_snapshot=capture_sqlite, deadline=capture_deadline)
            result = state_handoff.sqlite_result or {}
            state_bundle = state_handoff.bundle
            if not state_handoff.ok:
                emit({"ok": False, "stage": "STATE_CAPTURE", "code": "STATE_CAPTURE_NOT_VERIFIED",
                      **public_sqlite_disposition(state_handoff),
                      "state": public_state_receipt(state_handoff),
                      "full_application_recovery_certified": False})
                return 2
    except (OSError, sqlite3.Error, ValueError):
        emit({"ok": False, "stage": "BACKUP", "code": "SNAPSHOT_FAILED",
              "backup_created": None if state_plan is not None else False,
              **({"sqlite_disposition": "UNKNOWN_PRESERVE_AND_DO_NOT_RETRY"} if state_plan is not None else {})})
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
    state_options = {} if state_bundle is None else {"state_bundle": state_bundle}
    restored = verify_and_restore_isolated(directory, name, args.timeout,
                                          app_probe_mode=getattr(args, "app_probe_mode", None),
                                          **workspace_options, **state_options)
    emit({
        "ok": bool(restored.get("ok")),
        "stage": "COMPLETE" if restored.get("ok") else "ISOLATED_RESTORE",
        "code": restored.get("code"),
        "backup_created": True,
        "backup_name": name,
        "sha256": result.get("sha256"),
        "snapshot_bytes": check["snapshot_bytes"],
        "isolated_restore_ok": bool(restored.get("ok")),
        **({"restore_workspace": restored["restore_workspace"]}
           if "restore_workspace" in restored else {}),
        **({"restore_workspace_may_be_preserved": True}
           if (restored.get("workspace_may_be_preserved") is True
               or (restored.get("restore_workspace", {}).get("created") is True
                   and restored["restore_workspace"].get("cleanup_verified") is not True)) else {}),
        **({"state": public_state_receipt(state_handoff), "state_operation_id": state_bundle.operation_id,
            "state_proposal_sha256": state_bundle.proposal_sha256,
            "continuous_cross_store_consistency_certified": False,
            "full_application_recovery_certified": False}
           if state_handoff is not None else {}),
        **({"app_probe": restored["app_probe"], "full_application_recovery_certified": False}
           if "app_probe" in restored else {}),
    })
    return 0 if restored.get("ok") else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe manual SQLite backup and isolated restore for #327")
    parser.add_argument("--db", default=os.getenv("DB_PATH", "/data/database.db"))
    parser.add_argument("--backup-dir", default=None, help="Dedicated destination (default: operator_327)")
    parser.add_argument("--timeout", type=int, default=900, help="Shell-only budget in seconds (60-3600)")
    parser.add_argument("--restore-workspace-root", type=Path, default=None,
                        help="Explicit pre-existing Linux temporary root for ONE isolated restore/App workspace; "
                             "archive remains durable. No extra budget or data authorization; no automatic fallback.")
    parser.add_argument("--execute", action="store_true", help="Create the backup; without it, read-only preflight")
    parser.add_argument("--verify-existing", default=None, help="Recheck a named operator_327 backup, without creating one")
    parser.add_argument("--app-probe-mode", choices=("read_only", "normal_boot"), default=None,
                        help="Explicit guest App check on the SAME disposable restore; normal_boot may initialize only that clone. No extra time budget.")
    args = parser.parse_args()
    if not 60 <= args.timeout <= 3600:
        parser.error("--timeout must be between 60 and 3600 seconds")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
