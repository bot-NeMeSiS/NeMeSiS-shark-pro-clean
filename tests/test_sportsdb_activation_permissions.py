"""Operational consent is not a licence. Synthetic stores; no external requests."""
from html.parser import HTMLParser
from pathlib import Path
import sqlite3

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from engines import sportsdb_highlights_engine as media
from engines.highlight_review_engine import ReviewError, decide_highlight, review_snapshot
from engines.postmatch_store import Store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('External access forbidden in permissions tests')
    monkeypatch.setattr('socket.socket.connect', reject)
    monkeypatch.setattr('urllib.request.urlopen', reject)


@pytest.fixture
def catalogue(tmp_path):
    path = tmp_path / 'isolated.sqlite'
    media.ensure_sportsdb_highlights_schema(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE matches(id TEXT,external_id TEXT,source TEXT,home_team TEXT,away_team TEXT,match_date TEXT,league_id TEXT,league_name TEXT)')
        conn.execute('INSERT INTO matches VALUES(?,?,?,?,?,?,?,?)',
                     ('m1','sportsdb-123','TheSportsDB API','Norte','Sur','2026-09-20','1','Liga QA'))
        media._upsert_highlight(conn, {'idEvent':'123','dateEvent':'2026-09-20',
            'strHomeTeam':'Norte','strAwayTeam':'Sur','strLeague':'Liga QA','idLeague':'1',
            'strVideo':'https://www.youtube.com/watch?v=isolatedQA1'})
    return path


def values(path, decision='LINK_ONLY', evidence='https://example.org/specific-video-licence'):
    row = review_snapshot(path)['items'][0]
    return row['id'], {'decision':decision,'review_token':row['review_token'],
        'evidence_url':evidence,'attribution':'Synthetic test source',
        'basis':'Synthetic documented permission for this exact clip and APP only.',
        'rights_status':'LICENSED','confirmed':'1'}


def rights(path):
    with sqlite3.connect(path) as conn:
        return conn.execute('SELECT rights_status,commercial_use_status FROM sportsdb_match_highlights').fetchall()


@pytest.mark.parametrize('decision', ['LINK_ONLY', 'EMBED'])
@pytest.mark.parametrize('evidence', [
    'https://www.thesportsdb.com',
    'https://www.thesportsdb.com/docs_terms_of_use.php',
    'https://www.thesportsdb.com/docs_terms_of_use',
    'https://www.thesportsdb.com/documentation#premium',
    'https://www.thesportsdb.com/docs_api',
    'https://www.thesportsdb.com/api.php',
    'https://www.thesportsdb.com/pricing',
    'https://www.thesportsdb.com/user/synthetic',
    'https://www.thesportsdb.com/event/123',
    'https://www.thesportsdb.com/event.php?e=123',
    'https://www.thesportsdb.com/api/v1/json/SYNTHETIC/lookup.php',
    'https://www.thesportsdb.com/%64ocs_terms_of_use.php/',
])
def test_subscription_or_metadata_is_not_video_rights(catalogue, decision, evidence):
    before = catalogue.read_bytes()
    hid, form = values(catalogue, decision, evidence)
    with pytest.raises(ReviewError, match='no acreditan los derechos'):
        decide_highlight(catalogue, hid, form, actor='test-admin')
    assert catalogue.read_bytes() == before
    assert not review_snapshot(catalogue)['items'][0]['can_display']


@pytest.mark.parametrize('declared', ['LICENSED','OWNED','PROVIDER_ALLOWED','OPEN_LICENSE_ALLOWED','ATTRIBUTION_REQUIRED'])
def test_renaming_rights_does_not_make_a_subscription_evidence(catalogue, declared):
    hid, form = values(catalogue, evidence='https://www.thesportsdb.com/pricing')
    form['rights_status'] = declared
    with pytest.raises(ReviewError):
        decide_highlight(catalogue, hid, form, actor='test-admin')


def test_specific_documented_review_remains_app_only(catalogue):
    hid, form = values(catalogue)
    assert decide_highlight(catalogue, hid, form, actor='test-admin')['ok']
    with sqlite3.connect(catalogue) as conn:
        row = conn.execute('SELECT rights_status,embed_policy,allowed_channels_json FROM sportsdb_match_highlights').fetchone()
    assert row == ('LICENSED','LINK_ONLY','["APP"]')
    assert review_snapshot(catalogue)['items'][0]['can_display']


@pytest.mark.parametrize('decision', ['BLOCKED','REVIEW_REQUIRED'])
def test_keep_unpublished_needs_no_invented_evidence(catalogue, decision):
    hid, form = values(catalogue, decision)
    for key in ('evidence_url','attribution','basis','confirmed','rights_status'):
        form.pop(key, None)
    assert decide_highlight(catalogue, hid, form, actor='test-admin')['ok']
    assert not review_snapshot(catalogue)['items'][0]['can_display']


def test_activation_never_certifies_stored_video(catalogue):
    before = rights(catalogue)
    store = Store(catalogue)
    store.configure(enabled=True, sources=['thesportsdb'], daily_limit=60,
                    actor='test-admin', confirmed=True)
    assert store.config()['enabled'] is True
    assert rights(catalogue) == before
    assert not review_snapshot(catalogue)['items'][0]['can_display']
    with sqlite3.connect(catalogue) as conn:
        assert conn.execute('SELECT COUNT(*) FROM postmatch_source_budget').fetchone()[0] == 0


def test_unconfirmed_activation_still_fails_without_writes(catalogue):
    before = catalogue.read_bytes()
    with pytest.raises(ValueError):
        Store(catalogue).configure(enabled=True, sources=['thesportsdb'],
                                  daily_limit=60, actor='test-admin', confirmed=False)
    assert catalogue.read_bytes() == before


class Inputs(HTMLParser):
    def __init__(self):
        super().__init__(); self.inputs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'input': self.inputs.append(dict(attrs))


def template_env():
    env = Environment(loader=FileSystemLoader(ROOT/'templates'), autoescape=select_autoescape())
    env.globals.update(csrf_token=lambda:'isolated-token')
    env.filters['madrid_datetime_label'] = str
    return env


@pytest.mark.parametrize('enabled', [False, True])
def test_notice_requests_action_not_legal_self_certification(enabled):
    snapshot = {'state':'ACTIVE' if enabled else 'NOT_INITIALIZED',
        'config':{'enabled':enabled,'sources':['thesportsdb'] if enabled else [],'daily_limit':60},
        'budget':[],'jobs':[],'observations':[]}
    html = template_env().get_template('partials/postmatch_workers.html').render(postmatch=snapshot)
    parsed = Inputs(); parsed.feed(html)
    consent = [i for i in parsed.inputs if i.get('name') == 'confirmed']
    assert len(consent) == 1 and 'checked' not in consent[0]
    assert 'name="csrf_token"' in html
    assert 'He verificado que la cuenta' not in html
    assert 'Quiero activar las consultas' in html and 'no certifica licencias' in html
    assert 'Este formulario no comprueba tu facturación' in html
    assert 'https://www.thesportsdb.com/docs_terms_of_use.php' in html
    assert 'API-Football tiene condiciones propias' in html


@pytest.mark.parametrize('source,expected', [('thesportsdb',True),('api_football',False),('',False)])
def test_visible_statistics_credit_only_the_observed_source(source, expected):
    text = (ROOT/'templates/match_detail.html').read_text()
    fragment = text.split("{% for metric in recovery.get('items') %}",1)[1].split('{% endfor %}',1)[0]
    html = template_env().from_string(fragment).render(metric={
        'source':source,'label':'Córners','home':'3','away':'0','reference':'Synthetic event',
        'scope':'REGULATION'})
    assert ('href="https://www.thesportsdb.com"' in html) is expected
    assert '3 / 0' in html


def test_collector_copy_does_not_claim_shared_daily_budget():
    text = (ROOT/'templates/admin_highlights_review.html').read_text(encoding='utf-8')
    assert 'como máximo dos peticiones' not in text
    assert 'hasta 12 peticiones por ventana de seis horas' in text
    assert 'no está incluido en las 60 consultas' in text
    assert 'Para mantener pendiente o bloquear no necesitas declarar permisos' in text
