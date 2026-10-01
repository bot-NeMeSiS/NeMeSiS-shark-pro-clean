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
    assert str(path) in g(repo,'worktree','list','--porcelain')
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
