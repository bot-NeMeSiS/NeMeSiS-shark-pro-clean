"""Complete operator admission/preflight, not data-operation permission."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from tests.test_recovery_sqlite_set_state_handoff import complete_plan
from tools import recovery_sqlite_set_operator as operator


def options(tmp_path):
    plan=complete_plan(tmp_path)
    return dict(plan=plan,source=plan.sqlite.sources[0].source,directory=plan.sqlite.publication,
                restore_root=tmp_path/'isolated_root',timeout=300,app_probe_mode='read_only')


@pytest.mark.parametrize('field,bad', [('timeout',301),('timeout',True),('timeout',0),
    ('timeout',float('inf')),('app_probe_mode',None),('verify_existing','database_old.db'),
    ('restore_root',None)])
def test_invalid_set_invocation_denied_before_any_io(tmp_path,field,bad):
    args=options(tmp_path)
    args[field]=bad
    with pytest.raises(operator.SetOperatorError):
        operator.validate_set_invocation(**args)


@pytest.mark.parametrize('kind',['auxiliary','opaque','publication'])
def test_workspace_cannot_cover_any_protected_member(tmp_path,kind):
    args=options(tmp_path)
    protected={'auxiliary':args['plan'].sqlite.sources[1].source,
               'opaque':args['plan'].state.scopes[0].source,
               'publication':args['plan'].sqlite.publication}[kind]
    args['restore_root']=protected
    with pytest.raises(operator.SetOperatorError,match='SQLITE_SET_WORKSPACE_OVERLAP'):
        operator.validate_set_invocation(**args)


def test_preflight_accounts_complete_quota_and_cannot_capture(tmp_path,monkeypatch):
    args=options(tmp_path)
    calls=[]
    monkeypatch.setattr(operator,'admit_restore_root',lambda *a,**k: object())
    def capacity(**kwargs):
        calls.append(kwargs)
        return {'ok':True,'code':'READY','capacity_reserved':False}
    monkeypatch.setattr(operator,'workspace_capacity_preflight',capacity)
    def forbidden(**kwargs):
        raise AssertionError('PREFLIGHT_MUST_NOT_CAPTURE_OR_RESTORE')
    monkeypatch.setattr(operator,'capture_set_with_state',forbidden)
    monkeypatch.setattr(operator,'restore_all_members',forbidden)
    result=operator.run_set_operation(**args,project_root=tmp_path,execute=False)
    assert result['ok'] is True
    assert result['stage']=='PREFLIGHT'
    assert result['backup_created'] is False
    assert result['full_application_recovery_certified'] is False
    assert len(calls)==1
    assert calls[0]['snapshot_bytes']==sum(s.maximum_bytes for s in args['plan'].sqlite.sources)
    assert calls[0]['restored_state_bytes']==args['plan'].state.limits.bytes


def test_cli_default_cannot_select_set_plan(tmp_path,monkeypatch):
    from tools import backup_operator_recovery_327 as legacy
    args=SimpleNamespace(db=str(tmp_path/'main.db'),backup_dir=str(tmp_path/'backups'),
                         verify_existing=None,execute=False,timeout=300,app_probe_mode='read_only',
                         restore_workspace_root=None)
    observed=[]
    monkeypatch.setattr(legacy,'emit',observed.append)
    monkeypatch.setattr(legacy,'preflight',lambda *a,**k:{'ok':False,'code':'OWNED_STOP_BEFORE_WRITE'})
    monkeypatch.setattr(operator,'run_set_operation',lambda **k:pytest.fail('NO_AUTO_SET_SELECTION'))
    assert legacy.run(args)==2
    assert observed[0]['code']=='OWNED_STOP_BEFORE_WRITE'


def test_unexpected_preflight_failure_preserves_closed_public_result(tmp_path,monkeypatch):
    args=options(tmp_path)
    def fail(*a,**k):
        raise RuntimeError('PRIVATE_MUST_NOT_ESCAPE')
    monkeypatch.setattr(operator,'admit_restore_root',fail)
    result=operator.run_set_operation(**args,project_root=tmp_path,execute=False)
    assert result['ok'] is False
    assert result['backup_created'] is False
    assert result['code']=='COMPLETE_SET_OPERATION_NOT_VERIFIED'
    assert 'PRIVATE_MUST_NOT_ESCAPE' not in repr(result)


def admit_synthetic_capture(tmp_path, monkeypatch, handoff):
    from contextlib import nullcontext
    from engines import data_vault_engine

    monkeypatch.setattr(operator, 'admit_restore_root', lambda *a, **k: object())
    monkeypatch.setattr(operator, 'recheck_restore_root', lambda *a, **k: None)
    monkeypatch.setattr(operator, 'workspace_capacity_preflight',
                        lambda **k: {'ok': True, 'code': 'READY'})
    monkeypatch.setattr(data_vault_engine, 'backup_directory_lock',
                        lambda *a, **k: nullcontext())
    monkeypatch.setattr(operator, 'capture_set_with_state', lambda **k: handoff)
    return options(tmp_path)


def test_invalid_capture_receipt_returns_closed_failure(tmp_path, monkeypatch):
    handoff = object()
    args = admit_synthetic_capture(tmp_path, monkeypatch, handoff)
    calls = []
    validate = operator.public_set_disposition

    def invalid_receipt(value):
        calls.append(value)
        return validate(value)

    monkeypatch.setattr(operator, 'public_set_disposition', invalid_receipt)
    monkeypatch.setattr(operator, 'restore_all_members',
                        lambda **k: pytest.fail('MUST_NOT_RESTORE'))
    result = operator.run_set_operation(**args, project_root=tmp_path, execute=True)

    assert result['ok'] is False
    assert result['backup_created'] is None
    assert result['stage'] == 'SET_CAPTURE'
    assert result['code'] == 'COMPLETE_SET_OPERATION_NOT_VERIFIED'
    assert result['full_application_recovery_certified'] is False
    assert 'capture' not in result
    assert calls == [handoff]


@pytest.mark.parametrize('failure_phase', ['handoff_status', 'restore_workspace'])
def test_later_failure_preserves_validated_capture_receipt(tmp_path, monkeypatch,
                                                          failure_phase):
    from contextlib import contextmanager

    class Handoff:
        @property
        def ok(self):
            if failure_phase == 'handoff_status':
                raise ValueError('PRIVATE_MUST_NOT_ESCAPE')
            return True

    handoff = Handoff()
    args = admit_synthetic_capture(tmp_path, monkeypatch, handoff)
    capture = {'published_sqlite_members': 2, 'set_verified': True}
    calls = []

    def receipt(value):
        calls.append(value)
        if len(calls) > 1:
            raise ValueError('PRIVATE_REVALIDATION_MUST_NOT_ESCAPE')
        return capture

    @contextmanager
    def unavailable_workspace(*a, **k):
        raise OSError('PRIVATE_MUST_NOT_ESCAPE')
        yield  # pragma: no cover

    monkeypatch.setattr(operator, 'public_set_disposition', receipt)
    monkeypatch.setattr(operator, 'restore_workspace', unavailable_workspace)
    monkeypatch.setattr(operator, 'restore_all_members',
                        lambda **k: pytest.fail('MUST_NOT_RESTORE'))
    result = operator.run_set_operation(**args, project_root=tmp_path, execute=True)

    assert result['ok'] is False
    assert result['backup_created'] is True
    assert result['capture'] is capture
    assert result['stage'] == ('SET_CAPTURE' if failure_phase == 'handoff_status'
                               else 'RESTORE_COMPLETE_SET')
    assert result['code'] == 'COMPLETE_SET_OPERATION_NOT_VERIFIED'
    assert result['full_application_recovery_certified'] is False
    assert calls == [handoff]
    assert 'PRIVATE' not in repr(result)


@pytest.mark.parametrize('published', [False, True])
def test_real_partial_capture_receipt_preserved_without_restore(tmp_path, monkeypatch,
                                                              published):
    from tools.recovery_sqlite_set_state import SqliteSetCaptureHandoff

    handoff = SqliteSetCaptureHandoff(
        sqlite_result={'members': tuple((name, {
            'ok': False, 'sqlite_capture_attempted': True,
            'prepare_completed': True, 'backup_created': published,
        }) for name in ('principal', 'aux_app'))},
        state_result={'ok': False, 'sqlite_callback_invoked': True},
        bundle=None,
    )
    expected = operator.public_set_disposition(handoff)
    args = admit_synthetic_capture(tmp_path, monkeypatch, handoff)
    monkeypatch.setattr(operator, 'restore_workspace',
                        lambda *a, **k: pytest.fail('MUST_NOT_RESTORE'))
    result = operator.run_set_operation(**args, project_root=tmp_path, execute=True)

    assert result['ok'] is False
    assert result['backup_created'] is published
    assert result['stage'] == 'SET_CAPTURE'
    assert result['code'] == 'COMPLETE_SET_CAPTURE_NOT_VERIFIED'
    assert result['capture'] == expected
    assert result['capture']['recapture_attempted'] is False
    assert result['full_application_recovery_certified'] is False
