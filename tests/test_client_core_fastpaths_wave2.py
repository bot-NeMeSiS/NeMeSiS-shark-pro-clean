"""Fast-path regressions for high-value client surfaces."""


def _boom(*_args, **_kwargs):
    raise AssertionError("heavy dashboard/home builder must not run on this fast-path")


def test_global_competitions_does_not_build_dashboard(app_module, monkeypatch):
    captured = {}
    local_reads = []

    def recorded_competitions(sql):
        local_reads.append(sql)
        assert "SELECT DISTINCT competition_id" in sql
        assert "FROM matches" in sql
        return []

    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "competitions", lambda: [{"id": "laliga", "name": "LaLiga"}])
    monkeypatch.setattr(app_module, "rows", recorded_competitions)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: captured.update(name=name, **ctx) or "ok")

    with app_module.app.test_request_context("/global"):
        assert app_module.global_football() == "ok"

    assert captured["name"] == "global.html"
    assert len(local_reads) == 1
    assert captured["data"] == {
        "competitions": [{"id": "laliga", "name": "LaLiga", "has_matches": False}],
        "countries": [], "query": "", "country": "",
    }


def test_markets_page_reuses_one_local_input_bundle(app_module, monkeypatch):
    captured = {}
    calls = {"shared": 0, "markets": 0, "combis": 0}
    user = {"id": "u1", "membership": "PRO", "role": "CLIENT"}
    matches = [{"id": "m1"}, {"id": "m2"}]
    picks = [{"id": "p1"}, {"id": "p2"}]

    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)

    def shared(got_user):
        calls["shared"] += 1
        assert got_user is user
        return matches, picks

    def markets_context(**kwargs):
        calls["markets"] += 1
        assert kwargs["user"] is user
        assert kwargs["matches"] == matches
        assert kwargs["picks"] == picks
        return {"catalog": []}

    def combi_context(**kwargs):
        calls["combis"] += 1
        assert kwargs["user"] is user
        assert kwargs["matches"] is matches
        assert kwargs["picks"] is picks
        assert kwargs["requested_count"] == 4
        return {"requested_count": 4}

    monkeypatch.setattr(app_module, "_v765_shared_market_inputs", shared)
    monkeypatch.setattr(app_module, "v765_markets_context", markets_context)
    monkeypatch.setattr(app_module, "v765_combi_context", combi_context)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: captured.update(name=name, **ctx) or "ok")

    with app_module.app.test_request_context("/mercados?partidos=4"):
        assert app_module.betting_markets_page() == "ok"

    assert calls == {"shared": 1, "markets": 1, "combis": 1}
    assert captured["name"] == "betting_markets.html"
    assert captured["data"]["session_user"] is user


def test_markets_api_reuses_one_local_input_bundle(app_module, monkeypatch):
    calls = {"shared": 0}
    user = {"id": "u1", "membership": "ELITE", "role": "CLIENT"}
    matches = [{"id": "m1"}]
    picks = [{"id": "p1"}]

    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "home_light_data", _boom)
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)

    def shared(_user):
        calls["shared"] += 1
        return matches, picks

    monkeypatch.setattr(app_module, "_v765_shared_market_inputs", shared)
    monkeypatch.setattr(app_module, "v765_markets_context", lambda **_kwargs: {"catalog": ["ok"]})
    monkeypatch.setattr(app_module, "v765_combi_context", lambda **_kwargs: {"legs": ["ok"]})

    with app_module.app.test_request_context("/api/client/betting-markets?partidos=3"):
        response = app_module.api_client_betting_markets()

    payload = response.get_json()
    assert calls["shared"] == 1
    assert payload["ok"] is True
    assert payload["markets"]["catalog"] == ["ok"]
    assert payload["combis"]["legs"] == ["ok"]


def test_shark_core_page_uses_only_shark_summary(app_module, monkeypatch):
    captured = {}
    user = {"id": "u1", "name": "Cliente", "membership": "PRO", "role": "CLIENT"}
    monkeypatch.setattr(app_module, "dashboard_data", _boom)
    monkeypatch.setattr(app_module, "current_session_user", lambda: user)

    def summary(got_user=None):
        assert got_user is user
        return {"score": 75, "user": {"membership": "PRO"}, "sections": {}}

    monkeypatch.setattr(app_module, "v570_shark_core_summary", summary)
    monkeypatch.setattr(app_module, "render_template", lambda name, **ctx: captured.update(name=name, **ctx) or "ok")

    with app_module.app.test_request_context("/shark-core"):
        assert app_module.v570_shark_core_page() == "ok"

    assert captured["name"] == "shark_core.html"
    assert captured["data"] == {"session_user": user}
    assert captured["shark"]["score"] == 75


def test_shark_core_summary_accepts_known_user_without_session_lookup(app_module, monkeypatch):
    user = {"id": "u1", "name": "Cliente", "membership": "FREE", "role": "CLIENT"}
    monkeypatch.setattr(app_module, "current_session_user", _boom)
    monkeypatch.setattr(app_module, "get_favorites", lambda **_kwargs: [])
    monkeypatch.setattr(app_module, "v566_template_recommendations", lambda **_kwargs: [])
    monkeypatch.setattr(app_module, "_recommendations_for_current_membership", lambda items: ("FREE", list(items)))
    monkeypatch.setattr(app_module, "get_picks", lambda **_kwargs: [])
    monkeypatch.setattr(app_module, "get_matches", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app_module, "get_upcoming_matches", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app_module, "build_daily_briefing", lambda **_kwargs: {"score": 0})

    result = app_module.v570_shark_core_summary(user)
    assert result["user"]["membership"] == "FREE"
    assert result["sections"]["upcoming"] == []
