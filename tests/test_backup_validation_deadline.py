"""Bounded named validation and isolated restoration, synthetic data only."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import errno
import hashlib
import json
import os
import runpy
import sqlite3
import time

import pytest
from engines import data_vault_engine as vault

ROOT=Path(__file__).resolve().parents[1]
OP=runpy.run_path(str(ROOT/'tools/backup_operator_recovery_327.py'))
VERIFY=OP['verify_and_restore_isolated']
GLOBALS=VERIFY.__globals__

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture
def archive(tmp_path):
    source=tmp_path/'s.db'
    folder=tmp_path/'b'
    with sqlite3.connect(source) as conn:
        conn.execute('CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('CREATE INDEX users_name ON users(name)')
        conn.execute('CREATE VIEW user_names AS SELECT name FROM users')
        conn.executemany('INSERT INTO users(name) VALUES(?)',[('synthetic-'+str(i),) for i in range(10)])
    made=vault.create_sqlite_backup(source,tmp_path,'SYNTHETIC_DEADLINE',directory=folder,
                                  max_files=0,preserve_existing_backups=True)
    assert made['ok'] and made['backup_created'],made
    selected=Path(made['path'])
    return source,folder,selected,made

def contents(folder):
    return {p.name:sha(p) for p in folder.iterdir() if p.is_file()}

def test_named_validation_skips_catalogue_and_preserves_archive(archive,monkeypatch):
    source,folder,selected,made=archive
    before=contents(folder);source_hash=sha(source)
    def forbidden(*args,**kwargs):
        raise AssertionError('Bounded validation must not scan every historical archive')
    monkeypatch.setattr(vault,'list_backups',forbidden)
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert result['ok'] and result['validated']==1
    assert result['results'][0]['actual']==made['sha256']
    assert contents(folder)==before and sha(source)==source_hash

def test_default_validator_preserves_existing_catalogue_contract(archive,monkeypatch):
    _,folder,selected,_=archive
    real=vault.list_backups;seen=[]
    def catalogue(*args,**kwargs):
        seen.append(1);return real(*args,**kwargs)
    def forbidden(*args,**kwargs):
        raise AssertionError('No deadline: existing validator path must remain unchanged')
    monkeypatch.setattr(vault,'list_backups',catalogue)
    monkeypatch.setattr(vault,'_validate_named_backup_until',forbidden)
    result=vault.validate_backup(ROOT,selected.name,directory=folder)
    assert result['ok'] and len(seen)==1
    assert set(result)=={'ok','validated','results'}

@pytest.mark.parametrize('value',[True,0,-1,'30',float('nan'),float('inf')])
def test_invalid_validation_deadline_fails_closed(archive,value):
    _,folder,selected,_=archive
    before=contents(folder)
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=value)
    assert not result['ok'] and result['error']=='invalid_backup_validation_deadline'
    assert contents(folder)==before

@pytest.mark.parametrize('name',['../outside.db','database_../outside.db','database_..\\outside.db','unowned.db',''])
def test_bounded_name_rejects_paths_without_catalogue(archive,name,monkeypatch):
    _,folder,_,_=archive
    monkeypatch.setattr(vault,'list_backups',lambda *a,**k:(_ for _ in ()).throw(AssertionError('catalogue')))
    result=vault.validate_backup(ROOT,name,directory=folder,deadline=time.monotonic()+30)
    assert result['ok'] is False and result['validated']==0
    assert result['error']=='invalid_backup_name'

def test_expired_validation_does_not_hash_or_restore(archive,monkeypatch):
    _,folder,selected,_=archive
    before=contents(folder)
    monkeypatch.setattr(vault,'sha256_file',lambda *a,**k:(_ for _ in ()).throw(AssertionError('hash after expiry')))
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()-1)
    assert not result['ok'] and result['error']=='backup_validation_timeout'
    assert result['failure_stage']=='VALIDATION_METADATA'
    assert contents(folder)==before

@pytest.mark.parametrize('field,value',[('valid',False),('valid',1),('sha256','f'*63),('sha256','g'*64),('size_bytes',True),('size_bytes',999999)])
def test_invalid_manifest_never_reaches_sqlite(archive,field,value,monkeypatch):
    _,folder,selected,_=archive
    manifest=selected.with_suffix('.json');data=json.loads(manifest.read_text(encoding='utf-8'))
    data[field]=value;manifest.write_text(json.dumps(data),encoding='utf-8')
    before=contents(folder)
    monkeypatch.setattr(vault,'connect_archive_readonly',lambda *a,**k:(_ for _ in ()).throw(AssertionError('SQLite before valid metadata')))
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert not result['ok'] and result['error']=='invalid_backup_manifest'
    assert contents(folder)==before

@pytest.mark.parametrize('data',[b'[]',b'{',b' '* (128*1024+1)],ids=['nonobject','malformed','oversized'])
def test_nonobject_invalid_or_oversized_manifest_fails(archive,data):
    _,folder,selected,_=archive
    selected.with_suffix('.json').write_bytes(data)
    before=contents(folder)
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert not result['ok']
    assert contents(folder)==before

def test_hardlinked_backup_is_not_accepted(archive):
    _,folder,selected,_=archive
    link=folder/'owned-hardlink.db'
    try:link.hardlink_to(selected)
    except OSError as exc:pytest.skip('Owned temporary filesystem cannot create hardlinks: '+type(exc).__name__)
    before=contents(folder)
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert not result['ok']
    assert contents(folder)==before

def test_hash_mismatch_stops_before_sqlite(archive,monkeypatch):
    _,folder,selected,_=archive
    with selected.open('r+b') as out:
        out.seek(100);out.write(b'X')
    before=contents(folder)
    monkeypatch.setattr(vault,'connect_archive_readonly',lambda *a,**k:(_ for _ in ()).throw(AssertionError('SQLite after bad hash')))
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert not result['ok'] and result['error']=='backup_hash_mismatch'
    assert contents(folder)==before

def test_hash_deadline_includes_post_hash_check(archive):
    _,folder,selected,_=archive
    real=vault.sha256_file;clock=[1.0]
    def late(path,**kwargs):
        digest=real(path,**kwargs);clock[0]=12.0;return digest
    with patch.object(vault.time,'monotonic',lambda:clock[0]),patch.object(vault,'sha256_file',late):
        result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=10.0)
    assert not result['ok'] and result['error']=='backup_validation_timeout'
    assert result['failure_stage']=='VALIDATION_HASH'

def test_real_hash_io_error_is_not_masked_as_timeout(archive):
    _,folder,selected,_=archive
    clock=[1.0]
    def fail(*args,**kwargs):
        clock[0]=12.0;raise OSError(errno.EIO,'SYNTHETIC_PRIVATE_PATH_NOT_FOR_OUTPUT')
    with patch.object(vault.time,'monotonic',lambda:clock[0]),patch.object(vault,'sha256_file',fail):
        result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=10.0)
    assert result['error']=='backup_validation_failed' and result['error_type']=='OSError'
    assert 'SYNTHETIC_PRIVATE_PATH' not in json.dumps(result)

def test_small_integrity_query_is_checked_even_without_progress_callback(archive):
    _,folder,selected,_=archive
    real=vault.connect_archive_readonly;clock=[1.0]
    class LateConnection:
        def __init__(self,c):self.c=c
        def __getattr__(self,n):return getattr(self.c,n)
        def close(self):self.c.close()
        def execute(self,sql,*args):
            cursor=self.c.execute(sql,*args)
            if sql=='PRAGMA integrity_check':clock[0]=12.0
            return cursor
    with patch.object(vault.time,'monotonic',lambda:clock[0]),patch.object(vault,'connect_archive_readonly',lambda p:LateConnection(real(p))):
        result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=10.0)
    assert not result['ok'] and result['error']=='backup_validation_timeout'
    assert result['failure_stage']=='VALIDATION_INTEGRITY'

def test_manifest_change_during_validation_is_rejected(archive,monkeypatch):
    _,folder,selected,_=archive
    manifest=selected.with_suffix('.json');real=vault.sha256_file
    def changed(path,**kwargs):
        value=real(path,**kwargs)
        with manifest.open('ab') as out:out.write(b' ')
        return value
    monkeypatch.setattr(vault,'sha256_file',changed)
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert not result['ok'] and result['error']=='backup_changed_during_validation'

def test_actual_verify_restore_matches_full_schema_and_preserves_history(archive):
    source,folder,selected,made=archive
    before=contents(folder);source_hash=sha(source)
    result=VERIFY(folder,selected.name,30)
    assert result['ok'] and result['code']=='RESTORE_VERIFIED'
    assert result['sha256']==made['sha256'] and result['schema_match'] is True
    assert contents(folder)==before and sha(source)==source_hash
    assert not list(folder.glob('.isolated_restore_327_*'))

@pytest.mark.parametrize('value',[True,0,-1,'bad',float('nan'),float('inf')])
def test_invalid_operator_budget_writes_nothing(archive,value):
    _,folder,selected,_=archive
    before=contents(folder)
    result=VERIFY(folder,selected.name,value)
    assert not result['ok'] and result['code']=='INVALID_VERIFICATION_BUDGET'
    assert contents(folder)==before

def test_verifier_lock_busy_does_not_scan_or_restore(archive,monkeypatch):
    _,folder,selected,_=archive
    before=contents(folder)
    monkeypatch.setitem(GLOBALS,'validate_backup',lambda *a,**k:(_ for _ in ()).throw(AssertionError('scan while busy')))
    with vault.backup_directory_lock(folder):
        result=VERIFY(folder,selected.name,30)
    assert result['code']=='RECOVERY_LOCK_BUSY' and not result['ok']
    assert contents(folder)==before

def test_operator_reports_the_validation_timeout_stage(archive):
    _,folder,selected,_=archive
    real=vault.sha256_file;clock=[1.0]
    def late(path,**kwargs):
        value=real(path,**kwargs);clock[0]=12.0;return value
    with patch.object(vault.time,'monotonic',lambda:clock[0]),patch.object(vault,'sha256_file',late):
        result=VERIFY(folder,selected.name,9)
    assert result['code']=='VERIFICATION_TIMEOUT'
    assert result['failure_stage']=='VALIDATION_HASH'

def test_operator_does_not_hide_real_io_error_after_budget(archive):
    _,folder,selected,_=archive
    clock=[1.0]
    def fail(*args,**kwargs):
        clock[0]=12.0;raise OSError(errno.EIO,'DO_NOT_LEAK_PRIVATE_PATH')
    with patch.object(vault.time,'monotonic',lambda:clock[0]),patch.object(vault,'sha256_file',fail):
        result=VERIFY(folder,selected.name,9)
    assert result['code']=='HASH_OR_INTEGRITY_FAILED'
    assert result['error_type']=='OSError' and result['failure_stage']=='VALIDATION_HASH'
    assert 'DO_NOT_LEAK_PRIVATE_PATH' not in json.dumps(result)

def test_archive_change_after_validation_is_rejected(archive,monkeypatch):
    _,folder,selected,_=archive
    real=vault.validate_backup
    def changed(*args,**kwargs):
        checked=real(*args,**kwargs)
        info=selected.stat();os.utime(selected,ns=(info.st_atime_ns,info.st_mtime_ns+1000000000))
        return checked
    monkeypatch.setitem(GLOBALS,'validate_backup',changed)
    result=VERIFY(folder,selected.name,30)
    assert not result['ok'] and result['code']=='BACKUP_CHANGED_DURING_VERIFICATION'
    assert not list(folder.glob('.isolated_restore_327_*'))

def test_restore_callback_timeout_removes_only_own_temporary(archive,monkeypatch):
    _,folder,selected,_=archive
    before=contents(folder);real=GLOBALS['connect_archive_readonly'];clock=[1.0]
    class ExpiringCopy:
        def __init__(self,c):self.c=c
        def __getattr__(self,n):return getattr(self.c,n)
        def close(self):self.c.close()
        def backup(self,target,*,pages,progress,sleep):
            def expire(status,remaining,total):
                clock[0]=12.0;progress(status,remaining,total)
            return self.c.backup(target,pages=pages,progress=expire,sleep=sleep)
    monkeypatch.setitem(GLOBALS,'connect_archive_readonly',lambda p:ExpiringCopy(real(p)))
    with patch.object(vault.time,'monotonic',lambda:clock[0]):
        result=VERIFY(folder,selected.name,9)
    assert not result['ok'] and result['code']=='VERIFICATION_TIMEOUT'
    assert result['failure_stage']=='RESTORE_SNAPSHOT'
    assert contents(folder)==before and not list(folder.glob('.isolated_restore_327_*'))

def test_expiry_during_cleanup_cannot_report_success(archive,monkeypatch):
    _,folder,selected,_=archive
    before=contents(folder);real=GLOBALS['tempfile'].TemporaryDirectory;clock=[1.0]
    @contextmanager
    def expired(*args,**kwargs):
        with real(*args,**kwargs) as directory:
            yield directory
        clock[0]=12.0
    monkeypatch.setattr(GLOBALS['tempfile'],'TemporaryDirectory',expired)
    with patch.object(vault.time,'monotonic',lambda:clock[0]):
        result=VERIFY(folder,selected.name,9)
    assert not result['ok'] and result['code']=='VERIFICATION_TIMEOUT'
    assert result['failure_stage']=='FINAL_CHECK'
    assert contents(folder)==before and not list(folder.glob('.isolated_restore_327_*'))

def test_same_table_count_but_changed_restored_index_is_rejected(archive,monkeypatch):
    _,folder,selected,_=archive
    before=contents(folder);real=GLOBALS['connect_archive_readonly']
    class ChangedSchema:
        def __init__(self,c):self.c=c
        def __getattr__(self,n):return getattr(self.c,n)
        def close(self):self.c.close()
        def backup(self,target,**kwargs):
            self.c.backup(target,**kwargs)
            target.execute('CREATE INDEX restore_only_index ON users(id,name)')
            target.commit()
    monkeypatch.setitem(GLOBALS,'connect_archive_readonly',lambda p:ChangedSchema(real(p)))
    result=VERIFY(folder,selected.name,30)
    assert not result['ok'] and result['code']=='SCHEMA_MISMATCH',result
    assert contents(folder)==before and not list(folder.glob('.isolated_restore_327_*'))


def test_reported_success_duration_cannot_exceed_verification_budget(archive,monkeypatch):
    _,folder,selected,_=archive
    before=contents(folder);real=GLOBALS['tempfile'].TemporaryDirectory;closing_done=[False];final_samples=[0]
    @contextmanager
    def completed(*args,**kwargs):
        with real(*args,**kwargs) as directory:
            yield directory
        closing_done[0]=True
    def clock():
        if closing_done[0]:
            final_samples[0]+=1
            return 9.5 if final_samples[0]==1 else 10.5
        return 1.0
    monkeypatch.setattr(GLOBALS['tempfile'],'TemporaryDirectory',completed)
    with patch.object(vault.time,'monotonic',clock):
        result=VERIFY(folder,selected.name,9)
    if result['ok']:
        assert result['verification_duration_ms']<9000
    else:
        assert result['code']=='VERIFICATION_TIMEOUT'
    assert contents(folder)==before and not list(folder.glob('.isolated_restore_327_*'))



def test_invalid_manifest_values_are_not_echoed_into_errors(archive):
    _,folder,selected,_=archive
    manifest=selected.with_suffix('.json')
    data=json.loads(manifest.read_text(encoding='utf-8'))
    data['sha256']={'untrusted':'PRIVATE_FIXTURE_VALUE'}
    manifest.write_text(json.dumps(data),encoding='utf-8')
    result=vault.validate_backup(ROOT,selected.name,directory=folder,deadline=time.monotonic()+30)
    assert not result['ok'] and result['error']=='invalid_backup_manifest'
    assert result['results'][0]['expected']==''
    assert 'PRIVATE_FIXTURE_VALUE' not in json.dumps(result)
