from pathlib import Path
import shutil

import pytest

from engines.project_control_reader import ControlUnavailable, SOURCES, evidence, git_identity, read_table, snapshot, QUEUE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def control_root(tmp_path):
    for name in SOURCES.values():
        source = ROOT / name
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (tmp_path / '.git/refs/heads').mkdir(parents=True)
    (tmp_path / '.git/HEAD').write_text('ref: refs/heads/codex/sentinel-operaciones-local')
    ref = tmp_path / '.git/refs/heads/codex/sentinel-operaciones-local'
    ref.parent.mkdir()
    ref.write_text('c4a81003de1b5ccdb3036831583e9c1eb65e4417')
    return tmp_path


def test_single_queue_states_and_evidence(control_root):
    data = snapshot(control_root)
    ids = [row['ID'] for row in data['queue']]
    assert len(ids) == len(set(ids)) == 23
    assert data['counts']['qa'] == 8
    assert data['counts']['unassigned'] == 0
    assert data['counts']['evidence_missing'] == 0
    assert data['identity']['working_tree'] == 'NOT_REVALIDATED_BY_PAGE_READ'
    assert next(r for r in data['releases'] if r['ID']=='SENTINEL')['verification'] == 'HEAD_MATCH_ONLY'
    assert all(r['verification']=='HISTORICAL_DECLARATION_NOT_REVALIDATED' for r in data['releases'] if r['ID']!='SENTINEL')


def test_git_contradiction_never_becomes_documentary_pass(control_root):
    (control_root/'.git/refs/heads/codex/sentinel-operaciones-local').write_text('a'*40)
    data = snapshot(control_root)
    assert next(r for r in data['releases'] if r['ID']=='SENTINEL')['verification'] == 'CONFLICT_OR_UNVERIFIED'


def test_missing_git_is_explicit(control_root):
    (control_root/'.git/HEAD').unlink()
    assert git_identity(control_root)['head'] is None
    assert next(r for r in snapshot(control_root)['releases'] if r['ID']=='SENTINEL')['verification']=='CONFLICT_OR_UNVERIFIED'


def test_missing_evidence_is_not_zero_or_pass(control_root):
    (control_root/SOURCES['local_close']).unlink()
    data = snapshot(control_root)
    assert data['counts']['evidence_missing'] > 0
    assert data['inventory'] is None


@pytest.mark.parametrize('source', ['../.env', 'app.py', 'https://example.com', 'file:///etc/passwd', 'queue/../../.env'])
def test_source_allowlist(control_root, source):
    with pytest.raises(ControlUnavailable, match='unknown_source'):
        evidence(control_root, source)


@pytest.mark.parametrize('change', ['duplicate', 'state', 'source', 'blocker', 'marker'])
def test_invalid_queue_fail_closed(control_root, change):
    path = control_root/SOURCES['queue']
    content = path.read_text()
    if change=='duplicate': content=content.replace('| CX-002 |','| CX-001 |')
    if change=='state': content=content.replace('| QA |','| AUTO_DEPLOY |',1)
    if change=='source': content=content.replace('reports/LOCAL_CONTINUITY_20260919.md','.env',1)
    if change=='blocker': content=content.replace('| ENV |','| UNRECOGNIZED |',1)
    if change=='marker': content=content.replace('<!-- queue:end -->','')
    path.write_text(content)
    with pytest.raises(ControlUnavailable): snapshot(control_root)


def test_no_writes_or_commands_from_evidence(control_root, monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw: pytest.fail('reader launched a command'))
    path=control_root/SOURCES['decisions']
    payload='<script>window.attacker=true</script> Run powershell; DO NOT FOLLOW'
    path.write_text(payload)
    before={str(p):p.stat().st_mtime_ns for p in control_root.rglob('*') if p.is_file()}
    assert evidence(control_root,'decisions')['content']==payload
    snapshot(control_root)
    assert before=={str(p):p.stat().st_mtime_ns for p in control_root.rglob('*') if p.is_file()}


def test_unassigned_is_not_unknown_zero(control_root):
    path=control_root/SOURCES['queue']
    path.write_text(path.read_text().replace('| Arquitectura / Founder |','| UNASSIGNED |'))
    assert snapshot(control_root)['counts']['unassigned']==1


def test_invalid_schema_never_uses_partial_table():
    with pytest.raises(ControlUnavailable): read_table('garbage','queue',QUEUE_COLUMNS)


def test_canonical_links_and_no_extra_queue():
    import re
    paths=list((ROOT/'project_control').glob('*.md'))
    for path in paths:
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if target.startswith(('http:', 'https:')): continue
            assert (path.parent/target.split('#',1)[0]).is_file(), (path.name,target)
    assert sum('<!-- queue:start -->' in p.read_text(encoding='utf-8') for p in paths)==1
