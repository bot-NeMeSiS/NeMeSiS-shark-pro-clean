def test_admin_realtime_status_reports_cached_live_statistics_without_provider_calls(app_module, monkeypatch):
    snapshot = {
        "live": [
            {"id": "af-101", "home_team": "Local", "away_team": "A"},
            {"id": "af-202", "home_team": "B", "away_team": "C"},
            {"id": "af-303", "home_team": "D", "away_team": "E"},
        ],
        "counts": {"matches": 3, "live": 3},
        "matches": [],
        "picks": [],
        "cache_status": "available",
        "cache_state": "HIT",
        "provider_status": "data_available",
        "odds_freshness_status": "recorded_or_stale",
        "last_safe_sync": "2026-10-18T10:00:00+02:00",
        "poll_after_seconds": 45,
    }
    monkeypatch.setattr(app_module, "get_v934_realtime_context", lambda summary=None: snapshot)
    monkeypatch.setattr(app_module, "get_api_sports_status", lambda _db: {"api_sports_configured": True})

    def cached_summaries(_db, matches, limit=40):
        assert len(matches) == 3
        assert limit == 40
        return {
            "101": {"stats": {"available": True}, "external_calls": 0, "read_only": True},
            "af-202": {"stats": {"available": False}, "external_calls": 0, "read_only": True},
        }

    monkeypatch.setattr(app_module, "live_tracker_summaries_for_matches", cached_summaries)
    monkeypatch.setattr(app_module, "v934_realtime_cache_status", lambda: {"entries": 1})

    result = app_module.v934_admin_realtime_status()

    assert result["live_stats_observed"] == 1
    assert result["live_stats_total"] == 3
    assert result["live_stats_external_calls"] == 0
    assert result["live_stats_read_only"] is True


def test_admin_realtime_center_discloses_live_stats_cache_coverage():
    from pathlib import Path

    template = Path(__file__).resolve().parents[1] / "templates" / "admin_realtime_center.html"
    source = template.read_text(encoding="utf-8")
    assert "Estadísticas de directos" in source
    assert "Muestra de hasta 40 partidos" in source
    assert "guardadas" in source
    assert "live_stats_external_calls" in source
