"""The first Home request must not compile its shell after worker readiness."""
from pathlib import Path
import runpy
from types import SimpleNamespace


def test_worker_warmup_keeps_first_home_off_template_compilation(app_module, monkeypatch):
    app = app_module.app
    app.jinja_env.cache.clear()
    settings = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'gunicorn.conf.py'))
    settings['post_worker_init'](SimpleNamespace(wsgi=app))
    original = app.jinja_env.loader.get_source
    loaded = []

    def record(environment, name):
        loaded.append(name)
        return original(environment, name)

    monkeypatch.setattr(app.jinja_env.loader, 'get_source', record)
    response = app.test_client().get('/')
    assert response.status_code == 200
    assert b'NeMeSiS' in response.data
    assert loaded == []
