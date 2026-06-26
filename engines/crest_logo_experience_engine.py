"""V850 crest and logo presentation helpers.

This layer prefers cached/provider logo references and always returns a local
fallback. It never downloads images and never requires a provider call.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from engines.crest_engine import (
    fallback_crest_url,
    normalize_logo_key,
    resolve_league_logo_payload,
    resolve_team_crest_payload,
    safe_get_league_logo,
    safe_get_team_logo,
    safe_logo_url,
)


def normalize_logo_url(url: Any) -> str:
    return safe_logo_url(url)


def get_logo_fallback(team_or_league: Any) -> str:
    name = str(team_or_league or "Equipo").strip() or "Equipo"
    return fallback_crest_url(name)


def _connect(db_path: str | None) -> sqlite3.Connection | None:
    if not db_path:
        return None
    try:
        conn = sqlite3.connect(db_path, timeout=0.2)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def get_team_logo(team_id: Any = None, team_name: Any = None, provider_id: Any = None, db_path: str | None = None) -> dict[str, Any]:
    name = str(team_name or team_id or provider_id or "Equipo").strip() or "Equipo"
    key = normalize_logo_key(provider_id or team_id or name)
    conn = _connect(db_path)
    try:
        if conn is not None:
            found = safe_get_team_logo(conn, team_name=name, team_key=key)
            if found:
                found.setdefault("logo_state", "provider_cache" if found.get("has_real_logo") else "fallback")
                return found
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
    payload = resolve_team_crest_payload(name, "", provider="fallback")
    payload["logo_state"] = "fallback"
    payload["provider_id"] = str(provider_id or team_id or "")
    return payload


def get_league_logo(league_id: Any = None, league_name: Any = None, provider_id: Any = None, db_path: str | None = None) -> dict[str, Any]:
    name = str(league_name or league_id or provider_id or "Competición").strip() or "Competición"
    key = normalize_logo_key(provider_id or league_id or name)
    conn = _connect(db_path)
    try:
        if conn is not None:
            found = safe_get_league_logo(conn, league_name=name, league_key=key)
            if found:
                found.setdefault("logo_state", "provider_cache" if found.get("has_real_logo") else "fallback")
                return found
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
    payload = resolve_league_logo_payload(name, "", provider="fallback")
    payload["logo_state"] = "fallback"
    payload["provider_id"] = str(provider_id or league_id or "")
    return payload


def cache_logo_reference(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Dry helper for checks/admin: documents a cache intent without writing."""
    name = kwargs.get("team_name") or kwargs.get("league_name") or (args[0] if args else "Logo")
    url = kwargs.get("logo_url") or (args[1] if len(args) > 1 else "")
    return {
        "ok": True,
        "would_cache": bool(normalize_logo_url(url)),
        "name": str(name or "Logo"),
        "logo_url": normalize_logo_url(url),
        "write_performed": False,
        "policy": "No se descargan imágenes ni se escribe SQLite durante render.",
    }


def build_team_crest_payload(team: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(team, dict):
        name = team.get("name") or team.get("team_name") or team.get("safe_home") or team.get("home_team") or team.get("safe_away") or team.get("away_team") or "Equipo"
        logo = team.get("logo_url") or team.get("crest_url") or team.get("home_logo") or team.get("away_logo") or ""
        provider_id = team.get("provider_id") or team.get("team_id") or team.get("id") or ""
        payload = resolve_team_crest_payload(name, logo, provider=team.get("provider") or "provider-cache")
        payload["provider_id"] = str(provider_id or "")
        payload["logo_state"] = "provider_cache" if payload.get("has_real_logo") else "fallback"
        return payload
    return resolve_team_crest_payload(str(team or "Equipo"), "", provider="fallback")


def build_league_logo_payload(league: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(league, dict):
        name = league.get("name") or league.get("league_name") or league.get("competition_name") or "Competición"
        logo = league.get("logo_url") or league.get("league_logo") or league.get("crest_url") or ""
        provider_id = league.get("provider_id") or league.get("league_id") or league.get("id") or ""
        payload = resolve_league_logo_payload(name, logo, provider=league.get("provider") or "provider-cache")
        payload["provider_id"] = str(provider_id or "")
        payload["logo_state"] = "provider_cache" if payload.get("has_real_logo") else "fallback"
        return payload
    return resolve_league_logo_payload(str(league or "Competición"), "", provider="fallback")


def explain_logo_state(team_or_league: Any) -> dict[str, Any]:
    payload = build_team_crest_payload(team_or_league) if not isinstance(team_or_league, dict) or not (team_or_league.get("league_name") or team_or_league.get("competition_name")) else build_league_logo_payload(team_or_league)
    if payload.get("has_real_logo"):
        return {"label": "Logo del proveedor", "message": "Se usa una referencia segura cacheada del proveedor.", "payload": payload}
    return {"label": "Fallback premium", "message": "No hay logo real disponible; se usa escudo local sin inventar oficial.", "payload": payload}
