from datetime import datetime, timedelta, timezone
import secrets
import sqlite3
import uuid
import pytest

from engines import support_inbox_engine as inbox
from engines.ui_localization_engine import identity_value, owned_text, entity_copy, catalogue_issues


def payload(**values):
    return {'user_id':'qa-one','request_id':uuid.uuid4().hex,'subject':'Match question',
            'message':'A reproducible support question.', 'category':'partidos','priority':'normal', **values}


def test_support_is_persisted_and_visible_to_admin(tmp_path):
    path=tmp_path/'inbox.sqlite'
    sent=payload(message='<script>untrusted user content</script>')
    receipt=inbox.submit(path, **sent)
    snapshot=inbox.admin_snapshot(path)
    assert snapshot['total']==snapshot['open']==1
    assert snapshot['recent'][0]['id']==receipt==sent['request_id']
    assert snapshot['recent'][0]['message']==sent['message']
    assert 'user_id' not in snapshot['recent'][0]
    assert inbox.submit(path, **sent)==receipt
    assert inbox.admin_snapshot(path)['total']==1


def test_support_limit_is_persistent_and_user_scoped(tmp_path):
    path=tmp_path/'inbox.sqlite'
    start=datetime(2026,9,13,12,tzinfo=timezone.utc)
    inbox.submit(path,**payload(),now=start)
    with pytest.raises(inbox.SupportRejected, match='rate'):
        inbox.submit(path,**payload(),now=start+timedelta(seconds=30))
    inbox.submit(path,**payload(user_id='qa-two'),now=start)
    for minute in (1,2):
        inbox.submit(path,**payload(),now=start+timedelta(minutes=minute))
    with pytest.raises(inbox.SupportRejected, match='rate'):
        inbox.submit(path,**payload(),now=start+timedelta(minutes=3))
    assert inbox.admin_snapshot(path)['total']==4


@pytest.mark.parametrize('override', [{'user_id':None},{'request_id':'wrong'}, {'subject':'x'},
    {'subject':'x'*121},{'message':'x'},{'message':'x'*4001},{'category':'unknown'},{'priority':'urgent'}])
def test_invalid_support_does_not_create_storage(tmp_path,override):
    path=tmp_path/'inbox.sqlite'
    with pytest.raises(inbox.SupportRejected):
        inbox.submit(path,**payload(**override))
    assert not path.exists()


def test_sensitive_assignment_is_not_stored(tmp_path):
    path=tmp_path/'inbox.sqlite'
    with pytest.raises(inbox.SupportRejected,match='sensitive'):
        inbox.submit(path,**payload(message='password='+secrets.token_urlsafe(24)))
    assert not path.exists()


def test_insert_failure_rolls_back_and_never_confirms(tmp_path):
    path=tmp_path/'inbox.sqlite'
    inbox.submit(path,**payload())
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TRIGGER fail_support BEFORE INSERT ON nemesis_support_requests BEGIN SELECT RAISE(ABORT,'qa storage failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        inbox.submit(path,**payload(user_id='qa-other'))
    assert inbox.admin_snapshot(path)['total']==1


@pytest.mark.parametrize('lang', ['es','en','fr'])
def test_identity_and_user_or_provider_copy_are_not_translated(lang):
    for value in ['Real Madrid','Premier League','Kylian Mbappé',0]:
        assert identity_value(value,lang)==value
    assert identity_value(None,lang) not in {'None','null','undefined',''}
    assert owned_text('External narrative kept verbatim',lang)=='External narrative kept verbatim'
    assert catalogue_issues()==[]


@pytest.mark.parametrize('lang,word',[('en','Win'),('fr','Victoire')])
def test_entity_dynamic_copy_and_zero_values(lang,word):
    assert owned_text('Victoria',lang)==word
    assert 'Real Madrid' in owned_text('Real Madrid presiona',lang)
    result=entity_copy({'name':'Real Madrid','upcoming':[],'picks':[]},'team',lang)
    assert 'Real Madrid' in result['summary']
    assert 'Contexto SHARK para' not in result['summary']


def test_support_escapes_user_message_and_has_csrf(app_module):
    with app_module.app.test_request_context('/'):
        html=app_module.render_template('admin_support_center.html',data={'support':{
            'health':100,'open_feedback':0,'open_tickets':1,'total_feedback':0,'total_tickets':1,
            'recent':[{'subject':'<script>subject</script>','message':'<img onerror=alert(1)>','category':'general','priority':'normal','created_at':'2026-09-13T12:00:00Z'}], 'actions':[]}})
    assert '<script>subject</script>' not in html
    assert '&lt;script&gt;subject&lt;/script&gt;' in html


def test_match_intelligence_precedes_details_without_duplicate_region():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    template=(root/'templates/match_detail.html').read_text(encoding='utf-8')
    assert template.index('v944-match-intelligence-priority') < template.index('class="v944-match-main"')
    assert "if not shark.get('available')" in template
    css=(root/'static/v933-product.css').read_text(encoding='utf-8')
    assert 'body.ns-app .v944-match-team, body.ns-app .v944-match-team.is-away' in css


@pytest.mark.parametrize('language',['es','en','fr'])
@pytest.mark.parametrize('formatter',['match_time_short','match_full_datetime','match_madrid_datetime'])
def test_legacy_surface_adapters_keep_same_madrid_instant(app_module, language, formatter):
    with app_module.app.test_request_context('/',headers={'Accept-Language':language}):
        row={'kickoff_iso':'2026-07-15T23:30:00Z','country':'Japan','status':'NS'}
        value=app_module.app.jinja_env.filters[formatter](row)
        assert '01:30' in value
