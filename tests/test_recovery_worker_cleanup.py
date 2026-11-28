"""Owned process/channel cleanup, using fault-injected handles only."""
import os
import subprocess
from types import SimpleNamespace

import pytest

from tools.recovery_sqlite_prepare import _CaptureWorker, SqliteSnapshotProducer


def owned_worker(failures=(), *, exited=False, validator=True, handles=True):
    calls, errors = [], {}
    def action(name, result=None):
        def run(*args, **kwargs):
            calls.append(name)
            if name in failures:
                error = errors.setdefault(name, OSError("owned synthetic " + name))
                raise error
            return result
        return run
    process = SimpleNamespace(poll=action("poll", 0 if exited else None),
        kill=action("kill"), wait=action("wait"),
        stdin=SimpleNamespace(close=action("stdin")) if handles else None,
        stdout=SimpleNamespace(close=action("stdout")) if handles else None)
    worker = _CaptureWorker(process, {}, 100)
    if validator:
        worker.validation_worker = SimpleNamespace(close=action("validator"))
    return worker, calls, errors


@pytest.mark.parametrize("failure", ["validator", "poll", "kill", "wait", "stdin", "stdout"])
def test_each_failed_cleanup_still_attempts_remaining_owned_resources(failure):
    worker, calls, errors = owned_worker([failure])
    with pytest.raises(OSError) as caught:
        worker.close()
    assert calls == ["validator", "poll", "kill", "wait", "stdin", "stdout"]
    assert caught.value is errors[failure]


def test_multiple_failures_preserve_first_error_after_all_attempts():
    worker, calls, errors = owned_worker(["validator", "kill", "wait", "stdin", "stdout"])
    with pytest.raises(OSError) as caught:
        worker.close()
    assert calls == ["validator", "poll", "kill", "wait", "stdin", "stdout"]
    assert caught.value is errors["validator"]


def test_clean_worker_retains_existing_wait_bound_and_return_contract():
    worker, calls, _ = owned_worker()
    waits = []
    worker.process.wait = lambda **kw: (calls.append("wait"), waits.append(kw))
    assert worker.close() is None
    assert calls == ["validator", "poll", "kill", "wait", "stdin", "stdout"]
    assert waits == [{"timeout": 1.0}]


def test_exited_worker_is_not_killed_and_absent_resources_are_not_invented():
    worker, calls, _ = owned_worker(exited=True, validator=False, handles=False)
    assert worker.close() is None
    assert calls == ["poll", "wait"]


def test_actual_producer_records_failure_and_closes_its_descriptors(tmp_path):
    worker, calls, _ = owned_worker(["validator"])
    producer = SqliteSnapshotProducer.__new__(SqliteSnapshotProducer)
    producer._closed, producer._worker, producer._result = False, worker, {}
    descriptors = []
    try:
        for key in ("_fd", "_wfd", "_pfd"):
            path = tmp_path / key
            path.write_bytes(b"owned temporary handle, no real snapshot")
            fd = os.open(path, os.O_RDONLY)
            setattr(producer, key, fd)
            descriptors.append(fd)
        producer.close()
        assert calls == ["validator", "poll", "kill", "wait", "stdin", "stdout"]
        assert producer._result == {"owned_worker_cleanup_failed": True}
        assert producer._worker is None
        for fd in descriptors:
            with pytest.raises(OSError):
                os.fstat(fd)
        assert all(getattr(producer, key) is None for key in ("_fd", "_wfd", "_pfd"))
        producer.close()
        assert calls == ["validator", "poll", "kill", "wait", "stdin", "stdout"]
    finally:
        for fd in descriptors:
            try:
                os.close(fd)
            except OSError:
                pass


@pytest.mark.parametrize("error", [KeyboardInterrupt(), RuntimeError("synthetic cleanup"), subprocess.TimeoutExpired("owned worker", 1.0)])
def test_cleanup_does_not_turn_first_non_os_failure_into_success(error):
    worker, calls, _ = owned_worker()
    def fail():
        calls.append("validator")
        raise error
    worker.validation_worker.close = fail
    with pytest.raises(type(error)) as caught:
        worker.close()
    assert caught.value is error
    assert calls == ["validator", "poll", "kill", "wait", "stdin", "stdout"]


def test_real_nested_worker_ownership_closes_both_sets_after_validator_failure():
    parent, parent_calls, _ = owned_worker(validator=False)
    validator, validator_calls, errors = owned_worker(["stdin"], validator=False)
    parent.validation_worker = validator
    with pytest.raises(OSError) as caught:
        parent.close()
    expected = ["poll", "kill", "wait", "stdin", "stdout"]
    assert validator_calls == expected and parent_calls == expected
    assert caught.value is errors["stdin"]
