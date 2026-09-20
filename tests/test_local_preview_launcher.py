"""Launcher policy tests; real start/reuse/stop is also exercised by desktop QA."""
import json
import socket

from tools.local_review import preview


def test_child_does_not_inherit_secrets_or_production_config(monkeypatch):
    for key in ('STRIPE_SECRET_KEY','API_FOOTBALL_KEY','DB_PATH','DATABASE_URL',
                'TELEGRAM_BOT_TOKEN','NEMESIS_LOCAL_EXTERNAL_AUTHORIZED','PYTHONPATH'):
        monkeypatch.setenv(key,'MUST_NOT_REACH_CHILD')
    env=preview.safe_environment()
    assert all('MUST_NOT_REACH_CHILD' not in value for value in env.values())
    assert env['NEMESIS_LOCAL_EXTERNAL_AUTHORIZED']=='0'
    assert str(preview.ROOT) in env['PYTHONPATH']


def test_occupied_port_is_not_stolen():
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1',0))
        port=occupied.getsockname()[1]
        if port < 65516:
            assert preview.select_port(port) != port


def test_metadata_from_another_tree_is_not_reused(tmp_path,monkeypatch):
    path=tmp_path/'preview.json'
    monkeypatch.setattr(preview,'METADATA',path)
    row={'protocol':preview.PROTOCOL,'root':str(preview.ROOT),'port':54910,'instance_id':'test'}
    path.write_text(json.dumps(row))
    assert preview.read_metadata()==row
    row['root']='another-worktree'
    path.write_text(json.dumps(row))
    assert preview.read_metadata() is None


def test_stale_stop_request_cannot_stop_new_instance(tmp_path):
    stop=tmp_path/'stop.json'
    stop.write_text(json.dumps({'instance_id':'old'}))
    assert not preview.stop_requested('new',stop)
    assert preview.stop_requested('old',stop)
    stop.write_text('{invalid')
    assert not preview.stop_requested('new',stop)


def test_start_reuses_instance_without_spawning(tmp_path,monkeypatch):
    monkeypatch.setattr(preview,'LOCAL',tmp_path)
    meta={'instance_id':'existing','port':54910}
    monkeypatch.setattr(preview,'read_metadata',lambda:meta)
    monkeypatch.setattr(preview,'is_running',lambda value:True)
    shown=[]
    monkeypatch.setattr(preview,'show',lambda *args:shown.append(args))
    def forbidden(*args,**kwargs):
        raise AssertionError('No duplicate process')
    monkeypatch.setattr(preview.subprocess,'Popen',forbidden)
    preview.start(False)
    assert shown==[(meta,False)]


def test_stop_without_owned_instance_does_not_write(tmp_path,monkeypatch):
    stop=tmp_path/'stop.json'
    monkeypatch.setattr(preview,'STOP',stop)
    monkeypatch.setattr(preview,'read_metadata',lambda:None)
    preview.stop()
    assert not stop.exists()
