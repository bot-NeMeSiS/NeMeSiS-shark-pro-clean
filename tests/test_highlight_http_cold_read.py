"""Real Flask request hooks, templates and isolated SQLite; never provider access."""
import sqlite3
import pytest


@pytest.mark.parametrize('prefix',['/highlight/','/resumen/','/resumenes/'])
@pytest.mark.parametrize('storage,expected', [('not_initialized',404),('missing_db',503),('read_error',503)])
@pytest.mark.parametrize('role',[None,'PRO','ADMIN'])
def test_cold_http_detail_does_not_initialize_or_misclassify_catalogue(app_module, monkeypatch, tmp_path, prefix, storage, expected, role):
    path = tmp_path / 'catalogue.sqlite'
    if storage == 'not_initialized':
        with sqlite3.connect(path) as conn:
            conn.execute('CREATE TABLE sentinel(value TEXT)')
    elif storage == 'read_error':
        path.write_bytes(b'NOT A SQLITE DATABASE')
    before = path.read_bytes() if path.exists() else None
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', False)
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', '')
    calls = []
    def forbidden(*_a, **_k):
        calls.append('unexpected_initializer_or_dashboard')
        raise AssertionError('A media GET must not initialize storage or build the sports dashboard')
    monkeypatch.setattr(app_module, 'initialize_once', forbidden)
    monkeypatch.setattr(app_module, 'seed_core', forbidden)
    monkeypatch.setattr(app_module, 'dashboard_data', forbidden)
    # Isolate storage semantics from administrative pause. The visibility guard
    # and every other before/after-request hook still execute normally.
    monkeypatch.setattr(app_module, 'admin_operational_settings', lambda:{'highlights_enabled':True, 'settings_readable':True})
    client = app_module.app.test_client()
    if role:
        with client.session_transaction() as session:
            session.update(user_id='synthetic', user_role=role, membership=role)
    response = client.get(prefix+'v929-id-inexistente')
    assert calls == [], calls
    assert response.status_code == expected
    assert (path.read_bytes() if path.exists() else None) == before
    html = response.get_data(as_text=True)
    assert ('No se pudo comprobar este resumen' in html) is (expected == 503)
    assert 'Traceback' not in html


@pytest.mark.parametrize('prefix',['/highlight/','/resumen/','/resumenes/'])
@pytest.mark.parametrize('role',[None,'PRO','ADMIN'])
def test_authorized_http_video_renders_without_startup_or_dashboard(app_module, monkeypatch, tmp_path, prefix, role):
    from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema
    path = tmp_path / 'catalogue.sqlite'
    ensure_sportsdb_highlights_schema(path)
    with sqlite3.connect(path) as conn:
        conn.execute('''INSERT INTO sportsdb_match_highlights
            (id,match_id,video_url,rights_status,commercial_use_status,source,updated_at)
            VALUES(?,?,?,?,?,?,?)''',('synthetic','match-synthetic',
            'https://www.youtube.com/watch?v=SYNTHETIC_QA','LICENSED','ALLOWED',
            'Synthetic QA','2026-09-30T20:00:00+00:00'))
    before = path.read_bytes()
    monkeypatch.setattr(app_module, 'DB_PATH', str(path))
    monkeypatch.setattr(app_module, 'APP_INITIALIZED', False)
    monkeypatch.setattr(app_module, '_SEEDED_DB_PATH', '')
    calls = []
    def forbidden(*_a, **_k):
        calls.append('initializer_or_dashboard')
        raise AssertionError('A video GET must not seed or initialize the sports dashboard')
    for name in ('initialize_once','seed_core','dashboard_data'):
        monkeypatch.setattr(app_module, name, forbidden)
    client = app_module.app.test_client()
    if role:
        with client.session_transaction() as session:
            session.update(user_id='synthetic',user_role=role,membership=role)
    response = client.get(prefix+'synthetic')
    assert calls == []
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Abrir fuente' in html
    assert 'https://www.youtube.com/watch?v=SYNTHETIC_QA' in html
    assert '<iframe' not in html
    assert path.read_bytes() == before


@pytest.mark.parametrize('prefix',['/highlight/','/resumen/','/resumenes/'])
def test_administrative_pause_covers_all_video_aliases(app_module, monkeypatch, prefix):
    monkeypatch.setattr(app_module,'admin_operational_settings',lambda:{'highlights_enabled':False, 'settings_readable':True})
    calls = []
    def unexpected(*_a, **_k):
        calls.append('read')
        raise AssertionError('Paused content must not be read')
    monkeypatch.setattr(app_module, 'v769_get_highlight_snapshot', unexpected)
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session.update(user_id='synthetic',user_role='PRO',membership='PRO')
    response = client.get(prefix+'synthetic')
    assert response.status_code == 200
    assert calls == []
    assert '<iframe' not in response.get_data(as_text=True)


def test_highlight_detail_renders_cached_factual_postmatch_recap(app_module, monkeypatch):
    monkeypatch.setattr(app_module, 'admin_operational_settings', lambda:{'highlights_enabled':True, 'settings_readable':True})
    monkeypatch.setattr(app_module, 'v769_get_highlight_snapshot', lambda _hid: {
        'ok': True,
        'read_state': 'VERIFIED',
        'highlight': {
            'id': 'recap-highlight',
            'match_id': 'match-42',
            'match_label': 'Local vs Visitante',
            'competition_label': 'Liga QA',
            'event_date_label': '03/10/2026',
            'source_label': 'TheSportsDB · YouTube',
            'client_status': 'AUTHORIZED',
            'provider': 'YouTube',
            'safe_url': 'https://www.youtube.com/watch?v=SYNTHETIC_QA',
            'embed_url': 'https://www.youtube-nocookie.com/embed/SYNTHETIC_QA',
            'can_embed': True,
            'can_link': True,
            'rights_note': 'LICENSED',
            'match_url': '/match/match-42',
        },
    })
    monkeypatch.setattr(app_module, 'v769_highlight_match_context', lambda match_id: {
        'score': {'confirmed': True, 'label': '2 - 1'},
        'summaries': {
            'contract': 'NEMESIS-FACTUAL-MATCH-SUMMARIES-V1',
            'unsupported_claims': 0,
            'items': [
                {'type': 'FULLTIME_SUMMARY', 'text': 'Local y Visitante finalizaron 2 - 1.', 'evidence': ['match_status', 'score']},
                {'type': 'EVENTS_SUMMARY', 'text': 'La cronología contiene 2 eventos confirmados.', 'evidence': ['canonical_timeline']},
            ],
        },
        'event_summary': {
            'available': True,
            'count': 2,
            'items': [
                {'minute_label': "12'", 'label': 'Gol', 'team': 'Local', 'player': 'Jugador A', 'detail': ''},
                {'minute_label': "70'", 'label': 'Tarjeta amarilla', 'team': 'Visitante', 'player': 'Jugador B', 'detail': ''},
            ],
        },
        'statistics': {
            'available': True,
            'item_count': 2,
            'items': [
                {'label': 'Posesión', 'home': '55%', 'away': '45%'},
                {'label': 'Tiros a puerta', 'home': '6', 'away': '3'},
            ],
        },
        'diagnostics': {'external_calls': 0},
    } if match_id == 'match-42' else {})

    response = app_module.app.test_client().get('/resumen/recap-highlight')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'Así terminó el partido' in html
    assert 'Local y Visitante finalizaron 2 - 1.' in html
    assert 'La cronología contiene 2 eventos confirmados.' in html
    assert 'Jugador A' in html
    assert 'Posesión' in html and '55%' in html and '45%' in html
    assert '0 llamadas de IA generativa' in html
    assert '0 llamadas externas durante la lectura' in html
    assert '<iframe' not in html
