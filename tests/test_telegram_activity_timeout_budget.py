"""Regression for Telegram activity worker-timeout budget."""
from pathlib import Path


def test_v771_activity_pick_scan_is_bounded_and_reuses_normalized_rows(app_module, monkeypatch):
    seen = {"limit": None, "normalize_calls": 0, "enrich_flags": []}

    def fake_get_picks(limit=50, **_kwargs):
        seen["limit"] = limit
        return [
            {
                "id": f"p{idx}",
                "match_id": "",
                "home_team": "Local",
                "away_team": "Visitante",
                "market": "Gana local",
                "selection": "Gana local",
                "odds": 1.8,
                "confidence": 80,
                "status": "published",
            }
            for idx in range(limit)
        ]

    original_enrich = app_module.telegram_enrich_pick_for_message

    def tracked_enrich(pick, already_normalized=False):
        seen["enrich_flags"].append(already_normalized)
        return original_enrich(pick, already_normalized=already_normalized)

    monkeypatch.setattr(app_module, "get_picks", fake_get_picks)
    monkeypatch.setattr(app_module, "telegram_enrich_pick_for_message", tracked_enrich)
    monkeypatch.setenv("TELEGRAM_ACTIVITY_PICK_SCAN_LIMIT", "12")

    picks = app_module.v771_telegram_activity_picks()

    assert len(picks) == 12
    assert seen["limit"] == 12
    assert seen["enrich_flags"] == [True] * 12
    assert all(item.get("_telegram_message_enriched") is True for item in picks)


def test_v771_activity_pick_scan_has_hard_max(app_module, monkeypatch):
    captured = {}

    def fake_get_picks(limit=50, **_kwargs):
        captured["limit"] = limit
        return []

    monkeypatch.setattr(app_module, "get_picks", fake_get_picks)
    monkeypatch.setenv("TELEGRAM_ACTIVITY_PICK_SCAN_LIMIT", "999")
    assert app_module.v771_telegram_activity_picks() == []
    assert captured["limit"] == 18


def test_normalize_candidate_reuses_enriched_pick_without_reenriching(app_module, monkeypatch):
    candidate = {
        "_telegram_message_enriched": True,
        "id": "p1",
        "home_team": "Local",
        "away_team": "Visitante",
        "market": "Gana local",
        "selection": "Gana local",
        "odds": 1.8,
        "match_date": "2099-01-01",
        "kickoff_time": "20:00",
        "status": "published",
    }

    monkeypatch.setattr(
        app_module,
        "telegram_enrich_pick_for_message",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("must reuse enriched Telegram pick")),
    )

    normalized = app_module.normalize_telegram_pick_candidate(candidate)
    assert normalized["_telegram_message_enriched"] is True
    assert normalized["selection"] == "Gana local"


def test_telegram_activity_source_keeps_message_limit_separate_from_scan_budget():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    start = source.index("def v771_telegram_activity_picks")
    end = source.index("\n\ndef v771_telegram_activity_highlights", start)
    block = source[start:end]
    assert 'TELEGRAM_ACTIVITY_PICK_SCAN_LIMIT' in block
    assert "min(requested, 18)" in block
    assert "already_normalized=True" in block

    delivery_start = source.index("def telegram_scheduler_delivery")
    delivery_end = source.index("\n\ndef telegram_scheduler_tick", delivery_start)
    delivery = source[delivery_start:delivery_end]
    assert 'TELEGRAM_MAX_ACTIVITY_MESSAGES_PER_TICK' in delivery


def test_v771_activity_matches_avoid_match_hub_and_are_bounded(app_module, monkeypatch):
    calls = {"match_hub": 0, "rows": []}

    monkeypatch.setattr(
        app_module,
        "match_hub",
        lambda *_a, **_kw: calls.__setitem__("match_hub", calls["match_hub"] + 1),
    )

    raw = [
        {
            "id": f"m{idx}",
            "match_date": app_module.today_iso(),
            "kickoff_time": "20:00",
            "competition_name": "Liga QA",
            "home_team": f"Local {idx}",
            "away_team": f"Visitante {idx}",
            "priority": 90,
            "status": "PROGRAMADO",
        }
        for idx in range(40)
    ]

    def fake_rows(query, params=()):
        calls["rows"].append((query, params))
        if "SELECT DISTINCT match_id FROM picks" in query:
            return [{"match_id": "m1"}]
        if "FROM matches" in query:
            return raw[: int(params[-1])]
        return []

    monkeypatch.setattr(app_module, "rows", fake_rows)
    monkeypatch.setattr(app_module, "telegram_enrich_match_for_message", lambda item: dict(item))
    monkeypatch.setenv("TELEGRAM_ACTIVITY_MATCH_SCAN_LIMIT", "24")

    matches = app_module.v771_telegram_activity_matches()

    assert calls["match_hub"] == 0
    assert len(matches) == 24
    assert matches[1]["has_pick"] is True
    match_query, match_params = next((q, p) for q, p in calls["rows"] if "FROM matches" in q)
    assert "match_date>=?" in match_query
    assert "match_date<=?" in match_query
    assert match_params[-1] == 24


def test_v771_activity_match_scan_has_hard_max(app_module, monkeypatch):
    captured = {}

    def fake_rows(query, params=()):
        if "FROM matches" in query:
            captured["limit"] = params[-1]
        return []

    monkeypatch.setattr(app_module, "rows", fake_rows)
    monkeypatch.setenv("TELEGRAM_ACTIVITY_MATCH_SCAN_LIMIT", "999")
    assert app_module.v771_telegram_activity_matches() == []
    assert captured["limit"] == 30


def test_v771_activity_match_source_never_builds_full_match_hub():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    start = source.index("def v771_telegram_activity_matches")
    end = source.index("\n\ndef v771_telegram_activity_picks", start)
    block = source[start:end]
    assert "match_hub(" not in block
    assert "get_results_matches(" not in block
    assert "get_upcoming_matches(" not in block
    assert "TELEGRAM_ACTIVITY_MATCH_SCAN_LIMIT" in block
    assert "min(requested, 30)" in block
