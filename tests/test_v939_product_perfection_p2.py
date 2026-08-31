from __future__ import annotations

import re
import threading
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from engines.madrid_time_engine import format_madrid_sync_label
from engines.v934_realtime_sports_engine import (
    build_realtime_snapshot,
    cached_realtime_snapshot,
    invalidate_realtime_cache,
)
from engines.company_intelligence_engine import (
    build_company_intelligence_snapshot,
    load_company_intelligence_memory,
    save_company_intelligence_memory,
)
from engines.continuous_shark_sentinel_engine import run_continuous_sentinel_cycle
from engines.sentinel_autopilot_engine import (
    build_client_copy_audience_contract_snapshot,
    build_customer_trust_icon_contract_snapshot,
    build_madrid_timestamp_presentation_contract_snapshot,
    create_autopilot_task,
    detect_product_quality_contract_issues,
    run_autopilot_scan,
)


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_calendar_collection_reclaims_full_width_without_breaking_mobile_order():
    template = _read("templates/calendar.html")

    assert 'class="v933-rail-flow"' in template
    assert 'data-v939-layout-contract="full-width-continuation"' in template
    assert 'data-v939-layout-contract="context-strip"' in template
    assert template.index('data-v939-layout-contract="full-width-continuation"') < template.index(
        'data-v939-layout-contract="context-strip"'
    )
    assert 'class="v933-two-col"' not in template
    assert template.count("v933-match-grid") == 1


def test_client_quick_actions_continue_outside_the_bounded_rail():
    template = _read("templates/client_app_center.html")
    bounded = template.index('data-v939-layout-contract="bounded-rail"')
    continuation = template.index('data-v939-layout-contract="full-width-continuation"')
    segment = template[continuation:bounded]

    assert continuation < bounded
    assert "Tus accesos rápidos" not in segment
    assert template.count("Tus accesos rápidos") == 1
    assert template.index("Tus accesos rápidos") > continuation


def test_telegram_supporting_content_stays_flat_after_the_rail():
    template = _read("templates/telegram.html")
    bounded = template.index('data-v939-layout-contract="bounded-rail"')
    safety_note = template.index('class="ns-video-safety-note"')
    rail_segment = template[bounded:safety_note]

    assert "Configurar en 3 pasos" in rail_segment
    assert "Telegram extiende la app; no la sustituye" not in template
    assert "Calidad del canal" not in template
    assert 'class="v933-two-col is-balanced"' not in template
    assert "Calidad protegida" in template[safety_note:]


def test_bounded_rail_css_contract_has_desktop_reclaim_and_mobile_collapse():
    css = _read("static/v933-product.css")

    assert ".v933-two-col.is-balanced" in css
    assert ".v933-rail-flow" in css
    assert '[data-v939-layout-contract="context-strip"] { grid-row: 1; }' in css
    assert '[data-v939-layout-contract="full-width-continuation"] { grid-row: 2; }' in css
    assert re.search(
        r"@media \(max-width: 800px\)\s*\{[\s\S]*?"
        r"\.v933-two-col,\.v933-two-col\.is-balanced[^\{]+\{\s*grid-template-columns:\s*1fr;",
        css,
    )


def test_pqv939_004_templates_remain_valid_jinja():
    environment = Environment()
    for path in (
        "templates/calendar.html",
        "templates/client_app_center.html",
        "templates/telegram.html",
    ):
        environment.parse(_read(path))



def _write_trust_contract_fixture(tmp_path: Path, css: str) -> Path:
    _write_copy_contract_fixture(tmp_path)
    (tmp_path / "static" / "v933-product.css").write_text(css, encoding="utf-8")
    (tmp_path / "templates" / "components" / "v933_ui.html").write_text(
        _read("templates/components/v933_ui.html"), encoding="utf-8"
    )
    return tmp_path


def test_pqv939_005_trust_icons_use_direct_child_css_contract():
    css = _read("static/v933-product.css")
    snapshot = build_customer_trust_icon_contract_snapshot(ROOT, "V939")

    assert ".v935-customer-trust-rules > span {" in css
    assert ".v935-customer-trust-rules span {" not in css
    assert ".v935-customer-trust-rules > span:last-child {" in css
    assert snapshot["validation_result"] == "PASS"
    assert snapshot["evidence"]["violations"] == []
    assert detect_product_quality_contract_issues(ROOT, "V939") == []


def test_pqv939_005_regression_opens_p2_and_requires_human_approval(tmp_path):
    broken_css = _read("static/v933-product.css").replace(
        ".v935-customer-trust-rules > span {",
        ".v935-customer-trust-rules span {",
    ).replace(
        ".v935-customer-trust-rules > span:last-child {",
        ".v935-customer-trust-rules span:last-child {",
    )
    fixture_root = _write_trust_contract_fixture(tmp_path, broken_css)
    issues = detect_product_quality_contract_issues(fixture_root, "V939")

    assert len(issues) == 1
    assert issues[0]["id"] == "PQV939-005-CUSTOMER-TRUST-ICON-CONTRACT"
    assert issues[0]["severity"] == "medium"
    task = create_autopilot_task(issues[0])
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True
    assert "static/v933-product.css" in task["likely_files"]

    autopilot = run_autopilot_scan(app_version="V939", project_root=fixture_root)
    assert autopilot["score"] < 10
    assert any(issue["id"] == issues[0]["id"] for issue in autopilot["issues"])
    assert autopilot["dangerous_actions_executed"] is False


def test_pqv939_005_continuous_sentinel_score_reflects_regression(client, app_module, tmp_path):
    broken_css = _read("static/v933-product.css").replace(
        ".v935-customer-trust-rules > span {",
        ".v935-customer-trust-rules span {",
    )
    fixture_root = _write_trust_contract_fixture(tmp_path, broken_css)
    result = run_continuous_sentinel_cycle(
        client,
        app_module.APP_VERSION,
        mode="quick",
        dry_run=True,
        product_quality_root=fixture_root,
    )

    assert result["score"] < 10
    assert any(
        issue["issue_id"] == "PQV939-005-CUSTOMER-TRUST-ICON-CONTRACT"
        for issue in result["issues"]
    )
    assert result["no_code_writes"] is True
    assert result["no_deploy"] is True
    assert result["no_external_calls"] is True


def test_pqv939_005_company_intelligence_persists_learning_only_when_explicit(app_module, tmp_path):
    db_path = tmp_path / "company-intelligence.sqlite"
    snapshot = build_company_intelligence_snapshot(
        ROOT,
        db_path,
        app_module.APP_VERSION,
        environment="test",
    )
    learning = snapshot["product_quality_learning"][0]

    assert learning["issue_id"] == "PQV939-005"
    assert learning["validation_result"] == "PASS"
    assert learning["production_certified"] is False
    assert snapshot["database_written"] is False

    save_company_intelligence_memory(tmp_path, snapshot)
    stored = load_company_intelligence_memory(tmp_path)
    stored_learning = stored["snapshots"][-1]["product_quality_learning"][0]
    assert stored_learning["cause"] == learning["cause"]
    assert stored_learning["solution"] == learning["solution"]
    assert stored_learning["preventive_rule"] == learning["preventive_rule"]


def _write_copy_contract_fixture(tmp_path: Path, *, reintroduce_live_technical_copy: bool = False) -> Path:
    paths = (
        "app.py",
        "static/v933-product.css",
        "static/v934-realtime.js",
        "templates/components/v933_ui.html",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/match_detail.html",
        "templates/admin_dashboard.html",
        "templates/admin_data_center.html",
        "templates/admin_data_trust_center.html",
        "templates/admin_realtime_center.html",
        "engines/madrid_time_engine.py",
        "engines/v934_realtime_sports_engine.py",
    )
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = _read(path)
        if path == "templates/live.html" and reintroduce_live_technical_copy:
            content = content.replace(
                "Los últimos datos confirmados siguen accesibles",
                "DB y caché durante render",
            )
        target.write_text(content, encoding="utf-8")
    return tmp_path


def test_pqv939_006_client_copy_contract_separates_client_and_admin_audiences():
    snapshot = build_client_copy_audience_contract_snapshot(ROOT, "V939")
    engine = _read("engines/v934_realtime_sports_engine.py")
    shared_template = _read("templates/components/v933_ui.html")
    polling = _read("static/v934-realtime.js")
    live_template = _read("templates/live.html")

    assert snapshot["validation_result"] == "PASS"
    assert snapshot["evidence"]["client_visible_hits"] == {}
    assert snapshot["evidence"]["admin_contract"] is True
    assert "Datos confirmados disponibles. La información se mantiene accesible entre actualizaciones." in engine
    assert "Actualización temporalmente no disponible. Se conserva la última información confirmada." in engine
    assert "se conserva el ultimo cache seguro" not in engine
    assert "technical_message if technical else client_message" in shared_template
    assert "var message = technical" in polling
    assert "DB y caché durante render" not in live_template
    assert "Los últimos datos confirmados siguen accesibles" in live_template
    assert detect_product_quality_contract_issues(ROOT, "V939") == []


def test_pqv939_006_realtime_exception_fallback_remains_client_safe():
    cache_key = "pqv939-006-client-copy-fallback"
    invalidate_realtime_cache(cache_key)
    cached_realtime_snapshot(
        cache_key,
        lambda: {"safe_message": "Lectura confirmada", "counts": {}},
        force=True,
    )

    def fail_builder():
        raise RuntimeError("expected_local_test_failure")

    try:
        fallback, cache_state = cached_realtime_snapshot(cache_key, fail_builder, force=True)
        assert cache_state == "stale_fallback"
        assert fallback["safe_message"] == (
            "Actualización temporalmente no disponible. Se conserva la última información confirmada."
        )
        assert "cache" not in fallback["safe_message"].casefold()
        assert "render" not in fallback["safe_message"].casefold()
    finally:
        invalidate_realtime_cache(cache_key)


def test_pqv939_006_regression_opens_p2_and_requires_human_approval(tmp_path):
    fixture_root = _write_copy_contract_fixture(tmp_path, reintroduce_live_technical_copy=True)
    issues = detect_product_quality_contract_issues(fixture_root, "V939")
    issue = next(item for item in issues if item["id"] == "PQV939-006-CLIENT-COPY-AUDIENCE-CONTRACT")

    assert issue["severity"] == "medium"
    assert issue["route"] == "/live"
    assert "technical_terms_visible_in_client_templates" in issue["product_quality_contract"]["evidence"]["violations"]
    task = create_autopilot_task(issue)
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True
    assert "templates/live.html" in task["likely_files"]

    autopilot = run_autopilot_scan(app_version="V939", project_root=fixture_root)
    assert autopilot["score"] < 10
    assert any(item["id"] == issue["id"] for item in autopilot["issues"])
    assert autopilot["dangerous_actions_executed"] is False


def test_pqv939_006_continuous_sentinel_score_reflects_copy_regression(client, app_module, tmp_path):
    fixture_root = _write_copy_contract_fixture(tmp_path, reintroduce_live_technical_copy=True)
    result = run_continuous_sentinel_cycle(
        client,
        app_module.APP_VERSION,
        mode="quick",
        dry_run=True,
        product_quality_root=fixture_root,
    )

    assert result["score"] < 10
    assert any(
        issue["issue_id"] == "PQV939-006-CLIENT-COPY-AUDIENCE-CONTRACT"
        for issue in result["issues"]
    )
    assert result["no_code_writes"] is True
    assert result["no_deploy"] is True
    assert result["no_external_calls"] is True


def test_pqv939_006_company_intelligence_preserves_audience_learning(app_module, tmp_path):
    snapshot = build_company_intelligence_snapshot(
        ROOT,
        tmp_path / "company-intelligence.sqlite",
        app_module.APP_VERSION,
        environment="test",
    )
    learning_by_id = {
        item["issue_id"]: item
        for item in snapshot["product_quality_learning"]
    }
    learning = learning_by_id["PQV939-006"]

    assert learning["validation_result"] == "PASS"
    assert learning["evidence"]["client_visible_hits"] == {}
    assert learning["evidence"]["admin_contract"] is True
    assert learning["production_certified"] is False
    assert snapshot["database_written"] is False

    save_company_intelligence_memory(tmp_path, snapshot)
    stored = load_company_intelligence_memory(tmp_path)
    stored_learning = {
        item["issue_id"]: item
        for item in stored["snapshots"][-1]["product_quality_learning"]
    }["PQV939-006"]
    assert stored_learning["cause"] == learning["cause"]
    assert stored_learning["solution"] == learning["solution"]
    assert stored_learning["preventive_rule"] == learning["preventive_rule"]


def test_pqv939_006_affected_templates_remain_valid_jinja():
    environment = Environment()
    for path in (
        "templates/components/v933_ui.html",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
    ):
        environment.parse(_read(path))


def _visible_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _timestamp_contract_environment() -> Environment:
    environment = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    environment.filters["sync_madrid_label"] = format_madrid_sync_label
    return environment


def _write_timestamp_contract_fixture(tmp_path: Path, *, raw_client_timestamp: bool = False) -> Path:
    paths = (
        "app.py",
        "engines/madrid_time_engine.py",
        "engines/v934_realtime_sports_engine.py",
        "static/v934-realtime.js",
        "templates/components/v933_ui.html",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/match_detail.html",
    )
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = _read(path)
        if path == "templates/components/v933_ui.html" and raw_client_timestamp:
            content = content.replace(
                "{{ raw_sync if technical else client_sync }}",
                "{{ raw_sync }}",
            )
        target.write_text(content, encoding="utf-8")
    return tmp_path


def test_pqv939_007_formatter_and_snapshot_keep_label_and_machine_value_separate():
    raw = "2026-07-22T12:25:21Z"
    label = "22 jul 2026, 14:25 · Madrid"

    assert format_madrid_sync_label(raw) == label
    assert format_madrid_sync_label("2026-07-22T14:25:21+02:00") == label
    assert format_madrid_sync_label("invalid") == "Sin sincronización confirmada"

    snapshot = build_realtime_snapshot({"last_sync": raw})
    assert snapshot["last_safe_sync"] == raw
    assert snapshot["last_safe_sync_label"] == label
    assert snapshot["no_fake_data"] is True


def test_pqv939_007_shared_macros_render_client_label_and_keep_admin_iso():
    raw = "2026-07-22T14:25:21+02:00"
    label = "22 jul 2026, 14:25 · Madrid"
    module = _timestamp_contract_environment().get_template("components/v933_ui.html").module
    payload = {
        "last_safe_sync": raw,
        "last_safe_sync_label": label,
        "counts": {},
        "poll_after_seconds": 180,
    }

    client_html = str(module.realtime_state_bar(payload, "all", False))
    admin_html = str(module.realtime_state_bar(payload, "all", True))
    provider_html = str(module.provider_state(True, raw, "Datos confirmados"))

    assert raw not in _visible_text(client_html)
    assert raw not in _visible_text(provider_html)
    assert label in _visible_text(client_html)
    assert label in _visible_text(provider_html)
    assert raw in _visible_text(admin_html)
    assert f'datetime="{raw}"' in client_html
    assert f'data-v934-last-sync-raw="{raw}"' in client_html
    assert f'data-v939-sync-raw="{raw}"' in provider_html


def test_pqv939_007_api_exposes_label_without_replacing_iso(client, app_module, monkeypatch):
    raw = "2026-07-22T14:25:21+02:00"
    label = format_madrid_sync_label(raw)
    snapshot = build_realtime_snapshot({"last_sync": raw})
    snapshot["cache_state"] = "test"
    monkeypatch.setattr(app_module, "get_v934_realtime_context", lambda: snapshot)

    response = client.get("/api/realtime/sports")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["last_safe_sync"] == raw
    assert payload["last_safe_sync_label"] == label
    assert payload["no_external_calls"] is True


def test_pqv939_007_contract_is_green_and_polling_cannot_restore_raw_iso():
    snapshot = build_madrid_timestamp_presentation_contract_snapshot(ROOT, "V939")

    assert snapshot["validation_result"] == "PASS"
    assert snapshot["status"] == "RESOLVED_LOCALLY"
    assert snapshot["evidence"]["violations"] == []
    assert snapshot["production_certified"] is False
    assert detect_product_quality_contract_issues(ROOT, "V939") == []


def test_pqv939_007_regression_opens_p2_and_requires_human_approval(tmp_path):
    fixture_root = _write_timestamp_contract_fixture(tmp_path, raw_client_timestamp=True)
    issues = detect_product_quality_contract_issues(fixture_root, "V939")
    issue = next(item for item in issues if item["id"] == "PQV939-007-MADRID-TIMESTAMP-PRESENTATION-CONTRACT")

    assert issue["priority"] == "P2"
    assert issue["severity"] == "medium"
    assert issue["route"] == "/"
    assert issue["component"] == "madrid_sync_timestamp_presentation"
    assert "realtime_bar_can_print_raw_iso_to_client" in issue["product_quality_contract"]["evidence"]["violations"]

    task = create_autopilot_task(issue)
    assert task["status"] == "pending_approval"
    assert task["safe_fix_plan"]["requires_approval"] is True
    assert "templates/components/v933_ui.html" in task["likely_files"]

    autopilot = run_autopilot_scan(app_version="V939", project_root=fixture_root)
    assert autopilot["score"] < 10
    assert any(item["id"] == issue["id"] for item in autopilot["issues"])
    assert autopilot["dangerous_actions_executed"] is False


def test_pqv939_007_continuous_sentinel_detects_raw_client_iso(client, app_module, tmp_path):
    fixture_root = _write_timestamp_contract_fixture(tmp_path, raw_client_timestamp=True)
    result = run_continuous_sentinel_cycle(
        client,
        app_module.APP_VERSION,
        mode="quick",
        dry_run=True,
        product_quality_root=fixture_root,
    )

    assert result["score"] < 10
    assert any(
        issue["issue_id"] == "PQV939-007-MADRID-TIMESTAMP-PRESENTATION-CONTRACT"
        for issue in result["issues"]
    )
    assert result["no_code_writes"] is True
    assert result["no_deploy"] is True
    assert result["no_external_calls"] is True


def test_pqv939_007_company_intelligence_preserves_local_learning(app_module, tmp_path):
    snapshot = build_company_intelligence_snapshot(
        ROOT,
        tmp_path / "company-intelligence.sqlite",
        app_module.APP_VERSION,
        environment="test",
    )
    learning = {
        item["issue_id"]: item
        for item in snapshot["product_quality_learning"]
    }["PQV939-007"]

    assert learning["status"] == "RESOLVED_LOCALLY"
    assert learning["qa_result"] == "PASS"
    assert learning["impact"]
    assert learning["evaluated_at_madrid"]
    assert learning["version"] == app_module.APP_VERSION
    assert learning["production_certified"] is False
    assert snapshot["database_written"] is False

    save_company_intelligence_memory(tmp_path, snapshot)
    stored = load_company_intelligence_memory(tmp_path)
    stored_learning = {
        item["issue_id"]: item
        for item in stored["snapshots"][-1]["product_quality_learning"]
    }["PQV939-007"]
    assert stored_learning["cause"] == learning["cause"]
    assert stored_learning["solution"] == learning["solution"]
    assert stored_learning["preventive_rule"] == learning["preventive_rule"]


def test_pqv939_007_affected_templates_remain_valid_jinja():
    environment = Environment()
    for path in (
        "templates/components/v933_ui.html",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/match_detail.html",
        "templates/admin_realtime_center.html",
    ):
        environment.parse(_read(path))


def test_realtime_cache_single_flight_prevents_duplicate_builds():
    cache_key = "qa:performance-p0-single-flight"
    invalidate_realtime_cache(cache_key)
    workers = 6
    barrier = threading.Barrier(workers)
    counter_lock = threading.Lock()
    result_lock = threading.Lock()
    builds = {"count": 0}
    statuses = []
    payloads = []

    def builder():
        with counter_lock:
            builds["count"] += 1
        time.sleep(0.05)
        return {"ok": True, "source": "LOCAL_QA"}

    def worker():
        barrier.wait()
        payload, status = cached_realtime_snapshot(
            cache_key,
            builder,
            ttl_seconds=60,
        )
        with result_lock:
            statuses.append(status)
            payloads.append(payload)

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)

        assert all(not thread.is_alive() for thread in threads)
        assert builds["count"] == 1
        assert statuses.count("refreshed") == 1
        assert statuses.count("hit") == workers - 1
        assert all(payload == {"ok": True, "source": "LOCAL_QA"} for payload in payloads)
    finally:
        invalidate_realtime_cache(cache_key)
