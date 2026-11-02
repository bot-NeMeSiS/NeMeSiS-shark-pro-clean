"""Bounded, read-only recovery inventory. Never creates a backup or restore.

Only explicit application state roots are inspected. Secret-like names are not
opened or hashed; unclassified entries make the inventory incomplete. A complete
inventory is not an application recovery certificate or permission to copy data.
Use --metadata-only to omit all state-content reads and hashes. Backup integrity
verification is separate and is never replaced by this inventory.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from typing import Mapping

MAX_FILES = 400
MAX_DEPTH = 6
MAX_HASH_BYTES = 16 * 1024 * 1024
MAX_SECONDS = 5.0
SECRET_NAME = re.compile(r"(^\.env(?:\.|$)|secret|credential|token|^id_|\.(?:key|pem|p12|pfx)$)", re.I)
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
CONFIG_NAMES = (
    "DB_PATH", "PUBLIC_BASE_URL", "SECRET_KEY", "FLASK_SECRET_KEY", "AUTOMATION_SECRET",
    "CONTINUOUS_EVOLUTION_STORAGE_ROOT", "CONTINUOUS_EVOLUTION_SAFE_MODE",
    "BACKGROUND_JOBS_ENABLED", "AUTO_GENERATE_PICKS", "AUTO_SEND_TELEGRAM_PICKS",
    "DATA_BACKUP_ENABLED", "DATA_BACKUP_DIR", "BACKUP_DIR", "DATA_BACKUP_MAX_FILES",
    "NEMESIS_AUDIENCE_PROFILE",
)
CE_PRIMARY = frozenset((
    "automation_control.json", "product_memory.json", "scheduler_state.json",
    "native_workforce/state.json", "market_reviews.json",
    "autonomous_product_qa/control.json", "autonomous_product_qa/memory.json",
))
CE_EVIDENCE = frozenset((
    "latest_snapshot.json", "latest_run.json", "latest_founder_brief.md",
    "autonomous_product_qa/latest_run.json",
))
CE_HISTORY = ("snapshots/", "runs/", "briefs/", "job_logs/", "certifications/",
              "codex_inbox/", "autonomous_product_qa/history/")
RUNTIME_PRIMARY = frozenset((
    "sentinel_issues_memory.json", "sentinel_autopilot_memory.json",
    "company_intelligence_memory.json", "v938_company_operations/reviews.json",
))
RUNTIME_EVIDENCE = frozenset((
    "not_found_events.json", "sentinel_client_route_issues.json",
    "sentinel_authenticated_issues.json", "navigation_integrity/latest_run.json",
    "v938_company_operations/latest_scan.json",
))


class InventoryError(ValueError):
    """Only these closed diagnostic codes may enter the report."""


@dataclass(frozen=True)
class Limits:
    files: int = MAX_FILES
    depth: int = MAX_DEPTH
    hash_bytes: int = MAX_HASH_BYTES
    seconds: float = MAX_SECONDS

    def __post_init__(self):
        for value, maximum in ((self.files, MAX_FILES), (self.depth, MAX_DEPTH),
                               (self.hash_bytes, MAX_HASH_BYTES)):
            if type(value) is not int or not 0 < value <= maximum:
                raise ValueError("INVALID_INVENTORY_LIMIT")
        if type(self.seconds) not in (int, float) or not math.isfinite(self.seconds) or not 0 < self.seconds <= MAX_SECONDS:
            raise ValueError("INVALID_INVENTORY_LIMIT")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink)


def _link(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _checked_path(path: Path):
    # Do not resolve: that would follow the links this inventory must reject.
    raw = os.fspath(path)
    if not path.is_absolute() or ".." in path.parts or raw.startswith(("//", "\\\\")):
        raise InventoryError("UNSAFE_PATH")
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        if _link(info):
            raise InventoryError("LINK_STATE_NOT_VERIFIED")
    return info


def _open_for_hash(path: Path):
    # Path-based O_NOFOLLOW protects only the final component. Anchor every
    # ancestor too, so a swapped directory cannot redirect a content read.
    if os.name != "posix" or not getattr(os, "O_NOFOLLOW", 0) or os.open not in os.supports_dir_fd:
        raise InventoryError("CONFINED_HASH_UNSUPPORTED")
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def _open_directory(path: Path):
    if os.name != "posix" or not getattr(os, "O_NOFOLLOW", 0) or os.open not in os.supports_dir_fd or os.scandir not in os.supports_fd:
        raise InventoryError("CONFINED_ENUMERATION_UNSUPPORTED")
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return directory
    except BaseException:
        os.close(directory)
        raise


def _known_directory(role: str, relative: str):
    if role == "legacy_runtime" and relative == "continuous_evolution_os":
        return True
    if role == "legacy_runtime" and relative.startswith("continuous_evolution_os/"):
        role, relative = "ce", relative.removeprefix("continuous_evolution_os/")
    names = CE_PRIMARY | CE_EVIDENCE if role == "ce" else RUNTIME_PRIMARY | RUNTIME_EVIDENCE
    return (any(name.startswith(relative + "/") for name in names)
            or (role == "ce" and any(relative + "/" == prefix or relative.startswith(prefix)
                                      or prefix.startswith(relative + "/") for prefix in CE_HISTORY)))


def _classification(role: str, relative: str):
    if role == "legacy_runtime" and relative.startswith("continuous_evolution_os/"):
        relative = relative.removeprefix("continuous_evolution_os/")
        role = "ce"
    if relative == "scheduler.lock" or relative.endswith(".tmp"):
        return "TRANSIENT_NOT_RESTORED"
    primary, evidence = ((CE_PRIMARY, CE_EVIDENCE) if role == "ce"
                         else (RUNTIME_PRIMARY, RUNTIME_EVIDENCE))
    if relative in primary:
        return "PRIMARY_STATE"
    if relative in evidence:
        return "EVIDENCE"
    if role == "ce" and relative.startswith(CE_HISTORY) and Path(relative).suffix in (".json", ".jsonl", ".md", ".txt", ".log"):
        return "EVIDENCE"
    return "STATE_POLICY_REQUIRED"


def _directory_priority(role: str, relative: str):
    """Visit primary-state ancestors before history within the same limits."""
    if role == "legacy_runtime" and relative == "continuous_evolution_os":
        return 0
    if role == "legacy_runtime" and relative.startswith("continuous_evolution_os/"):
        role, relative = "ce", relative.removeprefix("continuous_evolution_os/")
    names = CE_PRIMARY if role == "ce" else RUNTIME_PRIMARY
    return 0 if any(name.startswith(relative + "/") for name in names) else 1


def collect_manifest(*, database: Path, roots: Mapping[str, Path],
                     environment: Mapping[str, str], limits: Limits = Limits(),
                     metadata_only: bool = False) -> dict:
    """Inspect existing files only. Does not connect to SQLite or import App."""
    if type(metadata_only) is not bool:
        raise ValueError("INVALID_CONTENT_MODE")
    if not roots or set(roots) - {"ce", "legacy_runtime"}:
        raise ValueError("INVALID_SCOPE_ROOTS")
    if not isinstance(database, Path) or any(not isinstance(root, Path) for root in roots.values()):
        raise ValueError("INVALID_SCOPE_PATHS")
    started = time.monotonic()
    deadline = started + limits.seconds
    result = {
        "schema": "NEMESIS_RECOVERY_SCOPE_METADATA_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "operation": "READ_ONLY_INVENTORY", "backup_created": False,
        "restore_created": False, "recovery_certified": False,
        "content_mode": "METADATA_ONLY" if metadata_only else "HASH_KNOWN_STATE",
        "configuration": {name: {"present": bool(environment.get(name))}
                          for name in CONFIG_NAMES},
        "configuration_custody": "NOT_ATTESTED",
        "database": {}, "roots": [], "files": [], "issues": [],
        "limits": {"files": limits.files, "depth": limits.depth,
                   "hash_bytes": limits.hash_bytes, "seconds": limits.seconds},
    }
    inspected = 0
    hashed_bytes = 0
    stopped = False
    # SQLite basenames are not constrained to .db. Never hash the declared
    # live database or its exact journals, even if a name matches state policy.
    db_names = {os.path.normcase(os.fspath(database) + suffix)
                for suffix in ("", "-wal", "-shm", "-journal")}

    def issue(code, role=None, path_id=None):
        value = {"code": code}
        if role is not None:
            value["scope"] = role
        if path_id is not None:
            value["path_id"] = path_id
        result["issues"].append(value)

    def check_time():
        if time.monotonic() >= deadline:
            raise InventoryError("INVENTORY_TIME_BUDGET")

    try:
        check_time()
        info = _checked_path(database)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise InventoryError("UNSAFE_DATABASE_FILE")
        result["database"] = {"state": "FILE_METADATA_ONLY", "file_bytes": info.st_size,
                              "mtime_ns": info.st_mtime_ns,
                              "sqlite_snapshot_or_integrity_verified": False,
                              "live_database_or_wal_hashed": False}
    except (OSError, ValueError, TimeoutError) as exc:
        result["database"] = {"state": "NOT_VERIFIED"}
        issue(str(exc) if isinstance(exc, InventoryError) else "DATABASE_UNAVAILABLE")

    for role, root in sorted(roots.items()):
        if stopped:
            break
        root_fact = {"scope": role, "state": "NOT_VERIFIED"}
        result["roots"].append(root_fact)
        try:
            check_time()
            root_info = _checked_path(root)
            if not stat.S_ISDIR(root_info.st_mode):
                raise InventoryError("SCOPE_NOT_DIRECTORY")
            root_fact["state"] = "OBSERVED_DIRECTORY"
            stack = [(root, 0)]
            while stack:
                stack.sort(key=lambda item: (_directory_priority(role, item[0].relative_to(root).as_posix()),
                                              item[0].relative_to(root).as_posix()), reverse=True)
                directory, depth = stack.pop()
                check_time()
                directory_info = _checked_path(directory)
                # Sorting is bounded by the entry limit, without collecting an
                # unbounded directory into a list first.
                directory_fd = _open_directory(directory)
                try:
                    if _identity(os.fstat(directory_fd)) != _identity(directory_info):
                        raise InventoryError("STATE_DIRECTORY_CHANGED")
                    with os.scandir(directory_fd) as iterator:
                        entries = []
                        for entry in iterator:
                            check_time()
                            inspected += 1
                            if inspected > limits.files:
                                raise InventoryError("INVENTORY_ENTRY_BUDGET")
                            entries.append(entry.name)
                    if _identity(os.fstat(directory_fd)) != _identity(directory_info) or _identity(_checked_path(directory)) != _identity(directory_info):
                        raise InventoryError("STATE_DIRECTORY_CHANGED")
                finally:
                    os.close(directory_fd)
                for name in sorted(entries):
                    check_time()
                    path = directory / name
                    relative = path.relative_to(root).as_posix()
                    path_id = hashlib.sha256(relative.encode("utf-8")).hexdigest()
                    if os.path.normcase(os.fspath(path)) in db_names:
                        issue("LIVE_DATABASE_SCOPE_OVERLAP", role, path_id)
                        continue
                    if any(SECRET_NAME.search(part) for part in path.relative_to(root).parts):
                        issue("SECRET_CUSTODY_NOT_ATTESTED", role, path_id)
                        # Never open/hash or print the name of a secret-like file.
                        continue
                    info = _checked_path(path)
                    if stat.S_ISDIR(info.st_mode):
                        if not _known_directory(role, relative):
                            issue("STATE_POLICY_REQUIRED", role, path_id)
                        elif depth >= limits.depth:
                            issue("INVENTORY_DEPTH_BUDGET", role, path_id)
                        else:
                            stack.append((path, depth + 1))
                        continue
                    category = _classification(role, relative)
                    fact = {"scope": role, "path_id": path_id, "classification": category,
                            "hash_state": "NOT_HASHED", "sha256": None}
                    result["files"].append(fact)
                    if not all(SAFE_COMPONENT.fullmatch(part) for part in path.relative_to(root).parts):
                        issue("PRIVATE_OR_UNCLASSIFIED_NAME", role, path_id)
                        continue
                    if category == "STATE_POLICY_REQUIRED":
                        issue(category, role, path_id)
                        continue
                    # Dynamic history names can contain identifiers. Their
                    # opaque path ID binds the fact without disclosing names.
                    static_names = CE_PRIMARY | CE_EVIDENCE | RUNTIME_PRIMARY | RUNTIME_EVIDENCE
                    static_relative = relative.removeprefix("continuous_evolution_os/") if role == "legacy_runtime" else relative
                    if static_relative in static_names or static_relative == "scheduler.lock":
                        fact["relative_path"] = relative
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        issue("UNSAFE_STATE_FILE", role, path_id)
                        continue
                    fact["bytes"] = info.st_size
                    fact["mtime_ns"] = info.st_mtime_ns
                    if category == "TRANSIENT_NOT_RESTORED":
                        continue
                    if metadata_only:
                        if _identity(_checked_path(path)) != _identity(info):
                            raise InventoryError("STATE_FILE_CHANGED")
                        fact["hash_state"] = "NOT_REQUESTED_METADATA_ONLY"
                        continue
                    if info.st_size > limits.hash_bytes - hashed_bytes:
                        issue("INVENTORY_HASH_BUDGET", role, path_id)
                        continue
                    descriptor = _open_for_hash(path)
                    with os.fdopen(descriptor, "rb") as stream:
                        opened = os.fstat(stream.fileno())
                        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(info) or _link(opened):
                            raise InventoryError("STATE_FILE_CHANGED")
                        digest = hashlib.sha256()
                        consumed = 0
                        while True:
                            check_time()
                            block = stream.read(min(65536, limits.hash_bytes - hashed_bytes + 1))
                            if not block:
                                break
                            consumed += len(block)
                            hashed_bytes += len(block)
                            if hashed_bytes > limits.hash_bytes or consumed > info.st_size:
                                raise InventoryError("INVENTORY_HASH_BUDGET")
                            digest.update(block)
                        if consumed != info.st_size or _identity(os.fstat(stream.fileno())) != _identity(info):
                            raise InventoryError("STATE_FILE_CHANGED")
                    if _identity(_checked_path(path)) != _identity(info):
                        raise InventoryError("STATE_FILE_CHANGED")
                    fact.update(hash_state="HASHED_STABLE_FILE", sha256=digest.hexdigest())
        except FileNotFoundError:
            root_fact["state"] = "NOT_PRESENT_OR_CHANGED"
            issue("SCOPE_NOT_PRESENT_OR_CHANGED", role)
        except (OSError, ValueError, TimeoutError) as exc:
            root_fact["state"] = "INCOMPLETE"
            code = str(exc) if isinstance(exc, InventoryError) else "SCOPE_UNAVAILABLE"
            issue(code, role)
            if code in ("INVENTORY_TIME_BUDGET", "INVENTORY_ENTRY_BUDGET", "INVENTORY_HASH_BUDGET"):
                stopped = True

    result["entries_inspected"] = inspected
    result["bytes_hashed"] = hashed_bytes
    result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    result["inventory_status"] = "INCOMPLETE" if result["issues"] else "OBSERVED_DECLARED_ROOTS_ONLY"
    result["scope_limit"] = "Explicit roots only; absent/unknown state, secret custody, code identity, application restore and cross-store consistency are not certified."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--ce-root", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--metadata-only", action="store_true",
                        help="Observe names and file metadata without opening state content; not an integrity check.")
    parser.add_argument("--scope", choices=("both", "ce", "legacy_runtime"), default="both",
                        help="Restrict the declared roots for this bounded observation (default: both).")
    args = parser.parse_args(argv)
    roots = {"ce": args.ce_root, "legacy_runtime": args.runtime_root}
    if args.scope != "both":
        roots = {args.scope: roots[args.scope]}
    report = collect_manifest(database=args.db, roots=roots, environment=os.environ,
                              metadata_only=args.metadata_only)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report["inventory_status"] == "OBSERVED_DECLARED_ROOTS_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
