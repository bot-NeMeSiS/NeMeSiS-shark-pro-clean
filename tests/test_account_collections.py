"""Account-scoped GET organization and honest, bounded backup presentation."""
from copy import deepcopy

import pytest

from engines.account_collection_views import favorite_collection, backup_observation
from engines.ui_localization_engine import catalogue_issues


FAVORITES = [
    {'kind': 'team', 'value': 'team-1', 'label': 'Atlético Madrid'},
    {'kind': 'league', 'value': 'league-1', 'label': 'Liga Madrid'},
    {'kind': 'match', 'value': 'match-1', 'label': 'Madrid · Sevilla'},
]


@pytest.mark.parametrize('query,kind,labels', [
    ('MADRID atletico', '', ['Atlético Madrid']),
    ('madrid', 'league', ['Liga Madrid']),
    ('team-1', '', ['Atlético Madrid']),
    ('inexistente', '', []), ('', 'unknown', [f['label'] for f in FAVORITES]),
])
def test_collection_preserves_order_and_does_not_change_saved_data(query, kind, labels):
    original = deepcopy(FAVORITES)
    result = favorite_collection(FAVORITES, query, kind)
    assert [item['label'] for item in result['items']] == labels
    assert result['total'] == 3 and FAVORITES == original
    assert len(favorite_collection(FAVORITES, 'x' * 1000)['query']) == 90


@pytest.mark.parametrize('result,label', [
    ({'ok':False,'failure_stage':'INTEGRITY','error':'secret-provider-payload'}, 'Último intento sin copia creada'),
    ({'ok':True,'backup_created':False,'status':'SKIPPED_NOT_DUE'}, 'Última ejecución sin copia nueva'),
    ({'ok':True,'backup_created':True}, 'Creación automática registrada'),
    ({'ok':False,'backup_created':True}, 'Copia creada con incidencias'),
    ({'ok':True}, 'Sin observación disponible'),
    (None, 'Sin observación disponible'),
])
def test_backup_evidence_never_invents_success_or_leaks_diagnostics(result, label):
    view = backup_observation({'time':'2026-10-09T04:30:00+02:00','result':result})
    assert view['label'] == label
    assert view['time'].endswith('+02:00')
    assert 'secret-provider-payload' not in str(view)
    assert backup_observation({'time':'<script>', 'result':[]})['time'] == ''
    assert backup_observation([])['tone'] == 'unknown'


def forbidden(*args, **kwargs):
    raise AssertionError('GET presentation invoked an operational function')


def test_favorites_search_is_account_scoped_and_read_only(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'current_session_user', lambda: {'id':'customer-one'})
    def favorites(*, user_id):
        assert user_id == 'customer-one'
        return FAVORITES
    monkeypatch.setattr(app_module,'get_favorites',favorites)
    monkeypatch.setattr(app_module,'favorite_feed_full',lambda **kw: {'matches':[],'live':[],'picks':[]})
    monkeypatch.setattr(app_module,'favorite_insights',lambda **kw: {'by_kind':{key:[] for key in ('team','league','match')}})
    for name in ('dashboard_data','add_favorite','remove_favorite'):
        monkeypatch.setattr(app_module,name,forbidden)
    with app_module.app.test_request_context('/favoritos?q=madrid&kind=team&user_id=other'):
        html = app_module.favorites_page()
    assert 'Atlético Madrid' in html and 'Liga Madrid' not in html
    assert '1 favorito encontrado' in html and 'Los filtros solo afectan' in html
    assert 'method="get" action="/favoritos#saved-favorites"' in html
    monkeypatch.setattr(app_module,'current_session_user',lambda:None)
    with app_module.app.test_request_context('/favoritos'):
        assert app_module.favorites_page().location == '/cliente-login'


@pytest.mark.parametrize('language', ['es','en','fr'])
def test_admin_backups_renders_recorded_failure_without_running_work(app_module, monkeypatch, language):
    monkeypatch.setattr(app_module,'is_admin_session',lambda:True)
    monkeypatch.setattr(app_module,'list_backups',lambda:[])
    monkeypatch.setattr(app_module,'backup_dir',lambda:'/synthetic/backups')
    monkeypatch.setattr(app_module,'automation_get_bounded',lambda *a: {
        'time':'2026-10-09T04:30:00+02:00', 'result':{'ok':False,'failure_stage':'INTEGRITY','error':'RAW_SECRET'}})
    for name in ('dashboard_data','create_database_backup','restore_database_backup'):
        monkeypatch.setattr(app_module,name,forbidden)
    with app_module.app.test_request_context('/admin/backups',headers={'Accept-Language':language}):
        html=app_module.admin_backups_page()
    assert 'RAW_SECRET' not in html
    assert 'data-tone="warning"' in html
    assert 'Sin operaciones registradas' not in html
    assert catalogue_issues() == []
    monkeypatch.setattr(app_module,'is_admin_session',lambda:False)
    with app_module.app.test_request_context('/admin/backups'):
        assert app_module.admin_backups_page().location == '/admin-login?next=/admin/backups'
