"""Real local HTTP continuity, without provider/production effects."""
import os


def test_historico_is_a_real_track_record_consumer_not_a_diagnostic_write(app_module, monkeypatch):
    client = app_module.app.test_client()
    client.get('/local-safe/login/client?token=' + os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'])
    def forbidden(*args, **kwargs):
        raise AssertionError('Opening pick history must not write a not-found report')
    monkeypatch.setattr(app_module, 'v896_record_not_found', forbidden)
    response = client.get('/historico')
    assert response.status_code == 200
    assert b'data-v933-template="track_record"' in response.data
