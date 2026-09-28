"""Compatibility tests for the recovered Highlights safety foundation.

This file deliberately tests only the foundation recovered on top of current main:
URL validation, rights/channel gating, safe match association, audited review, and
read-only catalogue behavior. Client routes/player activation remain a later phase.
"""
from __future__ import annotations

import sqlite3

import pytest

from engines import sportsdb_highlights_engine as media
from engines.highlight_read_model import read_highlights_for_match, read_highlights_summary
from engines.highlight_review_engine import ReviewError, decide_highlight, review_snapshot
from engines.highlight_url_engine import public_https_url, safe_embed_url


def _db(tmp_path):
    path = tmp_path / "media.sqlite"
    media.ensure_sportsdb_highlights_schema(path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE matches("
            "id TEXT,external_id TEXT,source TEXT,home_team TEXT,away_team TEXT,"
            "match_date TEXT,league_id TEXT,league_name TEXT)"
        )
        conn.execute(
            "INSERT INTO matches VALUES(?,?,?,?,?,?,?,?)",
            ("m1","sportsdb-123","TheSportsDB API","Norte","Sur","2026-09-20","1","Liga QA"),
        )
    return path


def _payload(**extra):
    base = {
        "idEvent":"123",
        "dateEvent":"2026-09-20",
        "strHomeTeam":"Norte",
        "strAwayTeam":"Sur",
        "strLeague":"Liga QA",
        "idLeague":"1",
        "strVideo":"https://www.youtube.com/watch?v=officialQA1",
    }
    base.update(extra)
    return base


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "http://youtube.com/watch?v=a",
    "https://user:pass@youtube.com/watch?v=a",
    "https://127.0.0.1/v",
    "https://localhost/v",
    "https://host.local/v",
    "https://youtube.com:444/watch?v=a",
    "https://youtube.com\\@evil.org/v",
    "https://youtube.com/watch?v=a\r\nX",
    "https://[::1]/v",
])
def test_invalid_public_video_urls_fail_closed(url):
    assert public_https_url(url) == ""
    row = {
        "video_url": url,
        "rights_status": "LICENSED",
        "commercial_use_status": "ALLOWED",
        "rights_verified_at": "2026-09-28T12:00:00+02:00",
        "allowed_channels_json": '["APP"]',
    }
    classified = media.classify_stored_highlight(row, channel="APP")
    assert classified["show_block"] is False
    assert classified["can_link"] is False
    assert classified["can_embed"] is False


def test_unsafe_video_url_is_not_persisted(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as conn:
        saved = media._upsert_highlight(conn, _payload(strVideo="javascript:alert(1)"))
        assert saved is None
        assert conn.execute("SELECT COUNT(*) FROM sportsdb_match_highlights").fetchone()[0] == 0


def test_channel_scope_is_enforced_even_for_approved_rights():
    row = {
        "video_url": "https://www.youtube.com/watch?v=officialQA1",
        "embed_url": "https://www.youtube-nocookie.com/embed/officialQA1",
        "rights_status": "LICENSED",
        "commercial_use_status": "ALLOWED",
        "rights_verified_at": "2026-09-28T12:00:00+02:00",
        "official_source_verified": 1,
        "allowed_channels_json": '["APP"]',
        "embed_policy": "EMBED",
    }
    assert media.classify_stored_highlight(row, channel="APP")["show_block"] is True
    blocked = media.classify_stored_highlight(row, channel="TELEGRAM")
    assert blocked["show_block"] is False
    assert blocked["decision"] == "BLOCKED"


def test_safe_embed_requires_same_video_identity():
    original = "https://www.youtube.com/watch?v=officialQA1"
    assert safe_embed_url(original).endswith("/officialQA1")
    assert safe_embed_url(original, "https://www.youtube.com/embed/different") == ""


def test_match_association_is_provider_scoped_and_unambiguous(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        assert media._find_match(conn, _payload()) == "m1"
        conn.execute(
            "UPDATE matches SET external_id='123',source='API-Football',home_team='Other',away_team='Teams'"
        )
        assert media._find_match(conn, _payload()) is None


def test_ambiguous_exact_pair_is_not_linked(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "INSERT INTO matches VALUES(?,?,?,?,?,?,?,?)",
            ("m2","sportsdb-456","TheSportsDB API","Norte","Sur","2026-09-20","1","Liga QA"),
        )
        item = _payload(idEvent="unknown")
        assert media._find_match(conn, item) is None


def test_review_records_app_only_authorization_and_is_audited(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        saved = media._upsert_highlight(conn, _payload())
        assert saved and saved["match_id"] == "m1"

    snapshot = review_snapshot(path)
    assert snapshot["items"]
    item = snapshot["items"][0]
    result = decide_highlight(
        path,
        item["id"],
        {
            "decision":"LINK_ONLY",
            "review_token":item["review_token"],
            "evidence_url":"https://example.org/licence",
            "attribution":"Fuente autorizada QA",
            "basis":"Licencia sintética de prueba para esta URL en APP.",
            "rights_status":"LICENSED",
            "confirmed":"1",
        },
        actor="qa-admin",
    )
    assert result["ok"] is True

    visible = read_highlights_for_match(path, "m1")["highlights"]
    assert len(visible) == 1
    classified = visible[0]
    assert classified["can_link"] is True
    assert classified["can_embed"] is False
    assert classified["allowed_channels"] == ["APP"]

    with sqlite3.connect(path) as conn:
        audit = conn.execute(
            "SELECT actor,decision FROM sportsdb_highlight_reviews ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert audit == ("qa-admin", "LINK_ONLY")


def test_stale_review_token_cannot_be_reused(tmp_path):
    path = _db(tmp_path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        media._upsert_highlight(conn, _payload())
    item = review_snapshot(path)["items"][0]
    values = {
        "decision":"LINK_ONLY",
        "review_token":item["review_token"],
        "evidence_url":"https://example.org/licence",
        "attribution":"Fuente autorizada QA",
        "basis":"Licencia sintética.",
        "rights_status":"LICENSED",
        "confirmed":"1",
    }
    decide_highlight(path, item["id"], values, actor="qa-admin")
    with pytest.raises(ReviewError):
        decide_highlight(path, item["id"], values, actor="qa-admin-2")


def test_missing_catalogue_is_read_only_and_not_fake_zero(tmp_path):
    path = tmp_path / "absent.sqlite"
    summary = read_highlights_summary(path)
    assert summary["ok"] is False
    assert summary["read_state"] == "NO_DATABASE"
    assert summary["highlights_total"] is None
    assert not path.exists()


def test_client_highlights_template_never_trusts_technical_headline():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "highlights.html").read_text(encoding="utf-8")
    assert "center.get('headline')" not in template
    assert "Resúmenes de partidos" in template
    assert "Catálogo no verificable" in template
    assert "Disponibilidad sin comprobar" in template
    assert "Partidos sin vídeo disponible" in template
