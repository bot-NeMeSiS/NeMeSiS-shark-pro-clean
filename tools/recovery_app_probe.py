"""Explicit App smoke on an existing isolated restoration, never on live data.

NORMAL_BOOT permits genuine initialization only inside the disposable working
copy. READ_ONLY is a separate diagnostic: seed/write attempts remain failures.
Neither mode certifies authentication, external services or complete recovery.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import subprocess
import sys
import time

MIB = 1024 * 1024
SOURCE_MAX_FILES = 6000
SOURCE_MAX_BYTES = 128 * MIB
EXCLUDED_ROOTS = frozenset(("data", "backups", "logs", "tests", "node_modules", ".git", ".venv"))
SOURCE_ROOTS = frozenset(("engines", "services", "blueprints", "automation_workforce", "config",
                          "localization", "static", "templates", "project_control", "reference_images"))
SOURCE_SUFFIXES = frozenset((".py", ".html", ".css", ".js", ".json", ".txt", ".md",
                             ".svg", ".png", ".webp", ".jpg", ".jpeg", ".ico", ".woff",
                             ".woff2", ".ttf", ".yml", ".yaml"))
SECRET_NAME = re.compile(r"^\.env(?:\.|$)|\.(?:key|pem|p12|pfx)\Z", re.I)
SECRET_DATA_NAME = re.compile(r"(?:credential|secret|password|private[_-]?key|access[_-]?token).*\.(?:json|txt|ya?ml)\Z", re.I)
DEFAULT_ROUTES = ("/calendario", "/", "/picks", "/shark", "/team/real-madrid", "/api/sports-search?q=owned&kind=team")
# Fixed canonical probes only; these paths do not represent every manifest entry.
STATE_CONSUMER_PATHS = {
    "legacy_runtime": Path("data/runtime/sentinel_issues_memory.json"),
    "ce": Path("data/continuous_evolution_os/product_memory.json"),
}
MAX_CONSUMER_COMPARE_BYTES = 1 * MIB
# The disjoint layout is synthetic fixture evidence, never a production attestation.
STATE_LAYOUT = "DISJOINT_CE_LEGACY_V1"
STATE_LAYOUT_MODEL = "SYNTHETIC_DISJOINT_CE_LEGACY_V1"
STATE_LAYOUT_PROVENANCE = "SYNTHETIC_FIXTURE_ONLY"
# V3 keeps the synthetic disjoint fixture contract for compatibility.
COLOCATED_LAYOUT_ID = "CE_COLOCATED_SENTINEL_AND_RUNTIME_AUTOPILOT_V1"
COLOCATED_LAYOUT_MODEL = COLOCATED_LAYOUT_ID
COLOCATED_LAYOUT_PROVENANCE = "SYNTHETIC_FIXTURE_ONLY"
COLOCATED_SCOPE_ROLES = ("ce", "legacy_runtime")
COLOCATED_CONSUMERS = (
    {"consumer_id": "ce_product_memory", "scope_role": "ce",
     "relative_path": Path("data/continuous_evolution_os/product_memory.json"),
     "owner": "engines.product_review_system_engine.load_product_memory", "kind": "product"},
    {"consumer_id": "ce_sentinel_issues", "scope_role": "ce",
     "relative_path": Path("data/continuous_evolution_os/sentinel_issues_memory.json"),
     "owner": "engines.sentinel_issues_engine.load_sentinel_issues_memory", "kind": "sentinel"},
    {"consumer_id": "runtime_sentinel_autopilot", "scope_role": "legacy_runtime",
     "relative_path": Path("data/runtime/sentinel_autopilot_memory.json"),
     "owner": "engines.sentinel_issues_engine._issues_from_autopilot_memory", "kind": "autopilot"},
)
COLOCATED_CONSUMER_IDS = tuple(spec["consumer_id"] for spec in COLOCATED_CONSUMERS)


def _colocated_consumer_receipt_rows():
    return [
        {"consumer_id": spec["consumer_id"], "scope_role": spec["scope_role"],
         "relative_path": spec["relative_path"].as_posix(), "owner": spec["owner"]}
        for spec in COLOCATED_CONSUMERS
    ]


def _prepare_colocated_consumer_targets(source: Path, roles, *, deadline: float, max_bytes: int):
    if tuple(roles) != COLOCATED_SCOPE_ROLES:
        raise ProbeError("STATE_CONSUMER_LAYOUT_ROLES")
    targets, missing, total = {}, [], 0
    for spec in COLOCATED_CONSUMERS:
        path = source / spec["relative_path"]
        try:
            info = _checked(path)
        except FileNotFoundError:
            missing.append(spec["consumer_id"])
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ProbeError("STATE_CONSUMER_IDENTITY")
        if info.st_size <= 0 or info.st_size > min(max_bytes, MAX_CONSUMER_COMPARE_BYTES):
            missing.append(spec["consumer_id"])
            continue
        size, digest, _ = _read_state_consumer_file(
            path, deadline=deadline, max_bytes=min(max_bytes, MAX_CONSUMER_COMPARE_BYTES))
        if size <= 0:
            missing.append(spec["consumer_id"])
            continue
        total += size
        if total > max_bytes:
            raise ProbeError("STATE_CONSUMER_BYTE_BUDGET")
        targets[spec["consumer_id"]] = {"bytes": size, "sha256": digest}
    return targets, missing


def _canonical_issue_pairs(rows):
    if not isinstance(rows, list):
        return None
    pairs = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        issue_id = item.get("id") or item.get("issue_id")
        alternate_id = item.get("issue_id") or item.get("id")
        if not isinstance(issue_id, str) or not issue_id or not isinstance(alternate_id, str) or not alternate_id:
            return None
        pairs.append((issue_id, alternate_id))
    return pairs


def _canonical_autopilot_ids(rows, *, normalized: bool):
    if not isinstance(rows, list):
        return None
    ids = []
    for item in rows:
        if not isinstance(item, dict):
            return None
        issue_id = item.get("id") if normalized else (item.get("id") or item.get("issue_id"))
        if not isinstance(issue_id, str) or not issue_id:
            return None
        ids.append(issue_id)
    return ids


def _colocated_projection_matches(spec, value, stored, expected_sha256, *, full_read: bool):
    if (full_read is not True or not isinstance(stored, dict)
            or not isinstance(expected_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None):
        return False
    if spec["kind"] == "product":
        if not isinstance(value, dict) or "recommendations" not in stored or "recommendations" not in value:
            return False
        return (isinstance(stored["recommendations"], dict)
                and isinstance(value["recommendations"], dict)
                and value["recommendations"] == stored["recommendations"])
    if spec["kind"] == "sentinel":
        if not isinstance(value, dict) or value.get("_storage_revision") != expected_sha256:
            return False
        stored_pairs = _canonical_issue_pairs(stored.get("issues"))
        observed_pairs = _canonical_issue_pairs(value.get("issues"))
        return stored_pairs is not None and stored_pairs == observed_pairs
    if spec["kind"] == "autopilot":
        if not isinstance(value, list) or not isinstance(stored.get("issues"), list):
            return False
        stored_ids = _canonical_autopilot_ids(stored["issues"], normalized=False)
        observed_ids = _canonical_autopilot_ids(value, normalized=True)
        return stored_ids is not None and stored_ids == observed_ids
    return False


def _observe_colocated_state_consumers(payload, source: Path, boundary, *, routes_verified: bool = True) -> dict:
    """Observe three fixed owners in the explicitly selected synthetic co-located layout."""
    roles = payload.get("restored_state_scope_roles")
    targets = payload.get("restored_state_targets")
    mode = payload.get("mode")
    rows = _colocated_consumer_receipt_rows()
    proof = {
        "schema": "NEMESIS_CANONICAL_CONSUMER_OBSERVATION_V4",
        "verified": False,
        "canonical_consumer_consumption_verified": False,
        "layout_id": COLOCATED_LAYOUT_ID,
        "layout_model": COLOCATED_LAYOUT_MODEL,
        "layout_provenance": COLOCATED_LAYOUT_PROVENANCE,
        "production_layout_attested": False,
        "full_application_recovery_certified": False,
        "observation_scope": "THREE_FIXED_CANONICAL_CONSUMERS_ONLY",
        "universal_scope_consumption_verified": False,
        "mode": mode if mode in ("normal_boot", "read_only") else "UNKNOWN",
        "scope_roles": list(COLOCATED_SCOPE_ROLES),
        "canonical_consumer_paths": rows,
        "observed_roles": [],
        "observed_consumer_ids": [],
        "successful_full_file_reads": False,
        "getters_read_only": False,
        "same_restored_workspace": False,
        "same_sqlite_boundary": False,
        "same_deadline": False,
        "canonical_value_projections_match_restored_bytes": False,
        "decoy_open_not_attempted_during_getters": False,
        "getters_wrote_nothing": False,
        "bundle_all_files_restored_verified": payload.get("restored_state_bundle_all_files_restored_verified") is True,
    }
    if not routes_verified:
        proof["code"] = "APP_ROUTES_NOT_VERIFIED"
        return proof
    if (payload.get("restored_state_layout") != COLOCATED_LAYOUT_ID
            or payload.get("restored_state_layout_provenance") != COLOCATED_LAYOUT_PROVENANCE
            or not isinstance(roles, list) or roles != list(COLOCATED_SCOPE_ROLES)
            or not isinstance(targets, dict) or set(targets) != set(COLOCATED_CONSUMER_IDS)):
        proof["code"] = "STATE_CONSUMER_TARGETS_INCOMPLETE"
        return proof
    total = 0
    for consumer_id in COLOCATED_CONSUMER_IDS:
        target = targets[consumer_id]
        if (not isinstance(target, dict) or set(target) != {"bytes", "sha256"}
                or type(target["bytes"]) is not int or not 0 < target["bytes"] <= MAX_CONSUMER_COMPARE_BYTES
                or not isinstance(target["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", target["sha256"]) is None):
            proof["code"] = "STATE_CONSUMER_TARGETS_INVALID"
            return proof
        total += target["bytes"]
    if total > 16 * MIB:
        proof["code"] = "STATE_CONSUMER_BYTE_BUDGET"
        return proof

    try:
        _deadline(payload["deadline"])
        if mode not in ("normal_boot", "read_only"):
            raise ProbeError("STATE_CONSUMER_MODE")
        if Path.cwd() != source or source != Path(payload["source"]):
            raise ProbeError("STATE_CONSUMER_WORKSPACE_BINDING")
        app = sys.modules.get("app")
        if app is None or Path(app.__file__) != source / "app.py":
            raise ProbeError("STATE_CONSUMER_APP_IDENTITY")
        ce_root = source / "data" / "continuous_evolution_os"
        runtime_root = source / "data" / "runtime"
        ce_path = ce_root / "product_memory.json"
        sentinel_path = ce_root / "sentinel_issues_memory.json"
        autopilot_path = runtime_root / "sentinel_autopilot_memory.json"
        if (os.environ.get("CONTINUOUS_EVOLUTION_SAFE_MODE", "").strip() != "1"
                or os.environ.get("CONTINUOUS_EVOLUTION_STORAGE_ROOT") != str(ce_root)):
            raise ProbeError("STATE_CONSUMER_CE_ROOT")
        ce = sys.modules.get("engines.product_review_system_engine")
        sentinel = sys.modules.get("engines.sentinel_issues_engine")
        if (ce is None or Path(ce.__file__) != source / "engines" / "product_review_system_engine.py"
                or ce._ce_storage() != ce_root):
            raise ProbeError("STATE_CONSUMER_CE_IDENTITY")
        if (sentinel is None or Path(sentinel.__file__) != source / "engines" / "sentinel_issues_engine.py"
                or sentinel.sentinel_issues_memory_path() != sentinel_path
                or sentinel._autopilot_memory_path() != autopilot_path):
            raise ProbeError("STATE_CONSUMER_SENTINEL_IDENTITY")
        readers = {
            "ce_product_memory": (ce.load_product_memory, ce, "ce"),
            "ce_sentinel_issues": (sentinel.load_sentinel_issues_memory, sentinel, "ce"),
            "runtime_sentinel_autopilot": (sentinel._issues_from_autopilot_memory, sentinel, "legacy_runtime"),
        }
        for spec in COLOCATED_CONSUMERS:
            reader = readers[spec["consumer_id"]][0]
            owner_module_name, owner_name = spec["owner"].rsplit(".", 1)
            if (not callable(reader) or getattr(reader, "__module__", None) != owner_module_name
                    or getattr(reader, "__name__", None) != owner_name
                    or not hasattr(reader, "__code__")
                    or Path(reader.__code__.co_filename).resolve()
                       != source / Path(*owner_module_name.split(".")).with_suffix(".py")):
                raise ProbeError("STATE_CONSUMER_OWNER_UNAVAILABLE")
        bound = getattr(sqlite3.connect, "__self__", None)
        if (bound is not boundary or boundary.source != source
                or boundary.database != Path(payload["database"])
                or boundary.deadline != payload["deadline"] or boundary.mode != mode):
            raise ProbeError("STATE_CONSUMER_BOUNDARY_BINDING")
        proof["same_restored_workspace"] = True
        proof["same_sqlite_boundary"] = True
        proof["same_deadline"] = True

        before_writes, before_sql_writes = boundary.fs_writes, boundary.sql_writes
        before_denials = len(boundary.denials)
        before_decoys = boundary._state_decoy_open_attempts
        for spec in COLOCATED_CONSUMERS:
            consumer_id = spec["consumer_id"]
            path = source / spec["relative_path"]
            expected = targets[consumer_id]
            size_before, digest_before, _ = _read_state_consumer_file(
                path, deadline=payload["deadline"], max_bytes=MAX_CONSUMER_COMPARE_BYTES)
            if size_before != expected["bytes"] or digest_before != expected["sha256"]:
                raise ProbeError("STATE_CONSUMER_RESTORED_BYTES_CHANGED")
            reader, owner_module, role = readers[consumer_id]
            if ((role == "ce" and owner_module not in (ce, sentinel))
                    or (role == "legacy_runtime" and owner_module is not sentinel)):
                raise ProbeError("STATE_CONSUMER_OWNER_BINDING")
            value, open_attempts, full_reads = boundary.observe_state_file(role, path, reader)
            size_after, digest_after, raw_after = _read_state_consumer_file(
                path, deadline=payload["deadline"], max_bytes=MAX_CONSUMER_COMPARE_BYTES, include_bytes=True)
            if (open_attempts <= 0 or full_reads <= 0 or size_after != expected["bytes"]
                    or digest_after != expected["sha256"]):
                raise ProbeError("STATE_CONSUMER_FULL_READ_NOT_BOUND_TO_RESTORE")
            stored = _decode_state_consumer_json(raw_after)
            if not _colocated_projection_matches(
                    spec, value, stored, expected["sha256"], full_read=full_reads > 0):
                raise ProbeError("STATE_CONSUMER_PROJECTION_MISMATCH")
            proof["observed_consumer_ids"].append(consumer_id)
            if role not in proof["observed_roles"]:
                proof["observed_roles"].append(role)
        _deadline(payload["deadline"])
        proof["observed_roles"].sort()
        proof["successful_full_file_reads"] = proof["observed_consumer_ids"] == list(COLOCATED_CONSUMER_IDS)
        proof["getters_read_only"] = (
            boundary.fs_writes == before_writes and boundary.sql_writes == before_sql_writes
            and len(boundary.denials) == before_denials
        )
        proof["decoy_open_not_attempted_during_getters"] = boundary._state_decoy_open_attempts == before_decoys
        proof["canonical_value_projections_match_restored_bytes"] = True
        proof["getters_wrote_nothing"] = proof["getters_read_only"]
        proof["verified"] = (
            proof["bundle_all_files_restored_verified"] and proof["successful_full_file_reads"]
            and proof["getters_read_only"] and proof["decoy_open_not_attempted_during_getters"]
            and proof["observed_roles"] == list(COLOCATED_SCOPE_ROLES)
            and proof["observed_consumer_ids"] == list(COLOCATED_CONSUMER_IDS)
        )
        proof["canonical_consumer_consumption_verified"] = proof["verified"]
        if not proof["verified"]:
            proof["code"] = "STATE_CONSUMER_OBSERVATION_INCOMPLETE"
    except ProbeError as exc:
        proof["code"] = str(exc)
    except BaseException:
        proof["code"] = "STATE_CONSUMER_OBSERVATION_FAILED"
    return proof



def _admitted_route(route):
    return isinstance(route, str) and (route in (*DEFAULT_ROUTES, "/health", "/app")
        or re.fullmatch(r"/team/[A-Za-z0-9][A-Za-z0-9_-]{0,79}", route) is not None)


def _storage_states(context):
    """Observe only closed status categories; never retain values or page data."""
    pending, observed, visited = [(context, 0)], set(), 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > 400:
            observed.add("OBSERVATION_LIMIT")
            break
        if not isinstance(value, dict) or depth > 7:
            continue
        for key, item in value.items():
            if key in ("storage_status", "picks_storage_status", "source_read_state"):
                observed.add("OK" if item in ("ok", "route_not_required", "not_required") else "UNAVAILABLE_OR_UNKNOWN")
            elif isinstance(item, dict):
                pending.append((item, depth+1))
    return sorted(observed)


def _search_ready(payload):
    return (isinstance(payload, dict) and payload.get("ok") is True
            and payload.get("status") == "READY" and payload.get("complete") is True)


def _progress_events(raw, nonce):
    if len(raw) > 4096:
        raise ProbeError("APP_PROBE_PROTOCOL_FAILED")
    events = []
    for line in raw.splitlines():
        item = json.loads(line)
        if (not isinstance(item, dict) or item.get("nonce") != nonce
                or item.get("stage") not in ("CHILD_READY", "GUARD_INSTALLED", "APP_IMPORTED", "ROUTE_STARTED", "ROUTE_FINISHED")):
            raise ProbeError("APP_PROBE_PROTOCOL_FAILED")
        events.append(item["stage"])
    return events


def _use_packaged_timezones():
    """Use the already-declared tzdata input, without granting OS symlinks.

    Linux's UTC entry may be a symlink. The fixed probe deliberately refuses
    filesystem links; a dependency-provided timezone database avoids making a
    blanket exception. No zone is constructed/cached before the App guard.
    """
    import zoneinfo
    from importlib.metadata import version, PackageNotFoundError
    try:
        installed = version("tzdata")
    except PackageNotFoundError:
        raise ProbeError("APP_TIMEZONE_DATA_MISSING") from None
    if not re.fullmatch(r"[0-9]{4}\.[0-9]+", installed):
        raise ProbeError("APP_TIMEZONE_DATA_VERSION_UNSUPPORTED")
    zoneinfo.reset_tzpath(())
    zoneinfo.ZoneInfo.clear_cache()
    if zoneinfo.TZPATH:
        raise ProbeError("APP_TIMEZONE_SOURCE_NOT_CONFINED")
    return {"source": "DECLARED_TZDATA_PACKAGE", "version": installed, "system_paths_enabled": False,
            "production_timezone_source_attested": False}


class ProbeError(ValueError):
    """Closed codes only: no paths, SQL, rows or exception messages in receipts."""


def _checked(path: Path):
    if not path.is_absolute() or ".." in path.parts or str(path).startswith(("//", "\\\\")):
        raise ProbeError("UNSAFE_PROBE_PATH")
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ProbeError("PROBE_LINK_REJECTED")
    return info


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink


def _deadline(deadline):
    if time.monotonic() >= deadline:
        raise ProbeError("APP_PROBE_DEADLINE_EXPIRED")


def _source_descriptor(root, relative, root_identity):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    if os.name != "posix" or os.open not in os.supports_dir_fd or not getattr(os, "O_NOFOLLOW", 0):
        # Windows additionally rechecks ancestor/reparse identities before and
        # after open; the file descriptor identity is checked BEFORE any read.
        return os.open(root / relative, flags)
    directory_flags = flags | os.O_DIRECTORY
    handles = []
    try:
        current = os.open(root, directory_flags)
        handles.append(current)
        if _identity(os.fstat(current)) != root_identity:
            raise ProbeError("SOURCE_CHANGED")
        for component in relative.parts[:-1]:
            current = os.open(component, directory_flags, dir_fd=current)
            handles.append(current)
        return os.open(relative.name, flags, dir_fd=current)
    finally:
        for descriptor in reversed(handles):
            os.close(descriptor)


def prepare_source(project_root: Path, workspace: Path, *, deadline: float) -> dict:
    """Copy code/assets only; production runtime data and secret files are excluded."""
    _deadline(deadline)
    if not stat.S_ISDIR(_checked(project_root).st_mode) or not stat.S_ISDIR(_checked(workspace).st_mode):
        raise ProbeError("PROBE_DIRECTORY_REQUIRED")
    root_identity = _identity(_checked(project_root))
    if workspace.is_relative_to(project_root) and workspace.relative_to(project_root).parts[:1] not in tuple((k,) for k in EXCLUDED_ROOTS):
        raise ProbeError("SOURCE_AND_WORKSPACE_OVERLAP")
    destination = workspace / "source"
    destination.mkdir()
    files, copied, aggregate = 0, 0, hashlib.sha256()
    pending = [(project_root, destination)]
    while pending:
        current, target = pending.pop()
        _deadline(deadline)
        initial = _identity(_checked(current))
        with os.scandir(current) as entries:
            for entry in entries:
                _deadline(deadline)
                relative = Path(entry.path).relative_to(project_root)
                if relative.parts[0] in EXCLUDED_ROOTS or any(p == "__pycache__" or p.startswith(".") for p in relative.parts):
                    continue
                if len(relative.parts) == 1 and entry.is_dir(follow_symlinks=False) and entry.name not in SOURCE_ROOTS:
                    continue
                if len(relative.parts) == 1 and not entry.is_dir(follow_symlinks=False) and relative.suffix != ".py" and entry.name not in ("APP_VERSION", "VERSION.txt"):
                    continue
                if SECRET_NAME.search(entry.name) or SECRET_DATA_NAME.search(entry.name):
                    continue
                info = _checked(Path(entry.path))
                if stat.S_ISDIR(info.st_mode):
                    child = target / entry.name
                    child.mkdir()
                    pending.append((Path(entry.path), child))
                    continue
                if relative.suffix.lower() not in SOURCE_SUFFIXES and relative.as_posix() != "APP_VERSION":
                    continue
                files += 1
                if files > SOURCE_MAX_FILES or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ProbeError("SOURCE_FILE_NOT_ADMITTED")
                if info.st_size > SOURCE_MAX_BYTES - copied:
                    raise ProbeError("SOURCE_BYTE_BUDGET")
                descriptor = _source_descriptor(project_root, relative, root_identity)
                digest = hashlib.sha256()
                with os.fdopen(descriptor, "rb") as source, (target / entry.name).open("xb") as output:
                    if _identity(os.fstat(source.fileno())) != _identity(info):
                        raise ProbeError("SOURCE_CHANGED")
                    consumed = 0
                    while True:
                        _deadline(deadline)
                        block = source.read(65536)
                        if not block:
                            break
                        consumed += len(block)
                        copied += len(block)
                        if consumed > info.st_size or copied > SOURCE_MAX_BYTES:
                            raise ProbeError("SOURCE_BYTE_BUDGET")
                        digest.update(block)
                        output.write(block)
                    if consumed != info.st_size or _identity(os.fstat(source.fileno())) != _identity(info):
                        raise ProbeError("SOURCE_CHANGED")
                if _identity(_checked(Path(entry.path))) != _identity(info):
                    raise ProbeError("SOURCE_CHANGED")
                aggregate.update(relative.as_posix().encode() + b"\0" + digest.digest())
        if _identity(_checked(current)) != initial:
            raise ProbeError("SOURCE_CHANGED")
    if not (destination / "app.py").is_file():
        raise ProbeError("APP_SOURCE_NOT_FOUND")
    return {"path": destination, "files": files, "bytes": copied, "observed_source_digest": aggregate.hexdigest(),
            "source_directory_anchoring": "POSIX_DIRFD" if os.name == "posix" else "ANCESTOR_AND_DESCRIPTOR_IDENTITY_RECHECK",
            "excluded_runtime_roots_copied": False, "excluded_secret_filenames_copied": False}


def _render_memory_gate(limit: int) -> dict:
    """Own App budget; metadata-reader allowances do not apply here."""
    if not any(os.environ.get(k) for k in ("RENDER_SERVICE_ID", "RENDER", "RENDER_GIT_COMMIT")):
        return {"state": "NOT_RENDER", "allowed": True, "reservation_certified": False}
    try:
        root = Path("/sys/fs/cgroup")
        current = int((root / "memory.current").read_text())
        maximum = int((root / "memory.max").read_text())
        values = dict(line.split() for line in (root / "memory.stat").read_text().splitlines())
        required = ("anon", "kernel", "file", "inactive_file", "file_dirty", "file_writeback", "shmem", "file_mapped", "unevictable")
        stats = {k: int(values[k]) for k in required}
        events = {k: int(v) for k, v in (line.split() for line in (root / "memory.events").read_text().splitlines())}
        if any(k not in events or events[k] < 0 for k in ("oom", "oom_kill", "max")):
            raise ValueError()
        if min(current, maximum) <= 0 or current >= maximum or any(v < 0 or v > current for v in stats.values()):
            raise ValueError()
        credit = max(0, min(stats["file"], stats["inactive_file"]) - sum(stats[k] for k in ("file_dirty", "file_writeback", "shmem", "file_mapped", "unevictable")))
        working = max(current - credit, stats["anon"] + stats["kernel"])
        return {"state": "OBSERVED_NOT_RESERVED", "allowed": working + limit + 32 * MIB < maximum,
                "working_estimate_bytes": working, "child_limit_bytes": limit,
                "margin_bytes": 32 * MIB, "cgroup_limit_bytes": maximum,
                "events_baseline": {k: events[k] for k in ("oom", "oom_kill", "max")},
                "reservation_certified": False}
    except (OSError, ValueError, KeyError):
        return {"state": "NOT_VERIFIED", "allowed": False, "reservation_certified": False}




def _read_state_consumer_file(path: Path, *, deadline: float, max_bytes: int,
                              include_bytes: bool = False) -> tuple[int, str, bytes | None]:
    """Read one fixed restored consumer file under the same deadline and byte cap."""
    _deadline(deadline)
    if type(max_bytes) is not int or not 0 < max_bytes <= 16 * MIB:
        raise ProbeError("STATE_CONSUMER_BYTE_BUDGET")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        raise ProbeError("STATE_CONSUMER_NOFOLLOW_UNAVAILABLE")
    before = _checked(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ProbeError("STATE_CONSUMER_IDENTITY")
    flags = os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags)
    digest, size, chunks = hashlib.sha256(), 0, []
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise ProbeError("STATE_CONSUMER_IDENTITY_CHANGED")
        while True:
            _deadline(deadline)
            block = os.read(descriptor, min(65536, max_bytes - size + 1))
            if not block:
                break
            size += len(block)
            if size > max_bytes:
                raise ProbeError("STATE_CONSUMER_BYTE_BUDGET")
            digest.update(block)
            if include_bytes:
                chunks.append(block)
        after_fd = os.fstat(descriptor)
        after_path = _checked(path)
        if (_identity(after_fd) != _identity(opened) or _identity(after_path) != _identity(opened)
                or not stat.S_ISREG(after_path.st_mode) or after_path.st_nlink != 1):
            raise ProbeError("STATE_CONSUMER_IDENTITY_CHANGED")
        if size != opened.st_size:
            raise ProbeError("STATE_CONSUMER_SIZE_MISMATCH")
    finally:
        os.close(descriptor)
    _deadline(deadline)
    return size, digest.hexdigest(), (b"".join(chunks) if include_bytes else None)


def _prepare_state_consumer_targets(source: Path, roles, *, deadline: float, max_bytes: int):
    """Hash only fixed consumer files already present in the verified restore."""
    targets, missing, total = {}, [], 0
    for role in sorted(roles):
        relative = STATE_CONSUMER_PATHS.get(role)
        if relative is None:
            raise ProbeError("STATE_CONSUMER_ROLE_UNSUPPORTED")
        path = source / relative
        try:
            info = _checked(path)
        except FileNotFoundError:
            missing.append(role)
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ProbeError("STATE_CONSUMER_IDENTITY")
        if info.st_size <= 0 or info.st_size > min(max_bytes, MAX_CONSUMER_COMPARE_BYTES):
            missing.append(role)
            continue
        size, digest, _ = _read_state_consumer_file(
            path, deadline=deadline, max_bytes=min(max_bytes, MAX_CONSUMER_COMPARE_BYTES))
        if size <= 0:
            missing.append(role)
            continue
        total += size
        if total > max_bytes:
            raise ProbeError("STATE_CONSUMER_BYTE_BUDGET")
        targets[role] = {"bytes": size, "sha256": digest}
    return targets, missing


def _decode_state_consumer_json(raw: bytes) -> dict:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, UnicodeError):
        raise ProbeError("STATE_CONSUMER_STORED_FORMAT") from None
    if not isinstance(value, dict):
        raise ProbeError("STATE_CONSUMER_STORED_FORMAT")
    return value


def _canonical_state_projection_matches(role, value, stored, expected_sha256, *, full_read: bool) -> bool:
    """Compare only stable, named projections after one complete native-file read."""
    if (full_read is not True or not isinstance(value, dict) or not isinstance(stored, dict)
            or not isinstance(expected_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None):
        return False
    if role == "legacy_runtime":
        if value.get("_storage_revision") != expected_sha256:
            return False
        stored_issues, observed_issues = stored.get("issues"), value.get("issues")
        if not isinstance(stored_issues, list) or not isinstance(observed_issues, list):
            return False
        if any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
               for item in stored_issues + observed_issues):
            return not stored_issues and not observed_issues
        stored_ids = {item["id"] for item in stored_issues}
        observed_ids = {item["id"] for item in observed_issues}
        return stored_ids.issubset(observed_ids) if stored_ids else not observed_ids
    if role == "ce":
        if "recommendations" not in stored or "recommendations" not in value:
            return False
        stored_recommendations = stored["recommendations"]
        observed_recommendations = value["recommendations"]
        return (isinstance(stored_recommendations, dict)
                and isinstance(observed_recommendations, dict)
                and observed_recommendations == stored_recommendations)
    return False


def _observe_restored_state_consumers(payload, source: Path, boundary) -> dict:
    """Observe fixed canonical consumers; this is not evidence of universal scope consumption."""
    if payload.get("restored_state_layout") == COLOCATED_LAYOUT_ID:
        return _observe_colocated_state_consumers(payload, source, boundary)
    roles = payload.get("restored_state_scope_roles")
    targets = payload.get("restored_state_targets")
    mode = payload.get("mode")
    proof = {
        "schema": "NEMESIS_CANONICAL_CONSUMER_OBSERVATION_V3",
        "verified": False,
        "canonical_consumer_consumption_verified": False,
        "layout_model": STATE_LAYOUT_MODEL,
        "layout_provenance": STATE_LAYOUT_PROVENANCE,
        "production_layout_attested": False,
        "observation_scope": "CANONICAL_GETTER_BRACKETS_ONLY",
        "mode": mode if mode in ("normal_boot", "read_only") else "UNKNOWN",
        "canonical_consumer_paths": [],
        "observed_roles": [],
        "successful_full_file_reads": False,
        "getters_read_only": False,
        "same_restored_workspace": False,
        "same_sqlite_boundary": False,
        "same_deadline": False,
        "canonical_value_projections_match_restored_bytes": False,
        "decoy_open_not_attempted_during_getters": False,
        "getters_wrote_nothing": False,
    }
    if (payload.get("restored_state_layout") != STATE_LAYOUT
            or payload.get("restored_state_layout_provenance") != STATE_LAYOUT_PROVENANCE
            or not isinstance(roles, list) or any(type(role) is not str for role in roles)
            or roles != sorted(set(roles)) or not 1 <= len(roles) <= 2
            or set(roles) - set(STATE_CONSUMER_PATHS) or not isinstance(targets, dict)
            or set(targets) != set(roles)):
        proof["code"] = "STATE_CONSUMER_TARGETS_INCOMPLETE"
        return proof
    proof["canonical_consumer_paths"] = [
        {"scope_role": role, "path": STATE_CONSUMER_PATHS[role].as_posix()}
        for role in roles
    ]
    total = 0
    for role, target in targets.items():
        if (not isinstance(target, dict) or set(target) != {"bytes", "sha256"}
                or type(target["bytes"]) is not int or not 0 < target["bytes"] <= MAX_CONSUMER_COMPARE_BYTES
                or not isinstance(target["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", target["sha256"]) is None):
            proof["code"] = "STATE_CONSUMER_TARGETS_INVALID"
            return proof
        total += target["bytes"]
    if total > 16 * MIB:
        proof["code"] = "STATE_CONSUMER_BYTE_BUDGET"
        return proof

    try:
        _deadline(payload["deadline"])
        if mode not in ("normal_boot", "read_only"):
            raise ProbeError("STATE_CONSUMER_MODE")
        if Path.cwd() != source or source != Path(payload["source"]):
            raise ProbeError("STATE_CONSUMER_WORKSPACE_BINDING")
        app = sys.modules.get("app")
        if app is None or Path(app.__file__) != source / "app.py":
            raise ProbeError("STATE_CONSUMER_APP_IDENTITY")
        ce_path = source / STATE_CONSUMER_PATHS["ce"]
        legacy_path = source / STATE_CONSUMER_PATHS["legacy_runtime"]
        if "ce" in roles:
            if (os.environ.get("CONTINUOUS_EVOLUTION_STORAGE_ROOT") != str(ce_path.parent)
                    or os.environ.get("CONTINUOUS_EVOLUTION_SAFE_MODE") == "1"):
                raise ProbeError("STATE_CONSUMER_CE_ROOT")
        legacy = sys.modules.get("engines.sentinel_issues_engine") if "legacy_runtime" in roles else None
        ce = sys.modules.get("engines.product_review_system_engine") if "ce" in roles else None
        if "legacy_runtime" in roles:
            if (legacy is None or Path(legacy.__file__) != source / "engines" / "sentinel_issues_engine.py"
                    or legacy.sentinel_issues_memory_path() != legacy_path):
                raise ProbeError("STATE_CONSUMER_LEGACY_IDENTITY")
        if "ce" in roles:
            if (ce is None or Path(ce.__file__) != source / "engines" / "product_review_system_engine.py"
                    or ce._ce_storage() != ce_path.parent):
                raise ProbeError("STATE_CONSUMER_CE_IDENTITY")
        bound = getattr(sqlite3.connect, "__self__", None)
        if (bound is not boundary or boundary.source != source
                or boundary.database != Path(payload["database"])
                or boundary.deadline != payload["deadline"] or boundary.mode != mode):
            raise ProbeError("STATE_CONSUMER_BOUNDARY_BINDING")
        proof["same_restored_workspace"] = True
        proof["same_sqlite_boundary"] = True
        proof["same_deadline"] = True

        before_writes, before_sql_writes = boundary.fs_writes, boundary.sql_writes
        before_denials = len(boundary.denials)
        before_decoys = boundary._state_decoy_open_attempts
        all_full_reads = True
        for role in roles:
            path = source / STATE_CONSUMER_PATHS[role]
            expected = targets[role]
            size_before, digest_before, _ = _read_state_consumer_file(
                path, deadline=payload["deadline"], max_bytes=MAX_CONSUMER_COMPARE_BYTES)
            if size_before != expected["bytes"] or digest_before != expected["sha256"]:
                raise ProbeError("STATE_CONSUMER_RESTORED_BYTES_CHANGED")
            if role == "legacy_runtime":
                value, _open_attempts, full_reads = boundary.observe_state_file(
                    role, path, legacy.load_sentinel_issues_memory)
            else:
                value, _open_attempts, full_reads = boundary.observe_state_file(
                    role, path, ce.load_product_memory)
            size_after, digest_after, raw_after = _read_state_consumer_file(
                path, deadline=payload["deadline"], max_bytes=MAX_CONSUMER_COMPARE_BYTES, include_bytes=True)
            if (size_after != expected["bytes"] or digest_after != expected["sha256"]
                    or full_reads <= 0):
                all_full_reads = False
                raise ProbeError("STATE_CONSUMER_FULL_READ_NOT_BOUND_TO_RESTORE")
            if not isinstance(value, dict):
                raise ProbeError("STATE_CONSUMER_RESULT_FORMAT")
            stored = _decode_state_consumer_json(raw_after)
            if not _canonical_state_projection_matches(
                    role, value, stored, expected["sha256"], full_read=full_reads > 0):
                raise ProbeError("STATE_CONSUMER_PROJECTION_MISMATCH")
            proof["observed_roles"].append(role)
        _deadline(payload["deadline"])
        proof["successful_full_file_reads"] = all_full_reads and proof["observed_roles"] == roles
        proof["getters_read_only"] = (
            boundary.fs_writes == before_writes and boundary.sql_writes == before_sql_writes
            and len(boundary.denials) == before_denials
        )
        proof["decoy_open_not_attempted_during_getters"] = boundary._state_decoy_open_attempts == before_decoys
        proof["canonical_value_projections_match_restored_bytes"] = True
        proof["getters_wrote_nothing"] = proof["getters_read_only"]
        proof["verified"] = (
            proof["successful_full_file_reads"] and proof["getters_read_only"]
            and proof["decoy_open_not_attempted_during_getters"] and proof["observed_roles"] == roles
        )
        proof["canonical_consumer_consumption_verified"] = proof["verified"]
        if not proof["verified"]:
            proof["code"] = "STATE_CONSUMER_OBSERVATION_INCOMPLETE"
    except ProbeError as exc:
        proof["code"] = str(exc)
    except BaseException:
        proof["code"] = "STATE_CONSUMER_OBSERVATION_FAILED"
    return proof

def _state_sqlite_consumption_binding(bundle):
    """Keep complete set identity explicit; never invent one aggregate DB hash."""
    from tools.recovery_sqlite_set_state import BoundSqliteSetStateBundle
    if type(bundle) is BoundSqliteSetStateBundle:
        from engines.recovery_sqlite_set_contract import to_record
        BoundSqliteSetStateBundle.__post_init__(bundle)
        return {"sqlite_set": to_record(bundle.sqlite), "auxiliary_sqlite_consumers_verified": False}
    from tools.recovery_state_adapter import BoundStateBundle
    if type(bundle) is not BoundStateBundle:
        raise ProbeError("TYPED_STATE_BUNDLE_REQUIRED")
    BoundStateBundle.__post_init__(bundle)
    return {"backup_name": bundle.backup_name, "sqlite_sha256": bundle.sqlite.sha256}


def run_app_probe(*, project_root: Path, restored_database: Path, workspace: Path,
                  deadline: float, mode: str = "read_only", routes=DEFAULT_ROUTES,
                  memory_bytes: int = 256 * MIB, state_bundle=None, restored_sqlite_set=None) -> dict:
    """Explicit smoke only. Does not capture, restore, delete or certify a backup."""
    report = {"schema": "NEMESIS_ISOLATED_APP_PROBE_V1", "mode": mode, "ok": False,
              "full_application_recovery_certified": False, "authenticated_client_verified": False,
              "external_services_verified": False, "external_state_restoration_verified": False,
              "bundle_all_files_restored_verified": False,
              "canonical_consumer_consumption_verified": False,
              "canonical_consumer_paths": [],
              "production_layout_attested": False,
              "backup_created": False, "restore_created": False}
    state_consumer_targets, state_consumer_missing = {}, []
    state_layout_id = None
    state_layout_model = STATE_LAYOUT_MODEL
    state_layout_provenance = STATE_LAYOUT_PROVENANCE
    expected_consumer_rows = []
    try:
        if mode not in ("read_only", "normal_boot"):
            raise ProbeError("INVALID_APP_PROBE_MODE")
        if type(memory_bytes) is not int or not 128 * MIB <= memory_bytes <= 512 * MIB:
            raise ProbeError("INVALID_APP_MEMORY_LIMIT")
        if type(deadline) not in (float, int) or not math.isfinite(deadline):
            raise ProbeError("INVALID_APP_PROBE_DEADLINE")
        _deadline(deadline)
        if not all(isinstance(p, Path) for p in (project_root, restored_database, workspace)):
            raise ProbeError("INVALID_APP_PROBE_PATH")
        if restored_database.parent != workspace or not workspace.name.startswith(".isolated_restore_327_"):
            raise ProbeError("ISOLATED_RESTORE_REQUIRED")
        # The Windows venv redirector cannot reliably start with long cwd/TEMP
        # paths. Refuse before copying/launching; never silently relax isolation.
        if os.name == "nt" and len(str(workspace / "scratch")) >= 240:
            raise ProbeError("APP_WINDOWS_WORKSPACE_PATH_UNSUPPORTED")
        db = _checked(restored_database)
        if not stat.S_ISREG(db.st_mode) or db.st_nlink != 1:
            raise ProbeError("ISOLATED_DATABASE_NOT_REGULAR")
        if any(Path(str(restored_database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
            raise ProbeError("ISOLATED_DATABASE_NOT_STANDALONE")
        if not isinstance(routes, (tuple, list)) or not routes or len(routes) > 12 or any(not _admitted_route(r) for r in routes):
            raise ProbeError("INVALID_APP_PROBE_ROUTES")
        if state_bundle is not None:
            from tools.recovery_state_adapter import BoundStateBundle
            from tools.recovery_sqlite_set_state import BoundSqliteSetStateBundle
            if type(state_bundle) is BoundSqliteSetStateBundle:
                from tools.recovery_sqlite_set_restore import RestoredSet
                if (type(restored_sqlite_set) is not RestoredSet
                        or restored_sqlite_set.bundle is not state_bundle
                        or restored_sqlite_set.workspace != workspace):
                    raise ProbeError("COMPLETE_SQLITE_SET_RESTORE_REQUIRED")
                restored_sqlite_set.verify_before_app(deadline)
                report.update(sqlite_set_members_verified_before_app=len(restored_sqlite_set.members),
                              auxiliary_sqlite_consumers_verified=False)
            elif type(state_bundle) is not BoundStateBundle or restored_sqlite_set is not None:
                raise ProbeError("TYPED_STATE_BUNDLE_REQUIRED")
            state_layout_id = getattr(state_bundle, "layout_id", None)
            if state_layout_id not in (None, COLOCATED_LAYOUT_ID):
                raise ProbeError("STATE_CONSUMER_LAYOUT_UNSUPPORTED")
            if state_layout_id == COLOCATED_LAYOUT_ID and tuple(state_bundle.scope_roles) != COLOCATED_SCOPE_ROLES:
                raise ProbeError("STATE_CONSUMER_LAYOUT_ROLES")
        if state_bundle is None and restored_sqlite_set is not None:
            raise ProbeError("COMPLETE_SQLITE_SET_RESTORE_REQUIRED")
        source = prepare_source(project_root, workspace, deadline=deadline)
        if state_bundle is not None:
            if restored_sqlite_set is not None:
                from engines import recovery_non_sqlite_state as native_state
                state_report = native_state.restore_state(
                    bundle=state_bundle.archive, expected_archive_sha256=state_bundle.archive_sha256,
                    expected_manifest_sha256=state_bundle.manifest_sha256,
                    expected_sqlite=state_bundle.sqlite, workspace=workspace,
                    expected_database_identity=native_state._identity(db), deadline=deadline,
                    limits=state_bundle.limits, expected_layout_id=state_bundle.layout_id,
                    expected_proposal_sha256=state_bundle.proposal_sha256,
                    expected_scope_roles=state_bundle.scope_roles, restored_sqlite_set=restored_sqlite_set)
            else:
                from tools.recovery_state_adapter import restore_before_app
                state_report = restore_before_app(state_bundle, source=source["path"],
                                                  restored_database=restored_database, workspace=workspace,
                                                  database_info=db, deadline=deadline)
            report["state_restore"] = state_report
            if (state_report.get("ok") is not True
                    or state_report.get("state_ready_before_app") is not True
                    or state_report.get("code") != "STATE_BYTES_VERIFIED_BEFORE_APP"):
                raise ProbeError("STATE_NOT_READY_BEFORE_APP")
            if state_layout_id == COLOCATED_LAYOUT_ID:
                restored_roles = state_report.get("scope_roles")
                if (state_report.get("layout_id") != COLOCATED_LAYOUT_ID
                        or not isinstance(restored_roles, (list, tuple))
                        or tuple(restored_roles) != COLOCATED_SCOPE_ROLES):
                    raise ProbeError("STATE_RESTORE_LAYOUT_BINDING")
                state_layout_model = COLOCATED_LAYOUT_MODEL
                state_layout_provenance = COLOCATED_LAYOUT_PROVENANCE
                expected_consumer_rows = _colocated_consumer_receipt_rows()
                state_consumer_targets, state_consumer_missing = _prepare_colocated_consumer_targets(
                    source["path"], state_bundle.scope_roles, deadline=deadline,
                    max_bytes=state_bundle.limits.bytes)
            else:
                expected_consumer_rows = [
                    {"scope_role": role, "path": STATE_CONSUMER_PATHS[role].as_posix()}
                    for role in state_bundle.scope_roles
                ]
                state_consumer_targets, state_consumer_missing = _prepare_state_consumer_targets(
                    source["path"], state_bundle.scope_roles, deadline=deadline,
                    max_bytes=state_bundle.limits.bytes)
            report["bundle_all_files_restored_verified"] = True
            report["state_scope_roles"] = list(state_bundle.scope_roles)
            report["state_proposal_sha256"] = state_bundle.proposal_sha256
            report["layout_id"] = state_layout_id
            report["layout_model"] = state_layout_model
            report["layout_provenance"] = state_layout_provenance
            report["canonical_consumer_paths"] = expected_consumer_rows
            report["canonical_consumer_scope"] = (
                "THREE_FIXED_CANONICAL_CONSUMERS_ONLY" if state_layout_id == COLOCATED_LAYOUT_ID
                else "FIXED_CANONICAL_CONSUMERS_ONLY")
            report["continuous_cross_store_consistency_certified"] = False
        if state_bundle is not None:
            expected_target_keys = (set(COLOCATED_CONSUMER_IDS)
                                    if state_layout_id == COLOCATED_LAYOUT_ID
                                    else set(state_bundle.scope_roles))
            if state_consumer_missing or set(state_consumer_targets) != expected_target_keys:
                raise ProbeError("STATE_CONSUMER_TARGETS_INCOMPLETE")
        scratch = workspace / "scratch"
        scratch.mkdir()
        memory = _render_memory_gate(memory_bytes)
        report["memory_preflight"] = memory
        if not memory["allowed"]:
            raise ProbeError("APP_MEMORY_PREFLIGHT_REFUSED")
        nonce = secrets.token_hex(16)
        if restored_sqlite_set is not None:
            restored_sqlite_set.verify_before_app(deadline)
        payload = {"nonce": nonce, "source": str(source["path"]), "database": str(restored_database), "workspace": str(workspace),
                   "scratch": str(scratch), "deadline": deadline, "mode": mode, "routes": list(routes),
                   "memory_bytes": memory_bytes}
        if state_bundle is not None:
            payload["restored_state_layout"] = state_layout_id or STATE_LAYOUT
            payload["restored_state_layout_provenance"] = state_layout_provenance
            payload["restored_state_scope_roles"] = list(state_bundle.scope_roles)
            payload["restored_state_targets"] = state_consumer_targets
            payload["restored_state_bundle_all_files_restored_verified"] = True
        env = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ}
        env.update(PATH=str(Path(sys.executable).parent), TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch),
                   PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        if state_layout_id == COLOCATED_LAYOUT_ID:
            env.update(CONTINUOUS_EVOLUTION_SAFE_MODE="1",
                       CONTINUOUS_EVOLUTION_STORAGE_ROOT=str(source["path"] / "data" / "continuous_evolution_os"))
        command = [sys.executable, "-I", "-B", str(Path(__file__)), "--child"]
        _deadline(deadline)
        with subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)) as child:
            job = None
            try:
                job = _attach_windows_limit(child, memory_bytes) if os.name == "nt" else None
                output, error = child.communicate(json.dumps(payload).encode(), timeout=max(.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                if job is not None:
                    job.close()
                    job = None
                output, error = child.communicate(timeout=2)
                report.update(child_exit=child.returncode, child_output_bytes=len(output), child_stderr_bytes=len(error),
                              child_progress=_progress_events(error, nonce))
                raise ProbeError("APP_PROBE_DEADLINE_EXPIRED")
            except BaseException:
                child.kill()
                child.communicate()
                raise
            finally:
                if job is not None:
                    job.close()
        report.update(child_exit=child.returncode, child_output_bytes=len(output), child_stderr_bytes=len(error))
        report["child_progress"] = _progress_events(error, nonce)
        if len(output) > 65536:
            raise ProbeError("APP_PROBE_PROTOCOL_FAILED")
        result = json.loads(output)
        if (not isinstance(result, dict) or result.get("schema") != "NEMESIS_APP_PROBE_CHILD_V1"
                or result.get("nonce") != nonce or result.get("mode") != mode):
            if isinstance(result, dict):
                for key in ("code", "error_type"):
                    value = result.get(key)
                    if isinstance(value, str) and re.fullmatch(r"[A-Za-z_]{1,64}", value):
                        report["child_" + key] = value
            raise ProbeError("APP_PROBE_PROTOCOL_FAILED")
        unchanged = _identity(_checked(restored_database)) == _identity(db)
        report.update(child=result, source_files=source["files"], source_bytes=source["bytes"],
                      observed_source_digest=source["observed_source_digest"], child_exit=child.returncode,
                      readonly_database_identity_unchanged=unchanged if mode == "read_only" else None)
        report["ok"] = child.returncode == 0 and result.get("ok") is True and (mode != "read_only" or unchanged)
        if state_bundle is None:
            if (result.get("canonical_consumer_consumption_verified") is not False
                    or result.get("external_state_restoration_verified") is not False
                    or result.get("bundle_all_files_restored_verified") is not False
                    or "restored_state_consumption" in result):
                raise ProbeError("APP_PROBE_PROTOCOL_FAILED")
        else:
            if state_layout_id == COLOCATED_LAYOUT_ID:
                proof = result.get("restored_state_consumption")
                expected_roles = list(COLOCATED_SCOPE_ROLES)
                canonical_paths = _colocated_consumer_receipt_rows()
                expected_ids = list(COLOCATED_CONSUMER_IDS)
                state_restore = report.get("state_restore", {})
                consumer_verified = (
                    report["ok"] and result.get("nonce") == nonce and result.get("mode") == mode
                    and result.get("layout_model") == COLOCATED_LAYOUT_MODEL
                    and result.get("production_layout_attested") is False
                    and result.get("full_application_recovery_certified") is False
                    and result.get("bundle_all_files_restored_verified") is True
                    and result.get("external_state_restoration_verified") is True
                    and result.get("canonical_consumer_consumption_verified") is True
                    and isinstance(proof, dict)
                    and proof.get("schema") == "NEMESIS_CANONICAL_CONSUMER_OBSERVATION_V4"
                    and proof.get("verified") is True
                    and proof.get("canonical_consumer_consumption_verified") is True
                    and proof.get("layout_id") == COLOCATED_LAYOUT_ID
                    and proof.get("mode") == mode
                    and proof.get("layout_model") == COLOCATED_LAYOUT_MODEL
                    and proof.get("layout_provenance") == COLOCATED_LAYOUT_PROVENANCE
                    and proof.get("production_layout_attested") is False
                    and proof.get("full_application_recovery_certified") is False
                    and proof.get("observation_scope") == "THREE_FIXED_CANONICAL_CONSUMERS_ONLY"
                    and proof.get("universal_scope_consumption_verified") is False
                    and proof.get("scope_roles") == expected_roles
                    and proof.get("canonical_consumer_paths") == canonical_paths
                    and proof.get("observed_roles") == expected_roles
                    and proof.get("observed_consumer_ids") == expected_ids
                    and all(proof.get(key) is True for key in (
                        "successful_full_file_reads", "getters_read_only", "same_restored_workspace",
                        "same_sqlite_boundary", "same_deadline", "canonical_value_projections_match_restored_bytes",
                        "decoy_open_not_attempted_during_getters", "getters_wrote_nothing",
                        "bundle_all_files_restored_verified"))
                    and report.get("bundle_all_files_restored_verified") is True
                    and state_restore.get("ok") is True
                    and state_restore.get("state_ready_before_app") is True
                    and state_restore.get("code") == "STATE_BYTES_VERIFIED_BEFORE_APP"
                    and state_restore.get("layout_id") == COLOCATED_LAYOUT_ID
                    and isinstance(state_restore.get("scope_roles"), (list, tuple))
                    and tuple(state_restore.get("scope_roles")) == COLOCATED_SCOPE_ROLES
                    and set(state_consumer_targets) == set(expected_ids)
                    and not state_consumer_missing
                )
                report["canonical_consumer_consumption_verified"] = bool(consumer_verified)
                report["external_state_restoration_verified"] = bool(
                    report["bundle_all_files_restored_verified"] and consumer_verified)
                report["state_consumption_binding"] = {
                    "verified": report["external_state_restoration_verified"],
                    "bundle_all_files_restored_verified": report["bundle_all_files_restored_verified"],
                    "canonical_consumer_consumption_verified": report["canonical_consumer_consumption_verified"],
                    "state_ready_before_app": state_restore.get("state_ready_before_app") is True,
                    "probe_nonce": nonce,
                    "operation_id": state_bundle.operation_id,
                    "proposal_sha256": state_bundle.proposal_sha256,
                    **_state_sqlite_consumption_binding(state_bundle),
                    "state_archive_sha256": state_bundle.archive_sha256,
                    "state_manifest_sha256": state_bundle.manifest_sha256,
                    "same_restored_workspace": proof.get("same_restored_workspace") is True if isinstance(proof, dict) else False,
                    "same_sqlite_boundary": proof.get("same_sqlite_boundary") is True if isinstance(proof, dict) else False,
                    "same_deadline": proof.get("same_deadline") is True if isinstance(proof, dict) else False,
                    "layout_id": COLOCATED_LAYOUT_ID,
                    "bundle_scope_roles": expected_roles,
                    "canonical_consumer_paths": canonical_paths,
                    "canonical_consumer_ids": expected_ids,
                    "observed_roles": list(proof.get("observed_roles", [])) if isinstance(proof, dict) else [],
                    "observed_consumer_ids": list(proof.get("observed_consumer_ids", [])) if isinstance(proof, dict) else [],
                    "consumer_mode": mode,
                    "layout_model": COLOCATED_LAYOUT_MODEL,
                    "production_layout_attested": False,
                    "full_application_recovery_certified": False,
                    "canonical_consumer_scope": "THREE_FIXED_CANONICAL_CONSUMERS_ONLY",
                    "universal_scope_consumption_verified": False,
                    "observation_scope": "THREE_FIXED_CANONICAL_CONSUMERS_ONLY",
                }
                report["ok"] = report["ok"] and report["external_state_restoration_verified"]
            else:
                proof = result.get("restored_state_consumption")
                expected_roles = list(state_bundle.scope_roles)
                canonical_paths = [
                    {"scope_role": role, "path": STATE_CONSUMER_PATHS[role].as_posix()}
                    for role in expected_roles
                ]
                consumer_verified = (
                    report["ok"] and result.get("nonce") == nonce and result.get("mode") == mode
                    and result.get("layout_model") == STATE_LAYOUT_MODEL
                    and result.get("production_layout_attested") is False
                    and result.get("canonical_consumer_consumption_verified") is True
                    and isinstance(proof, dict)
                    and proof.get("schema") == "NEMESIS_CANONICAL_CONSUMER_OBSERVATION_V3"
                    and proof.get("verified") is True
                    and proof.get("canonical_consumer_consumption_verified") is True
                    and proof.get("mode") == mode
                    and proof.get("layout_model") == STATE_LAYOUT_MODEL
                    and proof.get("layout_provenance") == STATE_LAYOUT_PROVENANCE
                    and proof.get("production_layout_attested") is False
                    and proof.get("observation_scope") == "CANONICAL_GETTER_BRACKETS_ONLY"
                    and proof.get("canonical_consumer_paths") == canonical_paths
                    and proof.get("observed_roles") == expected_roles
                    and all(proof.get(key) is True for key in (
                        "successful_full_file_reads", "getters_read_only", "same_restored_workspace",
                        "same_sqlite_boundary", "same_deadline", "canonical_value_projections_match_restored_bytes",
                        "decoy_open_not_attempted_during_getters", "getters_wrote_nothing"))
                    and report.get("bundle_all_files_restored_verified") is True
                    and report.get("state_restore", {}).get("ok") is True
                    and report.get("state_restore", {}).get("state_ready_before_app") is True
                    and report.get("state_restore", {}).get("code") == "STATE_BYTES_VERIFIED_BEFORE_APP"
                    and set(state_consumer_targets) == set(expected_roles)
                    and not state_consumer_missing
                )
                report["canonical_consumer_consumption_verified"] = bool(consumer_verified)
                report["external_state_restoration_verified"] = bool(
                    report["bundle_all_files_restored_verified"] and consumer_verified)
                report["state_consumption_binding"] = {
                    "verified": report["external_state_restoration_verified"],
                    "bundle_all_files_restored_verified": report["bundle_all_files_restored_verified"],
                    "canonical_consumer_consumption_verified": report["canonical_consumer_consumption_verified"],
                    "state_ready_before_app": report.get("state_restore", {}).get("state_ready_before_app") is True,
                    "probe_nonce": nonce,
                    "operation_id": state_bundle.operation_id,
                    **_state_sqlite_consumption_binding(state_bundle),
                    "state_archive_sha256": state_bundle.archive_sha256,
                    "state_manifest_sha256": state_bundle.manifest_sha256,
                    "bundle_scope_roles": expected_roles,
                    "canonical_consumer_paths": canonical_paths,
                    "observed_roles": list(proof.get("observed_roles", [])) if isinstance(proof, dict) else [],
                    "consumer_mode": mode,
                    "layout_model": STATE_LAYOUT_MODEL,
                    "production_layout_attested": False,
                    "observation_scope": "CANONICAL_GETTER_BRACKETS_ONLY",
                }
                report["ok"] = report["ok"] and report["external_state_restoration_verified"]
        report["code"] = "APP_SMOKE_VERIFIED" if report["ok"] else "APP_SMOKE_NOT_VERIFIED"
    except (OSError, ValueError, TypeError, ProbeError) as exc:
        report["ok"] = False
        report["code"] = str(exc) if isinstance(exc, ProbeError) else "APP_PROBE_FAILED"
        report["error_type"] = type(exc).__name__
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report


# Child limits and confinement are installed before importing repository App.
# No child is allowed to inherit credentials or open a second database.


def _attach_windows_limit(process, memory_bytes):
    # Microsoft: JOBOBJECT_EXTENDED_LIMIT_INFORMATION. The Windows limit bounds
    # committed private memory, not total RSS or a reservation in the service.
    # https://learn.microsoft.com/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information
    import ctypes
    from ctypes import wintypes

    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ProbeError("APP_PROCESS_LIMIT_UNAVAILABLE")
    info = Extended()
    # Windows venv redirectors retain a small launcher while the base Python
    # runs. Bound their aggregate commit to the SAME budget, not twice it.
    info.BasicLimitInformation.LimitFlags = 0x100 | 0x200 | 0x8 | 0x2000
    info.BasicLimitInformation.ActiveProcessLimit = 2
    info.ProcessMemoryLimit = memory_bytes
    info.JobMemoryLimit = memory_bytes
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(handle, wintypes.HANDLE(int(process._handle))):
        kernel.CloseHandle(handle)
        raise ProbeError("APP_PROCESS_LIMIT_UNAVAILABLE")

    class Job:
        def close(self):
            nonlocal handle
            if handle:
                kernel.CloseHandle(handle)
                handle = None
    return Job()


def _run_child(payload):
    import importlib
    import importlib.util
    import io
    import secrets

    if not isinstance(payload, dict) or not isinstance(payload.get("nonce"), str) or not re.fullmatch(r"[0-9a-f]{32}", payload["nonce"]):
        raise ProbeError("INVALID_CHILD_INPUT")
    report = {"schema": "NEMESIS_APP_PROBE_CHILD_V1", "ok": False, "nonce": payload["nonce"], "mode": payload.get("mode"),
              "authenticated_client_verified": False, "external_services_verified": False,
              "bundle_all_files_restored_verified": False,
              "external_state_restoration_verified": False,
              "canonical_consumer_consumption_verified": False,
              "layout_model": None, "production_layout_attested": False,
              "full_application_recovery_certified": False, "routes": []}
    mode = payload["mode"]
    progress_stream = sys.stderr
    def progress(stage):
        progress_stream.write(json.dumps({"nonce":payload["nonce"], "stage":stage})+"\n")
        progress_stream.flush()
    progress("CHILD_READY")
    if mode not in ("read_only", "normal_boot"):
        raise ProbeError("INVALID_APP_PROBE_MODE")
    if (type(payload.get("deadline")) not in (int, float) or not math.isfinite(payload["deadline"])
            or type(payload.get("memory_bytes")) is not int or not 128 * MIB <= payload["memory_bytes"] <= 512 * MIB
            or not isinstance(payload.get("routes"), list) or not 1 <= len(payload["routes"]) <= 12
            or any(not _admitted_route(r) for r in payload["routes"])):
        raise ProbeError("INVALID_CHILD_LIMITS")
    source, database, workspace, scratch = (Path(payload[k]) for k in ("source", "database", "workspace", "scratch"))
    if (source != workspace / "source" or database.parent != workspace or scratch != workspace / "scratch"
            or not workspace.name.startswith(".isolated_restore_327_")):
        raise ProbeError("INVALID_CHILD_PATH_BINDING")
    for path in (source, database, workspace, scratch):
        _checked(path)
    if (not stat.S_ISREG(database.lstat().st_mode) or database.lstat().st_nlink != 1
            or any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))):
        raise ProbeError("ISOLATED_DATABASE_NOT_STANDALONE")
    _deadline(payload["deadline"])
    memory = payload["memory_bytes"]
    if os.name == "posix":
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        limit = min([memory] + [value for value in (soft, hard) if value != resource.RLIM_INFINITY])
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        report["process_limit"] = {"kind": "RLIMIT_AS", "bytes": limit, "reservation_certified": False}
    elif os.name == "nt":
        report["process_limit"] = {"kind": "PARENT_WINDOWS_JOB_AGGREGATE_COMMIT", "bytes": memory,
                                   "active_process_limit_including_venv_launcher": 2, "reservation_certified": False}
    else:
        raise ProbeError("APP_PROCESS_LIMIT_UNAVAILABLE")
    layout = payload.get("restored_state_layout")
    layout_provenance = payload.get("restored_state_layout_provenance")
    if (layout not in (None, STATE_LAYOUT, COLOCATED_LAYOUT_ID)
            or (layout is None and layout_provenance is not None)
            or (layout == STATE_LAYOUT and layout_provenance != STATE_LAYOUT_PROVENANCE)
            or (layout == COLOCATED_LAYOUT_ID and layout_provenance != COLOCATED_LAYOUT_PROVENANCE)):
        raise ProbeError("INVALID_RESTORED_STATE_LAYOUT")
    roles = payload.get("restored_state_scope_roles")
    targets = payload.get("restored_state_targets")
    if layout is None:
        if (roles is not None or targets is not None
                or "restored_state_bundle_all_files_restored_verified" in payload):
            raise ProbeError("STATE_CONSUMER_PAYLOAD_WITHOUT_BUNDLE")
    elif layout == COLOCATED_LAYOUT_ID:
        report["layout_model"] = COLOCATED_LAYOUT_MODEL
        if (not isinstance(roles, list) or roles != list(COLOCATED_SCOPE_ROLES)
                or not isinstance(targets, dict) or set(targets) - set(COLOCATED_CONSUMER_IDS)
                or payload.get("restored_state_bundle_all_files_restored_verified") is not True):
            raise ProbeError("INVALID_STATE_CONSUMER_PAYLOAD")
    else:
        report["layout_model"] = STATE_LAYOUT_MODEL
        if (not isinstance(roles, list) or any(type(role) is not str for role in roles)
                or roles != sorted(set(roles)) or not 1 <= len(roles) <= 2
                or set(roles) - set(STATE_CONSUMER_PATHS) or not isinstance(targets, dict)
                or set(targets) - set(roles)
                or payload.get("restored_state_bundle_all_files_restored_verified") is not True):
            raise ProbeError("INVALID_STATE_CONSUMER_PAYLOAD")
    if layout is not None:
        report["bundle_all_files_restored_verified"] = (
            payload.get("restored_state_bundle_all_files_restored_verified") is True)
        if not report["bundle_all_files_restored_verified"]:
            raise ProbeError("STATE_BUNDLE_RESTORE_NOT_VERIFIED")
        total = 0
        for target in targets.values():
            if (not isinstance(target, dict) or set(target) != {"bytes", "sha256"}
                    or type(target["bytes"]) is not int or not 0 < target["bytes"] <= MAX_CONSUMER_COMPARE_BYTES
                    or not isinstance(target["sha256"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", target["sha256"]) is None):
                raise ProbeError("INVALID_STATE_CONSUMER_TARGET")
            total += target["bytes"]
        if total > 16 * MIB:
            raise ProbeError("STATE_CONSUMER_BYTE_BUDGET")
    if layout == COLOCATED_LAYOUT_ID:
        report["bundle_all_files_restored_verified"] = True
        ce_root = source / "data" / "continuous_evolution_os"
    elif layout == STATE_LAYOUT:
        ce_root = source / "data" / "continuous_evolution_os"
    else:
        ce_root = source / "data" / "runtime" / "continuous_evolution_os"
    clean = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "PATH") if k in os.environ}
    clean.update(DB_PATH=str(database), SECRET_KEY=secrets.token_urlsafe(32),
                 PYTHONTZPATH="",
                 CONTINUOUS_EVOLUTION_STORAGE_ROOT=str(ce_root),
                 PUBLIC_BASE_URL="https://probe.nemesis.invalid", PYTHON_DOTENV_DISABLED="1",
                 BACKUP_DIR=str(source / "data/backups"), DATA_BACKUP_DIR=str(source / "data/backups"),
                 TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch),
                 MPLCONFIGDIR=str(scratch), XDG_CACHE_HOME=str(scratch),
                 RUN_STARTUP_SCHEDULER_NOW="0", SCHEDULER_ENABLED="0", ENABLE_AUTO_SYNC="0",
                 AUTO_SYNC_ON_STARTUP="0", BACKGROUND_JOBS_ENABLED="0", AUTO_GENERATE_PICKS="0",
                 AUTO_SEND_TELEGRAM_PICKS="0", DATA_BACKUP_ENABLED="0", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    if layout == COLOCATED_LAYOUT_ID:
        clean["CONTINUOUS_EVOLUTION_SAFE_MODE"] = "1"
    os.environ.clear()
    os.environ.update(clean)
    report["timezone_data"] = _use_packaged_timezones()
    os.chdir(source)
    sys.dont_write_bytecode = True
    guard_path = Path(__file__).with_name("recovery_probe_guard.py")
    spec = importlib.util.spec_from_file_location("owned_recovery_probe_guard", guard_path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    libraries = {Path(sys.prefix), Path(sys.base_prefix)}
    libraries.update(Path(p) for p in sys.path if p and Path(p).is_absolute() and Path(p).is_dir()
                     and Path(p).name in ("site-packages", "dist-packages"))
    # The script source itself is not a general library read root.
    libraries.discard(Path(__file__).parent)
    boundary = guard.ProbeBoundary(database=database, source=source, scratch=scratch,
                                    libraries=libraries, mode=mode, deadline=payload["deadline"])
    if any(name in sys.modules for name in ("app", "engines", "database_manager", "config_db")):
        raise ProbeError("SUBJECT_MODULE_PRELOADED")
    class Sink(io.TextIOBase):
        def __init__(self):
            self.characters = 0
        def write(self, text):
            self.characters += len(text)
            return len(text)
        def flush(self):
            pass
    sink = Sink()
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = sink
    sys.path.insert(0, str(source))
    boundary.install()
    progress("GUARD_INSTALLED")
    app_module = None
    try:
        app_module = importlib.import_module("app")
        progress("APP_IMPORTED")
        if Path(app_module.__file__) != source / "app.py":
            raise ProbeError("APP_IMPORT_IDENTITY_MISMATCH")
        client = app_module.app.test_client()
        from flask import before_render_template
        observed_contexts = []
        def observe_template(_sender, template, context, **extra):
            observed_contexts.extend(_storage_states(context))
        before_render_template.connect(observe_template, app_module.app, weak=False)
        for route in payload["routes"]:
            progress("ROUTE_STARTED")
            _deadline(payload["deadline"])
            before_reads, before_denials, before_degraded = boundary.sql_reads, len(boundary.denials), boundary.degraded_calls
            before_executions, before_fetches = boundary.read_executions, boundary.read_fetches
            observed_contexts.clear()
            response = client.get(route, base_url="https://probe.nemesis.invalid", follow_redirects=False)
            progress("ROUTE_FINISHED")
            endpoint = None
            with app_module.app.test_request_context(route, base_url="https://probe.nemesis.invalid"):
                from flask import request
                endpoint = request.endpoint
            row = {"route": route.split("?", 1)[0], "http_status": response.status_code,
                   "handler": endpoint, "restored_db_read_authorizations": boundary.sql_reads - before_reads,
                   "completed_read_executions": boundary.read_executions - before_executions,
                   "completed_read_fetches": boundary.read_fetches - before_fetches,
                   "storage_states": sorted(set(observed_contexts)),
                   "boundary_denials": len(boundary.denials) - before_denials,
                   "degraded_handlers": boundary.degraded_calls - before_degraded,
                   "initialized": bool(getattr(app_module, "APP_INITIALIZED", False))}
            row["ok"] = response.status_code == 200 and row["boundary_denials"] == 0 and row["degraded_handlers"] == 0
            row["ok"] = row["ok"] and not set(observed_contexts).difference(("OK",))
            if route != "/health":
                row["ok"] = row["ok"] and row["completed_read_executions"] > 0 and row["completed_read_fetches"] > 0
            if route.startswith("/api/sports-search?"):
                row["search_ready"] = _search_ready(response.get_json(silent=True))
                row["ok"] = row["ok"] and row["search_ready"]
            report["routes"].append(row)
        report["initialized"] = bool(getattr(app_module, "APP_INITIALIZED", False))
        report["initialization_error_present"] = bool(getattr(app_module, "APP_INIT_ERROR", None))
        report["ok"] = bool(report["routes"]) and all(row["ok"] for row in report["routes"])
        if mode == "normal_boot":
            report["ok"] = report["ok"] and report["initialized"] and not report["initialization_error_present"]
        elif boundary.seed_calls or boundary.sql_writes:
            report["ok"] = False
    except BaseException as exc:
        report["error_type"] = type(exc).__name__
        report["code"] = str(exc) if isinstance(exc, (ProbeError, guard.ProbeBoundaryViolation)) else "APP_IMPORT_OR_ROUTE_FAILED"
        trace = exc.__traceback__
        while trace and trace.tb_next:
            trace = trace.tb_next
        if trace:
            path = Path(trace.tb_frame.f_code.co_filename)
            report["failure_site"] = {"source": path.relative_to(source).as_posix() if path.is_relative_to(source) else "probe_or_dependency",
                                      "line": trace.tb_lineno}
    finally:
        sys.setprofile(None)
        sys.stdout, sys.stderr = original_stdout, original_stderr
    report.update(boundary_denials=boundary.denials, restored_db_connections=boundary.connected,
                  restored_db_read_authorizations=boundary.sql_reads, sql_write_authorizations=boundary.sql_writes,
                  completed_read_executions=boundary.read_executions, completed_read_fetches=boundary.read_fetches,
                  filesystem_write_attempts_admitted=boundary.fs_writes, seed_entries_observed=boundary.seed_calls,
                  degraded_handler_entries_observed=boundary.degraded_calls,
                  discarded_log_characters=sink.characters, inherited_credentials=False,
                  canonical_consumer_consumption_verified=False)
    report["timezone_data"]["guarded_file_reads"] = boundary.timezone_reads
    report["timezone_data"]["both_zones_observed_inside_guard"] = all(boundary.timezone_reads.values())
    report["timezone_data"]["resource_origin"] = ("INSTALLED_LIBRARY_TZDATA"
        if report["timezone_data"]["both_zones_observed_inside_guard"] else "NOT_OBSERVED")
    report["timezone_data"]["library_resource_hashes_verified"] = False
    report["ok"] = report["ok"] and report["timezone_data"]["both_zones_observed_inside_guard"]
    report["ok"] = report["ok"] and not boundary.denials
    if layout == COLOCATED_LAYOUT_ID:
        consumption = _observe_colocated_state_consumers(
            payload, source, boundary, routes_verified=report["ok"])
        report["restored_state_consumption"] = consumption
        report["canonical_consumer_consumption_verified"] = (
            consumption.get("canonical_consumer_consumption_verified") is True)
        report["ok"] = report["ok"] and report["canonical_consumer_consumption_verified"]
    elif layout == STATE_LAYOUT:
        if report["ok"]:
            consumption = _observe_restored_state_consumers(payload, source, boundary)
        else:
            consumption = {
                "schema": "NEMESIS_CANONICAL_CONSUMER_OBSERVATION_V3",
                "verified": False,
                "canonical_consumer_consumption_verified": False,
                "layout_model": STATE_LAYOUT_MODEL,
                "layout_provenance": STATE_LAYOUT_PROVENANCE,
                "production_layout_attested": False,
                "observation_scope": "CANONICAL_GETTER_BRACKETS_ONLY",
                "mode": mode,
                "canonical_consumer_paths": [
                    {"scope_role": role, "path": STATE_CONSUMER_PATHS[role].as_posix()}
                    for role in roles
                ],
                "observed_roles": [],
                "code": "APP_ROUTES_NOT_VERIFIED",
                "successful_full_file_reads": False,
                "getters_read_only": False,
                "same_restored_workspace": False,
                "same_sqlite_boundary": False,
                "same_deadline": False,
                "canonical_value_projections_match_restored_bytes": False,
                "decoy_open_not_attempted_during_getters": False,
                "getters_wrote_nothing": False,
            }
        report["restored_state_consumption"] = consumption
        report["canonical_consumer_consumption_verified"] = (
            consumption.get("canonical_consumer_consumption_verified") is True)
        report["ok"] = report["ok"] and report["canonical_consumer_consumption_verified"]
    if layout is not None:
        report["external_state_restoration_verified"] = bool(
            report["bundle_all_files_restored_verified"]
            and report["canonical_consumer_consumption_verified"])
    return report


if __name__ == "__main__":
    # Parent attaches its Windows Job before sending this bounded input.
    try:
        if sys.argv[1:] != ["--child"]:
            raise ProbeError("EXPLICIT_PARENT_REQUIRED")
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise ProbeError("APP_PROBE_INPUT_LIMIT")
        result = _run_child(json.loads(raw))
    except BaseException as exc:
        result = {"schema": "NEMESIS_APP_PROBE_CHILD_V1", "ok": False,
                  "code": str(exc) if isinstance(exc, ProbeError) else "APP_PROBE_CHILD_FAILED",
                  "error_type": type(exc).__name__}
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result["ok"] else 3)
