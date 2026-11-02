"""Owned disposable fixtures; these tests do not certify a real restoration."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import stat
import sys
import tempfile
import time
import unittest

from tools import recovery_app_probe as probe

ROOT = Path(__file__).absolute().parents[1]

CHILD = r'''
import json, os, pathlib, sqlite3, sys, time
source, workspace, case = map(str, sys.argv[1:])
sys.path.insert(0, source)
from tools.recovery_probe_guard import ProbeBoundary, ProbeBoundaryViolation
w = pathlib.Path(workspace)
db = w / "restoration-test.db"
src, scratch = w / "source", w / "scratch"
b = ProbeBoundary(database=db, source=src, scratch=scratch,
    libraries=(pathlib.Path(sys.prefix), pathlib.Path(sys.base_prefix)),
    mode="read_only" if case.startswith("ro_") else "normal_boot", deadline=time.monotonic()+10)
b.install()
expected = None
try:
    if case in ("normal_sql", "ro_read", "ro_write", "ro_query_off", "ro_journal"):
        c = sqlite3.connect(db)
        if case == "normal_sql":
            c.execute("CREATE TABLE second_owned(id INTEGER)")
            c.execute("INSERT INTO second_owned VALUES(1)")
            c.commit()
            assert c.execute("SELECT id FROM second_owned").fetchone() == (1,)
        elif case == "ro_read":
            assert c.execute("SELECT value FROM canary").fetchone() == ("owned",)
        elif case == "ro_write":
            expected = "SQL_WRITE"
            c.execute("INSERT INTO canary VALUES('changed')")
        elif case == "ro_query_off":
            expected = "SQL_WRITE_PRAGMA"
            c.execute("PRAGMA query_only=OFF")
        else:
            expected = "SQL_WRITE_PRAGMA"
            c.execute("PRAGMA journal_mode=WAL")
        c.close()
    elif case == "other_database":
        expected = "OTHER_DATABASE"
        sqlite3.connect(w / "another.db")
    elif case == "native_connect":
        import _sqlite3
        expected = "UNGUARDED_DATABASE_CONNECT"
        _sqlite3.connect(db)
    elif case in ("memory_uri", "duplicate_uri", "unknown_uri"):
        expected = "DATABASE_URI"
        query = {"memory_uri":"mode=memory", "duplicate_uri":"mode=rw&mode=memory", "unknown_uri":"vfs=missing"}[case]
        sqlite3.connect(db.as_uri()+"?"+query, uri=True)
    elif case == "file_write":
        expected = "FILE_PATH"
        (w / "not-admitted.txt").write_text("must not persist")
    elif case == "source_read":
        assert (src / "owned.txt").read_text() == "owned code asset"
    elif case == "source_secret":
        expected = "SECRET_FILE"
        (src / ".env").read_text()
    elif case == "outside_directory":
        expected = "FILE_PATH"
        os.listdir(w.parent)
    elif case == "network":
        import socket
        expected = "NETWORK"
        socket.socket()
    elif case == "process":
        import subprocess
        expected = "PROCESS"
        subprocess.run([sys.executable, "-c", "pass"], check=True)
    elif case == "thread":
        import threading
        expected = "BACKGROUND_THREAD"
        threading.Thread(target=lambda: None).start()
    elif case == "normal_state":
        (src / "data").mkdir()
        (src / "data/state.json").write_text("{}")
    else:
        raise AssertionError("unknown test")
except (ProbeBoundaryViolation, sqlite3.DatabaseError):
    if expected is None or expected not in b.denials:
        raise
else:
    assert expected is None, "expected operation was admitted"
sys.setprofile(None)
print(json.dumps({"case":case,"ok":True,"denials":b.denials,"connections":b.connected,"reads":b.sql_reads,"writes":b.sql_writes}))
'''


class RecoveryProbeGuardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).absolute()
        self.db = self.root / "restoration-test.db"
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("CREATE TABLE canary(value TEXT)")
            c.execute("INSERT INTO canary VALUES('owned')")
            c.commit()
        (self.root / "source").mkdir()
        (self.root / "scratch").mkdir()
        (self.root / "source/owned.txt").write_text("owned code asset")
        (self.root / "source/.env").write_text("owned canary secret")

    def run_case(self, case):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        env = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR") if k in os.environ}
        p = subprocess.run([sys.executable, "-I", "-B", "-c", CHILD, str(ROOT), str(self.root), case],
                           cwd=self.root, env=env, capture_output=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr.decode(errors="replace"))
        result = json.loads(p.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["case"], case)
        if case != "normal_sql":
            self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)
        self.assertFalse((self.root / "another.db").exists())
        self.assertFalse((self.root / "not-admitted.txt").exists())
        return result

    def test_native_normal_database_boot_writes_are_confined(self):
        r = self.run_case("normal_sql")
        self.assertEqual(r["connections"], 1)
        self.assertGreater(r["reads"], 0)
        self.assertGreater(r["writes"], 0)

    def test_native_readonly_database_can_be_read(self):
        self.assertGreater(self.run_case("ro_read")["reads"], 0)

    def test_native_readonly_denies_write(self):
        self.run_case("ro_write")

    def test_readonly_cannot_disable_query_only(self):
        self.run_case("ro_query_off")

    def test_readonly_denies_persistent_journal_change(self):
        self.run_case("ro_journal")

    def test_second_database_is_rejected_before_creation(self):
        self.run_case("other_database")

    def test_unwrapped_native_connection_is_rejected(self):
        self.run_case("native_connect")

    def test_same_path_memory_uri_is_not_a_restored_database(self):
        self.run_case("memory_uri")

    def test_duplicate_uri_parameters_are_rejected(self):
        self.run_case("duplicate_uri")

    def test_unknown_uri_parameters_are_rejected(self):
        self.run_case("unknown_uri")

    def test_file_outside_clone_allowance_is_unchanged(self):
        self.run_case("file_write")

    def test_source_assets_remain_readable(self):
        self.run_case("source_read")

    def test_source_secret_name_is_not_readable(self):
        self.run_case("source_secret")

    def test_outside_directory_is_not_listed(self):
        self.run_case("outside_directory")

    def test_network_is_rejected_before_connect(self):
        self.run_case("network")

    def test_other_process_is_rejected(self):
        self.run_case("process")

    def test_background_thread_is_rejected(self):
        self.run_case("thread")

    def test_normal_boot_state_writes_stay_in_own_source_data(self):
        self.run_case("normal_state")


class RecoveryAppProbePreflightTests(unittest.TestCase):
    def test_expired_deadline_does_not_touch_source(self):
        result = probe.run_app_probe(project_root=Path("/does-not-exist"), restored_database=Path("/none"),
                                     workspace=Path("/none"), deadline=time.monotonic()-1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "APP_PROBE_DEADLINE_EXPIRED")
        self.assertFalse(result["backup_created"])
        self.assertFalse(result["restore_created"])

    def test_invalid_mode_is_not_a_recovery_certificate(self):
        result = probe.run_app_probe(project_root=ROOT, restored_database=ROOT/"unused",workspace=ROOT,
                                     deadline=time.monotonic()+1,mode="fake")
        self.assertEqual(result["code"], "INVALID_APP_PROBE_MODE")
        self.assertFalse(result["full_application_recovery_certified"])

    def test_invalid_child_limits_fail_before_app_import(self):
        with self.assertRaises(probe.ProbeError):
            probe._run_child({"nonce":"0"*32,"mode":"normal_boot","deadline":float("inf"),
                              "memory_bytes":probe.MIB*256,"routes":["/health"]})

    def test_unavailable_storage_cannot_pass_as_empty(self):
        self.assertEqual(probe._storage_states({"data":{"home_summary":{"storage_status":"database_locked"}}}),
                         ["UNAVAILABLE_OR_UNKNOWN"])
        self.assertEqual(probe._storage_states({"data":{"storage_status":"ok","matches":[]}}), ["OK"])

    def test_search_empty_ready_is_different_from_empty_unavailable(self):
        self.assertTrue(probe._search_ready({"ok":True,"status":"READY","complete":True,"items":[]}))
        self.assertFalse(probe._search_ready({"ok":True,"status":"UNAVAILABLE","complete":False,"items":[]}))
        self.assertFalse(probe._search_ready({"ok":True,"status":"PARTIAL","complete":False,"items":[{}]}))

    def test_team_route_admission_is_bounded(self):
        self.assertTrue(probe._admitted_route("/team/owned-team_1"))
        for route in ("/team/../admin", "/team/one?secret=two", "/team/"+"x"*81, "/admin", None):
            self.assertFalse(probe._admitted_route(route))

    def test_source_policy_excludes_runtime_reports_and_secret_filename(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root).absolute()
            source, work = r/"project", r/"project/data/backups/.isolated_restore_327_owned"
            work.mkdir(parents=True)
            (source/"app.py").write_text("# owned source policy fixture only")
            (source/"reports").mkdir()
            (source/"reports/private.json").write_text("must not copy")
            (source/".env").write_text("must not copy")
            (source/"config").mkdir()
            (source/"config/credentials.json").write_text("must not copy")
            result = probe.prepare_source(source, work, deadline=time.monotonic()+5)
            target = result["path"]
            self.assertTrue((target/"app.py").is_file())
            self.assertFalse((target/"data").exists())
            self.assertFalse((target/"reports").exists())
            self.assertFalse((target/".env").exists())
            self.assertFalse((target/"config/credentials.json").exists())

    @unittest.skipUnless(__import__('os').name == 'posix', 'Native POSIX descriptor admission')
    def test_source_descriptor_does_not_block_on_fifo(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root).absolute()
            os.mkfifo(r/"owned.py")
            started = time.monotonic()
            fd = probe._source_descriptor(r, Path("owned.py"), probe._identity(r.stat()))
            try:
                self.assertTrue(stat.S_ISFIFO(os.fstat(fd).st_mode))
            finally:
                os.close(fd)
            self.assertLess(time.monotonic()-started, 1)

    @unittest.skipUnless(__import__('os').name == 'posix', 'Native POSIX descriptor admission')
    def test_source_descriptor_rejects_linked_ancestor(self):
        with tempfile.TemporaryDirectory() as root:
            r = Path(root).absolute()
            source, outside = r/"source", r/"outside"
            source.mkdir(); outside.mkdir()
            (outside/"owned.py").write_text("must not read")
            (source/"engines").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                probe._source_descriptor(source, Path("engines/owned.py"), probe._identity(source.stat()))
