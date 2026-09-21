"""In-process Flask request concurrency. No real accounts or server reconfiguration."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import secrets
import socket
import sqlite3
import threading

import pytest
from engines.security_engine import generate_csrf_token


@pytest.fixture
def isolated(app_module, tmp_path, monkeypatch):
    app = app_module
    db = str(tmp_path / 'client-test.sqlite')
    monkeypatch.setattr(app, 'DB_PATH', db)
    def forbidden(*args, **kwargs):
        pytest.fail('No provider or external connection is allowed in this test')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    app.init_db()
    app.seed_core()
    with closing(sqlite3.connect(db)) as conn, conn:
        for uid in ['qa-client-one', 'qa-client-two']:
            conn.execute('''INSERT INTO users(id,name,email,password_hash,role,membership)
                            VALUES (?,?,?,?,?,?)''',
                         (uid, uid, uid+'@example.test', secrets.token_urlsafe(32), 'FREE', 'FREE'))
    return app, db


def test_concurrent_favorites_and_csrf_stay_with_their_owner(isolated):
    app, db = isolated
    rendezvous = threading.Barrier(2)
    tokens, token_lock = {}, threading.Lock()
    def customer(uid, other):
        client = app.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['user_role'] = 'FREE'
            sess['membership'] = 'FREE'
            token = generate_csrf_token(sess)
        with token_lock:
            tokens[uid] = token
        rendezvous.wait(timeout=8)
        wrong = client.post('/api/favorites', json={'kind': 'match', 'value': 'qa-shared'},
                            headers={'X-CSRF-Token': tokens[other]})
        assert wrong.status_code == 403
        for n in range(4):
            value = 'qa-shared' if n == 0 else f'{uid}-{n}'
            saved = client.post('/api/favorites', json={'kind': 'match', 'value': value, 'user_id': other},
                                headers={'X-CSRF-Token': token})
            assert saved.status_code == 200
            assert saved.get_json()['favorite']['user_id'] == uid
            own = client.get('/api/favorites').get_json()['favorites']
            assert all(item['user_id'] == uid for item in own)
        rendezvous.wait(timeout=8)
        if uid == 'qa-client-one':
            removed = client.delete('/api/favorites', json={'kind': 'match', 'value': 'qa-shared', 'user_id': other},
                                    headers={'X-CSRF-Token': token})
            assert removed.status_code == 200
        rendezvous.wait(timeout=8)
        remaining = client.get('/api/favorites').get_json()['favorites']
        assert ('qa-shared' in {item['value'] for item in remaining}) is (uid == 'qa-client-two')
        with client.session_transaction() as sess:
            assert sess['user_id'] == uid
            assert sess['user_role'] == 'FREE'
        return len(remaining)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(customer, 'qa-client-one', 'qa-client-two')
        second = pool.submit(customer, 'qa-client-two', 'qa-client-one')
        assert first.result(timeout=25) == 3
        assert second.result(timeout=25) == 4
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute('SELECT COUNT(*) FROM favorites').fetchone()[0] == 7
        assert conn.execute("SELECT COUNT(*) FROM users WHERE id LIKE 'qa-client-%' AND role='FREE'").fetchone()[0] == 2


def test_request_read_connections_are_distinct_and_closed(isolated):
    from flask import g
    app, _db = isolated
    barrier = threading.Barrier(2)
    seen, lock = [], threading.Lock()
    def read(uid):
        with app.app.test_request_context('/api/favorites'):
            from flask import session
            session['user_id'] = uid
            first = app.request_read_db()
            assert app.request_read_db() is first
            with lock:
                seen.append(id(first))
            barrier.wait(timeout=5)
            assert app.current_user_id() == uid
            assert g.nemesis_request_read_db is first
            assert first.execute('PRAGMA query_only').fetchone()[0] == 1
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            first.execute('SELECT 1')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(read, ['qa-client-one', 'qa-client-two']))
    assert len(set(seen)) == 2
