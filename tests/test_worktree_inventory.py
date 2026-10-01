"""Exercises the read-only inventory using disposable repositories only."""
from pathlib import Path
import importlib.util
import subprocess

import pytest

SPEC = importlib.util.spec_from_file_location('worktree_inventory', Path(__file__).resolve().parents[1]/'tools/inspect_local_worktrees.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def g(path, *args):
    return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.DEVNULL).decode().strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path/'main'; root.mkdir()
    g(root,'init','-b','main')
    g(root,'config','user.name','QA'); g(root,'config','user.email','qa@example.invalid')
    (root/'file.txt').write_text('base')
    (root/'.gitignore').write_text('.env\ncache/\n')
    g(root,'add','.'); g(root,'commit','-m','base')
    g(root,'update-ref','refs/remotes/origin/main','HEAD')
    return root


def linked(repo, name='linked'):
    path=repo.parent/name
    g(repo,'worktree','add','--detach',str(path),'HEAD')
    return path


def lookup(repo,path):
    return next(r for r in m.inspect(repo)['worktrees'] if r['path']==str(path))


def test_primary_is_preserved(repo):
    result=m.inspect(repo)
    assert result['files_deleted']==0
    assert 'PRIMARY_WORKTREE' in result['worktrees'][0]['reasons']
    assert not result['worktrees'][0]['safe_to_delete']


def test_clean_integrated_still_requires_activity_review(repo):
    path=linked(repo)
    row=lookup(repo,path)
    assert row['classification']=='CLEAN_INTEGRATED_REVIEW_ACTIVITY'
    assert row['active_chat_status']=='NOT_OBSERVED'
    assert not row['safe_to_delete']


@pytest.mark.parametrize('kind', ['tracked','untracked','ignored'])
def test_local_files_are_preserved(repo,kind):
    path=linked(repo)
    f=path/({'tracked':'file.txt','untracked':'new.txt','ignored':'.env'}[kind])
    f.write_text('DO NOT READ OR DELETE')
    row=lookup(repo,path)
    reason={'tracked':'TRACKED_CHANGES','untracked':'UNTRACKED_FILES','ignored':'IGNORED_LOCAL_FILES'}[kind]
    assert reason in row['reasons']
    assert f.read_text()=='DO NOT READ OR DELETE'
    assert 'DO NOT READ' not in str(row)


def test_locked_preserved(repo):
    path=linked(repo); g(repo,'worktree','lock',str(path),'--reason','private context')
    row=lookup(repo,path)
    assert row['locked'] and 'LOCKED' in row['reasons']
    assert 'private context' not in str(row)


def test_detached_unique_history_preserved(repo):
    path=linked(repo); (path/'file.txt').write_text('new commit')
    g(path,'add','.'); g(path,'commit','-m','unmerged')
    assert 'UNIQUE_OR_SQUASHED_HISTORY' in lookup(repo,path)['reasons']


def test_missing_worktree_no_prune(repo):
    path=linked(repo); moved=path.with_name('moved'); path.rename(moved)
    assert lookup(repo,path)['registered_missing']
    assert any(Path(row['worktree']) == path for row in
               m.parse_worktrees(g(repo,'worktree','list','--porcelain','-z')))
    assert moved.exists()


def test_unicode_and_space_paths(repo):
    path=linked(repo,'copia á con espacio')
    assert lookup(repo,path)['path']==str(path)


def test_status_rename_parsing():
    assert m.status_counts('R  new\0old\0?? free\0!! private\0')=={'tracked_changes':1,'untracked_entries':1,'ignored_entries':1}


def test_no_ref_or_index_changes(repo):
    linked(repo)
    before=(g(repo,'show-ref'),(repo/'.git/index').read_bytes())
    m.inspect(repo)
    assert before==(g(repo,'show-ref'),(repo/'.git/index').read_bytes())


def test_reject_non_ref_base(repo):
    with pytest.raises(m.InspectionError):m.inspect(repo,'--all')


def test_replace_refs_cannot_hide_unique_history(repo):
    main = g(repo, 'rev-parse', 'HEAD')
    tree = g(repo, 'rev-parse', 'HEAD^{tree}')
    unique = g(repo, 'commit-tree', tree, '-m', 'isolated unique history')
    path = repo.parent / 'unique'
    g(repo, 'worktree', 'add', '--detach', str(path), unique)
    substituted = g(repo, 'commit-tree', tree, '-p', unique, '-m', 'local graph customization')
    g(repo, 'replace', main, substituted)
    g(repo, 'merge-base', '--is-ancestor', unique, main)
    before = g(repo, 'show-ref')
    row = lookup(repo, path)
    assert row['ancestor_of_base'] is False
    assert 'UNIQUE_OR_SQUASHED_HISTORY' in row['reasons']
    assert not row['safe_to_delete']
    assert g(repo, 'show-ref') == before


@pytest.mark.parametrize('flags', [
    ['--assume-unchanged'], ['--skip-worktree'],
    ['--assume-unchanged', '--skip-worktree'],
])
def test_hidden_index_flags_are_not_clean(repo, flags):
    path=linked(repo)
    for flag in flags:
        g(path,'update-index',flag,'file.txt')
    (path/'file.txt').write_text('LOCAL CHANGE HIDDEN FROM STATUS')
    before=g(path,'ls-files','-v','file.txt')
    assert not g(path,'status','--porcelain')
    row=lookup(repo,path)
    assert row['classification']=='KEEP'
    if '--assume-unchanged' in flags:
        assert row['assume_unchanged_entries']==1
        assert 'ASSUME_UNCHANGED_INDEX_ENTRIES' in row['reasons']
    if '--skip-worktree' in flags:
        assert row['skip_worktree_entries']==1
        assert 'SKIP_WORKTREE_INDEX_ENTRIES' in row['reasons']
    assert g(path,'ls-files','-v','file.txt')==before
    assert (path/'file.txt').read_text()=='LOCAL CHANGE HIDDEN FROM STATUS'


def test_fsmonitor_hook_is_never_invoked_by_inspection(repo):
    path=linked(repo)
    marker=repo/'.git'/'hook-marker'
    hook=repo/'.git'/'qa-fsmonitor'
    hook.write_text('#!/bin/sh\nprintf "ran" >> "'+marker.as_posix()+'"\nprintf "token\\000"\n', newline='\n')
    hook.chmod(0o700)
    g(repo,'config','core.fsmonitor',hook.as_posix())
    # Establish that this Git setup really would execute the hook without a guard.
    g(path,'status','--porcelain')
    assert marker.exists()
    marker.unlink()  # Disposable marker in this test repository, not user data.
    before=(g(repo,'show-ref'),(repo/'.git/index').read_bytes())
    m.inspect(repo)
    assert not marker.exists(), 'Read-only inspection executed the fsmonitor hook'
    assert before==(g(repo,'show-ref'),(repo/'.git/index').read_bytes())
