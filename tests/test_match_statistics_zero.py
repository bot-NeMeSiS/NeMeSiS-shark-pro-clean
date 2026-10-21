from engines.match_context_engine import _real_statistics, _statistics_refresh_context


def test_persisted_zero_statistics_remain_available_and_localized():
    stats = _real_statistics({}, {'is_finished': True}, {
        'available': True, 'source': 'test-provider', 'items': [
            {'label': 'Shots on Target', 'home': 0, 'away': 0},
            {'label': 'Corners', 'home': None, 'away': 0},
        ]})
    assert stats['available']
    assert stats['items'][0]['label'] == 'Tiros a puerta'
    assert stats['items'][0]['home'] == stats['items'][0]['away'] == '0'
    assert stats['items'][1]['label'] == 'Córners'
    assert stats['items'][1]['home'] == 'No disponible'
    assert stats['items'][1]['away'] == '0'


def test_live_zero_statistics_are_not_confused_with_missing_values():
    stats = _real_statistics({'provider': 'test-provider', 'stat_cards': [
        {'label': 'Shots', 'home': 0, 'away': 0},
        {'label': 'Fouls', 'home': None, 'away': ''},
    ]}, {})
    assert stats['available']
    assert stats['item_count'] == 1
    assert stats['items'][0]['home'] == '0'


def test_boolean_flags_do_not_become_sport_statistics():
    stats = _real_statistics({}, {}, {'available': True, 'items': [
        {'label': 'Shots', 'home': False, 'away': True},
    ]})
    assert not stats['available']


def test_provider_stat_keys_are_shown_in_spanish_without_underscores():
    stats = _real_statistics({'provider': 'API-Football', 'stat_cards': [
        {'key': 'free_kicks', 'label': 'Free Kicks', 'home': 9, 'away': 12},
        {'key': 'expected_goals', 'label': 'expected_goals', 'home': '1.20', 'away': '0.80'},
    ]}, {})

    assert [item['label'] for item in stats['items']] == ['Tiros libres', 'Goles esperados']


def test_zero_statistics_reach_the_rendered_match_panel(app_module):
    stats = _real_statistics({}, {}, {'available': True, 'source': 'test', 'items': [
        {'label': 'Shots on Target', 'home': 0, 'away': 0},
    ]})
    with app_module.app.test_request_context():
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/v944_match_center.html' import stats_panel %}{{ stats_panel(context) }}")
        rendered = template.render(context={'statistics': stats, 'teams': {
            'home': {'name': 'Equipo local'}, 'away': {'name': 'Equipo visitante'},
        }})
    assert rendered.count('role="cell">0</span>') == 2
    assert 'Tiros a puerta' in rendered
    assert 'Equipo local' in rendered and 'Equipo visitante' in rendered


def test_persisted_statistics_keep_only_their_own_valid_capture_clocks():
    from engines.match_context_engine import _real_statistics

    home_clock = "2026-10-18T10:01:00Z"
    saved_clock = "2026-10-18T10:08:00Z"
    stats = _real_statistics({}, {}, {
        "available": True,
        "source": "API-Football",
        "updated_at": saved_clock,
        "items": [{
            "key": "fouls",
            "label": "Faltas",
            "home": 5,
            "away": 8,
            "home_captured_at": home_clock,
            "away_captured_at": "invalid-clock",
        }],
    })

    assert stats["snapshot_kind"] == "persisted"
    assert stats["updated_at"] == saved_clock
    assert stats["items"][0]["home_captured_at"] == home_clock
    assert stats["items"][0]["away_captured_at"] is None


def test_real_possession_is_rendered_as_a_labeled_pitch_share(app_module):
    stats = _real_statistics({'provider': 'API-Football Pro', 'stat_cards': [
        {'key': 'possession', 'label': 'Posesión', 'home': '61%', 'away': '39%'},
        {'key': 'fouls', 'label': 'Faltas', 'home': '8', 'away': '14'},
        {'key': 'throw_ins', 'label': 'Saques de banda', 'home': '12', 'away': '9'},
    ]}, {})
    with app_module.app.test_request_context():
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/v944_match_center.html' import stats_panel %}{{ stats_panel(context) }}")
        rendered = template.render(context={'statistics': stats, 'teams': {
            'home': {'name': 'Granada'}, 'away': {'name': 'Visitante'},
        }})
    assert 'v944-possession__pitch' in rendered
    assert 'Reparto porcentual de posesión: Granada 61%, Visitante 39%.' in rendered
    assert '61%' in rendered and '39%' in rendered
    assert 'Faltas' in rendered and 'Saques de banda' in rendered
    assert 'Dato real del proveedor' in rendered
    assert 'data-visualization="aggregate-share"' in rendered
    assert 'data-spatial-map-available="false"' in rendered
    assert 'no es un mapa de zonas ni la ubicación del balón' in rendered


def test_match_panel_explains_unavailable_possession_instead_of_guessing(app_module):
    stats = _real_statistics({'provider': 'API-Football Pro', 'stat_cards': [
        {'key': 'fouls', 'label': 'Faltas', 'home': '0', 'away': '3'},
    ]}, {})
    with app_module.app.test_request_context():
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/v944_match_center.html' import stats_panel %}{{ stats_panel(context) }}")
        rendered = template.render(context={'statistics': stats, 'teams': {
            'home': {'name': 'Granada'}, 'away': {'name': 'Visitante'},
        }})
    assert 'El proveedor no ha entregado la posesión de este partido.' in rendered
    assert 'v944-possession__pitch' not in rendered


def test_finished_match_uses_saved_possession_without_claiming_spatial_map(app_module):
    stats = _real_statistics({}, {'is_finished': True}, {
        'available': True, 'postmatch_recovered': True,
        'source': 'api_football_stats_cache', 'updated_at': '2026-10-17T16:01:00Z',
        'items': [{'key': 'possession', 'label': 'Posesión', 'home': '57%', 'away': '43%'}],
    })
    with app_module.app.test_request_context():
        template = app_module.app.jinja_env.from_string(
            "{% from 'components/v944_match_center.html' import stats_panel %}{{ stats_panel(context) }}")
        rendered = template.render(context={'statistics': stats, 'teams': {
            'home': {'name': 'Local'}, 'away': {'name': 'Visitante'},
        }})
    assert 'data-stat-source="api_football_stats_cache"' in rendered
    assert 'Local 57%' in rendered and 'Visitante 43%' in rendered
    assert 'data-spatial-map-available="false"' in rendered
    assert '2026-10-17T16:01:00Z' in rendered


def test_statistics_budget_and_cooldown_statuses_are_explained_without_provider_io():
    expected = {
        'DAILY_BUDGET': 'límite diario de consultas',
        'SOURCE_COOLDOWN': 'periodo de espera',
        'TIME_BUDGET': 'tiempo disponible',
    }
    for status, copy in expected.items():
        refresh, message = _statistics_refresh_context(
            {'available': False}, {'is_upcoming': False}, {'status': status},
        )
        assert refresh['status'] == status
        assert copy in message


def test_cached_statistics_explain_when_refresh_is_deferred():
    refresh, message = _statistics_refresh_context(
        {'available': True}, {'is_upcoming': False}, {'status': 'DAILY_BUDGET'},
    )
    assert refresh['status'] == 'DAILY_BUDGET'
    assert 'últimas estadísticas guardadas' in message
    assert 'límite diario de consultas' in message
