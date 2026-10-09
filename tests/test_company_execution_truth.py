"""Synthetic presentation regressions. No app, workers, providers or production data."""
from copy import deepcopy
from html import unescape
from pathlib import Path
import re

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, select_autoescape

from engines.company_operating_system_engine import build_company_os_summary


ROOT = Path(__file__).resolve().parents[1]


def render(name, **context):
    env = Environment(
        loader=ChoiceLoader([
            DictLoader({"base.html": "<!doctype html><html><body>{% block content %}{% endblock %}</body></html>"}),
            FileSystemLoader(ROOT / "templates"),
        ]),
        autoescape=select_autoescape(),
    )
    env.globals["ui"] = lambda value, **values: str(value).format(**values)
    env.globals["url_for"] = lambda endpoint, filename: "/static/" + filename
    env.filters["madrid_datetime_label"] = lambda value: value
    # Required to compile the imported shared macros; sports cards are not used.
    env.filters["sync_madrid_label"] = lambda value: value
    return env.get_template(name).render(**context)


def text(markup):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def workforce(**updates):
    payload = {
        "summary": {"v916_workforce_core_ready": False},
        "workers": [{"name": "Release Manager", "file": "release_manager.py", "status": "ready"}],
        "workflows": [{"name": "CI QA", "path": ".github/workflows/nemesis-ci.yml", "status": "ready"}],
        "latest_run": {},
    }
    payload.update(updates)
    return payload


def execution_panel(markup):
    return re.search(r'<section[^>]*data-workforce-execution[^>]*>(.*?)</section>', markup, re.S).group(1)


def core_card(markup):
    return next(card for card in re.findall(r'<article\b.*?</article>', markup, re.S) if "Componentes base" in card)


@pytest.mark.parametrize("runtime", [{}, {"api_football_configured": True, "telegram_configured": True}])
def test_configured_roles_never_claim_executions_or_continuous_monitoring(runtime):
    summary = build_company_os_summary("SIMULATED_QA", runtime)
    assert summary["global_status"] == "responsabilidades_configuradas"
    assert summary["execution_state"] == "UNVERIFIED"
    assert len(summary["workers"]) == 15
    assert {worker["status"] for worker in summary["workers"]} == {"Sin ejecución acreditada"}
    assert {worker["execution_state"] for worker in summary["workers"]} == {"UNVERIFIED"}
    assert all(worker["href"] and worker["safe_next_step"] for worker in summary["workers"])
    markup = render("admin_company_os.html", summary=summary)
    assert "Responsabilidades configuradas" in text(markup)
    assert "Alcance previsto" in text(markup)
    assert "Operativo con revisión continua" not in text(markup)
    assert "Product CEO Worker" not in text(markup)


def test_configuration_alerts_remain_separate_from_execution_evidence():
    missing = build_company_os_summary(runtime={})
    by_area = {worker["area"]: worker for worker in missing["workers"]}
    assert missing["configuration_attention_count"] == 2
    assert by_area["Telegram"]["configuration_status"] == "No configurado"
    assert by_area["API-SPORTS y live"]["configuration_status"] == "Requiere configuración real"
    assert by_area["Telegram"]["risk_level"] == "medio"
    markup = render("admin_company_os.html", summary=missing)
    assert "Configuración del contexto: No configurado" in text(markup)
    configured = build_company_os_summary(runtime={"api_sports_configured": True, "telegram_configured": True})
    assert configured["configuration_attention_count"] == 0
    assert {worker["status"] for worker in configured["workers"]} == {"Sin ejecución acreditada"}


@pytest.mark.parametrize("status", ["ready", "missing"])
def test_nonempty_inventory_does_not_make_core_ready_or_claim_a_run(status):
    payload = workforce(workers=[{"name": "Synthetic checker", "file": "synthetic.py", "status": status}])
    markup = render("admin_automation_workforce.html", workforce=payload)
    assert "Disponibilidad por comprobar" in text(core_card(markup))
    assert "is-success" not in core_card(markup)
    assert "Sin ejecución acreditada" in text(execution_panel(markup))
    assert "Última ejecución consolidada" not in text(markup)
    assert "Estado de preparación" in text(markup)
    assert ("No disponible" if status == "missing" else "Disponible") in text(markup)


def test_installed_core_is_only_available_and_has_no_execution_without_receipt():
    markup = render("admin_automation_workforce.html", workforce=workforce(summary={"v916_workforce_core_ready": True}))
    assert "Disponibles" in text(core_card(markup))
    assert "is-success" not in core_card(markup)
    assert "Sin ejecución acreditada" in text(execution_panel(markup))
    assert "su presencia no acredita resultados en GitHub" in text(markup)


@pytest.mark.parametrize("receipt", [None, [], "ok", {}, {"overall_status": "not_run"}, {"overall_status": True}])
def test_absent_or_malformed_receipt_is_not_inferred_from_legacy_summary(receipt):
    markup = render("admin_automation_workforce.html", workforce=workforce(
        latest_run=receipt, full_run={"v917_workforce_last_run_status": "ok"}))
    assert "Sin ejecución acreditada" in text(execution_panel(markup))


@pytest.mark.parametrize("status", ["ok", "action_required"])
def test_saved_result_keeps_original_date_version_and_scope_without_certifying_current_state(status):
    receipt = {"overall_status": status, "generated_at_madrid": "2020-01-02T10:00:00+01:00",
               "version": "SIMULATED_OLD", "dry_run": True}
    payload = workforce(latest_run=receipt)
    before = deepcopy(payload)
    markup = render("admin_automation_workforce.html", workforce=payload)
    panel = text(execution_panel(markup))
    assert f"Resultado registrado: {status}" in panel
    assert receipt["generated_at_madrid"] in panel
    assert "SIMULATED_OLD" in panel
    assert "Comprobación dry-run" in panel
    assert "no acredita el estado actual de producción" in panel
    assert "is-success" not in execution_panel(markup)
    assert payload == before


def test_incomplete_saved_result_preserves_unknown_date_version_and_scope():
    markup = render("admin_automation_workforce.html", workforce=workforce(latest_run={"overall_status": "action_required"}))
    panel = text(execution_panel(markup))
    assert "Fecha de evidencia no disponible" in panel
    assert "Versión registrada: No disponible" in panel
    assert "Alcance registrado: No especificado" in panel


def test_empty_inventory_is_explicit_and_saved_evidence_remains_escaped():
    markup = render("admin_automation_workforce.html", workforce=workforce(
        workers=[], workflows=[], latest_run={"overall_status": '<script>alert("fixture")</script>'}))
    assert "Sin componentes listados" in text(markup)
    assert '<script>alert("fixture")</script>' not in execution_panel(markup)
    assert "&lt;script&gt;" in execution_panel(markup)
