"""Real LOCAL SAFE Picks equivalence after removing an unconsumed trust scan.

The control is the published route from 23f155e, with its original template.
Both paths retain the actual login, SQLite reads, current membership gates,
fixture preparation, fresh metrics, odds checks and template rendering.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET

from jinja2 import ChoiceLoader, DictLoader
import pytest

from test_client_view_preparation import same_evaluation
from test_picks_read_path_efficiency import (
    _owned_supervisor, assert_same_with_elapsed_age, business_state, capture,
    prepared_probe, shark_probe,
)


BASELINE_COMMIT = "23f155e82f8d91982e996f95774e26ed37c4fc24"
# Exact published function text, with CRLF normalized to LF and one final LF.
BASELINE_SOURCE = '''def picks_page():
    data, summary = v932_safe_dashboard_data(request.path, compact=True, _picks_view=True)
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    membership = normalize_role(user.get("membership") or user.get("role") or "FREE")
    all_current_picks = list(summary.get("valid_active_picks") or [])
    safe_current_picks = get_safe_picks_context(all_current_picks).get("picks") or []
    data["picks"] = _v999_authorized_snapshot_picks(safe_current_picks, user, active_only=True)
    data["locked_pick_count"] = sum(
        1 for item in safe_current_picks
        if not _client_pick_membership_allows(membership, item)
    )
    visible_history = published_picks_for_user(user, limit=200)
    closed_statuses = {"won", "lost", "void", "win", "loss", "ganado", "perdido", "nulo", "settled", "graded"}
    closed_count = sum(
        1 for item in visible_history
        if str(item.get("result_status") or item.get("status") or "").strip().lower() in closed_statuses
    )
    data["pick_stats"] = {"closed": closed_count, "graded": closed_count}
    data["v925_picks"] = get_safe_picks_context(data["picks"])
    data["v925_odds"] = get_safe_odds_context(data["picks"])
    data["v934_realtime"] = get_realtime_safe_picks_context(summary)
    # Both contexts describe the same request-owned evaluation.
    data["v934_odds"] = _v934_odds_context_from_snapshot(data["v934_realtime"])
    data["v935_customer_trust"] = get_v935_customer_trust_context(summary)
    data["pick_readiness"], data["pick_watchlist"] = client_pick_readiness(
        summary,
        active_count=len(data["v925_picks"].get("picks") or []),
        locked_count=data["locked_pick_count"],
    )
    return render_template("picks.html", data=data)
'''
BASELINE_SOURCE_SHA256 = "c20e3f52043b45113a9fef662025b88afd472b2f62a8bb6dd2a916858080f630"
BASELINE_TEMPLATE_SHA256 = "f2c80ce1ef971ab6c73a33d6ec990d36684aa666b4de99494c988d5bd3a12752"


@contextmanager
def published_page(app, monkeypatch):
    """Execute the pinned original route and full original template in memory."""
    assert hashlib.sha256(BASELINE_SOURCE.encode()).hexdigest() == BASELINE_SOURCE_SHA256
    namespace = {}
    exec(compile(BASELINE_SOURCE, "<published-23f155e-picks>", "exec"), app.__dict__, namespace)
    current = (Path(__file__).resolve().parents[1] / "templates/picks.html").read_bytes()
    anchor = b"{% set realtime = data.get('v934_realtime') or {} %}\n\n"
    alias = b"{% set customer_trust = data.get('v935_customer_trust') or {} %}\n"
    assert current.count(anchor) == 1
    published = current.replace(anchor, anchor[:-1] + alias, 1)
    # A new unrelated template change must not silently alter this control.
    assert hashlib.sha256(published).hexdigest() == BASELINE_TEMPLATE_SHA256
    environment = app.app.jinja_env
    loader = ChoiceLoader([DictLoader({"picks.html": published.decode("utf-8")}), environment.loader])
    try:
        with monkeypatch.context() as control:
            control.setitem(app.app.view_functions, "picks_page", namespace["picks_page"])
            control.setattr(environment, "loader", loader)
            environment.cache.clear()
            yield
    finally:
        environment.cache.clear()


def owned_business_state(probe):
    state = business_state(probe["path"])
    # Also protect account, favorite and payment/membership rows. Session login
    # happens before this snapshot; no production store is ever opened here.
    with sqlite3.connect(probe["path"]) as connection:
        available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("users", "favorites", "subscription_accounts", "subscription_events",
                      "stripe_subscriptions", "payment_webhook_events"):
            if table in available:
                records = connection.execute('SELECT * FROM "' + table + '" ORDER BY rowid').fetchall()
                state[table] = hashlib.sha256(json.dumps(records, default=str, sort_keys=True).encode()).hexdigest()
    return state


def measured_page(app, client, calls, **kwargs):
    calls.clear()
    with capture(app) as contexts:
        started = datetime.now(timezone.utc)
        response = client.get("/picks", base_url="http://127.0.0.1", **kwargs)
        ended = datetime.now(timezone.utc)
    assert response.status_code == 200 and len(contexts) == 1
    return response, contexts[0], len(calls), (started, ended)


def compare(probe, monkeypatch, principal, **kwargs):
    app = probe["a"]
    client = app.app.test_client() if principal == "ANONYMOUS" else probe["login"](principal)[0]
    calls = []
    original = app.get_v935_customer_trust_context

    def observed_trust(*args, **kw):
        calls.append(1)
        return original(*args, **kw)

    monkeypatch.setattr(app, "get_v935_customer_trust_context", observed_trust)
    # Warm the real cache belonging to this fixture, without supplying a fake
    # summary, identity, permission, freshness result or clock.
    assert client.get("/picks", base_url="http://127.0.0.1").status_code == 200
    before = owned_business_state(probe)
    candidate, data, current_calls, window = measured_page(app, client, calls, **kwargs)
    with published_page(app, monkeypatch):
        baseline, prior, baseline_calls, old_window = measured_page(app, client, calls, **kwargs)
    elapsed = math.ceil((old_window[1] - window[0]).total_seconds()) + 1

    assert current_calls == 0 and baseline_calls == 1
    assert candidate.get_data() == baseline.get_data()
    assert set(prior) == set(data) | {"v935_customer_trust"}
    # These are the complete values used by the actual Picks template, plus
    # the authorized records, principal and locked count that feed them.
    for key in ("picks", "locked_pick_count", "pick_stats", "v925_picks", "v925_odds",
                "pick_readiness", "pick_watchlist", "session_user"):
        assert_same_with_elapsed_age(data[key], prior[key], elapsed)
    left, right = deepcopy(data["sports_metrics"]), deepcopy(prior["sports_metrics"])
    if left["generated_at_madrid"] != right["generated_at_madrid"]:
        same_evaluation(left["generated_at_madrid"], right["generated_at_madrid"], (window, old_window))
        left.pop("generated_at_madrid")
        right.pop("generated_at_madrid")
    assert left == right
    assert owned_business_state(probe) == before
    text = candidate.get_data(as_text=True)
    assert probe["draft_canary"] not in text
    assert probe["draft_pick"] not in {str(pick.get("id")) for pick in data["picks"]}
    if principal != "ELITE":
        assert probe["published_canary"] not in text
        assert probe["published_pick"] not in {str(pick.get("id")) for pick in data["picks"]}
    print("PICKS_UNUSED_TRUST_EQUIVALENCE " + json.dumps({
        "baseline_commit": BASELINE_COMMIT, "principal": principal,
        "trust_calls_candidate": current_calls, "trust_calls_baseline": baseline_calls,
        "HTML_byte_equal": True, "consumed_contexts_equal": True,
        "business_tables_unchanged": True,
    }))
    return data


if _owned_supervisor:
    @pytest.mark.parametrize("principal", ("ANONYMOUS", "FREE", "PRO", "ELITE"))
    def test_picks_keeps_published_and_private_boundaries_without_unused_scan(prepared_probe, monkeypatch, principal):
        data = compare(prepared_probe, monkeypatch, principal)
        if principal == "ELITE":
            assert prepared_probe["published_pick"] in {str(pick.get("id")) for pick in data["picks"]}
        else:
            assert data["locked_pick_count"] > 0

    @pytest.mark.parametrize("principal", ("ANONYMOUS", "ELITE"))
    def test_empty_owned_store_keeps_real_empty_state(prepared_probe, monkeypatch, principal):
        probe = prepared_probe
        # Delete only rows in this disposable fixture to exercise the actual
        # empty SQL source and ordinary summary/cache path.
        with sqlite3.connect(probe["path"]) as connection:
            connection.execute("DELETE FROM picks")
            connection.execute("DELETE FROM matches")
        probe["a"].invalidate_v934_realtime_cache()
        data = compare(probe, monkeypatch, principal)
        assert data["picks"] == [] and data["pick_watchlist"] == []
        assert data["pick_readiness"]["state"] == "waiting_for_matches"
        assert data["sports_metrics"]["matches_available"] == 0

    @pytest.mark.parametrize("principal", ("ANONYMOUS", "ELITE"))
    def test_existing_locked_read_guard_and_diagnostics_remain_active(prepared_probe, monkeypatch, principal):
        probe = prepared_probe
        app = probe["a"]
        for name in ("v931_record_client_route_issue", "v932_record_authenticated_issue"):
            original = getattr(app, name)

            def isolated_writer(*args, _original=original, **kwargs):
                with monkeypatch.context() as owned:
                    owned.setattr(app, "BASE_DIR", probe["path"].parent)
                    return _original(*args, **kwargs)

            monkeypatch.setattr(app, name, isolated_writer)
        data = compare(probe, monkeypatch, principal,
                       environ_overrides={"nemesis.v932.database_locked": True})
        assert data["sports_metrics"]["scope"] == "unprepared_observations"
        assert data["sports_metrics"]["matches_available"] == 0
        assert data["picks"] == [] and data["pick_watchlist"] == []
        issues_path = probe["path"].parent / "data/runtime/sentinel_client_route_issues.json"
        issues = json.loads(issues_path.read_text(encoding="utf-8"))["issues"]
        assert any(row["route"] == "/picks" and row["count"] == 2 for row in issues)

else:
    def test_unused_picks_trust_contracts_in_original_guarded_process(tmp_path):
        """The standard suite must run all eight real supervised HTTP cases."""
        root = Path(__file__).resolve().parents[1]
        runner = root / "tools/check_local_candidate.py"
        bootstrap = (
            "import platform,runpy,sys;platform.uname();platform.platform();"
            "sys.argv=[sys.argv[1],sys.argv[2],'-s','--tb=short'];"
            "runpy.run_path(sys.argv[0],run_name='__main__')"
        )
        env = dict(os.environ, PYTEST_ADDOPTS="", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                   PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [sys.executable, "-B", "-c", bootstrap, str(runner), str(Path(__file__).resolve())],
            cwd=root, env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180,
        )
        (tmp_path / "guarded.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (tmp_path / "guarded.stderr.txt").write_text(result.stderr, encoding="utf-8")
        assert result.returncode == 0, (result.stdout[-12000:], result.stderr[-2000:])
        outputs = [line.removeprefix("QA_OUTPUT ") for line in result.stdout.splitlines() if line.startswith("QA_OUTPUT ")]
        boundaries = [line.removeprefix("BOUNDARY_EVENTS ") for line in result.stdout.splitlines() if line.startswith("BOUNDARY_EVENTS ")]
        assert len(outputs) == len(boundaries) == 1 and ast.literal_eval(boundaries[0]) == []
        output = Path(outputs[0]).resolve()
        assert output.is_relative_to((root / "data/local_dev").resolve())
        assert output.name.startswith("candidate-") and not output.is_symlink()
        suite = ET.parse(output / "result.xml").find("testsuite")
        assert suite is not None and suite.attrib["tests"] == "8"
        assert all(suite.attrib[key] == "0" for key in ("failures", "errors", "skipped"))
        print("PICKS_UNUSED_TRUST_STANDARD_PROOF " + json.dumps({
            "actual_HTTP_cases": 8, "failures": 0, "errors": 0, "skips": 0,
            "boundary_events": [], "guarded_output": str(output),
        }))
