"""Preservation mode contracts; synthetic SQLite only, never App/Render."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout
import argparse
import hashlib
import io
import json
import runpy
import sqlite3

import pytest
from engines import data_vault_engine as vault

ROOT=Path(__file__).resolve().parents[1]
OPERATOR=runpy.run_path(str(ROOT/'tools/backup_operator_recovery_327.py'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def seed(tmp_path):
    source=tmp_path/'s.db'
    folder=tmp_path/'b'
    with sqlite3.connect(source) as conn:
        conn.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)')
        conn.executemany('INSERT INTO users(name) VALUES(?)', [('fixture-'+str(i),) for i in range(10)])
    for _ in range(2):
        made=vault.create_sqlite_backup(source,tmp_path,'SYNTHETIC',directory=folder,max_files=0)
        assert made['ok'] and made['backup_created'],made
    previous={p.name:sha(p) for p in folder.glob('database_*')}
    return source,folder,sha(source),previous

@pytest.mark.parametrize('free',[0,2**30])
def test_capacity_optout_never_catalogues_or_reclaims(tmp_path,monkeypatch,free):
    source,folder,source_hash,previous=seed(tmp_path)
    monkeypatch.setattr(vault.shutil,'disk_usage',lambda _:SimpleNamespace(free=free,total=2**31))
    def forbidden(*args,**kwargs):
        raise AssertionError('Preservation mode must not inspect/delete historical archives')
    monkeypatch.setattr(vault,'list_backups',forbidden)
    monkeypatch.setattr(vault,'_delete_backup_item',forbidden)
    result=vault.ensure_backup_capacity(source,tmp_path,directory=folder,allow_reclaim=False)
    assert result['ok'] is (free>0)
    assert result['reclamation_allowed'] is False
    assert result['removed']==[]
    assert {p.name:sha(p) for p in folder.glob('database_*')}==previous
    assert sha(source)==source_hash

@pytest.mark.parametrize('include_orphan',[False,True])
def test_operator_space_drop_preserves_every_prior_file(tmp_path,monkeypatch,include_orphan):
    source,folder,source_hash,previous=seed(tmp_path)
    if include_orphan:
        orphan=folder/'database_20000101_orphan.db'
        orphan.write_bytes(b'owner-preserved-unverified-history')
        previous[orphan.name]=sha(orphan)
    calls=[]
    def disk(_):
        free=2**30 if len(calls)<2 else 0
        calls.append(free)
        return SimpleNamespace(free=free,total=2**31)
    monkeypatch.setattr(vault.shutil,'disk_usage',disk)
    def forbidden(*args,**kwargs):
        raise AssertionError('A recovery command must not delete any prior archive')
    monkeypatch.setattr(vault,'_delete_backup_item',forbidden)
    args=argparse.Namespace(db=str(source),backup_dir=str(folder),verify_existing=None,execute=True,timeout=60)
    out=io.StringIO()
    with redirect_stdout(out):
        code=OPERATOR['run'](args)
    result=json.loads(out.getvalue().splitlines()[-1])
    assert code==2 and result['backup_created'] is False
    assert result['stage']=='CAPACITY'
    assert {p.name:sha(p) for p in folder.glob('database_*')}==previous
    assert sha(source)==source_hash
    assert not list(folder.glob('.backup-work-*'))
    assert calls[:3]==[2**30,2**30,0]

@pytest.mark.parametrize('limit',[0,1,None])
def test_preservation_mode_also_disables_final_retention(tmp_path,limit):
    source,folder,source_hash,previous=seed(tmp_path)
    made=vault.create_sqlite_backup(source,tmp_path,'SYNTHETIC',directory=folder,
                                  max_files=limit,preserve_existing_backups=True)
    assert made['ok'] and made['backup_created'],made
    assert made['storage']['reclamation_allowed'] is False
    assert made['storage']['removed']==[] and made['retention']['removed']==[]
    assert len(list(folder.glob('database_*.db')))==3
    assert all((folder/name).is_file() and sha(folder/name)==digest for name,digest in previous.items())
    assert vault.validate_backup(tmp_path,made['backup_file'],directory=folder)['ok']
    assert sha(source)==source_hash

@pytest.mark.parametrize('explicit_false',[False,True])
def test_default_call_contract_keeps_existing_private_caller_shape(tmp_path,monkeypatch,explicit_false):
    source,folder,source_hash,previous=seed(tmp_path)
    seen=[]
    def existing_signature(db_path,root,app_version,backup_type,created_by,*,directory,max_files,snapshot_timeout):
        seen.append((snapshot_timeout,max_files))
        return {'ok':False,'backup_created':False,'storage':{},'error':'INJECTED_NO_COPY'}
    monkeypatch.setattr(vault,'_create_sqlite_backup_locked',existing_signature)
    options={'preserve_existing_backups':False} if explicit_false else {}
    result=vault.create_sqlite_backup(source,tmp_path,'SYNTHETIC',directory=folder,**options)
    assert result['backup_created'] is False
    assert seen==[(15.0,None)]
    assert sha(source)==source_hash
    assert {p.name:sha(p) for p in folder.glob('database_*')}==previous

def test_hash_failure_preserves_priors_and_publishes_nothing(tmp_path,monkeypatch):
    source,folder,source_hash,previous=seed(tmp_path)
    original=vault.sha256_file
    def fail_snapshot(path,**kwargs):
        if Path(path).name=='snapshot.partial':
            raise sqlite3.OperationalError('SYNTHETIC_HASH_FAILURE')
        return original(path,**kwargs)
    monkeypatch.setattr(vault,'sha256_file',fail_snapshot)
    made=vault.create_sqlite_backup(source,tmp_path,'SYNTHETIC',directory=folder,
                                  preserve_existing_backups=True,max_files=1)
    assert made['ok'] is False and made['backup_created'] is False
    assert made['failure_stage']=='HASH'
    assert {p.name:sha(p) for p in folder.glob('database_*')}==previous
    assert not list(folder.glob('.backup-work-*'))
    assert sha(source)==source_hash
