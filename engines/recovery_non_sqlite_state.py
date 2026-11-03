"""Owned prototype only: bounded state preservation, never production authority.

Payload bytes are opaque. A successful bracket is NOT proof of continuous
cross-store quiescence. Windows capture/restore fail closed before state I/O.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import time
import uuid

MAX_ENTRIES = 400
MAX_DEPTH = 6
MAX_BYTES = 16 * 1024 * 1024
MAX_SECONDS = 5.0
MAX_MANIFEST = 1024 * 1024
MAX_ARCHIVE = MAX_BYTES + MAX_MANIFEST + MAX_ENTRIES * 1024 + 4096
CE_RUNTIME_STATE_V1 = "CE_RUNTIME_STATE_V1"
_PROFILE_CAPS = (
    (CE_RUNTIME_STATE_V1, 32768, 6, 96 * 1024 * 1024, 5.0, 32 * 1024 * 1024),
)
ROLES = frozenset(("ce", "legacy_runtime"))
DESTINATIONS = {"ce": "continuous_evolution_os", "legacy_runtime": "runtime"}
LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1 = "CE_COLOCATED_SENTINEL_AND_RUNTIME_AUTOPILOT_V1"
_LAYOUT_REQUIRED_ENTRIES = {
    LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1: (
        ("ce", "product_memory.json"),
        ("ce", "sentinel_issues_memory.json"),
        ("legacy_runtime", "sentinel_autopilot_memory.json"),
    ),
}
SECRET = re.compile(r"(^\.env(?:\.|$)|secret|credential|token|^id_|\.(?:key|pem|p12|pfx)$)", re.I)
HEX = re.compile(r"[0-9a-f]{64}\Z")
REF = re.compile(r"[A-Z0-9_-]{1,96}\Z")


_ERROR_CODES = frozenset(["PREPARED_SQLITE_CAPTURE_NOT_VERIFIED","PREPARED_SQLITE_CAPTURE_CHANGED","FOREIGN_PREPARED_SQLITE_CAPTURE","PREPARED_SQLITE_HASH_MISMATCH","INVALID_SQLITE_CAPTURE_MODE","ARCHIVE_BUDGET","ARCHIVE_HASH_MISMATCH","ARCHIVE_MEMBER_BUDGET","ARCHIVE_READ_BUDGET","BUDGET_PROFILE_MISMATCH","BUDGET_PROFILE_REQUIRED","BYTE_BUDGET","DEADLINE_EXPIRED","DUPLICATE_MANIFEST_KEY","DUPLICATE_STATE_PATH","ENTRY_BUDGET","FOREIGN_SQLITE_RECEIPT","INCOMPLETE_MANIFEST_NAMESPACE","INVALID_BUDGET_PROFILE","INVALID_DEADLINE","INVALID_EXPECTED_DIGEST","INVALID_LIMIT","INVALID_LAYOUT_BINDING","INVALID_MANIFEST","INVALID_MANIFEST_ENTRY","INVALID_MANIFEST_IDENTITY","INVALID_MANIFEST_LIMITS","INVALID_MANIFEST_ROOTS","INVALID_SCOPES","INVALID_TAR_HEADER","LAYOUT_BINDING_MISMATCH","LAYOUT_BINDING_REQUIRED","LAYOUT_REQUIRED_ENTRY_MISSING","MANIFEST_BUDGET","MANIFEST_COMPLEXITY_BUDGET","MANIFEST_HASH_MISMATCH","NONCANONICAL_PADDING","OWNED_RESTORE_WORKSPACE_REQUIRED","PAYLOAD_MANIFEST_MISMATCH","PRIVATE_ARCHIVE_REQUIRED","PRIVATE_PUBLICATION_NAMESPACE_REQUIRED","PROTECTED_SQLITE_PATHS_REQUIRED","PUBLICATION_IDENTITY_CHANGED","PUBLICATION_ROOT_OVERLAP","RESTORED_DATABASE_CHANGED","RESTORED_DATABASE_IDENTITY_MISMATCH","RESTORED_STATE_VERIFY_FAILED","SECRET_CUSTODY_REQUIRED","SOURCE_CHANGED","SOURCE_ROOT_OVERLAP","SPECIFIC_DATA_AUTHORITY_REQUIRED","SQLITE_RECEIPT_NOT_VERIFIED","SQLITE_SCOPE_COLLISION","STATE_CHANGED_ACROSS_SQLITE_INTERVAL","STATE_LINK","STRONG_FD_PRIMITIVES_UNSUPPORTED","TRAILING_ARCHIVE","TRUNCATED_ARCHIVE","UNCLASSIFIED_STATE_ERROR","UNSAFE_MEMBER_PATH","UNSAFE_PATH","UNSAFE_STATE_FILE","UNSAFE_TAR_HEADER","UNSAFE_TAR_NAME","UNSAFE_TAR_TYPE"])


class StateError(ValueError):
    """Closed codes, without file names, content or exception text."""
    def __init__(self, code):
        super().__init__(code if type(code) is str and code in _ERROR_CODES else "UNCLASSIFIED_STATE_ERROR")


@dataclass(frozen=True)
class Limits:
    entries: int = MAX_ENTRIES
    depth: int = MAX_DEPTH
    bytes: int = MAX_BYTES
    seconds: float = MAX_SECONDS

    def __post_init__(self):
        for value, maximum in ((self.entries, MAX_ENTRIES), (self.depth, MAX_DEPTH),
                               (self.bytes, MAX_BYTES)):
            if type(value) is not int or not 0 < value <= maximum:
                raise StateError("INVALID_LIMIT")
        if type(self.seconds) not in (int, float) or not math.isfinite(self.seconds) or not 0 < self.seconds <= MAX_SECONDS:
            raise StateError("INVALID_LIMIT")


@dataclass(frozen=True)
class _BudgetPolicy:
    profile_id: str | None
    entries: int
    depth: int
    bytes: int
    seconds: float
    manifest_bytes: int
    archive_bytes: int


def _policy(profile_id=None, limits=Limits()):
    if type(limits) is not Limits:
        raise StateError("INVALID_LIMIT")
    if profile_id is None:
        return _BudgetPolicy(None, limits.entries, limits.depth, limits.bytes, limits.seconds,
                             MAX_MANIFEST, MAX_ARCHIVE)
    if type(profile_id) is not str or limits != Limits():
        raise StateError("INVALID_BUDGET_PROFILE")
    for profile, entries, depth, payload_bytes, seconds, manifest_bytes in _PROFILE_CAPS:
        if profile == profile_id:
            archive_bytes = payload_bytes + manifest_bytes + entries * 1024 + 4096
            return _BudgetPolicy(profile, entries, depth, payload_bytes, seconds,
                                 manifest_bytes, archive_bytes)
    raise StateError("INVALID_BUDGET_PROFILE")


def _manifest_limits_record(policy, legacy_limits=None):
    if policy.profile_id is None:
        if type(legacy_limits) is not Limits:
            raise StateError("INVALID_LIMIT")
        return asdict(legacy_limits)
    return {
        "profile_id": policy.profile_id,
        "entries": policy.entries,
        "depth": policy.depth,
        "bytes": policy.bytes,
        "seconds": policy.seconds,
        "manifest_bytes": policy.manifest_bytes,
        "archive_bytes": policy.archive_bytes,
    }


def _validate_manifest_limits(schema, raw, policy):
    legacy_keys = {"entries", "depth", "bytes", "seconds"}
    if schema in {"OPAQUE_STATE_BUNDLE_V1", "OPAQUE_STATE_BUNDLE_V2"}:
        if policy.profile_id is not None:
            raise StateError("BUDGET_PROFILE_MISMATCH")
        if type(raw) is not dict or set(raw) != legacy_keys:
            raise StateError("INVALID_MANIFEST_LIMITS")
        try:
            return Limits(**raw)
        except (TypeError, ValueError):
            raise StateError("INVALID_MANIFEST_LIMITS") from None
    if schema == "OPAQUE_STATE_BUNDLE_V3":
        if policy.profile_id is None:
            raise StateError("BUDGET_PROFILE_REQUIRED")
        expected = _manifest_limits_record(policy)
        if (type(raw) is not dict or set(raw) != set(expected)
                or type(raw.get("profile_id")) is not str
                or any(type(raw.get(key)) is not int for key in
                       ("entries", "depth", "bytes", "manifest_bytes", "archive_bytes"))
                or type(raw.get("seconds")) is not float
                or raw != expected):
            raise StateError("BUDGET_PROFILE_MISMATCH")
        return policy
    raise StateError("INVALID_MANIFEST")


@dataclass(frozen=True)
class Scope:
    role: str
    source: Path


@dataclass(frozen=True)
class Authorization:
    # An evidence reference supplied by the operator, NOT an authorization grant.
    evidence_ref: str
    exact_roots: tuple[tuple[str, str], ...]
    unknown_regular_files_authorized: bool
    protected_sqlite_paths: tuple[str, ...]


@dataclass(frozen=True)
class SqliteReceipt:
    artifact_id: str
    sha256: str
    published_and_validated: bool


@dataclass(frozen=True)
class StateLayoutBinding:
    """Closed typed opt-in; required paths are fixed by this module."""
    layout_id: str
    operation_id: str
    proposal_sha256: str



_CAPTURE_IDENTITY_FIELDS = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                            "st_size", "st_mtime_ns", "st_ctime_ns")


@dataclass(frozen=True)
class PreparedSqliteCapture:
    """Pinned producer-owned capture; never a provisional SqliteReceipt."""
    operation_id: str
    proposal_sha256: str
    producer_id: str
    capture_id: str
    snapshot_fd: int
    snapshot_identity: tuple[int, ...]


@dataclass(frozen=True)
class ValidatedSqliteCapture:
    """Final producer result retaining the exact prepared capability object."""
    prepared: PreparedSqliteCapture
    receipt: SqliteReceipt
    published_identity: tuple[int, ...]
    publication: Path
    publication_fd: int
    backup_file: str


@dataclass(frozen=True)
class PreparedSqliteCallbacks:
    """Explicit trusted-code opt-in; neither callback comes from manifest/data."""
    prepare: object
    validate: object


def _capture_identity(info):
    return tuple(int(getattr(info, key)) for key in _CAPTURE_IDENTITY_FIELDS)


def _prepared_capture(value, binding):
    if (type(value) is not PreparedSqliteCapture or binding is None
            or value.operation_id != binding["operation_id"]
            or value.proposal_sha256 != binding["proposal_sha256"]
            or type(value.producer_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", value.producer_id)
            or type(value.capture_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", value.capture_id)
            or type(value.snapshot_fd) is not int or value.snapshot_fd < 0
            or type(value.snapshot_identity) is not tuple or len(value.snapshot_identity) != 9
            or any(type(v) is not int or v < 0 for v in value.snapshot_identity)):
        raise StateError("PREPARED_SQLITE_CAPTURE_NOT_VERIFIED")
    info = os.fstat(value.snapshot_fd)
    _regular(info)
    if (info.st_mode & 0o077 or info.st_uid != os.geteuid()
            or info.st_size <= 0 or _capture_identity(info) != value.snapshot_identity):
        raise StateError("PREPARED_SQLITE_CAPTURE_CHANGED")
    return value


def _validated_capture(value, prepared, binding, deadline):
    if (type(value) is not ValidatedSqliteCapture or value.prepared is not prepared
            or type(value.published_identity) is not tuple
            or len(value.published_identity) != 9
            or any(type(v) is not int or v < 0 for v in value.published_identity)
            or type(value.publication_fd) is not int or value.publication_fd < 0
            or type(value.backup_file) is not str
            or not re.fullmatch(r"database_[A-Za-z0-9_-]{1,180}\.db", value.backup_file)):
        raise StateError("FOREIGN_PREPARED_SQLITE_CAPTURE")
    receipt = _sqlite(value.receipt)
    if receipt["artifact_id"] != binding["operation_id"]:
        raise StateError("FOREIGN_SQLITE_RECEIPT")
    current = os.fstat(prepared.snapshot_fd)
    _regular(current)
    # No-replace link/unlink publication changes only ctime on the retained
    # single-link file. All content/owner/inode fields must remain identical.
    if (tuple(value.published_identity[:-1]) != prepared.snapshot_identity[:-1]
            or _capture_identity(current) != value.published_identity
            or current.st_ctime_ns < prepared.snapshot_identity[-1]):
        raise StateError("PREPARED_SQLITE_CAPTURE_CHANGED")
    def published_name_is_same_capture():
        _path(value.publication)
        namespace = os.fstat(value.publication_fd)
        if (not stat.S_ISDIR(namespace.st_mode) or namespace.st_mode & 0o077
                or namespace.st_uid != os.geteuid()):
            raise StateError("PREPARED_SQLITE_CAPTURE_CHANGED")
        check_fd = _directory(value.publication)
        try:
            actual = os.fstat(check_fd)
            if ((namespace.st_dev, namespace.st_ino, namespace.st_mode, namespace.st_uid, namespace.st_gid)
                    != (actual.st_dev, actual.st_ino, actual.st_mode, actual.st_uid, actual.st_gid)):
                raise StateError("PREPARED_SQLITE_CAPTURE_CHANGED")
        finally:
            os.close(check_fd)
        _same(current, os.stat(value.backup_file, dir_fd=value.publication_fd, follow_symlinks=False))
    published_name_is_same_capture()
    digest = _hash_fd(prepared.snapshot_fd, deadline, current.st_size)
    _same(current, os.fstat(prepared.snapshot_fd))
    published_name_is_same_capture()
    if digest != receipt["sha256"]:
        raise StateError("PREPARED_SQLITE_HASH_MISMATCH")
    _check_time(deadline)
    return receipt


def _check_time(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise StateError("INVALID_DEADLINE")
    if time.monotonic() >= deadline:
        raise StateError("DEADLINE_EXPIRED")


def _native():
    required = (os.open, os.stat, os.mkdir, os.unlink, os.link)
    if (os.name != "posix" or not getattr(os, "O_NOFOLLOW", 0)
            or not getattr(os, "O_DIRECTORY", 0)
            or any(f not in os.supports_dir_fd for f in required)
            or os.scandir not in os.supports_fd):
        raise StateError("STRONG_FD_PRIMITIVES_UNSUPPORTED")


def _path(path):
    if not isinstance(path, Path) or not path.is_absolute() or ".." in path.parts or str(path).startswith(("//", "\\\\")):
        raise StateError("UNSAFE_PATH")
    return path


def _identity(info):
    # atime is deliberately excluded: this reader can update it.
    return {key: int(getattr(info, key)) for key in (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
        "st_size", "st_mtime_ns", "st_ctime_ns")}


def _same(left, right):
    if _identity(left) != _identity(right):
        raise StateError("SOURCE_CHANGED")


def _directory(path):
    _path(path)
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _regular(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise StateError("UNSAFE_STATE_FILE")


def _relative(value, depth=MAX_DEPTH):
    if not isinstance(value, str):
        raise StateError("UNSAFE_MEMBER_PATH")
    parts = value.split("/")
    if (not parts or len(parts) > depth or any(p in ("", ".", "..") for p in parts)
            or "\\" in value or "\0" in value or PurePosixPath(value).is_absolute()):
        raise StateError("UNSAFE_MEMBER_PATH")
    if any(SECRET.search(p) for p in parts):
        raise StateError("SECRET_CUSTODY_REQUIRED")
    return parts


def _scopes(scopes, authorization):
    if not isinstance(scopes, (tuple, list)) or not 1 <= len(scopes) <= 2:
        raise StateError("INVALID_SCOPES")
    result = sorted(scopes, key=lambda s: s.role)
    if (any(type(s) is not Scope or s.role not in ROLES for s in result)
            or len({s.role for s in result}) != len(result)):
        raise StateError("INVALID_SCOPES")
    for s in result:
        _path(s.source)
        if any(SECRET.search(part) for part in s.source.parts):
            raise StateError("SECRET_CUSTODY_REQUIRED")
    for i, a in enumerate(result):
        for b in result[i+1:]:
            if a.source == b.source or a.source.is_relative_to(b.source) or b.source.is_relative_to(a.source):
                raise StateError("SOURCE_ROOT_OVERLAP")
    expected = tuple((s.role, str(s.source)) for s in result)
    if (type(authorization) is not Authorization or not isinstance(authorization.evidence_ref, str)
            or not REF.fullmatch(authorization.evidence_ref)
            or authorization.unknown_regular_files_authorized is not True
            or authorization.exact_roots != expected):
        raise StateError("SPECIFIC_DATA_AUTHORITY_REQUIRED")
    if (not isinstance(authorization.protected_sqlite_paths, tuple)
            or not authorization.protected_sqlite_paths):
        raise StateError("PROTECTED_SQLITE_PATHS_REQUIRED")
    for value in authorization.protected_sqlite_paths:
        if not isinstance(value, str):
            raise StateError("PROTECTED_SQLITE_PATHS_REQUIRED")
        _path(Path(value))
    return result


def _sqlite(receipt):
    if (type(receipt) is not SqliteReceipt or receipt.published_and_validated is not True
            or not isinstance(receipt.artifact_id, str) or not REF.fullmatch(receipt.artifact_id)
            or not isinstance(receipt.sha256, str) or not HEX.fullmatch(receipt.sha256)):
        raise StateError("SQLITE_RECEIPT_NOT_VERIFIED")
    return asdict(receipt)


def _validate_profile_manifest_value(value, policy, deadline):
    max_scalars = policy.entries * _PROFILE_MANIFEST_SCALARS_PER_ENTRY + _PROFILE_MANIFEST_FIXED_SCALARS
    max_containers = policy.entries * _PROFILE_MANIFEST_CONTAINERS_PER_ENTRY + _PROFILE_MANIFEST_FIXED_CONTAINERS
    counts = {"scalars": 0, "containers": 0, "visited": 0}

    def string_size(text):
        size = 2
        for index, character in enumerate(text):
            ordinal = ord(character)
            if ordinal in (8, 9, 10, 12, 13, 34, 92):
                size += 2
            elif ordinal < 32 or ordinal >= 127:
                size += 6 if ordinal <= 0xFFFF else 12
            else:
                size += 1
            if size > _PROFILE_MANIFEST_MAX_STRING_BYTES:
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")
            if index and index % 256 == 0:
                _check_time(deadline)
        _check_time(deadline)

    def scalar():
        counts["scalars"] += 1
        counts["visited"] += 1
        if counts["scalars"] > max_scalars:
            raise StateError("MANIFEST_COMPLEXITY_BUDGET")
        if counts["visited"] % 256 == 0:
            _check_time(deadline)

    def visit(item, depth):
        if type(item) is dict:
            depth += 1
            counts["containers"] += 1
            if (depth > _PROFILE_MANIFEST_MAX_DEPTH
                    or counts["containers"] > max_containers
                    or len(item) > _PROFILE_MANIFEST_MAX_OBJECT_KEYS):
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")
            for key, child in item.items():
                if type(key) is not str:
                    raise StateError("INVALID_MANIFEST")
                scalar()
                string_size(key)
                visit(child, depth)
        elif type(item) is list:
            depth += 1
            counts["containers"] += 1
            if (depth > _PROFILE_MANIFEST_MAX_DEPTH
                    or counts["containers"] > max_containers
                    or len(item) > policy.entries):
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")
            for child in item:
                visit(child, depth)
        elif type(item) is str:
            scalar()
            string_size(item)
        elif item is None or type(item) is bool:
            scalar()
        elif type(item) is int:
            if item.bit_length() > 212 or len(str(item)) > _PROFILE_MANIFEST_MAX_ATOM_BYTES:
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")
            scalar()
        elif type(item) is float:
            if not math.isfinite(item) or len(repr(item)) > _PROFILE_MANIFEST_MAX_ATOM_BYTES:
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")
            scalar()
        else:
            raise StateError("INVALID_MANIFEST")

    visit(value, 0)
    _check_time(deadline)


def _iter_profile_manifest_bytes(value, deadline):
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    for text in encoder.iterencode(value):
        _check_time(deadline)
        yield text.encode("ascii")
    _check_time(deadline)


def _measure_profile_manifest(value, policy, deadline):
    _validate_profile_manifest_value(value, policy, deadline)
    digest, length = hashlib.sha256(), 0
    for block in _iter_profile_manifest_bytes(value, deadline):
        length += len(block)
        if length > policy.manifest_bytes:
            raise StateError("MANIFEST_BUDGET")
        digest.update(block)
    _check_time(deadline)
    return length, digest.hexdigest()


def _write_profile_manifest(value, policy, deadline, stream, expected_length, expected_digest):
    _validate_profile_manifest_value(value, policy, deadline)
    digest, length = hashlib.sha256(), 0
    for block in _iter_profile_manifest_bytes(value, deadline):
        length += len(block)
        if length > policy.manifest_bytes:
            raise StateError("MANIFEST_BUDGET")
        digest.update(block)
        stream.write(block)
    _check_time(deadline)
    if length != expected_length or digest.hexdigest() != expected_digest:
        raise StateError("SOURCE_CHANGED")


def _snapshot_after_profile_manifest_preflight(
        manifest_template, policy, deadline, callback, before_callback):
    size, _ = _measure_profile_manifest(manifest_template, policy, deadline)
    _check_time(deadline)
    before_callback()
    return callback(deadline), size


class _Writer:
    def __init__(self, stream, deadline):
        self.stream, self.deadline = stream, deadline
        self.index = 0

    def _header(self, name, length):
        info = tarfile.TarInfo(name)
        info.type, info.mode, info.size, info.mtime = tarfile.REGTYPE, 0o600, length, 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        self.stream.write(info.tobuf(format=tarfile.USTAR_FORMAT))

    def file(self, fd, length, scan_deadline):
        name = "payload/%06d" % self.index
        self.index += 1
        self._header(name, length)
        digest, consumed = hashlib.sha256(), 0
        while consumed < length:
            _check_time(min(self.deadline, scan_deadline))
            block = os.read(fd, min(65536, length - consumed))
            if not block:
                raise StateError("SOURCE_CHANGED")
            digest.update(block)
            consumed += len(block)
            self.stream.write(block)
        if os.read(fd, 1):
            raise StateError("SOURCE_CHANGED")
        self.stream.write(b"\0" * (-length % 512))
        return name, digest.hexdigest()

    def manifest(self, value, policy=None, expected_length=None):
        if policy is None:
            policy = _policy()
        if policy.profile_id is None:
            # Keep the legacy V1/V2 byte path exactly as it was.
            raw = _canonical(value)
            if len(raw) > policy.manifest_bytes:
                raise StateError("MANIFEST_BUDGET")
            self._header("manifest.json", len(raw))
            self.stream.write(raw)
            self.stream.write(b"\0" * (-len(raw) % 512))
            self.stream.write(b"\0" * 1024)
            return hashlib.sha256(raw).hexdigest()
        length, digest = _measure_profile_manifest(value, policy, self.deadline)
        if expected_length is not None and length != expected_length:
            raise StateError("SOURCE_CHANGED")
        _check_time(self.deadline)
        self._header("manifest.json", length)
        _write_profile_manifest(
            value, policy, self.deadline, self.stream, length, digest
        )
        self.stream.write(b"\0" * (-length % 512))
        self.stream.write(b"\0" * 1024)
        return digest


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _layout_binding_record(binding, scopes):
    if binding is None:
        return None
    if (type(binding) is not StateLayoutBinding
            or type(binding.layout_id) is not str
            or binding.layout_id not in _LAYOUT_REQUIRED_ENTRIES
            or type(binding.operation_id) is not str or not REF.fullmatch(binding.operation_id)
            or type(binding.proposal_sha256) is not str or not HEX.fullmatch(binding.proposal_sha256)):
        raise StateError("INVALID_LAYOUT_BINDING")
    roles = tuple(sorted(scope.role for scope in scopes))
    required = _LAYOUT_REQUIRED_ENTRIES[binding.layout_id]
    required_roles = tuple(sorted({role for role, _ in required}))
    if roles != required_roles:
        raise StateError("INVALID_LAYOUT_BINDING")
    return {
        "layout_id": binding.layout_id,
        "operation_id": binding.operation_id,
        "proposal_sha256": binding.proposal_sha256,
        "scope_roles": list(roles),
        "required_entries": [{"scope": role, "relative": relative} for role, relative in required],
    }


def _validate_required_layout_entries(binding, entries):
    if binding is None:
        return
    by_path = {(entry["scope"], entry["relative"]): entry for entry in entries}
    required = _LAYOUT_REQUIRED_ENTRIES[binding["layout_id"]]
    if any(by_path.get(key, {}).get("kind") != "file" for key in required):
        raise StateError("LAYOUT_REQUIRED_ENTRY_MISSING")


def _validate_expected_layout_binding(manifest, *, expected_layout_id=None,
                                      expected_operation_id=None, expected_proposal_sha256=None,
                                      expected_scope_roles=None):
    binding = manifest.get("layout_binding")
    expectations = (expected_layout_id, expected_proposal_sha256, expected_scope_roles)
    if binding is None:
        if any(value is not None for value in expectations):
            raise StateError("LAYOUT_BINDING_MISMATCH")
        return None
    if (expected_layout_id is None or expected_proposal_sha256 is None
            or expected_scope_roles is None):
        raise StateError("LAYOUT_BINDING_REQUIRED")
    if (binding.get("layout_id") != expected_layout_id
            or binding.get("operation_id") != expected_operation_id
            or binding.get("proposal_sha256") != expected_proposal_sha256
            or binding.get("scope_roles") != list(expected_scope_roles)):
        raise StateError("LAYOUT_BINDING_MISMATCH")
    return binding


def _scan(scopes, limits, deadline, writer=None, protected=()):
    scan_deadline = min(deadline, time.monotonic() + limits.seconds)
    entries, roots, count, size = [], [], 0, 0
    blocked = {str(Path(value)) + suffix for value in protected
               for suffix in ("", "-wal", "-shm", "-journal")}
    sources = {s.role: s.source for s in scopes}

    def walk(fd, role, parent):
        nonlocal count, size
        before = os.fstat(fd)
        names = []
        with os.scandir(fd) as iterator:
            for item in iterator:
                _check_time(scan_deadline)
                count += 1
                if count > limits.entries:
                    raise StateError("ENTRY_BUDGET")
                names.append(item.name)
        for name in sorted(names, key=os.fsencode):
            _check_time(scan_deadline)
            relative = "/".join((*parent, name))
            parts = _relative(relative, limits.depth)
            if str(sources[role].joinpath(*parts)) in blocked:
                raise StateError("SQLITE_SCOPE_COLLISION")
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                raise StateError("STATE_LINK")
            record = {"scope": role, "relative": relative, "identity": _identity(info)}
            if stat.S_ISDIR(info.st_mode):
                record["kind"] = "directory"
                entries.append(record)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=fd)
                try:
                    _same(info, os.fstat(child))
                    walk(child, role, tuple(parts))
                finally:
                    os.close(child)
            else:
                _regular(info)
                size += info.st_size
                if size > limits.bytes:
                    raise StateError("BYTE_BUDGET")
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    opened = os.fstat(child)
                    _regular(opened)
                    _same(info, opened)
                    if writer is not None:
                        member, digest = writer.file(child, info.st_size, scan_deadline)
                        record["member"] = member
                    else:
                        digest = hashlib.sha256()
                        consumed = 0
                        while True:
                            _check_time(scan_deadline)
                            block = os.read(child, 65536)
                            if not block:
                                break
                            consumed += len(block)
                            if consumed > info.st_size:
                                raise StateError("SOURCE_CHANGED")
                            digest.update(block)
                        if consumed != info.st_size:
                            raise StateError("SOURCE_CHANGED")
                        digest = digest.hexdigest()
                    _same(info, os.fstat(child))
                finally:
                    os.close(child)
                record.update(kind="file", bytes=info.st_size, sha256=digest,
                              classification="OPAQUE_PRESERVED")
                entries.append(record)
            _same(info, os.stat(name, dir_fd=fd, follow_symlinks=False))
        _same(before, os.fstat(fd))

    for scope in scopes:
        _check_time(scan_deadline)
        fd = _directory(scope.source)
        try:
            roots.append({"scope": scope.role, "identity": _identity(os.fstat(fd))})
            walk(fd, scope.role, ())
        finally:
            os.close(fd)
    _check_time(scan_deadline)
    return {"roots": roots, "entries": entries, "entries_count": count, "bytes": size}


def _comparable(scan):
    return {"roots": scan["roots"], "entries": [
        {k: v for k, v in e.items() if k != "member"} for e in scan["entries"]]}


def _hash_fd(fd, deadline, maximum):
    os.lseek(fd, 0, os.SEEK_SET)
    digest, total = hashlib.sha256(), 0
    while True:
        _check_time(deadline)
        block = os.read(fd, 65536)
        if not block:
            break
        total += len(block)
        if total > maximum:
            raise StateError("ARCHIVE_BUDGET")
        digest.update(block)
    return digest.hexdigest()


def capture_state(*, scopes, authorization, publication: Path, deadline: float,
                  sqlite_snapshot_callback=None, limits: Limits = Limits(), layout_binding=None,
                  profile_id=None, sqlite_prepared_callbacks=None):
    result = {"schema": "OWNED_STATE_CAPTURE_PROTOTYPE_V1", "ok": False,
              "state_published": False, "sqlite_callback_invoked": False,
              "sqlite_receipt": None, "recapture_attempted": False,
              "full_application_recovery_certified": False,
              "continuous_cross_store_consistency_certified": False}
    pfd = None
    temporary = None
    try:
        _check_time(deadline)
        _native()
        if type(limits) is not Limits:
            raise StateError("INVALID_LIMIT")
        policy = _policy(profile_id, limits)
        split_capture = sqlite_prepared_callbacks is not None
        if split_capture and (type(sqlite_prepared_callbacks) is not PreparedSqliteCallbacks
                or sqlite_snapshot_callback is not None or policy.profile_id is None
                or not callable(sqlite_prepared_callbacks.prepare)
                or not callable(sqlite_prepared_callbacks.validate)):
            raise StateError("INVALID_SQLITE_CAPTURE_MODE")
        if not split_capture and not callable(sqlite_snapshot_callback):
            raise StateError("INVALID_SQLITE_CAPTURE_MODE")
        result["sqlite_capture_mode"] = "PREPARE_THEN_VALIDATE_V1" if split_capture else "LEGACY_CALLBACK"
        scopes = _scopes(scopes, authorization)
        layout_record = _layout_binding_record(layout_binding, scopes)
        if policy.profile_id is not None and (
                layout_record is None
                or layout_record["layout_id"] != LAYOUT_CE_COLOCATED_SENTINEL_AUTOPILOT_V1):
            raise StateError("LAYOUT_BINDING_REQUIRED")
        _path(publication)
        if any(publication == s.source or publication.is_relative_to(s.source)
               or s.source.is_relative_to(publication) for s in scopes):
            raise StateError("PUBLICATION_ROOT_OVERLAP")
        pfd = _directory(publication)
        pub_info = os.fstat(pfd)
        if pub_info.st_mode & 0o077 or pub_info.st_uid != os.geteuid():
            raise StateError("PRIVATE_PUBLICATION_NAMESPACE_REQUIRED")
        temporary = ".state-" + uuid.uuid4().hex + ".partial"
        final = "state-" + uuid.uuid4().hex + ".tar"
        fd = os.open(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=pfd)
        with os.fdopen(fd, "w+b") as stream:
            writer = _Writer(stream, deadline)
            before = _scan(scopes, policy, deadline, writer, authorization.protected_sqlite_paths)
            _validate_required_layout_entries(layout_record, before["entries"])
            _check_time(deadline)
            manifest_schema = ("OPAQUE_STATE_BUNDLE_V3" if policy.profile_id is not None else
                               "OPAQUE_STATE_BUNDLE_V2" if layout_record is not None else
                               "OPAQUE_STATE_BUNDLE_V1")
            profile_manifest_size = None
            if policy.profile_id is not None:
                sizing_manifest = {
                    "schema": manifest_schema,
                    "authorization_ref": authorization.evidence_ref,
                    # Shape sentinel only; null has the same JSON width as the final boolean.
                    "sqlite": {"artifact_id": layout_record["operation_id"],
                               "sha256": "0" * 64, "published_and_validated": None},
                    "limits": _manifest_limits_record(policy, limits),
                    "roots": before["roots"], "entries": before["entries"],
                    "bracket_equal": True,
                    "continuous_cross_store_consistency_certified": False,
                    "layout_binding": layout_record,
                }

                def mark_sqlite_callback_invoked():
                    result["sqlite_callback_invoked"] = True

                receipt, profile_manifest_size = _snapshot_after_profile_manifest_preflight(
                    sizing_manifest, policy, deadline,
                    (sqlite_prepared_callbacks.prepare if split_capture else sqlite_snapshot_callback),
                    mark_sqlite_callback_invoked,
                )
            else:
                result["sqlite_callback_invoked"] = True
                receipt = sqlite_snapshot_callback(deadline)
            if not split_capture:
                result["sqlite_receipt"] = _sqlite(receipt)
                if (layout_record is not None
                        and result["sqlite_receipt"]["artifact_id"] != layout_record["operation_id"]):
                    raise StateError("LAYOUT_BINDING_MISMATCH")
            # Close the complete opaque bracket immediately after preparation.
            # Validation, hashes and publication do not run inside this interval.
            _check_time(deadline)
            after = _scan(scopes, policy, deadline, protected=authorization.protected_sqlite_paths)
            if _comparable(before) != _comparable(after):
                raise StateError("STATE_CHANGED_ACROSS_SQLITE_INTERVAL")
            result["opaque_bracket_closed"] = True
            if split_capture:
                prepared_capture = _prepared_capture(receipt, layout_record)
                _check_time(deadline)
                result["sqlite_validator_invoked"] = True
                validated = sqlite_prepared_callbacks.validate(prepared_capture, deadline)
                result["sqlite_receipt"] = _validated_capture(
                    validated, prepared_capture, layout_record, deadline)
                result["same_prepared_sqlite_capture_verified"] = True
                result["sqlite_backup_file"] = validated.backup_file
            manifest = {"schema": manifest_schema,
                        "authorization_ref": authorization.evidence_ref,
                        "sqlite": result["sqlite_receipt"],
                        "limits": _manifest_limits_record(policy, limits),
                        "roots": before["roots"], "entries": before["entries"],
                        "bracket_equal": True,
                        "continuous_cross_store_consistency_certified": False}
            if layout_record is not None:
                manifest["layout_binding"] = layout_record
            mh = writer.manifest(
                manifest, policy, expected_length=profile_manifest_size
            )
            stream.flush()
            os.fsync(stream.fileno())
            _check_time(deadline)
            archive_sha = _hash_fd(stream.fileno(), deadline, policy.archive_bytes)
            prepared = os.fstat(stream.fileno())
        # link() publishes one complete private TAR without replacing any old file.
        _check_time(deadline)
        os.link(temporary, final, src_dir_fd=pfd, dst_dir_fd=pfd, follow_symlinks=False)
        result.update(state_published=True, bundle_file=final, archive_sha256=archive_sha,
                      manifest_sha256=mh)
        final_fd = os.open(final, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=pfd)
        try:
            published = os.fstat(final_fd)
            stable_fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_size", "st_mtime_ns")
            if (not stat.S_ISREG(published.st_mode)
                    or any(getattr(prepared, k) != getattr(published, k) for k in stable_fields)):
                raise StateError("PUBLICATION_IDENTITY_CHANGED")
        finally:
            os.close(final_fd)
        os.unlink(temporary, dir_fd=pfd)
        temporary = None
        os.fsync(pfd)
        _check_time(deadline)
        result.update(ok=True, code="BRACKETED_STATE_PRESERVED_NOT_FULL_RECOVERY",
                      entries=before["entries_count"], state_bytes=before["bytes"])
        if layout_record is not None:
            result.update(layout_id=layout_record["layout_id"],
                          scope_roles=layout_record["scope_roles"])
        if policy.profile_id is not None:
            result["profile_id"] = policy.profile_id
    except BaseException as exc:
        result.update(code=str(exc) if isinstance(exc, StateError) else "STATE_CAPTURE_FAILED",
                      error_type=type(exc).__name__)
        if result["sqlite_callback_invoked"] and result["sqlite_receipt"] is None:
            result["sqlite_disposition"] = "UNKNOWN_PRESERVE_AND_DO_NOT_RETRY"
    finally:
        if temporary is not None and pfd is not None:
            try:
                os.unlink(temporary, dir_fd=pfd)
            except OSError:
                result["owned_partial_cleanup_failed"] = True
        if pfd is not None:
            os.close(pfd)
    return result


def _no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise StateError("DUPLICATE_MANIFEST_KEY")
        value[key] = item
    return value


def _valid_identity(value, kind):
    keys = {"st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
            "st_size", "st_mtime_ns", "st_ctime_ns"}
    if (type(value) is not dict or set(value) != keys
            or any(type(v) is not int or v < 0 for v in value.values())
            or value["st_nlink"] < 1
            or (kind == "file" and (not stat.S_ISREG(value["st_mode"]) or value["st_nlink"] != 1))
            or (kind == "directory" and not stat.S_ISDIR(value["st_mode"]))):
        raise StateError("INVALID_MANIFEST_IDENTITY")


_PROFILE_MANIFEST_MAX_DEPTH = 6
_PROFILE_MANIFEST_MAX_STRING_BYTES = 16 * 1024
_PROFILE_MANIFEST_MAX_ATOM_BYTES = 64
_PROFILE_MANIFEST_MAX_OBJECT_KEYS = 32
_PROFILE_MANIFEST_SCALARS_PER_ENTRY = 40
_PROFILE_MANIFEST_FIXED_SCALARS = 1024
_PROFILE_MANIFEST_CONTAINERS_PER_ENTRY = 3
_PROFILE_MANIFEST_FIXED_CONTAINERS = 64


def _preflight_profile_manifest(raw, policy, deadline=None):
    """Bound V3 JSON allocation before the standard decoder allocates."""
    if policy.profile_id is None:
        return
    _check_time(deadline)
    if type(raw) is not bytes or len(raw) > policy.manifest_bytes:
        raise StateError("MANIFEST_BUDGET")
    max_scalars = policy.entries * _PROFILE_MANIFEST_SCALARS_PER_ENTRY + _PROFILE_MANIFEST_FIXED_SCALARS
    max_containers = policy.entries * _PROFILE_MANIFEST_CONTAINERS_PER_ENTRY + _PROFILE_MANIFEST_FIXED_CONTAINERS
    stack = []
    in_string = escaped = atom = False
    string_size = atom_size = depth = containers = scalars = 0

    def array_item():
        if stack and stack[-1]["kind"] == "array":
            stack[-1]["items"] += 1
            if stack[-1]["items"] > policy.entries:
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")

    def object_value_started():
        if stack and stack[-1]["kind"] == "object" and stack[-1]["state"] == "value":
            stack[-1]["state"] = "done"

    for block_start in range(0, len(raw), 65536):
        _check_time(deadline)
        block = raw[block_start:block_start + 65536]
        for byte in block:
            if in_string:
                string_size += 1
                if string_size > _PROFILE_MANIFEST_MAX_STRING_BYTES:
                    raise StateError("MANIFEST_COMPLEXITY_BUDGET")
                if escaped:
                    escaped = False
                elif byte == 92:
                    escaped = True
                elif byte == 34:
                    in_string = False
                    atom = False
                elif byte < 32:
                    raise StateError("INVALID_MANIFEST")
                continue
            if byte == 34:
                scalars += 1
                if stack and stack[-1]["kind"] == "array":
                    array_item()
                elif stack and stack[-1]["kind"] == "object":
                    current = stack[-1]
                    if current["state"] == "key":
                        current["keys"] += 1
                        if current["keys"] > _PROFILE_MANIFEST_MAX_OBJECT_KEYS:
                            raise StateError("MANIFEST_COMPLEXITY_BUDGET")
                        current["state"] = "colon"
                    elif current["state"] == "value":
                        current["state"] = "done"
                in_string = True
                escaped = False
                string_size = 0
                atom = False
            elif byte in (9, 10, 13, 32):
                atom = False
            elif byte in (123, 91):
                array_item()
                object_value_started()
                containers += 1
                depth += 1
                atom = False
                if containers > max_containers or depth > _PROFILE_MANIFEST_MAX_DEPTH:
                    raise StateError("MANIFEST_COMPLEXITY_BUDGET")
                stack.append({"kind": "object", "keys": 0, "state": "key"}
                             if byte == 123 else {"kind": "array", "items": 0})
            elif byte in (125, 93):
                expected_kind = "object" if byte == 125 else "array"
                if depth < 1 or not stack or stack[-1]["kind"] != expected_kind:
                    raise StateError("INVALID_MANIFEST")
                stack.pop()
                depth -= 1
                atom = False
            elif byte == 44:
                if stack and stack[-1]["kind"] == "object":
                    stack[-1]["state"] = "key"
                atom = False
            elif byte == 58:
                if stack and stack[-1]["kind"] == "object" and stack[-1]["state"] == "colon":
                    stack[-1]["state"] = "value"
                atom = False
            else:
                if not atom:
                    scalars += 1
                    array_item()
                    object_value_started()
                    atom = True
                    atom_size = 0
                atom_size += 1
                if atom_size > _PROFILE_MANIFEST_MAX_ATOM_BYTES:
                    raise StateError("MANIFEST_COMPLEXITY_BUDGET")
            if scalars > max_scalars:
                raise StateError("MANIFEST_COMPLEXITY_BUDGET")
    if in_string or escaped or depth != 0 or stack:
        raise StateError("INVALID_MANIFEST")
    _check_time(deadline)


def _coerce_manifest_policy(value):
    if type(value) is Limits:
        return _policy(None, value)
    if type(value) is not _BudgetPolicy:
        raise StateError("INVALID_LIMIT")
    if value.profile_id is None:
        try:
            limits = Limits(value.entries, value.depth, value.bytes, value.seconds)
        except (TypeError, ValueError):
            raise StateError("INVALID_LIMIT") from None
        expected = _policy(None, limits)
        if (value != expected
                or type(value.entries) is not type(expected.entries)
                or type(value.depth) is not type(expected.depth)
                or type(value.bytes) is not type(expected.bytes)
                or type(value.seconds) is not type(expected.seconds)
                or type(value.manifest_bytes) is not type(expected.manifest_bytes)
                or type(value.archive_bytes) is not type(expected.archive_bytes)):
            raise StateError("INVALID_LIMIT")
        return value
    expected = _policy(value.profile_id, Limits())
    if (value != expected
            or type(value.entries) is not int
            or type(value.depth) is not int
            or type(value.bytes) is not int
            or type(value.seconds) is not float
            or type(value.manifest_bytes) is not int
            or type(value.archive_bytes) is not int):
        raise StateError("INVALID_BUDGET_PROFILE")
    return value


def _manifest(raw, payloads, policy, deadline=None):
    policy = _coerce_manifest_policy(policy)
    _preflight_profile_manifest(raw, policy, deadline)
    if policy.profile_id is not None:
        _check_time(deadline)
    try:
        value = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, RecursionError, UnicodeError):
        raise StateError("INVALID_MANIFEST") from None
    if policy.profile_id is not None:
        _check_time(deadline)
    base_keys = {"schema", "authorization_ref", "sqlite", "limits", "roots", "entries",
                 "bracket_equal", "continuous_cross_store_consistency_certified"}
    schema = value.get("schema") if type(value) is dict else None
    if schema == "OPAQUE_STATE_BUNDLE_V1":
        expected_keys = base_keys
    elif schema in {"OPAQUE_STATE_BUNDLE_V2", "OPAQUE_STATE_BUNDLE_V3"}:
        expected_keys = base_keys | {"layout_binding"}
    else:
        raise StateError("INVALID_MANIFEST")
    if schema == "OPAQUE_STATE_BUNDLE_V3" and policy.profile_id is None:
        raise StateError("BUDGET_PROFILE_REQUIRED")
    if schema != "OPAQUE_STATE_BUNDLE_V3" and policy.profile_id is not None:
        raise StateError("BUDGET_PROFILE_MISMATCH")
    if (type(value) is not dict or set(value) != expected_keys
            or value["bracket_equal"] is not True
            or value["continuous_cross_store_consistency_certified"] is not False
            or not isinstance(value["authorization_ref"], str) or not REF.fullmatch(value["authorization_ref"])
            or not isinstance(value["roots"], list) or not 1 <= len(value["roots"]) <= 2
            or not isinstance(value["entries"], list) or len(value["entries"]) > policy.entries):
        raise StateError("INVALID_MANIFEST")
    _validate_manifest_limits(schema, value["limits"], policy)
    for root in value["roots"]:
        if type(root) is not dict or set(root) != {"scope", "identity"} or not isinstance(root["scope"], str):
            raise StateError("INVALID_MANIFEST_ROOTS")
        _valid_identity(root["identity"], "directory")
    roles = [r["scope"] for r in value["roots"]]
    if len(roles) != len(value["roots"]) or len(set(roles)) != len(roles) or set(roles) - ROLES:
        raise StateError("INVALID_MANIFEST_ROOTS")
    layout_binding = value.get("layout_binding")
    if schema in {"OPAQUE_STATE_BUNDLE_V2", "OPAQUE_STATE_BUNDLE_V3"}:
        binding_keys = {"layout_id", "operation_id", "proposal_sha256", "scope_roles", "required_entries"}
        sqlite_value = value.get("sqlite")
        try:
            if (type(sqlite_value) is not dict
                    or set(sqlite_value) != {"artifact_id", "sha256", "published_and_validated"}):
                raise StateError("INVALID_LAYOUT_BINDING")
            sqlite_receipt = _sqlite(SqliteReceipt(**sqlite_value))
        except (TypeError, StateError):
            raise StateError("INVALID_LAYOUT_BINDING") from None
        if (type(layout_binding) is not dict or set(layout_binding) != binding_keys
                or type(layout_binding.get("layout_id")) is not str
                or layout_binding["layout_id"] not in _LAYOUT_REQUIRED_ENTRIES
                or type(layout_binding.get("operation_id")) is not str
                or not REF.fullmatch(layout_binding["operation_id"])
                or type(layout_binding.get("proposal_sha256")) is not str
                or not HEX.fullmatch(layout_binding["proposal_sha256"])
                or type(layout_binding.get("scope_roles")) is not list
                or layout_binding["operation_id"] != sqlite_receipt["artifact_id"]
                or layout_binding["scope_roles"] != sorted(roles)
                or roles != sorted(roles)):
            raise StateError("INVALID_LAYOUT_BINDING")
        required = _LAYOUT_REQUIRED_ENTRIES[layout_binding["layout_id"]]
        required_roles = sorted({role for role, _ in required})
        expected_entries = [{"scope": role, "relative": relative} for role, relative in required]
        if (roles != required_roles or layout_binding["required_entries"] != expected_entries):
            raise StateError("INVALID_LAYOUT_BINDING")
    seen, members, total = set(), set(), 0
    for item in value["entries"]:
        if type(item) is not dict or not isinstance(item.get("scope"), str) or item.get("scope") not in roles:
            raise StateError("INVALID_MANIFEST_ENTRY")
        _relative(item.get("relative"), policy.depth)
        _valid_identity(item.get("identity"), item.get("kind"))
        key = (item["scope"], item["relative"])
        if key in seen:
            raise StateError("DUPLICATE_STATE_PATH")
        seen.add(key)
        if item.get("kind") == "directory":
            if set(item) != {"scope", "relative", "identity", "kind"}:
                raise StateError("INVALID_MANIFEST_ENTRY")
        elif item.get("kind") == "file":
            if (set(item) != {"scope", "relative", "identity", "kind", "member", "bytes",
                             "sha256", "classification"} or item["classification"] != "OPAQUE_PRESERVED"
                    or not isinstance(item["member"], str) or item["member"] not in payloads or item["member"] in members
                    or type(item["bytes"]) is not int or item["bytes"] < 0
                    or item["identity"]["st_size"] != item["bytes"]
                    or (item["bytes"], item["sha256"]) != payloads[item["member"]]):
                raise StateError("PAYLOAD_MANIFEST_MISMATCH")
            members.add(item["member"])
            total += item["bytes"]
        else:
            raise StateError("INVALID_MANIFEST_ENTRY")
    directories = {(e["scope"], e["relative"]) for e in value["entries"] if e["kind"] == "directory"}
    for item in value["entries"]:
        parts = _relative(item["relative"], policy.depth)
        for i in range(1, len(parts)):
            if (item["scope"], "/".join(parts[:i])) not in directories:
                raise StateError("INCOMPLETE_MANIFEST_NAMESPACE")
    if members != set(payloads) or total > policy.bytes:
        raise StateError("PAYLOAD_MANIFEST_MISMATCH")
    if schema in {"OPAQUE_STATE_BUNDLE_V2", "OPAQUE_STATE_BUNDLE_V3"}:
        _validate_required_layout_entries(layout_binding, value["entries"])
    return value


def parse_bundle(stream, *, expected_archive_sha256, expected_manifest_sha256,
                 expected_sqlite: SqliteReceipt, deadline, limits=Limits(), payload_sink=None,
                 expected_layout_id=None, expected_proposal_sha256=None, expected_scope_roles=None,
                 expected_profile_id=None):
    """Bounded USTAR subset; no extract(), pickle, links, PAX or GNU extensions."""
    _check_time(deadline)
    if type(limits) is not Limits:
        raise StateError("INVALID_LIMIT")
    policy = _policy(expected_profile_id, limits)
    sqlite = _sqlite(expected_sqlite)
    if not all(isinstance(v, str) and HEX.fullmatch(v) for v in
               (expected_archive_sha256, expected_manifest_sha256)):
        raise StateError("INVALID_EXPECTED_DIGEST")
    digest, consumed, total, payloads, manifest = hashlib.sha256(), 0, 0, {}, None

    def read(length):
        nonlocal consumed
        _check_time(deadline)
        if not 0 <= length <= policy.manifest_bytes:
            raise StateError("ARCHIVE_READ_BUDGET")
        block = stream.read(length)
        if len(block) != length:
            raise StateError("TRUNCATED_ARCHIVE")
        consumed += length
        if consumed > policy.archive_bytes:
            raise StateError("ARCHIVE_BUDGET")
        digest.update(block)
        return block

    while True:
        header = read(512)
        if header == b"\0" * 512:
            if read(512) != b"\0" * 512 or stream.read(1):
                raise StateError("TRAILING_ARCHIVE")
            break
        if manifest is not None or len(payloads) > policy.entries:
            raise StateError("ARCHIVE_MEMBER_BUDGET")
        if (header[156:157] != tarfile.REGTYPE or header[345:500].strip(b"\0")
                or header[257:263] != b"ustar\0" or header[263:265] != b"00"):
            raise StateError("UNSAFE_TAR_TYPE")
        try:
            item = tarfile.TarInfo.frombuf(header, "ascii", "strict")
        except (tarfile.TarError, ValueError, UnicodeError):
            raise StateError("INVALID_TAR_HEADER") from None
        if item.linkname or item.mode != 0o600 or item.size < 0:
            raise StateError("UNSAFE_TAR_HEADER")
        if item.name == "manifest.json":
            if not 0 < item.size <= policy.manifest_bytes:
                raise StateError("MANIFEST_BUDGET")
            raw = read(item.size)
            if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
                raise StateError("MANIFEST_HASH_MISMATCH")
            manifest = _manifest(raw, payloads, policy, deadline)
            if manifest["sqlite"] != sqlite:
                raise StateError("FOREIGN_SQLITE_RECEIPT")
            _validate_expected_layout_binding(
                manifest, expected_layout_id=expected_layout_id,
                expected_operation_id=sqlite["artifact_id"],
                expected_proposal_sha256=expected_proposal_sha256,
                expected_scope_roles=expected_scope_roles)
        else:
            if item.name != "payload/%06d" % len(payloads) or len(payloads) >= policy.entries:
                raise StateError("UNSAFE_TAR_NAME")
            total += item.size
            if total > policy.bytes:
                raise StateError("BYTE_BUDGET")
            target = payload_sink(item.name, item.size) if payload_sink is not None else None
            sha, left = hashlib.sha256(), item.size
            try:
                while left:
                    block = read(min(65536, left))
                    sha.update(block)
                    if target is not None:
                        target.write(block)
                    left -= len(block)
                if target is not None:
                    target.flush()
                    os.fsync(target.fileno())
            finally:
                if target is not None:
                    target.close()
            payloads[item.name] = (item.size, sha.hexdigest())
        if read(-item.size % 512).strip(b"\0"):
            raise StateError("NONCANONICAL_PADDING")
    if manifest is None or digest.hexdigest() != expected_archive_sha256:
        raise StateError("ARCHIVE_HASH_MISMATCH")
    return manifest


def _child_directory(parent, components):
    fd = os.dup(parent)
    try:
        for name in components:
            try:
                os.mkdir(name, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def restore_state(*, bundle: Path, expected_archive_sha256, expected_manifest_sha256,
                  expected_sqlite: SqliteReceipt, workspace: Path, expected_database_identity,
                  deadline, limits=Limits(), expected_layout_id=None,
                  expected_proposal_sha256=None, expected_scope_roles=None,
                  expected_profile_id=None):
    result = {"schema": "OWNED_STATE_RESTORE_PROTOTYPE_V1", "ok": False,
              "state_ready_before_app": False, "sqlite_restore_created": False,
              "live_restore_allowed": False, "full_application_recovery_certified": False}
    wfd = source_fd = data_fd = archive_fd = None
    created = False
    try:
        _check_time(deadline)
        _native()
        if type(limits) is not Limits:
            raise StateError("INVALID_LIMIT")
        policy = _policy(expected_profile_id, limits)
        _path(workspace)
        _path(bundle)
        if not workspace.name.startswith(".isolated_restore_327_"):
            raise StateError("OWNED_RESTORE_WORKSPACE_REQUIRED")
        wfd = _directory(workspace)
        db_info = os.stat("restoration-test.db", dir_fd=wfd, follow_symlinks=False)
        _regular(db_info)
        if _identity(db_info) != expected_database_identity:
            raise StateError("RESTORED_DATABASE_IDENTITY_MISMATCH")
        source_fd = os.open("source", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=wfd)
        pfd = _directory(bundle.parent)
        try:
            archive_fd = os.open(bundle.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=pfd)
        finally:
            os.close(pfd)
        info = os.fstat(archive_fd)
        _regular(info)
        if info.st_mode & 0o077 or info.st_size > policy.archive_bytes:
            raise StateError("PRIVATE_ARCHIVE_REQUIRED")
        with os.fdopen(os.dup(archive_fd), "rb") as stream:
            manifest = parse_bundle(stream, expected_archive_sha256=expected_archive_sha256,
                                    expected_manifest_sha256=expected_manifest_sha256,
                                    expected_sqlite=expected_sqlite, deadline=deadline, limits=limits,
                                    expected_layout_id=expected_layout_id,
                                    expected_proposal_sha256=expected_proposal_sha256,
                                    expected_scope_roles=expected_scope_roles,
                                    expected_profile_id=expected_profile_id)
        _same(info, os.fstat(archive_fd))
        # mkdir is exclusive: never merge into, replace or clear existing state.
        os.mkdir("data", 0o700, dir_fd=source_fd)
        created = True
        data_fd = os.open("data", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
        expected_files = {e["member"]: e for e in manifest["entries"] if e["kind"] == "file"}
        for root in manifest["roots"]:
            fd = _child_directory(data_fd, [DESTINATIONS[root["scope"]]])
            os.close(fd)
        for entry in manifest["entries"]:
            if entry["kind"] == "directory":
                fd = _child_directory(data_fd, [DESTINATIONS[entry["scope"]], *_relative(entry["relative"])])
                os.close(fd)

        def sink(member, length):
            entry = expected_files.get(member)
            if entry is None or entry["bytes"] != length:
                raise StateError("PAYLOAD_MANIFEST_MISMATCH")
            parts = _relative(entry["relative"], policy.depth)
            fd = _child_directory(data_fd, [DESTINATIONS[entry["scope"]], *parts[:-1]])
            try:
                output = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=fd)
            finally:
                os.close(fd)
            return os.fdopen(output, "wb")

        os.lseek(archive_fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(archive_fd), "rb") as stream:
            parse_bundle(stream, expected_archive_sha256=expected_archive_sha256,
                         expected_manifest_sha256=expected_manifest_sha256, expected_sqlite=expected_sqlite,
                         deadline=deadline, limits=limits, payload_sink=sink,
                         expected_layout_id=expected_layout_id,
                         expected_proposal_sha256=expected_proposal_sha256,
                         expected_scope_roles=expected_scope_roles,
                         expected_profile_id=expected_profile_id)
        _same(info, os.fstat(archive_fd))
        scopes = [Scope(r["scope"], workspace / "source/data" / DESTINATIONS[r["scope"]])
                  for r in manifest["roots"]]
        verified = _scan(scopes, policy, deadline)
        project = lambda records: sorted((e["scope"], e["relative"], e["kind"],
                                         e.get("bytes"), e.get("sha256")) for e in records)
        if project(verified["entries"]) != project(manifest["entries"]):
            raise StateError("RESTORED_STATE_VERIFY_FAILED")
        if _identity(os.stat("restoration-test.db", dir_fd=wfd, follow_symlinks=False)) != expected_database_identity:
            raise StateError("RESTORED_DATABASE_CHANGED")
        os.fsync(data_fd)
        _check_time(deadline)
        result.update(ok=True, code="STATE_BYTES_VERIFIED_BEFORE_APP",
                      state_ready_before_app=True, entries=verified["entries_count"],
                      state_bytes=verified["bytes"], app_started=False)
        if manifest.get("layout_binding") is not None:
            result.update(layout_id=manifest["layout_binding"]["layout_id"],
                          scope_roles=list(manifest["layout_binding"]["scope_roles"]))
    except BaseException as exc:
        result.update(code=str(exc) if isinstance(exc, StateError) else "STATE_RESTORE_FAILED",
                      error_type=type(exc).__name__,
                      partial_state_in_owned_workspace=created)
    finally:
        for fd in (archive_fd, data_fd, source_fd, wfd):
            if fd is not None:
                os.close(fd)
    return result
