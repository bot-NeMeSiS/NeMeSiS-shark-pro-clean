"""Synthetic, read-only presentation: user separation, missing evidence, safe links."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from engines.home_personal_agenda import build_personal_agenda
from engines.admin_daily_priorities import build_daily_priorities

NOW = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)


def fixture(identifier, *, days=1, status="upcoming", **values):
    return {"id": identifier, "home_team": "Equipo A", "away_team": "Equipo B",
            "competition_key": "liga-qa", "kickoff_iso": (NOW + timedelta(days=days)).isoformat(),
            "kind": status, **values}


def agenda(matches, favorites):
    return build_personal_agenda({"storage_status": "ok", "all_valid_matches": matches}, favorites,
        normalize=lambda s: str(s).lower(), status_for=lambda m: {"is_" + m["kind"]: True},
        kickoff_for=lambda m: datetime.fromisoformat(m["kickoff_iso"]), now=NOW)


def test_explicit_current_favorites_override_cached_flags_and_do_not_mutate():
    matches = [fixture("a", is_favorite=True), fixture("b", home_team="Otro equipo")]
    original = deepcopy(matches)
    assert [m["id"] for m in agenda(matches, [{"kind":"match", "value":"a"}])["matches"]] == ["a"]
    assert [m["id"] for m in agenda(matches, [{"kind":"match", "value":"b"}])["matches"]] == ["b"]
    assert agenda(matches, []) == {"state":"EMPTY", "saved_count":0, "matches":[]}
    assert matches == original


def test_saved_preferences_do_not_equal_available_matches_and_unknown_is_not_empty():
    assert agenda([], [{"kind":"team", "value":"Equipo A"}])["state"] == "NO_MATCHES"
    assert agenda([], None)["state"] == "UNAVAILABLE"
    assert agenda([], None)["saved_count"] is None


def test_rank_bound_dedupe_and_exclude_stale_or_past_scheduled():
    rows = [fixture("later", days=4), fixture("next"), fixture("live", status="live", days=0),
            fixture("final", status="finished", days=-1), fixture("stale",status="stale"),
            fixture("past",days=-2),fixture("next")]
    actual = agenda(rows, [{"kind":"team", "value":"equipo a"}])
    assert actual["saved_count"] == 1
    assert [m["id"] for m in actual["matches"]] == ["live","next","later"]
    assert all(m["personal_reason"] == "Sigues a un equipo" for m in actual["matches"])
    assert agenda([fixture("past",days=-2)], [{"kind":"league", "value":"liga-qa"}])["state"] == "NO_MATCHES"


def test_favorite_read_is_scoped_and_public_does_not_read(app_module, monkeypatch):
    calls=[]
    monkeypatch.setattr(app_module,"get_favorites",lambda **kw: calls.append(kw) or [])
    with app_module.app.test_request_context("/"):
        monkeypatch.setattr(app_module,"current_user_id",lambda:None)
        assert app_module.personal_home_agenda({}) is None
        assert not calls
        for user in ("user-a", "user-b"):
            monkeypatch.setattr(app_module,"current_user_id",lambda:user)
            assert app_module.personal_home_agenda({})["state"]=="EMPTY"
    assert calls==[{"user_id":"user-a"},{"user_id":"user-b"}]


@pytest.mark.parametrize("language",["es","en","fr"])
def test_personal_section_does_not_duplicate_main_cards_or_fake_empty(app_module,language):
    from test_design02_r7_home_composition import render_home
    from test_design02_calendar_presentation import Structure
    from engines.ui_localization_engine import translate
    match=fixture("favorite")
    personal={"state":"READY","saved_count":1,"matches":[{**match,"personal_reason":"Partido guardado"}]}
    dom=Structure(render_home(app_module,{"personal_home":personal,"match_hub":{"today":[match],"live":[match]}},language))
    personal_section,=[n for n in dom.nodes if "data-personal-home" in n["attrs"]]
    cards=[n for n in dom.nodes if n["attrs"].get("data-v934-match-id")=="favorite"]
    assert len(cards)==1 and personal_section in cards[0]["parents"]
    assert translate("{count} favorito guardado",language,count=1) in render_home(app_module,{"personal_home":personal},language)


def test_admin_priorities_show_missing_core_reads_without_inventing_incidents():
    areas=[{"key":"sports","state":"ATENCIÓN","detail":"Sin partidos hoy"},
           {"key":"db","state":"SIN DATOS","detail":"No se pudo leer"},
           {"key":"api_football","state":"ATENCIÓN","detail":"Evidencia guardada"},
           {"key":"jobs","state":"SIN DATOS"}, {"key":"app","state":"OK"},
           {"key":"api_football","state":"ATENCIÓN"}]
    before=deepcopy(areas)
    items=build_daily_priorities(areas,[{"key":"api_football","observed_at":"2026-10-08T10:35:40+02:00"}])
    assert [i["key"] for i in items]==["db","api_football","sports"]
    assert items[0]["category"]=="Por comprobar" and items[0]["observed_at"] is None
    assert items[1]["observed_at"]=="2026-10-08T10:35:40+02:00"
    assert all(i["href"].startswith("/admin/") and i["next_step"] for i in items)
    assert areas==before


def test_admin_never_uses_untrusted_link_or_unknown_timestamp():
    result=build_daily_priorities([{"key":"jobs","state":"ATENCIÓN","href":"https://evil.invalid"}],job_at="yesterday")
    assert result[0]["href"]=="/admin/daily-automation"
    assert result[0]["observed_at"] is None


def test_unreadable_favorites_are_not_reported_as_zero(app_module,monkeypatch):
    import sqlite3
    monkeypatch.setattr(app_module,"current_user_id",lambda:"qa-read-error")
    def fail(**kw): raise sqlite3.OperationalError("database locked")
    monkeypatch.setattr(app_module,"get_favorites",fail)
    with app_module.app.test_request_context('/app'):
        assert app_module.personal_home_agenda({})=={"state":"UNAVAILABLE","saved_count":None,"matches":[]}


def test_fail_job_creates_priority_without_borrowing_provider_timestamp(tmp_path):
    from types import SimpleNamespace
    from blueprints.admin_master_control import master_snapshot
    from engines.admin_control_engine import AdminControlStore
    store=AdminControlStore(tmp_path/'qa.sqlite','QA'); store.initialize()
    a=SimpleNamespace(DB_PATH=str(store.path),APP_VERSION='QA',BASE_DIR=tmp_path,
        get_public_home_sports_summary=lambda:{"storage_status":"ok","valid_matches_today_count":2,"valid_live_events":[]},
        v945_provider_health_snapshot=lambda:{"job_finished_at":"2026-10-08T14:00:00+02:00"},
        v928_telegram_overview_fast=lambda:{},
        v928_automation_overview_fast=lambda:{"jobs":[{"last_result":"FAIL"}]},
        env_present=lambda name:False,now_iso=lambda:'2026-10-08T15:00:00+02:00')
    result=master_snapshot(a)
    item,=[i for i in result['recommendations'] if i['key']=='jobs']
    assert item['observed_at'] is None
    assert result['external_calls']==0
