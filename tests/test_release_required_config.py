"""Required startup config survives packaging; SQLite sidecars do not."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def policy_namespace(filename):
    tree = ast.parse((ROOT / 'tools' / filename).read_text(encoding='utf-8-sig'))
    values = {'ROOT': ROOT, 'Path': Path, 'VERSION_PREFIX': 'V941'}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = value
    return tree, values

def test_release_includes_active_audience_policy():
    tree, values = policy_namespace('build_clean_release.py')
    selector = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'include')
    exec(compile(ast.Module(body=[selector], type_ignores=[]), 'release-selector', 'exec'), values)
    assert values['include'](ROOT / 'config/audience-priority.json')

def test_builder_and_auditor_exclude_sqlite3_sidecars():
    _, builder = policy_namespace('build_clean_release.py')
    _, auditor = policy_namespace('audit_release_zip.py')
    for suffix in ('.sqlite3-wal', '.sqlite3-shm', '.sqlite3-journal'):
        assert suffix in builder['EXCLUDE_SUFFIXES']
        assert suffix in auditor['FORBIDDEN_SUFFIXES']
