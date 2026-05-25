"""Football data population helpers for NeMeSiS SHARK PRO.

The module is intentionally pure: no Flask, no HTTP, no SQLite connection.
It centralizes the legal football coverage map used by app.py.
"""

from datetime import datetime, timedelta


PRIORITY_COMPETITIONS = [
    {"key": "laliga", "name": "LaLiga", "country": "Spain", "region": "Europe", "group": "spain", "tier": 99, "sportsdb_id": "4335", "odds_key": "soccer_spain_la_liga"},
    {"key": "segunda-division", "name": "Segunda Division", "country": "Spain", "region": "Europe", "group": "spain", "tier": 92, "sportsdb_id": "4401", "odds_key": "soccer_spain_segunda_division"},
    {"key": "primera-rfef", "name": "Primera RFEF", "country": "Spain", "region": "Spain", "group": "spain", "tier": 78, "sportsdb_id": "", "odds_key": ""},
    {"key": "segunda-rfef", "name": "Segunda RFEF", "country": "Spain", "region": "Spain", "group": "spain", "tier": 72, "sportsdb_id": "", "odds_key": ""},
    {"key": "tercera-rfef", "name": "Tercera RFEF", "country": "Spain", "region": "Spain", "group": "spain", "tier": 68, "sportsdb_id": "", "odds_key": ""},
    {"key": "premier-league", "name": "Premier League", "country": "England", "region": "Europe", "group": "international", "tier": 98, "sportsdb_id": "4328", "odds_key": "soccer_epl"},
    {"key": "ligue-1", "name": "Ligue 1", "country": "France", "region": "Europe", "group": "international", "tier": 92, "sportsdb_id": "4334", "odds_key": "soccer_france_ligue_one"},
    {"key": "serie-a", "name": "Serie A", "country": "Italy", "region": "Europe", "group": "international", "tier": 95, "sportsdb_id": "4332", "odds_key": "soccer_italy_serie_a"},
    {"key": "bundesliga", "name": "Bundesliga", "country": "Germany", "region": "Europe", "group": "international", "tier": 95, "sportsdb_id": "4331", "odds_key": "soccer_germany_bundesliga"},
    {"key": "primeira-liga", "name": "Primeira Liga", "country": "Portugal", "region": "Europe", "group": "international", "tier": 86, "sportsdb_id": "4344", "odds_key": "soccer_portugal_primeira_liga"},
    {"key": "uefa-champions-league", "name": "UEFA Champions League", "country": "Europe", "region": "UEFA", "group": "uefa", "tier": 100, "sportsdb_id": "4480", "odds_key": "soccer_uefa_champs_league"},
    {"key": "uefa-europa-league", "name": "UEFA Europa League", "country": "Europe", "region": "UEFA", "group": "uefa", "tier": 94, "sportsdb_id": "4481", "odds_key": "soccer_uefa_europa_league"},
    {"key": "uefa-conference-league", "name": "UEFA Conference League", "country": "Europe", "region": "UEFA", "group": "uefa", "tier": 88, "sportsdb_id": "", "odds_key": "soccer_uefa_europa_conference_league"},
    {"key": "fifa-world-cup", "name": "FIFA World Cup", "country": "World", "region": "Global", "group": "national", "tier": 100, "sportsdb_id": "4429", "odds_key": "soccer_fifa_world_cup"},
    {"key": "uefa-euro", "name": "UEFA Euro", "country": "Europe", "region": "UEFA", "group": "national", "tier": 98, "sportsdb_id": "4504", "odds_key": "soccer_uefa_european_championship"},
    {"key": "copa-america", "name": "Copa America", "country": "South America", "region": "CONMEBOL", "group": "national", "tier": 96, "sportsdb_id": "4450", "odds_key": "soccer_conmebol_copa_america"},
    {"key": "uefa-nations-league", "name": "UEFA Nations League", "country": "Europe", "region": "UEFA", "group": "national", "tier": 90, "sportsdb_id": "4664", "odds_key": "soccer_uefa_nations_league"},
    {"key": "andalucia-cadiz", "name": "Cadiz Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-sevilla", "name": "Sevilla Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-malaga", "name": "Malaga Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-granada", "name": "Granada Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-cordoba", "name": "Cordoba Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-huelva", "name": "Huelva Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-jaen", "name": "Jaen Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-almeria", "name": "Almeria Andalucia", "country": "Spain", "region": "Andalucia", "group": "andalucia", "tier": 65, "sportsdb_id": "", "odds_key": ""},
]


STRUCTURAL_TEAMS = [
    {"key": "real-madrid", "name": "Real Madrid", "country": "Spain", "region": "Europe", "external_id": "133738", "league": "LaLiga"},
    {"key": "barcelona", "name": "FC Barcelona", "country": "Spain", "region": "Europe", "external_id": "133739", "league": "LaLiga"},
    {"key": "atletico-madrid", "name": "Atletico de Madrid", "country": "Spain", "region": "Europe", "external_id": "133729", "league": "LaLiga"},
    {"key": "sevilla", "name": "Sevilla FC", "country": "Spain", "region": "Andalucia", "external_id": "133745", "league": "LaLiga"},
    {"key": "real-betis", "name": "Real Betis", "country": "Spain", "region": "Andalucia", "external_id": "133741", "league": "LaLiga"},
    {"key": "cadiz", "name": "Cadiz CF", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "malaga", "name": "Malaga CF", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "granada", "name": "Granada CF", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "cordoba", "name": "Cordoba CF", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "recreativo-huelva", "name": "Recreativo de Huelva", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "almeria", "name": "UD Almeria", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "real-jaen", "name": "Real Jaen", "country": "Spain", "region": "Andalucia", "external_id": "", "league": "Spain"},
    {"key": "arsenal", "name": "Arsenal", "country": "England", "region": "Europe", "external_id": "133604", "league": "Premier League"},
    {"key": "manchester-city", "name": "Manchester City", "country": "England", "region": "Europe", "external_id": "133613", "league": "Premier League"},
    {"key": "liverpool", "name": "Liverpool", "country": "England", "region": "Europe", "external_id": "133602", "league": "Premier League"},
    {"key": "chelsea", "name": "Chelsea", "country": "England", "region": "Europe", "external_id": "133610", "league": "Premier League"},
    {"key": "manchester-united", "name": "Manchester United", "country": "England", "region": "Europe", "external_id": "133612", "league": "Premier League"},
    {"key": "psg", "name": "Paris Saint-Germain", "country": "France", "region": "Europe", "external_id": "133714", "league": "Ligue 1"},
    {"key": "bayern-munich", "name": "Bayern Munich", "country": "Germany", "region": "Europe", "external_id": "133664", "league": "Bundesliga"},
    {"key": "borussia-dortmund", "name": "Borussia Dortmund", "country": "Germany", "region": "Europe", "external_id": "133650", "league": "Bundesliga"},
    {"key": "juventus", "name": "Juventus", "country": "Italy", "region": "Europe", "external_id": "133676", "league": "Serie A"},
    {"key": "inter", "name": "Inter Milan", "country": "Italy", "region": "Europe", "external_id": "133668", "league": "Serie A"},
    {"key": "ac-milan", "name": "AC Milan", "country": "Italy", "region": "Europe", "external_id": "133667", "league": "Serie A"},
    {"key": "benfica", "name": "Benfica", "country": "Portugal", "region": "Europe", "external_id": "133713", "league": "Primeira Liga"},
    {"key": "porto", "name": "FC Porto", "country": "Portugal", "region": "Europe", "external_id": "133721", "league": "Primeira Liga"},
    {"key": "sporting-cp", "name": "Sporting CP", "country": "Portugal", "region": "Europe", "external_id": "134513", "league": "Primeira Liga"},
]


def sportsdb_competitions():
    return [item for item in PRIORITY_COMPETITIONS if item.get("sportsdb_id")]


def odds_competitions():
    return [item for item in PRIORITY_COMPETITIONS if item.get("odds_key")]


def competition_payload(item):
    return {
        "key": item["key"],
        "name": item["name"],
        "scope": "regional" if item["group"] == "andalucia" else ("international" if item["country"] in {"World", "Europe", "South America"} else "domestic"),
        "country": item["country"],
        "region": item["region"],
        "tier": item["tier"],
        "source_strategy": "SportsDB/Odds/API legal" if item.get("sportsdb_id") or item.get("odds_key") else "Import legal preparado",
        "tags": [item["group"], item["country"].lower().replace(" ", "-")],
        "external_id": item.get("sportsdb_id") or item.get("odds_key") or "",
        "source": "population_engine",
        "sync_status": "prepared" if item.get("sportsdb_id") or item.get("odds_key") else "no_data",
    }


def team_payload(item):
    payload = dict(item)
    payload.setdefault("logo_url", "")
    payload.setdefault("source", "population_engine")
    payload.setdefault("legal_note", "Equipo real preparado como seed estructural; partidos solo desde API o import legal.")
    return payload


def empty_sync(source, sync_type, reason):
    return {
        "ok": False,
        "source": source,
        "sync_type": sync_type,
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [reason],
    }


def success_sync(source, sync_type, processed=0, inserted=0, updated=0, skipped=0, errors=None):
    return {
        "ok": not errors,
        "source": source,
        "sync_type": sync_type,
        "processed": processed,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors or [],
    }


def price_map_from_outcomes(outcomes, home_team, away_team):
    prices = {"home": "", "draw": "", "away": ""}
    for outcome in outcomes or []:
        name = str(outcome.get("name") or "").strip().lower()
        price = outcome.get("price", "")
        if name == str(home_team or "").strip().lower():
            prices["home"] = price
        elif name == str(away_team or "").strip().lower():
            prices["away"] = price
        elif name in {"draw", "empate", "x"}:
            prices["draw"] = price
    return prices


def should_run_interval(last_iso, hours, now_iso):
    if not last_iso:
        return True
    try:
        last = datetime.fromisoformat(str(last_iso))
        now = datetime.fromisoformat(str(now_iso))
        return now - last >= timedelta(hours=max(1, int(hours)))
    except (TypeError, ValueError):
        return True
