"""Fast-path and lane contract for /match-hub and /resultados."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def match_hub_page():")
    end = source.index("\n\n\n\ndef cached_match_intelligence_for_consumer", start)
    return source[start:end]


def test_match_hub_route_does_not_build_full_dashboard():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route
    assert 'data = {"match_hub": match_hub(date, lane)}' in route


def test_match_hub_template_only_requires_match_hub_payload():
    source = (ROOT / "templates" / "match_hub.html").read_text(encoding="utf-8")
    assert "data.match_hub" in source
    for marker in (
        "data.matches",
        "data.upcoming_matches",
        "data.picks",
        "data.combis",
        "data.smart_picks",
        "data.daily_briefing",
        "data.data_center",
    ):
        assert marker not in source


def test_match_hub_page_passes_requested_lane_and_date(app_module, monkeypatch):
    calls = []

    def fake_hub(date=None, lane="today"):
        calls.append((date, lane))
        return {"date": date, "lane": lane, "counts": {}}

    monkeypatch.setattr(app_module, "match_hub", fake_hub)
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: "2026-10-01" if offset == 1 else "2026-09-30")
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("must not build dashboard")),
    )

    with app_module.app.test_request_context("/match-hub?lane=live&date=2026-09-28"):
        name, ctx = app_module.match_hub_page()

    assert name == "match_hub.html"
    assert calls == [("2026-09-28", "live")]
    assert ctx["data"]["match_hub"]["lane"] == "live"


def test_resultados_alias_defaults_to_results_lane(app_module, monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_module,
        "match_hub",
        lambda date=None, lane="today": calls.append((date, lane)) or {"date": date, "lane": lane},
    )
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: "2026-09-30")
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/resultados"):
        name, ctx = app_module.match_hub_page()

    assert name == "match_hub.html"
    assert calls == [("2026-09-30", "results")]
    assert ctx["data"]["match_hub"]["lane"] == "results"


def test_results_lane_skips_unused_today_and_upcoming_reads(app_module, monkeypatch):
    reads = []
    favorite_reads = []
    result_match = {
        "id": "result-1",
        "match_date": "2026-10-19",
        "home_team": "Local",
        "away_team": "Visitante",
        "status": "FT",
    }
    monkeypatch.setattr(app_module, "cache_get", lambda _key: None)
    monkeypatch.setattr(app_module, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module, "get_favorites", lambda *_args, **_kwargs: favorite_reads.append(True) or [])
    monkeypatch.setattr(app_module, "rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app_module, "get_picks", lambda **_kwargs: [])
    monkeypatch.setattr(app_module, "get_matches", lambda *_args, **_kwargs: reads.append("today") or [])
    monkeypatch.setattr(app_module, "get_upcoming_matches", lambda *_args, **_kwargs: reads.append("upcoming") or [])
    monkeypatch.setattr(app_module, "get_results_matches", lambda *_args, **_kwargs: reads.append("results") or [result_match])
    monkeypatch.setattr(app_module, "v766_enrich_matches_with_highlights", lambda matches: matches)
    monkeypatch.setattr(app_module, "hub_sections", lambda *_args, **_kwargs: {
        key: [] for key in ("today", "live", "upcoming", "finished", "top", "favorites", "with_picks")
    })
    monkeypatch.setattr(app_module, "split_live", lambda _matches: {"live": [], "scheduled": []})
    monkeypatch.setattr(app_module, "sync_plan", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(app_module, "competitions", lambda: [])
    monkeypatch.setattr(app_module, "match_lane_filter", lambda _match, _lane: True)
    monkeypatch.setattr(app_module, "grouped_match_calendar", lambda _matches: [])
    monkeypatch.setattr(app_module, "group_matches_by_league", lambda _matches: [])
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: "2026-10-20")

    with app_module.app.test_request_context("/resultados"):
        hub = app_module.match_hub("2026-10-20", "results")

    assert hub["lane"] == "results"
    assert [item["id"] for item in hub["finished"]] == ["result-1"]
    assert reads == ["results"]
    assert len(favorite_reads) == 1


def test_tomorrow_lane_defaults_to_tomorrow_date(app_module, monkeypatch):
    calls = []

    def fake_today(offset=0):
        return "2026-10-01" if offset == 1 else "2026-09-30"

    monkeypatch.setattr(app_module, "today_iso", fake_today)
    monkeypatch.setattr(
        app_module,
        "match_hub",
        lambda date=None, lane="today": calls.append((date, lane)) or {"date": date, "lane": lane},
    )
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/match-hub?lane=tomorrow"):
        app_module.match_hub_page()

    assert calls == [("2026-10-01", "tomorrow")]


def test_lane_change_changes_match_hub_cache_identity(app_module, monkeypatch):
    # Route-level regression: each requested lane must reach match_hub, whose
    # cache key already includes lane. Do not silently collapse all tabs to today.
    calls = []
    monkeypatch.setattr(
        app_module,
        "match_hub",
        lambda date=None, lane="today": calls.append((date, lane)) or {"date": date, "lane": lane},
    )
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: "2026-09-30")
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    for lane in ("today", "results", "live", "spain", "uefa"):
        with app_module.app.test_request_context(f"/match-hub?lane={lane}"):
            app_module.match_hub_page()

    assert [lane for _date, lane in calls] == ["today", "results", "live", "spain", "uefa"]
