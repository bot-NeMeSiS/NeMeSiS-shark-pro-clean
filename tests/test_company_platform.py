import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DB_PATH", str(ROOT / "tmp" / "nemesis_company_platform_test.sqlite"))
os.environ.setdefault("SECRET_KEY", "company-platform-test-secret")
os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY"):
    os.environ[key] = ""

import app as app_module  # noqa: E402
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="strict")


def test_company_platform_public_routes_render_with_contract():
    client = app_module.app.test_client()
    routes = [
        "/landing",
        "/precios",
        "/faq",
        "/help-center",
        "/knowledge-base",
        "/roadmap",
        "/changelog",
        "/service-status",
        "/partners",
        "/afiliados",
        "/blog",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, route
        html = response.get_data(as_text=True)
        assert "NEMESIS-COMPANY-PLATFORM-BUSINESS-ECOSYSTEM-V1" in html
        assert "company-platform-v1" in html
        assert "<h1" in html
        assert "None" not in html
        assert "undefined" not in html


def test_company_platform_aliases_and_existing_trust_routes_exist():
    rules = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    required = {
        "/oficial", "/empresa", "/pricing", "/preguntas-frecuentes", "/centro-ayuda",
        "/base-conocimiento", "/roadmap-publico", "/cambios", "/estado-servicio", "/status",
        "/socios", "/affiliates", "/contact", "/support", "/terminos", "/privacidad", "/cookies",
    }
    assert required.issubset(rules)


def test_company_platform_does_not_start_payments_campaigns_or_external_actions():
    template = read_text("templates/company_platform.html")
    app_text = read_text("app.py")
    company_slice = app_text.split("COMPANY_PLATFORM_CONTRACT", 1)[1].split("# ===================== V741", 1)[0]
    forbidden = ["/api/payments", "create_checkout_session", "customer-portal", "checkout", "utm_", "send_telegram", "telegram_scheduler_tick"]
    lowered = (template + company_slice).lower()
    for item in forbidden:
        assert item.lower() not in lowered
    assert "Sin contenido ficticio" in template
    assert "Sin llamadas externas" in template


def test_company_platform_empty_states_are_honest():
    template = read_text("templates/company_platform.html")
    required = [
        "No hay changelog publico publicado",
        "No hay partners publicados",
        "Programa de afiliados no abierto",
        "No hay articulos publicados",
        "Sin articulos publicos aprobados",
    ]
    for snippet in required:
        assert snippet in template


def test_company_platform_registry_developer_center_and_reports():
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry["capabilities"]}
    assert capabilities["company_platform_business_ecosystem"]["contract"] == "NEMESIS-COMPANY-PLATFORM-BUSINESS-ECOSYSTEM-V1"
    roadmap = build_product_roadmap(ROOT)
    modules = {item["name"]: item for item in roadmap["modules"]}
    assert modules["Company Platform Business Ecosystem"]["state"] in {"COMPLETED", "IN_PROGRESS"}
    for report in [
        "reports/COMPANY_PLATFORM_REPORT.md",
        "reports/BUSINESS_READY_REPORT.md",
        "reports/COMMERCIAL_WEBSITE_REPORT.md",
        "reports/GO_TO_MARKET_PLATFORM.md",
    ]:
        assert (ROOT / report).is_file()
