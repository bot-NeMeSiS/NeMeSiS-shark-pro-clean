import json
import secrets
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engines.madrid_time_engine import madrid_greeting, format_madrid_client_datetime_label
from engines.ui_localization_engine import catalogue_issues, translate, valid_language


def test_catalogue_has_complete_languages_and_matching_placeholders():
    assert catalogue_issues() == []


@pytest.mark.parametrize('language,expected', [('es','Calendario'),('en','Calendar'),('fr','Calendrier')])
def test_explicit_ui_translation_only(language, expected):
    assert translate('Calendario', language) == expected
    assert translate('Paris Saint-Germain', language) == 'Paris Saint-Germain'
    assert translate('NeMeSiS', language) == 'NeMeSiS'
    assert translate('Una frase pendiente', language) == 'Una frase pendiente'


@pytest.mark.parametrize('language', ['es','en','fr'])
@pytest.mark.parametrize('hour,minute,slot', [(4,59,2),(5,0,0),(11,59,0),(12,0,1),(19,59,1),(20,0,2),(23,59,2),(0,0,2)])
def test_multilingual_greeting_uses_madrid(language, hour, minute, slot):
    expected = {'es':['Buenos días','Buenas tardes','Buenas noches'],
                'en':['Good morning','Good afternoon','Good evening'],
                'fr':['Bonjour','Bon après-midi','Bonsoir']}[language][slot]
    now = datetime(2026,7,15,hour,minute,tzinfo=ZoneInfo('Europe/Madrid')).astimezone(ZoneInfo('Asia/Tokyo'))
    greeting = madrid_greeting('Damian', now=now, locale=language)
    assert greeting == {'label':expected, 'name':'Damian'}


@pytest.mark.parametrize('date', ['2026-03-29T03:30:00+02:00','2026-10-25T02:30:00+01:00','2026-07-15T23:30:00Z'])
def test_locale_does_not_change_madrid_instant(date):
    labels = [format_madrid_client_datetime_label(date, locale=lang) for lang in ('es','en','fr')]
    assert len({label.rsplit(' · ',1)[1] for label in labels}) == 1


@pytest.mark.parametrize('language', ['de','../en','EN','fr<script>',None])
def test_unsupported_language_is_rejected(language):
    assert valid_language(language) is None


def test_locale_precedence_and_no_read_mutation(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'current_session_user', lambda: {'id':'qa-locale'})
    monkeypatch.setattr(app_module, '_load_user_intelligence_preferences', lambda _id: {'language':'fr'})
    with app_module.app.test_request_context('/app', headers={'Accept-Language':'en'}):
        app_module.session['ui_locale']='es'
        assert app_module.current_ui_locale() == 'fr'
    monkeypatch.setattr(app_module, 'current_session_user', lambda: None)
    with app_module.app.test_request_context('/app', headers={'Accept-Language':'en'}):
        assert app_module.current_ui_locale() == 'en'
    with app_module.app.test_request_context('/app', headers={'Accept-Language':'ja'}):
        assert app_module.current_ui_locale() == 'es'


def test_language_post_requires_csrf_and_sets_restricted_cookie(app_module, client, monkeypatch):
    monkeypatch.setattr(app_module, 'current_session_user', lambda: None)
    assert client.post('/preferences/language', data={'language':'fr'}).status_code == 403
    with client.session_transaction() as session:
        token = app_module.generate_csrf_token(session)
    response = client.post('/preferences/language', data={'language':'fr','csrf_token':token,'next':'//evil.invalid'})
    assert response.status_code == 303
    assert response.location == '/cliente-login'
    cookie = next(h for h in response.headers.getlist('Set-Cookie') if h.startswith('nemesis_locale='))
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie and 'Max-Age=31536000' in cookie
    with client.session_transaction() as session:
        session.clear()
    with app_module.app.test_request_context('/', headers={'Cookie':'nemesis_locale=fr'}):
        assert app_module.current_ui_locale() == 'fr'


def test_preference_write_preserves_unrelated_profile_data(app_module, monkeypatch, tmp_path):
    path = tmp_path / 'language.sqlite'
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    user = {'id':'qa-'+secrets.token_hex(8)}
    profile_id = app_module._user_intelligence_profile_id(user['id'])
    conn = connect()
    conn.execute('CREATE TABLE client_profiles(id TEXT PRIMARY KEY,name TEXT,preferences_json TEXT,created_at TEXT,updated_at TEXT,favorite_teams_json TEXT)')
    conn.execute('INSERT INTO client_profiles VALUES(?,?,?,?,?,?)', (profile_id,'Kept name',json.dumps({'history_enabled':False,'language':'es'}),'before','before','["kept"]'))
    conn.commit()
    conn.close()
    monkeypatch.setattr(app_module,'db',connect)
    monkeypatch.setattr(app_module,'current_session_user',lambda:user)
    with app_module.app.test_request_context('/preferences/language',method='POST',data={'language':'fr','next':'/calendar?date=2026-07-16&team=Paris'}):
        response = app_module.update_ui_language()
        assert response.status_code == 303
        assert response.location == '/calendar?date=2026-07-16&team=Paris'
    conn=connect()
    row=dict(conn.execute('SELECT * FROM client_profiles').fetchone())
    conn.close()
    assert row['name']=='Kept name' and row['created_at']=='before'
    assert row['favorite_teams_json']=='["kept"]'
    assert json.loads(row['preferences_json']) == {'history_enabled':False,'language':'fr'}


def test_translation_parameters_are_escaped_by_jinja(app_module):
    with app_module.app.test_request_context('/'):
        html=app_module.app.jinja_env.from_string('{{ ui("Plan {plan}", plan=value) }}').render(value='<script>alert(1)</script>')
        assert '<script>' not in html
        assert '&lt;script&gt;' in html


def test_language_selector_does_not_suppress_auth_csrf(app_module, client, monkeypatch):
    from html.parser import HTMLParser
    class Forms(HTMLParser):
        def __init__(self):
            super().__init__()
            self.forms = []
            self.current = None
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "form":
                self.current = {"action": attrs.get("action"), "tokens": []}
                self.forms.append(self.current)
            if tag == "input" and self.current is not None and attrs.get("name") == "csrf_token":
                self.current["tokens"].append(attrs.get("value"))
        def handle_endtag(self, tag):
            if tag == "form":
                self.current = None
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    response = client.get("/cliente-login")
    parser = Forms()
    parser.feed(response.get_data(as_text=True))
    by_action = {form["action"]: form["tokens"] for form in parser.forms}
    for action in ("/cliente-login", "/preferences/language"):
        assert len(by_action[action]) == 1 and by_action[action][0]


@pytest.mark.parametrize('language', ['en','fr'])
@pytest.mark.parametrize('kind', ['FULLTIME_SUMMARY','PREMATCH_SUMMARY','STALE_SUMMARY','LIVE_SUMMARY','POSTPONED_SUMMARY'])
@pytest.mark.parametrize('confirmed', [False, True])
def test_summary_locale_preserves_canonical_state_and_unknown_score(language, kind, confirmed):
    from copy import deepcopy
    from engines.ui_localization_engine import match_summary
    context = {'summaries':{'items':[{'type':kind,'text':'original'}]},
               'teams':{'home':{'name':'Paris Saint-Germain'},'away':{'name':'Club Norte'}},
               'score':{'confirmed':confirmed,'label':'0-0'}}
    original = deepcopy(context)
    rendered = match_summary(context, language)
    assert context == original
    if kind in {'FULLTIME_SUMMARY','STALE_SUMMARY','LIVE_SUMMARY'}:
        assert ('0-0' in rendered) is confirmed
    if kind == 'STALE_SUMMARY':
        assert ('not confirmed' in rendered if language == 'en' else "n'est pas confirmée" in rendered)
    if kind == 'POSTPONED_SUMMARY':
        assert ('postponed' in rendered if language == 'en' else 'reporté' in rendered)
        assert '0-0' not in rendered
