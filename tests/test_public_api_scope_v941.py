"""V941 public API scope: no provider/write bypasses and no membership leaks."""
from __future__ import annotations


def test_public_startup_check_is_sanitized(client):
    response=client.get("/api/startup-check")
    assert response.status_code==200
    payload=response.get_json()
    assert payload["diagnostics"]=="admin_required"
    for forbidden in ("db","error","seed_lock","seeded_db_path"):
        assert forbidden not in payload


def test_public_crest_diagnostics_does_not_seed_or_expose_internal_state(client,app_module,monkeypatch):
    monkeypatch.setattr(app_module,"seed_core",lambda: (_ for _ in ()).throw(AssertionError("public diagnostics must not seed")))
    response=client.get("/api/crest-diagnostics")
    assert response.status_code==200
    payload=response.get_json()
    assert payload["diagnostics"]=="admin_required"
    assert "provider_key_masked" not in payload
    assert "last_error" not in payload
    assert "sample_missing" not in payload


def test_public_sportsdb_diagnostics_never_calls_provider(client,app_module,monkeypatch):
    monkeypatch.setattr(app_module,"thesportsdb_diagnostics",lambda *_a,**_k: (_ for _ in ()).throw(AssertionError("public GET must not call provider")))
    response=client.get("/api/thesportsdb/diagnostics?team=QA")
    assert response.status_code==200
    payload=response.get_json()["diagnostics"]
    assert payload["direct_check"]=="admin_required"
    assert payload["external_calls"]==0
    assert "key_masked" not in payload


def test_team_resolve_get_is_read_only_and_refresh_is_rejected(client,app_module,monkeypatch):
    calls=[]
    monkeypatch.setattr(app_module,"resolve_team",lambda team,refresh=False: calls.append((team,refresh)) or {"name":team,"refresh":refresh})
    response=client.get("/api/team/resolve?team=Club%20QA")
    assert response.status_code==200
    assert calls==[("Club QA",False)]
    calls.clear()
    blocked=client.get("/api/team/resolve?team=Club%20QA&refresh=1")
    assert blocked.status_code==405
    assert blocked.get_json()["error"]=="refresh_requires_admin_post"
    assert calls==[]


def test_team_resolve_refresh_requires_authenticated_admin_post(client,app_module,monkeypatch):
    calls=[]
    monkeypatch.setattr(app_module,"resolve_team",lambda team,refresh=False: calls.append((team,refresh)) or {"name":team,"refresh":refresh})
    assert client.post("/api/team/resolve",json={"team":"Club QA","refresh":True}).status_code==403
    assert calls==[]

    with client.session_transaction() as state:
        state.update(user_id="qa-admin-api-scope",user_role="ADMIN",membership="ADMIN",user_membership="ADMIN",user_name="QA Admin")
        token=app_module.generate_csrf_token(state)
    response=client.post("/api/team/resolve",json={"team":"Club QA","refresh":True,"csrf_token":token})
    assert response.status_code==200
    assert calls==[("Club QA",True)]


def test_import_history_is_admin_only(client):
    response=client.get("/api/imports")
    assert response.status_code==403


def _recommendations():
    return [
        {"id":"free","membership_required":"FREE","selection":"Libre"},
        {"id":"pro","membership_required":"PRO","selection":"Pro"},
        {"id":"elite","membership_required":"ELITE","selection":"Elite"},
    ]


def test_public_recommendation_apis_respect_membership(client,app_module,monkeypatch):
    monkeypatch.setattr(app_module,"v565_recommendation_pool",lambda limit=50:_recommendations())
    monkeypatch.setattr(app_module,"v566_template_recommendations",lambda limit=40:_recommendations())

    for path in ("/api/v565/recommendations","/api/recommendations"):
        anonymous=client.get(path)
        assert anonymous.status_code==200
        assert anonymous.get_json()["membership"]=="FREE"
        assert [x["id"] for x in anonymous.get_json()["recommendations"]]==["free"]

    with client.session_transaction() as state:
        state.update(user_id="qa-pro-api-scope",user_role="PRO",membership="PRO",user_membership="PRO",user_name="QA")
    for path in ("/api/v565/recommendations","/api/recommendations"):
        pro=client.get(path)
        assert [x["id"] for x in pro.get_json()["recommendations"]]==["free","pro"]


def test_shark_intelligence_pick_subset_respects_plan(app_module):
    summary={"valid_active_picks":[
        {"id":"free","match_id":"m1","membership_required":"FREE"},
        {"id":"pro","match_id":"m1","membership_required":"PRO"},
        {"id":"elite","match_id":"m1","membership_required":"ELITE"},
    ]}
    free=app_module._shark_intelligence_pick_subset(summary,"m1",user={"membership":"FREE","role":"FREE"})
    pro=app_module._shark_intelligence_pick_subset(summary,"m1",user={"membership":"PRO","role":"PRO"})
    elite=app_module._shark_intelligence_pick_subset(summary,"m1",user={"membership":"ELITE","role":"ELITE"})
    assert [x["id"] for x in free]==["free"]
    assert [x["id"] for x in pro]==["free","pro"]
    assert [x["id"] for x in elite]==["free","pro","elite"]


def test_shark_intelligence_filters_detail_picks_before_match_context(app_module,monkeypatch):
    summary={
        "valid_matches_today":[{"id":"m1"}],
        "valid_active_picks":[{"id":"free","match_id":"m1","membership_required":"FREE"}],
    }
    captured={}
    monkeypatch.setattr(app_module,"get_public_home_sports_summary",lambda:summary)
    monkeypatch.setattr(app_module,"get_sports_metrics_contract",lambda _s:{})
    monkeypatch.setattr(app_module,"match_detail",lambda *_a,**_k:{
        "match":{"id":"m1"},"timeline":[],
        "related_picks":[
            {"id":"free","membership_required":"FREE"},
            {"id":"pro","membership_required":"PRO"},
            {"id":"elite","membership_required":"ELITE"},
        ],
    })
    monkeypatch.setattr(app_module,"live_tracker_for_match",lambda *_a,**_k:{})
    monkeypatch.setattr(app_module,"client_match_display_context",lambda *_a,**_k:{})
    monkeypatch.setattr(app_module,"canonical_match_for_domain_context",lambda value:value)
    def context(detail,**_kwargs):
        captured["picks"]=detail["related_picks"]
        return {"ok":True}
    monkeypatch.setattr(app_module,"build_match_context",context)
    monkeypatch.setattr(app_module,"build_shark_intelligence_platform_snapshot",lambda **kwargs:kwargs)

    with app_module.app.test_request_context("/api/shark/intelligence"):
        app_module.session.update(user_id="qa-free-intelligence",user_role="FREE",membership="FREE",user_membership="FREE")
        app_module.build_shark_intelligence_page_context()
    assert [x["id"] for x in captured["picks"]]==["free"]


def test_internal_diagnostic_apis_require_admin(client):
    paths=(
        "/api/deep-route-check",
        "/api/client-experience-check",
        "/api/route-check",
        "/api/v565/sports-data-picks-check",
        "/api/v566/product-polish-check",
        "/api/autonomous-picks/status",
        "/api/system/v570-check",
    )
    for path in paths:
        response=client.get(path)
        assert response.status_code==403,(path,response.status_code)


def test_public_timezone_check_does_not_expose_match_samples(client):
    response=client.get("/api/timezone-check")
    assert response.status_code==200
    payload=response.get_json()
    assert payload["timezone"]=="Europe/Madrid"
    assert "sample_matches" not in payload


def test_admin_can_still_access_internal_diagnostics(client):
    with client.session_transaction() as state:
        state.update(user_id="qa-admin-diagnostics",user_role="ADMIN",membership="ADMIN",user_membership="ADMIN",user_name="QA Admin")
    response=client.get("/api/route-check")
    assert response.status_code==200
    assert response.get_json()["ok"] is True


def test_api_cache_headers_are_session_safe(client,app_module,monkeypatch):
    monkeypatch.setattr(app_module,"v566_template_recommendations",lambda limit=40:_recommendations())

    public_response=client.get("/api/recommendations")
    assert public_response.status_code==200
    assert "Cookie" in public_response.headers.get("Vary","")

    with client.session_transaction() as state:
        state.update(user_id="qa-cache-scope",user_role="PRO",membership="PRO",user_membership="PRO",user_name="QA")
    private_response=client.get("/api/recommendations")
    assert private_response.status_code==200
    cache_control=private_response.headers.get("Cache-Control","").lower()
    assert "private" in cache_control
    assert "no-store" in cache_control
    assert "Cookie" in private_response.headers.get("Vary","")


def test_authenticated_html_cache_is_private(client):
    with client.session_transaction() as state:
        state.update(user_id="qa-cache-html",user_role="PRO",membership="PRO",user_membership="PRO",user_name="QA")
    response=client.get("/profile")
    assert response.status_code in (200,302)
    if response.status_code==200:
        cache_control=response.headers.get("Cache-Control","").lower()
        assert "private" in cache_control
        assert "no-store" in cache_control
        assert "Cookie" in response.headers.get("Vary","")

