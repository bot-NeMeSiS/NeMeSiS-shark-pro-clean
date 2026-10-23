from datetime import datetime, timezone
import sqlite3

from engines.calendar_export_engine import build_match_calendar_event
from engines.ui_localization_engine import catalogue, translate


def _unfold(ical: str) -> list[str]:
    lines = ical.split("\r\n")
    result: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and result:
            result[-1] += line[1:]
        elif line:
            result.append(line)
    return result


def test_calendar_event_uses_provider_offset_and_stable_match_identity():
    match = {
        "id": "af-42",
        "kickoff_iso": "2026-10-25T02:30:00+02:00",
        "home_team": "Granada",
        "away_team": "Club Sur",
        "competition_name": "Liga, España",
    }
    generated = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

    first = build_match_calendar_event(match, event_url="https://example.test/match/af-42", generated_at=generated)
    second = build_match_calendar_event(match, event_url="https://example.test/match/af-42", generated_at=generated)

    assert first == second
    lines = _unfold(first)
    assert "METHOD:PUBLISH" not in lines
    assert not any(line.startswith("ORGANIZER:") for line in lines)
    assert any(line.startswith("DTSTART:") for line in lines)
    assert "DTSTART:20261025T003000Z" in lines
    assert "SUMMARY:Granada vs Club Sur" in lines
    assert any(
        line.startswith(r"DESCRIPTION:Competición: Liga\, España\nCopia estática importada\;")
        for line in lines
    )
    assert next(line for line in lines if line.startswith("UID:"))
    assert "DTSTAMP:20261020T120000Z" in lines
    assert "DTEND:" not in "\n".join(lines)
    assert "DURATION:" not in "\n".join(lines)


def test_calendar_event_marks_date_only_without_inventing_a_kickoff():
    ical = build_match_calendar_event(
        {
            "id": "match-1",
            "kickoff_iso": "2026-10-25",
            "home_team": "Club Norte",
            "away_team": "Club Sur",
        },
        event_url="https://example.test/match/match-1",
        generated_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
    )

    lines = _unfold(ical)
    assert "DTSTART;VALUE=DATE:20261025" in lines
    assert "METHOD:PUBLISH" not in lines
    assert any(line.startswith("DTSTART") for line in lines)
    assert any("Hora de inicio no disponible" in line for line in lines)
    assert not any(line.startswith("DTEND") for line in lines)
    assert not any(line.startswith("DURATION") for line in lines)

    timed = build_match_calendar_event(
        {
            "id": "match-2",
            "kickoff_iso": "2026-10-26",
            "kickoff_time": "02:30",
            "home_team": "Club Norte",
            "away_team": "Club Sur",
        },
        event_url="https://example.test/match/match-2",
    )
    assert "DTSTART:20261026T013000Z" in _unfold(timed)

    canonical_date = build_match_calendar_event(
        {
            "id": "match-3",
            "kickoff_iso": "2026-10-26",
            "match_date": "2026-10-27",
            "kickoff_time": "02:30",
            "home_team": "Club Norte",
            "away_team": "Club Sur",
        },
        event_url="https://example.test/match/match-3",
    )
    assert "DTSTART:20261026T013000Z" in _unfold(canonical_date)


def test_calendar_event_rejects_ambiguous_or_nonexistent_madrid_wall_times():
    common = {
        "home_team": "Club Norte",
        "away_team": "Club Sur",
    }

    # Madrid repeats 02:30 when summer time ends; without an explicit offset
    # the source does not say which of the two kickoffs is intended.
    assert build_match_calendar_event(
        {**common, "id": "ambiguous", "kickoff_iso": "2026-10-25", "kickoff_time": "02:30"},
        event_url="",
    ) is None

    # Madrid skips 02:30 when summer time starts, so it is not a real instant.
    assert build_match_calendar_event(
        {**common, "id": "nonexistent", "kickoff_iso": "2026-03-29T02:30:00"},
        event_url="",
    ) is None

    # An explicit source offset disambiguates the repeated hour.
    explicit = build_match_calendar_event(
        {**common, "id": "explicit", "kickoff_iso": "2026-10-25T02:30:00+01:00"},
        event_url="",
    )
    assert "DTSTART:20261025T013000Z" in _unfold(explicit)


def test_calendar_event_escapes_injection_and_folds_utf8_lines():
    ical = build_match_calendar_event(
        {
            "id": "match-escape",
            "kickoff_iso": "2026-10-25T12:00:00Z",
            "home_team": "Club;\nBEGIN:VEVENT",
            "away_team": "Equipo " + chr(0x00D1) * 120,
            "venue": "Campo, principal",
        },
        event_url="https://example.test/match/match-escape",
    )

    lines = ical.split("\r\n")
    assert all(len(line.encode("utf-8")) <= 75 for line in lines if line)
    logical = _unfold(ical)
    assert any(line.startswith(r"SUMMARY:Club\;\nBEGIN:VEVENT vs Equipo ") for line in logical)
    assert r"LOCATION:Campo\, principal" in logical
    assert logical.count("BEGIN:VEVENT") == 1


def test_calendar_event_requires_real_identity_teams_and_date():
    assert build_match_calendar_event({}, event_url="https://example.test/match/x") is None
    assert build_match_calendar_event(
        {"id": "x", "match_date": "not-a-date", "home_team": "A", "away_team": "B"},
        event_url="https://example.test/match/x",
    ) is None


def test_calendar_export_marks_cancelled_events_and_does_not_confirm_postponed_kickoff():
    generated = datetime(2026, 10, 20, tzinfo=timezone.utc)
    base = {
        "id": "match-life",
        "kickoff_iso": "2026-10-25T19:00:00+01:00",
        "home_team": "Club Norte",
        "away_team": "Club Sur",
    }

    cancelled = _unfold(build_match_calendar_event(
        {**base, "calendar_lifecycle": "CANCELLED"},
        event_url="",
        static_copy_notice="Static copy; no automatic updates.",
        generated_at=generated,
    ))
    assert "STATUS:CANCELLED" in cancelled
    assert "DTSTART:20261025T180000Z" in cancelled
    assert "SUMMARY:Cancelado: Club Norte vs Club Sur" in cancelled
    assert any(r"Static copy\; no automatic updates." in line for line in cancelled)

    for lifecycle in ("POSTPONED", "SUSPENDED", "STALE", "INCOMPLETE", "CONFLICT", "ARCHIVED"):
        assert build_match_calendar_event(
            {**base, "calendar_lifecycle": lifecycle},
            event_url="",
            generated_at=generated,
        ) is None

    assert build_match_calendar_event(
        {"id": "x", "match_date": "2026-10-25", "home_team": "A"},
        event_url="https://example.test/match/x",
    ) is None


def test_calendar_export_cold_http_request_is_read_only_and_supports_legacy_schema(
    client, app_module, monkeypatch, tmp_path,
):
    database = tmp_path / "legacy-matches.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """CREATE TABLE matches(
             id TEXT PRIMARY KEY, match_date TEXT, kickoff_time TEXT,
             home_team TEXT, away_team TEXT, status TEXT, raw_json TEXT
           )"""
    )
    private_marker = "PRIVATE_RAW_MATCH_MARKER"
    connection.execute(
        "INSERT INTO matches VALUES(?,?,?,?,?,?,?)",
        ("af-42", "2026-10-25", "19:30", "Granada", "Club Sur", "NS", private_marker),
    )
    connection.commit()
    connection.close()
    before = database.read_bytes()

    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot-apuestas-crgf.onrender.com")
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    initialization_attempts = []

    def forbidden_initialization():
        initialization_attempts.append(True)
        raise AssertionError("calendar GET must not initialize the database")

    monkeypatch.setattr(
        app_module,
        "initialize_once",
        forbidden_initialization,
    )

    response = client.get("/calendar/match/af-42.ics", headers={"Host": "untrusted.example"})

    assert response.status_code == 200
    assert response.mimetype == "text/calendar"
    assert response.headers["Content-Disposition"].endswith('filename="nemesis-partido-af-42.ics"')
    assert response.headers["Cache-Control"] == "private, no-store"
    exported = response.get_data(as_text=True)
    assert "DTSTART:20261025T183000Z" in exported
    assert "METHOD:PUBLISH" not in exported
    assert "ORGANIZER:" not in exported
    assert "URL:https://bot-apuestas-crgf.onrender.com/partido/af-42" in exported
    assert any(
        r"Copia estática importada\; no se actualiza automáticamente." in line
        for line in _unfold(exported)
    )
    assert "untrusted.example" not in exported
    assert private_marker not in exported
    assert database.read_bytes() == before
    assert initialization_attempts == []
    missing_recording = []

    def forbidden_not_found_recording(*_args, **_kwargs):
        missing_recording.append(True)
        raise AssertionError("an expected calendar miss must not write global 404 diagnostics")

    monkeypatch.setattr(app_module, "v896_record_not_found", forbidden_not_found_recording)
    missing_response = client.get("/calendar/match/missing.ics")
    assert missing_response.status_code == 404
    assert missing_recording == []


def test_calendar_export_route_omits_the_old_kickoff_for_a_postponed_match(
    client, app_module, monkeypatch, tmp_path,
):
    database = tmp_path / "postponed.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE matches(id TEXT PRIMARY KEY, match_date TEXT, kickoff_time TEXT, home_team TEXT, away_team TEXT, status TEXT)"
    )
    connection.execute(
        "INSERT INTO matches VALUES(?,?,?,?,?,?)",
        ("af-postponed", "2026-10-20", "20:00", "Club Norte", "Club Sur", "PST"),
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    response = client.get("/calendar/match/af-postponed.ics")

    assert response.status_code == 422
    assert response.mimetype == "text/plain"
    assert "no hay una fecha fiable confirmada" in response.get_data(as_text=True).lower()
    assert "Content-Disposition" not in response.headers


def test_calendar_export_route_returns_404_for_unknown_match(
    client, app_module, monkeypatch, tmp_path,
):
    database = tmp_path / "empty-matches.sqlite"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE matches(id TEXT PRIMARY KEY)")
    connection.commit()
    connection.close()
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    monkeypatch.setattr(
        app_module,
        "v896_record_not_found",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("calendar misses must not enter the disk-writing 404 reporter")
        ),
    )
    assert client.get("/calendar/match/missing.ics").status_code == 404


def test_calendar_export_with_missing_database_returns_unavailable_without_creating_it(
    client, app_module, monkeypatch, tmp_path,
):
    database = tmp_path / "not-created.sqlite"
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    initialization_attempts = []

    def forbidden_initialization():
        initialization_attempts.append(True)
        raise AssertionError("calendar GET must not initialize the database")

    monkeypatch.setattr(
        app_module,
        "initialize_once",
        forbidden_initialization,
    )
    not_found_recordings = []

    def forbidden_not_found_recording(*_args, **_kwargs):
        not_found_recordings.append(True)
        raise AssertionError("calendar path misses must not write global 404 diagnostics")

    monkeypatch.setattr(app_module, "v896_record_not_found", forbidden_not_found_recording)

    response = client.get("/calendar/match/af-42.ics")

    assert response.status_code == 503
    assert not database.exists()
    assert initialization_attempts == []
    malformed = client.get("/calendar/match/af-42.ics/extra")
    assert malformed.status_code == 404
    malformed_head = client.head("/calendar/match/af-42.ics/extra")
    assert malformed_head.status_code == 404
    malformed_options = client.options("/calendar/match/af-42.ics/extra")
    assert malformed_options.status_code == 404
    for method in ("get", "head", "options"):
        namespace_root = getattr(client, method)("/calendar/match")
        assert namespace_root.status_code == 404
    assert not database.exists()
    assert initialization_attempts == []
    assert not_found_recordings == []


def test_unrelated_not_found_route_still_uses_global_diagnostic(client, app_module, monkeypatch):
    recorded = []
    monkeypatch.setattr(app_module, "initialize_once", lambda: None)

    def record(path, method, referrer, user_agent, **kwargs):
        recorded.append((path, method, kwargs.get("source")))
        return {"count": len(recorded)}

    monkeypatch.setattr(app_module, "v896_record_not_found", record)
    response = client.get("/unrelated-missing-route")

    assert response.status_code == 404
    assert recorded == [("/unrelated-missing-route", "GET", "flask_404")]


def test_calendar_export_copy_and_lifecycle_translations_are_registered():
    assert catalogue()
    assert translate("Copia estática importada; no se actualiza automáticamente.", "en") == (
        "Static calendar copy; it will not update automatically."
    )
    assert translate(
        "No se puede añadir al calendario porque no hay una fecha fiable confirmada. Revisa la ficha del partido.",
        "en",
    ) == "This match cannot be added to the calendar because no reliable date is confirmed. Check the match details."
    assert translate("Partido aplazado: la nueva fecha no está confirmada.", "fr") == (
        "Match reporté : la nouvelle date n’est pas confirmée."
    )
    assert translate("Partido archivado", "en") == "Archived match"


def test_calendar_export_reads_existing_sqlite_without_changing_database(tmp_path, app_module, monkeypatch):
    database = tmp_path / "matches.sqlite"
    connection = sqlite3.connect(database)
    connection.execute(
        """CREATE TABLE matches(
             id TEXT PRIMARY KEY, external_id TEXT, match_date TEXT, kickoff_time TEXT,
             match_time TEXT, kickoff_iso TEXT, home_team TEXT, away_team TEXT,
             competition_name TEXT, league_name TEXT, venue TEXT, status TEXT, score TEXT,
             home_score TEXT, away_score TEXT, raw_json TEXT, last_synced_at TEXT, updated_at TEXT
           )"""
    )
    connection.execute(
        """INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "persisted-1", "fixture-1", "2026-10-25", "20:30", "20:30",
            "2026-10-25T20:30:00+01:00", "Club Norte", "Club Sur", "Liga Real",
            "Liga Real", "Estadio Norte", "NS", "", None, None, "",
            "2026-10-23T09:00:00+02:00", "2026-10-23T09:00:00+02:00",
        ),
    )
    connection.commit()
    connection.close()
    before = database.read_bytes()
    monkeypatch.setattr(app_module, "DB_PATH", str(database))
    monkeypatch.setattr(app_module, "password_reset_public_base_url", lambda: "")

    with app_module.app.test_request_context("/calendar/match/persisted-1.ics"):
        response = app_module.calendar_match_export("persisted-1")

    assert response.status_code == 200
    assert "DTSTART:20261025T193000Z" in response.get_data(as_text=True)
    assert database.read_bytes() == before
