"""Inventory every top-level screen, including legacy Admin/client surfaces."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def report():
    rows = []
    for path in sorted((ROOT / 'templates').glob('*.html')):
        source = path.read_text(encoding='utf-8')
        if not re.search(r'{%\s*extends\s+["\']base.html["\']',source) and '<html' not in source.lower():
            continue
        family = 'Admin' if path.stem.startswith('admin_') else 'Client/public'
        primitives = [name for name, token in [
            ('header','page_header('),('metrics','kpi_card('),('matches','match_card('),
            ('panels','v933-panel'),('legacy panels','v928-admin-panel'),
            ('collection','collection('),('tables','<table'),('forms','<form'),
        ] if token in source]
        coverage = 'Shared shell' if 'extends' in source else 'Explicit shared stylesheet'
        rows.append(f'| `{path.name}` | {family} | {coverage} | {", ".join(primitives) or "Shell/legacy layout"} |')
    return '\n'.join([
        '# Global visual density inventory', '',
        f'{len(rows)} top-level templates receive the shared adaptive density contract.',
        'This is static coverage, not a claim that every record state has been visually tested.', '',
        '| Screen | Family | Density coverage | Shared presentation |',
        '|---|---|---|---|', *rows, '',
    ])


if __name__ == '__main__':
    target=ROOT/'docs'/'global-density-inventory.md'
    target.parent.mkdir(exist_ok=True)
    target.write_text(report(),encoding='utf-8')
    print(str(target))
