"""Closed restore receipts plus native owned snapshot restores, never live data."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sqlite3
import time
import pytest
from tests.test_recovery_sqlite_set_manifest import _receipt as set_receipt, native
from tests.test_recovery_sqlite_set_state_handoff import complete_plan
from tools.recovery_sqlite_set_state import BoundSqliteSetStateBundle, capture_set_with_state
from tools import recovery_sqlite_set_restore as restore


def bundle(tmp_path):
    plan = complete_plan(tmp_path)
    return BoundSqliteSetStateBundle(plan, plan.state.publication / ('state-'+'3'*32+'.tar'),
                                    'a'*64, 'b'*64, set_receipt())


def receipt(bound, deadline):
    member=bound.sqlite.members[0]
    return {"schema":"G3_RESTORE_MEMBER_RECEIPT_V1", "ok":True,
        "operation_id":bound.plan.sqlite.operation_id,"proposal_sha256":bound.plan.sqlite.proposal_sha256,
        "capture_id":member.capture_id,"source_id":member.source_id,"deadline":deadline,
        "maximum_bytes":member.maximum_bytes,"size_bytes":member.size_bytes,"sha256":member.sha256,
        "worker_pid":1234,"source_identity":[1]*9,"destination_identity":[2]*9,
        "integrity_attested_before_sql":True,"integrity_check_ok":True,
        "sealed_snapshot_copy_calls":1,"live_source_capture_calls":0}


def test_closed_receipt_requires_same_member_and_worker(tmp_path):
    bound=bundle(tmp_path)
    restore._receipt(receipt(bound, 100),bound,bound.sqlite.members[0],100,
                     destination_identity=(2,)*9,pid=1234,source_identity=(1,)*9)


@pytest.mark.parametrize('field,bad',[
    ('operation_id','FOREIGN'),('proposal_sha256','c'*64),('capture_id','9'*32),
    ('source_id','aux_app'),('deadline',101),('maximum_bytes',True),('size_bytes',1),
    ('sha256','f'*64),('worker_pid',4321),('source_identity',[3]*9),
    ('destination_identity',[4]*9),('integrity_attested_before_sql',1),
    ('integrity_check_ok',False),('sealed_snapshot_copy_calls',True),('live_source_capture_calls',1),
    ('schema','G3_CAPTURE_WORKER_RECEIPT_V2')])
def test_replayed_or_weakened_restore_receipt_rejected(tmp_path, field, bad):
    bound=bundle(tmp_path)
    value=receipt(bound,100)
    value[field]=bad
    with pytest.raises(restore.SqliteSetRestoreError,match='NATIVE_RESTORE_MEMBER_NOT_VERIFIED'):
        restore._receipt(value,bound,bound.sqlite.members[0],100,
                         destination_identity=(2,)*9,pid=1234,source_identity=(1,)*9)


def test_changing_B_deadline_denied_before_io(tmp_path):
    bound=bundle(tmp_path)
    restored=restore.RestoredSet(bound,tmp_path/'MUST_NOT_OPEN',(),100,())
    with pytest.raises(restore.SqliteSetRestoreError,match='RESTORE_SET_DEADLINE_CHANGED'):
        restored.verify_before_app(101)


@native
def test_native_all_members_restored_from_same_sealed_snapshots(tmp_path):
    plan=complete_plan(tmp_path)
    captured=capture_set_with_state(plan=plan,deadline=time.monotonic()+30)
    assert captured.ok is True, captured.state_result
    before=tuple(s.source.read_bytes() for s in plan.sqlite.sources)
    workspace=tmp_path/'.isolated_restore_327_owned_set'
    workspace.mkdir(mode=0o700)
    workspace.chmod(0o700)
    deadline=time.monotonic()+30
    with restore.restore_all_members(bundle=captured.bundle,workspace=workspace,deadline=deadline) as restored:
        assert len(restored.members)==2
        restored.verify_before_app(deadline)
        for member, expected in zip(restored.members,captured.bundle.sqlite.members):
            assert member.worker_receipt['deadline']==deadline
            assert (workspace/member.relative).read_bytes()==(plan.sqlite.publication/expected.backup_file).read_bytes()
            with sqlite3.connect('file:'+str(workspace/member.relative)+'?mode=ro',uri=True) as db:
                assert db.execute('SELECT source_id FROM owned_rows').fetchall()==[(expected.source_id,)]
            assert member.worker_receipt['live_source_capture_calls']==0
        restored.verify_before_app(deadline)
    assert tuple(s.source.read_bytes() for s in plan.sqlite.sources)==before
    assert (workspace/'restoration-test.db').exists(), 'helper never deletes scratch'


@native
def test_native_auxiliary_tamper_preserves_principal_and_never_yields(tmp_path):
    plan=complete_plan(tmp_path)
    captured=capture_set_with_state(plan=plan,deadline=time.monotonic()+30)
    assert captured.ok is True, captured.state_result
    aux=plan.sqlite.publication/captured.bundle.sqlite.members[1].backup_file
    with aux.open('r+b') as stream:
        stream.seek(-1,2)
        stream.write(b'X')
    workspace=tmp_path/'.isolated_restore_327_owned_failure'
    workspace.mkdir(mode=0o700)
    workspace.chmod(0o700)
    yielded=False
    with pytest.raises(ValueError):
        with restore.restore_all_members(bundle=captured.bundle,workspace=workspace,
                                         deadline=time.monotonic()+30):
            yielded=True
    assert yielded is False
    assert (workspace/'restoration-test.db').exists()
    assert aux.exists(), 'no recapture or cleanup'

@native
@pytest.mark.parametrize('tamper_auxiliary', [False, True])
def test_native_state_restoration_requires_unchanged_complete_set(tmp_path, monkeypatch, tamper_auxiliary):
    from engines import recovery_non_sqlite_state as state
    plan=complete_plan(tmp_path)
    captured=capture_set_with_state(plan=plan,deadline=time.monotonic()+30)
    assert captured.ok is True, captured.state_result
    workspace=tmp_path/'.isolated_restore_327_state_set'
    workspace.mkdir(mode=0o700)
    workspace.chmod(0o700)
    (workspace/'source').mkdir(mode=0o700)
    deadline=time.monotonic()+30
    with restore.restore_all_members(bundle=captured.bundle,workspace=workspace,deadline=deadline) as restored:
        if tamper_auxiliary:
            original=state._scan
            def changed_after_state(*args,**kwargs):
                result=original(*args,**kwargs)
                with (workspace/'sqlite/aux_app.db').open('r+b') as stream:
                    stream.seek(-1,2)
                    stream.write(b'X')
                return result
            monkeypatch.setattr(state,'_scan',changed_after_state)
        result=state.restore_state(bundle=captured.bundle.archive,
            expected_archive_sha256=captured.bundle.archive_sha256,
            expected_manifest_sha256=captured.bundle.manifest_sha256,
            expected_sqlite=captured.bundle.sqlite,workspace=workspace,
            expected_database_identity=state._identity((workspace/'restoration-test.db').stat()),
            deadline=deadline,limits=plan.state.limits,expected_layout_id=plan.state.layout_id,
            expected_proposal_sha256=plan.state.proposal_sha256,
            expected_scope_roles=('ce','legacy_runtime'),restored_sqlite_set=restored)
        assert result['ok'] is (not tamper_auxiliary), result
        assert result['state_ready_before_app'] is (not tamper_auxiliary)
        assert result['full_application_recovery_certified'] is False
        if not tamper_auxiliary:
            assert (workspace/'source/data/continuous_evolution_os/product_memory.json').read_bytes()==(plan.state.scopes[0].source/'product_memory.json').read_bytes()


def test_failed_handle_close_does_not_skip_other_owned_handles(monkeypatch):
    closed=[]
    def close(fd):
        closed.append(fd)
        if fd==10:
            raise OSError('PRIVATE')
    monkeypatch.setattr(restore.os,'close',close)
    with pytest.raises(restore.SqliteSetRestoreError,match='^RESTORE_SET_CLOSE_NOT_VERIFIED$'):
        restore._close_fds((10,None,11,12))
    assert closed==[10,11,12]


def test_set_app_probe_denies_missing_native_bindings_before_clone_or_app(tmp_path, monkeypatch):
    from tools import recovery_app_probe as probe
    bound=bundle(tmp_path)
    workspace=tmp_path/'.isolated_restore_327_probe_admission'
    workspace.mkdir()
    main=workspace/'restoration-test.db'
    with sqlite3.connect(main) as db:
        db.execute('CREATE TABLE owned (value TEXT)')
    called=[]
    def forbidden(*args,**kwargs):
        called.append(True)
        raise AssertionError('MUST_NOT_CLONE_OR_LAUNCH')
    monkeypatch.setattr(probe,'prepare_source',forbidden)
    monkeypatch.setattr(probe.subprocess,'Popen',forbidden)
    result=probe.run_app_probe(project_root=Path(__file__).resolve().parents[1],
        restored_database=main,workspace=workspace,deadline=time.monotonic()+20,state_bundle=bound)
    assert result['ok'] is False
    assert result['code']=='COMPLETE_SQLITE_SET_RESTORE_REQUIRED'
    assert not called
    assert result['full_application_recovery_certified'] is False

@pytest.mark.parametrize('kind',['source','opaque','publication'])
def test_direct_restore_cannot_overlap_protected_live_scope(tmp_path,kind):
    bound=bundle(tmp_path)
    root={'source':bound.plan.sqlite.sources[1].source,
          'opaque':bound.plan.state.scopes[0].source,
          'publication':bound.plan.sqlite.publication}[kind]
    with pytest.raises(restore.SqliteSetRestoreError,match='RESTORE_SET_WORKSPACE_OVERLAP'):
        with restore.restore_all_members(bundle=bound,workspace=root,deadline=time.monotonic()+20):
            pytest.fail('MUST_NOT_RESTORE')


def test_app_binding_keeps_each_member_instead_of_fictitious_single_digest(tmp_path):
    from tools import recovery_app_probe as probe
    from engines.recovery_sqlite_set_contract import to_record
    bound=bundle(tmp_path)
    result=probe._state_sqlite_consumption_binding(bound)
    assert result['sqlite_set']==to_record(bound.sqlite)
    assert len(result['sqlite_set']['members'])==2
    assert 'backup_name' not in result
    assert 'sqlite_sha256' not in result
    assert result['auxiliary_sqlite_consumers_verified'] is False
