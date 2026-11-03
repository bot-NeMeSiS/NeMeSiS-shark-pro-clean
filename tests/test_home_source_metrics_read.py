"""Home keeps prepared sections and fresh consumer metrics, with real owned SQL.

Run through the original LOCAL SAFE supervisor. Only the disposable database
binding is changed by the fixture; App/getters/normalizers/authorization stay real.
The profiler observes real calls. Its one mutation case changes an owned in-memory
row after preparation to exercise C3, never the database or a function binding.
"""

from contextlib import contextmanager
from pathlib import Path
import sys

from flask import session, template_rendered
import pytest

from v991_api_prepare_only_cases import Runtime, digest


_ROLES = ("anonymous", "free", "pro", "elite", "admin")
_STATES = ("upcoming", "live", "empty")
_ROW_FIELDS = (
    "id", "match_id", "external_id", "source", "provider", "competition_key",
    "competition_id", "competition_name", "league_name", "country", "season",
    "home_team", "away_team", "home_team_id", "away_team_id", "match_date",
    "kickoff_iso", "kickoff_time", "match_time", "status", "status_short",
    "home_score", "away_score", "score", "minute", "market", "pick_type",
    "selection", "odds", "bookmaker", "membership_required", "reasoning",
    "created_at", "updated_at", "published_at", "last_synced_at", "live_updated_at",
    "provider_updated_at", "raw_json", "payload_json",
)


@pytest.fixture
def owned_home(monkeypatch, tmp_path):
    a = sys.modules.get("app")
    assert a is not None, "Use tools/check_local_candidate.py before collecting this file"
    assert a.local_safe_mode_enabled()
    repo = Path(__file__).resolve().parents[1]
    assert Path(a.__file__).resolve() == repo / "app.py"
    assert tmp_path.resolve().is_relative_to(Path(a.LOCAL_SAFE_DATA_DIR).resolve())
    database = (tmp_path / "home-source-metrics.sqlite").resolve()
    assert not database.exists()
    monkeypatch.setattr(a, "DB_PATH", str(database))
    monkeypatch.setattr(a, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(a, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(a, "APP_INITIALIZED", False)
    a.seed_core()
    runtime = Runtime(a, repo, database, tmp_path.resolve(), [])
    try:
        yield runtime
    finally:
        runtime.invalidate()


@contextmanager
def _captured(a):
    rendered = []
    def receive(sender, template, context, **kwargs):
        user = context.get("current_user") or {}
        principal = {"id": str(user.get("id") or ""), "role": str(user.get("role") or "")}
        rendered.append((template.name, context.get("data") or {}, principal))
    template_rendered.connect(receive, a.app, weak=False)
    try:
        yield rendered
    finally:
        template_rendered.disconnect(receive, a.app)


def _assert_principal(principal, role):
    if role == "anonymous":
        assert principal["id"] == "", "anonymous Home must have no authenticated ID"
    else:
        assert principal["id"] == "prepare-only-" + role, "real owned Home principal ID"
        assert principal["role"] == role.upper(), "real owned Home principal role"


@contextmanager
def _observed(a, *, mutate_after_finish=False):
    codes = {getattr(a, name).__code__: name for name in (
        "get_public_home_sports_summary", "_v991_finish_summary",
        "_v991_prepare_summary_operation", "build_sports_home_sections",
        "build_sports_metrics_contract",
    )}
    trace = {"metrics": [], "homes": [], "prepares": 0, "getter_modes": [],
             "getter_callers": [], "finishes": [], "mutation": None}
    previous = sys.getprofile()
    def observe(frame, event, arg):
        name = codes.get(frame.f_code)
        if name is None:
            return
        acceptance = bool(a._v991_cache_acceptance.get())
        if event == "call":
            if name == "get_public_home_sports_summary":
                trace["getter_modes"].append((frame.f_locals.get("_prepare_only"),
                                              frame.f_locals.get("_home_only")))
                trace["getter_callers"].append(frame.f_back.f_code.co_name if frame.f_back else "")
            if not acceptance:
                caller = frame.f_back.f_code.co_name if frame.f_back else ""
                if name == "build_sports_metrics_contract":
                    summary = frame.f_locals["summary"]
                    consumer = (frame.f_back.f_back.f_code.co_name
                                if caller == "get_sports_metrics_contract" and frame.f_back.f_back
                                else caller)
                    trace["metrics"].append({"caller": caller, "summary": summary,
                                             "consumer": consumer,
                                             "operation": a._v991_operation_for(summary)})
                elif name == "build_sports_home_sections":
                    trace["homes"].append(caller)
                elif name == "_v991_prepare_summary_operation":
                    trace["prepares"] += 1
        if event == "return" and name == "_v991_finish_summary" and isinstance(arg, tuple):
            summary, operation = arg
            trace["finishes"].append((summary, operation))
            if mutate_after_finish and trace["mutation"] is None:
                row = next(item for item in summary["all_valid_matches"]
                           if item.get("id") == "af-901001")
                before = operation.snapshot.context_for(row).state
                row["home_canonical_team_id"] = "qa-home-changed-after-finish"
                trace["mutation"] = {
                    "summary": summary, "operation": operation, "row": row,
                    "before": before, "after": operation.snapshot.context_for(row).state,
                    "same_operation": a._v991_operation_for(summary) is operation,
                }
    sys.setprofile(observe)
    try:
        yield trace
    finally:
        sys.setprofile(previous)


def _page(runtime, role, *, mutate=False):
    a = runtime.app
    with runtime.bounded("owned Home " + role), _captured(a) as rendered, _observed(
        a, mutate_after_finish=mutate,
    ) as trace:
        response = runtime.clients[role].get("/", base_url="http://localhost")
        body = response.get_data()
    assert response.status_code == 200
    names = [name for name, _data, _principal in rendered]
    assert names == ["home.html"]
    _assert_principal(rendered[-1][2], role)
    trace["principal"] = dict(rendered[-1][2])
    marker = b'data-v933-template="home"' in body
    assert marker
    return rendered[-1][1], trace, body


@contextmanager
def _principal_context(runtime, role):
    a = runtime.app
    with runtime.clients[role].session_transaction() as stored:
        principal_state = dict(stored)
    with a.app.test_request_context(
        "/", base_url="http://localhost",
    ):
        session.update(principal_state)
        user = a.current_session_user() or {}
        principal = {"id": str(user.get("id") or ""), "role": str(user.get("role") or "")}
        _assert_principal(principal, role)
        yield principal


def _full_control(runtime, role):
    """Independent FULL getter/builder, then default alerts outside the observer."""
    a = runtime.app
    with runtime.bounded("Home FULL control " + role), _principal_context(runtime, role) as principal:
        with _observed(a) as trace:
            summary = a.get_public_home_sports_summary()
            assert "sports_home" in summary and "sports_metrics" in summary
            data = a.home_light_data(summary, include_payments=False)
            data["home_matchday"] = a.home_matchday_context(summary)
            data["v925_picks"] = a.get_safe_picks_context(data.get("picks") or [])
            with _captured(a) as rendered:
                a.render_template("home.html", data=data)
            names = [name for name, _data, _principal in rendered]
            assert names == ["home.html"]
            _assert_principal(rendered[-1][2], role)
        default_alerts = a.build_client_alerts(limit=3)
        # Preserve Home's existing no-personal-alerts gate for an actual guest.
        expected_alerts = default_alerts if principal["id"] else []
    return rendered[-1][1], trace, summary, expected_alerts


def _same(left, right, label):
    # Assertion output is hashes/labels only, never a template context or HTML.
    assert digest(left) == digest(right), label


def _rows(items):
    return [{key: row[key] for key in _ROW_FIELDS if key in row} for row in items or []]


def _compare_sports(actual, expected):
    # Every metric field, including complete sports_quality/coverage, is tested.
    _same(actual["sports_metrics"], expected["sports_metrics"], "main complete metrics")
    _same(actual["home_summary"]["sports_metrics"],
          expected["home_summary"]["sports_metrics"], "home_summary complete metrics")
    for root in ("home_summary", "match_hub"):
        home, control = actual[root]["sports_home"], expected[root]["sports_home"]
        for key in ("contract", "identity_state", "quality", "counts", "unknown_quality", "rules"):
            _same(home.get(key), control.get(key), root + ":" + key)
        for lane in ("live_now", "important_today", "favorites", "upcoming", "recent_results", "ranked"):
            _same(_rows(home.get(lane)), _rows(control.get(lane)), root + ":" + lane)
    for lane in ("available_matches", "upcoming_matches", "picks", "favorites"):
        _same(_rows(actual.get(lane)), _rows(expected.get(lane)), lane)
    for lane in ("valid_matches_today", "upcoming_matches", "live_matches", "finished_matches",
                 "valid_matches_available", "picks", "favorites"):
        _same(_rows(actual["home_summary"].get(lane)),
              _rows(expected["home_summary"].get(lane)), "home_summary:" + lane)
    _same(actual["home_summary"]["counts"], expected["home_summary"]["counts"], "summary counts")
    _same(_rows(actual["v925_picks"].get("picks")),
          _rows(expected["v925_picks"].get("picks")), "normalized permitted picks")


def _assert_permissions(data, body, role, state):
    allowed = {"anonymous": set(), "free": set(), "pro": {"prepare-pick-0"},
               "elite": {"prepare-pick-0", "prepare-pick-1"},
               "admin": {"prepare-pick-0", "prepare-pick-1"}}[role]
    if state == "empty":
        allowed = set()
    for picks in (data.get("picks"), data["home_summary"].get("picks"),
                  data["v925_picks"].get("picks")):
        identifiers = {str(item["id"]) for item in picks or []}
        assert identifiers <= allowed, "permitted Home advice IDs"
        for item in picks or []:
            assert float(item["odds"]) == {"prepare-pick-0": 1.83, "prepare-pick-1": 2.14}[item["id"]]
            assert item["source"] == "The Odds API"
    for hidden in {"prepare-pick-0", "prepare-pick-1"} - allowed:
        hidden_present = hidden.encode() in body
        assert not hidden_present, "unpermitted advice ID in Home"


@pytest.mark.parametrize("role,state", [(role, state) for role in _ROLES for state in _STATES],
                         ids=[role + "-" + state for role in _ROLES for state in _STATES])
def test_home_has_two_fresh_consumer_metrics_and_full_output_parity(owned_home, role, state):
    r, a = owned_home, owned_home.app
    r.seed(live=state == "live", empty=state == "empty")
    before = r.table_hashes()
    data, trace, body = _page(r, role)
    # Drop only the source-finalization metric; retain both fresh consumers and
    # the historical FULL read performed by signed-in client alerts.
    prepared_metrics = len(trace["metrics"])
    signed_in = bool(trace["principal"]["id"])
    source_metrics = sum(record["caller"] == "_v991_finish_summary" for record in trace["metrics"])
    assert source_metrics == 0, "Home source must not build a discarded prepared metric"
    assert prepared_metrics == 2 + int(signed_in), "two consumers plus historical signed-in alerts"
    assert sum(record["consumer"] == "_v931_legacy_home_summary" for record in trace["metrics"]) == 1
    assert sum(record["consumer"] == "home_light_data" for record in trace["metrics"]) == 1
    assert trace["getter_callers"].count("build_client_alerts") == int(signed_in)
    assert trace["prepares"] == 1
    assert trace["homes"].count("_v991_finish_summary") == 1
    assert all(record["operation"] is trace["finishes"][0][1] for record in trace["metrics"])
    assert all(record["caller"] != "_v991_finish_summary" for record in trace["metrics"])
    expected, control, source, default_alerts = _full_control(r, role)
    assert control["getter_modes"] == [(False, False)] * (1 + int(signed_in)), "default getters remain FULL"
    assert control["prepares"] == 1
    assert len(control["metrics"]) == prepared_metrics + 1
    assert control["getter_callers"].count("build_client_alerts") == int(signed_in)
    assert sum(record["caller"] == "_v991_finish_summary" for record in control["metrics"]) == 1
    assert source["sports_home"]["identity_state"] == "PREPARED"
    _compare_sports(data, expected)
    _same(data.get("client_alerts"), expected.get("client_alerts"), "Home alerts parity")
    _same(data.get("client_alerts"), default_alerts, "independent default alerts for actual principal")
    _assert_permissions(data, body, role, state)
    assert r.table_hashes() == before


def test_home_metrics_recheck_mutated_original_without_repreparing(owned_home):
    r, a = owned_home, owned_home.app
    r.seed(live=True)
    before = r.table_hashes()
    data, trace, _body = _page(r, "anonymous", mutate=True)
    prepared_metrics = len(trace["metrics"])
    assert prepared_metrics == 2
    assert trace["prepares"] == 1 and len(trace["finishes"]) == 1
    mutation = trace["mutation"]
    assert mutation is not None and mutation["before"] == "RESOLVED"
    assert mutation["after"] == "UNKNOWN_IDENTITY_CHANGED" and mutation["same_operation"]
    assert all(record["summary"] is mutation["summary"]
               and record["operation"] is mutation["operation"] for record in trace["metrics"])
    for metrics in (data["sports_metrics"], data["home_summary"]["sports_metrics"]):
        assert metrics["identity_coverage"]["state"] == "PREPARED"
        assert metrics["matches_today"] == metrics["matches_available"] == metrics["live_confirmed"] == 3
    # The mutation was only the original request's memory, not stored/cache data.
    _control_data, control, fresh, _default_alerts = _full_control(r, "anonymous")
    assert control["getter_modes"] == [(False, False)] and control["prepares"] == 1
    assert fresh["sports_metrics"]["matches_available"] == 2
    assert fresh["sports_metrics"]["identity_coverage"]["state"] == "PREPARED"
    assert r.table_hashes() == before
