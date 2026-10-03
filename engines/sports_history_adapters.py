"""Pure adapters for supplied provider responses; no transport or plan changes."""
from engines.sports_history_engine import entity, ingest_match, link_entities


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



def sportsdb_team_profile(item):
    """Normalize one provider-confirmed team profile without transport."""
    item = dict(item or {})
    return {
        "external_id": str(item.get("idTeam") or item.get("external_id") or item.get("id") or "").strip(),
        "name": item.get("strTeam") or item.get("name") or "",
        "short_name": item.get("strTeamShort") or "",
        "alternate_name": item.get("strTeamAlternate") or "",
        "country": item.get("strCountry") or item.get("country") or "",
        "league_id": str(item.get("idLeague") or item.get("league_id") or "").strip(),
        "league_name": item.get("strLeague") or item.get("league") or item.get("league_name") or "",
        "formed_year": item.get("intFormedYear") or item.get("formed_year") or item.get("founded") or "",
        "stadium_name": item.get("strStadium") or item.get("stadium_name") or item.get("stadium") or "",
        "stadium_id": str(item.get("idVenue") or item.get("idStadium") or item.get("stadium_id") or "").strip(),
        "stadium_location": item.get("strStadiumLocation") or item.get("stadium_location") or "",
        "stadium_capacity": item.get("intStadiumCapacity") or item.get("stadium_capacity") or "",
        "logo": item.get("strBadge") or item.get("strTeamBadge") or item.get("strLogo") or item.get("logo_url") or item.get("logo") or "",
        "jersey": item.get("strEquipment") or item.get("jersey") or "",
        "website": item.get("strWebsite") or item.get("website") or "",
        "coach": item.get("strManager") or item.get("strCoach") or item.get("coach") or "",
        "description_es": item.get("strDescriptionES") or item.get("description_es") or "",
        "description_en": item.get("strDescriptionEN") or item.get("description_en") or "",
        "source": "thesportsdb",
    }


def ingest_sportsdb_team_profile(conn, item):
    profile = sportsdb_team_profile(item)
    if not profile["external_id"] or not profile["name"]:
        raise ValueError("SportsDB team profile requires idTeam and name")
    team_id = entity(
        conn,
        "team",
        "thesportsdb",
        profile["external_id"],
        {
            "name": profile["name"],
            "short_name": profile["short_name"],
            "alternate_name": profile["alternate_name"],
            "country": profile["country"],
            "formed_year": profile["formed_year"],
            "stadium_name": profile["stadium_name"],
            "stadium_location": profile["stadium_location"],
            "stadium_capacity": profile["stadium_capacity"],
            "logo": profile["logo"],
            "jersey": profile["jersey"],
            "website": profile["website"],
            "coach": profile["coach"],
            "description_es": profile["description_es"],
            "description_en": profile["description_en"],
            "identity_confirmed": True,
        },
    )
    if profile["league_id"]:
        competition_id = entity(
            conn,
            "competition",
            "thesportsdb",
            profile["league_id"],
            {"name": profile["league_name"], "country": profile["country"]},
        )
        link_entities(conn, team_id, "team_competes_in_competition", competition_id, "thesportsdb")
        link_entities(conn, competition_id, "competition_has_team", team_id, "thesportsdb")
    if profile["stadium_id"]:
        stadium_id = entity(
            conn,
            "stadium",
            "thesportsdb",
            profile["stadium_id"],
            {
                "name": profile["stadium_name"],
                "location": profile["stadium_location"],
                "capacity": profile["stadium_capacity"],
            },
        )
        link_entities(conn, team_id, "team_uses_stadium", stadium_id, "thesportsdb")
        link_entities(conn, stadium_id, "stadium_home_team", team_id, "thesportsdb")
    return team_id


def sportsdb_player_profile(item, *, team_external_id="", team_name=""):
    """Normalize one player returned by list/players or lookup/player."""
    item = dict(item or {})
    provider_team_id = str(
        item.get("idTeam")
        or item.get("idCurrentTeam")
        or item.get("team_external_id")
        or item.get("team_id")
        or team_external_id
        or ""
    ).strip()
    return {
        "external_id": str(item.get("idPlayer") or item.get("external_id") or item.get("player_id") or item.get("id") or "").strip(),
        "name": item.get("strPlayer") or item.get("player_name") or item.get("name") or "",
        "team_external_id": provider_team_id,
        "team_name": item.get("strTeam") or item.get("strCurrentTeam") or item.get("team_name") or team_name or "",
        "position": item.get("strPosition") or item.get("position") or "",
        "shirt_number": item.get("strNumber") or item.get("intNumber") or item.get("shirt_number") or item.get("number") or "",
        "nationality": item.get("strNationality") or item.get("nationality") or "",
        "birth_date": item.get("dateBorn") or item.get("birth_date") or "",
        "birth_location": item.get("strBirthLocation") or "",
        "height": item.get("strHeight") or item.get("height") or "",
        "weight": item.get("strWeight") or "",
        "preferred_foot": item.get("strSide") or item.get("strFoot") or item.get("preferred_foot") or "",
        "photo": item.get("strThumb") or item.get("strCutout") or item.get("photo") or item.get("photo_url") or "",
        "description_es": item.get("strDescriptionES") or "",
        "description_en": item.get("strDescriptionEN") or "",
        "status": item.get("strStatus") or "",
        "source": "thesportsdb",
    }


def ingest_sportsdb_player_profile(conn, item, *, team_external_id="", team_name=""):
    profile = sportsdb_player_profile(
        item,
        team_external_id=team_external_id,
        team_name=team_name,
    )
    if not profile["external_id"] or not profile["name"]:
        raise ValueError("SportsDB player profile requires idPlayer and name")
    if team_external_id and profile["team_external_id"] != str(team_external_id):
        raise ValueError("SportsDB roster team identity mismatch")
    player_id = entity(
        conn,
        "player",
        "thesportsdb",
        profile["external_id"],
        {
            "name": profile["name"],
            "team_name": profile["team_name"],
            "team_external_id": profile["team_external_id"],
            "position": profile["position"],
            "shirt_number": profile["shirt_number"],
            "nationality": profile["nationality"],
            "birth_date": profile["birth_date"],
            "birth_location": profile["birth_location"],
            "height": profile["height"],
            "weight": profile["weight"],
            "preferred_foot": profile["preferred_foot"],
            "photo": profile["photo"],
            "description_es": profile["description_es"],
            "description_en": profile["description_en"],
            "status": profile["status"],
            "identity_confirmed": True,
        },
    )
    if profile["team_external_id"]:
        team_id = entity(
            conn,
            "team",
            "thesportsdb",
            profile["team_external_id"],
            {"name": profile["team_name"], "identity_confirmed": True},
        )
        link_entities(
            conn,
            team_id,
            "team_has_player",
            player_id,
            "thesportsdb",
            {"position": profile["position"], "shirt_number": profile["shirt_number"]},
        )
        link_entities(conn, player_id, "player_linked_to_team", team_id, "thesportsdb")
    return player_id
