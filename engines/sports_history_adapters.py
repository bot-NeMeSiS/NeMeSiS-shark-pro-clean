"""Pure adapters for supplied provider responses; no transport or plan changes."""
from engines.sports_history_engine import ingest_match


def sportsdb_event(event):
    return {
        'provider': 'thesportsdb', 'external_id': event.get('idEvent'),
        'league_id': event.get('idLeague'), 'league_name': event.get('strLeague'),
        'season': event.get('strSeason'), 'round_name': event.get('intRound'),
        'home_team_id': event.get('idHomeTeam'), 'away_team_id': event.get('idAwayTeam'),
        'home_team': event.get('strHomeTeam'), 'away_team': event.get('strAwayTeam'),
        'home_score': event.get('intHomeScore'), 'away_score': event.get('intAwayScore'),
        'status': event.get('strStatus'), 'kickoff_iso': event.get('strTimestamp'),
        'match_date': event.get('dateEvent'), 'venue': event.get('strVenue'),
        'venue_id': event.get('idVenue'), 'competition_logo': event.get('strLeagueBadge'),
        'home_logo': event.get('strHomeTeamBadge'), 'away_logo': event.get('strAwayTeamBadge'),
    }


def odds_event(event, *, season=None, team_ids=None):
    """Odds does not supply season or team IDs. Caller must supply verified links.

    Prices are deliberately excluded unless an authorized normalized detail
    includes explicit retention permission. Commence time never implies FT.
    """
    ids = team_ids or {}
    scores = {score.get('name'): score.get('score') for score in event.get('scores') or []}
    return {
        'provider': 'the_odds_api', 'external_id': event.get('id'),
        'league_id': event.get('sport_key'), 'league_name': event.get('sport_title'),
        'season': season, 'kickoff_iso': event.get('commence_time'),
        'home_team': event.get('home_team'), 'away_team': event.get('away_team'),
        'home_team_id': ids.get(event.get('home_team')), 'away_team_id': ids.get(event.get('away_team')),
        'status': 'FT' if event.get('completed') is True else 'unknown',
        'home_score': scores.get(event.get('home_team')), 'away_score': scores.get(event.get('away_team')),
    }


def ingest_sportsdb(conn, event):
    return ingest_match(conn, sportsdb_event(event))


def ingest_odds(conn, event):
    return ingest_match(conn, odds_event(event))
