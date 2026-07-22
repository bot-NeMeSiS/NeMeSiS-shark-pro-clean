from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment
from engines.v934_realtime_sports_engine import (
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
    segment = template[bounded:continuation]

    assert continuation > bounded
    assert "Tus accesos rápidos" not in segment
    assert template.count("Tus accesos rápidos") == 1
    assert template.index("Tus accesos rápidos") > continuation


def test_telegram_supporting_blocks_form_a_balanced_pair_after_the_rail():
    template = _read("templates/telegram.html")
    bounded = template.index('data-v939-layout-contract="bounded-rail"')
    balanced = template.index('data-v939-layout-contract="balanced-pair"')
    rail_segment = template[bounded:balanced]
    pair_segment = template[balanced:]

    assert "Configurar en 3 pasos" in rail_segment
    assert "Telegram extiende la app; no la sustituye" not in rail_segment
    assert "Calidad del canal" not in rail_segment
    assert 'class="v933-two-col is-balanced"' in template
    assert "Telegram extiende la app; no la sustituye" in pair_segment
    assert "Calidad del canal" in pair_segment


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
        "static/v933-product.css",
        "static/v934-realtime.js",
        "templates/components/v933_ui.html",
        "templates/home.html",
        "templates/client_app_center.html",
        "templates/calendar.html",
        "templates/live.html",
        "templates/picks.html",
        "templates/shark.html",
        "templates/admin_dashboard.html",
        "templates/admin_data_center.html",
        "templates/admin_data_trust_center.html",
        "templates/admin_realtime_center.html",
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
