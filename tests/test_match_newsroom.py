"""Synthetic sports newsroom: real fixture states, link-only rights and protected Admin."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import sqlite3

import pytest

from engines import match_newsroom_engine as news


FIXTURES = [
    ("pre-fixture", "Equipo Local", "Equipo Visitante", "2026-10-29", "NS", None, None, "TheSportsDB"),
    ("post-fixture", "Equipo Rojo", "Equipo Azul", "2026-10-27", "FT", 2, 1, "API-Football"),
    ("uncertain-fixture", "Equipo A", "Equipo B", "2026-10-26", "FT", None, None, "Unknown"),
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "newsroom.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE matches(id TEXT PRIMARY KEY,home_team TEXT,away_team TEXT,"
                     "match_date TEXT,status TEXT,home_score INTEGER,away_score INTEGER,source TEXT)")
        conn.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?)", FIXTURES)
    return str(path)


def stamp():
    return datetime(2026, 10, 28, 12, tzinfo=ZoneInfo("Europe/Madrid"))


def link(mid="pre-fixture", **changes):
    return {
        "match_id": mid, "phase": "PRE" if mid == "pre-fixture" else "POST",
        "publisher": "UEFA", "url": "https://www.uefa.com/uefachampionsleague/news/example",
        "label": "Contexto oficial del encuentro", "link_only_confirmed": "1",
        **changes,
    }


def test_newsroom_read_only_without_schema_no_faked_recaps(db):
    before = hashlib.sha256(Path(db).read_bytes()).hexdigest()
    result = news.board(db, stamp())
    assert result["state"] == "AVAILABLE"
    assert len(result["previews"]) == 1
    assert len(result["recaps"]) == 1
    assert result["recaps"][0]["score"] == "2-1"
    assert all("uncertain-fixture" not in str(result[k]) for k in ("recaps", "previews"))
    assert result["external_calls"] == result["copied_articles"] == 0
    assert not result["recaps"][0]["links"]
    assert hashlib.sha256(Path(db).read_bytes()).hexdigest() == before
    with sqlite3.connect(db) as conn:
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='match_external_news_links'").fetchone()


def test_verified_external_link_bound_to_unchanged_match_identity(db):
    saved = news.add_link(db, link(), "admin")
    assert saved["publication_state"] == "EXTERNAL_LINK_ONLY"
    match = news.match_links(db, "pre-fixture")
    assert len(match) == 1 and match[0]["publisher"] == "UEFA"
    assert match[0]["kind"] == "EXTERNAL_LINK_ONLY"
    assert news.board(db, stamp())["previews"][0]["links"][0]["label"] == link()["label"]
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE matches SET away_team='Otro Club' WHERE id='pre-fixture'")
    assert news.match_links(db, "pre-fixture") == []
    assert news.board(db, stamp())["previews"][0]["links"] == []


def test_withdraw_keeps_internal_record_but_hides_public_link(db):
    saved = news.add_link(db, link(), "admin")
    news.withdraw_link(db, saved["id"])
    assert news.match_links(db, "pre-fixture") == []
    rows = news.editor_links(db)
    assert len(rows) == 1 and rows[0]["visible"] == 0
    with pytest.raises(ValueError):
        news.withdraw_link(db, saved["id"])


@pytest.mark.parametrize("changes", [
    {"url": "http://www.uefa.com/sport"},
    {"url": "https://evil-uefa.com/sport"},
    {"url": "https://uefa.com.evil.com/sport"},
    {"url": "https://user:secret@www.uefa.com/news"},
    {"url": "https://www.uefa.com:8443/news"},
    {"url": r"https://www.uefa.com\@attacker.invalid/news"},
    {"url": "https://www.uefa.com/news#fragment"},
    {"publisher": "Unapproved media"},
    {"label": "<script>alert(1)</script>"},
    {"link_only_confirmed": "0"},
    {"match_id": "invented-id"},
])
def test_reject_unapproved_or_fake_source(db, changes):
    with pytest.raises(ValueError):
        news.add_link(db, link(**changes), "admin")


def test_no_database_or_urls_fetch_on_newsroom_read(tmp_path):
    path = tmp_path / "missing.sqlite"
    state = news.board(path, stamp())
    assert state["state"] == "READ_UNAVAILABLE"
    assert not path.exists()


def test_admin_newsroom_routes_require_role_and_csrf(app_module, tmp_path, monkeypatch):
    a = app_module
    monkeypatch.setattr(a, "DB_PATH", str(tmp_path / "app.sqlite"))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    monkeypatch.setattr(a, "LOCAL_SAFE_DATA_DIR", tmp_path)
    a.seed_core()
    a.app.config.update(TESTING=True)
    anon = a.app.test_client()
    assert anon.get("/noticias").status_code == 200
    head = anon.head("/noticias")
    assert head.status_code == 200 and head.data == b""
    assert anon.get("/admin/newsroom").status_code == 403
    assert anon.head("/admin/newsroom").status_code == 403
    assert anon.get("/api/admin/postmatch/status").status_code == 403
    assert anon.post("/admin/newsroom/link", data=link()).status_code == 403
    admin = a.app.test_client()
    with admin.session_transaction() as s:
        s.update(user_id="SIMULATED_QA_admin", user_role="ADMIN", membership="ADMIN")
        token = a.generate_csrf_token(s)
    assert admin.get("/admin/newsroom").status_code == 200
    assert admin.post("/admin/newsroom/link", data=link()).status_code == 403
    failure = admin.post("/admin/newsroom/link", data={**link(), "csrf_token": token})
    assert failure.status_code == 400   # Fixture not in main application's synthetic DB.



def test_dense_future_matches_do_not_displace_real_postmatch(db):
    with sqlite3.connect(db) as conn:
        conn.executemany(
            "INSERT INTO matches VALUES(?,?,?,?,?,?,?,?)",
            ((f"upcoming-{i}", f"Local {i}", f"Visita {i}", "2026-10-29",
              "NS", None, None, "TheSportsDB") for i in range(240)),
        )
    state = news.board(db, stamp())
    assert state["state"] == "AVAILABLE"
    assert state["recaps"] and state["recaps"][0]["match_id"] == "post-fixture"
    assert state["recaps"][0]["score"] == "2-1"
    assert len(state["previews"]) <= 12 and len(state["recaps"]) <= 12


def test_batched_news_links_need_no_per_card_sql_open(db, monkeypatch):
    news.add_link(db, link(), "admin")
    def fail(*_args, **_kwargs):
        raise AssertionError("N+1 per-card link query attempted")
    monkeypatch.setattr(news, "match_links", fail)
    data = news.board(db, stamp())
    assert data["previews"][0]["links"][0]["kind"] == "EXTERNAL_LINK_ONLY"
    assert data["external_calls"] == 0
