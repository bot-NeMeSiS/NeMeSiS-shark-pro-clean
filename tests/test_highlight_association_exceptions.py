import sqlite3
from engines.sportsdb_highlights_engine import ensure_sportsdb_highlights_schema
from engines.highlight_review_engine import review_snapshot


def test_unlinked_filter_finds_old_exception_hidden_by_recent_rows(tmp_path):
    path = tmp_path / 'media.sqlite'
    ensure_sportsdb_highlights_schema(path)
    with sqlite3.connect(path) as conn:
        for index in range(45):
            conn.execute('INSERT INTO sportsdb_match_highlights(id,match_id,updated_at,title) VALUES(?,?,?,?)',
                         (str(index), 'm' if index else '', f'2026-10-03T10:{index:02d}:00', str(index)))
    recent = review_snapshot(path)
    assert '0' not in {row['id'] for row in recent['items']}
    snapshot = review_snapshot(path, unlinked=True)
    assert snapshot['counts'] == {'stored': 45, 'unlinked': 1}
    assert [row['id'] for row in snapshot['items']] == ['0']
    assert snapshot['items'][0]['can_display'] is False
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT COUNT(*) FROM sportsdb_match_highlights').fetchone()[0] == 45
