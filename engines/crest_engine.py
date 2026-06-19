"""Central crest/logo resolver for NeMeSiS SHARK PRO.

V821 keeps this module stdlib-only and non-blocking: it never downloads images
while rendering a page. Runtime helpers always return a valid local fallback if
SQLite is locked, a table is missing, a URL is invalid, or input is incomplete.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
import urllib.parse
from datetime import datetime
from typing import Any


_LOGO_TABLES_READY = False


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def normalize_logo_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "equipo"


def safe_logo_url(url: Any) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    low = value.lower()
    if low in {"none", "null", "undefined", "nan", "false", "0", "-", "sin escudo", "pendiente"}:
        return ""
    if any(bad in low for bad in ("javascript:", "vbscript:", "<script", "data:text/html")):
        return ""
    if value.startswith("//"):
        value = "https:" + value
    if value.startswith("http://"):
        value = "https://" + value[len("http://") :]
    if value.startswith(("https://", "/static/", "/team-crest.svg", "data:image/")):
        return value
    return ""


def fallback_crest_url(name: Any) -> str:
    return "/team-crest.svg?" + urllib.parse.urlencode({"name": str(name or "Equipo")})


def fallback_crest_svg(name: Any) -> str:
    return fallback_crest_url(name)


def crest_status(team: dict[str, Any] | None) -> dict[str, Any]:
    team = dict(team or {})
    logo = safe_logo_url(team.get("logo_url") or team.get("crest_url"))
    if logo and not logo.startswith(("/team-crest.svg", "data:image/")):
        return {"mode": "logo", "source": team.get("source") or team.get("provider") or "cache", "is_fallback": False}
    return {"mode": "fallback", "source": "fallback_svg_local", "is_fallback": True}


def ensure_crest_logo_schema(conn: sqlite3.Connection) -> None:
    global _LOGO_TABLES_READY
    if _LOGO_TABLES_READY:
        return
    conn.execute(
        """CREATE TABLE IF NOT EXISTS team_logo_cache(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_key TEXT UNIQUE,
            team_name TEXT,
            provider TEXT,
            logo_url TEXT,
            local_path TEXT,
            is_fallback INTEGER DEFAULT 0,
            last_checked_at TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS league_logo_cache(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_key TEXT UNIQUE,
            league_name TEXT,
            provider TEXT,
            logo_url TEXT,
            is_fallback INTEGER DEFAULT 0,
            last_checked_at TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_team_logo_cache_key ON team_logo_cache(team_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_league_logo_cache_key ON league_logo_cache(league_key)")
    _LOGO_TABLES_READY = True


def ensure_logo_tables_once(conn: sqlite3.Connection | None) -> bool:
    if conn is None:
        return False
    try:
        ensure_crest_logo_schema(conn)
        return True
    except (sqlite3.Error, RuntimeError, OSError):
        return False


def upsert_team_logo_cache(
    conn: sqlite3.Connection,
    team_name: Any,
    logo_url: Any,
    *,
    provider: str = "cache",
    is_fallback: bool = False,
) -> dict[str, Any]:
    ensure_crest_logo_schema(conn)
    name = str(team_name or "Equipo").strip() or "Equipo"
    key = normalize_logo_key(name)
    safe_url = safe_logo_url(logo_url)
    now = _now_iso()
    conn.execute(
        """INSERT INTO team_logo_cache(team_key,team_name,provider,logo_url,is_fallback,last_checked_at,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(team_key) DO UPDATE SET
             team_name=excluded.team_name,
             provider=excluded.provider,
             logo_url=excluded.logo_url,
             is_fallback=excluded.is_fallback,
             last_checked_at=excluded.last_checked_at,
             updated_at=excluded.updated_at""",
        (key, name, provider or "cache", safe_url, 1 if is_fallback or not safe_url else 0, now, now, now),
    )
    return {"team_key": key, "team_name": name, "logo_url": safe_url, "provider": provider, "is_fallback": bool(is_fallback or not safe_url)}


def upsert_league_logo_cache(
    conn: sqlite3.Connection,
    league_name: Any,
    logo_url: Any,
    *,
    provider: str = "cache",
    is_fallback: bool = False,
) -> dict[str, Any]:
    ensure_crest_logo_schema(conn)
    name = str(league_name or "Competición").strip() or "Competición"
    key = normalize_logo_key(name)
    safe_url = safe_logo_url(logo_url)
    now = _now_iso()
    conn.execute(
        """INSERT INTO league_logo_cache(league_key,league_name,provider,logo_url,is_fallback,last_checked_at,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(league_key) DO UPDATE SET
             league_name=excluded.league_name,
             provider=excluded.provider,
             logo_url=excluded.logo_url,
             is_fallback=excluded.is_fallback,
             last_checked_at=excluded.last_checked_at,
             updated_at=excluded.updated_at""",
        (key, name, provider or "cache", safe_url, 1 if is_fallback or not safe_url else 0, now, now, now),
    )
    return {"league_key": key, "league_name": name, "logo_url": safe_url, "provider": provider, "is_fallback": bool(is_fallback or not safe_url)}


def resolve_team_crest_payload(team_name: Any, explicit_logo: Any = "", *, country: Any = "", provider: str = "ui") -> dict[str, Any]:
    name = str(team_name or "Equipo").strip() or "Equipo"
    logo = safe_logo_url(explicit_logo)
    is_real_logo = bool(logo and logo.startswith("https://"))
    crest_url = logo or fallback_crest_url(name)
    return {
        "team_key": normalize_logo_key(name),
        "name": name,
        "display_name": name,
        "country": str(country or ""),
        "provider": provider or ("provider" if is_real_logo else "fallback"),
        "logo_url": logo if is_real_logo else "",
        "crest_url": crest_url,
        "crest_mode": "logo" if is_real_logo else "fallback",
        "ui_class": "crest-logo" if is_real_logo else "crest-fallback",
        "has_real_logo": is_real_logo,
        "is_fallback": not is_real_logo,
        "visible_badge": "".join(part[:1].upper() for part in name.split()[:2]) or "NS",
    }


def resolve_league_logo_payload(league_name: Any, explicit_logo: Any = "", *, provider: str = "ui") -> dict[str, Any]:
    name = str(league_name or "Competición").strip() or "Competición"
    logo = safe_logo_url(explicit_logo)
    is_real_logo = bool(logo and logo.startswith("https://"))
    return {
        "league_key": normalize_logo_key(name),
        "name": name,
        "provider": provider or ("provider" if is_real_logo else "fallback"),
        "logo_url": logo if is_real_logo else "",
        "crest_url": logo or fallback_crest_url(name),
        "has_real_logo": is_real_logo,
        "is_fallback": not is_real_logo,
    }


def _fetch_one(conn: sqlite3.Connection | None, sql: str, params: tuple[Any, ...]) -> dict[str, Any]:
    if conn is None:
        return {}
    try:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return {}
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        columns = [col[0] for col in cur.description or []]
        return dict(zip(columns, row))
    except (sqlite3.Error, RuntimeError, OSError):
        return {}


def safe_get_team_logo(conn: sqlite3.Connection | None, team_name: Any = "", team_key: Any = "") -> dict[str, Any]:
    name = str(team_name or team_key or "Equipo").strip() or "Equipo"
    key = normalize_logo_key(team_key or name)
    fallback = resolve_team_crest_payload(name, "", provider="fallback")
    fallback["team_key"] = key
    try:
        row = _fetch_one(
            conn,
            """SELECT logo_url, team_name, provider, is_fallback
               FROM team_logo_cache
               WHERE team_key=? AND COALESCE(logo_url,'')!='' AND COALESCE(is_fallback,0)=0
               LIMIT 1""",
            (key,),
        )
        logo = safe_logo_url(row.get("logo_url"))
        if logo:
            return resolve_team_crest_payload(row.get("team_name") or name, logo, provider=row.get("provider") or "cache")
        row = _fetch_one(
            conn,
            """SELECT logo_url, name AS team_name, source AS provider
               FROM teams
               WHERE key=? AND COALESCE(logo_url,'')!=''
               LIMIT 1""",
            (key,),
        )
        logo = safe_logo_url(row.get("logo_url"))
        if logo:
            return resolve_team_crest_payload(row.get("team_name") or name, logo, provider=row.get("provider") or "teams")
    except Exception:
        return fallback
    return fallback


def safe_get_league_logo(conn: sqlite3.Connection | None, league_name: Any = "", league_key: Any = "") -> dict[str, Any]:
    name = str(league_name or league_key or "Competicion").strip() or "Competicion"
    key = normalize_logo_key(league_key or name)
    fallback = resolve_league_logo_payload(name, "", provider="fallback")
    fallback["league_key"] = key
    try:
        row = _fetch_one(
            conn,
            """SELECT logo_url, league_name, provider, is_fallback
               FROM league_logo_cache
               WHERE league_key=? AND COALESCE(logo_url,'')!='' AND COALESCE(is_fallback,0)=0
               LIMIT 1""",
            (key,),
        )
        logo = safe_logo_url(row.get("logo_url"))
        if logo:
            return resolve_league_logo_payload(row.get("league_name") or name, logo, provider=row.get("provider") or "cache")
    except Exception:
        return fallback
    return fallback


def safe_crest_context(conn: sqlite3.Connection | None, *, team_name: Any = "", team_key: Any = "", league_name: Any = "", league_key: Any = "") -> dict[str, Any]:
    if team_name or team_key:
        return safe_get_team_logo(conn, team_name=team_name, team_key=team_key)
    return safe_get_league_logo(conn, league_name=league_name, league_key=league_key)
