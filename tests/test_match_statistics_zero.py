from engines.match_context_engine import _real_statistics


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
