"""Confinement for a fixed App smoke, not a sandbox for arbitrary Python.

The only database is the disposable restoration. Normal boot may mutate that
working copy; a read-only diagnostic may not. External actions stay denied.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
from urllib.parse import parse_qsl, unquote, urlsplit


SECRET_FILE = re.compile(r"^\.env(?:\.|$)|\.(?:key|pem|p12|pfx)\Z", re.I)
PROCESS_EVENTS = frozenset(("subprocess.Popen", "os.system", "os.exec", "os.spawn",
                            "os.posix_spawn", "os.fork", "os.forkpty"))
MUTATION_EVENTS = frozenset(("os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.chown",
                             "os.utime", "os.truncate", "os.rename", "os.replace", "os.link", "os.symlink"))
WRITE_SQL = frozenset(getattr(sqlite3, name) for name in (
    "SQLITE_INSERT", "SQLITE_UPDATE", "SQLITE_DELETE", "SQLITE_CREATE_INDEX", "SQLITE_CREATE_TABLE",
    "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_TABLE", "SQLITE_CREATE_TEMP_TRIGGER",
    "SQLITE_CREATE_TEMP_VIEW", "SQLITE_CREATE_TRIGGER", "SQLITE_CREATE_VIEW", "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TABLE", "SQLITE_DROP_TEMP_INDEX", "SQLITE_DROP_TEMP_TABLE", "SQLITE_DROP_TEMP_TRIGGER",
    "SQLITE_DROP_TEMP_VIEW", "SQLITE_DROP_TRIGGER", "SQLITE_DROP_VIEW", "SQLITE_ALTER_TABLE",
    "SQLITE_CREATE_VTABLE", "SQLITE_DROP_VTABLE", "SQLITE_REINDEX", "SQLITE_ANALYZE"))


class ProbeBoundaryViolation(BaseException):
    """Abort this diagnostic; App's recovery fallbacks must not hide denials."""


class ProbeBoundary:
    def __init__(self, *, database: Path, source: Path, scratch: Path, libraries, mode: str, deadline: float):
        self.database, self.source, self.scratch = database, source, scratch
        self.data = source / "data"
        self.libraries = tuple(Path(p) for p in libraries)
        self.mode, self.deadline = mode, deadline
        self.denials, self.sql_reads, self.sql_writes, self.fs_writes, self.seed_calls = [], 0, 0, 0, 0
        self.degraded_calls = 0
        self.connected = 0
        self.read_executions, self.read_fetches = 0, 0
        self.timezone_reads = {"UTC": 0, "Europe/Madrid": 0}
        self._connecting, self._configuring = False, False
        self._state_read_role, self._state_read_target = None, None
        self._state_read_open_attempt_counts = {"ce": 0, "legacy_runtime": 0}
        self._state_read_full_counts = {"ce": 0, "legacy_runtime": 0}
        self._state_pending_reads = []
        self._state_read_identity = None
        self._state_read_expected_size = 0
        self._state_decoy_open_attempts = 0
        self._native_connect = sqlite3.connect
        boundary = self

        class ObservedCursor(sqlite3.Cursor):
            def execute(self, *args, **kwargs):
                before_denials = len(boundary.denials)
                try:
                    result = super().execute(*args, **kwargs)
                except sqlite3.DatabaseError:
                    if len(boundary.denials) > before_denials:
                        raise ProbeBoundaryViolation("APP_PROBE_BOUNDARY_SQL") from None
                    raise
                if self.description is not None:
                    boundary.read_executions += 1
                return result

            def fetchone(self):
                result = super().fetchone()
                if self.description is not None:
                    boundary.read_fetches += 1
                return result

            def fetchmany(self, *args, **kwargs):
                result = super().fetchmany(*args, **kwargs)
                if self.description is not None:
                    boundary.read_fetches += 1
                return result

            def fetchall(self):
                result = super().fetchall()
                if self.description is not None:
                    boundary.read_fetches += 1
                return result

            def __next__(self):
                try:
                    result = super().__next__()
                except StopIteration:
                    if self.description is not None:
                        boundary.read_fetches += 1
                    raise
                if self.description is not None:
                    boundary.read_fetches += 1
                return result

        class ObservedConnection(sqlite3.Connection):
            def cursor(self, factory=None):
                if factory not in (None, sqlite3.Cursor):
                    boundary.deny("CUSTOM_CURSOR_FACTORY")
                return super().cursor(factory=ObservedCursor)

            def execute(self, *args, **kwargs):
                return self.cursor().execute(*args, **kwargs)

        self._observed_factory = ObservedConnection

    def deny(self, code):
        if len(self.denials) < 64:
            self.denials.append(code)
        raise ProbeBoundaryViolation("APP_PROBE_BOUNDARY_" + code)

    def _sql_deny(self, code):
        if len(self.denials) < 64:
            self.denials.append(code)
        return sqlite3.SQLITE_DENY

    @staticmethod
    def _under(path, root):
        return path == root or path.is_relative_to(root)

    def _path(self, value):
        try:
            raw = os.fsdecode(value)
            if raw.startswith(("//", "\\\\")):
                self.deny("REMOTE_FILE_PATH")
            path = Path(raw)
            if not path.is_absolute():
                path = Path.cwd() / path
            if not path.is_absolute() or ".." in path.parts:
                self.deny("PATH_TRAVERSAL")
            # Lexical rejection precedes lstat: probing an external UNC or
            # mount is already an unwanted OS access, even without open().
            if not (path == self.database or str(path) in {str(self.database)+s for s in ("-wal", "-shm", "-journal")}
                    or self._under(path, self.source) or self._under(path, self.scratch)
                    or any(self._under(path, root) for root in self.libraries)
                    or (os.name == "posix" and self._under(path, Path("/usr/share/zoneinfo")))
                    or path == self.database.parent):
                self.deny("FILE_PATH")
            # Reject existing reparse/symlink ancestors without resolving them.
            for part in (*reversed(path.parents), path):
                try:
                    info = part.lstat()
                except FileNotFoundError:
                    continue
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    self.deny("FILE_LINK")
            return path
        except (TypeError, ValueError, OSError):
            if sys.exc_info()[0] is PermissionError:
                raise
            self.deny("FILE_PATH")

    def _writable(self, path):
        if self._under(path, self.scratch):
            return True
        if self.mode != "normal_boot":
            return False
        return (path == self.database or str(path) in {str(self.database) + s for s in ("-wal", "-shm", "-journal")}
                or self._under(path, self.data))

    def observe_state_file(self, role, path, reader):
        """Observe the exact owner getter and a complete native-file read."""
        if role not in ("ce", "legacy_runtime") or not callable(reader):
            self.deny("STATE_READ_OBSERVER")
        target = self._path(path)
        if target == self.data or not self._under(target, self.data):
            self.deny("STATE_READ_TARGET")
        try:
            before = target.lstat()
        except OSError:
            self.deny("STATE_READ_TARGET")
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            self.deny("STATE_READ_IDENTITY")
        if self._state_read_role is not None:
            self.deny("NESTED_STATE_READ_OBSERVER")
        identity = (before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
                    before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        open_count = self._state_read_open_attempt_counts[role]
        successful_count = self._state_read_full_counts[role]
        previous_profile = sys.getprofile()
        self._state_read_role, self._state_read_target = role, target
        self._state_read_identity = identity
        self._state_read_expected_size = before.st_size
        try:
            sys.setprofile(self.profile)
            value = reader()
        finally:
            self._state_read_role, self._state_read_target = None, None
            self._state_read_identity = None
            self._state_read_expected_size = 0
            self._state_pending_reads = [entry for entry in self._state_pending_reads if entry[2] != role]
            sys.setprofile(previous_profile)
        try:
            after = target.lstat()
        except OSError:
            self.deny("STATE_READ_TARGET")
        after_identity = (after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
                          after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if not stat.S_ISREG(after.st_mode) or after.st_nlink != 1 or identity != after_identity:
            self.deny("STATE_READ_IDENTITY_CHANGED")
        return (value, self._state_read_open_attempt_counts[role] - open_count,
                self._state_read_full_counts[role] - successful_count)

    def _database_path(self, value):
        if not isinstance(value, (str, os.PathLike)):
            self.deny("OTHER_DATABASE")
        raw = os.fspath(value)
        if raw.startswith("file:"):
            parsed = urlsplit(raw)
            options = parse_qsl(parsed.query, keep_blank_values=True)
            allowed = {"mode": {"ro", "rw"}, "immutable": {"0", "1"}, "cache": {"private"}}
            if (parsed.netloc or parsed.fragment or len({k for k, _ in options}) != len(options)
                    or any(k not in allowed or v not in allowed[k] for k, v in options)):
                self.deny("DATABASE_URI")
            raw = unquote(parsed.path)
            if os.name == "nt" and re.match(r"^/[A-Za-z]:", raw):
                raw = raw[1:]
        path = Path(raw)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path != self.database:
            self.deny("OTHER_DATABASE")
        path = self._path(raw)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            self.deny("DATABASE_IDENTITY")
        return path

    def connect(self, *args, **kwargs):
        self._database_path(args[0] if args else kwargs.get("database"))
        factory = args[5] if len(args) > 5 else kwargs.get("factory", sqlite3.Connection)
        if factory is not sqlite3.Connection:
            self.deny("CUSTOM_CONNECTION_FACTORY")
        values = list(args)
        if len(values) > 5:
            values[5] = self._observed_factory
        else:
            kwargs["factory"] = self._observed_factory
        args = tuple(values)
        if self.mode == "read_only":
            # Same actual database, with an independently enforced read capability.
            # Attempts by App to write are still observed by the authorizer.
            values = list(args)
            uri = self.database.as_uri() + "?mode=ro&immutable=1"
            if values:
                values[0] = uri
            else:
                kwargs["database"] = uri
            if len(values) > 7:
                values[7] = True
            else:
                kwargs["uri"] = True
            args = tuple(values)
        self._connecting = True
        try:
            connection = self._native_connect(*args, **kwargs)
        finally:
            self._connecting = False
        # CPython emits connect/handle BEFORE Connection.__init__ completes.
        # Configure only after native construction, before giving App the handle.
        try:
            connection.set_authorizer(self.authorize_sql)
            connection.set_progress_handler(lambda: int(time.monotonic() >= self.deadline), 1000)
            self._configuring = True
            try:
                connection.execute("PRAGMA temp_store=MEMORY")
                if self.mode == "read_only":
                    connection.execute("PRAGMA query_only=ON")
            finally:
                self._configuring = False
            self.connected += 1
            return connection
        except BaseException:
            connection.close()
            raise

    def authorize_sql(self, action, first, second, _database, _trigger):
        if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
            return self._sql_deny("SQL_ATTACH")
        if action == sqlite3.SQLITE_FUNCTION and str(second or first).lower() in ("load_extension", "readfile", "writefile", "fts3_tokenizer"):
            return self._sql_deny("SQL_EXTERNAL_FUNCTION")
        if action == sqlite3.SQLITE_PRAGMA:
            pragma = str(first).lower()
            if pragma in ("temp_store_directory", "data_store_directory", "writable_schema"):
                return self._sql_deny("SQL_EXTERNAL_PRAGMA")
            if self.mode == "read_only" and second is not None and not self._configuring:
                if pragma == "query_only" and str(second).lower() not in ("1", "on", "true", "yes"):
                    return self._sql_deny("SQL_WRITE_PRAGMA")
                if pragma not in ("query_only", "busy_timeout", "foreign_keys", "temp_store", "synchronous"):
                    return self._sql_deny("SQL_WRITE_PRAGMA")
        if action in WRITE_SQL:
            if self.mode == "read_only":
                return self._sql_deny("SQL_WRITE")
            self.sql_writes += 1
        if action == sqlite3.SQLITE_READ:
            self.sql_reads += 1
        return sqlite3.SQLITE_OK

    def audit(self, event, args):
        if event.startswith("socket."):
            self.deny("NETWORK")
        if event in PROCESS_EVENTS:
            self.deny("PROCESS")
        if event == "os.chdir":
            self.deny("WORKING_DIRECTORY_CHANGE")
        if event in ("os.listdir", "os.scandir"):
            if args and args[0] is not None:
                if not isinstance(args[0], (str, bytes, os.PathLike)):
                    self.deny("DIRECTORY_HANDLE")
                self._path(args[0])
            else:
                self._path(".")
        if event.startswith("sqlite3.") and event in ("sqlite3.load_extension", "sqlite3.enable_load_extension"):
            self.deny("SQL_EXTENSION")
        if event == "sqlite3.connect":
            if not self._connecting:
                self.deny("UNGUARDED_DATABASE_CONNECT")
            self._database_path(args[0])
        elif event == "sqlite3.connect/handle":
            if not self._connecting:
                self.deny("UNGUARDED_DATABASE_CONNECT")
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = self._path(args[0])
            mode, flags = args[1], args[2]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing:
                if not self._writable(path):
                    self.deny("FILE_WRITE")
                self.fs_writes += 1
                return
            if self._state_read_role is not None:
                if path == self._state_read_target:
                    self._state_read_open_attempt_counts[self._state_read_role] += 1
                decoys = (
                    self.data / "runtime" / "continuous_evolution_os" / "product_memory.json",
                    self.data / "runtime" / "sentinel_issues_memory.json",
                )
                if path != self._state_read_target and path in decoys:
                    self._state_decoy_open_attempts += 1
            if any(SECRET_FILE.search(part) for part in path.parts):
                self.deny("SECRET_FILE")
            if path == self.database or self._under(path, self.source) or self._under(path, self.scratch):
                return
            if any(self._under(path, root) for root in self.libraries) or self._under(path, Path("/usr/share/zoneinfo")):
                if path.parts[-3:] == ("tzdata", "zoneinfo", "UTC"):
                    self.timezone_reads["UTC"] += 1
                elif path.parts[-4:] == ("tzdata", "zoneinfo", "Europe", "Madrid"):
                    self.timezone_reads["Europe/Madrid"] += 1
                return
            self.deny("FILE_READ")
        if event in MUTATION_EVENTS:
            if event == "os.mkdir" and self.mode == "normal_boot":
                path = self._path(args[0])
                # Normal connect() requests mkdir(exist_ok=True) for its existing
                # disposable parent. This does not permit other parent mutations.
                if path == self.database.parent and path.is_dir():
                    self.fs_writes += 1
                    return
            targets = args[:2] if event in ("os.rename", "os.replace", "os.link", "os.symlink") else args[:1]
            if any(not isinstance(p, (str, bytes, os.PathLike)) or not self._writable(self._path(p)) for p in targets):
                self.deny("FILESYSTEM_MUTATION")
            self.fs_writes += 1

    def _profile_file_path(self, owner):
        value = getattr(owner, "name", None)
        if not isinstance(value, (str, bytes, os.PathLike)):
            return None
        candidate = Path(os.fsdecode(value))
        return candidate if candidate.is_absolute() else Path.cwd() / candidate

    @staticmethod
    def _native_file_identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def profile(self, frame, event, argument):
        name = frame.f_code.co_name
        if event == "call" and name in ("seed_core", "_seed_core_unlocked", "init_db", "initialize_once",
                                         "v931_record_client_route_issue", "v932_record_authenticated_issue"):
            if frame.f_code.co_filename == str(self.source / "app.py"):
                if name in ("v931_record_client_route_issue", "v932_record_authenticated_issue"):
                    self.degraded_calls += 1
                    return
                self.seed_calls += 1

        if (self._state_read_role is None or event not in ("c_call", "c_return", "c_exception")
                or argument is None):
            return
        method_name = getattr(argument, "__name__", None)
        if method_name not in ("read", "read1", "readall", "readline", "readlines",
                               "readinto", "readinto1", "__next__"):
            return
        owner = getattr(argument, "__self__", None)
        if (owner is None or type(owner).__module__ != "_io"
                or self._profile_file_path(owner) != self._state_read_target):
            return
        if event == "c_call":
            try:
                position = owner.tell()
                descriptor = owner.fileno()
                descriptor_position = os.lseek(descriptor, 0, os.SEEK_CUR)
                descriptor_identity = self._native_file_identity(os.fstat(descriptor))
            except (AttributeError, OSError, ValueError):
                return
            if (type(position) is int and position == 0 and descriptor_position == 0
                    and self._state_read_expected_size > 0
                    and descriptor_identity == self._state_read_identity):
                self._state_pending_reads.append(
                    (owner, method_name, self._state_read_role, self._state_read_target,
                     position, descriptor, descriptor_identity, self._state_read_expected_size))
            return
        for index in range(len(self._state_pending_reads) - 1, -1, -1):
            (pending_owner, pending_name, role, target, before_position,
             descriptor, before_identity, expected_size) = self._state_pending_reads[index]
            if (pending_owner is owner and pending_name == method_name
                    and role == self._state_read_role and target == self._state_read_target):
                self._state_pending_reads.pop(index)
                if event != "c_return":
                    return
                try:
                    descriptor_position = os.lseek(descriptor, 0, os.SEEK_CUR)
                    after_identity = self._native_file_identity(os.fstat(descriptor))
                    logical_position = owner.tell()
                except (AttributeError, OSError, ValueError):
                    return
                if (before_position == 0 and descriptor_position == expected_size
                        and type(logical_position) is int and logical_position == expected_size
                        and before_identity == self._state_read_identity
                        and after_identity == before_identity):
                    self._state_read_full_counts[role] += 1
                return

    def install(self):
        import _thread
        import threading
        import sqlite3.dbapi2
        sqlite3.connect = self.connect
        sqlite3.dbapi2.connect = self.connect
        _thread.start_new_thread = lambda *a, **k: self.deny("BACKGROUND_THREAD")
        threading.Thread.start = lambda *a, **k: self.deny("BACKGROUND_THREAD")
        sys.addaudithook(self.audit)
        sys.setprofile(self.profile)
