"""Native review scheduling uses persistent receipts without chat or providers."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from engines import product_review_system_engine as engine
from tools import render_cron_master_tick as master


TASK = "platform_workforce_review"


class NativeWorkforceSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.storage = self.root / "review-store"
        self.calls = []

    def native(self, _root, _version, **kwargs):
        lock = json.loads((self.storage / "scheduler.lock").read_text())
        self.assertEqual(lock["job_id"], kwargs["job_id"])
        self.assertTrue(kwargs["write"])
        self.calls.append(kwargs)
        run_id = "NWR-" + format(len(self.calls), "016x")
        receipt = {"receipt_id": run_id, "review_kind": "STATIC_PARTIAL", "outcome": "UNKNOWN",
                   "executed_count": 22, "expected_count": 22}
        run = {"run_id": run_id, "duration_ms": 1, "result": "PASS"}
        return {"ok": True, "result": "PASS", "run_id": run_id, "duration_ms": 1,
                "run": run, "receipt": receipt}

    def run_native(self, now, **kwargs):
        return engine.run_continuous_evolution_scheduler_task(
            self.root, "TEST", task_name=TASK, now=now, storage_root=self.storage,
            trigger=kwargs.pop("trigger", "SCHEDULED_PRODUCTION"), **kwargs,
        )

    def state(self):
        return json.loads((self.storage / "scheduler_state.json").read_text())

    def test_hourly_executes_native_checks_and_never_daily_full_cycle(self):
        with patch.object(engine, "run_native_workforce_review", self.native, create=True), \
             patch.object(engine, "run_continuous_evolution_cycle", side_effect=AssertionError("full daily cycle")):
            result = self.run_native("2026-10-29T11:10:00+01:00")
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result["receipt"]["executed_count"], 22)
        self.assertIsNone(result["job"]["founder_brief_id"])
        self.assertIsNone(result["job"]["snapshot_id"])
        self.assertEqual(self.state()["tasks"][TASK]["last_completed_period"], "2026-10-29T10:00Z")
        self.assertFalse((self.storage / "scheduler.lock").exists())

    def test_repeated_tick_preserves_last_receipt_and_does_not_write_new_job(self):
        with patch.object(engine, "run_native_workforce_review", self.native, create=True):
            first = self.run_native("2026-10-29T11:10:00+01:00")
            before = (self.storage / "scheduler_state.json").read_bytes()
            logs = list((self.storage / "job_logs").iterdir())
            second = self.run_native("2026-10-29T11:15:00+01:00")
        self.assertEqual(second["result"], "SKIPPED_NOT_DUE")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(before, (self.storage / "scheduler_state.json").read_bytes())
        self.assertEqual(logs, list((self.storage / "job_logs").iterdir()))
        self.assertEqual(self.state()["tasks"][TASK]["last_receipt_id"], first["receipt"]["receipt_id"])

    def test_next_utc_hour_runs_once(self):
        with patch.object(engine, "run_native_workforce_review", self.native, create=True):
            self.run_native("2026-10-29T11:10:00+01:00")
            self.run_native("2026-10-29T12:00:00+01:00")
        self.assertEqual(len(self.calls), 2)

    def test_autumn_repeated_madrid_hour_has_distinct_utc_periods(self):
        with patch.object(engine, "run_native_workforce_review", self.native, create=True):
            first = self.run_native("2026-10-25T02:10:00+02:00")
            second = self.run_native("2026-10-25T02:10:00+01:00")
        self.assertEqual(len(self.calls), 2)
        self.assertNotEqual(first["job"]["period"], second["job"]["period"])
        self.assertEqual(first["job"]["next_expected_run"], "2026-10-25T02:00:00+01:00")

    def test_spring_madrid_clock_skips_nonexistent_local_hour(self):
        now = datetime.fromisoformat("2026-03-29T01:10:00+01:00")
        self.assertEqual(engine._ce_next_expected(TASK, now), "2026-03-29T03:00:00+02:00")

    def test_failed_attempt_does_not_retry_on_every_cron_tick(self):
        with patch.object(engine, "run_native_workforce_review", side_effect=RuntimeError("bounded synthetic failure"), create=True) as call:
            first = self.run_native("2026-10-29T11:10:00+01:00")
            again = self.run_native("2026-10-29T11:15:00+01:00")
            following = self.run_native("2026-10-29T12:00:00+01:00")
        self.assertFalse(first["ok"])
        self.assertEqual(first["result"], "PARTIAL")
        self.assertEqual(again["result"], "SKIPPED_NOT_DUE")
        self.assertFalse(following["ok"])
        self.assertEqual(call.call_count, 2)
        self.assertFalse((self.storage / "scheduler.lock").exists())

    def test_paused_scheduled_tick_never_evaluates_reviewers(self):
        engine.set_continuous_evolution_pause(self.root, paused=True, storage_root=self.storage,
                                             now="2026-10-29T11:00:00+01:00")
        with patch.object(engine, "run_native_workforce_review", side_effect=AssertionError("paused"), create=True):
            result = self.run_native("2026-10-29T11:10:00+01:00")
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "SKIPPED_PAUSED")
        self.assertFalse(list((self.storage / "job_logs").glob("JOB-*.json")))

    def test_production_force_cannot_bypass_hourly_dedupe(self):
        with patch.object(engine, "run_native_workforce_review", side_effect=AssertionError("forced"), create=True):
            result = self.run_native("2026-10-29T11:10:00+01:00", force=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["result"], "FORCE_NOT_ALLOWED_IN_PRODUCTION")
        self.assertFalse(self.storage.exists())

    def test_losing_caller_does_not_overwrite_active_owner_state(self):
        entered, finish = threading.Event(), threading.Event()
        results = []
        def slow(*args, **kwargs):
            entered.set()
            if not finish.wait(5):
                raise AssertionError("test owner was not released")
            return self.native(*args, **kwargs)
        with patch.object(engine, "run_native_workforce_review", slow, create=True):
            owner = threading.Thread(target=lambda: results.append(self.run_native("2026-10-29T11:10:00+01:00")))
            owner.start()
            try:
                self.assertTrue(entered.wait(5))
                before = (self.storage / "scheduler_state.json").read_bytes()
                loser = self.run_native("2026-10-29T11:10:00+01:00")
                self.assertEqual(loser["result"], "SKIPPED_ALREADY_RUNNING")
                self.assertEqual(before, (self.storage / "scheduler_state.json").read_bytes())
                self.assertFalse(list((self.storage / "job_logs").glob("JOB-*.json")))
            finally:
                finish.set()
                owner.join(5)
        self.assertFalse(owner.is_alive())
        self.assertEqual(results[0]["result"], "PASS")
        self.assertEqual(self.state()["tasks"][TASK]["run_count"], 1)

    def test_due_is_rechecked_after_acquiring_lock(self):
        waiting, release = threading.Event(), threading.Event()
        acquire = engine._ce_acquire_lock
        delayed_results = []
        def delayed_acquire(*args):
            if threading.current_thread().name == "delayed-review":
                waiting.set()
                if not release.wait(5):
                    raise AssertionError("delayed lock was not released")
            return acquire(*args)
        with patch.object(engine, "_ce_acquire_lock", delayed_acquire), \
             patch.object(engine, "run_native_workforce_review", self.native, create=True):
            delayed = threading.Thread(name="delayed-review", target=lambda: delayed_results.append(self.run_native("2026-10-29T11:10:00+01:00")))
            delayed.start()
            try:
                self.assertTrue(waiting.wait(5))
                winner = self.run_native("2026-10-29T11:10:00+01:00")
                self.assertEqual(winner["result"], "PASS")
            finally:
                release.set()
                delayed.join(5)
        self.assertFalse(delayed.is_alive())
        self.assertEqual(delayed_results[0]["result"], "SKIPPED_NOT_DUE")
        self.assertEqual(len(self.calls), 1)

    def test_stale_lock_is_reported_without_deleting_unknown_owner(self):
        self.storage.mkdir(parents=True)
        lock = self.storage / "scheduler.lock"
        original = b'{"job_id":"OTHER","locked_at_madrid":"2026-10-29T08:00:00+01:00"}'
        lock.write_bytes(original)
        with patch.object(engine, "run_native_workforce_review", side_effect=AssertionError("stale"), create=True):
            result = self.run_native("2026-10-29T11:10:00+01:00")
        self.assertEqual(result["result"], "STALE_LOCK")
        self.assertFalse(result["ok"])
        self.assertEqual(lock.read_bytes(), original)
        self.assertFalse((self.storage / "scheduler_state.json").exists())

    def test_malformed_lock_is_unverified_not_claimed_as_active(self):
        self.storage.mkdir(parents=True)
        lock = self.storage / "scheduler.lock"
        lock.write_bytes(b'{"job_id":"OTHER"}')
        result = self.run_native("2026-10-29T11:10:00+01:00")
        self.assertFalse(result["ok"])
        self.assertEqual(result["result"], "LOCK_UNVERIFIED")
        self.assertEqual(lock.read_bytes(), b'{"job_id":"OTHER"}')

    def test_releasing_another_jobs_lock_is_impossible(self):
        self.storage.mkdir(parents=True)
        paths = engine._ce_paths(self.storage)
        paths["scheduler_lock"].write_text('{"job_id":"OWNER"}')
        engine._ce_release_lock(paths, "LOSER")
        self.assertTrue(paths["scheduler_lock"].exists())

    def test_daily_four_oclock_and_founder_brief_remain_unchanged(self):
        daily = {"ok": True, "run": {"run_id": "RUN-DAY", "duration_ms": 3},
                 "snapshot": {"snapshot_id": "SNAP-DAY", "result": "PASS", "founder_brief": {"brief_id": "BRIEF-DAY"}}}
        with patch.object(engine, "run_continuous_evolution_cycle", return_value=daily) as full, \
             patch.object(engine, "run_native_workforce_review", side_effect=AssertionError("daily reevaluated native"), create=True):
            before = engine.run_continuous_evolution_scheduler_task(self.root, "TEST", now="2026-10-29T03:55:00+01:00", storage_root=self.storage)
            due = engine.run_continuous_evolution_scheduler_task(self.root, "TEST", now="2026-10-29T04:00:00+01:00", storage_root=self.storage)
        self.assertEqual(before["result"], "SKIPPED_NOT_DUE")
        self.assertEqual(due["result"], "PASS")
        self.assertEqual(full.call_count, 1)
        self.assertEqual(due["job"]["founder_brief_id"], "BRIEF-DAY")
        self.assertEqual(self.state()["tasks"]["daily_founder_brief"]["run_count"], 1)

    def test_child_dangerous_action_flag_is_propagated_to_endpoint_guard(self):
        def reported(*args, **kwargs):
            result = self.native(*args, **kwargs)
            result["run"]["dangerous_actions_executed"] = True
            return result
        with patch.object(engine, "run_native_workforce_review", reported, create=True):
            result = self.run_native("2026-10-29T11:10:00+01:00")
        self.assertFalse(result["ok"])
        self.assertTrue(result["dangerous_actions_executed"])
        self.assertTrue(result["job"]["dangerous_actions_executed"])

    def test_native_receipts_never_inflate_full_cycle_status(self):
        daily = {"task_name": "daily_product_review", "status": "PASS"}
        native = {"task_name": TASK, "status": "PASS"}
        cases = [
            ([daily, native], 1, 0),
            ([daily, {**native, "status": "PARTIAL"}], 1, 1),
            ([native], 0, 0),
        ]
        for jobs, daily_count, native_failures in cases:
            with self.subTest(jobs=jobs), \
                 patch.object(engine, "_ce_job_history", return_value=jobs), \
                 patch.object(engine, "_ce_latest_snapshot", return_value=None), \
                 patch.object(engine, "_ce_snapshot_history", return_value=[]), \
                 patch.object(engine, "load_product_memory", return_value={}), \
                 patch.object(engine, "load_sentinel_issues_memory", return_value={}, create=True), \
                 patch.object(engine, "build_sentinel_issues_summary", return_value={}, create=True), \
                 patch.object(engine, "build_market_intelligence_foundation_snapshot", return_value={}):
                status = engine.build_continuous_evolution_status_snapshot(
                    self.root, "TEST", storage_root=self.storage, now="2026-10-29T11:10:00+01:00",
                )
            self.assertEqual(status["cycles_completed"], daily_count)
            self.assertEqual(status["cycles_failed"], 0)
            self.assertEqual(status["native_review_runs_completed"], 1)
            self.assertEqual(status["native_review_runs_failed"], native_failures)
            self.assertEqual(status["status"], "PREPARED_ONLY")
            self.assertEqual(status["automation_status"], "ACTIVE")


class NativeWorkforceTransportTests(unittest.TestCase):
    class Response:
        status = 200
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _limit): return json.dumps(self.payload).encode()

    def test_administrative_pause_is_not_a_technical_cron_failure(self):
        with patch.object(master.urllib.request, "urlopen", return_value=self.Response({"ok": True, "result": "SKIPPED_PAUSED"})):
            result = master.continuous_evolution_tick("https://example.invalid", "test-secret")
        self.assertEqual(result["continuous_status"], "PASS")
        self.assertEqual(result["continuous_result"], "SKIPPED_PAUSED")

    def test_native_failure_is_not_masked_by_daily_not_due(self):
        payload = {"ok": False, "result": "PARTIAL", "daily_result": "SKIPPED_NOT_DUE",
                   "native_workforce": {"result": "PARTIAL", "review_kind": "STATIC_PARTIAL", "outcome": "UNKNOWN"}}
        with patch.object(master.urllib.request, "urlopen", return_value=self.Response(payload)):
            result = master.continuous_evolution_tick("https://example.invalid", "test-secret")
        self.assertEqual(result["continuous_status"], "FAIL")
        self.assertEqual(result["native_workforce"]["result"], "PARTIAL")

    def test_only_closed_native_receipt_fields_are_logged(self):
        secret = "synthetic-private-secret"
        raw = {"result": "PASS", "receipt_id": "NWR-0123456789abcdef", "run_id": "NWR-0123456789abcdef",
               "review_kind": "STATIC_PARTIAL", "outcome": "UNKNOWN", "executed_count": 22,
               "expected_count": 22, "duration_ms": 31, "next_expected_run": "2026-10-29T12:00:00+01:00",
               "evidence": secret, "proposals": [{"email": "person@example.invalid"}],
               "production_certified": True, "business_execution_certified": True}
        summary = master.compact_native_workforce(raw, secret)
        self.assertEqual(summary["executed_count"], 22)
        self.assertEqual(summary["outcome"], "UNKNOWN")
        self.assertEqual(summary["receipt_id"], raw["receipt_id"])
        self.assertFalse(summary["production_certified"])
        self.assertFalse(summary["business_execution_certified"])
        self.assertNotIn(secret, json.dumps(summary))
        self.assertNotIn("person@", json.dumps(summary))
        self.assertNotIn("proposals", summary)

    def test_malformed_native_metadata_cannot_inject_free_text(self):
        raw = {"result": ["PASS"], "receipt_id": "person@example.invalid", "run_id": "JOB-0123456789abcdef", "outcome": {"private": "value"},
               "executed_count": True, "expected_count": -1, "duration_ms": "token", "next_expected_run": "secret"}
        summary = master.compact_native_workforce(raw, "secret")
        self.assertEqual(summary["result"], "UNKNOWN")
        self.assertEqual(summary["outcome"], "UNKNOWN")
        for key in ("receipt_id", "run_id", "executed_count", "expected_count", "duration_ms", "next_expected_run"):
            self.assertIsNone(summary[key])


if __name__ == "__main__":
    unittest.main()
