"""Spanish display and Madrid-time helpers for NeMeSiS SHARK PRO.

Pure stdlib helpers: safe to import from app.py and Telegram formatting modules.
They do not perform network calls or persistence.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from engines.madrid_time_engine import (
    normalize_kickoff_for_display,
    to_madrid_time,
)

MADRID_TZ = ZoneInfo("Europe/Madrid")


def _norm(value: object) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


SPANISH_TEAM_OVERRIDES = {
    # Selecciones vistas en el vídeo y competiciones internacionales frecuentes.
    "mexico": "México",
    "south africa": "Sudáfrica",
    "south korea": "Corea del Sur",
    "korea republic": "Corea del Sur",
    "north korea": "Corea del Norte",
    "czech republic": "República Checa",
    "czechia": "República Checa",
    "bosnia herzogovina": "Bosnia y Herzegovina",
    "bosnia herzegovina": "Bosnia y Herzegovina",
    "bosnia and herzegovina": "Bosnia y Herzegovina",
    "cape verde": "Cabo Verde",
    "ivory coast": "Costa de Marfil",
    "cote d ivoire": "Costa de Marfil",
    "new zealand": "Nueva Zelanda",
    "saudi arabia": "Arabia Saudí",
    "united arab emirates": "Emiratos Árabes Unidos",
    "uae": "Emiratos Árabes Unidos",
    "united states": "Estados Unidos",
    "usa": "Estados Unidos",
    "usmnt": "Estados Unidos",
    "england": "Inglaterra",
    "scotland": "Escocia",
    "wales": "Gales",
    "northern ireland": "Irlanda del Norte",
    "republic of ireland": "Irlanda",
    "ireland": "Irlanda",
    "netherlands": "Países Bajos",
    "holland": "Países Bajos",
    "switzerland": "Suiza",
    "sweden": "Suecia",
    "norway": "Noruega",
    "denmark": "Dinamarca",
    "finland": "Finlandia",
    "germany": "Alemania",
    "france": "Francia",
    "italy": "Italia",
    "spain": "España",
    "portugal": "Portugal",
    "belgium": "Bélgica",
    "austria": "Austria",
    "croatia": "Croacia",
    "serbia": "Serbia",
    "slovenia": "Eslovenia",
    "slovakia": "Eslovaquia",
    "hungary": "Hungría",
    "poland": "Polonia",
    "ukraine": "Ucrania",
    "romania": "Rumanía",
    "turkey": "Turquía",
    "greece": "Grecia",
    "albania": "Albania",
    "georgia": "Georgia",
    "japan": "Japón",
    "china": "China",
    "iran": "Irán",
    "iraq": "Irak",
    "qatar": "Catar",
    "australia": "Australia",
    "morocco": "Marruecos",
    "egypt": "Egipto",
    "tunisia": "Túnez",
    "algeria": "Argelia",
    "nigeria": "Nigeria",
    "senegal": "Senegal",
    "ghana": "Ghana",
    "cameroon": "Camerún",
    "uruguay": "Uruguay",
    "paraguay": "Paraguay",
    "argentina": "Argentina",
    "brazil": "Brasil",
    "chile": "Chile",
    "colombia": "Colombia",
    "ecuador": "Ecuador",
    "peru": "Perú",
    "venezuela": "Venezuela",
    "bolivia": "Bolivia",
    "canada": "Canadá",
    "costa rica": "Costa Rica",
    "jamaica": "Jamaica",
    "panama": "Panamá",
    # Clubes con traducción habitual en castellano.
    "atletico madrid": "Atlético de Madrid",
    "atletico de madrid": "Atlético de Madrid",
    "bayern munich": "Bayern de Múnich",
    "inter milan": "Inter de Milán",
    "sporting lisbon": "Sporting CP",
    "red star belgrade": "Estrella Roja",
    "slavia prague": "Slavia Praga",
    "sparta prague": "Sparta Praga",
}


SPANISH_COUNTRY_OVERRIDES = {
    "world": "Mundial",
    "global": "Global",
    "international": "Internacional",
    "spain": "España",
    "england": "Inglaterra",
    "scotland": "Escocia",
    "wales": "Gales",
    "france": "Francia",
    "germany": "Alemania",
    "italy": "Italia",
    "portugal": "Portugal",
    "netherlands": "Países Bajos",
    "brazil": "Brasil",
    "argentina": "Argentina",
    "south america": "Sudamérica",
    "north america": "Norteamérica",
    "europe": "Europa",
    "usa": "Estados Unidos",
    "united states": "Estados Unidos",
    "mexico": "México",
    "south africa": "Sudáfrica",
    "south korea": "Corea del Sur",
    "czech republic": "República Checa",
    "czechia": "República Checa",
}


SPANISH_COMPETITION_OVERRIDES = {
    "fifa world cup": "Mundial FIFA",
    "world cup": "Mundial",
    "fifa club world cup": "Mundial de Clubes FIFA",
    "club world cup": "Mundial de Clubes",
    "uefa euro": "Eurocopa",
    "euro": "Eurocopa",
    "uefa european championship": "Eurocopa",
    "copa america": "Copa América",
    "copa america centenario": "Copa América",
    "uefa champions league": "Champions League",
    "champions league": "Champions League",
    "uefa europa league": "Europa League",
    "europa league": "Europa League",
    "uefa conference league": "Conference League",
    "conference league": "Conference League",
    "english premier league": "Premier League",
    "premier league": "Premier League",
    "efl championship": "Championship",
    "championship": "Championship",
    "fa cup": "Copa FA",
    "efl cup": "Copa de la Liga inglesa",
    "spanish la liga": "LaLiga EA Sports",
    "laliga": "LaLiga EA Sports",
    "la liga": "LaLiga EA Sports",
    "spanish segunda division": "Segunda División",
    "segunda division": "Segunda División",
    "serie a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue 1": "Ligue 1",
    "primeira liga": "Primeira Liga",
    "eredivisie": "Eredivisie",
    "brasileirao serie a": "Brasileirão Serie A",
    "brasileirao": "Brasileirão",
    "argentina primera division": "Primera División Argentina",
    "mls": "MLS",
    "major league soccer": "MLS",
    "nations league": "Liga de Naciones",
    "uefa nations league": "Liga de Naciones UEFA",
    "soccer_fifa_world_cup": "Mundial FIFA",
    "soccer_fifa_club_world_cup": "Mundial de Clubes FIFA",
    "soccer_uefa_champs_league": "Champions League",
    "soccer_uefa_champions_league": "Champions League",
    "soccer_uefa_europa_league": "Europa League",
    "soccer_uefa_europa_conference_league": "Conference League",
    "soccer_spain_la_liga": "LaLiga EA Sports",
    "soccer_spain_segunda_division": "Segunda División",
    "soccer_epl": "Premier League",
    "soccer_england_league1": "League One inglesa",
    "soccer_england_league2": "League Two inglesa",
    "soccer_england_championship": "Championship inglesa",
    "soccer_italy_serie_a": "Serie A",
    "soccer_italy_serie_b": "Serie B",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_germany_bundesliga2": "2. Bundesliga",
    "soccer_france_ligue_one": "Ligue 1",
    "soccer_france_ligue_two": "Ligue 2",
    "soccer_portugal_primeira_liga": "Primeira Liga",
    "soccer_netherlands_eredivisie": "Eredivisie",
    "soccer_brazil_campeonato": "Brasileirão Serie A",
    "soccer_argentina_primera_division": "Primera División Argentina",
    "soccer_usa_mls": "MLS",
    "copa del rey": "Copa del Rey",
    "supercopa de espana": "Supercopa de España",
    "supercopa de españa": "Supercopa de España",
    "spanish copa del rey": "Copa del Rey",
    "coppa italia": "Copa de Italia",
    "dfb pokal": "Copa de Alemania",
    "coupe de france": "Copa de Francia",
    "community shield": "Community Shield",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "copa sudamericana": "Copa Sudamericana",
    "afc champions league": "Champions League AFC",
    "caf champions league": "Champions League CAF",
    "concacaf champions cup": "Copa de Campeones CONCACAF",
}


SPANISH_MARKET_OVERRIDES = {
    "home": "Local",
    "away": "Visitante",
    "draw": "Empate",
    "over": "Más de",
    "under": "Menos de",
    "both teams to score": "Ambos equipos marcan",
    "btts": "Ambos equipos marcan",
    "double chance": "Doble oportunidad",
    "moneyline": "Ganador del partido",
    "h2h": "Ganador del partido",
    "match winner": "Ganador del partido",
    "winner": "Ganador",
    "spread": "Hándicap",
    "handicap": "Hándicap",
    "total": "Total de goles/puntos",
    "totals": "Total de goles/puntos",
    "result": "Resultado",
    "main": "Mercado principal",
    "principal": "Mercado principal",
}


def _title_preserving_acronyms(text: str) -> str:
    replacements = {
        "Atletico": "Atlético",
        "Mexico": "México",
        "Copa America": "Copa América",
        "Division": "División",
        "Brasileirao": "Brasileirão",
    }
    out = str(text or "").strip()
    for src, dst in replacements.items():
        out = re.sub(rf"\b{re.escape(src)}\b", dst, out, flags=re.I)
    return out


def spanish_team_name(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return SPANISH_TEAM_OVERRIDES.get(_norm(raw), _title_preserving_acronyms(raw))


def spanish_country_name(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return SPANISH_COUNTRY_OVERRIDES.get(_norm(raw), _title_preserving_acronyms(raw))


def _humanize_competition_key(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    cleaned = re.sub(r"^(soccer|football)[_\-\s]+", "", text, flags=re.I)
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    replacements = {
        "fifa world cup": "Mundial FIFA",
        "fifa club world cup": "Mundial de Clubes FIFA",
        "uefa champs league": "Champions League",
        "uefa champions league": "Champions League",
        "uefa europa league": "Europa League",
        "uefa europa conference league": "Conference League",
        "spain la liga": "LaLiga EA Sports",
        "spain segunda division": "Segunda División",
        "epl": "Premier League",
        "england championship": "Championship inglesa",
        "italy serie a": "Serie A",
        "germany bundesliga": "Bundesliga",
        "france ligue one": "Ligue 1",
        "france ligue two": "Ligue 2",
        "portugal primeira liga": "Primeira Liga",
        "netherlands eredivisie": "Eredivisie",
        "usa mls": "MLS",
        "brazil campeonato": "Brasileirão Serie A",
        "argentina primera division": "Primera División Argentina",
    }
    key = _norm(cleaned)
    if key in replacements:
        return replacements[key]
    # País + liga: mantener castellano si reconocemos el país.
    pieces = cleaned.split(" ")
    if pieces:
        country = spanish_country_name(pieces[0])
        rest = " ".join(pieces[1:])
        if country and rest:
            return _title_preserving_acronyms(f"{rest.title()} {country}")
    return _title_preserving_acronyms(cleaned.title())


def spanish_competition_name(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = _norm(raw)
    if key in SPANISH_COMPETITION_OVERRIDES:
        return SPANISH_COMPETITION_OVERRIDES[key]
    compact_key = raw.strip().lower()
    if compact_key in SPANISH_COMPETITION_OVERRIDES:
        return SPANISH_COMPETITION_OVERRIDES[compact_key]
    for needle, translated in SPANISH_COMPETITION_OVERRIDES.items():
        if needle and needle in key:
            return translated
    # API keys such as soccer_spain_la_liga should never be displayed raw.
    if "_" in raw or raw.lower().startswith(("soccer", "football")):
        return _humanize_competition_key(raw)
    return _title_preserving_acronyms(raw)

def spanish_market_name(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = _norm(raw)
    if key in SPANISH_MARKET_OVERRIDES:
        return SPANISH_MARKET_OVERRIDES[key]
    for needle, translated in SPANISH_MARKET_OVERRIDES.items():
        if needle and needle in key:
            return translated if key == needle else raw
    return _title_preserving_acronyms(raw)




def spanish_pick_selection_name(value: object, home_team: object = "", away_team: object = "", market: object = "") -> str:
    """Devuelve una selección de apuesta clara para cliente.

    Evita mostrar valores técnicos como "Local" o "Visitante" y los convierte en
    instrucciones accionables: "Gana Canadá", "Gana Croacia", "Empate", etc.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    home = spanish_team_name(home_team) or "equipo local"
    away = spanish_team_name(away_team) or "equipo visitante"
    key = _norm(raw)
    pending_re = r"(esperar|pendiente|sin cuota|no disponible|value en c[aá]lculo|cuota pendiente|mercado pendiente|undefined|null|none)"
    if re.search(pending_re, raw, flags=re.I):
        return ""

    # 1X2 / ganador del partido
    if key in {"home", "local", "1", "winner home", "match winner home", "home win", "local win", "equipo local"}:
        return f"Gana {home}"
    if key in {"away", "visitante", "2", "winner away", "match winner away", "away win", "visitante win", "equipo visitante"}:
        return f"Gana {away}"
    if key in {"draw", "empate", "x", "tie"}:
        return "Empate"

    # Doble oportunidad
    if key in {"1x", "home or draw", "local or draw", "local empate", "local o empate"}:
        return f"{home} o empate"
    if key in {"x2", "away or draw", "visitante or draw", "visitante empate", "visitante o empate"}:
        return f"{away} o empate"
    if key in {"12", "home or away", "local or away", "local o visitante"}:
        return f"{home} o {away}"

    # Totales y ambos marcan
    over_match = re.search(r"(?:over|m[aá]s de)\s*([0-9]+(?:[\.,][0-9]+)?)", raw, flags=re.I)
    if over_match:
        return f"Más de {over_match.group(1).replace(',', '.')} goles"
    under_match = re.search(r"(?:under|menos de)\s*([0-9]+(?:[\.,][0-9]+)?)", raw, flags=re.I)
    if under_match:
        return f"Menos de {under_match.group(1).replace(',', '.')} goles"
    if "btts" in key or "both teams" in key or "ambos equipos" in key:
        if any(x in key for x in {"no", "not", "false"}):
            return "Ambos equipos marcan: No"
        return "Ambos equipos marcan: Sí"

    # Si la API trae directamente el nombre del equipo, convertirlo en instrucción.
    if key and key == _norm(home):
        return f"Gana {home}"
    if key and key == _norm(away):
        return f"Gana {away}"

    # Hándicaps frecuentes con Local/Visitante.
    handicap = re.search(r"\b(home|local|away|visitante)\b\s*([+-]\s*\d+(?:[\.,]\d+)?)", raw, flags=re.I)
    if handicap:
        side = _norm(handicap.group(1))
        line = handicap.group(2).replace(" ", "").replace(",", ".")
        team = home if side in {"home", "local"} else away
        return f"Hándicap {team} {line}"

    return _title_preserving_acronyms(raw)


def _has_explicit_timezone(value: str) -> bool:
    s = str(value or "").strip()
    return bool(s.endswith("Z") or re.search(r"[+-]\d{2}:?\d{2}$", s))


def parse_datetime_to_madrid(value: object, assume_naive_madrid: bool = True) -> datetime | None:
    return to_madrid_time(value)


def madrid_values_from_datetime(value: object, fallback_date: object = "", fallback_time: object = "") -> dict:
    dt = parse_datetime_to_madrid(value)
    if dt is None and fallback_date and fallback_time:
        dt = parse_datetime_to_madrid(f"{fallback_date}T{str(fallback_time)[:5]}:00")
    if dt is None:
        return {
            "match_date": str(fallback_date or "")[:10],
            "kickoff_time": str(fallback_time or "")[:5],
            "kickoff_iso": str(value or ""),
            "safe_time": str(fallback_time or "")[:5] or "Hora",
            "safe_date": str(fallback_date or "")[:10],
            "safe_datetime": "",
        }
    return {
        "match_date": dt.date().isoformat(),
        "kickoff_time": dt.strftime("%H:%M"),
        "kickoff_iso": dt.isoformat(timespec="seconds"),
        "safe_time": dt.strftime("%H:%M"),
        "safe_date": dt.strftime("%d/%m/%Y"),
        "safe_datetime": dt.strftime("%d/%m/%Y · %H:%M"),
        "display_datetime": spanish_datetime_label(dt),
    }


def spanish_datetime_label(value: object, fallback_date: object = "", fallback_time: object = "") -> str:
    dt = value if isinstance(value, datetime) else parse_datetime_to_madrid(value)
    if dt is None and fallback_date and fallback_time:
        dt = parse_datetime_to_madrid(f"{fallback_date}T{str(fallback_time)[:5]}:00")
    if dt is None:
        date = str(fallback_date or "")[:10]
        time = str(fallback_time or "")[:5]
        return f"{date} · {time}".strip(" ·") or "Hora pendiente"
    dt = dt.astimezone(MADRID_TZ)
    today = datetime.now(MADRID_TZ).date()
    tomorrow = today + timedelta(days=1)
    weekday = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][dt.weekday()]
    if dt.date() == today:
        return f"Hoy {dt:%H:%M}"
    if dt.date() == tomorrow:
        return f"Mañana {dt:%H:%M}"
    return f"{weekday} {dt:%d/%m} · {dt:%H:%M}"


def apply_match_localization(match: dict | None) -> dict:
    item = dict(match or {})
    if not item:
        return item
    item = normalize_kickoff_for_display(item)
    raw_home = item.get("_raw_home_team") or item.get("home_team") or item.get("home") or ""
    raw_away = item.get("_raw_away_team") or item.get("away_team") or item.get("away") or ""
    raw_comp = item.get("_raw_competition_name") or item.get("competition_name") or item.get("league_name") or item.get("competition") or item.get("league") or ""
    raw_country = item.get("_raw_country") or item.get("country") or ""
    item["_raw_home_team"] = raw_home
    item["_raw_away_team"] = raw_away
    item["_raw_competition_name"] = raw_comp
    item["_raw_country"] = raw_country
    item["home_team"] = spanish_team_name(raw_home) or "Equipo local"
    item["away_team"] = spanish_team_name(raw_away) or "Equipo visitante"
    item["competition_name"] = spanish_competition_name(raw_comp) or "Competición"
    item["league_name"] = spanish_competition_name(item.get("league_name") or raw_comp) or item["competition_name"]
    item["country"] = spanish_country_name(raw_country) or raw_country
    values = madrid_values_from_datetime(item.get("madrid_dt_iso") or item.get("kickoff_iso") or item.get("commence_time") or "", item.get("match_date"), item.get("kickoff_time") or item.get("match_time"))
    # For timezone-aware API timestamps, update visible date/time to Madrid. For rows without a real timestamp, keep the fallback date/time.
    if values.get("match_date"):
        item["match_date"] = values["match_date"]
    if values.get("kickoff_time"):
        item["kickoff_time"] = values["kickoff_time"]
        item["match_time"] = values["kickoff_time"]
    if values.get("kickoff_iso"):
        item["kickoff_iso_madrid"] = values["kickoff_iso"]
    item["safe_home"] = item["home_team"]
    item["safe_away"] = item["away_team"]
    item["safe_competition"] = item["competition_name"]
    item["safe_country"] = item["country"] or "Global"
    item["safe_time"] = values.get("safe_time") or item.get("kickoff_time") or item.get("match_time") or "Hora"
    item["safe_date"] = values.get("safe_date") or item.get("match_date") or ""
    item["safe_datetime"] = values.get("safe_datetime") or ""
    item["display_datetime"] = values.get("display_datetime") or spanish_datetime_label("", item.get("match_date"), item.get("kickoff_time") or item.get("match_time"))
    item["time_context"] = "Hora española"
    return item


def apply_pick_localization(pick: dict | None) -> dict:
    item = dict(pick or {})
    if not item:
        return item
    item = normalize_kickoff_for_display(item)
    item["home_team"] = spanish_team_name(item.get("home_team") or item.get("home") or "") or "Equipo local"
    item["away_team"] = spanish_team_name(item.get("away_team") or item.get("away") or "") or "Equipo visitante"
    item["competition_name"] = spanish_competition_name(item.get("competition_name") or item.get("league_name") or "") or "Competición"
    item["league_name"] = spanish_competition_name(item.get("league_name") or item.get("competition_name")) or item["competition_name"]
    values = madrid_values_from_datetime(item.get("madrid_dt_iso") or item.get("kickoff_iso") or "", item.get("match_date"), item.get("kickoff_time") or item.get("match_time"))
    if values.get("match_date"):
        item["match_date"] = values["match_date"]
    if values.get("kickoff_time"):
        item["kickoff_time"] = values["kickoff_time"]
        item["match_time"] = values["kickoff_time"]
    item["safe_time"] = values.get("safe_time") or item.get("kickoff_time") or item.get("match_time") or "Hora"
    item["safe_date"] = values.get("safe_date") or item.get("match_date") or ""
    item["display_datetime"] = values.get("display_datetime") or spanish_datetime_label("", item.get("match_date"), item.get("kickoff_time") or item.get("match_time"))
    item["time_context"] = "Hora española"
    raw_selection = item.get("_raw_selection") or item.get("selection") or item.get("pick") or item.get("recommendation") or ""
    item["_raw_selection"] = raw_selection
    item["market"] = spanish_market_name(item.get("market") or item.get("pick_type") or "")
    item["pick_type"] = spanish_market_name(item.get("pick_type") or item.get("market") or "")
    selection_label = spanish_pick_selection_name(raw_selection, item.get("home_team"), item.get("away_team"), item.get("market"))
    if selection_label:
        item["selection"] = selection_label
        item["selection_display"] = selection_label
    else:
        item["selection_display"] = "Selección pendiente"
        # Mantener vacío para que filtros premium no traten pendientes como picks cerrados.
        if raw_selection:
            item["selection"] = ""
    return item
