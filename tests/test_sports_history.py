import json
import sqlite3
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from engines.sports_history_engine import (
    ensure_schema, entity, ingest_match, team_metrics, record_coverage,
    persist_detail, match_details, backfill_page, history_summary, match_history,
)


class SportsHistoryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        ensure_schema(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def fixture(self, number=1, **changes):
        return dict(provider='sportsdb', external_id=str(number), internal_match_id=str(number),
                    league_id='4335', league_name='LaLiga', season='2026-2027',
                    home_team_id='h', away_team_id='a', home_team='Home', away_team='Away',
                    kickoff_iso=f'2026-09-{number:02}T19:00:00Z', status='FT', home_score=2, away_score=1, **changes)

    def add(self, number=1, **changes):
        item = self.fixture(number)
        item.update(changes)
        identifier = ingest_match(self.conn, item)
        self.conn.commit()
        return identifier

    def scope(self):
        return self.conn.execute('SELECT home,competition,season FROM sports_history_matches LIMIT 1').fetchone()

    def test_counts_windows_home_away_and_streak(self):
        for i in range(1, 22):
            self.add(i, home_score=0 if i < 4 else 2, away_score=0 if i < 4 else 1)
        result = team_metrics(self.conn, *self.scope())
        self.assertEqual((result['played'], result['wins'], result['draws'], result['losses']), (21,18,3,0))
        self.assertTrue(result['coherent'])
        self.assertEqual((result['gf'], result['ga']), (36,18))
        self.assertEqual(result['windows']['5']['played'],5)
        self.assertEqual(result['windows']['10']['played'],10)
        self.assertEqual(result['windows']['20']['played'],20)
        self.assertEqual(result['streak']['length'],18)
        self.assertEqual(result['home']['played'],21)
        self.assertEqual(result['away']['played'],0)
        away = self.conn.execute('SELECT away FROM sports_history_matches LIMIT 1').fetchone()[0]
        self.assertEqual(team_metrics(self.conn, away, *self.scope()[1:])['losses'],18)

    def test_unknown_score_is_not_zero_and_live_not_result(self):
        self.add(1,home_score=None)
        self.add(2,status='LIVE')
        self.add(3,home_score=0,away_score=0)
        result = team_metrics(self.conn,*self.scope())
        self.assertEqual(result['played'],1)
        self.assertEqual(result['draws'],1)
        self.assertEqual(result['unscored'],1)
        self.assertEqual(result['coverage'],'partial')

    def test_partial_expected_five_with_two_confirmed(self):
        self.add(1)
        self.add(2)
        record_coverage(self.conn,*self.scope(),source='standings',expected=5,verified_complete=True)
        result=team_metrics(self.conn,*self.scope())
        self.assertEqual((result['played'],result['missing'],result['coverage']),(2,3,'partial'))
        record_coverage(self.conn,*self.scope(),source='standings',expected=2,verified_complete=True)
        self.assertEqual(team_metrics(self.conn,*self.scope())['coverage'],'complete')

    def test_idempotent_no_history_loss_and_terminal_protection(self):
        first=self.add(1)
        self.add(2)
        self.assertEqual(first,self.add(1,status='PROGRAMADO',home_score=None,away_score=None))
        self.assertEqual(team_metrics(self.conn,*self.scope())['played'],2)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM sports_history_matches').fetchone()[0],2)
        self.add(1,home_score=3,away_score=1)
        self.assertEqual(team_metrics(self.conn,*self.scope())['gf'],5)

    def test_canonical_dedupe_requires_team_links(self):
        first=self.add(1)
        home,comp,season=self.scope()
        away=self.conn.execute('SELECT away FROM sports_history_matches').fetchone()[0]
        entity(self.conn,'team','odds','oh',canonical_id=home)
        entity(self.conn,'team','odds','oa',canonical_id=away)
        item=self.fixture(1)
        item.update(provider='odds',external_id='other',league_id='soccer_spain_la_liga',home_team_id='oh',away_team_id='oa',kickoff_iso='2026-09-01T21:00:00+02:00')
        self.assertEqual(ingest_match(self.conn,item),first)
        self.assertEqual(team_metrics(self.conn,home,comp,season)['played'],1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sports_history_ids WHERE kind='match'").fetchone()[0],2)

    def test_names_dont_merge_provider_entities_or_gender(self):
        a=entity(self.conn,'team','sportsdb','1',{'name':'United'})
        b=entity(self.conn,'team','odds','1',{'name':'United'})
        self.assertNotEqual(a,b)
        with self.assertRaises(ValueError):
            entity(self.conn,'player','odds','1',canonical_id=a)
        with self.assertRaises(ValueError):
            entity(self.conn,'team','odds','1',canonical_id=a)

    def test_previous_season_and_h2h_no_future_leak(self):
        self.add(1)
        self.add(2,season='2025-2026')
        self.add(3)
        team,comp,season=self.scope()
        self.assertEqual(team_metrics(self.conn,team,comp,'2025-2026')['played'],1)
        self.assertEqual(team_metrics(self.conn,team,comp,season,before='2026-09-03T19:00:00+00:00')['played'],1)
        self.assertEqual(team_metrics(self.conn,team,comp,season,opponent='unknown')['played'],0)

    def test_details_retention_and_confirmed_pitch(self):
        identifier=self.add(1)
        self.assertFalse(persist_detail(self.conn,identifier,'odds','odds','x',{'price':2}))
        persist_detail(self.conn,identifier,'lineups','sportsdb','l',{'confirmed':False})
        self.assertEqual(match_details(self.conn,identifier)['lineups'],[])
        persist_detail(self.conn,identifier,'lineups','sportsdb','l',{'confirmed':True,'formation':'4-4-2','starters':[]})
        self.assertEqual(len(match_details(self.conn,identifier)['lineups']),1)
        persist_detail(self.conn,identifier,'events','sportsdb','e',{'type':'VAR','minute':91})
        self.assertEqual(match_details(self.conn,identifier)['events'][0]['payload']['type'],'VAR')

    def test_backfill_cache_idempotence_persistent_budget_and_failure(self):
        calls=[]
        def fetch(scope,page):
            calls.append(page)
            return [self.fixture(1)]
        args=dict(budget=1,timestamp=1790000000)
        self.assertEqual(backfill_page(self.conn,'sportsdb','4335/2026','1',fetch,ingest_match,**args)['status'],'success')
        self.assertEqual(backfill_page(self.conn,'sportsdb','4335/2026','1',fetch,ingest_match,**args)['calls'],0)
        self.assertEqual(backfill_page(self.conn,'sportsdb','4335/2026','2',fetch,ingest_match,**args)['status'],'budget_exhausted')
        self.assertEqual(len(calls),1)
        def fail(scope,page):
            raise RuntimeError('secret provider message')
        args['budget']=2
        result=backfill_page(self.conn,'sportsdb','4335/2026','2',fail,ingest_match,**args)
        self.assertEqual(result,dict(status='error',calls=1))
        self.assertEqual(backfill_page(self.conn,'sportsdb','4335/2026','3',fetch,ingest_match,**args)['status'],'budget_exhausted')

    def test_failed_batch_is_atomic_and_doesnt_clear_existing(self):
        self.add(1)
        def fetch(scope,page):
            return [self.fixture(2),{'bad':'data'}]
        self.assertEqual(backfill_page(self.conn,'sportsdb','scope','1',fetch,ingest_match,budget=1,timestamp=1790000000)['status'],'error')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM sports_history_matches').fetchone()[0],1)

    def test_read_only_views_no_schema_creation(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'history.db'
            sqlite3.connect(path).close()
            self.assertFalse(history_summary(path)['available'])
            self.assertEqual(match_history(path,'1'),{})
            conn=sqlite3.connect(path)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM sqlite_master').fetchone()[0],0)
            ensure_schema(conn)
            ingest_match(conn,self.fixture(1))
            ingest_match(conn,self.fixture(2))
            conn.commit()
            self.assertEqual(match_history(path,'2')['home']['played'],1)
            self.assertTrue(history_summary(path)['available'])
            conn.close()

    def test_provider_adapters_never_infer_finished_or_season(self):
        from engines.sports_history_adapters import odds_event, sportsdb_event
        odds = odds_event({'id':'x','sport_key':'soccer_epl','home_team':'A','away_team':'B','commence_time':'2020-01-01T12:00:00Z'})
        self.assertEqual(odds['status'],'unknown')
        self.assertIsNone(odds['season'])
        self.assertIsNone(odds['home_score'])
        self.assertNotIn('odds',odds)
        sports = sportsdb_event({'idEvent':'x','intHomeScore':'0','intAwayScore':None})
        self.assertEqual(sports['home_score'],'0')
        self.assertIsNone(sports['away_score'])

    def test_warehouse_sync_persists_and_protects_terminal_scores(self):
        from engines.football_data_warehouse_engine import ensure_football_warehouse_schema, _upsert_match, sync_football_data_warehouse
        with TemporaryDirectory() as directory:
            path=str(Path(directory)/'warehouse.db')
            ensure_football_warehouse_schema(path)
            conn=sqlite3.connect(path)
            try:
                _upsert_match(conn,self.fixture(1))
                conn.commit()
                incomplete=self.fixture(1)
                incomplete.update(status='scheduled',home_score=None,away_score=None)
                _upsert_match(conn,incomplete)
                conn.commit()
                self.assertEqual(conn.execute('SELECT home_score,away_score FROM football_matches_history').fetchone(),(2,1))
                self.assertEqual(team_metrics(conn,*conn.execute('SELECT home,competition,season FROM sports_history_matches').fetchone())['played'],1)
            finally:
                conn.close()
            sync_football_data_warehouse(path,include_api_football=False)
            self.assertTrue(history_summary(path)['available'])

    def test_daily_snapshot_boundary_and_existing_replay(self):
        from engines.sports_history_engine import remember_sports_match
        from tools.import_sports_history import import_existing
        with TemporaryDirectory() as directory:
            path=str(Path(directory)/'snapshot.db')
            original=self.fixture(1)
            original.update(id='internal',source='sportsdb',competition_id='4335')
            remember_sports_match(path,original)
            self.assertTrue(history_summary(path)['available'])
            self.assertEqual(import_existing(path)['external_calls'],0)

    def test_component_renders_partial_and_admin_without_network(self):
        from jinja2 import Environment, FileSystemLoader
        env=Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1]/'templates')), autoescape=True)
        env.filters['madrid_datetime_label']=str
        self.add(1)
        metrics=team_metrics(self.conn,*self.scope())
        rendered=env.get_template('components/sports_history.html').module.team_history(metrics,'Example')
        self.assertIn('Cobertura parcial',rendered)
        self.assertIn('1 resultados confirmados',rendered)

    def test_budget_survives_connection_restart_and_next_day(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'backfill.db'
            conn=sqlite3.connect(path)
            ensure_schema(conn)
            conn.commit()
            result=backfill_page(conn,'odds','scope',1,lambda s,p:[],ingest_match,budget=1,timestamp=1790000000)
            self.assertEqual(result['calls'],1)
            conn.close()
            conn=sqlite3.connect(path)
            try:
                self.assertEqual(backfill_page(conn,'odds','scope',2,lambda s,p:[],ingest_match,budget=1,timestamp=1790000001)['calls'],0)
                self.assertEqual(backfill_page(conn,'odds','scope',1,lambda s,p:[],ingest_match,budget=1,timestamp=1790086401)['calls'],1)
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM sports_history_call_ledger').fetchone()[0],2)
            finally:
                conn.close()

    def test_archive_match_center_survives_current_fixture_disappearance(self):
        from engines.sports_history_engine import historical_match_detail, remember_sports_match
        from engines.match_context_engine import build_match_context
        with TemporaryDirectory() as directory:
            path=str(Path(directory)/'archive.db')
            original=self.fixture(1)
            original.update(id='original',source='sportsdb',competition_id='4335')
            remember_sports_match(path,original)
            detail=historical_match_detail(path,'original')
            self.assertEqual(detail['match']['home_score'],2)
            self.assertEqual(detail['match']['home_team'],'Home')
            self.assertTrue(detail['historical_archive'])
            self.assertIsNone(historical_match_detail(path,'unknown'))
            context=build_match_context(detail)
            self.assertIsInstance(context,dict)


if __name__ == '__main__':
    unittest.main()

