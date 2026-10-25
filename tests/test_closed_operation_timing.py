import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from engines.closed_operation_timing import PHASES, operation, phase, trace_id

KEYS = {'event','domain','trace','parent','phase','point','duration_ms','offset_ms',
        'in_transaction','error','dropped_records'}


def records(capsys):
    result = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    for row in result:
        assert set(row) == KEYS
        assert row['event'] == 'operational_phase'
        assert row['domain'] in PHASES and row['phase'] in PHASES[row['domain']]
        assert re.fullmatch('[0-9a-f]{16}', row['trace'])
        assert row['parent'] is None or re.fullmatch('[0-9a-f]{16}', row['parent'])
        assert row['point'] in {'begin','end'}
        assert type(row['offset_ms']) is int and row['offset_ms'] >= 0
        assert row['dropped_records'] == 0
        assert row['duration_ms'] is None if row['point']=='begin' else type(row['duration_ms']) is int
    return result


def test_nested_operations_correlate_without_payloads_and_reset(capsys):
    @operation('media')
    def child():
        with phase('media', 'profile_cache'):
            return object()
    @operation('media_request')
    def parent():
        return child()
    answer = parent()
    assert answer is not None and trace_id('media') is trace_id('media_request') is None
    rows = records(capsys)
    parent_ids = {r['trace'] for r in rows if r['domain']=='media_request'}
    child_rows = [r for r in rows if r['domain']=='media']
    assert len(rows)==6 and len(parent_ids)==1
    assert {r['parent'] for r in child_rows} == parent_ids
    assert len({r['trace'] for r in child_rows})==1
    assert all(r['in_transaction'] is None and r['error'] is None for r in rows)


def test_unknown_labels_and_inactive_scopes_never_emit_supplied_text(capsys):
    with phase('media','profile_cache'):
        pass
    @operation('media')
    def call():
        with phase('media','secret SQL / token / user@example.invalid'):
            return 42
    assert call()==42
    rows=records(capsys)
    assert len(rows)==2 and {r['phase'] for r in rows}=={'operation'}


def test_failure_keeps_original_exception_and_never_logs_its_message(capsys):
    problem=RuntimeError('SECRET_PAYLOAD https://provider.invalid/private-key')
    @operation('media')
    def call():
        with phase('media','v2_candidates'):
            raise problem
    with pytest.raises(RuntimeError) as caught:
        call()
    assert caught.value is problem
    text=capsys.readouterr().out
    assert 'SECRET_PAYLOAD' not in text and 'private-key' not in text
    rows=[json.loads(line) for line in text.splitlines()]
    assert [r['error'] for r in rows if r['point']=='end']==['ERROR','ERROR']
    assert trace_id('media') is None


def test_log_sink_failure_cannot_change_result_or_exception(monkeypatch):
    def broken(*args,**kwargs):raise OSError('sink unavailable')
    monkeypatch.setattr('builtins.print',broken)
    marker=object()
    @operation('media')
    def success():return marker
    assert success() is marker
    problem=ValueError('private business error')
    @operation('media')
    def failed():raise problem
    with pytest.raises(ValueError) as caught:failed()
    assert caught.value is problem and trace_id('media') is None


def test_concurrent_operations_keep_distinct_contexts(capsys):
    barrier=Barrier(2)
    @operation('media')
    def call():
        current=trace_id('media')
        with phase('media','v2_candidates'):
            barrier.wait(timeout=3)
            assert trace_id('media')==current
        return current
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(call);second=pool.submit(call)
        ids={first.result(timeout=5),second.result(timeout=5)}
    assert len(ids)==2 and trace_id('media') is None
    rows=records(capsys)
    assert {r['trace'] for r in rows}==ids and all(r['parent'] is None for r in rows)


def test_transaction_state_is_measured_not_inferred(tmp_path,capsys):
    conn=sqlite3.connect(tmp_path/'transaction.sqlite')
    conn.execute('CREATE TABLE sample(value)')
    @operation('media')
    def call():
        with phase('media','ledger_start_write',conn):
            conn.execute('INSERT INTO sample VALUES(1)')
        with phase('media','ledger_start_commit',conn):conn.commit()
    try:call()
    finally:conn.close()
    rows=records(capsys)
    ends={r['phase']:r for r in rows if r['point']=='end'}
    assert ends['ledger_start_write']['in_transaction'] is True
    assert ends['ledger_start_commit']['in_transaction'] is False


def test_trace_output_waits_until_observed_transaction_is_released(tmp_path,monkeypatch):
    conn=sqlite3.connect(tmp_path/'no-log-backpressure.sqlite')
    conn.execute('CREATE TABLE sample(value)')
    output=[];transaction_at_emission=[]
    def record(text,**kwargs):
        transaction_at_emission.append(conn.in_transaction)
        output.append(json.loads(text))
    monkeypatch.setattr('builtins.print',record)
    @operation('media')
    def call():
        with phase('media','ledger_start_write',conn):
            conn.execute('INSERT INTO sample VALUES(1)')
        with phase('media','ledger_start_commit',conn):
            conn.commit()
    try:call()
    finally:conn.close()
    assert any(r['in_transaction'] is True for r in output)
    assert not any(transaction_at_emission)
    assert all(r['dropped_records']==0 for r in output)
