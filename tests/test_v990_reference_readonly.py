"""Reference reads are exact, bounded and local; observations remain intact."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from engines import data_vault_engine as vault
from engines.fixture_snapshot_read_model import prepare_fixture_snapshot
from engines.v935_launch_trust_engine import match_kickoff_madrid


class ReferenceReadOnlyContracts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='nemesis-v990-reference-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'synthetic.sqlite'
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('CREATE TABLE competitions(key TEXT, name TEXT, country TEXT, source TEXT, external_id TEXT)')
            conn.execute('INSERT INTO competitions VALUES (?,?,?,?,?)',
                         ('laliga', 'LaLiga', 'Spain', 'API_FOOTBALL', '140'))

    def test_official_readonly_adapter_never_creates_a_missing_database(self):
        absent = self.path.parent / 'must-not-exist.sqlite'
        with self.assertRaises(sqlite3.OperationalError):
            vault.read_competition_references(absent, ('laliga',))
        self.assertFalse(absent.exists())

    def test_official_connection_rejects_writes_and_preserves_database_bytes(self):
        before = self.path.read_bytes()
        with closing(vault.connect_readonly(self.path)) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM competitions")
        result = vault.read_competition_references(self.path, ('laliga',))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['external_id'], '140')
        self.assertEqual(self.path.read_bytes(), before)

    def test_exact_primary_keys_are_bound_not_interpolated_or_looked_up_by_name(self):
        injected = "x'); DELETE FROM competitions; --"
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('INSERT INTO competitions VALUES (?,?,?,?,?)',
                         (injected, 'Synthetic exact key', 'Spain', 'API_FOOTBALL', '999'))
        before = self.path.read_bytes()
        records = vault.read_competition_references(self.path, tuple(sorted((injected, 'laliga'))))
        self.assertEqual({item['key'] for item in records}, {injected, 'laliga'})
        self.assertEqual(vault.read_competition_references(self.path, ('LaLiga',)), ())
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_or_empty_key_requests_never_open_a_connection(self):
        invalid = [[], ('laliga', 'laliga'), ('z', 'a'), ('',), ('x\x00y',),
                   ('a' * 257,), (True,), tuple(str(i) for i in range(501))]
        with patch.object(vault, 'connect_readonly', side_effect=AssertionError('unexpected read')) as read:
            for keys in invalid:
                with self.subTest(keys_type=type(keys).__name__, count=len(keys)):
                    with self.assertRaises((TypeError, ValueError)):
                        vault.read_competition_references(self.path, keys)
            self.assertEqual(vault.read_competition_references(self.path, ()), ())
        read.assert_not_called()

    def test_missing_reference_table_is_unavailable_not_a_verified_empty_catalogue(self):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('DROP TABLE competitions')
        row = self.observation('missing')
        snapshot = prepare_fixture_snapshot({'current': [row]},
            lambda keys: vault.read_competition_references(self.path, keys),
            kickoff_for=match_kickoff_madrid)
        self.assertEqual(snapshot.context.read_state, 'UNAVAILABLE')
        self.assertEqual(snapshot.context_for(row).state, 'UNKNOWN_READ_UNAVAILABLE')
        selection = snapshot.select('current')
        self.assertEqual(selection.count, 1)
        self.assertIs(selection.rows[0], row)
        self.assertEqual(selection.confirmed_count, 0)

    def test_current_800_and_history_400_are_preserved_with_one_exact_reference_read(self):
        current = [self.observation('current-' + str(i), i) for i in range(800)]
        history = [self.observation('history-' + str(i), i + 800) for i in range(400)]
        before = deepcopy((current, history))
        calls = []
        def read(keys):
            calls.append(keys)
            return vault.read_competition_references(self.path, keys)
        snapshot = prepare_fixture_snapshot({'current': current, 'history': history}, read,
                                            kickoff_for=match_kickoff_madrid)
        self.assertEqual(calls, [('laliga',)])
        self.assertEqual(snapshot.context.lookup_calls, 1)
        self.assertEqual(len(snapshot.cohorts['current']), 800)
        self.assertEqual(len(snapshot.cohorts['history']), 400)
        for name, original in (('current', current), ('history', history)):
            self.assertTrue(all(a is b for a, b in zip(snapshot.cohorts[name], original)))
            self.assertEqual(snapshot.select(name).count, len(original))
        self.assertEqual((current, history), before)
        self.assertEqual(snapshot.identity_coverage['observations'], 1200)
        self.assertEqual(snapshot.identity_coverage['resolved'], 1200)
        self.assertNotIn('raw_json', snapshot.identity_coverage)

    @staticmethod
    def observation(identifier, offset=0):
        return {'id': identifier, 'source': 'API_FOOTBALL', 'competition_id': '140',
                'competition_key': 'laliga', 'country': 'Spain', 'competition_name': 'LaLiga',
                'home_team': 'Synthetic Home ' + str(offset), 'away_team': 'Synthetic Away ' + str(offset),
                'kickoff_iso': datetime(2099, 1, 1, 20, tzinfo=timezone.utc).isoformat(),
                'status': 'NS', 'quote': {'id': 'quote-' + identifier, 'price': 2.0},
                'provider_quota': {'remaining': 17}}


if __name__ == '__main__':
    unittest.main()
