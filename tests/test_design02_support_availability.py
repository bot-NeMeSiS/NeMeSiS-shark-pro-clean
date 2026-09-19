"""Do not acknowledge a support message without a delivery/persistence channel."""
import pytest
import sqlite3
import uuid


@pytest.mark.parametrize('route', ['/support', '/soporte', '/contact'])
def test_support_does_not_claim_delivery_or_log_message_as_delivered(app_module, monkeypatch, route):
    logged = []
    monkeypatch.setattr(app_module, 'home_light_data', lambda: {})
    monkeypatch.setattr(app_module, 'record_security_event', lambda *args, **kwargs: logged.append(kwargs))
    monkeypatch.setattr(app_module, 'render_template', lambda template, **context: context['data'])
    monkeypatch.setattr(app_module, 'current_session_user', lambda: {'id': 'qa-support-user'})
    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('storage unavailable')
    monkeypatch.setattr(app_module, 'submit_support_request', unavailable)
    request_id = uuid.uuid4().hex
    with app_module.app.test_request_context(route, method='POST', data={
        'subject': 'SIMULATED_QA', 'message': 'Delivery must not be invented.', 'request_id': request_id
    }):
        app_module.session['support_request_id'] = request_id
        result = app_module.v724_contact_alias_page()
    assert isinstance(result, tuple) and result[1] == 503
    assert result[0]['sent'] is False
    assert result[0]['support_available'] is True
    assert result[0]['error']
    assert logged == []
