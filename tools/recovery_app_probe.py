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


def run_app_probe(*, project_root: Path, restored_database: Path, workspace: Path,
                  deadline: float, mode: str = "read_only", routes=DEFAULT_ROUTES,
                  memory_bytes: int = 256 * MIB) -> dict:
    """Explicit smoke only. Does not capture, restore, delete or certify a backup."""
    report = {"schema": "NEMESIS_ISOLATED_APP_PROBE_V1", "mode": mode, "ok": False,
              "full_application_recovery_certified": False, "authenticated_client_verified": False,
              "external_services_verified": False, "backup_created": False, "restore_created": False}
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
        source = prepare_source(project_root, workspace, deadline=deadline)
        scratch = workspace / "scratch"
        scratch.mkdir()
        memory = _render_memory_gate(memory_bytes)
        report["memory_preflight"] = memory
        if not memory["allowed"]:
            raise ProbeError("APP_MEMORY_PREFLIGHT_REFUSED")
        nonce = secrets.token_hex(16)
        payload = {"nonce": nonce, "source": str(source["path"]), "database": str(restored_database), "workspace": str(workspace),
                   "scratch": str(scratch), "deadline": deadline, "mode": mode, "routes": list(routes),
                   "memory_bytes": memory_bytes}
        env = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ}
        env.update(PATH=str(Path(sys.executable).parent), TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch),
                   PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
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
        report["code"] = "APP_SMOKE_VERIFIED" if report["ok"] else "APP_SMOKE_NOT_VERIFIED"
    except (OSError, ValueError, TypeError, ProbeError) as exc:
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
    clean = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "PATH") if k in os.environ}
    clean.update(DB_PATH=str(database), SECRET_KEY=secrets.token_urlsafe(32),
                 CONTINUOUS_EVOLUTION_STORAGE_ROOT=str(source / "data/runtime/continuous_evolution_os"),
                 PUBLIC_BASE_URL="https://probe.nemesis.invalid", PYTHON_DOTENV_DISABLED="1",
                 BACKUP_DIR=str(source / "data/backups"), DATA_BACKUP_DIR=str(source / "data/backups"),
                 TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch),
                 MPLCONFIGDIR=str(scratch), XDG_CACHE_HOME=str(scratch),
                 RUN_STARTUP_SCHEDULER_NOW="0", SCHEDULER_ENABLED="0", ENABLE_AUTO_SYNC="0",
                 AUTO_SYNC_ON_STARTUP="0", BACKGROUND_JOBS_ENABLED="0", AUTO_GENERATE_PICKS="0",
                 AUTO_SEND_TELEGRAM_PICKS="0", DATA_BACKUP_ENABLED="0", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    os.environ.clear()
    os.environ.update(clean)
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
                  external_state_restoration_verified=False)
    report["ok"] = report["ok"] and not boundary.denials
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
