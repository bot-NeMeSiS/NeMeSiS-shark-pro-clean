"""Game UI specialist division never implies real staffing, running agents, paid usage or QA PASS."""
from copy import deepcopy
from pathlib import Path

from engines.game_ui_review_lab import build_game_ui_lab, GAME_UI_DISCIPLINES
from engines.company_operating_system_engine import build_company_os_summary


def test_game_ui_roles_have_measurable_gates_without_running_agents():
    original = deepcopy(GAME_UI_DISCIPLINES)
    state = build_game_ui_lab()
    assert state["contract"] == "NEMESIS-GAME-UI-LAB-V1"
    assert state["state"] == "PLANNED_NOT_EXECUTED"
    assert state["autonomous_agents_started"] == state["external_calls"] == 0
    assert state["paid_credits_consumed"] == state["releases_approved"] == 0
    assert state["founder_review_required"] is True
    assert len(state["disciplines"]) == 7
    assert len({r["id"] for r in state["disciplines"]}) == 7
    assert all(r["execution_state"] == "UNVERIFIED" for r in state["disciplines"])
    assert all(r["focus"] and r["acceptance"] and r["proof"] and r["surfaces"]
               for r in state["disciplines"])
    assert GAME_UI_DISCIPLINES == original


def test_company_os_combines_existing_workers_without_claiming_24x7_execution():
    summary = build_company_os_summary(version="SIMULATED_QA")
    state = summary["game_ui_lab"]
    assert summary["execution_state"] == "UNVERIFIED"
    assert summary["external_calls"] is False
    assert all(w["execution_state"] == "UNVERIFIED" for w in summary["workers"])
    assert state["autonomous_agents_started"] == 0
    assert state["tiers"] == ["FREE", "PRO", "ELITE", "ADMIN"]
    assert state["target_viewports"] == [320, 390, 768, 1440]


def test_admin_game_ui_section_exposes_no_fake_hired_personnel():
    html = (Path(__file__).resolve().parents[1] / "templates/admin_company_os.html").read_text("utf-8")
    assert 'data-game-ui-lab=' in html
    assert "No son personas contratadas" in html
    assert "Revisión humana obligatoria" in html
    assert "/admin/visual-qa" in html


def test_admin_route_preserves_auth_and_creative_lab(client):
    assert client.get("/admin/company-os").status_code in {302, 403}
    with client.session_transaction() as session:
        session.update(user_id="SIMULATED_QA_admin", user_role="ADMIN", membership="ADMIN")
    response = client.get("/admin/company-os")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "NEMESIS-GAME-UI-LAB-V1" in text
    assert "Especialistas visuales de videojuegos" in text
    assert "PLANNED_NOT_EXECUTED" in text
