"""Actual Picks HTML/authorization equivalence against published176a6eef route."""
from pathlib import Path
import pytest
from test_picks_read_path_efficiency import (
    _owned_supervisor, prepared_probe, shark_probe, measured_page,
    business_state, assert_same_with_elapsed_age,
)

PUBLISHED_BASE = "176a6eef4852bb2471011fda893845240232aade"
PUBLISHED_ROUTE_SOURCE = 'def picks_page():\n    data, summary = v932_safe_dashboard_data(request.path, compact=True, _picks_view=True)\n    user = current_session_user() or {"membership": "FREE", "role": "FREE"}\n    membership = normalize_role(user.get("membership") or user.get("role") or "FREE")\n    all_current_picks = list(summary.get("valid_active_picks") or [])\n    safe_current_picks = get_safe_picks_context(all_current_picks).get("picks") or []\n    data["picks"] = _v999_authorized_snapshot_picks(safe_current_picks, user, active_only=True)\n    data["locked_pick_count"] = sum(\n        1 for item in safe_current_picks\n        if not _client_pick_membership_allows(membership, item)\n    )\n    visible_history = published_picks_for_user(user, limit=200)\n    closed_statuses = {"won", "lost", "void", "win", "loss", "ganado", "perdido", "nulo", "settled", "graded"}\n    closed_count = sum(\n        1 for item in visible_history\n        if str(item.get("result_status") or item.get("status") or "").strip().lower() in closed_statuses\n    )\n    data["pick_stats"] = {"closed": closed_count, "graded": closed_count}\n    data["v925_picks"] = get_safe_picks_context(data["picks"])\n    data["v925_odds"] = get_safe_odds_context(data["picks"])\n    data["v934_realtime"] = get_realtime_safe_picks_context(summary)\n    # Both contexts describe the same request-owned evaluation.\n    data["v934_odds"] = _v934_odds_context_from_snapshot(data["v934_realtime"])\n    data["v935_customer_trust"] = get_v935_customer_trust_context(summary)\n    data["pick_readiness"], data["pick_watchlist"] = client_pick_readiness(\n        summary,\n        active_count=len(data["v925_picks"].get("picks") or []),\n        locked_count=data["locked_pick_count"],\n    )\n    return render_template("picks.html", data=data)\n'


def published_route(app):
    # Defining the exact old function neither registers a route nor replaces any
    # principal/SQL/builder results. Flask's real request guards still run.
    local = {}
    exec(compile(PUBLISHED_ROUTE_SOURCE, "<published-picks-176a6eef>", "exec"), app.__dict__, local)
    return local["picks_page"]


if _owned_supervisor:
    @pytest.mark.parametrize("principal", ("ANONYMOUS", "FREE", "PRO", "ELITE"))
    def test_picks_omits_unrendered_realtime_work_with_identical_html_and_authorization(prepared_probe, monkeypatch, principal):
        probe = prepared_probe
        app = probe["a"]
        client = app.app.test_client() if principal == "ANONYMOUS" else probe["login"](principal)[0]
        assert client.get("/picks", base_url="http://127.0.0.1").status_code == 200
        before = business_state(probe["path"])
        candidate, data, calls = measured_page(app, client)
        with monkeypatch.context() as control:
            control.setitem(app.app.view_functions, "picks_page", published_route(app))
            previous, old_data, old_calls = measured_page(app, client)
        assert candidate.get_data() == previous.get_data()
        for key in ("picks", "locked_pick_count", "pick_stats", "v925_picks", "v925_odds", "pick_readiness", "pick_watchlist"):
            assert_same_with_elapsed_age(data[key], old_data[key], 5)
        assert data["sports_metrics"] == old_data["sports_metrics"]
        assert old_calls["_v991_realtime_projection"] == 1
        assert calls["_v991_realtime_projection"] == 0
        assert calls["_v991_prepare_summary_operation"] == old_calls["_v991_prepare_summary_operation"] == 1
        assert "v934_realtime" in old_data and "v934_odds" in old_data
        assert "v934_realtime" not in data and "v934_odds" not in data
        html = candidate.get_data(as_text=True)
        assert probe["draft_canary"] not in html
        if principal != "ELITE":
            assert probe["published_canary"] not in html
        assert business_state(probe["path"]) == before


def test_picks_literal_template_closure_does_not_consume_removed_contexts():
    from jinja2 import Environment, FileSystemLoader, meta
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1]/"templates")))
    pending, seen = ["picks.html"], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        source, unused, unused = env.loader.get_source(env, name)
        assert "v934_realtime" not in source and "v934_odds" not in source, name
        for dependency in meta.find_referenced_templates(env.parse(source)):
            assert dependency is not None, (name, "dynamic template dependency requires review")
            pending.append(dependency)
    assert "base.html" in seen and "components/v933_ui.html" in seen
