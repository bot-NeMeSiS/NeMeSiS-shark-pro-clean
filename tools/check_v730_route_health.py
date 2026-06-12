#!/usr/bin/env python3
"""Static route health check for V730 without importing Flask."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
TEMPLATES = ROOT / "templates"
REPORTS = ROOT / "reports"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip() if (ROOT / "VERSION.txt").exists() else "DEV"

ROUTE_RE = re.compile(r"@app\.route\(\s*([\"'])(?P<rule>.+?)\1(?P<args>[^)]*)\)\s*\ndef\s+(?P<func>[a-zA-Z_][a-zA-Z0-9_]*)", re.S)
TEMPLATE_RE = re.compile(r"render_template\(\s*[\"']([^\"']+)[\"']")


def function_body(text: str, func: str) -> str:
    m = re.search(rf"^def\s+{re.escape(func)}\s*\([^)]*\):", text, re.M)
    if not m:
        return ""
    start = m.start()
    nxt = re.search(r"^def\s+[a-zA-Z_]", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[start:end]


def methods_from_args(args: str) -> list[str]:
    m = re.search(r"methods\s*=\s*\[([^\]]+)\]", args or "")
    if not m:
        return ["GET"]
    return sorted(set(re.findall(r"[\"']([A-Z]+)[\"']", m.group(1)))) or ["GET"]


def bucket(rule: str, methods: list[str]) -> str:
    if rule.startswith('/api/automation/'):
        return 'cron'
    if rule.startswith('/api/admin/'):
        return 'admin_api'
    if rule.startswith('/api/'):
        return 'api'
    if rule.startswith('/admin'):
        return 'admin'
    if rule in {'/', '/login', '/cliente-login', '/registro', '/privacy', '/terms', '/contact', '/responsible-gaming'}:
        return 'public'
    if rule.startswith('/telegram'):
        return 'telegram'
    if any(m in {'POST','PUT','PATCH','DELETE'} for m in methods):
        return 'action'
    return 'client'


def main() -> int:
    text = APP.read_text(encoding="utf-8", errors="replace")
    routes = []
    counts = Counter()
    missing_templates = []
    warnings = []
    template_uses = Counter()
    for match in ROUTE_RE.finditer(text):
        rule = match.group('rule')
        func = match.group('func')
        methods = methods_from_args(match.group('args'))
        body = function_body(text, func)
        b = bucket(rule, methods)
        counts[b] += 1
        tmpl = ''
        tm = TEMPLATE_RE.search(body)
        if tm:
            tmpl = tm.group(1)
            template_uses[tmpl] += 1
            if not (TEMPLATES / tmpl).exists():
                missing_templates.append({'route': rule, 'function': func, 'template': tmpl})
        if b == 'admin' and 'is_admin_session' not in body:
            warnings.append({'route': rule, 'function': func, 'issue': 'admin route without visible is_admin_session check'})
        if b == 'admin_api' and 'admin_json_forbidden' not in body and 'is_admin_session' not in body:
            warnings.append({'route': rule, 'function': func, 'issue': 'admin api without visible admin guard'})
        if b == 'cron' and 'automation_cron_access_allowed' not in body and 'automation_secret' not in body:
            warnings.append({'route': rule, 'function': func, 'issue': 'cron route without visible automation secret check'})
        routes.append({'rule': rule, 'function': func, 'methods': methods, 'bucket': b, 'template': tmpl})
    report = {
        'ok': not missing_templates,
        'version': VERSION,
        'total_routes': len(routes),
        'bucket_counts': dict(sorted(counts.items())),
        'missing_templates': missing_templates,
        'warnings': warnings[:100],
        'top_templates': [{'template': k, 'uses': v} for k, v in template_uses.most_common(20)],
        'route_map_available': '/admin/route-health' in [r['rule'] for r in routes],
        'api_route_health_available': '/api/admin/route-health' in [r['rule'] for r in routes],
        'routes': routes,
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / 'ROUTE_HEALTH_AUDIT_V730.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = [
        '# Route Health Audit V730', '',
        f'- Versión: `{VERSION}`',
        f'- Rutas: {len(routes)}',
        f'- Templates faltantes: {len(missing_templates)}',
        f'- Resultado: {"OK" if report["ok"] else "FAIL"}', '',
        '## Distribución por tipo',
    ]
    for k, v in sorted(counts.items()):
        lines.append(f'- `{k}`: {v}')
    lines += ['', '## Templates más usados']
    for item in report['top_templates'][:12]:
        lines.append(f'- `{item["template"]}`: {item["uses"]}')
    if missing_templates:
        lines += ['', '## Templates faltantes']
        for item in missing_templates:
            lines.append(f'- `{item["template"]}` usado por `{item["route"]}` / `{item["function"]}`')
    if warnings:
        lines += ['', '## Avisos']
        for item in warnings[:40]:
            lines.append(f'- `{item["route"]}` `{item["function"]}`: {item["issue"]}')
    (REPORTS / 'ROUTE_HEALTH_AUDIT_V730.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'routes'}, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
