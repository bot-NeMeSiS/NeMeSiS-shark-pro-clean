"""Regression coverage for Render gateway readiness between master-Cron lanes."""

from pathlib import Path

from tools import render_cron_master_tick as master


def test_readiness_guarded_tick_runs_post_only_after_public_gateway_passes(monkeypatch):
    events = []

    def ready(_base_url):
        events.append("ready")
        return {
            "readiness_status": "PASS",
            "readiness_http": 200,
            "readiness_result": "WEB_READY",
            "readiness_attempts": 1,
            "readiness_duration_ms": 10,
        }

    def lane(_base_url, _secret):
        events.append("post")
        return {
            "highlights_status": "PARTIAL",
            "highlights_http": 200,
            "highlights_result": "retry_cooldown",
            "highlights_duration_ms": 5,
        }

    monkeypatch.setattr(master, "wait_for_web_ready", ready)
    result = master.readiness_guarded_tick(
        lane, "highlights", "https://example.invalid", "test"
    )

    assert events == ["ready", "post"]
    assert result["highlights_status"] == "PARTIAL"
    assert result["preflight_readiness"]["readiness_status"] == "PASS"


def test_readiness_guarded_tick_never_posts_when_public_gateway_is_not_ready(monkeypatch):
    calls = []

    monkeypatch.setattr(
        master,
        "wait_for_web_ready",
        lambda _base_url: {
            "readiness_status": "FAIL",
            "readiness_http": 502,
            "readiness_result": "HTTP_502",
            "readiness_attempts": 6,
            "readiness_duration_ms": 25000,
        },
    )

    def lane(_base_url, _secret):
        calls.append("post")
        raise AssertionError("side-effecting lane must not run")

    result = master.readiness_guarded_tick(
        lane, "postmatch", "https://example.invalid", "test"
    )

    assert calls == []
    assert result["postmatch_status"] == "FAIL"
    assert result["postmatch_http"] == 502
    assert result["postmatch_result"] == "HTTP_502"
    assert result["preflight_readiness"]["readiness_status"] == "FAIL"


def test_gateway_error_after_successful_preflight_recovers_readiness_without_replaying_post(monkeypatch):
    readiness_calls = []
    post_calls = []

    def ready(_base_url):
        readiness_calls.append(1)
        return {
            "readiness_status": "PASS",
            "readiness_http": 200,
            "readiness_result": "WEB_READY",
            "readiness_attempts": 1,
            "readiness_duration_ms": 10,
        }

    def lane(_base_url, _secret):
        post_calls.append(1)
        return {
            "highlights_status": "FAIL",
            "highlights_http": 502,
            "highlights_result": "HTTP_502",
            "highlights_duration_ms": 3,
        }

    monkeypatch.setattr(master, "wait_for_web_ready", ready)
    result = master.readiness_guarded_tick(
        lane, "highlights", "https://example.invalid", "test"
    )

    assert post_calls == [1]
    assert len(readiness_calls) == 2
    assert result["highlights_status"] == "FAIL"
    assert result["web_recovery"]["readiness_status"] == "PASS"


def test_master_uses_readiness_guard_for_observed_gateway_sensitive_lanes():
    source = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "render_cron_master_tick.py"
    ).read_text(encoding="utf-8")

    assert 'telegram = readiness_guarded_tick(telegram_tick, "telegram"' in source
    assert 'highlights = readiness_guarded_tick(highlights_tick, "highlights"' in source
    assert 'postmatch = readiness_guarded_tick(postmatch_tick, "postmatch"' in source
