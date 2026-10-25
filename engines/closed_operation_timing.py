"""Request-local timing only: no payloads, identifiers, SQL or exception text."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
import secrets
import sqlite3
import time

PHASES = {
    'media_request': frozenset({'operation', 'receipt'}),
    'media': frozenset({'operation', 'ledger_start_connect', 'ledger_start_write',
        'ledger_start_commit', 'profile_cache', 'v2_candidates', 'reserve_call',
        'recent_reserve', 'historical_job', 'ledger_finalize_connect',
        'ledger_finalize_write', 'ledger_finalize_commit'}),
    'postmatch_discover': frozenset({'operation', 'connect', 'begin', 'read',
        'inventory', 'enqueue', 'commit', 'rollback'}),
}
_ACTIVE = ContextVar('closed_operation_timing', default=())
_CODES = {5:'SQLITE_BUSY', 6:'SQLITE_LOCKED', 9:'SQLITE_INTERRUPT', 10:'SQLITE_IOERR',
          11:'SQLITE_CORRUPT', 13:'SQLITE_FULL', 19:'SQLITE_CONSTRAINT'}


def trace_id(domain):
    return next((item[1] for item in reversed(_ACTIVE.get()) if item[0] == domain), None)


def _flush(state):
    pending = state[3][:]
    state[3].clear()
    for index, record in enumerate(pending):
        try:
            record['dropped_records'] = state[5]
            print(json.dumps(record), flush=True)
        except Exception:
            state[5] += len(pending) - index
            break


def _emit(domain, label, point, elapsed, conn, error):
    active = _ACTIVE.get()
    identifier = trace_id(domain)
    if identifier is None or label not in PHASES.get(domain, ()):
        return
    state = next(item for item in reversed(active) if item[1] == identifier)
    try:
        code = None
        if error is not None:
            raw = getattr(error, 'sqlite_errorcode', None)
            code = (_CODES.get(raw & 255, 'SQLITE_OTHER') if type(raw) is int
                    else 'SQLITE_OTHER' if isinstance(error, sqlite3.Error) else 'ERROR')
        try:
            transaction = bool(conn.in_transaction) if isinstance(conn, sqlite3.Connection) else None
        except sqlite3.Error:
            transaction = None
        record = {'event':'operational_phase', 'domain':domain, 'trace':identifier,
            'parent':state[2], 'phase':label, 'point':point, 'duration_ms':elapsed,
            'offset_ms':max(0, round((time.monotonic()-state[4])*1000)),
            'in_transaction':transaction, 'error':code, 'dropped_records':state[5]}
        # Do not add stdout backpressure while this observed connection owns
        # its transaction. Offsets retain capture timing when emission is deferred.
        if transaction is not True:
            _flush(state)
            state[3].append(record)
            _flush(state)
        elif len(state[3]) < 64:
            state[3].append(record)
        else:
            state[5] += 1
    except Exception:
        pass  # Observation must not discard a completed result or replace its error.


@contextmanager
def phase(domain, label, conn=None):
    if trace_id(domain) is None or label not in PHASES.get(domain, ()):
        yield
        return
    began = time.monotonic()
    _emit(domain, label, 'begin', None, conn, None)
    error = None
    try:
        yield
    except BaseException as exc:
        error = exc
        raise
    finally:
        _emit(domain, label, 'end', max(0, round((time.monotonic()-began)*1000)), conn, error)


def operation(domain):
    if domain not in PHASES:
        raise ValueError('Unknown operational timing domain')
    def decorate(function):
        @wraps(function)
        def observed(*args, **kwargs):
            active = _ACTIVE.get()
            state = [domain, secrets.token_hex(8), active[-1][1] if active else None,
                     [], time.monotonic(), 0]
            token = _ACTIVE.set(active + (state,))
            try:
                with phase(domain, 'operation'):
                    return function(*args, **kwargs)
            finally:
                _flush(state)
                _ACTIVE.reset(token)
        return observed
    return decorate
