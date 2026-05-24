"""SQLite hardening helpers for NeMeSiS SHARK PRO.

Centraliza conexiones con timeout, WAL y retry corto para evitar
`sqlite3.OperationalError: database is locked` en Render cuando varios
engines arrancan a la vez.
"""

import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")

DEFAULT_TIMEOUT = int(os.getenv("SQLITE_TIMEOUT_SECONDS", "30"))
BUSY_TIMEOUT_MS = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "30000"))
RETRY_ATTEMPTS = int(os.getenv("SQLITE_RETRY_ATTEMPTS", "5"))
RETRY_BASE_SLEEP = float(os.getenv("SQLITE_RETRY_BASE_SLEEP", "0.15"))


def connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=DEFAULT_TIMEOUT, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.OperationalError:
        # Si otro proceso está cambiando PRAGMAs justo al arrancar,
        # mantenemos la conexión con timeout/busy_timeout y reintentamos
        # en la operación superior.
        pass
    return conn


@contextmanager
def connection(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def retry_locked(operation: Callable[[], T], attempts: int = RETRY_ATTEMPTS) -> T:
    last_exc: Exception | None = None
    for index in range(max(1, attempts)):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "database is locked" not in message and "database table is locked" not in message:
                raise
            last_exc = exc
            time.sleep(RETRY_BASE_SLEEP * (index + 1))
    assert last_exc is not None
    raise last_exc
