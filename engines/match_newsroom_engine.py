"""Factual match news board with manually reviewed external links only.

No RSS scraping, copied article bodies, unlicensed images, real provider calls,
automatic publication, or made-up sporting facts. GET is strictly read-only.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import re
import secrets
import sqlite3

from engines.postmatch_store import identity

PUBLISHERS = {
    "UEFA": ("uefa.com",),
    "FIFA": ("fifa.com",),
    "LaLiga": ("laliga.com",),
    "RFEF": ("rfef.es",),
    "MARCA": ("marca.com",),
    "AS": ("as.com",),
    "BBC Sport": ("bbc.co.uk", "bbc.com"),
    "ESPN": ("espn.com",),
}
PHASES = ("PRE", "POST")
SCHEMA = """
CREATE TABLE IF NOT EXISTS match_external_news_links(
 id TEXT PRIMARY KEY, match_id TEXT NOT NULL, match_identity TEXT NOT NULL,
 phase TEXT NOT NULL, publisher TEXT NOT NULL, label TEXT NOT NULL,
 external_url TEXT NOT NULL, reviewed_at TEXT NOT NULL,
 reviewer TEXT NOT NULL, visible INTEGER NOT NULL DEFAULT 1,
 UNIQUE(match_id,external_url)
);
CREATE INDEX IF NOT EXISTS match_external_news_match
 ON match_external_news_links(match_id,match_identity,visible,phase);
"""

def _connection(db_path, write=False):
    path = Path(db_path).resolve()
    if not path.is_file():
        raise ValueError("SPORTS_DB_MISSING")
    conn = sqlite3.connect(path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                           uri=True, timeout=.6)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=600")
    if not write:
        conn.execute("PRAGMA query_only=ON")
    return conn

def _safe_url(url, publisher):
    if not isinstance(url, str) or len(url) > 700 or any(ch.isspace() for ch in url):
        raise ValueError("Enlace no válido.")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        if (parts.scheme != "https" or parts.username or parts.password or parts.port
            or not host or parts.fragment or not parts.path or "\\\\" in url):
            raise ValueError("Solo se admiten enlaces HTTPS directos del medio.")
        if publisher not in PUBLISHERS or not any(
            host == allowed or host.endswith("." + allowed)
            for allowed in PUBLISHERS[publisher]
        ):
            raise ValueError("El enlace no pertenece al medio seleccionado.")
    except (ValueError, TypeError) as exc:
        raise ValueError("Enlace HTTPS o dominio de medio no admitido.") from exc
    return url

def _caption(text):
    if not isinstance(text, str) or not 8 <= len(text.strip()) <= 140 or "<" in text or ">" in text:
        raise ValueError("Escribe una etiqueta propia de entre 8 y 140 caracteres.")
    return text.strip()

def _match(conn, mid):
    return conn.execute("SELECT * FROM matches WHERE id=? LIMIT 1", (mid,)).fetchone()

def add_link(db_path, data, actor):
    """Only an authenticated editor may attach an original label to a link."""
    if not isinstance(actor, str) or not actor or len(actor) > 128:
        raise ValueError("Requiere un editor administrativo identificado.")
    if not isinstance(data, dict) or data.get("link_only_confirmed") != "1":
        raise ValueError("Confirma que no se copia contenido del medio.")
    mid, phase, publisher = data.get("match_id"), data.get("phase"), data.get("publisher")
    if not isinstance(mid, str) or not 1 <= len(mid) <= 120 or phase not in PHASES:
        raise ValueError("Falta el partido o la fase.")
    url = _safe_url(data.get("url"), publisher)
    label = _caption(data.get("label"))
    with _connection(db_path, write=True) as conn:
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        raw = _match(conn, mid)
        if not raw:
            raise ValueError("El partido no está registrado.")
        current = dict(raw)
        if not current.get("home_team") or not current.get("away_team") or not current.get("match_date"):
            raise ValueError("La identidad del partido no es suficiente.")
        ident = identity(current)
        exists = conn.execute(
            "SELECT id FROM match_external_news_links WHERE match_id=? AND external_url=?",
            (mid, url)).fetchone()
        if exists:
            raise ValueError("El enlace ya existe para este partido.")
        link_id = "news:" + secrets.token_hex(16)
        conn.execute(
            "INSERT INTO match_external_news_links"
            "(id,match_id,match_identity,phase,publisher,label,external_url,reviewed_at,reviewer)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (link_id, mid, ident, phase, publisher, label, url,
             datetime.now(timezone.utc).isoformat(timespec="seconds"), actor),
        )
    return {"ok": True, "id": link_id, "publication_state": "EXTERNAL_LINK_ONLY"}

def withdraw_link(db_path, link_id):
    if not isinstance(link_id, str) or not re.fullmatch(r"news:[a-f0-9]{32}", link_id):
        raise ValueError("Enlace no válido.")
    with _connection(db_path, write=True) as conn:
        result = conn.execute(
            "UPDATE match_external_news_links SET visible=0 "
            "WHERE id=? AND visible=1", (link_id,))
        if not result.rowcount:
            raise ValueError("No existe un enlace publicado con ese identificador.")
    return {"ok": True, "id": link_id}

def _public_link(row):
    return {"phase": row["phase"], "publisher": row["publisher"], "label": row["label"],
            "url": row["external_url"], "reviewed_at": row["reviewed_at"],
            "kind": "EXTERNAL_LINK_ONLY"}

def match_links(db_path, match_id, limit=8):
    """Only same-identity, approved external links. Never trust match_id alone."""
    if not isinstance(match_id, str) or not 1 <= len(match_id) <= 120:
        return []
    try:
        with _connection(db_path) as conn:
            raw = _match(conn, match_id)
            if not raw:
                return []
            if not conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='match_external_news_links'").fetchone():
                return []
            current = identity(dict(raw))
            result = conn.execute(
                "SELECT phase,publisher,label,external_url,reviewed_at "
                "FROM match_external_news_links WHERE match_id=? "
                "AND match_identity=? AND visible=1 "
                "ORDER BY reviewed_at DESC,id DESC LIMIT ?",
                (match_id, current, min(max(int(limit), 1), 12))).fetchall()
            return [_public_link(row) for row in result]
    except (ValueError, OSError, sqlite3.Error):
        return []

def _score(value):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 30:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,2}", value):
        val = int(value)
        return val if val <= 30 else None
    return None

def board(db_path, now=None):
    """Limited original factual previews/recaps, never external news inference."""
    now = now or datetime.now(ZoneInfo("Europe/Madrid"))
    start = (now.date() - timedelta(days=7)).isoformat()
    end = (now.date() + timedelta(days=15)).isoformat()
    empty = {"contract": "NEMESIS-MATCH-NEWSROOM-V1", "state": "NO_DATA",
             "previews": [], "recaps": [], "external_calls": 0, "copied_articles": 0}
    try:
        with _connection(db_path) as conn:
            rows = conn.execute(
                "SELECT id,home_team,away_team,match_date,status,home_score,away_score,source "
                "FROM matches WHERE match_date>=? AND match_date<? "
                "ORDER BY match_date DESC,id LIMIT 220", (start, end)).fetchall()
        previews, recaps = [], []
        for row in rows:
            match = dict(row)
            mid = str(match.get("id") or "")
            home, away = str(match.get("home_team") or "").strip(), str(match.get("away_team") or "").strip()
            day = str(match.get("match_date") or "")[:10]
            state = str(match.get("status") or "").upper()
            if not mid or not home or not away or not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", day):
                continue
            h, a = _score(match.get("home_score")), _score(match.get("away_score"))
            common = {"match_id": mid, "home": home[:90], "away": away[:90],
                      "date": day, "source": str(match.get("source") or "Sin fuente")[:48]}
            if state in {"FT", "FINISHED", "FINAL", "AET", "PEN", "FINALIZADO"} and h is not None and a is not None:
                if len(recaps) < 12:
                    recaps.append({**common, "phase": "POST", "score": f"{h}-{a}",
                                   "summary": f"Resultado registrado: {home} {h}-{a} {away}. "
                                   "La crónica de incidencias depende de eventos verificados.",
                                   "links": match_links(db_path, mid, 3)})
            elif state in {"NS", "NOT_STARTED", "SCHEDULED", "TIMED", "TBD"} and day >= now.date().isoformat():
                if len(previews) < 12:
                    previews.append({**common, "phase": "PRE",
                                     "summary": f"Partido programado: {home} frente a {away}. "
                                     "Alineaciones y novedades: pendientes de confirmar.",
                                     "links": match_links(db_path, mid, 3)})
        return {**empty, "state": "AVAILABLE" if previews or recaps else "NO_DATA",
                "previews": sorted(previews, key=lambda x:x["date"]),
                "recaps": recaps}
    except (OSError, ValueError, sqlite3.Error):
        return {**empty, "state": "READ_UNAVAILABLE"}
