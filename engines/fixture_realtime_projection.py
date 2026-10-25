"""Pure descriptor projection over a caller-prepared snapshot and own frames.

No App/SQLite/network/cache imports; the caller supplies already filtered original
members and the existing kickoff parser. No group carries a sports observation.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from collections import Counter
from engines.fixture_identity_read_model import project_fixture_identity
from engines.realtime_state_engine import build_realtime_match_evidence
from collections.abc import Mapping

from types import SimpleNamespace

from engines.fixture_identity_read_model import project_fixture_identity,provider_family,_fixture

def verify_native_fixture_owner(row,*,kickoff_for):
    projected=project_fixture_identity(row,kickoff_for=kickoff_for)
    if projected is None:return None
    view=projected[0]
    if provider_family(view.get('source') or view.get('provider'))!='api-football':return None
    raw=view.get('raw_json')
    if not isinstance(raw,Mapping):return None
    event=raw.get('fixture');league=raw.get('league');teams=raw.get('teams')
    if not all(isinstance(value,Mapping) for value in (event,league,teams)):return None
    if not all(isinstance(teams.get(side),Mapping) for side in ('home','away')):return None
    native=str(event.get('id') or '')
    if not native.isdecimal() or not native.startswith(tuple('123456789')) or len(native)>18:return None
    fixture_field=row.get('fixture_id')
    if fixture_field not in (None,''):
        if type(fixture_field) not in (str,int) or str(fixture_field)!=native:return None
    # A raw payload alone cannot claim an arbitrary local action ID. Require an
    # existing own external ID or the application's exact native AF identifier.
    if not view.get('external_id') and str(view.get('id') or '')!='af-'+native:return None
    copied=dict(view)
    for field,value in (
        ('external_id',native),('competition_id',league.get('id')),
        ('home_team_id',teams['home'].get('id')),('away_team_id',teams['away'].get('id')),
        ('season',league.get('season')),
    ):
        if copied.get(field) in (None,'') and value not in (None,''):copied[field]=str(value)
    # UNKNOWN native-only context cannot grant a canonical group/reference.
    context=SimpleNamespace(state='UNKNOWN_NATIVE_ONLY',issues=(),country_evidence=())
    fixture=_fixture(copied,0,kickoff_for,lambda _:context)
    if fixture is None or not fixture.native_verified or fixture.provider!='api-football':return None
    return {'provider':fixture.provider,'fixture_id':fixture.native_id,
        'competition_id':fixture.native_league_id,
        'home_team_id':fixture.home.ids.get(fixture.provider),
        'away_team_id':fixture.away.ids.get(fixture.provider),
        'season':copied.get('season'),'basis':'PROVIDER_NATIVE_FIXTURE'}

CONTRACT='NEMESIS-FIXTURE-GROUPS-V1'
MEASURES=('live','halftime','today','available','finished_verified','with_pick')
BASES=frozenset({'CANONICAL_COMPETITION','PROVIDER_NATIVE_FIXTURE','UNRESOLVED'})
BOOTSTRAP_STATE_FIELDS=('contract','sports_truth_contract','fixture_id','provider','competition_id','season',
    'home_team_id','away_team_id','status_canonical','is_live','is_stale','is_finished','status_conflict',
    'freshness_state','evaluated_at_madrid','provider_observed_at','live_valid_until_madrid',
    'score_home','score_away','minute','period_label')

def compact_bootstrap_state(state):
    return {key:state[key] for key in BOOTSTRAP_STATE_FIELDS if key in state} if isinstance(state,dict) else None

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:24]

def canonical_view(lane,query,normalize_query):
    lane=str(lane or 'live').strip().lower()
    aliases={'directo':'live','all':'live','today':'live','todos':'live','halftime':'break','descanso':'break',
             'finalizados':'finished','results':'finished','history':'finished','picks':'with_pick'}
    lane=aliases.get(lane,lane)
    if lane not in {'live','all','break','finished','with_pick'}:lane='live'
    return {'consumer':'directo-v2','lane':lane,'query':str(normalize_query(str(query or '')[:90]))[:90]}

def scope_id(scope):return _digest(scope)

def semantic_validator_payload(payload):
    """Opt-in weak comparison: exclude only closed evaluation-metadata paths.

    A same-named key in statistics/provider data is retained. Every contract,
    observation clock, lease, association, status, score and scope is retained.
    """
    result={key:value for key,value in payload.items() if key not in {'generated_at_madrid','cache_state'}}
    for array_name in ('matches','live'):
        if not isinstance(result.get(array_name),list):continue
        projected=[]
        for frame in result[array_name]:
            if not isinstance(frame,dict):projected.append(frame);continue
            item={key:value for key,value in frame.items() if key!='age_seconds'}
            state=item.get('realtime_state')
            if isinstance(state,dict):
                item['realtime_state']={key:value for key,value in state.items() if key not in {'evaluated_at_madrid','freshness_seconds'}}
            truth=item.get('status_truth')
            if isinstance(truth,dict):
                item['status_truth']={key:value for key,value in truth.items() if key!='live_age_seconds'}
            projected.append(item)
        result[array_name]=projected
    return result

def verified_api_fixture_id(row,kickoff_for):
    """Own native proof for saved statistics; no cross-provider alias grant."""
    proof=verify_native_fixture_owner(row,kickoff_for=kickoff_for)
    return proof['fixture_id'] if proof else None

def own_realtime_source(row,kickoff_for):
    """Fill absent identity fields only from this record's verified native raw.

    The copy never changes action IDs, prices, source, scores or clocks, and no
    conflicting explicit identity is overwritten. This also matches legitimate
    persisted API rows whose optional top-level identity columns are null.
    """
    proof=verify_native_fixture_owner(row,kickoff_for=kickoff_for)
    if not proof:return row
    copied=dict(row)
    values={'external_id':proof['fixture_id'],'competition_id':proof['competition_id'],
            'home_team_id':proof['home_team_id'],'away_team_id':proof['away_team_id'],'season':proof['season']}
    for key,value in values.items():
        if copied.get(key) in (None,'') and value not in (None,''):copied[key]=value
    return copied

def build_metrics_metadata(descriptor,*,picks,synchronized,scope):
    established=descriptor['state']=='ESTABLISHED_FOR_EMITTED_COHORT'
    numbers=descriptor['general']['counts']
    counts={'matches':numbers['available'],'today':numbers['today'],'live':numbers['live'],
            'finished':numbers['finished_verified'],'matches_with_picks':numbers['with_pick'],
            'picks':picks,'synchronized':synchronized}
    if not established:counts=dict.fromkeys(counts)
    units={key:'retained_fixture_groups' for key in counts}
    units.update(picks='safe_active_pick_observations',synchronized='source_observations')
    coverage=descriptor['coverage']
    result={'contract':'NEMESIS-FIXTURE-METRICS-V1',
        'state':'ESTABLISHED_FOR_CURRENT_COHORT' if established else 'NOT_ESTABLISHED',
        'unit':'mixed_declared_units','units':units,'cohort_scope':dict(descriptor['cohort_scope']),'counts':counts,
        'coverage':{'source_observations':coverage['emitted_observations'],'reference_state':coverage['reference_state'],
            'unresolved_singletons':coverage['unresolved_singletons'],'not_covered_observations':coverage['not_covered_observations'],
            'reasons':list(coverage['reasons'])}}
    result['generation']=_digest([descriptor['generation'],scope,result])
    return result

def _own_state(row,frame,kickoff_for):
    state=frame.get('realtime_state')
    if not isinstance(state,dict) or state.get('contract')!='NEMESIS-REALTIME-STATE-V1':return False
    try:
        evaluated=datetime.fromisoformat(str(state.get('evaluated_at_madrid') or '').replace('Z','+00:00'))
        if evaluated.tzinfo is None:return False
        own,_truth=build_realtime_match_evidence(own_realtime_source(row,kickoff_for),now=evaluated)
    except (ValueError,TypeError,OverflowError):return False
    # Same local/native/provider identity is insufficient: a clock, score or
    # minute from a different observation of that fixture must be rejected too.
    return own==state

def _stable_proof(row,kickoff_for):
    # Derived age/evaluation/presentation fields must not churn generation.
    allowed={'id','match_id','external_id','source','provider','competition_key','competition_id','league_id',
        'country','_raw_country','season','sport','sport_name','sport_key','home_team','away_team',
        'home_team_id','away_team_id','home_provider_team_ids','away_provider_team_ids',
        'home_canonical_team_id','away_canonical_team_id','home_team_aliases','away_team_aliases',
        '_raw_home_team','_raw_away_team','competition_name','league_name','_raw_competition_name',
        'kickoff_iso','commence_time','match_date','kickoff_time','match_time','raw_json','payload_json',
        'home_score','away_score','score','result','status','status_short','live_updated_at','provider_updated_at','last_synced_at'}
    value=project_fixture_identity({key:row[key] for key in allowed if key in row},kickoff_for=kickoff_for)
    return value[1].hex() if value is not None else 'UNSUPPORTED'

def _selection_members(snapshot,rows,tag,proofs):
    selection=snapshot.select_rows(rows)
    members=[]
    for group,basis in zip(selection.groups,selection.identity_basis):
        basis=basis if basis in BASES else 'UNRESOLVED'
        token='fg-'+_digest([tag,basis,sorted((str(row.get('id') or ''),proofs[id(row)]) for row in group)])
        members.extend({'id':str(row.get('id') or ''),'group':token,'basis':basis} for row in group)
    return members,selection

def build_descriptor(snapshot,rows,frames,*,scope,date_madrid,measure_rows,view_rows,kickoff_for,prepared=True,historical=False):
    rows=list(rows);frames=list(frames)
    proof={id(row):_stable_proof(row,kickoff_for) for row in rows}
    originals=[str(row.get('id') or '') for row in rows]
    emitted=[str(frame.get('id') or '') for frame in frames]
    reasons=[]
    if len(rows)>800:reasons.append('CURRENT_COHORT_LIMIT')
    if not prepared or snapshot is None:reasons.append('UNPREPARED_CONTEXT')
    if historical:reasons.append('HISTORICAL_SCOPE')
    if any(not identifier for identifier in originals):reasons.append('MISSING_ID')
    if any(len(identifier)>90 for identifier in originals):reasons.append('ID_EXCEEDS_TRANSPORT_BOUND')
    if any(count>1 for count in Counter(originals).values()):reasons.append('DUPLICATE_ID')
    if emitted!=originals:reasons.append('EMITTED_COHORT_MISMATCH')
    if any(not isinstance(frame.get('realtime_state'),dict) for frame in frames):reasons.append('MISSING_OWN_STATE')
    if len(rows)==len(frames) and any(not _own_state(row,frame,kickoff_for) for row,frame in zip(rows,frames)):reasons.append('WRONG_OWN_STATE')
    cohort_objects={id(row) for row in rows}
    if any(id(row) not in cohort_objects for values in measure_rows.values() for row in values):reasons.append('MEASURE_MEMBER_OUTSIDE_COHORT')
    if any(id(row) not in cohort_objects for row in view_rows):reasons.append('VIEW_MEMBER_OUTSIDE_COHORT')
    cohort={'kind':'current_sports','date_madrid':date_madrid,'historical':False}
    blank={'contract':CONTRACT,'state':'NOT_ESTABLISHED','cohort_scope':cohort,
        'general':{'members':[],'counts':dict.fromkeys(MEASURES)},
        'view':{'scope':dict(scope),'scope_id':scope_id(scope),'members':[],'groups_before_limit':None},
        'coverage':{'emitted_observations':len(frames),'grouped_observations':None,'unresolved_singletons':None,
            'reference_state':'UNKNOWN','not_covered_observations':len(rows),'reasons':sorted(set(reasons))}}
    if reasons:
        blank['generation']=_digest([scope,sorted(set(reasons)),[(identifier,proof[id(row)]) for identifier,row in zip(originals,rows)]])
        return blank
    member_rows,selection=_selection_members(snapshot,rows,'general',proof)
    by_id={member['id']:{**member,'measures':{}} for member in member_rows}
    counts={}
    for name in MEASURES:
        selected,measure=_selection_members(snapshot,measure_rows.get(name,()),'general:'+name,proof)
        counts[name]=measure.count
        for member in selected:by_id[member['id']]['measures'][name]={'group':member['group'],'basis':member['basis']}
    view_members,view_selection=_selection_members(snapshot,view_rows,'view:'+scope_id(scope),proof)
    view_by_id={member['id']:{**member,'measures':{}} for member in view_members}
    live_ids={id(row) for row in measure_rows.get('live',())}
    halftime_ids={id(row) for row in measure_rows.get('halftime',())}
    for name,eligible in (('live',live_ids),('halftime',halftime_ids)):
        selected,_measure=_selection_members(snapshot,[row for row in view_rows if id(row) in eligible],'view:'+scope_id(scope)+':'+name,proof)
        for member in selected:view_by_id[member['id']]['measures'][name]={'group':member['group'],'basis':member['basis']}
    states=[snapshot.context_for(row).state for row in rows]
    reference='RESOLVED' if all(state=='RESOLVED' for state in states) else 'PARTIAL_UNKNOWN' if any(state=='RESOLVED' for state in states) else 'UNKNOWN'
    result={'contract':CONTRACT,'state':'ESTABLISHED_FOR_EMITTED_COHORT','cohort_scope':cohort,
        'general':{'members':[by_id[identifier] for identifier in originals],'counts':counts},
        'view':{'scope':dict(scope),'scope_id':scope_id(scope),'members':[view_by_id[str(row['id'])] for row in view_rows],
                'groups_before_limit':view_selection.count},
        'coverage':{'emitted_observations':len(frames),'grouped_observations':selection.count,
            'unresolved_singletons':sum(member['basis']=='UNRESOLVED' for member in member_rows),
            'reference_state':reference,'not_covered_observations':0,'reasons':[]}}
    clocks=('provider_observed_at','provider_observed_at_source','live_valid_until_madrid',
            'lifecycle_observed_at','score_observed_at','minute_observed_at','events_observed_at','stats_observed_at')
    context=[]
    for row,frame in zip(rows,frames):
        identifier=str(row['id'])
        row_proof=proof[id(row)]
        current_context=snapshot.context_for(row)
        context.append((identifier,row_proof,current_context.state,list(current_context.issues),
                        {key:frame['realtime_state'].get(key) for key in clocks}))
    result['generation']=_digest([scope,cohort,context,result['general'],result['view']])
    return result
