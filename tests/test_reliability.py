"""SIMULATED_QA: deterministic incident memory, no transport or real storage."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import pytest
from engines import sentinel_issues_engine as ledger


@pytest.fixture
def memory(tmp_path, monkeypatch):
    monkeypatch.delenv('CONTINUOUS_EVOLUTION_SAFE_MODE', raising=False)
    monkeypatch.delenv('CONTINUOUS_EVOLUTION_STORAGE_ROOT', raising=False)
    issue = ledger.normalize_sentinel_issue({'title':'QA known failure', 'area':'sports', 'route':'/live',
        'stable_key':'qa-known-failure', 'evidence':'Confirmed reproducible QA failure condition',
        'severity':'high', 'last_seen':(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()})
    ledger.save_sentinel_issues_memory({'issues':[issue]}, tmp_path)
    return tmp_path, issue


def record():
    return dict(root_cause='QA confirmed cause', corrective_action='QA isolated correction', regression_test='tests/test_reliability.py',
        prevention='Fail closed guard', detection='Sentinel regression gate', fix_sha='a'*40,
        evidence_ref='SIMULATED_QA/report', checked_at=datetime.now(timezone.utc).isoformat(), result='PASS', scope='CI')


def test_close_without_verification_rejected(memory):
    root, issue = memory
    result = ledger.update_issue_status(issue['id'], 'RESOLVED', root)
    assert result['ok'] is False and result['error']=='verification_required'
    assert ledger.load_sentinel_issues_memory(root)['issues'][0]['status'] != 'RESOLVED'


def test_valid_proof_can_verify_then_resolve(memory):
    root, issue = memory
    assert ledger.record_issue_verification(issue['id'],record(),root)['ok']
    assert ledger.load_sentinel_issues_memory(root)['issues'][0]['status']=='VERIFIED'
    assert ledger.update_issue_status(issue['id'],'RESOLVED',root)['ok']
    assert ledger.load_sentinel_issues_memory(root)['issues'][0]['status']=='RESOLVED'


@pytest.mark.parametrize('mutation', ['missing_test','fail','old','future','wrong_sha','missing_ref','status_only'])
def test_incomplete_stale_or_failed_proof_cannot_close(memory, mutation):
    root, issue=memory; proof=record()
    if mutation=='missing_test': proof['regression_test']=''
    if mutation=='fail': proof['result']='FAIL'
    if mutation=='old': proof['checked_at']='2000-01-01T00:00:00Z'
    if mutation=='future': proof['checked_at']='2099-01-01T00:00:00Z'
    if mutation=='missing_ref': proof['evidence_ref']=''
    if mutation=='status_only':
        assert not ledger.update_issue_status(issue['id'],'VERIFIED',root)['ok']
    else:
        ledger.record_issue_verification(issue['id'],proof,root)
    if mutation=='wrong_sha':
        m=ledger.load_sentinel_issues_memory(root);m['issues'][0]['fix_sha']='b'*40;ledger.save_sentinel_issues_memory(m,root)
    assert not ledger.update_issue_status(issue['id'],'RESOLVED',root)['ok']


def test_recurrence_invalidates_old_verification(memory):
    root, issue=memory
    ledger.record_issue_verification(issue['id'],record(),root)
    ledger.update_issue_status(issue['id'],'RESOLVED',root)
    old=ledger.load_sentinel_issues_memory(root)
    candidate=dict(issue, status='OPEN_REAL', last_seen=datetime.now(timezone.utc).isoformat())
    new=ledger.upsert_sentinel_issues(old['issues'],[candidate])
    assert len(new)==1 and new[0]['seen_count']==2 and new[0]['reopened_count']==1
    assert new[0]['first_seen']==issue['first_seen'] and new[0]['verification_record'] is None
    ledger.save_sentinel_issues_memory({'issues':new},root)
    assert not ledger.update_issue_status(issue['id'],'RESOLVED',root)['ok']


def test_unverified_legacy_resolution_remains_pending(memory):
    root,issue=memory
    ledger.save_sentinel_issues_memory({'issues':[dict(issue,status='RESOLVED',verification='looks fixed')]},root)
    assert ledger.load_sentinel_issues_memory(root)['issues'][0]['status']=='FIXED_PENDING_VERIFICATION'


def test_stale_writer_cannot_erase_new_recurrence(memory):
    root, issue=memory
    stale=ledger.load_sentinel_issues_memory(root)
    current=ledger.load_sentinel_issues_memory(root)
    current['issues']=ledger.upsert_sentinel_issues(current['issues'],[issue])
    ledger.save_sentinel_issues_memory(current,root)
    with pytest.raises(OSError,match='changed_reload'):
        ledger.save_sentinel_issues_memory(stale,root)
    assert ledger.load_sentinel_issues_memory(root)['issues'][0]['seen_count']==2


@pytest.mark.parametrize('field', ['provider','job','route','error_code','exception_type'])
def test_same_rule_different_context_does_not_collapse(memory,field):
    _, issue=memory
    other=dict(issue, **{field:'different'}, fingerprint=issue['fingerprint'])
    output=ledger.upsert_sentinel_issues([issue],[other])
    assert len(output)==2 and len({i['id'] for i in output})==2


def test_shared_word_is_not_a_match(memory):
    from engines.reliability_engine import related_incidents
    _,issue=memory
    assert related_incidents({'title':'failure elsewhere'},[issue])['state']=='SIN EVIDENCIA'
    assert related_incidents({'id':issue['id']},[issue])['state']=='CONFIRMADO'
    assert related_incidents({'route':issue['route'],'component':issue['component']},[issue])['state']=='POSIBLE RELACIÓN'
    assert related_incidents({'route':issue['route'],'component':issue['component'],'file':'x'},[dict(issue,file='x')])['state']=='SIMILAR'


def test_reconciliation_does_not_merge_distinct_providers(memory):
    root,issue=memory
    other=ledger.normalize_sentinel_issue({k:v for k,v in dict(issue,provider='other').items() if k not in ('id','issue_id','fingerprint')})
    ledger.save_sentinel_issues_memory({'issues':[issue,other]},root)
    result=ledger.reconcile_autonomous_workforce_evidence(root,save=False)
    selected=[i for i in result['issues'] if i['id'] in (issue['id'],other['id'])]
    assert len(selected)==2 and all(i['status']!='DUPLICATE' for i in selected)


def test_memory_redacts_sensitive_text_and_nested_values(memory):
    root,issue=memory
    issue['root_cause']='Authorization: Bearer synthetic-sensitive-value'
    issue['history']=[{'token':'synthetic-sensitive-value','note':'Traceback (sensitive value)'}]
    ledger.save_sentinel_issues_memory({'issues':[issue]},root)
    raw=ledger.sentinel_issues_memory_path(root).read_text(encoding='utf-8')
    assert 'synthetic-sensitive-value' not in raw and 'Traceback (' not in raw


def identity():
    return dict(main_sha='a'*40,candidate_sha='b'*40,deployed_sha='a'*40,render_sha='a'*40,
        runtime_version='V941_TEST',app_version='V941_TEST',version_file='V941_TEST',
        production_observed_at=datetime.now(timezone.utc).isoformat())


def test_version_and_health_do_not_certify_sha_alignment():
    from engines.reliability_engine import production_drift
    state=production_drift({'runtime_version':'V941','deployed_version':'V941','health':200})
    assert state['state']=='UNKNOWN' and state['deployment_certified'] is False


def test_existing_runtime_adapter_distinguishes_reported_sha_from_render_evidence():
    from engines.sentinel_render_alignment_engine import build_render_alignment
    r=build_render_alignment({'app_version':'V941_TEST','git_commit_hint':'b'*40},
                            {'app_version':'V941_TEST','git_commit_hint':'a'*40})
    assert r['aligned'] is False and r['state']=='UNKNOWN'
    assert r['identity']['candidate_sha']=='b'*40 and r['identity']['deployed_sha']=='a'*40
    assert r['identity']['main_sha'] is None and r['identity']['render_sha'] is None


def test_stale_divergence_cannot_be_claimed_current():
    from engines.reliability_engine import production_drift
    data=identity();data.update(render_sha='c'*40,production_observed_at='2000-01-01T00:00:00Z')
    assert production_drift(data)['state']=='UNKNOWN'


@pytest.mark.parametrize('status',['OPEN_REAL','VERIFICATION_FAILED','FIXED_PENDING_VERIFICATION'])
def test_reopening_or_new_fix_invalidates_previous_proof(memory,status):
    root,issue=memory
    ledger.record_issue_verification(issue['id'],record(),root)
    assert ledger.update_issue_status(issue['id'],status,root)['ok']
    assert not ledger.update_issue_status(issue['id'],'RESOLVED',root)['ok']


def test_shark_relations_remain_local_and_require_multiple_signals(memory):
    from engines.shark_ai_product_assistant_engine import admin_deterministic_answer
    _,issue=memory
    state={'reliability':{'issues':[issue],'memory_available':True}}
    answer=admin_deterministic_answer('¿Esto ya ocurrió? ruta=/live componente=sports',state)
    assert answer['relation']['state']=='POSIBLE RELACIÓN' and answer['local_only'] is True
    answer=admin_deterministic_answer('¿Esto ya ocurrió? failure',state)
    assert answer['relation']['state']=='SIN EVIDENCIA'


def test_improvement_workflow_cannot_bypass_ledger_verification(memory):
    from engines.sentinel_improvement_workflow_engine import update_issue_state
    root,issue=memory
    assert update_issue_state(issue,'resolved')['status']=='verification_pending'
    ledger.record_issue_verification(issue['id'],record(),root)
    verified=ledger.load_sentinel_issues_memory(root)['issues'][0]
    assert update_issue_state(verified,'resolved')['status']=='resolved'


def test_failed_verification_stays_active_for_sentinel_and_codex(memory):
    from engines.sentinel_codex_outbox_engine import _codex_eligible
    root,issue=memory
    proof=record();proof['result']='FAIL'
    ledger.record_issue_verification(issue['id'],proof,root)
    m=ledger.load_sentinel_issues_memory(root)
    summary=ledger.build_sentinel_issues_summary('QA',m)
    assert summary['counts']['open']==1
    candidate=dict(m['issues'][0],evidence_sufficient=True)
    assert _codex_eligible(candidate)


@pytest.mark.parametrize('missing',['main_sha','deployed_sha','render_sha','production_observed_at'])
def test_incomplete_identity_is_unknown(missing):
    from engines.reliability_engine import production_drift
    data=identity();data.pop(missing)
    assert production_drift(data)['state']=='UNKNOWN'


def test_candidate_may_differ_from_main_without_production_drift():
    from engines.reliability_engine import production_drift
    state=production_drift(identity())
    assert state['state']=='ALIGNED_CONFIRMED' and state['candidate_matches_main'] is False
    assert state['deployment_certified'] is False


@pytest.mark.parametrize('field',['deployed_sha','render_sha','version_file'])
def test_divergent_evidence_is_detected(field):
    from engines.reliability_engine import production_drift
    data=identity();data[field]='V940_OTHER' if field=='version_file' else 'c'*40
    assert production_drift(data)['state']=='MISALIGNED_CONFIRMED'


def test_missing_runtime_authority_cannot_align():
    from engines.reliability_engine import production_drift
    data=identity();data['version_file']='Desconocida'
    assert production_drift(data)['state']=='UNKNOWN'


def test_same_deployed_sha_with_different_version_is_detected():
    from engines.reliability_engine import production_drift
    data=identity();data.update(runtime_sha='a'*40,deployed_version='V940_OTHER')
    assert production_drift(data)['state']=='MISALIGNED_CONFIRMED'


def test_radar_early_warning_requires_four_ordered_real_observations():
    from engines.reliability_engine import risk_radar
    now=datetime.now(timezone.utc)
    samples=[{'at':(now-timedelta(minutes=4-i)).isoformat(),'failed':i} for i in range(4)]
    alerts=risk_radar({'queue_samples':samples},now)['alerts']
    assert next(a for a in alerts if a['code']=='queue_growth')['state']=='OBSERVAR'
    for bad in (samples[:3],samples[::-1], [samples[0]]*4):
        assert not any(a['code']=='queue_growth' for a in risk_radar({'queue_samples':bad},now)['alerts'])


def test_radar_unknown_is_not_zero_and_stale_is_detected():
    from engines.reliability_engine import risk_radar
    data={'jobs':[{'name':'telegram_tick','enabled':True,'last_run':'2000-01-01T00:00:00Z'}],
          'providers':[{'key':'the_odds','configured':True,'status':'CACHE'}],
          'missing_tests':['tests/critical.py'],'unbound_buttons':['dashboard:4']}
    radar=risk_radar(data);by_code={a['code']:a for a in radar['alerts']}
    assert by_code['job:telegram_tick']['state']=='ATENCIÓN'
    assert by_code['cache:the_odds']['state']=='DESCONOCIDO'
    assert radar['probabilities'] is None


def test_real_internal_consumers_are_satisfied():
    from engines.reliability_engine import internal_interface_failures
    assert internal_interface_failures(Path(ledger.__file__).resolve().parents[1])==[]


def test_internal_contract_detects_break_but_allows_joint_refactor(tmp_path):
    from engines.reliability_engine import internal_interface_failures
    (tmp_path/'engines').mkdir();(tmp_path/'tests').mkdir()
    target=tmp_path/'engines/telegram_visual_card_engine.py';consumer=tmp_path/'tests/test_card.py'
    target.write_text('STATIC_ROOT = 1')
    consumer.write_text('from engines import telegram_visual_card_engine as cards\nvalue=cards.STATIC_ROOT')
    assert not internal_interface_failures(tmp_path)
    target.write_text('ASSET_ROOT = 1')
    assert internal_interface_failures(tmp_path)
    consumer.write_text('from engines import telegram_visual_card_engine as cards\nvalue=cards.ASSET_ROOT')
    assert not internal_interface_failures(tmp_path)
