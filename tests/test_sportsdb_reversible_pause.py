"""TheSportsDB reversible pause must block all outgoing provider lanes."""
from __future__ import annotations

from engines.sportsdb_pause_engine import sportsdb_effective_key, sportsdb_paused


def test_sportsdb_pause_preserves_credentials(monkeypatch):
    monkeypatch.setenv("THESPORTSDB_KEY", "keep-this-key")
    monkeypatch.setenv("THESPORTSDB_PAUSED", "true")
    assert sportsdb_paused() is True
    assert sportsdb_effective_key() == ""
    assert monkeypatch is not None
    monkeypatch.setenv("THESPORTSDB_PAUSED", "false")
    assert sportsdb_paused() is False
    assert sportsdb_effective_key() == "keep-this-key"


def test_paused_sportsdb_engines_do_not_use_network(monkeypatch, tmp_path):
    monkeypatch.setenv("THESPORTSDB_KEY", "keep-this-key")
    monkeypatch.setenv("THESPORTSDB_PAUSED", "true")
    def fail_if_called(*args, **kwargs):
        raise AssertionError("SportsDB network access during pause")
    monkeypatch.setattr("urllib.request.urlopen", fail_if_called)
    from engines.sportsdb_highlights_engine import sync_sportsdb_highlights
    from engines.sportsdb_broadcast_engine import sync_upcoming_broadcasts
    from engines.sportsdb_enrichment_engine import _api_key as enrichment_key
    from sportsdb_highlights_engine import _api_key as legacy_highlight_key
    assert enrichment_key() == ""
    assert legacy_highlight_key() == ""
    highlights = sync_sportsdb_highlights(str(tmp_path / "no-highlights.db"))
    assert highlights["status"] == "PAUSED"
    assert highlights["external_calls"] == 0
    broadcasts = sync_upcoming_broadcasts(str(tmp_path / "no-broadcasts.db"))
    assert broadcasts["reason"] == "SPORTSDB_PAUSED"
    assert broadcasts["external_calls"] == 0


def test_paused_inventory_keeps_football_primary(monkeypatch):
    monkeypatch.setenv("THESPORTSDB_KEY", "keep-this-key")
    monkeypatch.setenv("THESPORTSDB_PAUSED", "true")
    monkeypatch.setenv("PRIMARY_FOOTBALL_DATA_PROVIDER", "thesportsdb")
    from engines.data_provider_engine import primary_provider, provider_order, provider_status
    assert primary_provider() == "api_football"
    assert provider_order()[0] == "api_football"
    assert "thesportsdb" not in provider_order()
    provider = provider_status("thesportsdb")
    assert provider["configured"] is True
    assert provider["enabled"] is False
    assert provider["paused"] is True


def test_paused_media_cron_never_requests_external_service(monkeypatch):
    monkeypatch.setenv("THESPORTSDB_PAUSED", "true")
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Cron requested network during pause")
    monkeypatch.setattr("urllib.request.urlopen", fail_if_called)
    from tools.render_cron_master_tick import highlights_tick
    result = highlights_tick("https://unused.invalid", "not-a-real-secret")
    assert result["highlights_status"] == "PASS"
    assert result["highlights_result"] == "provider_paused"
    assert result["external_calls"] == 0
