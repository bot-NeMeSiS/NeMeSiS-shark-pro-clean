from pathlib import Path
import sqlite3

import pytest

from engines.sports_search import search_sports, mark_saved, search_saved


@pytest.fixture()
def sports_catalogue(tmp_path):
    path = tmp_path/'sports.db'
    with sqlite3.connect(path) as db:
        db.executescript('''CREATE TABLE teams(key TEXT PRIMARY KEY,name TEXT,country TEXT,league TEXT,external_id TEXT,source TEXT);
            CREATE TABLE competitions(key TEXT PRIMARY KEY,name TEXT,country TEXT,region TEXT);
            CREATE TABLE matches(id TEXT PRIMARY KEY,home_team TEXT,away_team TEXT,competition_name TEXT,league_name TEXT,country TEXT,match_date TEXT,kickoff_time TEXT,source TEXT);
            CREATE INDEX idx_matches_date_status ON matches(match_date);
            CREATE TABLE favorites(id TEXT PRIMARY KEY,user_id TEXT,kind TEXT,value TEXT,label TEXT,created_at TEXT);''')
        db.executemany('INSERT INTO teams VALUES(?,?,?,?,?,?)', [
            ('granada-cf','Granada CF','España','Segunda División','1','sportsdb'),
            ('granada-fem','Granada Femenino','España','Liga F','2','sportsdb'),
            ('atletico','Atlético Granada','España','Regional','3','sportsdb'),
            ('granada-ni','Granada CF','Nicaragua','Primera','4','sportsdb'),
            ('percent','100% Granada','España','Local','5','sportsdb'),
            ('unsafe','<img src=x onerror=alert(1)> Granada','España','Regional','6','sportsdb'),
        ])
        db.executemany('INSERT INTO competitions VALUES(?,?,?,?)', [('sp2','Segunda División','España','Europa'), ('grcup','Copa Granada','España','Andalucía')])
        db.executemany('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)', [
            ('gr-future','Granada CF','Málaga','Segunda División','Segunda División','España','2099-10-10','20:00','sportsdb'),
            ('gr-recent','Granada CF','Sevilla','Copa','Copa','España','2020-10-09','18:00','sportsdb'),
            ('not-gr','Málaga','Sevilla','Copa','Copa','España','2099-10-10','20:00','sportsdb'),
            ('fake','Equipo A','Granada CF','Copa','Copa','España','2099-10-10','21:00','seed estructural'),
        ])
    return path


def search(path, query, kind=''):
    return search_sports(path, query, kind, today='2026-10-09', excluded_names={'equipo a'})


def test_progressively_narrows_words_and_accents(sports_catalogue):
    broad=search(sports_catalogue,'gra','team')
    narrow=search(sports_catalogue,'GRANÁDA fem','team')
    assert len(broad['items'])>len(narrow['items'])==1
    assert narrow['items'][0]['label']=='Granada Femenino'
    assert search(sports_catalogue,'granada atletico','team')['items'][0]['label']=='Atlético Granada'
    assert search(sports_catalogue,'granada nicaragua','team')['items'][0]['value']=='@team:granada-ni'
    assert broad['complete'] and narrow['complete']


@pytest.mark.parametrize('query', ['', 'g', '   ', '%', '_', "' OR 1=1 --", 'inexistente'])
def test_empty_short_or_literal_queries_never_dump_catalogue(sports_catalogue, query):
    assert search(sports_catalogue,query)['items']==[]


def test_wildcards_are_literal_and_kinds_are_allowlisted(sports_catalogue):
    assert [x['label'] for x in search(sports_catalogue,'100%','team')['items']]==['100% Granada']
    assert search(sports_catalogue,'gra',"team; DROP TABLE teams")['kind']==''


def test_match_disambiguation_and_no_placeholder_or_private_payload(sports_catalogue):
    result=search(sports_catalogue,'granada','match')
    assert [x['value'] for x in result['items']]==['gr-future','gr-recent']
    assert '2099-10-10' in result['items'][0]['context']
    assert search(sports_catalogue,'granada malaga','match')['items'][0]['value']=='gr-future'
    assert all(set(x)=={'kind','value','label','context','href','legacy_values','saved'} for x in result['items'])


def test_competitions_share_normalized_matching(sports_catalogue):
    result=search(sports_catalogue,'division espana','league')
    assert [x['value'] for x in result['items']]==['sp2']
    assert result['items'][0]['href']=='/competition/sp2'


def test_cap_reports_more_without_claiming_all_results(sports_catalogue):
    result=search_sports(sports_catalogue,'gra','team',limit=2)
    assert len(result['items'])==2 and result['has_more']


def test_historical_timeout_preserves_already_found_upcoming_matches(sports_catalogue,monkeypatch):
    original_connect=sqlite3.connect
    class InterruptedHistory(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if 'FROM matches' in sql and 'match_date < ?' in sql:
                raise sqlite3.OperationalError('interrupted')
            return super().execute(sql,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**kw:original_connect(*a,**kw,factory=InterruptedHistory))
    result=search(sports_catalogue,'granada','match')
    assert result['status']=='PARTIAL' and not result['complete']
    assert [item['value'] for item in result['items']]==['gr-future']


def test_full_upcoming_list_does_not_scan_history(sports_catalogue,monkeypatch):
    with sqlite3.connect(sports_catalogue) as db:
        db.executemany('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?)',[(f'gr-{i}','Granada CF','Málaga','Segunda División','Segunda División','España','2099-10-10','20:00','sportsdb') for i in range(10)])
    db.close()
    original_connect=sqlite3.connect
    class NoHistory(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            assert 'match_date < ?' not in sql
            return super().execute(sql,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**kw:original_connect(*a,**kw,factory=NoHistory))
    result=search(sports_catalogue,'granada','match')
    assert len(result['items'])==8 and result['has_more'] and result['complete']


def test_read_only_and_unavailable_are_not_fabricated_empty_success(sports_catalogue, tmp_path):
    before=sports_catalogue.read_bytes()
    search(sports_catalogue,'granada')
    assert sports_catalogue.read_bytes()==before
    missing=tmp_path/'missing.db'
    assert search(missing,'granada')['status']=='UNAVAILABLE'
    assert not missing.exists()
    result=search_sports(sports_catalogue,'granada',budget_seconds=-1)
    assert not result['complete']


def test_saved_status_is_explicit_and_does_not_change_favorites(sports_catalogue):
    favorites=[{'kind':'team','value':'@team:granada-fem','label':'Granada Femenino'}]
    result=mark_saved(search(sports_catalogue,'granada','team'),favorites)
    assert [x['value'] for x in result['items'] if x['saved']]==['@team:granada-fem']
    assert all('legacy_values' not in x for x in result['items'])
    saved=search_saved(favorites,'fem')
    assert saved['items'][0]['href'].startswith('/favoritos?q=Granada+Femenino&kind=team')
    assert len(favorites)==1


def test_api_is_get_only_account_scoped_and_does_not_initialize(client, app_module, monkeypatch, sports_catalogue):
    monkeypatch.setattr(app_module,'DB_PATH',str(sports_catalogue))
    monkeypatch.setattr(app_module,'initialize_once',lambda: (_ for _ in ()).throw(AssertionError('search must not initialize')))
    monkeypatch.setattr(app_module,'current_session_user',lambda:None)
    before=sports_catalogue.read_bytes()
    result=client.get('/api/sports-search?q=granada&kind=team')
    assert result.status_code==200
    assert result.headers['Cache-Control']=='private, no-store'
    assert len(result.get_json()['items'])>=3
    assert client.get('/api/sports-search?q=granada&scope=saved').status_code==401
    favorites=[{'kind':'team','value':'Granada CF','label':'Granada CF'}]
    monkeypatch.setattr(app_module,'current_session_user',lambda:{'id':'owner'})
    def read(*,user_id):
        assert user_id=='owner'
        return favorites
    monkeypatch.setattr(app_module,'get_favorites',read)
    result=client.get('/api/sports-search?q=gra&scope=saved&user_id=someone-else')
    assert [x['label'] for x in result.get_json()['items']]==['Granada CF']
    assert sports_catalogue.read_bytes()==before
    # Invalid methods may be logged by the global CSRF/security middleware.
    assert client.post('/api/sports-search',json={'q':'gra'}).status_code in {403,405}


def test_scoped_favorites_distinguish_provider_ids_and_keep_legacy(app_module, monkeypatch, sports_catalogue):
    monkeypatch.setattr(app_module,'DB_PATH',str(sports_catalogue))
    monkeypatch.setattr(app_module,'get_favorites',lambda **kw:[{'kind':'team','value':'@team:granada-cf','label':'Granada CF'}])
    favorites=app_module.favorite_sets(user_id='owner')
    assert len(favorites['team_refs'])==1
    base={'home_team':'Granada CF','away_team':'Sevilla','home_team_id':'1','country':'España','source':'sportsdb'}
    assert app_module._scoped_team_favorite(base,favorites)
    assert not app_module._scoped_team_favorite({**base,'home_team_id':'4'},favorites)
    assert not app_module._scoped_team_favorite({**base,'home_team_id':'','country':'Nicaragua'},favorites)
    assert app_module._sports_match_favorite(base,favorites)
    assert app_module._sports_match_favorite(base,{'team':{'granada cf'}})
    assert app_module.team_lookup('granada-ni')['country']=='Nicaragua'


def test_selected_favorite_saves_and_removes_only_for_current_account(app_module, monkeypatch, sports_catalogue):
    monkeypatch.setattr(app_module,'DB_PATH',str(sports_catalogue))
    monkeypatch.setattr(app_module,'current_session_user',lambda:{'id':'owner'})
    monkeypatch.setattr(app_module,'_growth_maybe_activate_user',lambda **kw:None)
    with app_module.app.test_request_context('/favoritos',method='POST',data={'action':'add','kind':'team','value':'@team:granada-cf','label':'Granada CF','user_id':'other'}):
        app_module.session['user_id']='owner'
        assert app_module.favorites_page().status_code==302
    assert [x['value'] for x in app_module.get_favorites(user_id='owner')]==['@team:granada-cf']
    assert app_module.get_favorites(user_id='other')==[]
    with app_module.app.test_request_context('/favoritos',method='POST',data={'action':'remove','kind':'team','value':'@team:granada-cf'}):
        app_module.session['user_id']='other'
        app_module.favorites_page()
    assert len(app_module.get_favorites(user_id='owner'))==1
    app_module.remove_favorite('team','@team:granada-cf',user_id='owner')
    assert app_module.get_favorites(user_id='owner')==[]


@pytest.mark.parametrize('stored,expected', [([], '@team:granada-ni'), ([{'kind':'team','value':'@team:granada-ni'}], '@team:granada-ni'), ([{'kind':'team','value':'Granada CF'}], 'Granada CF')])
def test_team_detail_uses_selected_identity_and_can_remove_legacy_favorite(app_module,monkeypatch,sports_catalogue,stored,expected):
    monkeypatch.setattr(app_module,'DB_PATH',str(sports_catalogue))
    monkeypatch.setattr(app_module,'get_favorites',lambda **kw:stored)
    monkeypatch.setattr(app_module,'_sports_history_team_context',lambda team:{})
    monkeypatch.setattr(app_module,'_team_journey_matches',lambda *a,**kw:[])
    monkeypatch.setattr(app_module,'_sports_history_players_for_team',lambda team:[])
    monkeypatch.setattr(app_module,'_cached_players_for_team',lambda *a:[])
    monkeypatch.setattr(app_module,'get_picks',lambda **kw:[])
    detail=app_module.team_page_data('granada-ni')
    assert detail['team']['country']=='Nicaragua'
    assert detail['favorite_value']==expected
    assert detail['is_favorite'] is bool(stored)
