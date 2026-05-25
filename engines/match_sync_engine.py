"""Legal match sync helpers for SportsDB/Odds feeds.

This module has no Flask dependency. The app owns persistence and HTTP calls.
"""

IMPORTANT_COMPETITIONS = [
    {"key": "laliga", "name": "LaLiga EA Sports", "country": "Spain", "group": "spain", "sportsdb_id": "4335", "odds_key": "soccer_spain_la_liga"},
    {"key": "segunda-division", "name": "Segunda Division", "country": "Spain", "group": "spain", "sportsdb_id": "4401", "odds_key": "soccer_spain_segunda_division"},
    {"key": "primera-rfef", "name": "Primera RFEF", "country": "Spain", "group": "spain", "sportsdb_id": "", "odds_key": ""},
    {"key": "segunda-rfef", "name": "Segunda RFEF", "country": "Spain", "group": "spain", "sportsdb_id": "", "odds_key": ""},
    {"key": "tercera-rfef", "name": "Tercera RFEF", "country": "Spain", "group": "spain", "sportsdb_id": "", "odds_key": ""},
    {"key": "premier-league", "name": "Premier League", "country": "England", "group": "international", "sportsdb_id": "4328", "odds_key": "soccer_epl"},
    {"key": "ligue-1", "name": "Ligue 1", "country": "France", "group": "international", "sportsdb_id": "4334", "odds_key": "soccer_france_ligue_one"},
    {"key": "serie-a", "name": "Serie A", "country": "Italy", "group": "international", "sportsdb_id": "4332", "odds_key": "soccer_italy_serie_a"},
    {"key": "bundesliga", "name": "Bundesliga", "country": "Germany", "group": "international", "sportsdb_id": "4331", "odds_key": "soccer_germany_bundesliga"},
    {"key": "primeira-liga", "name": "Primeira Liga", "country": "Portugal", "group": "international", "sportsdb_id": "4344", "odds_key": "soccer_portugal_primeira_liga"},
    {"key": "uefa-champions-league", "name": "UEFA Champions League", "country": "Europe", "group": "international", "sportsdb_id": "4480", "odds_key": "soccer_uefa_champs_league"},
    {"key": "uefa-europa-league", "name": "UEFA Europa League", "country": "Europe", "group": "international", "sportsdb_id": "4481", "odds_key": "soccer_uefa_europa_league"},
    {"key": "uefa-conference-league", "name": "UEFA Conference League", "country": "Europe", "group": "international", "sportsdb_id": "", "odds_key": "soccer_uefa_europa_conference_league"},
    {"key": "fifa-world-cup", "name": "FIFA World Cup", "country": "World", "group": "national", "sportsdb_id": "4429", "odds_key": "soccer_fifa_world_cup"},
    {"key": "uefa-euro", "name": "UEFA Euro", "country": "Europe", "group": "national", "sportsdb_id": "4504", "odds_key": "soccer_uefa_european_championship"},
    {"key": "copa-america", "name": "Copa America", "country": "South America", "group": "national", "sportsdb_id": "4450", "odds_key": "soccer_conmebol_copa_america"},
    {"key": "uefa-nations-league", "name": "UEFA Nations League", "country": "Europe", "group": "national", "sportsdb_id": "4664", "odds_key": "soccer_uefa_nations_league"},
    {"key": "andalucia-cadiz", "name": "Cadiz base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-sevilla", "name": "Sevilla base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-malaga", "name": "Malaga base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-granada", "name": "Granada base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-cordoba", "name": "Cordoba base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-huelva", "name": "Huelva base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-jaen", "name": "Jaen base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
    {"key": "andalucia-almeria", "name": "Almeria base", "country": "Spain", "group": "andalucia", "sportsdb_id": "", "odds_key": ""},
]


def sportsdb_leagues():
    return [item for item in IMPORTANT_COMPETITIONS if item.get("sportsdb_id")]


def odds_sports():
    return [item for item in IMPORTANT_COMPETITIONS if item.get("odds_key")]


def normalize_status(value):
    text = str(value or "").strip().lower()
    if text in {"ft", "finished", "final", "finalizado"} or "final" in text:
        return "FINALIZADO"
    if text in {"ht", "halftime", "half time", "descanso"}:
        return "DESCANSO"
    if text in {"live", "1h", "2h", "in play", "inprogress"} or "live" in text:
        return "LIVE"
    if text in {"suspended", "postponed", "cancelled", "canc", "pst", "abd"}:
        return "SUSPENDIDO"
    return "PROGRAMADO"


def h2h_price_snapshot(event):
    bookmakers = event.get("bookmakers") or []
    if not bookmakers:
        return {}
    bookmaker = bookmakers[0] or {}
    markets = bookmaker.get("markets") or []
    h2h = next((market for market in markets if market.get("key") == "h2h"), markets[0] if markets else {})
    return {
        "bookmaker": bookmaker.get("title") or bookmaker.get("key") or "",
        "last_update": bookmaker.get("last_update") or h2h.get("last_update") or "",
        "outcomes": h2h.get("outcomes") or [],
    }
