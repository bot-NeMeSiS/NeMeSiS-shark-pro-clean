from __future__ import annotations

import json
from pathlib import Path

import pytest

from engines.audience_priority_policy import load_policy, priority_registry
from engines.match_sync_engine import IMPORTANT_COMPETITIONS

KEYS = {item['key'] for item in IMPORTANT_COMPETITIONS}


def test_default_policy_has_research_and_no_claim_of_user_telemetry():
    policy = load_policy(KEYS)
    assert policy['profile'] == 'ES_EU'
    assert 'not_user_telemetry' in policy['basis']
    assert len(policy['evidence']) == 2
    assert load_policy(KEYS, 'GLOBAL')['rules'] == []


@pytest.mark.parametrize('bad_rule', [
    {'key':'invented-league','rank':1,'rationale':'invalid'},
    {'key':'laliga','rank':True,'rationale':'invalid'},
    {'key':'laliga','rank':0,'rationale':'invalid'},
    {'key':'laliga','rank':1,'rationale':''},
])
def test_invalid_policy_falls_back_atomically(tmp_path, bad_rule):
    payload = {'schema_version':1,'profiles':{'ES_EU':{
        'rules':[{'key':'premier-league','rank':8,'rationale':'valid'},bad_rule],
        'evidence':['research'], 'basis':'editorial','reviewed_at':'2026-10-03'}}}
    path = tmp_path / 'policy.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    assert load_policy(KEYS, path=path)['rules'] == []


def test_missing_and_unknown_profile_preserve_catalog(tmp_path):
    assert load_policy(KEYS, path=tmp_path/'missing.json')['rules'] == []
    assert load_policy(KEYS, profile='UNKNOWN')['rules'] == []


def test_spain_and_europe_order_is_independent_of_provider_and_pick_bonus(app_module):
    rows = [
        {'id':'eng','competition_id':'4328','competition_name':'Premier League','country':'England','home_team':'Arsenal','away_team':'Chelsea','has_pick':True},
        {'id':'esp','competition_id':'4335','competition_name':'LaLiga','country':'Spain','home_team':'Villarreal','away_team':'Getafe'},
        {'id':'ucl','competition_id':'4480','competition_name':'UEFA Champions League','country':'Europe','home_team':'Liverpool','away_team':'PSG'},
        {'id':'ukr','competition_name':'Premier League','country':'Ukraine','home_team':'Local','away_team':'Visitante'},
    ]
    for row in rows:
        row.update(match_date=app_module.today_iso(),kickoff_time='20:00',status='PROGRAMADO',source='test-fixture')
    ranks = [app_module.sports_competition_priority(row, audience=True)['rank'] for row in rows]
    assert ranks == [8,3,4,95]
    assert [app_module.sports_competition_priority(row)['rank'] for row in rows] == [10,10,10,95]
    assert app_module.sports_relevance_profile(rows[1])['competition_rank'] == 10
    grouped = app_module._calendar_group(app_module.sort_matches_by_sports_relevance(rows, 'calendar'))
    assert [league['matches'][0]['id'] for league in grouped[0]['leagues']][:3] == ['esp','ucl','eng']
    assert rows[0]['has_pick'] is True
    assert 'sports_relevance' not in rows[0]  # never mutate input/pick facts


def test_global_profile_keeps_legacy_registry():
    original = [{'keys':['laliga'],'tier':'S','weight':420,'rank':10,'label':'Elite'}]
    assert priority_registry(load_policy(KEYS,'GLOBAL'), IMPORTANT_COMPETITIONS, original) == original
