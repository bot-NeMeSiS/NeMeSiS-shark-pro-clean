"""Regression coverage for the remaining high-value client fast paths.

These tests protect navigation speed without changing sports truth: GET screens
must not rebuild the legacy dashboard fan-out when their templates only need a
bounded read-only context.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _app_source():
    return (ROOT / "app.py").read_text(encoding="utf-8")


def _between(start_marker, end_marker):
    source = _app_source()
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[start:end]


def test_favorites_uses_compact_snapshot_and_explicit_personal_context():
    route = _between("def favorites_page():", "# ===================== V785")
    assert 'v932_safe_dashboard_data(request.path, scope="client", compact=True)' in route
    assert "data = dashboard_data(" not in route
    for marker in (
        'get_favorites(user_id=user_id)',
        'favorite_feed_full(limit=80, user_id=user_id)',
        'favorite_insights(',
        'data["favorites"] = favorites',
        'data["favorite_feed"] = list(favorite_bundle.get("matches") or [])',
        'data["favorite_bundle"] = favorite_bundle',
        'data["favorite_insights"] = favorite_insights(',
        '"favorites_list"',
        '"favorites_bundle"',
    ):
        assert marker in route


def test_home_does_not_build_unused_legacy_presentation_contexts():
    route = _between(
        "def v757_client_app_center_page():",
        '@app.route("/api/client/app-center")',
    )
    assert "v932_safe_dashboard_data(request.path, compact=True)" in route
    for marker in (
        "v742_track_record_context",
        "build_client_app_premium_context",
        "build_v757_app_center",
        "build_v757_trust_snapshot",
        "v758_adaptive_context",
        "v777_client_product_context",
        "v778_client_product_organization_context",
        "get_v934_realtime_context",
        "get_v935_customer_trust_context",
    ):
        assert marker not in route


def test_daily_briefing_builds_only_the_context_rendered_by_the_template():
    route = _between("def daily_briefing_page():", "def membership_page():")
    assert "dashboard_data(" not in route
    assert "client_command_center_data(" not in route
    assert '"briefing": build_daily_briefing(user)' in route
    assert '"session_user": user' in route


def test_favorites_runtime_preserves_template_contract_without_full_dashboard(app_module, monkeypatch):
    user = {"id": "qa-fast-favorites", "membership": "PRO", "role": "PRO"}
    calls = {"safe": 0, "favorites": 0, "bundle": 0, "insights": 0}

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("favorites must not build the full dashboard")
        ),
    )

    def fake_safe(route, lane="today", date_value=None, scope="client", compact=False, sports_summary=None):
        calls["safe"] += 1
        assert route == "/favoritos"
        assert scope == "client"
        assert compact is True
        return ({"session_user": user, "matches": [], "picks": []}, {"provider_status": "ok"})

    def fake_favorites(kind=None, user_id=None):
        calls["favorites"] += 1
        assert kind is None
        assert user_id == user["id"]
        return [{"kind": "team", "value": "QA FC", "label": "QA FC"}]

    bundle = {
        "matches": [{"id": "m1", "home_team": "QA FC", "away_team": "Test FC"}],
        "live": [],
        "picks": [{"id": "p1", "selection": "QA"}],
        "priority": [],
    }

    def fake_bundle(limit=80, user_id=None):
        calls["bundle"] += 1
        assert limit == 80
        assert user_id == user["id"]
        return bundle

    def fake_insights(user_id=None, favorites=None, bundle=None):
        calls["insights"] += 1
        assert user_id == user["id"]
        assert favorites and favorites[0]["value"] == "QA FC"
        assert bundle is not None and bundle["matches"][0]["id"] == "m1"
        return {
            "favorites": favorites,
            "by_kind": {"team": favorites, "league": [], "match": []},
            "matches": bundle["matches"],
            "live": [],
            "picks": bundle["picks"],
            "summary": "1 equipos seguidos",
            "total": 1,
        }

    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", fake_safe)
    monkeypatch.setattr(app_module, "get_favorites", fake_favorites)
    monkeypatch.setattr(app_module, "favorite_feed_full", fake_bundle)
    monkeypatch.setattr(app_module, "favorite_insights", fake_insights)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/favoritos"):
        name, ctx = app_module.favorites_page()

    data = ctx["data"]
    assert name == "favorites.html"
    assert data["favorites"][0]["value"] == "QA FC"
    assert data["favorite_feed"][0]["id"] == "m1"
    assert data["favorite_bundle"]["picks"][0]["id"] == "p1"
    assert data["favorite_insights"]["total"] == 1
    assert calls == {"safe": 1, "favorites": 1, "bundle": 1, "insights": 1}


def test_home_runtime_skips_all_dead_builders(app_module, monkeypatch):
    user = {"id": "qa-fast-home", "membership": "FREE", "role": "FREE"}

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "v932_safe_dashboard_data",
        lambda *_a, **_kw: (
            {"picks": [], "matches": [], "upcoming_matches": [], "match_hub": {}},
            {"provider_status": "ok", "valid_active_picks": []},
        ),
    )
    monkeypatch.setattr(app_module, "v566_membership_ui", lambda _user: {"name": "FREE"})
    monkeypatch.setattr(app_module, "_v931_provider_context", lambda _summary: {"provider_status": "ok"})
    monkeypatch.setattr(app_module, "get_safe_picks_context", lambda picks: {"picks": list(picks)})
    monkeypatch.setattr(app_module, "get_safe_odds_context", lambda picks: {"picks": list(picks)})
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    forbidden = (
        "v742_track_record_context",
        "build_client_app_premium_context",
        "build_v757_app_center",
        "build_v757_trust_snapshot",
        "v758_adaptive_context",
        "v777_client_product_context",
        "v778_client_product_organization_context",
        "get_v934_realtime_context",
        "get_v935_customer_trust_context",
    )
    for name in forbidden:
        monkeypatch.setattr(
            app_module,
            name,
            lambda *_a, _name=name, **_kw: (_ for _ in ()).throw(
                AssertionError(f"dead builder called: {_name}")
            ),
        )

    with app_module.app.test_request_context("/app"):
        name, ctx = app_module.v757_client_app_center_page()

    assert name == "client_app_center.html"
    assert ctx["data"]["membership"]["name"] == "FREE"
    for key in (
        "track_record",
        "client_premium",
        "v757_app",
        "v757_trust",
        "v758_adaptive",
        "v777_product",
        "v778_organization",
        "v934_realtime",
        "v935_customer_trust",
    ):
        assert key not in ctx["data"]


def test_daily_briefing_runtime_never_builds_legacy_dashboard(app_module, monkeypatch):
    user = {"id": "qa-fast-briefing", "membership": "ELITE", "role": "ELITE"}
    briefing = {
        "date": "2026-09-30",
        "score": 80,
        "next_action": {"href": "/picks", "title": "Ver pronósticos"},
        "priorities": [],
        "alerts": [],
        "activity": [],
        "favorites": [],
        "picks": [],
        "smart_picks": [],
        "upcoming": [],
        "today_matches": [],
        "live": [],
        "counts": {"today": 0, "upcoming": 0, "live": 0, "favorites": 0, "picks": 0},
        "message": "QA",
    }

    monkeypatch.setattr(app_module, "current_session_user", lambda: user)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("briefing must not build the full dashboard")
        ),
    )
    monkeypatch.setattr(
        app_module,
        "client_command_center_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("client command is not rendered by daily briefing")
        ),
    )
    monkeypatch.setattr(app_module, "build_daily_briefing", lambda actual: briefing if actual is user else None)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/mi-dia"):
        name, ctx = app_module.daily_briefing_page()

    assert name == "daily_briefing.html"
    assert ctx["data"]["session_user"]["id"] == user["id"]
    assert ctx["data"]["briefing"]["next_action"]["href"] == "/picks"
    assert "client_command" not in ctx["data"]


def test_admin_dashboard_uses_bounded_context_only():
    route = _between(
        "def v566_admin_dashboard_page():",
        '@app.route("/api/admin/control-center")',
    )
    assert 'v932_safe_dashboard_data(request.path, scope="admin", compact=True)' in route
    assert "data = dashboard_data(" not in route
    assert 'data["v934_realtime"] = get_v934_realtime_context(summary)' in route
    assert 'data["admin_master"] = master_snapshot(__import__(__name__))' in route
    for marker in (
        "v928_admin_overview",
        "quality_center_summary",
        "v566_admin_items",
        "fallback_overview",
        "q=quality",
        "items=items",
    ):
        assert marker not in route


def test_admin_dashboard_runtime_skips_legacy_fanout(app_module, monkeypatch):
    import blueprints.admin_master_control as admin_master_control

    calls = {"safe": 0, "realtime": 0, "master": 0}
    summary = {"provider_status": "ok", "valid_live_events": []}

    monkeypatch.setattr(app_module, "is_admin_session", lambda: True)

    def fake_safe(route, lane="today", date_value=None, scope="client", compact=False, sports_summary=None):
        calls["safe"] += 1
        assert route == "/admin/dashboard"
        assert scope == "admin"
        assert compact is True
        return ({"session_user": {"role": "ADMIN"}}, summary)

    monkeypatch.setattr(app_module, "v932_safe_dashboard_data", fake_safe)
    monkeypatch.setattr(
        app_module,
        "dashboard_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("admin dashboard must not build legacy dashboard_data")
        ),
    )

    for name in ("v928_admin_overview", "quality_center_summary", "v566_admin_items"):
        monkeypatch.setattr(
            app_module,
            name,
            lambda *_a, _name=name, **_kw: (_ for _ in ()).throw(
                AssertionError(f"unused admin builder called: {_name}")
            ),
        )

    def fake_realtime(actual):
        calls["realtime"] += 1
        assert actual is summary
        return {"state": "qa"}

    def fake_master(actual_app):
        calls["master"] += 1
        assert actual_app is app_module
        return {"version": "QA", "facts": [], "areas": []}

    monkeypatch.setattr(app_module, "get_v934_realtime_context", fake_realtime)
    monkeypatch.setattr(admin_master_control, "master_snapshot", fake_master)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: (name, ctx))

    with app_module.app.test_request_context("/admin/dashboard"):
        name, ctx = app_module.v566_admin_dashboard_page()

    assert name == "admin_dashboard.html"
    assert ctx["data"]["v934_realtime"]["state"] == "qa"
    assert ctx["data"]["admin_master"]["version"] == "QA"
    assert "q" not in ctx
    assert "items" not in ctx
    assert calls == {"safe": 1, "realtime": 1, "master": 1}


def test_service_worker_caches_only_versioned_same_origin_static_assets():
    route = _between("def service_worker():", "def pwa_install_guide_page():")
    assert "NEMESIS_STATIC_V1_" in route
    assert "req.mode==='navigate'" in route
    assert "cache:'no-store'" in route
    assert "url.origin===self.location.origin" in route
    assert "url.pathname.startsWith('/static/')" in route
    assert "url.searchParams.has('v')" in route
    assert "req.destination==='style'||req.destination==='script'" in route
    assert "caches.open(NEMESIS_CACHE)" in route
    assert "cache.match(req)" in route
    assert "cache.put(req,response.clone())" in route
    assert "if(req.destination==='style'||req.destination==='script'){event.respondWith(fetch(req,{cache:'reload'}))" not in route


def test_service_worker_runtime_keeps_html_network_only_and_private_data_out_of_cache_storage(app_module):
    with app_module.app.test_request_context("/service-worker.js"):
        response = app_module.service_worker()

    body = response.get_data(as_text=True)
    assert "NEMESIS_STATIC_V1_" in body
    assert "if(req.mode==='navigate'){event.respondWith(fetch(req,{cache:'no-store'})" in body
    assert "url.pathname.startsWith('/static/')" in body
    assert "url.searchParams.has('v')" in body
    assert "caches.open(NEMESIS_CACHE)" in body
    assert "cache.put(req,response.clone())" in body
    assert "url.pathname.startsWith('/api/')" not in body
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Service-Worker-Allowed"] == "/"
