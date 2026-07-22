from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment
from engines.company_intelligence_engine import (
    build_company_intelligence_snapshot,
    load_company_intelligence_memory,
    save_company_intelligence_memory,
)
from engines.continuous_shark_sentinel_engine import run_continuous_sentinel_cycle
from engines.sentinel_autopilot_engine import (
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
    (tmp_path / "static").mkdir(parents=True)
    (tmp_path / "templates" / "components").mkdir(parents=True)
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
