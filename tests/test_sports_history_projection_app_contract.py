"""Actual App consumer contracts. Authored here; run only by Root's App guard."""
import json
from tools.render_cron_master_tick import sanitized_sports_pipeline

OLD="2026-10-01T01:02:03+00:00"
NOW="2026-11-02T20:00:00+00:00"

def history(state="DEFERRED"):
    return {"latest_run":{"status":"OK","finished_at":OLD,"external_calls":1,"payload_json":"{}"},
            "latest_account":{"ok":True,"http_status":200,"plan":"OWNED_PERSISTED"},
            "continuity":[{"capability":"fixtures","requested":True,"received":1,"persisted":0}],
            "sports_read_state":{"state":state,"reason":"TIME_BUDGET","unknown_capabilities":["players","stats"],
                "latest_run_observed":True,"account_observed_at":OLD,"account_is_current":False,
                "snapshot_scope":"ONE_READ_TRANSACTION","query_interrupted":True}}

def compact(app,pipeline):
    return app._cron_compact_payload("sports_sync",{"ok":True,"status":"PARTIAL","sports_pipeline":pipeline},
                                     NOW,NOW)["sports_pipeline"]

def test_actual_current_coverage_does_not_hide_partial_historical_read(app_module):
    current={"ok":True,"status":"OK","finished_at":NOW,"deep_enrichment":{
        "status":"OK","finished_at":NOW,"account":{"ok":True,"http_status":200},
        "capabilities":{"stats":{"requested":True,"received":2,"persisted":1}}}}
    pipeline=app_module._build_sports_pipeline_diagnostics(current,history())
    assert pipeline["coverage"]["source"]=="CURRENT_DEEP_RUN"
    assert pipeline["provider_access"]["is_current"] is True
    assert pipeline["history_read"]["state"]=="DEFERRED"
    assert pipeline["history_read"]["account_observed_at"]==OLD
    assert pipeline["history_read"]["account_is_current"] is False
    assert pipeline["history_read"]["unknown_capabilities"]==["players","stats"]
    framed=compact(app_module,pipeline)
    emitted=sanitized_sports_pipeline({"sports_pipeline":framed},"owned-secret")
    assert emitted["history_read"]==pipeline["history_read"]
    assert emitted["coverage"]["source"]=="CURRENT_DEEP_RUN"

def test_actual_partial_history_preserves_old_clock_zero_and_no_unknown_rows(app_module):
    pipeline=app_module._build_sports_pipeline_diagnostics(
        {"ok":True,"status":"PARTIAL","deep_enrichment":{"status":"SKIPPED_NOT_DUE"}},history())
    assert pipeline["coverage"]["source"]=="PARTIAL_PERSISTED_DEEP_SAMPLE"
    assert pipeline["coverage"]["capabilities"]["fixtures"]["state"]=="LAST_OBSERVED"
    assert pipeline["coverage"]["capabilities"]["fixtures"]["persisted"]==0
    assert pipeline["coverage"]["capabilities"]["fixtures"]["persisted_scope"]=="STORE_TOTAL"
    assert pipeline["coverage"]["capabilities"]["fixtures"]["observed_at"]==OLD
    assert "players" not in pipeline["coverage"]["capabilities"]
    assert "players" not in pipeline["capabilities"]
    assert pipeline["provider_access"]["checked_at"]==OLD
    assert pipeline["provider_access"]["is_current"] is False
    assert pipeline["provider_access"]["freshness"]=="LAST_OBSERVED_NOT_CURRENT"
    framed=compact(app_module,pipeline)
    emitted=sanitized_sports_pipeline({"sports_pipeline":framed},"owned-secret")
    assert "players" not in emitted["coverage"]["capabilities"]
    assert "players" not in emitted["capabilities"]
    assert emitted["history_read"]==pipeline["history_read"]

def test_actual_compact_and_master_independently_close_history_metadata(app_module):
    raw=app_module._build_sports_pipeline_diagnostics({},history())
    raw["history_read"].update(reason="PRIVATE_ERROR_SQL_USERS",unknown_capabilities=["players","foreign_fixture_id"],
                              account_observed_at="PRIVATE_SECRET",account_is_current=True,foreign_sql="PRIVATE_SQL")
    framed=compact(app_module,raw)
    assert framed["history_read"]["unknown_capabilities"]==["players"]
    assert framed["history_read"]["reason"]=="UNKNOWN"
    assert framed["history_read"]["account_observed_at"]==""
    assert framed["history_read"]["account_is_current"] is False
    assert "PRIVATE" not in json.dumps(framed["history_read"])
    # Do not rely on App sanitization: runner must independently close its input.
    framed["history_read"]["unknown_capabilities"].append("SQL_USER_ID")
    framed["history_read"]["reason"]="PRIVATE_ERROR"
    emitted=sanitized_sports_pipeline({"sports_pipeline":framed},"owned-secret")
    assert emitted["history_read"]["unknown_capabilities"]==["players"]
    assert emitted["history_read"]["reason"]=="UNKNOWN"

def test_actual_legacy_nominal_path_is_unchanged_without_new_read_metadata(app_module):
    sample=history()
    del sample["sports_read_state"]
    pipeline=app_module._build_sports_pipeline_diagnostics({"deep_enrichment":{"status":"SKIPPED_NOT_DUE"}},sample)
    assert pipeline["coverage"]["source"]=="LAST_PERSISTED_DEEP_SAMPLE"
    assert pipeline["coverage"]["capabilities"]["fixtures"]["persisted"]==0
    assert pipeline["coverage"]["capabilities"]["fixtures"]["state"]=="LAST_OBSERVED"
    assert "history_read" not in pipeline
    framed=compact(app_module,pipeline)
    assert "history_read" not in framed
    assert "history_read" not in sanitized_sports_pipeline({"sports_pipeline":framed},"")


def _provider_seams_for_real_sports_post(app_module,monkeypatch,*,complete_deep=False):
    # External/business stage seams only. App, seed_core, DB getters, window
    # state, candidate selection and initializer remain their REAL functions.
    monkeypatch.setenv("AUTOMATION_SECRET","owned-sports-history-caller")
    monkeypatch.setattr(app_module,"sync_api_football_match_window",lambda *a,**k:{
        "ok":True,"status":"OK","fixtures_count":1,"external_calls":0})
    monkeypatch.setattr(app_module,"sync_api_football_live_tracker",lambda *a,**k:{
        "ok":True,"status":"OK","fixtures_count":0,"external_calls":0})
    monkeypatch.setattr(app_module,"refresh_api_football_statistics_if_due",lambda *a,**k:{
        "ok":True,"status":"SKIPPED_NOT_DUE","external_calls":0})
    deep=({"ok":True,"status":"OK","finished_at":NOW,"external_calls":0,
           "account":{"ok":True,"http_status":200,"configured":True},
           "capabilities":{"account":{"requested":True,"http_status":200},
                           "stats":{"requested":True,"received":1,"persisted":1}}}
          if complete_deep else {"ok":True,"status":"SKIPPED_NOT_DUE","external_calls":0})
    monkeypatch.setattr(app_module,"run_api_exploitation_if_due",lambda *a,**k:deep)
    monkeypatch.setattr(app_module,"run_pick_grading",lambda *a,**k:{"ok":True,"picks_checked":0})
    return {"X-Automation-Secret":"owned-sports-history-caller","X-NeMeSiS-Cron-Runner":"render-cron"}

def test_actual_post_deferred_reader_uses_same_budget_and_preserves_business_success(client,app_module,monkeypatch):
    from engines import cron_request_budget as scopes
    headers=_provider_seams_for_real_sports_post(app_module,monkeypatch)
    observed=[];before=scopes._CURRENT.get()
    def reader(db_path,sports_budget=None):
        assert type(sports_budget) is scopes.CronRequestBudget
        assert scopes._CURRENT.get() is sports_budget
        observed.append(sports_budget)
        sports_budget.deferred=True  # The dependency's controlled-deferral seam.
        partial=history()
        partial["ok"]=False
        partial["persisted_totals"]={"fixtures":0}
        partial["latest_run"]["payload_json"]=json.dumps({
            "account":partial["latest_account"],"capabilities":{"fixtures":{"requested":True,"received":1}},
            "selected_fixture_ids":["owned-fixture"]})
        partial["sports_read_state"]["unknown_capabilities"]=[
            "events","lineups","players","stats","standings","h2h","injuries"]
        return partial
    monkeypatch.setattr(app_module,"api_exploitation_summary",reader)
    response=client.post("/api/automation/sports/sync",headers=headers)
    assert response.status_code==200
    payload=response.get_json()
    assert len(observed)==1 and scopes._CURRENT.get() is before
    assert payload["ok"] is True and payload["processed"]==1
    assert payload["status"]=="PARTIAL"
    assert "TIME_BUDGET" in payload["controlled_deferrals"]
    assert payload["technical_errors"]==[]
    pipeline=payload["sports_pipeline"]
    assert pipeline["history_read"]["state"]=="DEFERRED"
    assert "players" in pipeline["history_read"]["unknown_capabilities"]
    assert pipeline["coverage"]["source"]=="PARTIAL_PERSISTED_DEEP_SAMPLE"
    assert "players" not in pipeline["coverage"]["capabilities"]
    assert "players" not in pipeline["capabilities"]
    assert pipeline["provider_access_is_current"] is False
    assert pipeline["provider_access"]["is_current"] is False
    assert pipeline["provider_access"]["checked_at"]==OLD
    assert pipeline["provider_access"]["freshness"]=="LAST_OBSERVED_NOT_CURRENT"

def test_actual_post_complete_current_deep_does_not_request_history_or_defer(client,app_module,monkeypatch):
    headers=_provider_seams_for_real_sports_post(app_module,monkeypatch,complete_deep=True)
    reads=[]
    def forbidden_history(*args,**kwargs):
        reads.append(True)
        raise AssertionError("Complete current deep evidence needs no historical reader")
    monkeypatch.setattr(app_module,"api_exploitation_summary",forbidden_history)
    response=client.post("/api/automation/sports/sync",headers=headers)
    assert response.status_code==200
    payload=response.get_json()
    assert reads==[]
    assert payload["ok"] is True and payload["processed"]==1
    assert payload["status"]=="OK"
    assert payload["technical_errors"]==[]
    assert "TIME_BUDGET" not in payload["controlled_deferrals"]
    pipeline=payload["sports_pipeline"]
    assert pipeline["coverage"]["source"]=="CURRENT_DEEP_RUN"
    assert pipeline["provider_access_is_current"] is True
    assert "history_read" not in pipeline

def test_actual_post_denied_token_does_not_invoke_historical_reader(client,app_module,monkeypatch):
    headers=_provider_seams_for_real_sports_post(app_module,monkeypatch)
    reads=[]
    monkeypatch.setattr(app_module,"api_exploitation_summary",lambda *a,**k:reads.append(True))
    response=client.post("/api/automation/sports/sync",headers={
        **headers,"X-Automation-Secret":"wrong-owned-sports-history-caller"})
    assert response.status_code==403
    assert response.get_json()["ok"] is False
    assert response.get_json()["error"]=="automation_secret_invalid"
    assert reads==[]
