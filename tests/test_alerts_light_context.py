"""Performance contract for /alertas."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _route_source():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index("def alerts_page():")
    end = source.index('\n\n@app.route("/actividad")', start)
    return source[start:end]


def test_alerts_route_never_builds_full_dashboard():
    route = _route_source()
    assert "dashboard_data(" not in route
    assert "v932_safe_dashboard_data(" not in route


def test_alerts_route_loads_only_rendered_personal_context():
    route = _route_source()
    for marker in (
        "build_client_alerts(limit=8, user_id=user_id)",
        "client_activity_feed(limit=8, user_id=user_id)",
        "get_favorites(user_id=user_id)",
        "client_retention_summary(",
        '"date": today_iso()',
        '"session_user": user',
        '"client_alerts": client_alerts',
        '"client_activity": activity',
        '"retention": retention',
    ):
        assert marker in route


def test_alerts_route_drops_unrelated_dashboard_fanout():
    route = _route_source()
    for marker in (
        "get_results_matches(",
        "pick_candidate_matches(",
        "smart_pick_board(",
        "favorite_feed_full(",
        "get_combis(",
        "data_center_summary(",
        "match_calendar_diagnostics(",
        "build_daily_briefing(",
        "client_command_center_data(",
    ):
        assert marker not in route


def test_alerts_route_runtime_context(app_module, monkeypatch):
    user = {"id": "qa-alert-user", "membership": "PRO", "role": "PRO"}
    calls = {"alerts": 0, "activity": 0, "favorites": 0, "retention": 0}

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("must not build dashboard")),
    )

    def fake_alerts(limit=8, user_id=None):
        calls["alerts"] += 1
        assert limit == 8 and user_id == "qa-alert-user"
        return [{"type": "picks", "title": "QA", "href": "/picks"}]

    def fake_activity(limit=8, user_id=None, include_internal=False):
        calls["activity"] += 1
        assert limit == 8 and user_id == "qa-alert-user" and include_internal is False
        return [{"id": "a1", "label": "Actividad QA"}]

    def fake_favorites(user_id=None):
        calls["favorites"] += 1
        assert user_id == "qa-alert-user"
        return [{"kind": "team", "value": "QA"}]

    def fake_retention(user=None, alerts=None, activity=None, favorites=None, telegram=None):
        calls["retention"] += 1
        assert user["id"] == "qa-alert-user"
        assert alerts and activity and favorites
        return {"next_best_action": alerts[0]}

    monkeypatch.setattr(app_module, "build_client_alerts", fake_alerts)
    monkeypatch.setattr(app_module, "client_activity_feed", fake_activity)
    monkeypatch.setattr(app_module, "get_favorites", fake_favorites)
    monkeypatch.setattr(app_module, "client_retention_summary", fake_retention)
    monkeypatch.setattr(app_module, "today_iso", lambda *args: "2026-09-30")
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/alertas"):
        name, ctx = app_module.alerts_page()

    assert name == "alerts.html"
    assert ctx["data"]["date"] == "2026-09-30"
    assert ctx["data"]["session_user"]["id"] == "qa-alert-user"
    assert ctx["data"]["client_alerts"][0]["title"] == "QA"
    assert ctx["data"]["client_activity"][0]["id"] == "a1"
    assert ctx["data"]["retention"]["next_best_action"]["href"] == "/picks"
    assert calls == {"alerts": 1, "activity": 1, "favorites": 1, "retention": 1}


def test_alert_builder_uses_validated_shared_snapshot_for_live_and_picks(app_module, monkeypatch):
    user = {"id": "qa-alert-user", "membership": "ELITE", "role": "ELITE"}
    summary = {
        "valid_live_events": [{"id": "live-1"}, {"id": "live-2"}],
        "valid_active_picks": [{"id": "current-pick", "match_id": "upcoming-1"}],
        "valid_upcoming_matches": [
            {"id": "upcoming-1", "home_team": "Granada", "away_team": "Almeria", "competition_name": "Liga"},
        ],
    }
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)
    monkeypatch.setattr(
        app_module,
        "_current_client_picks",
        lambda actual_user, actual_summary: (
            summary["valid_active_picks"] if actual_user == user and actual_summary is summary else []
        ),
    )
    monkeypatch.setattr(app_module, "match_hub", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("legacy match hub used")))
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("unvalidated published picks used")))
    monkeypatch.setattr(app_module, "get_upcoming_matches", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("legacy upcoming matches used")))
    monkeypatch.setattr(app_module, "get_favorites", lambda **_k: [])
    monkeypatch.setattr(app_module, "telegram_config", lambda: {"configured": True})

    with app_module.app.test_request_context("/alertas"):
        alerts = app_module.build_client_alerts(user_id=user["id"])

    live_alert = next(item for item in alerts if item["type"] == "live")
    pick_alert = next(item for item in alerts if item["type"] == "picks")
    assert live_alert["body"].startswith("Hay 2 partidos en directo.")
    assert pick_alert["body"] == "Pronósticos visibles según tu plan: 1."

    monkeypatch.setattr(app_module, "_current_client_picks", lambda *_a, **_k: [])
    with app_module.app.test_request_context("/alertas"):
        no_pick_alerts = app_module.build_client_alerts(user_id=user["id"])
    analysis_alert = next(item for item in no_pick_alerts if item["type"] == "analysis")
    assert "no hay pronósticos SHARK vigentes" in analysis_alert["body"]
    assert "SHARK ya puede ayudarte" not in analysis_alert["body"]


def test_retention_counts_use_the_same_validated_snapshot(app_module, monkeypatch):
    user = {"id": "qa-alert-user", "membership": "ELITE", "role": "ELITE"}
    summary = {
        "valid_upcoming_matches": [{"id": "upcoming-1"}, {"id": "upcoming-2"}],
        "valid_active_picks": [{"id": "current-pick", "match_id": "upcoming-1"}],
    }
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", lambda: summary)
    monkeypatch.setattr(
        app_module,
        "_current_client_picks",
        lambda actual_user, actual_summary: (
            summary["valid_active_picks"] if actual_user == user and actual_summary is summary else []
        ),
    )
    monkeypatch.setattr(app_module, "get_upcoming_matches", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("legacy upcoming count used")))
    monkeypatch.setattr(app_module, "published_picks_for_user", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("legacy pick count used")))

    result = app_module.client_retention_summary(
        user=user,
        alerts=[{"type": "picks", "href": "/picks"}],
        activity=[],
        favorites=[],
        telegram={"configured": True},
    )

    assert result["upcoming_count"] == 2
    assert result["picks_count"] == 1


def test_alerts_route_redirects_without_session(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "current_session_user", lambda: None)
    with app_module.app.test_request_context("/alertas"):
        response = app_module.alerts_page()
    assert response.status_code == 302
    assert response.location.endswith("/cliente-login")


def test_alerts_template_matches_light_payload():
    source = (ROOT / "templates" / "alerts.html").read_text(encoding="utf-8")
    for marker in (
        "data.date",
        "data.client_alerts",
        "data.retention.next_best_action",
        "data.client_activity",
    ):
        assert marker in source
    for marker in (
        "data.matches",
        "data.upcoming_matches",
        "data.picks",
        "data.combis",
        "data.match_hub",
        "data.past_results",
        "data.smart_picks",
        "data.daily_briefing",
        "data.data_center",
    ):
        assert marker not in source
