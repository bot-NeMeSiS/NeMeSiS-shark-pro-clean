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
ROLES = frozenset(("ce", "legacy_runtime"))
DESTINATIONS = {"ce": "continuous_evolution_os", "legacy_runtime": "runtime"}
SECRET = re.compile(r"(^\.env(?:\.|$)|secret|credential|token|^id_|\.(?:key|pem|p12|pfx)$)", re.I)
HEX = re.compile(r"[0-9a-f]{64}\Z")
REF = re.compile(r"[A-Z0-9_-]{1,96}\Z")


_ERROR_CODES = frozenset(["ARCHIVE_BUDGET","ARCHIVE_HASH_MISMATCH","ARCHIVE_MEMBER_BUDGET","ARCHIVE_READ_BUDGET","BYTE_BUDGET","DEADLINE_EXPIRED","DUPLICATE_MANIFEST_KEY","DUPLICATE_STATE_PATH","ENTRY_BUDGET","FOREIGN_SQLITE_RECEIPT","INCOMPLETE_MANIFEST_NAMESPACE","INVALID_DEADLINE","INVALID_EXPECTED_DIGEST","INVALID_LIMIT","INVALID_MANIFEST","INVALID_MANIFEST_ENTRY","INVALID_MANIFEST_IDENTITY","INVALID_MANIFEST_LIMITS","INVALID_MANIFEST_ROOTS","INVALID_SCOPES","INVALID_TAR_HEADER","MANIFEST_BUDGET","MANIFEST_HASH_MISMATCH","NONCANONICAL_PADDING","OWNED_RESTORE_WORKSPACE_REQUIRED","PAYLOAD_MANIFEST_MISMATCH","PRIVATE_ARCHIVE_REQUIRED","PRIVATE_PUBLICATION_NAMESPACE_REQUIRED","PROTECTED_SQLITE_PATHS_REQUIRED","PUBLICATION_IDENTITY_CHANGED","PUBLICATION_ROOT_OVERLAP","RESTORED_DATABASE_CHANGED","RESTORED_DATABASE_IDENTITY_MISMATCH","RESTORED_STATE_VERIFY_FAILED","SECRET_CUSTODY_REQUIRED","SOURCE_CHANGED","SOURCE_ROOT_OVERLAP","SPECIFIC_DATA_AUTHORITY_REQUIRED","SQLITE_RECEIPT_NOT_VERIFIED","SQLITE_SCOPE_COLLISION","STATE_CHANGED_ACROSS_SQLITE_INTERVAL","STATE_LINK","STRONG_FD_PRIMITIVES_UNSUPPORTED","TRAILING_ARCHIVE","TRUNCATED_ARCHIVE","UNCLASSIFIED_STATE_ERROR","UNSAFE_MEMBER_PATH","UNSAFE_PATH","UNSAFE_STATE_FILE","UNSAFE_TAR_HEADER","UNSAFE_TAR_NAME","UNSAFE_TAR_TYPE"])


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

    def manifest(self, value):
        raw = _canonical(value)
        if len(raw) > MAX_MANIFEST:
            raise StateError("MANIFEST_BUDGET")
        self._header("manifest.json", len(raw))
        self.stream.write(raw)
        self.stream.write(b"\0" * (-len(raw) % 512))
        self.stream.write(b"\0" * 1024)
        return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


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
                  sqlite_snapshot_callback, limits: Limits = Limits()):
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
        scopes = _scopes(scopes, authorization)
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
            before = _scan(scopes, limits, deadline, writer, authorization.protected_sqlite_paths)
            _check_time(deadline)
            result["sqlite_callback_invoked"] = True
            receipt = sqlite_snapshot_callback(deadline)
            result["sqlite_receipt"] = _sqlite(receipt)
            _check_time(deadline)
            after = _scan(scopes, limits, deadline, protected=authorization.protected_sqlite_paths)
            if _comparable(before) != _comparable(after):
                raise StateError("STATE_CHANGED_ACROSS_SQLITE_INTERVAL")
            manifest = {"schema": "OPAQUE_STATE_BUNDLE_V1", "authorization_ref": authorization.evidence_ref,
                        "sqlite": result["sqlite_receipt"], "limits": asdict(limits),
                        "roots": before["roots"], "entries": before["entries"],
                        "bracket_equal": True,
                        "continuous_cross_store_consistency_certified": False}
            mh = writer.manifest(manifest)
            stream.flush()
            os.fsync(stream.fileno())
            _check_time(deadline)
            archive_sha = _hash_fd(stream.fileno(), deadline, MAX_ARCHIVE)
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


def _manifest(raw, payloads, limits):
    try:
        value = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, RecursionError, UnicodeError):
        raise StateError("INVALID_MANIFEST") from None
    keys = {"schema", "authorization_ref", "sqlite", "limits", "roots", "entries",
            "bracket_equal", "continuous_cross_store_consistency_certified"}
    if (type(value) is not dict or set(value) != keys or value["schema"] != "OPAQUE_STATE_BUNDLE_V1"
            or value["bracket_equal"] is not True
            or value["continuous_cross_store_consistency_certified"] is not False
            or not isinstance(value["authorization_ref"], str) or not REF.fullmatch(value["authorization_ref"])
            or not isinstance(value["roots"], list) or not 1 <= len(value["roots"]) <= 2
            or not isinstance(value["entries"], list) or len(value["entries"]) > limits.entries):
        raise StateError("INVALID_MANIFEST")
    try:
        if type(value["limits"]) is not dict or set(value["limits"]) != {"entries", "depth", "bytes", "seconds"}:
            raise StateError("INVALID_MANIFEST_LIMITS")
        Limits(**value["limits"])
    except (TypeError, ValueError):
        raise StateError("INVALID_MANIFEST_LIMITS") from None
    for root in value["roots"]:
        if type(root) is not dict or set(root) != {"scope", "identity"} or not isinstance(root["scope"], str):
            raise StateError("INVALID_MANIFEST_ROOTS")
        _valid_identity(root["identity"], "directory")
    roles = [r["scope"] for r in value["roots"]]
    if len(roles) != len(value["roots"]) or len(set(roles)) != len(roles) or set(roles) - ROLES:
        raise StateError("INVALID_MANIFEST_ROOTS")
    seen, members, total = set(), set(), 0
    for item in value["entries"]:
        if type(item) is not dict or not isinstance(item.get("scope"), str) or item.get("scope") not in roles:
            raise StateError("INVALID_MANIFEST_ENTRY")
        _relative(item.get("relative"), limits.depth)
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
        parts = _relative(item["relative"], limits.depth)
        for i in range(1, len(parts)):
            if (item["scope"], "/".join(parts[:i])) not in directories:
                raise StateError("INCOMPLETE_MANIFEST_NAMESPACE")
    if members != set(payloads) or total > limits.bytes:
        raise StateError("PAYLOAD_MANIFEST_MISMATCH")
    return value


def parse_bundle(stream, *, expected_archive_sha256, expected_manifest_sha256,
                 expected_sqlite: SqliteReceipt, deadline, limits=Limits(), payload_sink=None):
    """Bounded USTAR subset; no extract(), pickle, links, PAX or GNU extensions."""
    _check_time(deadline)
    if type(limits) is not Limits:
        raise StateError("INVALID_LIMIT")
    sqlite = _sqlite(expected_sqlite)
    if not all(isinstance(v, str) and HEX.fullmatch(v) for v in
               (expected_archive_sha256, expected_manifest_sha256)):
        raise StateError("INVALID_EXPECTED_DIGEST")
    digest, consumed, total, payloads, manifest = hashlib.sha256(), 0, 0, {}, None

    def read(length):
        nonlocal consumed
        _check_time(deadline)
        if not 0 <= length <= MAX_MANIFEST:
            raise StateError("ARCHIVE_READ_BUDGET")
        block = stream.read(length)
        if len(block) != length:
            raise StateError("TRUNCATED_ARCHIVE")
        consumed += length
        if consumed > MAX_ARCHIVE:
            raise StateError("ARCHIVE_BUDGET")
        digest.update(block)
        return block

    while True:
        header = read(512)
        if header == b"\0" * 512:
            if read(512) != b"\0" * 512 or stream.read(1):
                raise StateError("TRAILING_ARCHIVE")
            break
        if manifest is not None or len(payloads) > limits.entries:
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
            if not 0 < item.size <= MAX_MANIFEST:
                raise StateError("MANIFEST_BUDGET")
            raw = read(item.size)
            if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
                raise StateError("MANIFEST_HASH_MISMATCH")
            manifest = _manifest(raw, payloads, limits)
            if manifest["sqlite"] != sqlite:
                raise StateError("FOREIGN_SQLITE_RECEIPT")
        else:
            if item.name != "payload/%06d" % len(payloads) or len(payloads) >= limits.entries:
                raise StateError("UNSAFE_TAR_NAME")
            total += item.size
            if total > limits.bytes:
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
                  deadline, limits=Limits()):
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
        if info.st_mode & 0o077 or info.st_size > MAX_ARCHIVE:
            raise StateError("PRIVATE_ARCHIVE_REQUIRED")
        with os.fdopen(os.dup(archive_fd), "rb") as stream:
            manifest = parse_bundle(stream, expected_archive_sha256=expected_archive_sha256,
                                    expected_manifest_sha256=expected_manifest_sha256,
                                    expected_sqlite=expected_sqlite, deadline=deadline, limits=limits)
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
            parts = _relative(entry["relative"], limits.depth)
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
                         deadline=deadline, limits=limits, payload_sink=sink)
        _same(info, os.fstat(archive_fd))
        scopes = [Scope(r["scope"], workspace / "source/data" / DESTINATIONS[r["scope"]])
                  for r in manifest["roots"]]
        verified = _scan(scopes, limits, deadline)
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
    except BaseException as exc:
        result.update(code=str(exc) if isinstance(exc, StateError) else "STATE_RESTORE_FAILED",
                      error_type=type(exc).__name__,
                      partial_state_in_owned_workspace=created)
    finally:
        for fd in (archive_fd, data_fd, source_fd, wfd):
            if fd is not None:
                os.close(fd)
    return result
