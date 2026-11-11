"""Trusted-code-only complete set operator; never selected by App/Cron/CLI.

A typed plan is not a human data authorization. Real-data invocation remains a
separate decision. One A and one B budget; same restore is passed to the App.
"""
import math
import time
from pathlib import Path
from engines import recovery_non_sqlite_state as state
from tools.recovery_sqlite_set_state import StateSqliteSetPlan, capture_set_with_state, public_set_disposition
from tools.recovery_sqlite_set_restore import restore_all_members
from tools.recovery_workspace import admit_restore_root, recheck_restore_root, restore_workspace, workspace_capacity_preflight


class SetOperatorError(ValueError):
    """Closed admission codes."""


def validate_set_invocation(*, plan, source, directory, restore_root, timeout, app_probe_mode,
                            verify_existing=None):
    if type(plan) is not StateSqliteSetPlan:
        raise SetOperatorError('TYPED_COMPLETE_SET_PLAN_REQUIRED')
    StateSqliteSetPlan.__post_init__(plan)
    if (verify_existing is not None or app_probe_mode not in ('read_only','normal_boot')
            or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0 < timeout <= 300
            or source != plan.sqlite.sources[0].source or directory != plan.sqlite.publication
            or not isinstance(restore_root,Path)):
        raise SetOperatorError('SQLITE_SET_OPERATOR_NOT_ADMITTED')
    state._path(restore_root)
    protected = (directory, plan.state.publication,
                 *(s.source for s in plan.sqlite.sources), *(s.source for s in plan.state.scopes))
    for path in protected:
        if restore_root == path or restore_root.is_relative_to(path) or path.is_relative_to(restore_root):
            raise SetOperatorError('SQLITE_SET_WORKSPACE_OVERLAP')
    return protected


def run_set_operation(*, plan, source, directory, restore_root, timeout, app_probe_mode,
                      project_root, execute=False, verify_existing=None):
    """A complete set flow; partial captures are preserved, never retried."""
    report={'schema':'OWNED_SQLITE_SET_OPERATOR_V1','ok':False,'stage':'PREFLIGHT',
            'execute_requested':execute is True,'backup_created':False,
            'full_application_recovery_certified':False,
            'continuous_cross_store_consistency_certified':False,
            'auxiliary_sqlite_consumers_verified':False}
    handoff=None
    try:
        if type(execute) is not bool:
            raise SetOperatorError('SQLITE_SET_OPERATOR_NOT_ADMITTED')
        protected=validate_set_invocation(plan=plan,source=source,directory=directory,
            restore_root=restore_root,timeout=timeout,app_probe_mode=app_probe_mode,
            verify_existing=verify_existing)
        state._path(project_root)
        # One aggregate A starts here, including admission and capacity checks.
        capture_deadline=time.monotonic()+timeout
        identity=admit_restore_root(restore_root,protected_paths=protected)
        policy=state._policy(None,plan.state.limits)
        capacity=workspace_capacity_preflight(source=source,directory=directory,restore_root=restore_root,
            snapshot_bytes=sum(s.maximum_bytes for s in plan.sqlite.sources),
            app_probe_mode=app_probe_mode,expected_identity=identity,
            state_archive_bytes=policy.archive_bytes,restored_state_bytes=policy.bytes)
        report['capacity']=capacity
        state._check_time(capture_deadline)
        if capacity.get('ok') is not True or not execute:
            report.update(ok=capacity.get('ok') is True,code=capacity.get('code'))
            return report
        recheck_restore_root(identity,protected_paths=protected)
        from engines.data_vault_engine import backup_directory_lock
        with backup_directory_lock(directory):
            state._check_time(capture_deadline)
            report['stage']='SET_CAPTURE'
            # No unverified assertion of no attempt survives an interrupted call.
            report['backup_created']=None
            handoff=capture_set_with_state(plan=plan,deadline=capture_deadline)
            report['capture']=public_set_disposition(handoff)
            report['backup_created']=report['capture']['published_sqlite_members']>0
            if not handoff.ok:
                report['code']='COMPLETE_SET_CAPTURE_NOT_VERIFIED'
                return report
            # Exactly one B deadline for every restore, state, clone, App and cleanup.
            deadline=time.monotonic()+timeout
            def check_time():
                state._check_time(deadline)
                recheck_restore_root(identity,protected_paths=protected)
            check_time()
            observation={}
            report['restore_workspace']=observation
            report['stage']='RESTORE_COMPLETE_SET'
            with restore_workspace(directory,identity=identity,check_time=check_time,
                                   observation=observation) as workspace:
                with restore_all_members(bundle=handoff.bundle,workspace=workspace,deadline=deadline) as restored:
                    check_time()
                    report['sqlite_members_restored']=len(restored.members)
                    report['stage']='SAME_RESTORE_APP_PROBE'
                    from tools.recovery_app_probe import run_app_probe
                    app=run_app_probe(project_root=project_root,restored_database=workspace/'restoration-test.db',
                        workspace=workspace,deadline=deadline,mode=app_probe_mode,
                        state_bundle=handoff.bundle,restored_sqlite_set=restored)
                    report['app_probe']=app
                    if app.get('ok') is not True:
                        report['code']='COMPLETE_SET_RESTORED_APP_NOT_VERIFIED'
                        return report
            check_time()
            report.update(ok=True,stage='COMPLETE',code='SET_STATE_AND_GUEST_APP_SMOKE_VERIFIED')
            return report
    except Exception:
        report.update(ok=False,code='COMPLETE_SET_OPERATION_NOT_VERIFIED')
        if handoff is not None:
            report['capture']=public_set_disposition(handoff)
        return report
