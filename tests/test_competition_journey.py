"""Regressions for the public competition -> fixture -> team journey."""
import json
import sqlite3
import pytest

from engines.competition_center_engine import build_competition_center_context


def match(identifier, competition_id="4335", name="Spanish La Liga", *, date="2026-10-10", status="NS", season="2026-2027"):
    return {
        "id": identifier, "competition_id": competition_id,
        "competition_key": "spanish-la-liga" if competition_id == "4335" else "spanish-la-liga-2",
        "competition_name": name, "league_name": name, "country": "Spain",
        "source": "TheSportsDB API", "season": season, "round": "8",
        "match_date": date, "kickoff_time": "18:30", "kickoff_iso": date + "T18:30:00+02:00",
        "home_team": "Barcelona", "away_team": "Getafe", "home_team_id": "133739", "away_team_id": "133731",
        "status": status, "home_score": 2 if status == "FT" else None,
        "away_score": 0 if status == "FT" else None,
        "updated_at": "2026-10-08T12:00:00+02:00",
    }


def competition():
    return {"key": "laliga", "external_id": "4335", "name": "LaLiga EA Sports", "country": "Spain", "source": "population_engine"}


def test_strong_competition_id_rejects_legacy_mislabeled_rows(app_module, monkeypatch):
    fixtures = [match("first"), match("second", "4400", "LaLiga EA Sports"), match("peru", "5908", "LaLiga EA Sports")]
    monkeypatch.setattr(app_module, "rows", lambda *a, **kw: fixtures)
    monkeypatch.setattr(app_module, "annotate_match", lambda item, **kw: dict(item))
    assert [row["id"] for row in app_module._competition_matches_for(competition(), "4335")] == ["first"]


def test_pending_old_and_cancelled_fixtures_are_not_the_next_round():
    fixtures = [match("old", date="2026-06-14"), match("next"), match("cancelled", date="2026-10-09", status="CANC"), match("result", date="2026-10-07", status="FT")]
    fixtures[0]["round"] = "1"
    center = build_competition_center_context({"competition": competition(), "matches": fixtures}, observed_at_madrid="2026-10-08T16:00:00+02:00")
    assert [row["id"] for row in center["calendar"]["upcoming"]] == ["next"]
    assert [row["id"] for row in center["calendar"]["recent"]] == ["result"]
    assert center["calendar"]["current_round"] == "8"
    assert center["competition"]["stage"] == "8"


def test_team_catalog_does_not_duplicate_persisted_and_match_identities():
    fixtures = [match("next")]
    teams = [{"key": "barcelona", "name": "Barcelona", "external_id": "133739", "country": "Spain", "source": "sportsdb"}]
    center = build_competition_center_context({"competition": competition(), "matches": fixtures, "teams": teams}, observed_at_madrid="2026-10-08T16:00:00+02:00")
    assert [team["name"] for team in center["teams"]] == ["Barcelona", "Getafe"]
    assert center["teams"][0]["matches"] == 1


def test_localization_recovers_provider_name_without_rewriting_the_source(app_module):
    from engines.spanish_localization_engine import apply_match_localization
    row = match("second", "4400", "LaLiga EA Sports")
    row["raw_json"] = json.dumps({"idLeague": "4400", "strLeague": "Spanish La Liga 2", "strCountry": "Spain"})
    localized = apply_match_localization(row)
    assert localized["competition_name"] == "Segunda División"
    assert row["competition_name"] == "LaLiga EA Sports"


@pytest.mark.parametrize('raw', ['not-json', '[]', '{"idLeague":"4335","strLeague":"Spanish La Liga"}'])
def test_mismatched_or_invalid_payload_does_not_replace_identity(raw):
    from engines.spanish_localization_engine import provider_competition_facts
    assert provider_competition_facts({**match('second', '4400'), 'raw_json': raw}) == {}


def test_provider_ids_are_namespaced_and_generic_names_are_country_scoped():
    from engines.competition_read_model import competition_contains
    assert not competition_contains(competition(), {**match('other'), 'source': 'api_football_cache', 'competition_name':'Another league', 'league_name':'Another league'})
    assert competition_contains(competition(), {**match('api', '140'), 'source':'api_football_cache'})
    assert not competition_contains(competition(), {**match('other'), 'country':'Peru'})
    assert not competition_contains(competition(), {**match('second', '4400', 'LaLiga EA Sports'), 'source':'api_football_cache', 'raw_json':json.dumps({'league':{'id':4400,'name':'Spanish La Liga 2'}})})


def test_season_aliases_do_not_mix_history_or_unconfirmed_seasons():
    from engines.competition_read_model import select_season
    fixtures = [match('old',season='2025'),match('this'),match('alias',season='2026'),match('unknown',season='')]
    selected, season, options = select_season(fixtures)
    assert {row['id'] for row in selected} == {'this','alias'}
    assert season == '2026-2027' and options == ['2026-2027','2025']
    assert [row['id'] for row in select_season(fixtures,'2025')[0]] == ['old']
    assert select_season(fixtures,'missing')[0] == []


def test_unplayed_placeholder_scores_do_not_count_as_team_form():
    row = {**match('next'), 'home_score':0,'away_score':0}
    center = build_competition_center_context({'competition':competition(),'matches':[row]},observed_at_madrid='2026-10-08T16:00:00+02:00')
    assert all(team['form']['sequence'] == [] for team in center['teams'])
    assert center['data_quality']['certification_state'] != 'VERIFIED'


def test_weak_team_identity_joins_only_one_strong_identity():
    strong = match('strong')
    weak = {**match('weak'), 'home_team_id':None}
    center = build_competition_center_context({'matches':[strong,weak]})
    assert len(center['teams']) == 2
    assert next(team for team in center['teams'] if team['name']=='Barcelona')['matches'] == 2
    conflict = {**match('conflict'), 'home_team_id':'different'}
    center = build_competition_center_context({'matches':[strong,weak,conflict]})
    assert len([team for team in center['teams'] if team['name']=='Barcelona']) == 3


def test_picks_require_a_match_in_the_selected_competition_and_season(app_module,monkeypatch):
    monkeypatch.setattr(app_module,'get_picks',lambda **kw:[
        {'id':'pick1','match_id':'included'},
        {'id':'pick2','match_id':'another','competition_name':'LaLiga EA Sports'},
        {'id':'included','competition_name':'LaLiga EA Sports'}])
    assert [p['id'] for p in app_module._competition_picks_for(competition(),[match('included')])] == ['pick1']


def test_sql_candidate_query_filters_polluted_names_and_does_not_write(app_module,monkeypatch):
    with sqlite3.connect(':memory:') as connection:
        connection.row_factory=sqlite3.Row
        fixtures=[match('first'),match('second','4400','LaLiga EA Sports'),match('peru','5908','LaLiga EA Sports')]
        keys=list(fixtures[0])
        connection.execute('CREATE TABLE matches (' + ','.join('"'+key+'" TEXT' for key in keys) + ')')
        connection.executemany('INSERT INTO matches VALUES ('+','.join('?' for key in keys)+')',[[row[key] for key in keys] for row in fixtures])
        monkeypatch.setattr(app_module,'rows',lambda sql,args=():[dict(row) for row in connection.execute(sql,args)])
        monkeypatch.setattr(app_module,'annotate_match',lambda row,**kw:row)
        changed=connection.total_changes
        assert [row['id'] for row in app_module._competition_matches_for(competition(),'4335')] == ['first']
        assert connection.total_changes == changed


def test_standings_cannot_use_a_sportsdb_id_in_the_api_football_table(app_module,monkeypatch):
    monkeypatch.setattr(app_module,'competition_lookup',lambda _:competition())
    fixtures=[match('first')]
    monkeypatch.setattr(app_module,'_competition_matches_for',lambda *a,**kw:fixtures)
    monkeypatch.setattr(app_module,'_competition_teams_for',lambda *a:[])
    monkeypatch.setattr(app_module,'_competition_picks_for',lambda *a:[])
    calls=[]
    monkeypatch.setattr(app_module,'_competition_standings_for',lambda *a,**kw:calls.append((a,kw)) or [])
    assert app_module.competition_page_data('4335')['standings'] == []
    assert calls == []
    fixtures.append({**match('api','140',season='2026'),'source':'api_football_cache'})
    app_module.competition_page_data('4335')
    assert calls[0][0][1] == '140'
    assert calls[0][1] == {'season':'2026','strict_identity':True}


@pytest.mark.parametrize('locale,title,count',[('es','Encuentra tu competición','1 competición'),('en','Find your competition','1 competition'),('fr','Trouvez votre compétition','1 compétition')])
def test_directory_get_search_works_without_js_and_with_locales(app_module,monkeypatch,locale,title,count):
    monkeypatch.setattr(app_module,'competitions',lambda:[{**competition(),'country':'España'},{'key':'premier','name':'Premier League','country':'Inglaterra'}])
    monkeypatch.setattr(app_module,'rows',lambda *a,**kw:[])
    with app_module.app.test_request_context('/competiciones?q=laliga&country=España',headers={'Accept-Language':locale}):
        html=app_module.global_football()
    assert title in html and count in html
    assert 'href="/competition/laliga"' in html and 'href="/competition/premier"' not in html
    assert 'method="get"' in html


def test_empty_directory_and_search_input_are_safe(app_module,monkeypatch):
    monkeypatch.setattr(app_module,'competitions',lambda:[])
    monkeypatch.setattr(app_module,'rows',lambda *a,**kw:[])
    with app_module.app.test_request_context('/competiciones',query_string={'q':'<script>alert(1)</script>'}):
        html=app_module.global_football()
    assert 'No encontramos esa competición' in html
    assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html


def test_team_journey_retains_registered_aliases_without_country_or_id_collisions(app_module,monkeypatch):
    team={'name':'FC Barcelona','external_id':'133739','country':'Spain','source':'sportsdb'}
    fixtures=[match('short'), {**match('long'),'home_team':'FC Barcelona'},
              {**match('homonym'),'country':'Ecuador'},
              {**match('conflict'),'home_team_id':'other'},
              {**match('continental'),'country':'Europe'}]
    with sqlite3.connect(':memory:') as connection:
        connection.row_factory=sqlite3.Row
        keys=list(fixtures[0])
        connection.execute('CREATE TABLE matches ('+','.join('"'+k+'" TEXT' for k in keys)+')')
        connection.executemany('INSERT INTO matches VALUES ('+','.join('?' for _ in keys)+')',[[row[k] for k in keys] for row in fixtures])
        monkeypatch.setattr(app_module,'today_iso',lambda:'2026-10-08')
        monkeypatch.setattr(app_module,'rows',lambda sql,args=():[dict(row) for row in connection.execute(sql,args)])
        assert {row['id'] for row in app_module._team_journey_matches(team,'Barcelona')} == {'short','long','continental'}
