"""Isolated SQLite-memory contract tests. No app import, provider or real DB."""
from __future__ import annotations
import base64
import copy
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("client_activity_candidate", ROOT / "engines/client_activity_engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class ClientActivitySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE user_activity(id TEXT PRIMARY KEY,user_id TEXT,activity_type TEXT,target_type TEXT,target_id TEXT,payload_json TEXT,created_at TEXT);
            CREATE INDEX idx_user_activity_user_type ON user_activity(user_id,activity_type,created_at);
            CREATE TABLE teams(key TEXT PRIMARY KEY,name TEXT);
            CREATE TABLE matches(id TEXT PRIMARY KEY,home_team TEXT,away_team TEXT);
            CREATE TABLE competitions(key TEXT PRIMARY KEY,name TEXT);
            INSERT INTO teams VALUES ('team-1','Norte'),('team-2','Sur');
            INSERT INTO matches VALUES ('match-1','Norte','Sur'),('match-2','Este','Oeste');
            INSERT INTO competitions VALUES ('league-1','Liga local');
        """)
        self.query_calls = []
        self.resolver_calls = []
        self.denied_operations = []

    def tearDown(self):
        self.conn.close()

    def _insert(self, item_id, *, user="alice", kind="view", target="team", target_id="team-1", date="2026-10-24T00:00:00+00:00", payload=None):
        self.conn.execute("INSERT INTO user_activity VALUES(?,?,?,?,?,?,?)",
            (item_id, user, kind, target, target_id, json.dumps(payload or {}), date))

    def _seed(self, count, *, user="alice", prefix="a"):
        for number in range(count):
            self._insert(f"{prefix}{number:03}", user=user, date=f"2026-10-24T00:00:{number:02}+00:00")

    def _rows(self, sql, params):
        self.query_calls.append((sql, params))
        return self.conn.execute(sql, params).fetchall()

    def _resolver(self, target_type, target_id):
        self.resolver_calls.append((target_type, target_id))
        if target_type == "team":
            record = self.conn.execute("SELECT key,name FROM teams WHERE key=?", (target_id,)).fetchone()
            name = record["name"] if record else None
        elif target_type == "match":
            record = self.conn.execute("SELECT id,home_team,away_team FROM matches WHERE id=?", (target_id,)).fetchone()
            name = f"{record['home_team']} — {record['away_team']}" if record else None
        else:
            record = self.conn.execute("SELECT key,name FROM competitions WHERE key=?", (target_id,)).fetchone()
            name = record["name"] if record else None
        if record is None:
            return {"verified": False, "state": "unknown"}
        return {"verified": True, "target_type": target_type, "target_id": target_id,
                "canonical_id": target_id, "name": name}

    def _authorizer(self, operation, arg1, arg2, database, trigger):
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
        if hasattr(sqlite3, "SQLITE_RECURSIVE"):
            allowed.add(sqlite3.SQLITE_RECURSIVE)
        if operation in allowed:
            return sqlite3.SQLITE_OK
        self.denied_operations.append(operation)
        return sqlite3.SQLITE_DENY

    def _snapshot(self, **overrides):
        kwargs = dict(user_id="alice", resolve_target=self._resolver)
        kwargs.update(overrides)
        self.conn.set_authorizer(self._authorizer)
        try:
            return engine.build_client_activity_snapshot(self._rows, **kwargs)
        finally:
            self.conn.set_authorizer(None)

    def test_count_and_preview_boundaries_0_7_8_20_21_25(self):
        for count in (0, 7, 8, 20, 21, 25):
            with self.subTest(count=count):
                self.conn.execute("DELETE FROM user_activity")
                self._seed(count)
                self.query_calls.clear()
                self.resolver_calls.clear()
                result = self._snapshot()
                self.assertEqual(result["state"], "available" if count else "empty", result)
                self.assertEqual(result["total"], count)
                self.assertTrue(result["total_is_exact"])
                self.assertEqual(len(result["items"]), min(count, 20))
                self.assertEqual(result["preview_count"], min(count, 7))
                self.assertEqual(result["preview_items"], result["items"][:7])
                self.assertEqual(result["has_more"], count > 20)
                self.assertEqual(len(self.query_calls), 1)
                self.assertLessEqual(len(self.resolver_calls), 20)
                self.assertFalse(self.denied_operations)
                if count > 20:
                    second = self._snapshot(cursor=result["next_cursor"])
                    self.assertEqual(second["total"], count)
                    self.assertEqual(len(second["items"]), count - 20)
                    self.assertFalse(second["has_more"])
                    self.assertFalse(set(item["id"] for item in result["items"]) & set(item["id"] for item in second["items"]))

    def test_user_and_growth_filter_precede_total_and_limit(self):
        self._seed(8)
        self._seed(25, user="bob", prefix="b")
        for number in range(25):
            self._insert(f"g{number}", kind="growth_returning", date="2026-11-01T00:00:00Z")
            self._insert(f"f{number}", target="growth_funnel", date="2026-11-02T00:00:00Z")
        self._insert("upper-internal", kind="GROWTH_ACTIVATED")
        result = self._snapshot(limit=7)
        self.assertEqual(result["total"], 8)
        self.assertTrue(all(item["id"].startswith("a") for item in result["items"]))
        second = self._snapshot(limit=7, cursor=result["next_cursor"])
        self.assertEqual(second["total"], 8)
        self.assertEqual(len(second["items"]), 1)

    def test_dst_offsets_sort_by_real_utc_instant(self):
        self._insert("earlier", date="2026-10-25T02:50:00+02:00")
        self._insert("later", date="2026-10-25T02:10:00+01:00")
        result = self._snapshot()
        self.assertEqual([item["id"] for item in result["items"]], ["later", "earlier"])
        self.assertEqual(result["items"][0]["created_at_utc"], "2026-10-25T01:10:00.000Z")

    def test_equal_utc_instants_use_id_desc_without_duplicates(self):
        self._insert("a", date="2026-10-25T02:30:00+02:00")
        self._insert("z", date="2026-10-25T01:30:00+01:00")
        self._insert("m", date="2026-10-25T00:30:00Z")
        first = self._snapshot(limit=1)
        second = self._snapshot(limit=1, cursor=first["next_cursor"])
        third = self._snapshot(limit=1, cursor=second["next_cursor"])
        self.assertEqual([first["items"][0]["id"], second["items"][0]["id"], third["items"][0]["id"]], ["z", "m", "a"])
        self.assertFalse(third["has_more"])

    def test_unknown_dates_are_last_and_page_stably(self):
        self._insert("dated-new", date="2026-10-24T10:00:00Z")
        self._insert("dated-old", date="2026-10-24T09:00:00Z")
        self._insert("unknown-z", date="not a date")
        self._insert("unknown-m", date=None)
        self._insert("unknown-a", date="")
        first = self._snapshot(limit=2)
        second = self._snapshot(limit=2, cursor=first["next_cursor"])
        third = self._snapshot(limit=2, cursor=second["next_cursor"])
        self.assertEqual([item["id"] for item in first["items"]], ["dated-new", "dated-old"])
        self.assertEqual([item["id"] for item in second["items"]], ["unknown-z", "unknown-m"])
        self.assertEqual([item["id"] for item in third["items"]], ["unknown-a"])
        for item in second["items"] + third["items"]:
            self.assertEqual(item["date_state"], "unknown")
            self.assertEqual(item["date_label"], "Fecha no establecida")
            self.assertEqual(item["created_at_utc"], "")

    def test_cursor_alteration_other_user_and_size_are_rejected_before_query(self):
        self._seed(8)
        token = self._snapshot(limit=7)["next_cursor"]
        self.query_calls.clear()
        for cursor in (token[:-1] + ("A" if token[-1] != "A" else "B"), "x" * 769, "https://example.test/?cursor=x", "===="):
            result = self._snapshot(cursor=cursor)
            self.assertEqual(result["state"], "unavailable")
            self.assertEqual(result["reason"], "cursor_invalid")
        other = self._snapshot(user_id="bob", cursor=token)
        self.assertEqual(other["reason"], "cursor_invalid")
        self.assertFalse(self.query_calls)

    def test_recomputed_checksum_cannot_anchor_to_another_users_record(self):
        self._seed(8)
        self._insert("bob-row", user="bob")
        token = self._snapshot(limit=7)["next_cursor"]
        data = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
        data.pop("c")
        data["i"] = "bob-row"
        data["j"] = None
        data["c"] = engine._cursor_checksum(data)
        altered = base64.urlsafe_b64encode(engine._canonical_cursor(data)).decode().rstrip("=")
        result = self._snapshot(cursor=altered)
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["reason"], "cursor_invalid")
        self.assertEqual(result["items"], [])

    def test_changed_or_deleted_cursor_anchor_is_rejected(self):
        self._seed(8)
        first = self._snapshot(limit=7)
        anchor_id = first["items"][-1]["id"]
        self.conn.execute("UPDATE user_activity SET created_at='2026-12-01T00:00:00Z' WHERE id=?", (anchor_id,))
        self.assertEqual(self._snapshot(cursor=first["next_cursor"])["reason"], "cursor_invalid")
        self.conn.execute("DELETE FROM user_activity WHERE id=?", (anchor_id,))
        self.assertEqual(self._snapshot(cursor=first["next_cursor"])["reason"], "cursor_invalid")

    def test_distinct_verified_entities_keep_real_names_and_detail_links(self):
        self._insert("one", target="match", target_id="match-1")
        self._insert("two", target="match", target_id="match-2")
        self._insert("three", target="competition", target_id="league-1")
        items = self._snapshot()["items"]
        by_id = {item["id"]: item for item in items}
        self.assertEqual(by_id["one"]["target_name"], "Norte — Sur")
        self.assertEqual(by_id["two"]["target_name"], "Este — Oeste")
        self.assertNotEqual(by_id["one"]["label"], by_id["two"]["label"])
        self.assertEqual(by_id["one"]["href"], "/match/match-1")
        self.assertEqual(by_id["three"]["href"], "/competition/league-1")
        self.assertIn("consultada", by_id["three"]["label"])

    def test_payload_names_and_links_are_never_used_for_unknown_targets(self):
        self._insert("unknown", target="team", target_id="gone", payload={"name": "Invented Team", "href": "javascript:alert(1)", "url": "https://evil.test/", "team_name": "Injected"})
        item = self._snapshot()["items"][0]
        self.assertEqual(item["label"], "Equipo no disponible.")
        self.assertIsNone(item["href"])
        self.assertNotIn("payload", item)
        self.assertNotIn("payload_json", item)
        self.assertNotIn("Invented", json.dumps(item))
        self.assertNotIn("evil.test", json.dumps(item))

    def test_deleted_and_ambiguous_targets_are_honest_fallbacks(self):
        self._insert("a", target="team")
        for state in ("deleted", "ambiguous", "unknown"):
            result = self._snapshot(resolve_target=lambda kind, identifier: {"verified": False, "state": state, "name": "Must not use"})
            item = result["items"][0]
            self.assertEqual(item["target_state"], state)
            self.assertEqual(item["target_name"], "")
            self.assertIsNone(item["href"])

    def test_verified_callback_href_is_ignored_and_generated_route_is_allowlisted(self):
        self._insert("a")
        def resolver(kind, identifier):
            return {"verified": True, "target_type": kind, "target_id": identifier,
                    "canonical_id": "verified-team", "name": "Actual Team", "href": "//evil.test/x"}
        item = self._snapshot(resolve_target=resolver)["items"][0]
        self.assertEqual(item["href"], "/team/verified-team")
        self.assertNotIn("evil.test", json.dumps(item))

    def test_canonical_alias_requires_matching_resolver_identity(self):
        self._insert("a", target_id="old-reference")
        valid = {"verified": True, "target_type": "team", "target_id": "old-reference", "canonical_id": "team-1", "name": "Norte"}
        self.assertEqual(self._snapshot(resolve_target=lambda *_: valid)["items"][0]["href"], "/team/team-1")
        wrong = dict(valid, target_id="another-reference")
        item = self._snapshot(resolve_target=lambda *_: wrong)["items"][0]
        self.assertEqual(item["label"], "Equipo no disponible.")
        self.assertIsNone(item["href"])

    def test_unsafe_canonical_segments_and_truthy_verification_are_not_links(self):
        self._insert("a")
        for canonical in ("../team", "//evil.test", "a?redirect=evil", "a#fragment", "a%2fb", "..", "", "x\ny"):
            identity = {"verified": True, "target_type": "team", "target_id": "team-1", "canonical_id": canonical, "name": "Actual"}
            self.assertIsNone(self._snapshot(resolve_target=lambda *_: identity)["items"][0]["href"])
        for truthy in (1, "true"):
            identity = {"verified": truthy, "target_type": "team", "target_id": "team-1", "canonical_id": "team-1", "name": "Actual"}
            self.assertIsNone(self._snapshot(resolve_target=lambda *_: identity)["items"][0]["href"])

    def test_names_are_plain_text_and_template_escapable(self):
        self.conn.execute("UPDATE teams SET name=? WHERE key='team-1'", ('<img src=x onerror="alert(1)">',))
        self._insert("a")
        item = self._snapshot()["items"][0]
        self.assertIs(type(item["label"]), str)
        escaped = html.escape(item["label"])
        self.assertNotIn("<img", escaped)
        self.assertIn("&lt;img", escaped)

    def test_read_error_and_swallowed_empty_rows_are_not_empty_history(self):
        def broken(*_args):
            raise sqlite3.OperationalError("sensitive local path or internal query")
        for callback in (broken, lambda *_args: []):
            result = engine.build_client_activity_snapshot(callback, user_id="alice")
            self.assertEqual(result["state"], "unavailable")
            self.assertIsNone(result["total"])
            self.assertFalse(result["total_is_exact"])
            self.assertTrue(result["retry_allowed"])
            self.assertNotIn("sensitive", json.dumps(result))

    def test_resolver_failure_preserves_history_but_reports_partial_enrichment(self):
        self._insert("a")
        def broken(*_args):
            raise sqlite3.OperationalError("sensitive target diagnostic")
        result = self._snapshot(resolve_target=broken)
        self.assertEqual(result["state"], "available")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["enrichment_state"], "partial")
        self.assertTrue(result["retry_allowed"])
        self.assertIsNone(result["items"][0]["href"])
        self.assertNotIn("sensitive", json.dumps(result))

    def test_user_limit_and_injection_boundaries_do_not_broaden_access(self):
        self._seed(8)
        for user in (None, "", 1, "x" * 257, "x\ny"):
            self.assertEqual(self._snapshot(user_id=user)["state"], "unavailable")
        for limit in (0, 101, True, "20", None):
            self.assertEqual(self._snapshot(limit=limit)["reason"], "limit_invalid")
        result = self._snapshot(user_id="alice' OR 1=1 --")
        self.assertEqual(result["state"], "empty")
        self.assertEqual(result["total"], 0)

    def test_no_sql_writes_or_tracking_are_introduced(self):
        self._seed(25)
        before = self.conn.total_changes
        result = self._snapshot()
        second = self._snapshot(cursor=result["next_cursor"])
        self.assertEqual(self.conn.total_changes, before)
        self.assertFalse(self.denied_operations)
        self.assertFalse(result["tracking_enabled_by_this_read"])
        self.assertFalse(second["tracking_enabled_by_this_read"])
        self.assertEqual(len(self.query_calls), 2)
        for sql, params in self.query_calls:
            self.assertNotIn("INSERT", sql.upper())
            self.assertNotIn("UPDATE", sql.upper())
            self.assertNotIn("DELETE", sql.upper())
            self.assertEqual(params[0], "alice")

    def test_repeated_local_target_is_resolved_once_per_snapshot_without_shared_cache(self):
        self._seed(25)
        self._seed(8, user="bob", prefix="b")
        first = self._snapshot()
        self.assertEqual(self.resolver_calls, [("team", "team-1")])
        self.assertEqual(first["total"], 25)
        self._snapshot(user_id="bob")
        self.assertEqual(self.resolver_calls, [("team", "team-1"), ("team", "team-1")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
