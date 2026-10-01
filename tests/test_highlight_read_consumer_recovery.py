"""Recovery from archived PR60 against modern contracts; synthetic/offline only."""
from jinja2 import DictLoader, ChoiceLoader
import pytest


def test_context_unavailable_is_unknown_and_sanitized(app_module, monkeypatch):
    def fail(*_a, **_k):
        raise RuntimeError('PRIVATE-PATH-AND-CREDENTIAL')
    monkeypatch.setattr(app_module, 'sportsdb_highlights_summary', fail)
    result = app_module.v766_highlights_context()
    assert result['ok'] is False and result['read_state'] == 'READ_UNAVAILABLE'
    assert all(result[k] is None for k in ('stored_media_total', 'highlights_total', 'linked_matches'))
    assert 'PRIVATE-PATH' not in str(result)


def test_unavailable_catalogue_does_not_guess_pending_count(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'v766_highlights_context', lambda **_k: {'ok':False,'read_state':'READ_UNAVAILABLE'})
    monkeypatch.setattr(app_module, 'v769_pending_highlight_snapshot', lambda **_k: pytest.fail('Unexpected pending query'))
    result = app_module.v769_highlights_content_center({}, {'membership':'FREE'})
    assert result['counts']['videos'] is None and result['counts']['pending'] is None
    assert 'Disponibilidad sin comprobar' in result['headline']


def test_verified_empty_catalogue_keeps_real_zero(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'v766_highlights_context', lambda **_k: {'ok':True,'read_state':'VERIFIED','stored_media_total':0})
    monkeypatch.setattr(app_module, 'v769_pending_highlight_snapshot', lambda **_k: {'ok':True,'read_state':'VERIFIED','matches':[]})
    result = app_module.v769_highlights_content_center({}, {'membership':'FREE'})
    assert result['counts']['videos'] == 0 and result['counts']['pending'] == 0


def test_known_empty_batch_does_not_query_per_match(app_module, monkeypatch):
    calls=[]
    monkeypatch.setattr(app_module, 'sportsdb_highlights_map', lambda *_a, **_k: calls.append(1) or {'ok':True,'read_state':'VERIFIED','map':{}})
    monkeypatch.setattr(app_module, 'sportsdb_highlights_for_match', lambda *_a, **_k: pytest.fail('N+1 read'))
    result = app_module.v766_enrich_matches_with_highlights([{'id':'a'},{'id':'b'}])
    assert calls == [1]
    assert all(row['highlight_count'] == 0 for row in result)


def test_batch_failure_preserves_unknown(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'sportsdb_highlights_map', lambda *_a, **_k: {'ok':False,'read_state':'READ_UNAVAILABLE','map':{}})
    result = app_module.v766_enrich_matches_with_highlights([{'id':'a'}])[0]
    assert result['has_highlights'] is None and result['highlight_count'] is None


def test_admin_pause_is_not_removed_by_historical_recovery(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'is_admin_session', lambda:False)
    monkeypatch.setattr(app_module, 'admin_operational_settings', lambda:{'highlights_enabled':False})
    monkeypatch.setattr(app_module, 'sportsdb_highlights_summary', lambda *_a: pytest.fail('Paused read'))
    with app_module.app.test_request_context('/highlights'):
        context = app_module.v766_highlights_context()
        badge = app_module.v766_apply_match_highlight_badge({'id':'a'})
    assert context['status'] == 'DISABLED_BY_ADMIN'
    assert badge['has_highlights'] is False and badge['client_highlight_label'] == ''


def test_match_video_query_uses_only_local_identity(app_module, monkeypatch):
    seen=[]
    monkeypatch.setattr(app_module, 'db_table_exists', lambda *_a:True)
    monkeypatch.setattr(app_module, 'rows', lambda sql, params: seen.append(params) or [])
    app_module._cached_match_media({'id':'local-a','external_id':'foreign-b'})
    assert seen == [('local-a',6)]


def test_legacy_map_and_detail_do_not_initialize_storage(app_module, tmp_path, monkeypatch):
    missing=tmp_path/'absent.sqlite'
    monkeypatch.setattr(app_module, 'DB_PATH', str(missing))
    assert app_module.v766_highlight_map(['a']) == {}
    assert app_module.v769_get_highlight_by_id('not-present') == {}
    assert not missing.exists()


@pytest.mark.parametrize('can_embed',[False,True])
def test_standalone_detail_shares_current_opt_in_player(app_module, monkeypatch, can_embed):
    env = app_module.app.jinja_env.overlay()
    env.loader = ChoiceLoader([DictLoader({'base.html':'{% block content %}{% endblock %}'}), env.loader])
    h={'match_label':'Synthetic A vs B','title':'Synthetic clip','can_embed':can_embed,
       'safe_url':'https://www.youtube.com/watch?v=synthetic','embed_url':'https://www.youtube-nocookie.com/embed/synthetic'}
    with app_module.app.test_request_context('/highlight/synthetic'):
        html=env.get_template('highlight_detail.html').render(data={'highlight':h})
    assert '<iframe' not in html
    assert ('data-video-activate=' in html) is can_embed
    assert 'Abrir fuente' in html
    assert 'postmatch-media.js' in html


def test_detail_unreadable_catalogue_is_not_a_missing_video(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'v769_get_highlight_snapshot', lambda _id: {'ok':False,'read_state':'READ_UNAVAILABLE'})
    monkeypatch.setattr(app_module, 'dashboard_data', lambda *_a, **_k: pytest.fail('Do not build a dashboard after a failed catalogue read'))
    monkeypatch.setattr(app_module, 'render_template', lambda *_a, **_k: 'unavailable')
    with app_module.app.test_request_context('/highlight/unknown'):
        result = app_module.highlight_detail_page('unknown')
    assert result == ('unavailable',503)


def test_detail_known_missing_video_stays_not_found(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'v769_get_highlight_snapshot', lambda _id: {'ok':True,'read_state':'VERIFIED','highlight':{}})
    monkeypatch.setattr(app_module, 'dashboard_data', lambda *_a, **_k: {})
    monkeypatch.setattr(app_module, 'render_template', lambda *_a, **_k: 'missing')
    with app_module.app.test_request_context('/highlight/unknown'):
        result = app_module.highlight_detail_page('unknown')
    assert result == ('missing',404)
