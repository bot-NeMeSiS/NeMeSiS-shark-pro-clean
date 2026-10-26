"""Readonly URI semantics using only owned SQLite files, never App or Render."""
from contextlib import closing
import hashlib
import os
import sqlite3

import pytest

from engines.data_vault_engine import connect_readonly


@pytest.mark.parametrize('name',['matches # observed.db','matches %23.db','fútbol mañana.db','matches with spaces.db'])
def test_literal_path_is_exact_and_writes_are_rejected(tmp_path,name):
    database=tmp_path/name
    with closing(sqlite3.connect(database)) as conn:
        conn.execute('CREATE TABLE evidence(value TEXT)')
        conn.execute('INSERT INTO evidence VALUES(?)',('owned literal file',));conn.commit()
    before=hashlib.sha256(database.read_bytes()).hexdigest()
    files=set(tmp_path.iterdir())
    with closing(connect_readonly(database)) as conn:
        assert conn.execute('SELECT value FROM evidence').fetchone()[0]=='owned literal file'
        with pytest.raises(sqlite3.OperationalError,match='readonly'):
            conn.execute('INSERT INTO evidence VALUES(?)',('must not write',))
    assert hashlib.sha256(database.read_bytes()).hexdigest()==before
    assert set(tmp_path.iterdir())==files, 'Do not create an unintended path before a URI fragment'


def test_missing_path_with_fragment_cannot_create_a_prefix_file(tmp_path):
    before=set(tmp_path.iterdir())
    with pytest.raises(sqlite3.OperationalError,match='unable to open'):
        with closing(connect_readonly(tmp_path/'missing#name.db')):
            pass
    assert set(tmp_path.iterdir())==before


@pytest.mark.skipif(os.name=='nt',reason='A question mark is not a legal Windows filename')
def test_filename_cannot_supply_a_different_uri_mode(tmp_path):
    database=tmp_path/'matches?mode=rw.db'
    with closing(sqlite3.connect(database)) as conn:
        conn.execute('CREATE TABLE evidence(value TEXT)');conn.commit()
    before=hashlib.sha256(database.read_bytes()).hexdigest()
    with closing(connect_readonly(database)) as conn:
        with pytest.raises(sqlite3.OperationalError,match='readonly'):
            conn.execute('INSERT INTO evidence VALUES(?)',('must not write',))
    assert hashlib.sha256(database.read_bytes()).hexdigest()==before
