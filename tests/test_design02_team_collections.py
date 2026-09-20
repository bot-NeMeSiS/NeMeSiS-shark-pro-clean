"""A team's display collections consume canonical status, never infer FT from date."""
import pytest


@pytest.mark.parametrize('key', ['FT', 'RESULT_PENDING', 'STALE', 'POSTPONED', 'SUSPENDED'])
def test_team_date_partition_does_not_override_canonical_status(app_module, monkeypatch, key):
    future = {'id': 'today', 'home_team': 'Club QA', 'away_team': 'Visitante',
              'match_date': '2026-09-13', 'kickoff_time': '18:00', 'home_score': None, 'away_score': None,
              'status_info': {'key': key, 'is_finished': key == 'FT', 'is_upcoming': False, 'is_live': False}}
    past = {'id': 'past-unknown', 'home_team': 'Club QA', 'away_team': 'Visitante',
            'match_date': '2026-09-12', 'status_info': {'key': 'RESULT_PENDING'}}
    monkeypatch.setattr(app_module, 'team_lookup', lambda _: {'name': 'Club QA'})
    monkeypatch.setattr(app_module, 'resolve_team', lambda _: {})
    monkeypatch.setattr(app_module, 'favorite_sets', lambda: {})
    monkeypatch.setattr(app_module, 'rows', lambda sql, params: [future] if 'match_date>=' in sql else [past])
    monkeypatch.setattr(app_module, 'annotate_match', lambda m, *a, **kw: m)
    monkeypatch.setattr(app_module, 'is_fake_match', lambda _: False)
    monkeypatch.setattr(app_module, 'get_picks', lambda **kw: [])
    monkeypatch.setattr(app_module, '_cached_players_for_team', lambda *a: [])
    monkeypatch.setattr(app_module, 'shark_context_summary', lambda _: {})
    monkeypatch.setattr(app_module, 'build_team_center_context', lambda *a, **kw: {})
    detail = app_module.team_page_data('Club QA')
    assert detail['upcoming'] == []
    assert [m['id'] for m in detail['recent']] == (['today'] if key == 'FT' else [])
    assert [m['id'] for m in detail['pending']] == (['past-unknown'] if key == 'FT' else ['today', 'past-unknown'])
    assert future['home_score'] is None and future['away_score'] is None
