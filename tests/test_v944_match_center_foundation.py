from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engines.match_context_engine import (
    CANONICAL_COMPONENT_STATES,
    MATCH_CENTER_COMPONENTS,
    MATCH_CENTER_CONTRACT,
    build_match_context,
)
from engines.sentinel_autopilot_engine import (
    build_v944_match_center_foundation_contract_snapshot,
    create_autopilot_task,
    detect_product_quality_contract_issues,
)


ROOT = Path(__file__).resolve().parents[1]
SPRINT = "V944_MATCH_CENTER_FOUNDATION_PHASE_1_FINAL"


def _detail(*, finished: bool = False, with_score: bool = False) -> dict:
    match = {
        "id": "v944-match-1",
        "home_team": "Real Club Deportivo Local",
        "away_team": "Unión Deportiva Visitante",
        "competition_name": "Competición de prueba local",
        "competition_key": "test-local",
        "match_date": "2026-07-23",
        "kickoff_time": "20:30",
        "kickoff_iso": "2026-07-23T20:30:00+02:00",
        "status": "finished" if finished else "upcoming",
        "source": "fixture-local",
        "updated_at": "2026-07-23T19:45:00+02:00",
        "status_info": {
            "key": "FT" if finished else "UPCOMING",
            "label": "Finalizado" if finished else "Próximo",
            "is_finished": finished,
            "is_live": False,
            "is_upcoming": not finished,
        },
        "live_depth": {
            "state": "FT" if finished else "UPCOMING",
            "label": "Finalizado" if finished else "Próximo",
            "minute": "FT" if finished else "20:30",
        },
        "home_identity": {"crest_url": "/team-crest.svg?name=Local"},
        "away_identity": {"crest_url": "/team-crest.svg?name=Visitante"},
    }
    if with_score:
        match.update({"home_score": 0, "away_score": 0, "score": "0-0"})
    return {
        "id": match["id"],
        "match": match,
        "favorite": True,
        "timeline": [
            {
                "minute": "FT" if finished else "20:30",
                "event_type": "state",
                "title": "Final del partido" if finished else "Partido programado",
                "detail": "Estado confirmado en la fuente local.",
            }
        ],
        "related_picks": [],
        "state": {
            "state": "FT" if finished else "UPCOMING",
            "shark_momentum": {"stats_available": False},
        },
        "statistics": {"items": []},
    }


def _context(detail: dict, **kwargs) -> dict:
    return build_match_context(
        detail,
        madrid_context={
            "client_full_datetime_label": "jueves, 23 de julio · 20:30",
            "client_date_label": "jueves, 23 de julio",
            "client_time_label": "20:30",
            "client_competition": "Competición de prueba local",
            "client_score_label": detail["match"].get("score") or "VS",
        },
        **kwargs,
    )


def test_match_context_is_one_pure_snapshot_for_all_foundation_components():
    context = _context(_detail())

    assert context["contract"] == MATCH_CENTER_CONTRACT
    assert context["foundation"] == SPRINT
    assert set(context["components"]) == set(MATCH_CENTER_COMPONENTS)
    assert all(
        component["state"] in CANONICAL_COMPONENT_STATES
        for component in context["components"].values()
    )
    assert context["diagnostics"] == {
        "builder_database_queries": 0,
        "builder_database_writes": 0,
        "external_calls": 0,
        "single_snapshot": True,
        "component_contracts": list(MATCH_CENTER_COMPONENTS),
        "canonical_states": list(CANONICAL_COMPONENT_STATES),
    }
    assert context["picks"]["count"] == 0
    assert context["statistics"]["available"] is False
    assert context["statistics"]["item_count"] == 0


def test_match_context_preserves_zero_zero_and_safe_partial_offline_states():
    finished = _context(_detail(finished=True, with_score=True))
    assert finished["state"] == "finished"
    assert finished["score"] == {
        "home": 0,
        "away": 0,
        "label": "0-0",
        "confirmed": True,
    }

    partial_detail = _detail()
    partial_detail["match"].pop("competition_name")
    partial_detail["match"].pop("kickoff_time")
    partial_detail["match"].pop("kickoff_iso")
    partial = build_match_context(partial_detail, madrid_context={})
    assert partial["competition"]["available"] is False
    assert any(
        item.startswith("Compet") and "confirmada" in item
        for item in partial["limitations"]
    )
    assert partial["score"]["confirmed"] is False

    offline = _context(_detail(), offline=True)
    assert offline["state"] == "offline"
    assert offline["components"]["MatchStory"]["state"] == "offline"


def test_match_detail_page_uses_one_detail_load_and_no_legacy_side_effects(
    client,
    app_module,
    monkeypatch,
):
    calls = {"detail": 0, "live": 0}
    fixture = _detail()

    def load_detail(match_id, *, include_depth=True):
        calls["detail"] += 1
        assert match_id == "v944-match-1"
        assert include_depth is False
        return fixture

    def load_live(_db_path, match_id):
        calls["live"] += 1
        assert match_id == "v944-match-1"
        return {"events": fixture["timeline"], "available": True}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("legacy dashboard/write path must not run")

    monkeypatch.setattr(app_module, "match_detail", load_detail)
    monkeypatch.setattr(app_module, "live_tracker_for_match", load_live)
    monkeypatch.setattr(app_module, "v935_enrich_match_lifecycle", lambda match: match)
    monkeypatch.setattr(app_module, "dashboard_data", forbidden)
    monkeypatch.setattr(app_module, "get_public_home_sports_summary", forbidden)
    monkeypatch.setattr(app_module, "record_user_activity", forbidden)

    response = client.get("/match/v944-match-1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert calls == {"detail": 1, "live": 1}
    assert 'data-match-contract="MATCH-CENTER-LIFECYCLE-STORY-V1"' in html
    assert 'data-v944-match-center-foundation="phase-1"' in html
    assert html.count("data-match-component=") == len(MATCH_CENTER_COMPONENTS)
    assert "v933-match-hero" not in html
    assert "v933-detail-tabs" not in html
    assert "Real Club Deportivo Local" in html
    assert "Unión Deportiva Visitante" in html


def test_match_detail_loader_reuses_timeline_and_picks(app_module, monkeypatch):
    calls = {
        "one": 0,
        "annotate": 0,
        "picks": 0,
        "build": 0,
        "depth": 0,
    }
    fixture = _detail()
    raw = dict(fixture["match"])

    def one(_query, _params):
        calls["one"] += 1
        return dict(raw)

    def annotate(match):
        calls["annotate"] += 1
        item = dict(match)
        item["timeline"] = list(fixture["timeline"])
        item["is_favorite"] = True
        return item

    def picks(_match):
        calls["picks"] += 1
        return []

    def build(match, timeline=None, related_picks=None, favorite=False):
        calls["build"] += 1
        return {
            "id": match["id"],
            "match": match,
            "timeline": timeline,
            "events": timeline,
            "related_picks": related_picks,
            "favorite": favorite,
            "state": {"shark_momentum": {"stats_available": False}},
            "statistics": {"items": []},
        }

    def depth(*_args, **_kwargs):
        calls["depth"] += 1
        return {
            "home_form": [],
            "away_form": [],
            "head_to_head": [],
            "shark_notes": [],
            "data_quality": {},
        }

    monkeypatch.setattr(app_module, "one", one)
    monkeypatch.setattr(app_module, "annotate_match", annotate)
    monkeypatch.setattr(app_module, "related_picks_for_match", picks)
    monkeypatch.setattr(app_module, "build_match_detail", build)
    monkeypatch.setattr(app_module, "match_depth_payload", depth)

    page_detail = app_module.match_detail("v944-match-1", include_depth=False)
    assert page_detail["timeline"] == fixture["timeline"]
    assert calls == {"one": 1, "annotate": 1, "picks": 1, "build": 1, "depth": 0}

    api_detail = app_module.match_detail("v944-match-1")
    assert api_detail["v540_depth"]["home_form"] == []
    assert calls == {"one": 2, "annotate": 2, "picks": 2, "build": 2, "depth": 1}


def test_v944_jinja_contracts_are_valid_and_responsive():
    environment = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    for relative in (
        "templates/match_detail.html",
        "templates/components/v944_match_center.html",
    ):
        environment.parse((ROOT / relative).read_text(encoding="utf-8"))

    template = (ROOT / "templates/match_detail.html").read_text(encoding="utf-8")
    components = (
        ROOT / "templates/components/v944_match_center.html"
    ).read_text(encoding="utf-8")
    css = (ROOT / "static/v933-product.css").read_text(encoding="utf-8")

    assert template.count("match_header(match_context)") == 1
    assert template.count("score_widget(match_context)") == 1
    assert all(name in components for name in MATCH_CENTER_COMPONENTS)
    assert all(f"'{state}'" in components for state in CANONICAL_COMPONENT_STATES)
    assert "@media (max-width: 1080px)" in css
    assert "@media (max-width: 800px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert not (ROOT / "static/v944-match-center.js").exists()


def _sentinel_fixture(tmp_path: Path, *, break_shell: bool = False) -> Path:
    for relative in (
        "app.py",
        "engines/match_context_engine.py",
        "templates/match_detail.html",
        "templates/components/v944_match_center.html",
        "static/v933-product.css",
    ):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if break_shell:
        template = tmp_path / "templates/match_detail.html"
        text = template.read_text(encoding="utf-8")
        template.write_text(
            text.replace(
                'data-v944-match-center-foundation="phase-1"',
                'data-v944-match-center-foundation-removed="phase-1"',
            ),
            encoding="utf-8",
        )
    return tmp_path


def test_v944_sentinel_detects_mutation_and_autopilot_requires_approval(tmp_path):
    healthy = build_v944_match_center_foundation_contract_snapshot(ROOT, SPRINT)
    assert healthy["validation_result"] == "PASS"
    assert healthy["evidence"]["violations"] == []

    broken_root = _sentinel_fixture(tmp_path, break_shell=True)
    broken = build_v944_match_center_foundation_contract_snapshot(
        broken_root,
        SPRINT,
    )
    assert broken["validation_result"] == "REGRESSION"
    assert "shell_contract" in broken["evidence"]["violations"]

    issues = detect_product_quality_contract_issues(broken_root, SPRINT)
    issue = next(
        item
        for item in issues
        if item["id"] == "V944-MATCH-CENTER-FOUNDATION-CONTRACT"
    )
    task = create_autopilot_task(issue)
    assert issue["priority"] == "P1"
    assert issue["safe_to_auto_fix"] is False
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True
