import contextlib
import io
import json
import sqlite3
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from engines.sports_history_engine import ensure_schema, ingest_match, entity, team_metrics, backfill_page, persist_detail, historical_match_detail
from engines.sports_history_reconciliation import reconcile_identity, resolve
from engines.sports_history_backfill import run_season_backfill


def fixture(source='sportsdb', external='s', home='h', away='a', internal='internal-s', hs=2):
    return dict(provider=source,external_id=external,internal_match_id=internal,
                league_id='4335' if source=='sportsdb' else 'soccer_spain_la_liga',league_name='LaLiga',
                season='2026-2027',home_team_id=home,away_team_id=away,home_team='Home',away_team='Away',
                kickoff_iso='2026-09-01T19:00:00Z',status='FT',home_score=hs,away_score=1)


class HistoryOperationsTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(':memory:')
        ensure_schema(self.conn)
        self.s=ingest_match(self.conn,fixture())
        self.o=ingest_match(self.conn,fixture('odds','o','oh','oa','internal-o'))
        self.home,self.away,self.comp=self.conn.execute('SELECT home,away,competition FROM sports_history_matches WHERE id=?',(self.s,)).fetchone()
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def link(self,external,target):
        return reconcile_identity(self.conn,'team','odds',external,target,'reviewed-provider-cross-reference')

    def test_existing_entities_reconcile_and_matches_count_once(self):
        self.assertEqual(self.link('oh',self.home)['merged_matches'],0)
        result=self.link('oa',self.away)
        self.assertEqual(result['merged_matches'],1)
        self.assertEqual(team_metrics(self.conn,self.home,self.comp,'2026-2027')['played'],1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM sports_history_matches').fetchone()[0],2)
        self.assertEqual(resolve(self.conn,self.o),resolve(self.conn,self.s))
        snapshot=json.loads(self.conn.execute('SELECT snapshot FROM sports_history_identity_audit WHERE id=?',(result['audit_id'],)).fetchone()[0])
        self.assertTrue(snapshot['before']['matches'])
        self.assertEqual(len(snapshot['merged_matches']),1)
        self.assertEqual(self.link('oa',self.away)['status'],'already_linked')

    def test_conflicting_final_scores_roll_back_whole_link(self):
        self.conn.execute('UPDATE sports_history_matches SET home_score=5 WHERE id=?',(self.o,))
        self.link('oh',self.home)
        old=self.conn.execute("SELECT canonical_id FROM sports_history_ids WHERE source='the_odds_api' AND kind='team' AND external_id='oa'").fetchone()[0]
        with self.assertRaises(ValueError):
            self.link('oa',self.away)
        self.assertEqual(resolve(self.conn,old),old)
        self.assertEqual(self.conn.execute('SELECT away FROM sports_history_matches WHERE id=?',(self.o,)).fetchone()[0],old)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sports_history_redirects WHERE kind='match'").fetchone()[0],0)

    def test_opponents_and_type_mismatch_require_review(self):
        with self.assertRaises(ValueError):
            reconcile_identity(self.conn,'team','sportsdb','h',self.away,'reviewed-cross-reference')
        with self.assertRaises(ValueError):
            reconcile_identity(self.conn,'player','odds','p',self.home,'reviewed-cross-reference')
        with self.assertRaises(ValueError):
            self.link('oh','missing')
        with self.assertRaises(ValueError):
            reconcile_identity(self.conn,'team','odds','oh',self.home,'')

    def test_detail_rows_preserved_and_copied_after_dedupe(self):
        persist_detail(self.conn,self.o,'events','odds','goal',{'type':'Goal','minute':8})
        self.link('oh',self.home)
        self.link('oa',self.away)
        active=resolve(self.conn,self.o)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM sports_history_details WHERE match_id=?',(active,)).fetchone()[0],1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sports_history_details WHERE match_id=?",(self.o,)).fetchone()[0],1)
        # Replaying either source must not recreate an active duplicate.
        ingest_match(self.conn,fixture('odds','o','oh','oa','internal-o'))
        self.assertEqual(team_metrics(self.conn,self.home,self.comp,'2026-2027')['played'],1)

    def test_no_source_ids_are_invented_and_player_links_supported(self):
        player=entity(self.conn,'player','sportsdb','p',{'name':'Player'})
        result=reconcile_identity(self.conn,'player','other','known-provider-player',player,'verified-player-id-reference')
        self.assertEqual(result['merged_matches'],0)
        self.assertEqual(entity(self.conn,'player','other','known-provider-player'),player)

    def test_old_internal_urls_still_reach_archive_after_merging(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'archive.db'
            with contextlib.closing(sqlite3.connect(path)) as target:
                self.link('oh',self.home)
                self.link('oa',self.away)
                self.conn.commit()
                self.conn.backup(target)
            for identifier in ('internal-o','internal-s',self.o,self.s):
                self.assertEqual(historical_match_detail(path,identifier)['match']['home_score'],2)

    def test_budget_rolls_over_at_madrid_midnight(self):
        stamp=datetime.fromisoformat('2026-10-03T21:59:59+00:00').timestamp()
        self.assertEqual(backfill_page(self.conn,'sportsdb','scope',1,lambda s,p:[],ingest_match,budget=1,timestamp=stamp)['calls'],1)
        self.assertEqual(backfill_page(self.conn,'sportsdb','scope',2,lambda s,p:[],ingest_match,budget=1,timestamp=stamp+2)['calls'],1)
        self.assertEqual(backfill_page(self.conn,'sportsdb','scope',3,lambda s,p:[],ingest_match,budget=1,timestamp=stamp+7202)['status'],'budget_exhausted')

    def test_expired_worker_cannot_overwrite_successor(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'leases.db'
            with contextlib.closing(sqlite3.connect(path)) as conn:
                ensure_schema(conn)
                conn.commit()
                def slow(scope,page):
                    with contextlib.closing(sqlite3.connect(path)) as successor:
                        result=backfill_page(successor,'sportsdb','scope',1,lambda s,p:[fixture(hs=4)],ingest_match,budget=2,timestamp=1790000002,ttl=1)
                        self.assertEqual(result['status'],'success')
                    return [fixture(hs=2)]
                result=backfill_page(conn,'sportsdb','scope',1,slow,ingest_match,budget=2,timestamp=1790000000,ttl=1)
                self.assertEqual(result['status'],'superseded')
                self.assertEqual(conn.execute('SELECT home_score FROM sports_history_matches').fetchone()[0],4)

    def test_backfill_single_transport_call_cached_and_strict_scope(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'season.db'
            calls=[]
            def fetch(endpoint,params):
                calls.append((endpoint,params))
                return {'events':[dict(idEvent='1',idLeague='4335',strSeason='2026-2027',idHomeTeam='h',idAwayTeam='a',strHomeTeam='Home',strAwayTeam='Away',strTimestamp='2026-09-01T19:00:00Z',strStatus='FT',intHomeScore='2',intAwayScore='1')]}
            result=run_season_backfill(path,'4335','2026-2027',budget=1,timestamp=1790000000,transport=fetch)
            self.assertEqual(result['status'],'success')
            self.assertEqual(run_season_backfill(path,'4335','2026-2027',budget=1,timestamp=1790000000,transport=fetch)['calls'],0)
            self.assertEqual(len(calls),1)
            result=run_season_backfill(path,'4335','2025-2026',budget=2,timestamp=1790000000,transport=fetch)
            self.assertEqual(result['status'],'error')
            with contextlib.closing(sqlite3.connect(path)) as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM sports_history_matches').fetchone()[0],1)

    def test_cli_preview_does_not_open_database_or_call_provider(self):
        from tools.backfill_sports_history import main
        with TemporaryDirectory() as folder:
            path=Path(folder)/'not-created.db'
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code=main(['--database',str(path),'--league-id','4335','--season','2025-2026','--max-calls-per-day','1'])
            self.assertEqual(code,0)
            self.assertFalse(path.exists())
            self.assertEqual(json.loads(output.getvalue())['external_calls'],0)

    def standings(self,played=1,wins=1,draws=0,losses=0,gf=2):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS football_standings_history
            (provider TEXT,league_id TEXT,league_name TEXT,season TEXT,team_id TEXT,team_name TEXT,
             played INTEGER,wins INTEGER,draws INTEGER,losses INTEGER,goals_for INTEGER,goals_against INTEGER,snapshot_at TEXT)''')
        self.conn.execute('INSERT INTO football_standings_history VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          ('sportsdb','4335','LaLiga','2026-2027','h','Home',played,wins,draws,losses,gf,1,'2026-09-02T10:00:00+00:00'))

    def test_standings_expected_counts_and_partial_missing_results(self):
        from engines.sports_history_engine import sync_standings_coverage
        self.standings(played=5,wins=3,draws=1,losses=1)
        sync_standings_coverage(self.conn)
        metrics=team_metrics(self.conn,self.home,self.comp,'2026-2027')
        self.assertEqual((metrics['missing'],metrics['coverage']),(4,'partial'))

    def test_standings_cannot_certify_inconsistent_counts_or_goals(self):
        from engines.sports_history_engine import sync_standings_coverage
        self.standings(played=1,wins=0,draws=1,gf=2)
        sync_standings_coverage(self.conn)
        metrics=team_metrics(self.conn,self.home,self.comp,'2026-2027')
        self.assertEqual(metrics['coverage'],'partial')
        self.assertEqual(metrics['coverage_issue'],'standings_results_mismatch')
        self.conn.execute('DELETE FROM football_standings_history')
        self.standings(gf=9)
        sync_standings_coverage(self.conn)
        self.assertEqual(team_metrics(self.conn,self.home,self.comp,'2026-2027')['coverage'],'partial')
        self.conn.execute('DELETE FROM football_standings_history')
        self.standings()
        sync_standings_coverage(self.conn)
        self.assertEqual(team_metrics(self.conn,self.home,self.comp,'2026-2027')['coverage'],'complete')

    def test_archive_details_fill_existing_components_without_restoring_picks(self):
        from engines.sports_history_match_center import attach_archived_sports_details
        from engines.match_context_engine import build_match_context
        with TemporaryDirectory() as folder:
            path=Path(folder)/'details.db'
            with contextlib.closing(sqlite3.connect(path)) as conn:
                ensure_schema(conn)
                match=ingest_match(conn,fixture())
                persist_detail(conn,match,'events','sportsdb','event',{'type':'Goal','minute':8,'team_name':'Home','player_name':'Player'})
                persist_detail(conn,match,'lineups','sportsdb','lineup',{'confirmed':True,'team_id':'h','team_name':'Home','formation':'4-4-2','starters':[{'id':'p','name':'Player','position':'GK'}]})
                persist_detail(conn,match,'statistics','sportsdb','stats',{'items':[{'label':'Shots on Goal','home':2,'away':1}]})
                persist_detail(conn,match,'picks','internal','private-pick',{'selection':'private-selection'})
                conn.commit()
            detail=historical_match_detail(path,'internal-s')
            attach_archived_sports_details(path,detail)
            self.assertEqual(len(detail['timeline']),1)
            self.assertEqual(len(detail['lineups']),1)
            self.assertTrue(detail['cached_statistics']['available'])
            self.assertNotIn('related_picks',detail)
            self.assertNotIn('private-selection',json.dumps(detail))
            context=build_match_context(detail)
            self.assertTrue(context['lineups']['confirmed'])
            self.assertTrue(context['statistics']['available'])

    def test_archive_does_not_overwrite_current_data_or_accept_unconfirmed_lineups(self):
        from engines.sports_history_match_center import attach_archived_sports_details
        with TemporaryDirectory() as folder:
            path=Path(folder)/'partial.db'
            with contextlib.closing(sqlite3.connect(path)) as conn:
                ensure_schema(conn)
                match=ingest_match(conn,fixture())
                persist_detail(conn,match,'lineups','sportsdb','bad',{'confirmed':'false','player_id':'p','player_name':'Player'})
                persist_detail(conn,match,'events','sportsdb','goal',{'type':'Goal','minute':8})
                conn.commit()
            detail=historical_match_detail(path,'internal-s')
            current=[{'type':'Card','source':'verified-current','minute':9}]
            detail['timeline']=current
            attach_archived_sports_details(path,detail)
            self.assertEqual(detail['timeline'],current)
            self.assertFalse(detail.get('lineups'))

    def test_raw_statistics_only_use_one_supplied_snapshot(self):
        from engines.sports_history_match_center import attach_archived_sports_details
        with TemporaryDirectory() as folder:
            path=Path(folder)/'stats.db'
            with contextlib.closing(sqlite3.connect(path)) as conn:
                ensure_schema(conn)
                match=ingest_match(conn,fixture())
                for number,team,value,captured in [(1,'Home','2','2026-09-01T20:00:00Z'),(2,'Away','1','2026-09-01T20:00:00Z'),(3,'Home','9','2026-09-01T21:00:00Z')]:
                    persist_detail(conn,match,'statistics','sportsdb',str(number),{'team_name':team,'stat_name':'Shots','stat_value':value,'captured_at':captured})
                conn.commit()
            detail=historical_match_detail(path,'internal-s')
            attach_archived_sports_details(path,detail)
            item=detail['cached_statistics']['items'][0]
            self.assertEqual(item['home'],'9')
            self.assertIsNone(item['away'])

    def test_team_center_uses_history_only_after_identity_reconciliation(self):
        from engines.sports_history_engine import team_history_snapshot
        with TemporaryDirectory() as folder:
            path=Path(folder)/'team.db'
            matches=[dict(id='internal-s',home_team='Home',away_team='Away'),dict(id='internal-o',home_team='Home',away_team='Away')]
            with contextlib.closing(sqlite3.connect(path)) as target:
                self.conn.backup(target)
            history=team_history_snapshot(path,'Home',matches)
            self.assertFalse(history['available'])
            self.assertTrue(history['requires_reconciliation'])
            self.link('oh',self.home)
            self.link('oa',self.away)
            self.conn.commit()
            with contextlib.closing(sqlite3.connect(path)) as target:
                self.conn.backup(target)
            history=team_history_snapshot(path,'Home',matches)
            self.assertTrue(history['available'])
            self.assertEqual(history['scopes'][0]['played'],1)
            self.assertFalse(team_history_snapshot(path,'unrelated',matches)['available'])

    def test_naive_or_invalid_dates_do_not_define_recent_windows(self):
        unknown=fixture(external='unknown',internal='unknown')
        unknown['kickoff_iso']='2026-09-02T20:00:00'
        ingest_match(self.conn,unknown)
        metrics=team_metrics(self.conn,self.home,self.comp,'2026-2027')
        self.assertEqual(metrics['played'],2)
        self.assertEqual(metrics['windows']['5']['played'],1)
        self.assertTrue(metrics['chronology_partial'])
        self.assertEqual(metrics['streak']['coverage'],'partial')
        self.assertEqual(team_metrics(self.conn,self.home,self.comp,'2026-2027',before='2026-09-03T20:00:00+00:00')['played'],1)


if __name__ == '__main__':
    unittest.main()
