"""Real Flask routes with local, synthetic data and unchanged auth boundaries."""
import socket
from unittest.mock import patch

import pytest

from engines.team_form_engine import team_form_snapshot


@pytest.fixture
def form_client(app_module, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "form-http.sqlite"))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", True)
    app_module.seed_core()
    def deny_network(*_args, **_kwargs):
        pytest.fail("unexpected external connection during the HTTP test")
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    return app_module.app.test_client()


def sample():
    row = dict(id="qa-final", source="api_football_cache", home_team="Club QA", away_team="Rival QA",
               home_score=0, away_score=0, status="FT", kickoff_iso="2026-09-01T18:00:00Z")
    return {
        "counts":{"matches":1,"picks":0},
        "intelligence":{"quality":{},"no_fake_data":True,"title":"QA"},
        "team_form":{"home":team_form_snapshot([row],"Club QA"),"away":team_form_snapshot([row],"Rival QA")},
    }


@pytest.mark.parametrize("role", [None,"PRO"])
@pytest.mark.parametrize("route,code", [("/admin/match-intelligence",302),("/api/admin/match-intelligence",403)])
def test_protected_routes_do_not_load_private_context(app_module,form_client,role,route,code):
    with form_client.session_transaction() as state:
        if role: state.update(user_role=role,user_id="qa-client")
    with patch.object(app_module,"v745_match_intelligence_context",side_effect=AssertionError("unauthorized context")):
        response = form_client.get(route)
    assert response.status_code == code


def test_full_admin_template_uses_one_scoped_evidence_panel(app_module,form_client,monkeypatch):
    with form_client.session_transaction() as state:
        state.update(user_role="ADMIN",user_id="qa-admin",membership="ADMIN")
    monkeypatch.setattr(app_module,"dashboard_data",lambda:{})
    monkeypatch.setattr(app_module,"v745_match_intelligence_context",lambda *_:sample())
    response = form_client.get("/admin/match-intelligence")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('data-admin-team-form>') == 1
    assert html.count('filename=admin-team-form') == 0
    assert html.count('/static/admin-team-form.css') == 1
    assert "0–0" in html and "Total de temporada: no verificado" in html
    assert 'href="/match/qa-final"' in html
    assert "Traceback" not in html and "UndefinedError" not in html


def test_actual_context_and_api_delegate_to_shared_final_evidence(app_module,form_client,monkeypatch):
    final = dict(id="qa-final",source="api_football_cache",home_team="Club QA",away_team="Rival QA",
                 status="FT",home_score=0,away_score=0,kickoff_iso="2026-09-01T18:00:00Z")
    upcoming = dict(final,id="qa-future",status="NS",kickoff_iso="2099-09-01T18:00:00Z")
    monkeypatch.setattr(app_module,"dashboard_data",lambda:{"candidate_matches":[upcoming],"past_results":[final]})
    monkeypatch.setattr(app_module,"get_picks",lambda **_:[])
    with form_client.session_transaction() as state:
        state.update(user_role="ADMIN",user_id="qa-admin",membership="ADMIN")
    response = form_client.get("/api/admin/match-intelligence?match_id=qa-future")
    assert response.status_code == 200
    body = response.get_json()["match_intelligence"]
    for side in ("home","away"):
        assert body["team_form"][side]["matches_found"] == 1
        assert body["team_form"][side]["form"] == ["D"]
        assert body["team_form"][side]["last_matches"][0]["id"] == "qa-final"
