"""Own all HTTP handlers until disposable browser-fixture state can be restored."""
from contextlib import contextmanager
import threading

from werkzeug.serving import make_server


@contextmanager
def owned_http_server(application):
    server = make_server("127.0.0.1", 0, application, threaded=True)
    # Werkzeug's default daemon handlers are not joined by server_close(). A
    # pending handler must finish before fixtures restore the shared App's DB.
    server.daemon_threads = False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
