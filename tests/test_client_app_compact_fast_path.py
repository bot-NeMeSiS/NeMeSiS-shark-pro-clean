"""Fast-path contract for the authenticated client app home."""
from pathlib import Path


def _summary():
    return {
        "valid_matches_today": [
            {
                "id": "m1",
                "home_team": "Local QA",
                "away_team": "Visitante QA",
                "competition_name": "Liga QA",
                "match_date": "2026-09-29",
                "kickoff_time": "10:00",
                "source": "TheSportsDB API",
                "status": "PROGRAMADO",
            }
        ],
        "valid_upcoming_matches": [],
        "valid_live_events": [],
        "valid_active_picks": [],
        "valid_matches_available": [],
        "finished_matches": [
            {
                "id": "finished-qa",
                "home_team": "Final QA",
                "away_team": "Visitante QA",
                "competition_name": "Liga QA",
                "match_date": "2026-09-29",
                "kickoff_time": "08:00",
                "source": "TheSportsDB API",
                "status": "FT",
                "home_score": 2,
                "away_score": 1,
                "score": "2-1",
            }
        ],
        "all_valid_matches": [],
        "incomplete_matches": [],
        "provider_status": "qa",
        "last_sync": "2026-09-29T07:00:00+02:00",
        "safe_message": "QA",
        "sports_home": {
            "important_today": [],
            "live_now": [],
            "favorites": [],
            "upcoming": [],
            "recent_results": [
                {
                    "id": "finished-qa",
                    "home_team": "Final QA",
                    "away_team": "Visitante QA",
                    "competition_name": "Liga QA",
                    "match_date": "2026-09-29",
                    "kickoff_time": "08:00",
                    "source": "TheSportsDB API",
                    "status": "FT",
                    "home_score": 2,
                    "away_score": 1,
                    "score": "2-1",
                }
            ],
            "counts": {},
        },
    }


def test_compact_client_home_never_calls_full_dashboard_builder(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("client /app fast path must not call dashboard_data")
        ),
    )
    monkeypatch.setattr(
        app_module,
        "get_v932_real_sports_value_context",
        lambda summary=None: {"real_matches_available": True},
    )
    with app_module.app.test_request_context("/app"):
        data, summary = app_module.v932_safe_dashboard_data(
            "/app",
            compact=True,
            sports_summary=_summary(),
        )

    assert data["v931_route_guard"]["status"] == "compact_read_only_context"
    assert data["v931_route_guard"]["no_render_api_call"] is True
    assert "match_hub" in data
    assert "sports_home" in data["home_summary"]
    assert "v925_picks" in data
    assert "sports_metrics" in data
    assert summary["provider_status"] == "qa"

    home_summary = data["home_summary"]
    assert home_summary["sports_home"]["recent_results"]


def test_client_app_route_selects_compact_context():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    start = source.index("def v757_client_app_center_page():")
    end = source.index("\n\n@app.route(\"/api/client/app-center\")", start)
    route = source[start:end]
    assert "v932_safe_dashboard_data(request.path, compact=True)" in route
    assert "\n    data = dashboard_data(" not in route
    assert "\n    return dashboard_data(" not in route

    assert '"finished": sports_home.get("recent_results") or []' in route
    assert '"sports_home": sports_home' in route


def test_client_home_template_only_depends_on_compact_sports_contract():
    source = (Path(__file__).resolve().parents[1] / "templates" / "client_app_center.html").read_text(encoding="utf-8")
    for marker in (
        "data.get('match_hub')",
        "data.get('available_matches')",
        "data.get('v925_picks')",
        "data.get('sports_metrics')",
        "data.get('v925_calendar')",
    ):
        assert marker in source
