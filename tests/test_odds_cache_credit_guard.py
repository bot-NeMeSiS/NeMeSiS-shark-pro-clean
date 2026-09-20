from __future__ import annotations

from datetime import datetime, timedelta


def _iso(app_module, delta=timedelta()):
    return (datetime.now(app_module.TZ) + delta).isoformat(timespec="seconds")


def test_odds_cache_guard_reads_current_last_sync_field(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {"ok": True, "last_sync": _iso(app_module)},
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_recently_synced() is True


def test_odds_cache_guard_keeps_legacy_time_compatibility(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {"ok": True, "time": _iso(app_module)},
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_recently_synced() is True


def test_odds_cache_guard_expires_old_sync(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {"ok": True, "last_sync": _iso(app_module, timedelta(hours=-2))},
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)

    assert app_module.odds_recently_synced() is False


def test_cached_odds_sync_makes_zero_provider_calls(app_module, monkeypatch):
    monkeypatch.setenv("THE_ODDS_API_KEY", "qa-placeholder-not-a-real-key")
    monkeypatch.setenv("ENABLE_ODDS_API", "true")
    monkeypatch.setattr(app_module, "seed_core", lambda: None)
    monkeypatch.setattr(app_module, "odds_recently_synced", lambda: True)
    monkeypatch.setattr(
        app_module,
        "odds_last_sync",
        lambda: {
            "ok": True,
            "skipped": False,
            "processed": 7,
            "last_sync": _iso(app_module),
            "external_calls": 14,
            "errors": ["historical provider error"],
        },
    )
    monkeypatch.setattr(app_module, "odds_cache_minutes", lambda: 60)
    monkeypatch.setattr(
        app_module,
        "fetch_odds_events",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("paid provider must not be called while cache is fresh")
        ),
    )

    result = app_module.sync_odds_events(limit=80, force=False)

    assert result["ok"] is True
    assert result["skipped"] is True
    assert result["reason"] == "cache_activa"
    assert result["status"] == "CACHE_REUSED"
    assert result["external_calls"] == 0
    assert result["processed"] == 0
    assert result["errors"] == []
    assert result["cached_processed"] == 7
    assert result["cached_external_calls"] == 14
