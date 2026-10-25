import copy
import json
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from engines.fixture_realtime_projection import build_descriptor,canonical_view,verified_api_fixture_id,own_realtime_source,semantic_validator_payload,compact_bootstrap_state,BOOTSTRAP_STATE_FIELDS,build_metrics_metadata
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.v934_realtime_sports_engine import normalize_match
from engines.api_football_live_tracker_engine import _normalize_fixture

class Contracts(unittest.TestCase):
    def setUp(self):
        seed=json.loads((Path(__file__).with_name('v991_fixture_identity.json')).read_text(encoding='utf-8'))['input']
        self.rows=copy.deepcopy(seed['rows']);self.refs=seed['catalogue'];self.calls=[]
        self.now=datetime.now(ZoneInfo('Europe/Madrid'));self.kickoff=self.now+timedelta(hours=1)
        for row in self.rows:
            row.update(kickoff_iso=self.kickoff.isoformat(),match_date=self.kickoff.date().isoformat(),
                kickoff_time=self.kickoff.strftime('%H:%M'),match_time=self.kickoff.strftime('%H:%M'),
                last_synced_at=self.now.isoformat(),updated_at=self.now.isoformat())
            raw=json.loads(row['raw_json'])
            if row['source']=='api_football_live':raw['fixture']['date']=self.kickoff.isoformat()
            else:raw['strTimestamp']=self.kickoff.isoformat()
            row['raw_json']=json.dumps(raw)
        self.parse=lambda row:datetime.fromisoformat(row['kickoff_iso'])
        self.scope=canonical_view('all','',lambda value:value.strip().lower())
    def snapshot(self,rows=None,refs=None):
        def read(keys):self.calls.append(list(keys));return self.refs if refs is None else refs
        return prepare_fixture_snapshot({'current':self.rows if rows is None else rows},read,kickoff_for=self.parse)
    def frames(self,rows=None,now=None):
        return [normalize_match(own_realtime_source(row,self.parse),self.now if now is None else now) for row in self.rows if rows is None] if rows is None else [normalize_match(own_realtime_source(row,self.parse),self.now if now is None else now) for row in rows]
    def build(self,rows=None,frames=None,snapshot=None,view=None,scope=None,refs=None):
        rows=self.rows if rows is None else rows;frames=self.frames(rows) if frames is None else frames
        snapshot=self.snapshot(rows,refs) if snapshot is None else snapshot
        return build_descriptor(snapshot,rows,frames,scope=self.scope if scope is None else scope,
            date_madrid=self.now.date().isoformat(),measure_rows={'today':rows,'available':rows},
            view_rows=rows if view is None else view,kickoff_for=self.parse)
    def test_three_observations_two_groups_and_exact_coverage(self):
        result=self.build();self.assertEqual(result['state'],'ESTABLISHED_FOR_EMITTED_COHORT')
        self.assertEqual(result['coverage']['grouped_observations'],2)
        self.assertEqual(result['general']['counts']['today'],2)
        self.assertEqual([item['id'] for item in result['general']['members']],[row['id'] for row in self.rows])
        self.assertEqual(len(self.calls),1)
    def test_secondary_member_filter_owns_view_not_general_winner(self):
        result=self.build(view=[self.rows[1]])
        self.assertEqual([member['id'] for member in result['view']['members']],['sdb-901002'])
        self.assertEqual(result['view']['groups_before_limit'],1)
    def test_each_measure_has_own_group_namespace(self):
        result=self.build();member=result['general']['members'][0]
        self.assertNotEqual(member['group'],member['measures']['today']['group'])
        self.assertNotEqual(member['measures']['today']['group'],member['measures']['available']['group'])
    def test_missing_reference_is_retained_not_false_zero(self):
        result=self.build(refs=[])
        self.assertEqual(result['state'],'ESTABLISHED_FOR_EMITTED_COHORT')
        self.assertEqual(result['coverage']['reference_state'],'UNKNOWN')
        self.assertEqual(result['coverage']['grouped_observations'],3)
    def test_wrong_provider_frame_fails_closed(self):
        frames=self.frames();frames[1]['realtime_state']=copy.deepcopy(frames[0]['realtime_state'])
        result=self.build(frames=frames);self.assertEqual(result['state'],'NOT_ESTABLISHED')
        self.assertIn('WRONG_OWN_STATE',result['coverage']['reasons'])
        self.assertTrue(all(value is None for value in result['general']['counts'].values()))
    def test_same_native_fixture_other_clock_score_is_not_own_state(self):
        row=copy.deepcopy(self.rows[0]);row.update(status='LIVE',minute=15,home_score=1,away_score=0)
        row['kickoff_iso']=(self.now-timedelta(minutes=20)).isoformat()
        donor=copy.deepcopy(row);donor.update(minute=10,home_score=0,last_synced_at=(self.now-timedelta(seconds=5)).isoformat())
        result=self.build(rows=[row],frames=self.frames([donor]))
        self.assertEqual(result['state'],'NOT_ESTABLISHED');self.assertIn('WRONG_OWN_STATE',result['coverage']['reasons'])
    def test_generation_ignores_evaluation_age_not_provider_clock(self):
        snap=self.snapshot();one=self.build(snapshot=snap)
        two=self.build(snapshot=snap,frames=self.frames(now=self.now+timedelta(seconds=1)))
        self.assertEqual(one['generation'],two['generation'])
        changed=copy.deepcopy(self.rows);changed[0]['last_synced_at']=(self.now+timedelta(seconds=1)).isoformat()
        three=self.build(rows=changed)
        self.assertNotEqual(one['generation'],three['generation'])
    def test_reference_only_change_changes_generation_without_leases(self):
        frames=self.frames();one=self.build(frames=frames)
        altered=copy.deepcopy(self.refs);altered[0]['country']='Portugal'
        two=self.build(frames=frames,refs=altered)
        self.assertNotEqual(one['generation'],two['generation']);self.assertEqual(frames,self.frames())
    def test_scope_only_change_changes_generation(self):
        one=self.build();two=self.build(scope=canonical_view('live','madrid',lambda value:value))
        self.assertNotEqual(one['generation'],two['generation']);self.assertNotEqual(one['view']['scope_id'],two['view']['scope_id'])
    def test_duplicate_ids_invalidate_whole_map(self):
        rows=copy.deepcopy(self.rows);rows[1]['id']=rows[0]['id'];result=self.build(rows=rows)
        self.assertEqual(result['state'],'NOT_ESTABLISHED');self.assertEqual(result['general']['members'],[])
        self.assertEqual(result['view']['members'],[]);self.assertIsNone(result['view']['groups_before_limit'])
    def test_overlong_ids_do_not_become_truncated_identity(self):
        rows=copy.deepcopy(self.rows);rows[0]['id']='x'*91;frames=self.frames(rows)
        for row,frame in zip(rows,frames):frame['id']=row['id']
        result=self.build(rows=rows,frames=frames)
        self.assertIn('ID_EXCEEDS_TRANSPORT_BOUND',result['coverage']['reasons'])
    def test_identity_objects_never_serialize(self):
        result=self.build();encoded=json.dumps(result)
        self.assertNotIn('raw_json',encoded);self.assertNotIn('PreparedFixtureSnapshot',encoded)
    def test_missing_state_is_unknown_not_empty(self):
        frames=self.frames();frames[1]['realtime_state']=None;result=self.build(frames=frames)
        self.assertEqual(result['state'],'NOT_ESTABLISHED');self.assertIsNone(result['general']['counts']['live'])
    def test_foreign_view_member_is_rejected(self):
        result=self.build(view=[copy.deepcopy(self.rows[0])])
        self.assertIn('VIEW_MEMBER_OUTSIDE_COHORT',result['coverage']['reasons'])
    def test_real_api_normalizer_persisted_shape_and_nullable_ids(self):
        payload=json.loads(self.rows[0]['raw_json']);payload['fixture']['status']={'short':'NS','elapsed':None}
        payload['goals']={'home':None,'away':None}
        native=_normalize_fixture(payload)
        row={'id':native['match_id'],'external_id':native['fixture_id'],'source':'api_football_live',
            'competition_id':native['league_id'],'competition_name':native['league_name'],'season':native['season'],
            'home_team':native['home_team'],'away_team':native['away_team'],'home_team_id':native['home_team_id'],
            'away_team_id':native['away_team_id'],'kickoff_iso':native['kickoff_iso'],'raw_json':native['payload_json']}
        self.assertEqual(verified_api_fixture_id(row,self.parse),native['fixture_id'])
        for key in ('home_team_id','away_team_id','competition_id','external_id'):row[key]=None
        before=copy.deepcopy(row);projection=own_realtime_source(row,self.parse)
        self.assertEqual(verified_api_fixture_id(row,self.parse),native['fixture_id'])
        self.assertEqual(projection['home_team_id'],native['home_team_id']);self.assertEqual(projection['external_id'],native['fixture_id'])
        self.assertEqual(row,before);self.assertEqual(projection['id'],before['id'])
    def test_explicit_native_conflict_does_not_grant_statistics(self):
        for key in ('external_id','competition_id','home_team_id','away_team_id','id'):
            row=copy.deepcopy(self.rows[0]);row[key]='af-999' if key=='id' else '999'
            self.assertIsNone(verified_api_fixture_id(row,self.parse),key)
        self.assertIsNone(verified_api_fixture_id(self.rows[1],self.parse))
    def test_missing_native_payload_is_not_verified_statistics(self):
        row=copy.deepcopy(self.rows[0]);row['raw_json']='{}';self.assertIsNone(verified_api_fixture_id(row,self.parse))
    def test_semantic_validator_excludes_only_closed_eval_paths(self):
        base={'generated_at_madrid':'one','cache_state':'one','matches':[{'age_seconds':1,'realtime_state':{'evaluated_at_madrid':'one','freshness_seconds':1,
            'provider_observed_at':'clock','live_valid_until_madrid':'lease','score_home':1},'live_statistics':{'evaluated_at_madrid':'observation','age_seconds':7}}]}
        newer=copy.deepcopy(base);newer.update(generated_at_madrid='two',cache_state='two')
        newer['matches'][0]['age_seconds']=2;newer['matches'][0]['realtime_state'].update(evaluated_at_madrid='two',freshness_seconds=2)
        self.assertEqual(semantic_validator_payload(base),semantic_validator_payload(newer))
        newer['matches'][0]['live_statistics']['evaluated_at_madrid']='new observed statistic'
        self.assertNotEqual(semantic_validator_payload(base),semantic_validator_payload(newer))
    def test_semantic_validator_preserves_lease_score_clock_map_scope(self):
        base={'matches':[{'realtime_state':{'provider_observed_at':'clock','live_valid_until_madrid':'lease','score_home':1,'status_canonical':'LIVE'}}],
            'fixture_identity':self.build()}
        for key in ('provider_observed_at','live_valid_until_madrid','score_home','status_canonical'):
            changed=copy.deepcopy(base);changed['matches'][0]['realtime_state'][key]='changed'
            self.assertNotEqual(semantic_validator_payload(base),semantic_validator_payload(changed),key)
        changed=copy.deepcopy(base);changed['fixture_identity']['generation']='0'*24
        self.assertNotEqual(semantic_validator_payload(base),semantic_validator_payload(changed))
    def test_bootstrap_has_exact_twenty_one_used_fields(self):
        state=self.frames()[0]['realtime_state'];compact=compact_bootstrap_state(state)
        self.assertEqual(set(compact),set(BOOTSTRAP_STATE_FIELDS));self.assertEqual(len(compact),21)
        for key in compact:self.assertEqual(compact[key],state[key])
        self.assertNotIn('coverage',compact);self.assertIsNone(compact_bootstrap_state(None))
    def test_api_native_proof_uses_full_unchanged_c2_guard(self):
        for field,value in (('season','2025'),('country','Portugal'),('kickoff_iso',(self.kickoff+timedelta(hours=1)).isoformat()),
                            ('sport','basketball'),('competition_name','Premier League'),('home_team','Atletico Madrid')):
            row=copy.deepcopy(self.rows[0]);row[field]=value;before=copy.deepcopy(row)
            self.assertIsNone(verified_api_fixture_id(row,self.parse),field);self.assertEqual(row,before)
    def test_real_live_age_path_does_not_churn_weak_semantics(self):
        row=copy.deepcopy(self.rows[0]);row.update(status='LIVE',minute=15,home_score=1,away_score=0,
            kickoff_iso=(self.now-timedelta(minutes=20)).isoformat(),last_synced_at=(self.now-timedelta(seconds=30)).isoformat())
        raw=json.loads(row['raw_json']);raw['fixture']['date']=row['kickoff_iso'];row['raw_json']=json.dumps(raw)
        one=normalize_match(row,self.now);two=normalize_match(row,self.now+timedelta(seconds=1))
        self.assertEqual(one['status_truth']['live_age_seconds']+1,two['status_truth']['live_age_seconds'])
        self.assertEqual(semantic_validator_payload({'matches':[one],'live':[one]}),semantic_validator_payload({'matches':[two],'live':[two]}))
    def test_generic_metrics_units_and_generation_cover_all_declared_metadata(self):
        descriptor=self.build();one=build_metrics_metadata(descriptor,picks=4,synchronized=3,scope='all')
        self.assertEqual(one['contract'],'NEMESIS-FIXTURE-METRICS-V1')
        self.assertEqual(one['counts']['matches'],2);self.assertEqual(one['counts']['picks'],4)
        self.assertEqual(one['units']['picks'],'safe_active_pick_observations')
        self.assertEqual(one['units']['synchronized'],'source_observations')
        self.assertNotIn('members',json.dumps(one))
        for picks,synchronized,scope in ((5,3,'all'),(4,4,'all'),(4,3,'picks')):
            two=build_metrics_metadata(descriptor,picks=picks,synchronized=synchronized,scope=scope)
            self.assertNotEqual(one['generation'],two['generation'])
        changed=copy.deepcopy(descriptor);changed['coverage']['reference_state']='UNKNOWN'
        self.assertNotEqual(one['generation'],build_metrics_metadata(changed,picks=4,synchronized=3,scope='all')['generation'])
    def test_generic_unestablished_has_no_fake_numeric_counts(self):
        frames=self.frames();frames[0]['realtime_state']=None
        descriptor=self.build(frames=frames)
        meta=build_metrics_metadata(descriptor,picks=4,synchronized=3,scope='odds')
        self.assertEqual(meta['state'],'NOT_ESTABLISHED');self.assertTrue(all(value is None for value in meta['counts'].values()))
    def test_all_bookmark_is_canonical_live_alias(self):
        self.assertEqual(canonical_view('all','',lambda value:value)['lane'],'live')
