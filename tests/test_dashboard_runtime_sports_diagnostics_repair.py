from __future__ import annotations

import copy
import json

from flask import session

from engines import picks_quality_engine as quality


def _pick(index: int, **overrides):
    item = {
        "id": f"qa-pick-{index}",
        "match_id": f"qa-match-{index}",
        "home_team": "Ñublense CF",
        "away_team": "PSG",
        "competition_name": "UEFA Champions League",
        "league_name": "UEFA Champions League",
        "market": "Match Winner",
        "pick_type": "Match Winner",
        "selection": "Ñublense CF",
        "odds": "1.90",
        "confidence": 78,
        "stake_units": 1,
        "risk_level": "MEDIO",
        "status": "published",
        "membership_required": "FREE",
        "kickoff_iso": "2035-09-07T19:00:00+00:00",
        "published_at": "2035-09-06T10:00:00+00:00",
        "reasoning": "Evidencia QA aislada.",
    }
    item.update(overrides)
    return item


def test_quality_enrichment_scores_once_and_preserves_unicode(monkeypatch):
    calls = 0
    original = quality.pick_quality_score

    def counted(item):
        nonlocal calls
        calls += 1
        return original(item)

    monkeypatch.setattr(quality, "pick_quality_score", counted)

    result = quality.enrich_pick_quality(_pick(1))

    assert calls == 1
    assert result["id"] == "qa-pick-1"
    assert "Ñublense" in result["selection"]
    assert result["away_team"] == "PSG"
    assert result["quality_bucket"] in {"top", "premium", "value", "study"}
    assert result["premium_ready"] == quality.pick_is_premium_ready(
        result,
        quality_score=result["quality_score"],
    )


def test_enriched_sort_and_split_never_reenrich(monkeypatch):
    enriched = [
        {
            "id": "study",
            "quality_score": 99,
            "quality_bucket": "study",
            "premium_ready": False,
            "stale_pick": True,
            "low_relevance_competition": False,
            "competition_priority": 14,
            "odds": 2.1,
            "confidence": 99,
        },
        {
            "id": "ready",
            "quality_score": 78,
            "quality_bucket": "premium",
            "premium_ready": True,
            "stale_pick": False,
            "low_relevance_competition": False,
            "competition_priority": 14,
            "odds": 1.9,
            "confidence": 78,
        },
    ]
    monkeypatch.setattr(
        quality,
        "enrich_pick_quality",
        lambda _item: (_ for _ in ()).throw(
            AssertionError("Already-enriched picks must not be enriched again")
        ),
    )

    ordered = quality.sort_enriched_picks_by_quality(enriched)
    split = quality.split_enriched_picks_by_quality(enriched)

    assert [item["id"] for item in ordered] == ["ready", "study"]
    assert [item["id"] for item in split["ready"]] == ["ready"]
    assert [item["id"] for item in split["study"]] == ["study"]


def test_get_picks_is_equivalent_and_reuses_work_only_inside_request(
    app_module,
    monkeypatch,
):
    raw = [
        _pick(index)
        for index in range(120)
    ] + [
        _pick(
            121,
            selection="Pendiente",
            market="",
            pick_type="",
            odds="",
        ),
        _pick(
            122,
            kickoff_iso="2020-01-01T20:00:00+00:00",
            published_at="2020-01-01T10:00:00+00:00",
        ),
        _pick(123, status="finished"),
    ]
    expected = quality.sort_picks_by_quality(
        [app_module.normalize_pick_row(copy.deepcopy(item)) for item in raw]
    )
    query_calls = []
    normalize_calls = 0
    original_normalize = app_module.normalize_pick_row
    madrid_day = ["2026-09-06"]

    def fake_rows(query, params=()):
        query_calls.append((query, tuple(params)))
        return copy.deepcopy(raw)

    def counted_normalize(item):
        nonlocal normalize_calls
        normalize_calls += 1
        return original_normalize(item)

    monkeypatch.setattr(app_module, "rows", fake_rows)
    monkeypatch.setattr(app_module, "normalize_pick_row", counted_normalize)
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: madrid_day[0])

    with app_module.app.test_request_context("/app"):
        session.update(
            {
                "user_id": "qa-user-a",
                "user_role": "PRO",
                "user_membership": "PRO",
                "membership": "PRO",
            }
        )
        first = app_module.get_picks(limit=500)
        first[0]["selection"] = "mutated consumer copy"
        second = app_module.get_picks(limit=500)

        assert second == expected
        assert normalize_calls == len(raw)
        assert len(query_calls) == 1
        assert second[0]["selection"] != "mutated consumer copy"

        madrid_day[0] = "2026-09-07"
        third = app_module.get_picks(limit=500)
        assert third == expected
        assert normalize_calls == len(raw) * 2
        assert len(query_calls) == 2

    with app_module.app.test_request_context("/app"):
        session.update(
            {
                "user_id": "qa-user-b",
                "user_role": "PRO",
                "user_membership": "PRO",
                "membership": "PRO",
            }
        )
        assert app_module.get_picks(limit=500) == expected

    assert normalize_calls == len(raw) * 3
    assert len(query_calls) == 3


def test_pick_plan_filters_cover_current_contract_and_admin_isolation(
    app_module,
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        app_module,
        "rows",
        lambda query, params=(): calls.append((query, tuple(params))) or [],
    )
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: "2026-09-06")

    cases = {
        "FREE": ("FREE", 10),
        "PRO": ("FREE", "PRO", 10),
        "ELITE": ("FREE", "PRO", "ELITE", 10),
    }
    for index, (plan, expected_params) in enumerate(cases.items()):
        with app_module.app.test_request_context("/app"):
            session.update(
                {
                    "user_id": f"qa-tier-{index}",
                    "user_role": plan,
                    "user_membership": plan,
                    "membership": plan,
                }
            )
            app_module.get_picks(limit=10, membership=plan)
        assert calls[-1][1] == expected_params

    with app_module.app.test_request_context("/admin"):
        session.update(
            {
                "user_id": "qa-admin",
                "user_role": "ADMIN",
                "user_membership": "ADMIN",
                "membership": "ADMIN",
            }
        )
        app_module.get_picks(
            limit=10,
            membership="ADMIN",
            include_admin=True,
        )
    assert calls[-1][1] == (10,)
    assert "membership_required" not in calls[-1][0]
    assert app_module.VALID_ROLES == {"FREE", "PRO", "ELITE", "ADMIN"}


def test_same_plan_users_and_admin_never_share_session_cache(
    app_module,
    monkeypatch,
):
    expiry_calls = []
    monkeypatch.setattr(
        app_module,
        "expire_user_memberships_if_needed",
        lambda user_id: expiry_calls.append(user_id),
    )
    monkeypatch.setattr(app_module, "get_user_by_id", lambda _user_id: None)

    def read_user(user_id, name, role="PRO"):
        with app_module.app.test_request_context("/app"):
            session.update(
                {
                    "user_id": user_id,
                    "user_name": name,
                    "username": user_id,
                    "user_email": f"{user_id}@example.invalid",
                    "user_role": role,
                    "user_membership": role,
                    "membership": role,
                }
            )
            first = app_module.current_session_user()
            first["name"] = "mutated consumer copy"
            second = app_module.current_session_user()
            return second

    user_a = read_user("qa-same-plan-a", "Usuario A")
    user_b = read_user("qa-same-plan-b", "Usuario B")
    admin = read_user("qa-admin", "Administración", role="ADMIN")

    assert user_a["id"] == "qa-same-plan-a"
    assert user_a["name"] == "Usuario A"
    assert user_b["id"] == "qa-same-plan-b"
    assert user_b["name"] == "Usuario B"
    assert admin["id"] == "qa-admin"
    assert admin["role"] == "ADMIN"
    assert expiry_calls == ["qa-same-plan-a", "qa-same-plan-b"]


def test_dashboard_composition_reuses_expensive_personal_context(
    app_module,
    monkeypatch,
):
    calls = {
        "user": 0,
        "smart": 0,
        "briefing": 0,
        "command": 0,
        "favorite_insights": 0,
    }
    user = {"id": "qa-user", "role": "PRO", "membership": "PRO"}
    hub = {"today": [], "live": [], "counts": {"live": 0}}
    briefing = {
        "counts": {
            "today": 0,
            "upcoming": 0,
            "live": 0,
            "favorites": 0,
            "picks": 0,
        },
        "picks": [],
    }

    def count(name, value):
        def callback(*_args, **_kwargs):
            calls[name] += 1
            return value

        return callback

    simple_stubs = {
        "ensure_client_match_lifecycle_fresh": {},
        "get_matches": [],
        "get_upcoming_matches": [],
        "competitions": [],
        "rows": [],
        "get_picks": [],
        "get_combis": [],
        "default_profile": {},
        "get_favorites": [],
        "match_hub": hub,
        "get_results_matches": [],
        "pick_candidate_matches": [],
        "favorite_feed_full": {
            "matches": [],
            "live": [],
            "picks": [],
            "priority": [],
        },
        "build_client_alerts": [],
        "client_activity_feed": [],
        "telegram_config": {"configured": False},
        "client_retention_summary": {},
        "build_live_flow": {},
        "match_calendar_diagnostics": {},
        "crest_sync_status": {},
        "sportsdb_feed_status": {},
        "odds_diagnostics": {},
        "data_center_summary": {},
        "split_live": {"live": [], "scheduled": [], "finished": []},
    }
    for name, value in simple_stubs.items():
        monkeypatch.setattr(app_module, name, lambda *_args, _value=value, **_kwargs: _value)
    monkeypatch.setattr(app_module, "current_session_user", count("user", user))
    monkeypatch.setattr(app_module, "smart_pick_board", count("smart", {"published": []}))
    monkeypatch.setattr(
        app_module,
        "favorite_insights",
        count("favorite_insights", {"total": 0}),
    )
    monkeypatch.setattr(app_module, "build_daily_briefing", count("briefing", briefing))

    def command_callback(_user=None, briefing=None):
        calls["command"] += 1
        assert briefing is not None
        return {"briefing": briefing}

    monkeypatch.setattr(app_module, "client_command_center_data", command_callback)
    monkeypatch.setattr(app_module, "enrich_pick_client_context", lambda item: item)
    monkeypatch.setattr(app_module, "annotate_match", lambda item: item)
    monkeypatch.setattr(app_module, "today_iso", lambda offset=0: "2026-09-06")

    result = app_module.dashboard_data()

    assert calls == {
        "user": 1,
        "smart": 1,
        "briefing": 1,
        "command": 1,
        "favorite_insights": 1,
    }
    assert result["session_user"] == user
    assert result["daily_briefing"] is briefing
    assert result["client_command"]["briefing"] is briefing


def _historical_pipeline_sample():
    return {
        "latest_account": {
            "ok": True,
            "configured": True,
            "plan": "Free",
            "quota": {
                "daily_limit": 100,
                "daily_used": 7,
                "daily_remaining": 93,
            },
        },
        "latest_run": {
            "status": "PARTIAL",
            "finished_at": "2026-09-05T22:05:25+00:00",
            "external_calls": 1,
            "payload_json": json.dumps(
                {
                    "selected_fixture_ids": ["9001"],
                    "capabilities": {
                        "account": {
                            "requested": True,
                            "http_status": 200,
                        }
                    },
                }
            ),
        },
        "continuity": [
            {
                "capability": "fixtures",
                "requested": True,
                "received": 0,
                "persisted": 5,
            },
            {
                "capability": "lineups",
                "requested": False,
                "received": 0,
                "persisted": 2,
            },
        ],
    }


def test_pipeline_diagnostics_marks_historical_quota_and_store_totals(
    app_module,
):
    pipeline = app_module._build_sports_pipeline_diagnostics(
        {
            "ok": True,
            "status": "PARTIAL",
            "deep_status": "SKIPPED_NOT_DUE",
            "deep_external_calls": 0,
            "external_calls": 0,
            "processed": 0,
            "started_at": "2026-09-06T08:15:45+00:00",
            "finished_at": "2026-09-06T08:15:48+00:00",
            "trigger_type": "shared_telegram_cron",
            "deep_enrichment": {"status": "SKIPPED_NOT_DUE"},
        },
        _historical_pipeline_sample(),
    )

    assert pipeline["provider_authenticated"] is True
    assert pipeline["provider_plan"] == "Free"
    assert pipeline["deep_execution"]["state"] == "NOT_DUE"
    assert pipeline["provider_access"] == {
        "provider": "API-Football",
        "state": "AUTHENTICATED",
        "configured": True,
        "authenticated": True,
        "checked_at": "2026-09-05T22:05:25+00:00",
        "source": "LAST_PERSISTED_DEEP_SAMPLE",
    }
    assert pipeline["quota_observation"]["state"] == "OBSERVED"
    assert pipeline["quota_observation"]["freshness"] == "LAST_OBSERVED_NOT_CURRENT"
    assert pipeline["quota_observation"]["observed_at"] == "2026-09-05T22:05:25+00:00"
    fixtures = pipeline["coverage"]["capabilities"]["fixtures"]
    assert fixtures["state"] == "LAST_OBSERVED"
    assert fixtures["received"] == 0
    assert fixtures["persisted"] == 5
    assert fixtures["received_scope"] == "LAST_PERSISTED_DEEP_SAMPLE_RESPONSE"
    assert fixtures["persisted_scope"] == "STORE_TOTAL"
    assert pipeline["last_sample"]["is_current_job"] is False
    assert pipeline["last_sample"]["freshness_state"] == "HISTORICAL_SAMPLE_AGE_UNASSESSED"
    assert pipeline["data_freshness"]["state"] == "NOT_ESTABLISHED"
    assert pipeline["data_freshness"]["entity_timestamps_evaluated"] is False


def test_pipeline_diagnostics_distinguishes_not_checked_from_access_failure(
    app_module,
):
    not_checked = app_module._build_sports_pipeline_diagnostics(
        {
            "status": "PARTIAL",
            "deep_status": "ERROR",
            "deep_enrichment": {
                "status": "ERROR",
                "account": {
                    "ok": False,
                    "configured": False,
                    "plan": "INACCESSIBLE",
                    "quota": {},
                },
                "capabilities": {
                    "lineups": {
                        "requested": False,
                        "reason": "missing_canonical_identity",
                        "persisted": 0,
                    }
                },
            },
        }
    )
    failed = app_module._build_sports_pipeline_diagnostics(
        {
            "status": "PROVIDER_UNAVAILABLE",
            "deep_status": "ERROR",
            "deep_enrichment": {
                "status": "ERROR",
                "finished_at": "2026-09-06T08:20:00+00:00",
                "account": {
                    "ok": False,
                    "configured": True,
                    "plan": "INACCESSIBLE",
                    "quota": {},
                    "http_status": 401,
                    "error": "unauthorized",
                },
                "capabilities": {
                    "account": {
                        "ok": False,
                        "http_status": 401,
                    }
                },
            },
        }
    )

    assert not_checked["provider_access"]["state"] == "NOT_CHECKED"
    assert not_checked["provider_access"]["authenticated"] is None
    assert not_checked["provider_plan_observation"]["state"] == "UNKNOWN"
    assert not_checked["quota_observation"]["state"] == "UNKNOWN"
    assert (
        not_checked["coverage"]["capabilities"]["lineups"]["state"]
        == "NOT_AVAILABLE_FOR_CONTEXT"
    )
    assert failed["provider_access"]["state"] == "ACCESS_FAILED"
    assert failed["provider_access"]["authenticated"] is False
    assert failed["provider_access"]["checked_at"] == "2026-09-06T08:20:00+00:00"


def test_pipeline_diagnostics_current_empty_response_is_not_network_failure(
    app_module,
):
    pipeline = app_module._build_sports_pipeline_diagnostics(
        {
            "ok": True,
            "status": "OK",
            "deep_status": "OK",
            "deep_external_calls": 2,
            "external_calls": 3,
            "processed": 1,
            "started_at": "2026-09-06T08:20:00+00:00",
            "finished_at": "2026-09-06T08:20:05+00:00",
            "trigger_type": "shared_telegram_cron",
            "deep_enrichment": {
                "status": "OK",
                "finished_at": "2026-09-06T08:20:04+00:00",
                "external_calls": 2,
                "selected_fixture_ids": ["9002"],
                "account": {
                    "ok": True,
                    "configured": True,
                    "plan": "Free",
                    "quota": {
                        "daily_limit": 100,
                        "daily_remaining": 90,
                    },
                },
                "capabilities": {
                    "account": {
                        "requested": True,
                        "http_status": 200,
                    },
                    "lineups": {
                        "requested": True,
                        "received": 0,
                        "persisted": 0,
                    },
                    "events": {
                        "requested": True,
                        "received": 3,
                        "persisted": 2,
                    },
                },
            },
        }
    )

    assert pipeline["job_execution"]["state"] == "OK"
    assert pipeline["job_execution"]["ok"] is True
    assert pipeline["provider_access"]["state"] == "AUTHENTICATED"
    assert pipeline["quota_observation"]["freshness"] == "CURRENT_DEEP_RUN"
    assert pipeline["coverage"]["source"] == "CURRENT_DEEP_RUN"
    assert pipeline["coverage"]["capabilities"]["lineups"]["state"] == "EMPTY_RESPONSE"
    assert pipeline["coverage"]["capabilities"]["lineups"]["persisted_scope"] == "CURRENT_DEEP_RUN_WRITES"
    assert pipeline["coverage"]["capabilities"]["events"]["state"] == "RECEIVED"
    assert pipeline["last_sample"]["is_current_job"] is True
    assert pipeline["last_sample"]["fixture_ids"] == ["9002"]


def test_compact_pipeline_keeps_new_contract_and_masks_known_secret(
    app_module,
    monkeypatch,
):
    secret = "pytest-diagnostics-sensitive-secret"
    monkeypatch.setenv("AUTOMATION_SECRET", secret)
    pipeline = app_module._build_sports_pipeline_diagnostics(
        {
            "ok": True,
            "status": "OK",
            "deep_status": "OK",
            "deep_external_calls": 1,
            "deep_enrichment": {
                "status": "OK",
                "finished_at": "2026-09-06T08:20:04+00:00",
                "account": {
                    "ok": True,
                    "configured": True,
                    "plan": secret,
                    "quota": {"daily_remaining": 90},
                },
                "capabilities": {
                    "account": {"requested": True, "http_status": 200},
                    "lineups": {
                        "requested": False,
                        "reason": secret,
                        "persisted": 0,
                    },
                },
            },
        }
    )

    compact = app_module._cron_compact_payload(
        "telegram_tick",
        {"ok": True, "status": "PASS", "sports_pipeline": pipeline},
        "2026-09-06T08:20:00+00:00",
        "2026-09-06T08:20:05+00:00",
    )
    serialized = json.dumps(compact, ensure_ascii=False)

    assert compact["sports_pipeline"]["provider_access"]["state"] == "AUTHENTICATED"
    assert compact["sports_pipeline"]["data_freshness"]["state"] == "NOT_ESTABLISHED"
    assert (
        compact["sports_pipeline"]["coverage"]["capabilities"]["lineups"][
            "persisted_scope"
        ]
        == "CURRENT_DEEP_RUN_WRITES"
    )
    assert secret not in serialized
