"""Read-only cron diagnostic regression. No provider calls or app startup."""
import importlib.util
from pathlib import Path
import json
import pytest

path = Path(__file__).resolve().parents[1] / 'tools' / 'render_cron_master_tick.py'
spec = importlib.util.spec_from_file_location('cron_observation_test',path)
master = importlib.util.module_from_spec(spec)
spec.loader.exec_module(master)

@pytest.mark.parametrize('source,expected',[
 ('LAST_PERSISTED_DEEP_SAMPLE',False),('NONE',False),('',False),('CURRENT_DEEP_RUN',True)])
def test_access_uses_observation_source_not_legacy_flag(source,expected):
    raw={'provider_authenticated':True,'provider_access':{'source':source,'state':'ACCESS_FAILED','authenticated':False}}
    out=master.sanitized_sports_pipeline({'sports_pipeline':raw},'qa-secret')
    assert out['provider_access']['is_current_observation'] is expected
    assert out['provider_access']['current_state']==('ACCESS_FAILED' if expected else 'NOT_CHECKED')
    assert out['provider_access']['state']=='ACCESS_FAILED'


def test_no_fixture_is_not_scheduled_not_due():
    out=master.sanitized_sports_pipeline({'sports_pipeline':{'deep_status':'SKIPPED_NO_API_FOOTBALL_FIXTURE','deep_execution':{'state':'NOT_DUE'}}},'x')
    assert out['deep_execution']['state']=='NO_ELIGIBLE_FIXTURE'


def test_missing_fallback_is_not_zero_calls_or_complete():
    out=master.sanitized_sports_pipeline({'sports_pipeline':{'status':'PARTIAL'}},'x')
    assert out['fallback_execution']['status']=='NOT_REPORTED'
    assert out['fallback_execution']['external_calls'] is None
    assert out['fallback_execution']['budget']['requests_started'] is None


def test_budget_allowlist_does_not_expose_secret_or_change_quota_freshness():
    raw={'fallback_execution':{'status':'PARTIAL','external_calls':2,'budget':{'requests_started':2,'secret':'qa-private','budget_exhausted':True}},'quota_observation':{'freshness':'LAST_OBSERVED_NOT_CURRENT','values':{'daily_remaining':99}}}
    out=master.sanitized_sports_pipeline({'sports_pipeline':raw},'qa-private')
    assert 'qa-private' not in json.dumps(out)
    assert out['quota_observation']['freshness']=='LAST_OBSERVED_NOT_CURRENT'
    assert out['fallback_execution']['budget']['budget_exhausted'] is True
