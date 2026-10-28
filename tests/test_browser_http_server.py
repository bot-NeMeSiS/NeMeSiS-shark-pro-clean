"""In-memory ownership regression; no App import, sockets, accounts or database."""
import socketserver
import threading

import pytest
from werkzeug.serving import ThreadedWSGIServer

import browser_http_server


@pytest.mark.parametrize("body_fails", [False, True])
def test_fixture_drains_handler_before_restoring_database(monkeypatch, body_fails):
    started, release, finished = (threading.Event() for _ in range(3))
    close_entered, stopped, restored = (threading.Event() for _ in range(3))
    state = {"database": "owned-fixture"}
    observations, errors = [], []

    class MemoryBase:
        def server_close(self):
            close_entered.set()

    class MemoryServer(socketserver.ThreadingMixIn, MemoryBase):
        # Reuse the real server's default, including its daemon-thread trap.
        # ThreadingMixIn still creates and joins real threads in this test.
        daemon_threads = ThreadedWSGIServer.daemon_threads

        def serve_forever(self):
            if not stopped.wait(5):
                errors.append("acceptor did not stop")

        def shutdown(self):
            stopped.set()

        def finish_request(self, request, client_address):
            observations.append(state["database"])
            started.set()
            if not release.wait(5):
                raise RuntimeError("handler was not released")
            observations.append(state["database"])

        def shutdown_request(self, request):
            finished.set()

        def handle_error(self, request, client_address):
            errors.append("handler failed")

    server = MemoryServer()
    monkeypatch.setattr(browser_http_server, "make_server", lambda *args, **kwargs: server)

    class BodyFailure(Exception):
        pass

    def use_fixture():
        try:
            try:
                with browser_http_server.owned_http_server(object()) as owned:
                    owned.process_request(None, ("127.0.0.1", 0))
                    if not started.wait(5):
                        raise RuntimeError("handler did not start")
                    if body_fails:
                        raise BodyFailure()
            except BodyFailure:
                pass
            # Models the shared App DB_PATH restoration after the fixture's
            # context exits, rather than asserting a configuration flag.
            state["database"] = "next-fixture"
            restored.set()
        except Exception as exc:
            errors.append(type(exc).__name__)

    fixture_thread = threading.Thread(target=use_fixture, daemon=True)
    fixture_thread.start()
    try:
        assert close_entered.wait(5), "fixture never reached server_close"
        restored_with_pending_handler = restored.wait(0.1)
    finally:
        release.set()
        stopped.set()
        fixture_thread.join(timeout=5)
        assert finished.wait(5), "handler did not finish"

    assert not fixture_thread.is_alive()
    assert not errors, errors
    assert not restored_with_pending_handler, "fixture restored state while its handler was still running"
    assert observations == ["owned-fixture", "owned-fixture"]
    assert state["database"] == "next-fixture"
