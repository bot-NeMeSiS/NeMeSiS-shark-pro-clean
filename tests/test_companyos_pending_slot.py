"""Read-only pending dates agree with existing due/consumed-period rules."""
import json
from datetime import datetime
from pathlib import Path
import pytest
from engines import product_review_system_engine as ce

ROOT=Path(__file__).resolve().parents[1]


def preview(storage, now, task="daily_product_review"):
    return ce.preview_continuous_evolution_scheduler_task(ROOT,"TEST",task_name=task,now=now,storage_root=storage)


@pytest.mark.parametrize("now",["2026-11-11T03:59:00+01:00","2026-11-11T04:00:00+01:00","2026-11-11T09:00:00+01:00"])
def test_unconsumed_daily_slot_is_today_even_after_due_time(tmp_path,now):
    storage=tmp_path/"absent-owned-store"
    value=preview(storage,now)
    assert value["next_expected_run"]=="2026-11-11T04:00:00+01:00"
    assert value["scheduled_for"]==value["next_expected_run"]
    assert value["due"] is (now!="2026-11-11T03:59:00+01:00")
    assert not storage.exists()


def write_owned_state(storage, task, record):
    storage.mkdir()
    path=storage/"scheduler_state.json"
    path.write_text(json.dumps({"tasks":{task:record}}),encoding="utf-8")
    return path,path.read_bytes()


@pytest.mark.parametrize("completed,expected,due",[(None,"2026-11-11T04:00:00+01:00",True),
                            ("2026-11-10","2026-11-11T04:00:00+01:00",True),
                            ("2026-11-11","2026-11-12T04:00:00+01:00",False)])
def test_stale_stored_prediction_does_not_replace_consumption_truth(tmp_path,completed,expected,due):
    storage=tmp_path/"owned-store"
    path,before=write_owned_state(storage,"daily_product_review",{
        "last_completed_period":completed,"next_expected_run":"2030-01-01T04:00:00+01:00",
        "last_result":"FAILED","run_count":17,"last_job_id":"OWNED-RECEIPT"})
    value=preview(storage,"2026-11-11T09:00:00+01:00")
    assert value["next_expected_run"]==expected
    assert value["due"] is due
    assert path.read_bytes()==before
    assert sorted(p.name for p in storage.iterdir())==["scheduler_state.json"]


@pytest.mark.parametrize("task,now,expected",[
    ("weekly_executive_review","2026-11-11T12:00:00+01:00","2026-11-09T04:30:00+01:00"),
    ("monthly_strategy_review","2026-11-11T12:00:00+01:00","2026-11-01T05:00:00+01:00")])
def test_overdue_weekly_and_monthly_slots_remain_visible(tmp_path,task,now,expected):
    value=preview(tmp_path/"absent-owned-store",now,task)
    assert value["due"] is True
    assert value["next_expected_run"]==expected


@pytest.mark.parametrize("consumed",["last_completed_period","last_attempt_period"])
def test_native_consumed_hour_never_appears_due_again(tmp_path,consumed):
    storage=tmp_path/"owned-store"
    task="platform_workforce_review"
    now=ce._ce_now("2026-10-25T02:30:00+02:00")
    path,before=write_owned_state(storage,task,{consumed:ce._ce_period_key(task,now),
        "next_expected_run":"2026-10-25T02:00:00+02:00"})
    value=preview(storage,now,task)
    assert value["due"] is False
    assert value["next_expected_run"]=="2026-10-25T02:00:00+01:00"
    assert path.read_bytes()==before


def test_preview_does_not_write_lock_or_execute_reviews(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError("read-only observation attempted action")
    for name in ["_ce_ensure_dirs","_ce_write_json","_ce_acquire_lock","run_native_workforce_review","run_continuous_evolution_cycle"]:
        monkeypatch.setattr(ce,name,forbidden)
    value=preview(tmp_path/"absent-owned-store","2026-11-11T09:00:00+01:00")
    assert value["due"] is True
    assert value["dangerous_actions_executed"] is False
    assert not (tmp_path/"absent-owned-store").exists()


def test_period_consumed_before_nominal_time_stays_consumed(tmp_path):
    storage=tmp_path/"owned-store"
    path,before=write_owned_state(storage,"daily_product_review",{
        "last_completed_period":"2026-11-11", "next_expected_run":"2026-11-12T04:00:00+01:00"})
    value=preview(storage,"2026-11-11T03:00:00+01:00")
    assert value["due"] is False
    assert value["next_expected_run"]=="2026-11-12T04:00:00+01:00"
    assert path.read_bytes()==before
