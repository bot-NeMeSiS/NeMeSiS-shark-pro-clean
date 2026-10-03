"""Offline visual review of real structural entities and empty sports data.

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


def prepare(port=54920, snapshot=None):
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
            match_ids.append(match_id)
        conn.commit()
        conn.close()
    module.app.config['VISUAL_REVIEW_MATCH_IDS'] = match_ids
    return module


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    module = prepare(snapshot=args.snapshot)
    metadata = ROOT / 'data/local_dev/visual-preview.json'
    metadata.write_text(json.dumps({'port': 54920, 'token': os.environ['NEMESIS_LOCAL_ACCESS_TOKEN'],
                                   'match_ids': module.app.config['VISUAL_REVIEW_MATCH_IDS']}))
    module.app.run(host='127.0.0.1', port=54920, debug=False, use_reloader=False)
