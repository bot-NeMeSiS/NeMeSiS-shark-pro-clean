"""Authentic-checkout native complete-set -> state -> stock App integration.

Owned fixtures only. Success proves this bounded guest flow, not production
layout, private custody, auxiliary consumers or continuous coherence.
"""
from pathlib import Path
import hashlib
import json
import time

import pytest
from tests.test_recovery_sqlite_set_manifest import native
from tests.test_recovery_sqlite_set_state_handoff import complete_plan
from tools import recovery_sqlite_set_operator as operator
from tools import recovery_app_probe as probe

ROOT = Path(__file__).resolve().parents[1]


def _fixture(tmp_path):
    plan=complete_plan(tmp_path)
    ce,runtime=(s.source for s in plan.state.scopes)
    (ce/'product_memory.json').write_text(json.dumps({
        'recommendations':{'owned-set-recommendation':{'title':'Owned set fixture','status':'OBSERVED'}},
        'events':[],'snapshots':[]}),encoding='utf-8')
    (ce/'sentinel_issues_memory.json').write_text(json.dumps({'issues':[
        {'id':'OWNED-SET-CE','title':'Owned CE issue','status':'OPEN_REAL','severity':'low'}],
        'events':[]}),encoding='utf-8')
    (runtime/'sentinel_autopilot_memory.json').write_text(json.dumps({'issues':[
        {'id':'OWNED-SET-AUTO','title':'Owned autopilot issue','status':'OPEN_REAL','severity':'low'}]}),encoding='utf-8')
    workspace_root=tmp_path/'admitted_restore_root'
    workspace_root.mkdir(mode=0o700)
    workspace_root.chmod(0o700)
    originals={s.source:s.source.read_bytes() for s in plan.sqlite.sources}
    originals.update({p:p.read_bytes() for scope in plan.state.scopes for p in scope.source.iterdir()})
    return plan,workspace_root,originals


@native
def test_complete_set_operator_reaches_stock_app_on_same_native_restore(tmp_path,monkeypatch):
    plan,workspace_root,originals=_fixture(tmp_path)
    real=probe.run_app_probe
    observations=[]
    def observe_actual_app(**kwargs):
        restored=kwargs['restored_sqlite_set']
        deadline=kwargs['deadline']
        restored.verify_before_app(deadline)
        assert len(restored.members)==2
        assert kwargs['state_bundle'] is restored.bundle
        assert kwargs['workspace']==restored.workspace
        assert kwargs['restored_database']==restored.workspace/'restoration-test.db'
        assert all(m.worker_receipt['deadline']==deadline for m in restored.members)
        assert all(m.worker_receipt['integrity_check_ok'] is True for m in restored.members)
        observations.append((restored.workspace,deadline))
        return real(**kwargs)
    monkeypatch.setattr(probe,'run_app_probe',observe_actual_app)
    result=operator.run_set_operation(plan=plan,source=plan.sqlite.sources[0].source,
        directory=plan.sqlite.publication,restore_root=workspace_root,timeout=60,
        app_probe_mode='normal_boot',project_root=ROOT,execute=True)
    assert result['ok'] is True, json.dumps(result)
    assert result['code']=='SET_STATE_AND_GUEST_APP_SMOKE_VERIFIED'
    assert len(observations)==1
    app=result['app_probe']
    assert app['child_exit']==0 and app['child']['ok'] is True
    assert app['child']['initialized'] is True
    assert app['child']['boundary_denials']==[]
    assert all(row['ok'] and row['completed_read_fetches']>0 for row in app['child']['routes'])
    assert app['state_restore']['state_ready_before_app'] is True
    assert app['canonical_consumer_consumption_verified'] is True
    assert app['child']['restored_state_consumption']['same_deadline'] is True
    assert app['sqlite_set_members_verified_before_app']==2
    binding=app['state_consumption_binding']
    assert binding['verified'] is True
    assert [m['source_id'] for m in binding['sqlite_set']['members']]==['principal','aux_app']
    assert 'sqlite_sha256' not in binding and 'backup_name' not in binding
    assert binding['auxiliary_sqlite_consumers_verified'] is False
    assert result['full_application_recovery_certified'] is False
    assert result['continuous_cross_store_consistency_certified'] is False
    assert result['restore_workspace']['cleanup_verified'] is True
    assert not observations[0][0].exists()
    assert all(path.read_bytes()==before for path,before in originals.items())
    assert len(list(plan.sqlite.publication.glob('database_*.db')))==2
    assert len(list(plan.state.publication.glob('state-*.tar')))==1


@native
def test_auxiliary_changed_after_clone_is_denied_before_app_launch(tmp_path,monkeypatch):
    plan,workspace_root,originals=_fixture(tmp_path)
    real_prepare=probe.prepare_source
    changes=[]
    def prepare_then_change(project_root,workspace,*,deadline):
        result=real_prepare(project_root,workspace,deadline=deadline)
        auxiliary=workspace/'sqlite/aux_app.db'
        with auxiliary.open('r+b') as stream:
            stream.seek(-1,2)
            stream.write(b'X')
        changes.append(workspace)
        return result
    monkeypatch.setattr(probe,'prepare_source',prepare_then_change)
    def must_not_reach_child_gate(*args,**kwargs):
        pytest.fail('Changed auxiliary reached child launch preflight')
    monkeypatch.setattr(probe,'_render_memory_gate',must_not_reach_child_gate)
    result=operator.run_set_operation(plan=plan,source=plan.sqlite.sources[0].source,
        directory=plan.sqlite.publication,restore_root=workspace_root,timeout=60,
        app_probe_mode='normal_boot',project_root=ROOT,execute=True)
    assert result['ok'] is False
    assert result['code']=='COMPLETE_SET_RESTORED_APP_NOT_VERIFIED'
    assert result['app_probe']['code']=='STATE_NOT_READY_BEFORE_APP'
    assert 'child_exit' not in result['app_probe']
    assert len(changes)==1
    assert result['restore_workspace']['cleanup_verified'] is True
    assert all(path.read_bytes()==before for path,before in originals.items())
    assert len(list(plan.sqlite.publication.glob('database_*.db')))==2
