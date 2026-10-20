from __future__ import annotations

import gzip
import json
from datetime import date, timedelta


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
    summary = _calendar_summary(app_module)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *_args, **_kwargs: ({}, summary),
    )

    url = "/api/calendar?lane=week"
    plain = client.get(url, headers={"Accept-Encoding": "identity"})
    compressed = client.get(url, headers={"Accept-Encoding": "gzip"})

    assert plain.status_code == compressed.status_code == 200
    assert "Content-Encoding" not in plain.headers
    assert compressed.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in compressed.headers.get("Vary", "")
    decoded = gzip.decompress(compressed.data)
    assert json.loads(decoded) == plain.get_json()
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
