from __future__ import annotations

import gzip
import json
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


def _calendar_summary(app_module, count: int = 240) -> dict:
    today = date.fromisoformat(app_module.today_iso())
    matches = []
    for index in range(count):
        match_date = (today + timedelta(days=index % 7)).isoformat()
        matches.append({
            "id": f"calendar-payload-{index}",
            "match_id": f"calendar-payload-{index}",
            "home_team": f"Equipo local {index}",
            "away_team": f"Equipo visitante {index}",
            "competition_name": f"Competición {index % 12}",
            "league_name": f"Competición {index % 12}",
            "country": "España" if index % 2 == 0 else "Europa",
            "match_date": match_date,
            "kickoff_time": f"{12 + index % 10:02d}:{index % 60:02d}",
            "status": "NS",
            "v935_lifecycle": "UPCOMING",
            "source": "local-test",
        })
    summary = {
        "all_valid_matches": matches,
        "valid_upcoming_matches": matches,
        "valid_matches_available": matches,
        "valid_matches_today": [item for item in matches if item["match_date"] == app_module.today_iso()],
        "valid_live_events": [],
        "valid_active_picks": [],
        "finished_matches": [],
        "incident_matches": [],
        "incomplete_matches": [],
        "raw_matches_count": len(matches),
        "safe_message": "Agenda local de prueba.",
    }
    summary["sports_metrics"] = app_module.build_sports_metrics_contract(summary)
    return summary


def test_calendar_api_gzip_preserves_legacy_json_and_reduces_wire_size(
    app_module, client, monkeypatch
):
    from copy import deepcopy
    summary = _calendar_summary(app_module)
    generation = datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0)
    source_generations = []

    def supplied_summary(*_args, **_kwargs):
        # Two independent reads may legitimately carry different generation
        # metadata. Supply that input explicitly; do not freeze the App clock.
        current = deepcopy(summary)
        generated = (generation + timedelta(seconds=len(source_generations))).isoformat()
        current["metrics_generated_at_madrid"] = generated
        source_generations.append(generated)
        return {}, current

    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", supplied_summary)
    serialized = {}
    real_jsonify = app_module.jsonify

    def observe_serialized_response(*args, **kwargs):
        # Observe the actual serializer's untouched response before transport
        # hooks. The real route, serializer and gzip implementation all run.
        response = real_jsonify(*args, **kwargs)
        if app_module.request.path == "/api/calendar":
            value = response.get_json(silent=True)
            if isinstance(value, dict) and isinstance(value.get("calendar"), dict):
                encoding = app_module.request.headers.get("Accept-Encoding", "")
                serialized.setdefault(encoding, []).append(response.get_data())
        return response

    monkeypatch.setattr(app_module, "jsonify", observe_serialized_response)
    url = "/api/calendar?lane=week"
    plain = client.get(url, headers={"Accept-Encoding": "identity"})
    compressed = client.get(url, headers={"Accept-Encoding": "gzip"})

    assert plain.status_code == compressed.status_code == 200
    assert "Content-Encoding" not in plain.headers
    assert compressed.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in compressed.headers.get("Vary", "")
    assert set(serialized) == {"identity", "gzip"}
    assert len(serialized["identity"]) == len(serialized["gzip"]) == 1
    decoded = gzip.decompress(compressed.data)
    assert plain.data == serialized["identity"][0]
    assert decoded == serialized["gzip"][0]
    plain_payload, gzip_payload = plain.get_json(), json.loads(decoded)
    assert len(source_generations) == 2 and source_generations[0] != source_generations[1]
    for payload, generated in zip((plain_payload, gzip_payload), source_generations):
        assert payload["version"] == app_module.APP_VERSION
        calendar = payload["calendar"]
        assert calendar["sports_metrics"]["generated_at_madrid"] == generated
        assert calendar["counts"]["visible"] == len(summary["all_valid_matches"])
        assert len(calendar["matches"]) == len(summary["all_valid_matches"])
        assert payload["matches"] == calendar["matches"]
        assert {row["id"] for row in calendar["matches"]} == {
            row["id"] for row in summary["all_valid_matches"]
        }
    assert len(compressed.data) < len(plain.data)


def test_calendar_api_does_not_compress_when_client_rejects_gzip(
    app_module, client, monkeypatch
):
    summary = _calendar_summary(app_module)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *_args, **_kwargs: ({}, summary),
    )

    response = client.get(
        "/api/calendar?lane=week",
        headers={"Accept-Encoding": "gzip;q=0, identity"},
    )

    assert response.status_code == 200
    assert "Content-Encoding" not in response.headers
    assert response.get_json()["calendar"]["counts"]["visible"] == len(summary["all_valid_matches"])


def test_calendar_html_exposes_only_bounded_stage_timings(app_module, client, monkeypatch):
    summary = _calendar_summary(app_module, count=6)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *_args, **_kwargs: ({}, summary),
    )
    monkeypatch.setattr(
        app_module,
        "_v940_hydrate_selected_date_results",
        lambda value, _date: value,
    )
    def unexpected_unused_realtime(*_args, **_kwargs):
        raise AssertionError("Calendar must not derive an unused realtime context")

    monkeypatch.setattr(app_module, "get_realtime_safe_matches_context", unexpected_unused_realtime)

    response = client.get("/calendario")

    assert response.status_code == 200
    assert response.headers["X-Nemesis-Route-Phases"] == "calendar"
    timing = response.headers["Server-Timing"]
    for phase in (
        "sports_context",
        "historical_results",
        "calendar_context",
        "template_render",
    ):
        match = re.search(rf"(?:^|,\s*)calendar_{phase};dur=([0-9]+(?:\.[0-9]+)?)", timing)
        assert match, f"Missing timing for {phase}: {timing}"
        assert float(match.group(1)) >= 0
    assert "calendar_realtime_context;" not in timing


def test_calendar_cards_reuse_prepared_madrid_labels(app_module, client, monkeypatch):
    summary = _calendar_summary(app_module, count=1)
    match = summary["all_valid_matches"][0]
    match["kickoff_iso"] = f"{app_module.today_iso()}T23:30:00Z"
    with app_module.app.test_request_context(
        "/calendario?lane=week",
        headers={"Accept-Language": "en"},
    ):
        expected_label = app_module.ui_match_datetime(match)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *_args, **_kwargs: ({}, summary),
    )
    monkeypatch.setattr(
        app_module,
        "_v940_hydrate_selected_date_results",
        lambda value, _date: value,
    )
    monkeypatch.setattr(app_module, "get_realtime_safe_matches_context", lambda _summary: {})

    def unexpected_reformat(*_args, **_kwargs):
        raise AssertionError("Prepared Calendar cards must reuse their Madrid labels")

    monkeypatch.setitem(app_module.app.jinja_env.globals, "ui_match_datetime", unexpected_reformat)
    monkeypatch.setitem(app_module.app.jinja_env.globals, "ui_match_clock", unexpected_reformat)

    response = client.get("/calendario?lane=week", headers={"Accept-Language": "en"})

    assert response.status_code == 200
    madrid_clock = datetime.fromisoformat(match["kickoff_iso"].replace("Z", "+00:00")).astimezone(
        ZoneInfo("Europe/Madrid")
    ).strftime("%H:%M")
    assert expected_label.endswith(f"· {madrid_clock}")
    assert expected_label.encode("utf-8") in response.data


@pytest.mark.parametrize("kickoff_iso,expected_clock", (
    ("2026-01-15T23:30:00Z", "00:30"),
    ("2026-07-15T23:30:00Z", "01:30"),
    ("2026-03-29T23:30:00Z", "01:30"),
    ("2026-10-25T23:30:00Z", "00:30"),
))
def test_calendar_madrid_label_respects_seasonal_offset(
    app_module, kickoff_iso, expected_clock
):
    # Fixed input instants test display conversion without changing any clock.
    with app_module.app.test_request_context(
        "/calendario?lane=week", headers={"Accept-Language": "en"}
    ):
        label = app_module.ui_match_datetime({"kickoff_iso": kickoff_iso})
    assert label.endswith(f"· {expected_clock}")
