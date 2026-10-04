import pytest


@pytest.mark.parametrize('message', [
    'runtime PARTIAL', 'provider unavailable', 'cache reused',
    'cron FAIL', 'Sports Truth pipeline', 'storage DB_PATH',
])
def test_provider_diagnostics_never_render_as_client_copy(app_module, message):
    template = app_module.app.jinja_env.from_string('''
      {% from 'components/v933_ui.html' import client_message, realtime_state_bar with context %}
      {{ client_message(message) }}
      {{ realtime_state_bar({'safe_message': message, 'cache_state': 'INTERNAL_DIAGNOSTIC'}, technical=true) }}
    ''')
    with app_module.app.test_request_context('/directo'):
        rendered = template.render(message=message)
    assert message not in rendered
    assert 'INTERNAL_DIAGNOSTIC' not in rendered
    assert 'data-v934-technical="false"' in rendered
    assert 'datos confirmados' in rendered


def test_admin_realtime_diagnostics_remain_available(app_module):
    template = app_module.app.jinja_env.from_string('''
      {% from 'components/v933_ui.html' import realtime_state_bar with context %}
      {{ realtime_state_bar({'cache_state': 'INTERNAL_DIAGNOSTIC'}, technical=true) }}
    ''')
    with app_module.app.test_request_context('/admin/dashboard'):
        rendered = template.render()
    assert 'data-v934-technical="true"' in rendered
    assert 'INTERNAL_DIAGNOSTIC' in rendered


def test_live_uses_a_distinct_semantic_role(app_module):
    template = app_module.app.jinja_env.from_string('''
      {% from 'components/v933_ui.html' import canonical_match_state with context %}
      {{ canonical_match_state({'lifecycle': 'LIVE', 'is_live': true}) }}
    ''')
    with app_module.app.test_request_context('/directo'):
        rendered = template.render()
    assert 'is-live' in rendered
    assert 'is-success' not in rendered
