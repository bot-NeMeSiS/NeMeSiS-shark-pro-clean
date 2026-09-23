"""Legacy highlight consumers must preserve read truth and never initialize media on GET."""
from contextlib import closing
import sqlite3

import pytest

from engines import sportsdb_highlights_engine as media


@pytest.fixture
def catalogue(tmp_path):
    path = tmp_path / "media.sqlite"
    media.ensure_sportsdb_highlights_schema(path)
    return path


def add(path, ident="h1", match_id="m1", rights="LICENSED"):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            """INSERT INTO sportsdb_match_highlights
            (id,match_id,video_url,rights_status,commercial_use_status,source,updated_at)
            VALUES(?,?,?,?,?,?,?)""",
            (ident, match_id, "https://www.youtube.com/watch?v=SIMULATED_QA", rights,
             "ALLOWED" if rights == "LICENSED" else "UNKNOWN", "Synthetic QA",
             "2026-09-23T12:00:00+00:00"),
        )
        conn.commit()


@pytest.mark.parametrize("reader,args", [
    (media.sportsdb_highlight_by_id, ("h1",)),
    (media.sportsdb_highlights_map, (["m1"],)),
])
def test_new_legacy_readers_do_not_create_missing_database(tmp_path, reader, args):
    path = tmp_path / "absent.sqlite"
    result = reader(path, *args)
    assert result["ok"] is False
    assert result["read_state"] == "NO_DATABASE"
    assert not path.exists()


def test_single_reader_distinguishes_verified_missing_from_unavailable(catalogue):
    missing = media.sportsdb_highlight_by_id(catalogue, "absent")
    assert missing["ok"] is True and missing["read_state"] == "VERIFIED"
    assert missing["highlight"] == {}
    add(catalogue)
    found = media.sportsdb_highlight_by_id(catalogue, "h1")
    assert found["ok"] is True and found["highlight"]["match_id"] == "m1"


def test_batch_map_keeps_only_authorized_rows(catalogue):
    add(catalogue, "allowed", "m1", "LICENSED")
    add(catalogue, "blocked", "m1", "UNKNOWN_RIGHTS")
    add(catalogue, "other", "m2", "LICENSED")
    result = media.sportsdb_highlights_map(catalogue, ["m1", "m2"], limit_per_match=3)
    assert result["ok"] is True and result["read_state"] == "VERIFIED"
    assert [row["id"] for row in result["map"]["m1"]] == ["allowed"]
    assert [row["id"] for row in result["map"]["m2"]] == ["other"]


def test_legacy_context_unknown_is_not_zero(app_module, tmp_path, monkeypatch):
    path = tmp_path / "absent.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    context = app_module.v766_highlights_context()
    assert context["ok"] is False and context["read_state"] == "NO_DATABASE"
    for key in ("highlights_total", "with_video", "linked_matches", "stored_media_total",
                "authorized_highlights", "rights_warnings", "enriched_matches"):
        assert context[key] is None
    assert "Disponibilidad sin comprobar" in context["client_note"]
    assert not path.exists()


def test_legacy_badge_unknown_is_not_pending(app_module, tmp_path, monkeypatch):
    path = tmp_path / "absent.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    item = app_module.v766_enrich_matches_with_highlights([{"id": "m1"}])[0]
    assert item["highlight_read_state"] == "NO_DATABASE"
    assert item["has_highlights"] is None and item["highlight_count"] is None
    assert item["client_highlight_label"] == "Disponibilidad sin comprobar"
    assert not path.exists()


def test_content_center_does_not_call_pending_reader_when_catalogue_unavailable(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "v766_highlights_context", lambda limit=24: {
        "ok": False, "read_state": "READ_UNAVAILABLE", "status": "READ_UNAVAILABLE",
        "key_present": True, "latest": [], "recent_runs": [], "stored_media_total": None,
        "rights_warnings": None, "linked_matches": None, "enriched_matches": None,
    })
    monkeypatch.setattr(app_module, "v769_pending_highlight_snapshot",
                        lambda *a, **k: pytest.fail("pending reader should not run"))
    center = app_module.v769_highlights_content_center({}, {"membership": "FREE"}, 24)
    assert center["read_ok"] is False and center["status"] == "READ_UNAVAILABLE"
    assert center["counts"]["videos"] is None and center["counts"]["pending"] is None
    assert "Disponibilidad sin comprobar" in center["headline"]
    assert "THESPORTSDB" not in center["description"].upper()


def test_verified_empty_content_center_is_valid_zero(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "v766_highlights_context", lambda limit=24: {
        "ok": True, "read_state": "VERIFIED", "status": "NO_LINKS_RECORDED",
        "key_present": False, "latest": [], "recent_runs": [], "stored_media_total": 0,
        "rights_warnings": 0, "linked_matches": 0, "enriched_matches": None,
    })
    monkeypatch.setattr(app_module, "v769_pending_highlight_snapshot",
                        lambda *a, **k: {"ok": True, "read_state": "VERIFIED", "matches": []})
    center = app_module.v769_highlights_content_center({}, {"membership": "FREE"}, 24)
    assert center["read_ok"] is True and center["counts"]["videos"] == 0
    assert center["counts"]["pending"] == 0 and center["counts"]["stored"] == 0
    assert "Sin resúmenes disponibles" in center["headline"]


def test_detail_snapshot_does_not_initialize_and_preserves_verified_missing(app_module, tmp_path, monkeypatch):
    absent = tmp_path / "absent.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(absent))
    unavailable = app_module.v769_get_highlight_snapshot("h1")
    assert unavailable["ok"] is False and unavailable["read_state"] == "NO_DATABASE"
    assert not absent.exists()

    ready = tmp_path / "ready.sqlite"
    media.ensure_sportsdb_highlights_schema(ready)
    monkeypatch.setattr(app_module, "DB_PATH", str(ready))
    missing = app_module.v769_get_highlight_snapshot("not-there")
    assert missing["ok"] is True and missing["read_state"] == "VERIFIED"
    assert missing["highlight"] == {}


def test_batch_reader_is_read_only(catalogue, monkeypatch):
    add(catalogue, "allowed", "m1", "LICENSED")
    before = catalogue.read_bytes()
    original = sqlite3.connect
    statements = []
    def connect(*args, **kwargs):
        conn = original(*args, **kwargs)
        conn.set_trace_callback(statements.append)
        return conn
    monkeypatch.setattr(sqlite3, "connect", connect)
    result = media.sportsdb_highlights_map(catalogue, ["m1"])
    assert result["ok"] is True
    assert not any(s.lstrip().upper().startswith(("CREATE","INSERT","UPDATE","ALTER","DELETE","REPLACE")) for s in statements)
    assert catalogue.read_bytes() == before


def test_unavailable_detail_page_is_safe_client_state_not_5xx(app_module, tmp_path, monkeypatch):
    path = tmp_path / "absent.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(path))
    monkeypatch.setattr(app_module, "dashboard_data", lambda *a, **k: {})
    client = app_module.app.test_client()
    response = client.get("/highlight/missing-qa")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "No se pudo comprobar este resumen" in text
    assert "no exista" in text
    assert not path.exists()
