"""SHARK read-path regressions through the original LOCAL SAFE supervisor.

Spies only observe calls to the real builders. Authentication, request validation,
prepared fixture ownership, SQLite, quotas, snapshots and Jinja stay in place.
Do not import App here or run this file against production storage.
"""
from functools import wraps
import re

import pytest

from test_shark_functional_flow import (
    Form,
    prepared_probe as prepared_probe,
    snapshots,
)
from test_shark_selected_pick_boundary import shark_probe as shark_probe


def _observe_collector(a, monkeypatch):
    """Count work only while the actual SHARK collector is executing."""
    calls, active = [], []
    collector = a._v998_shark_collections
    live_context = a.v931_live_context
    get_metrics = a.get_sports_metrics_contract
    build_metrics = a.build_sports_metrics_contract
    prepare = a._v991_prepare_summary_operation

    @wraps(collector)
    def observed_collector(summary, user):
        call = {
            "summary": summary,
            "operation": a._v991_operation_for(summary),
            "get_metrics": [],
            "build_metrics": [],
            "prepare": [],
            "live": [],
            "inside_live": False,
        }
        calls.append(call)
        active.append(call)
        try:
            call["result"] = collector(summary, user)
            return call["result"]
        finally:
            active.pop()

    @wraps(live_context)
    def observed_live(summary, *args, **kwargs):
        if not active:
            return live_context(summary, *args, **kwargs)
        call = active[-1]
        call["inside_live"] = True
        try:
            result = live_context(summary, *args, **kwargs)
            call["live"].append({
                "summary": summary,
                "projection": kwargs.get("fixture_projection"),
                "result": result,
            })
            return result
        finally:
            call["inside_live"] = False

    @wraps(get_metrics)
    def observed_get_metrics(summary, *args, **kwargs):
        result = get_metrics(summary, *args, **kwargs)
        if active:
            active[-1]["get_metrics"].append({
                "summary": summary,
                "inside_live": active[-1]["inside_live"],
                "result": result,
            })
        return result

    @wraps(build_metrics)
    def observed_build_metrics(summary, *args, **kwargs):
        result = build_metrics(summary, *args, **kwargs)
        if active:
            active[-1]["build_metrics"].append({
                "summary": summary,
                "operation": a._v991_operation_for(summary),
                "result": result,
            })
        return result

    @wraps(prepare)
    def observed_prepare(*args, **kwargs):
        result = prepare(*args, **kwargs)
        if active:
            active[-1]["prepare"].append(result)
        return result

    for name, observer in (
        ("_v998_shark_collections", observed_collector),
        ("v931_live_context", observed_live),
        ("get_sports_metrics_contract", observed_get_metrics),
        ("build_sports_metrics_contract", observed_build_metrics),
        ("_v991_prepare_summary_operation", observed_prepare),
    ):
        monkeypatch.setattr(a, name, observer)
    return calls


def _assert_single_live_metrics_read(call):
    # v931_live_context already builds these metrics once. A second collector
    # getter would repeat the real grouped selections over the same operation.
    assert len(call["live"]) == 1
    assert len(call["get_metrics"]) == 1
    assert len(call["build_metrics"]) == 1
    assert call["prepare"] == []
    live, getter, builder = (
        call["live"][0], call["get_metrics"][0], call["build_metrics"][0]
    )
    assert live["summary"] is getter["summary"] is builder["summary"] is call["summary"]
    assert getter["inside_live"] is True
    assert getter["result"] is builder["result"] is live["result"]["sports_metrics"]
    assert builder["operation"] is call["operation"]
    assert live["projection"] is not None
    return live["result"]["sports_metrics"]


def _ask_live(client, csrf):
    response = client.post(
        "/api/shark/ask", base_url="http://127.0.0.1",
        headers={"X-CSRF-Token": csrf}, json={"q": "directo"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    result = response.get_json()["shark"]
    assert result["execution_source"] == "LOCAL" and result["external_calls"] == 0
    return result["context"]["collections"]


def test_collector_reuses_metrics_from_its_real_prepared_live_context(prepared_probe, monkeypatch):
    client, csrf = prepared_probe["login"]("ELITE")
    calls = _observe_collector(prepared_probe["a"], monkeypatch)
    collections = _ask_live(client, csrf)

    assert len(calls) == 1
    call = calls[0]
    metrics = _assert_single_live_metrics_read(call)
    assert call["operation"] is not None
    assert metrics["identity_coverage"]["state"] == "PREPARED"
    assert metrics["identity_coverage"]["generation"] == call["operation"].generation
    assert collections["live"]["state"] == "AVAILABLE"
    assert collections["live"]["total"] == metrics["live_confirmed"]
    assert collections["live"]["matches"]
    assert collections == call["result"]


@pytest.mark.parametrize("fault", ["mutated_cohort", "legacy_clone"])
def test_metrics_reuse_does_not_reuse_proof_after_owner_or_cohort_changes(
    prepared_probe, monkeypatch, fault,
):
    a = prepared_probe["a"]
    client, csrf = prepared_probe["login"]("ELITE")
    calls = _observe_collector(a, monkeypatch)
    established = _ask_live(client, csrf)
    assert established["live"]["state"] == "AVAILABLE"
    assert _assert_single_live_metrics_read(calls[0])["identity_coverage"]["state"] == "PREPARED"

    public_summary = a.get_public_home_sports_summary
    origins = []

    def changed_summary():
        summary = public_summary()
        for original, supplied in origins:
            if original is summary:
                return supplied
        assert a._v991_operation_for(summary) is not None
        assert summary["sports_metrics"]["identity_coverage"]["state"] == "PREPARED"
        if fault == "legacy_clone":
            # A copied metrics marker is not ownership of the prepared snapshot.
            supplied = dict(summary)
            assert supplied["sports_metrics"] is summary["sports_metrics"]
        else:
            supplied = summary
            supplied["all_valid_matches"].append(dict(supplied["all_valid_matches"][0]))
        origins.append((summary, supplied))
        return supplied

    monkeypatch.setattr(a, "get_public_home_sports_summary", changed_summary)
    unknown = _ask_live(client, csrf)

    assert len(calls) == 2 and origins
    changed = calls[-1]
    metrics = _assert_single_live_metrics_read(changed)
    assert changed["operation"] is None
    assert metrics["identity_coverage"]["state"] == "UNPREPARED"
    assert metrics is not calls[0]["get_metrics"][0]["result"]
    for collection in ("live", "agenda"):
        assert unknown[collection] == {"state": "UNAVAILABLE", "matches": [], "total": None}
    assert unknown["favorites"] == {"state": "EMPTY", "matches": [], "total": 0, "saved_count": 0}


def _observe_page_builders(a, monkeypatch):
    observed = {"compact": [], "render": [], "trust": []}
    compact = a.v932_safe_dashboard_data
    render = a.render_template
    trust = a.get_v935_customer_trust_context
    prepared_keys = ("v925_calendar", "v925_picks", "v925_odds", "sports_metrics")

    @wraps(compact)
    def observed_compact(*args, **kwargs):
        data, summary = compact(*args, **kwargs)
        observed["compact"].append({
            "data": data, "prepared": {key: data[key] for key in prepared_keys},
        })
        return data, summary

    @wraps(render)
    def observed_render(template, *args, **kwargs):
        if template == "shark.html":
            data = kwargs["data"]
            observed["render"].append({
                "data": data, "prepared": {key: data[key] for key in prepared_keys},
            })
        return render(template, *args, **kwargs)

    @wraps(trust)
    def observed_trust(*args, **kwargs):
        observed["trust"].append((args, kwargs))
        return trust(*args, **kwargs)

    monkeypatch.setattr(a, "v932_safe_dashboard_data", observed_compact)
    monkeypatch.setattr(a, "render_template", observed_render)
    monkeypatch.setattr(a, "get_v935_customer_trust_context", observed_trust)
    return observed


def _assert_page_reuses_compact_values(observed, count):
    assert len(observed["compact"]) == len(observed["render"]) == count
    # The actual SHARK/base templates have no customer-trust consumer. Every
    # remaining presentation value was already prepared by compact context.
    assert observed["trust"] == []
    for compact, rendered in zip(observed["compact"], observed["render"]):
        assert rendered["data"] is compact["data"]
        for key, value in compact["prepared"].items():
            assert rendered["prepared"][key] is value, key


def _assert_closed_timing(response, a):
    header = response.headers["Server-Timing"]
    phases = {name: float(duration) for name, duration in
              re.findall(r"(?:^|, )shark_([a-z_]+);dur=([0-9.]+)", header)}
    assert set(phases) == a._V999_SHARK_PHASES
    assert all(duration >= 0 for duration in phases.values())
    # Parent view and nested assistant phases intentionally overlap. Never add
    # children to their parents when assessing the latency contribution.
    parents = ("input", "sports_context", "admission", "briefing", "provider_state",
               "assistant_context", "assistant_answer", "template")
    assert phases["view_total"] + 1 >= sum(phases[name] for name in parents)
    assert phases["assistant_context"] + 1 >= sum(value for name, value in phases.items()
                                                              if name.startswith("nested_"))
    assert response.headers["X-Nemesis-Shark-Data"] == "db-cache-only"


@pytest.mark.parametrize("path", ["/shark", "/shark-ai"])
def test_full_page_reuses_prepared_values_without_changing_selection_or_admission(
    shark_probe, monkeypatch, path,
):
    client, _ = shark_probe["login"]("ELITE")
    user_id = shark_probe["users"]["ELITE"][0]
    before, saved = shark_probe["quota_count"](user_id), len(snapshots(shark_probe))
    observed = _observe_page_builders(shark_probe["a"], monkeypatch)

    page = client.get(path, base_url="http://127.0.0.1", query_string={
        "q": "pick", "pick": shark_probe["published_pick"],
    })
    assert page.status_code == 200
    _assert_closed_timing(page, shark_probe["a"])
    html = page.get_data(as_text=True)
    form = Form(); form.feed(html)
    assert form.fields["pick_id"] == shark_probe["published_pick"]
    assert form.fields["match_id"] == shark_probe["published_match"]
    assert form.fields["csrf_token"]
    assert shark_probe["published_canary"] in html
    assert shark_probe["draft_canary"] not in html
    assert shark_probe["quota_count"](user_id) == before
    assert len(snapshots(shark_probe)) == saved
    _assert_page_reuses_compact_values(observed, 1)
    assistant = observed["render"][-1]["data"]["shark_assistant"]
    assert set(assistant) == {
        "context", "answer", "openai_configured", "fallback_mode",
        "execution_source", "generation_enabled", "external_verification",
    }
    assert assistant["execution_source"] == "LOCAL" and assistant["generation_enabled"] is False
    assert assistant["context"]["pick"]["odds"] == 1.8
    assert "raw_json" not in assistant["context"]["pick"]
    for marker in ('data-v933-template="shark"', 'data-shark-question-entry="existing-answer-v1"',
                   'data-shark-safe-mode="local-response"', 'data-sports-snapshot='):
        assert marker in html

    denied = client.post(path, base_url="http://127.0.0.1", data={
        **form.fields, "q": "Explica el pronóstico", "csrf_token": "invalid-owned-probe-token",
    })
    assert denied.status_code == 403
    assert shark_probe["quota_count"](user_id) == before
    assert len(snapshots(shark_probe)) == saved
    _assert_page_reuses_compact_values(observed, 1)

    submitted = client.post(path, base_url="http://127.0.0.1", data={
        **form.fields, "q": "Explica el pronóstico",
    })
    assert submitted.status_code == 200, submitted.get_data(as_text=True)
    _assert_closed_timing(submitted, shark_probe["a"])
    assert shark_probe["published_canary"] in submitted.get_data(as_text=True)
    assert shark_probe["quota_count"](user_id) == before + 1
    assert len(snapshots(shark_probe)) == saved + 1
    context = snapshots(shark_probe)[-1]
    assert context["match"]["id"] == shark_probe["published_match"]
    assert context["pick"]["id"] == shark_probe["published_pick"]
    posted_context = observed["render"][-1]["data"]["shark_assistant"]["context"]
    assert posted_context["pick"]["odds"] == 1.8
    if not context.get("truncated"):
        assert context["pick"]["odds"] == 1.8
    _assert_page_reuses_compact_values(observed, 2)

    question = "Mi pregunta <segura> & conservada"
    rejected = client.post(path, base_url="http://127.0.0.1", data={
        **form.fields, "q": question, "match_id": shark_probe["draft_match"],
    })
    assert rejected.status_code == 400
    _assert_closed_timing(rejected, shark_probe["a"])
    recovered = Form(); recovered.feed(rejected.get_data(as_text=True))
    assert recovered.question == question
    assert "match_id" not in recovered.fields and "pick_id" not in recovered.fields
    assert "No se ha descontado" in rejected.get_data(as_text=True)
    assert shark_probe["quota_count"](user_id) == before + 1
    assert len(snapshots(shark_probe)) == saved + 1
    _assert_page_reuses_compact_values(observed, 3)
