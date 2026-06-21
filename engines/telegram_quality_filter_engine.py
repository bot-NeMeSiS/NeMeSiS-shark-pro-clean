"""V844 Telegram quality filter for commercial public delivery.

The app can list broad football coverage, but the Telegram public channel must
stay conservative: top football only, no filler, and no weak competitions.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

TOP_COMPETITION_RE = re.compile(
    r"\b("
    r"champions\s+league|uefa\s+champions|europa\s+league|conference\s+league|"
    r"premier\s+league|la\s*liga|laliga|primera\s+division|primera\s+división|"
    r"copa\s+del\s+rey|supercopa|serie\s+a|bundesliga|ligue\s+1|primeira\s+liga|"
    r"eredivisie|world\s+cup|mundial|eurocopa|uefa\s+euro|copa\s+america|copa\s+américa|"
    r"nations\s+league|libertadores|sudamericana|fa\s+cup|fifa|uefa"
    r")\b",
    re.I,
)

MEDIUM_COMPETITION_RE = re.compile(
    r"\b("
    r"championship|segunda\s+division|segunda\s+división|serie\s+b|bundesliga\s*2|"
    r"ligue\s*2|mls|liga\s+mx|brasileirao|brasileirão|argentina|brasil|mexico|méxico"
    r")\b",
    re.I,
)

TOP_TEAM_RE = re.compile(
    r"\b("
    r"real\s+madrid|barcelona|atletico|atl[eé]tico|sevilla|valencia|betis|villarreal|"
    r"manchester|liverpool|arsenal|chelsea|tottenham|newcastle|aston\s+villa|"
    r"juventus|inter|milan|napoli|roma|lazio|atalanta|"
    r"bayern|dortmund|leverkusen|leipzig|psg|marseille|lyon|monaco|"
    r"benfica|porto|sporting|ajax|psv|feyenoord|"
    r"river|boca|flamengo|palmeiras|corinthians|santos|deportivo\s+la\s+coru[ñn]a|zaragoza|"
    r"argentina|brasil|brazil|spain|españa|france|francia|germany|alemania|italy|italia|"
    r"england|inglaterra|portugal|netherlands|países\s+bajos|uruguay|mexico|méxico"
    r")\b",
    re.I,
)

NON_FOOTBALL_RE = re.compile(
    r"\b(nba|wnba|basket|basketball|nfl|nhl|mlb|baseball|tennis|atp|wta|hockey|cricket|rugby|volleyball|handball|ufc|mma|boxing|golf|f1|formula\s*1|esports)\b",
    re.I,
)

BLOCKED_RE = re.compile(
    r"\b("
    r"reserve|reserves|youth|juvenil|u19|u20|u21|u23|u18|u17|sub[-\s]?19|sub[-\s]?20|sub[-\s]?21|"
    r"b\s+team|academy|development|juniors|primavera|amateur|regional|county|district|"
    r"tercera|cuarta|fourth|lower|state\s+league|women|womens|femenino|femenina|"
    r"club\s+friendlies|friendly|friendlies|amistoso"
    r")\b",
    re.I,
)

CONTEXT_FIELDS = (
    "sport",
    "sport_key",
    "sport_title",
    "strSport",
    "competition_name",
    "league_name",
    "league",
    "competition",
    "country",
    "home_team",
    "away_team",
    "title",
    "market",
    "source",
)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _context(match: Mapping[str, Any] | None) -> str:
    item = dict(match or {})
    return " | ".join(_text(item.get(key)) for key in CONTEXT_FIELDS if item.get(key)).lower()


def _teams(match: Mapping[str, Any] | None) -> str:
    item = dict(match or {})
    return f"{_text(item.get('home_team') or item.get('home'))} {_text(item.get('away_team') or item.get('away'))}"


def _has_time(match: Mapping[str, Any] | None) -> bool:
    item = dict(match or {})
    for key in ("kickoff_iso", "kickoff_time", "match_time", "commence_time", "date_time"):
        if _text(item.get(key)):
            return True
    return bool(_text(item.get("match_date") or item.get("date")))


def _minutes_until(match: Mapping[str, Any] | None) -> int | None:
    raw = _text((match or {}).get("kickoff_iso") or (match or {}).get("commence_time") or "")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return int((dt.astimezone(TZ) - datetime.now(TZ)).total_seconds() // 60)
    except Exception:
        return None


def is_blocked_telegram_competition(match: Mapping[str, Any] | None) -> bool:
    context = _context(match)
    if NON_FOOTBALL_RE.search(context):
        return True
    if BLOCKED_RE.search(context) and not TOP_TEAM_RE.search(context):
        return True
    explicit = _text((match or {}).get("sport_key") or (match or {}).get("sport") or "").lower()
    if explicit and not any(token in explicit for token in ("soccer", "football", "futbol", "fútbol")):
        if NON_FOOTBALL_RE.search(explicit):
            return True
    return False


def is_allowed_telegram_competition(match: Mapping[str, Any] | None) -> bool:
    if not match or is_blocked_telegram_competition(match):
        return False
    context = _context(match)
    teams = _teams(match)
    if TOP_COMPETITION_RE.search(context):
        return True
    if MEDIUM_COMPETITION_RE.search(context) and TOP_TEAM_RE.search(teams + " " + context):
        return True
    try:
        if int((match or {}).get("priority") or (match or {}).get("importance") or 0) >= 90:
            return True
    except Exception:
        pass
    return False


def telegram_match_quality_score(match: Mapping[str, Any] | None) -> int:
    if not match or is_blocked_telegram_competition(match):
        return 0
    context = _context(match)
    teams = _teams(match)
    score = 0
    if TOP_COMPETITION_RE.search(context):
        score += 70
    elif MEDIUM_COMPETITION_RE.search(context):
        score += 45
    if TOP_TEAM_RE.search(teams + " " + context):
        score += 20
    if _has_time(match):
        score += 10
    minutes = _minutes_until(match)
    if minutes is not None and -30 <= minutes <= 48 * 60:
        score += 8
    if (match or {}).get("odds") or (match or {}).get("bookmaker"):
        score += 5
    if (match or {}).get("pick_id") or (match or {}).get("selection") or (match or {}).get("recommendation"):
        score += 7
    return min(score, 100)


def explain_telegram_filter_decision(match: Mapping[str, Any] | None) -> dict[str, Any]:
    item = dict(match or {})
    context = _context(item)
    score = telegram_match_quality_score(item)
    if not item:
        return {"allowed": False, "reason": "skipped_no_candidate", "score": 0}
    if NON_FOOTBALL_RE.search(context):
        return {"allowed": False, "reason": "skipped_blocked_sport", "score": score}
    if is_blocked_telegram_competition(item):
        return {"allowed": False, "reason": "skipped_blocked_competition", "score": score}
    if not _has_time(item):
        return {"allowed": False, "reason": "skipped_missing_reliable_time", "score": score}
    if is_allowed_telegram_competition(item) and score >= 60:
        return {"allowed": True, "reason": "allowed_top_football", "score": score}
    if score >= 82:
        return {"allowed": True, "reason": "allowed_high_quality_context", "score": score}
    return {"allowed": False, "reason": "skipped_low_quality", "score": score}


def is_top_football_match(match: Mapping[str, Any] | None) -> bool:
    return bool(explain_telegram_filter_decision(match).get("allowed"))


def filter_telegram_candidates(candidates: Iterable[Mapping[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    allowed: list[dict[str, Any]] = []
    for candidate in candidates or []:
        item = dict(candidate or {})
        decision = explain_telegram_filter_decision(item)
        if decision.get("allowed"):
            item["_telegram_quality"] = decision
            allowed.append(item)
    allowed.sort(key=lambda row: (row.get("_telegram_quality") or {}).get("score", 0), reverse=True)
    if limit is not None:
        allowed = allowed[: int(limit)]
    return allowed


def rejected_telegram_candidates(candidates: Iterable[Mapping[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    rejected = []
    for candidate in candidates or []:
        item = dict(candidate or {})
        decision = explain_telegram_filter_decision(item)
        if not decision.get("allowed"):
            rejected.append(
                {
                    "id": item.get("id") or item.get("match_id") or item.get("fixture_id") or item.get("pick_id"),
                    "competition": item.get("competition_name") or item.get("league_name") or item.get("competition") or "",
                    "match": f"{item.get('home_team') or 'Local'} vs {item.get('away_team') or 'Visitante'}",
                    "reason": decision.get("reason"),
                    "score": decision.get("score", 0),
                }
            )
    return rejected[: int(limit or 20)]
