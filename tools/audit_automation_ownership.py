"""Reproducible source inventory; references are evidence, not execution proof."""
from __future__ import annotations
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_MODULES = {
    'engines.automation_domains', 'engines.automation_orchestrator_engine',
    'engines.daily_automation_engine', 'engines.scheduler_engine',
    'engines.data_vault_engine', 'engines.product_review_system_engine',
    'engines.content_rights_engine', 'sports_service', 'telegram_service',
    'engines.telegram_autonomous_delivery_engine',
}


def inventory():
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    sources = {p: (ROOT / p).read_text(encoding='utf-8', errors='replace') for p in paths
               if p.endswith(('.py', '.yml', '.yaml', '.toml', '.sh', '.ps1'))}
    imports = {}
    reference_index = {}
    for path, source in sources.items():
        for line, value in enumerate(source.splitlines(), 1):
            for token in set(re.findall(r'[A-Za-z_][A-Za-z_0-9/\.\\-]*', value)):
                reference_index.setdefault(token.replace('\\', '/'), []).append(f'{path}:{line}')
    for path, source in sources.items():
        if not path.endswith('.py'):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) else []
            for name in names:
                if name:
                    imports.setdefault(name, []).append(f'{path}:{node.lineno}')
    items = []
    for path in sorted(sources):
        if not (path.startswith(('automation_workforce/', 'tools/', '.github/workflows/')) or
                path.startswith('engines/') and any(x in path for x in ('automation', 'postmatch', 'highlight', 'sentinel', 'worker')) or
                path[:-3].replace('/', '.') in PRODUCTION_MODULES or path in {'scheduler_engine.py', 'sportsdb_highlights_engine.py'}):
            continue
        stem = Path(path).stem
        module = path[:-3].replace('/', '.') if path.endswith('.py') else ''
        imported = sorted(set(imports.get(module, []) + imports.get(stem, [])))
        tokens = (path, module, stem, stem.removesuffix('_worker')) if path.startswith('automation_workforce/') else (path, module, stem)
        refs = [r for token in tokens for r in reference_index.get(token, [])
                if not r.startswith(path + ':')]
        qa = path.startswith('automation_workforce/') or path.startswith('.github/workflows/') or stem.startswith(('check_', 'test_', 'audit_', 'benchmark_')) or any(x in stem for x in ('browser_qa', 'sentinel', 'visual_company_worker'))
        production = stem.startswith('render_cron') or module in PRODUCTION_MODULES or path.startswith('engines/') and any(x in stem for x in ('postmatch', 'highlight'))
        category = 'PRODUCTION' if production else 'QA' if qa else 'DEV'
        if not imported and not refs and not qa and not production:
            category = 'LEGACY'  # Candidate only; dynamic use still needs human inspection.
        purpose = ''
        if path.endswith('.py'):
            try:
                purpose = (ast.get_docstring(ast.parse(sources[path])) or '').split('\n')[0]
            except SyntaxError:
                pass
        items.append({'path': path, 'category': category, 'purpose': purpose or stem, 'imports': imported,
                      'references': sorted(set(refs)),
                      'execution_surfaces': sorted(set('GitHub QA' if r.startswith('.github/') else 'Render web import' if r.startswith('app.py:') else 'source reference (execution unproven)' for r in imported + refs)),
                      'retained': True, 'removal_eligible': False})
    endpoints = []
    for path, source in sources.items():
        if path == 'app.py' or path.startswith('blueprints/'):
            for line, value in enumerate(source.splitlines(), 1):
                if '@' in value and '/api/automation/' in value:
                    endpoints.append({'reference': f'{path}:{line}', 'route': value.strip()})
    return {'method': 'Tracked source, AST imports and literal workflow/orchestrator references; no proof of LIVE execution. LEGACY means candidate, never permission to delete.',
            'items': items, 'endpoints': endpoints, 'removed': []}


if __name__ == '__main__':
    output = ROOT / 'docs/automation-ownership.json'
    output.write_text(json.dumps(inventory(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output.name)
