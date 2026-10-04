"""Isolated visual review with empty sports data or a verified public cache snapshot.

Creates only local review accounts. Never seeds simulated matches or picks.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def prepare(port=54920, snapshot=None, template_ref=None):
    from tools.local_desktop.run_local_desktop import configure_local_environment
    configure_local_environment('OFFLINE_SAFE', port, 'premium_visual_' + secrets.token_hex(6) + '.sqlite')
    os.environ.update(BACKGROUND_JOBS_ENABLED='false', AUTO_GENERATE_PICKS='false',
                      AUTO_SEND_TELEGRAM_PICKS='false', ADMIN_EMAIL='visual@example.invalid',
                      ADMIN_PASSWORD=secrets.token_urlsafe(32))
    import app as module
    module.app.config['TEMPLATES_AUTO_RELOAD'] = True
    module.app.jinja_env.auto_reload = True
    module.seed_core()
    conn = module.db()
    from werkzeug.security import generate_password_hash
    for kind, username, role in [('client', 'cliente_local', 'FREE'), ('admin', 'admin_local', 'ADMIN')]:
        conn.execute('''INSERT OR IGNORE INTO users
            (id,name,username,email,password_hash,role,membership,membership_source,membership_note,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)''',
            ('visual-' + kind, 'Revisión local', username, kind + '@example.invalid',
             generate_password_hash(secrets.token_urlsafe(32)), role, role,
             'LOCAL_SAFE_QA', 'Cuenta local para revisión visual', module.now_iso()))
    conn.commit()
    counts = {table: conn.execute('SELECT count(*) FROM ' + table).fetchone()[0]
              for table in ('matches', 'picks')}
    conn.close()
    if any(counts.values()):
        raise RuntimeError('Visual preview requires an empty sports database')
    match_ids = []
    if snapshot:
        payload = json.loads(Path(snapshot).read_text(encoding='utf-8-sig'))
        if payload.get('no_external_calls') is not True or not payload.get('ok'):
            raise ValueError('Only a read-only public cache snapshot is supported')
        from tools.local_desktop.run_local_desktop import insert_row
        conn = module.db()
        # Retain published values and timestamps exactly. Never invent odds, picks,
        # events, lineups or statistics that the cache did not supply.
        for record in payload.get('matches', []):
            state = record.get('realtime_state') or {}
            match_id = record.get('id')
            if not match_id or not record.get('source'):
                continue
            insert_row(conn, 'matches', {
                'id': match_id, 'source': record['source'], 'home_team': record.get('home_team'),
                'away_team': record.get('away_team'), 'competition_name': record.get('competition'),
                'competition_id': state.get('competition_id'), 'home_team_id': state.get('home_team_id'),
                'away_team_id': state.get('away_team_id'), 'match_date': record.get('match_date'),
                'kickoff_time': record.get('kickoff_time'), 'kickoff_iso': state.get('kickoff_madrid'),
                'status': record.get('status'), 'minute': record.get('minute'),
                'home_score': record.get('home_score'), 'away_score': record.get('away_score'),
                'updated_at': record.get('updated_at'), 'last_synced_at': record.get('last_synced_at'),
                'raw_json': json.dumps(record), 'external_id': state.get('fixture_id'),
                'legal_note': 'Local review snapshot of the public application cache; original timestamps retained.'
            })
            cached = (payload.get('match_details') or {}).get(match_id)
            if cached:
                if cached.get('side_effects') != {'database_writes': 0, 'external_calls': 0}:
                    raise ValueError('Detail must be a read-only cache response')
                full = (cached.get('detail') or {}).get('match') or {}
                if full.get('id') != match_id:
                    raise ValueError('Cached detail identity mismatch')
                insert_row(conn, 'matches', {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in full.items()})
            match_ids.append(match_id)
        conn.commit()
        conn.close()
    if template_ref:
        import subprocess
        from jinja2 import ChoiceLoader, DictLoader
        from flask import Response, request
        import io, tarfile
        archive = subprocess.check_output(['git', 'archive', template_ref, 'templates'])
        with tarfile.open(fileobj=io.BytesIO(archive)) as files:
            historical = {member.name.removeprefix('templates/'): files.extractfile(member).read().decode('utf-8')
                          for member in files.getmembers() if member.isfile() and member.name.endswith('.html')}
        module.app.jinja_env.loader = ChoiceLoader([DictLoader(historical), module.app.jinja_env.loader])
        original_sources = json.loads(subprocess.check_output(['git', 'show', template_ref + ':tools/visual_css_sources.json']))
        original_sources.extend(['product-system.css', 'admin-master-control.css', 'founder-os.css', 'combinadas.css', 'platform-help.css'])
        original_css = {name: subprocess.check_output(['git', 'show', template_ref + ':static/' + name]) for name in original_sources}
        @module.app.before_request
        def historical_styles():
            if request.endpoint == 'static' and request.view_args.get('filename') in original_css:
                return Response(original_css[request.view_args['filename']], mimetype='text/css')
    module.app.config['VISUAL_REVIEW_MATCH_IDS'] = list((payload.get('match_details') or {}).keys()) + [i for i in match_ids if i not in (payload.get('match_details') or {})] if snapshot else []
    return module


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--port', type=int, default=54920)
    parser.add_argument('--template-ref')
    parser.add_argument('--metadata', type=Path)
    args = parser.parse_args()
    module = prepare(port=args.port, snapshot=args.snapshot, template_ref=args.template_ref)
    metadata = args.metadata or ROOT / 'data/local_dev/visual-preview.json'
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(json.dumps({'port': args.port, 'token': os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'],
                                   'match_ids': module.app.config['VISUAL_REVIEW_MATCH_IDS']}))
    module.app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)
