"""Public product identity across real guarded Flask/Jinja consumers.

SIMULATED_QA only. Existing runtime, PWA/icon and browser gates retain their
independent coverage; template-only cases do not certify account authentication.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

import pytest
from flask import render_template

from test_design02_calendar_presentation import Structure


class TextStructure(Structure):
    """Add rendered text to the repository's existing structural HTML helper."""

    def handle_data(self, data):
        if any(
            node["tag"] in {"head", "script", "style", "template"}
            or "hidden" in node["attrs"]
            for node in self.stack
        ):
            return
        for node in self.stack:
            node.setdefault("text_parts", []).append(data)


def text(node):
    return " ".join("".join(node.get("text_parts", [])).split())


def body_text(dom):
    body, = [node for node in dom.nodes if node["tag"] == "body"]
    return text(body)


def token(value, rendered):
    return re.search(r"(?<![\w.])" + re.escape(value) + r"(?![\w.])", rendered)


def meta(dom, name):
    node, = [
        node for node in dom.nodes
        if node["tag"] == "meta" and node["attrs"].get("name") == name
    ]
    return node["attrs"]["content"]


def assert_public_shell(dom, app_module):
    brands = dom.with_class("ns-brand")
    assert brands, "The actual shared brand must be present"
    footer, = dom.with_class("v933-legal-footer")
    for node in [*brands, footer]:
        assert token("v1", text(node)), text(node)
        assert not token("001", text(node)), "Revision belongs in information, not branding"
        assert app_module.APP_VERSION not in text(node)
    assert meta(dom, "nemesis-product-version") == "v1"
    assert meta(dom, "nemesis-product-revision") == "001"
    # Technical metadata legitimately remains in the same HTML document.
    assert meta(dom, "nemesis-version") == app_module.APP_VERSION


@pytest.fixture
def identity_client(app_module, monkeypatch, tmp_path):
    """Own the local database using the existing App fixture/seed conventions."""
    monkeypatch.setattr(app_module, "DB_PATH", str(tmp_path / "public-identity.sqlite"))
    monkeypatch.setattr(app_module, "_SEEDED_DB_PATH", None)
    monkeypatch.setattr(app_module, "_SEEDING_DB_PATH", None)
    monkeypatch.setattr(app_module, "APP_INITIALIZED", False)
    app_module.seed_core()
    return app_module, app_module.app.test_client()


@pytest.mark.parametrize(
    "variant,compact",
    [("topbar", True), ("auth", False), ("admin", False)],
)
def test_imported_brand_uses_public_global_without_request_context(
    app_module, variant, compact,
):
    # No Flask request context and no context processor. Context poison must not
    # enter a macro imported WITHOUT "with context"; the Jinja global must work.
    template = app_module.app.jinja_env.from_string(
        '{% from "partials/brand_logo.html" import nemesis_brand %}'
        "{{ nemesis_brand('/', variant, compact) }}"
    )
    html = template.render(
        variant=variant,
        compact=compact,
        app_version="V9999_UNRELATED_TECHNICAL_BUILD",
        public_product_version="CONTEXT_POISON_DO_NOT_BRAND",
        public_product_revision="999",
    )
    dom = TextStructure(html)
    brand, = dom.with_class("ns-brand")
    assert token("v1", text(brand))
    assert not token("001", text(brand))
    assert "CONTEXT_POISON" not in text(brand)
    assert "V9999" not in text(brand)
    assert brand["attrs"]["href"] == "/"


@pytest.mark.parametrize(
    "route",
    ["/landing", "/cliente-login", "/admin-login", "/instalar"],
)
def test_actual_public_consumers_show_v1_but_keep_technical_metadata(
    identity_client, route,
):
    a, client = identity_client
    response = client.get(route)
    assert response.status_code == 200, (route, response.status_code)
    dom = TextStructure(response.get_data(as_text=True))
    assert_public_shell(dom, a)
    assert token("v1", body_text(dom))
    # Do not assert APP_VERSION absent from raw HTML: meta and cache URLs need it.


@pytest.mark.parametrize(
    "path,role",
    [("/mi-cuenta", "ELITE"), ("/admin/control-center", "ADMIN")],
)
def test_actual_shared_cuenta_and_admin_shells_keep_public_brand(
    app_module, path, role,
):
    # Same template-only convention as test_shark_workspace.shell. This is not
    # an authentication/session acceptance test; those existing tests still run.
    user = {"id": "public-brand-qa", "name": "QA", "role": role, "membership": role}
    with app_module.app.test_request_context(path):
        html = render_template("base.html", data={}, current_user=user)
    assert_public_shell(TextStructure(html), app_module)


def test_actual_support_places_revision_in_information_not_header_or_footer(identity_client):
    a, client = identity_client
    response = client.get("/soporte")
    assert response.status_code == 200
    dom = TextStructure(response.get_data(as_text=True))
    assert_public_shell(dom, a)
    revision, = [
        node for node in dom.nodes
        if "data-product-revision" in node["attrs"]
    ]
    assert revision["attrs"]["data-product-revision"] == "001"
    assert token("001", text(revision)) and token("v1", text(revision))
    assert re.search(r"Revisi[oó]n", text(revision))
    assert not any(
        ancestor in revision["parents"]
        for ancestor in [*dom.with_class("ns-brand"), *dom.with_class("v933-legal-footer")]
    )
    # The naming addition must not replace the original support form contract.
    form, = dom.with_class("v933-support-form")
    assert form["attrs"]["method"].lower() == "post"
    assert any(
        node["attrs"].get("name") == "csrf_token" and node["attrs"].get("value")
        and form in node["parents"] for node in dom.nodes
    )


def test_actual_service_status_foreground_uses_product_name_and_keeps_truthful_scope(
    identity_client,
):
    a, client = identity_client
    response = client.get("/service-status")
    assert response.status_code == 200
    dom = TextStructure(response.get_data(as_text=True))
    card, = [
        node for node in dom.with_class("company-platform-card")
        if "Respuesta servida por esta instancia" in text(node)
    ]
    assert re.search(r"Versi[oó]n\s+v1\b", text(card))
    assert a.APP_VERSION not in text(card)
    assert "no certifica otros sistemas" in text(card)
    assert "Consulta" in text(card)
    assert meta(dom, "nemesis-version") == a.APP_VERSION


def commercial_payload():
    """Independent synthetic evidence, not a copy of any readiness builder."""
    recorded = "V940_RECORDED_EVIDENCE"
    check = {"label": "Recorded build", "ok": False, "value": recorded}
    gate = {
        "title": "Evidence still pending", "critical": True, "score": 0,
        "status": "BLOCKED", "checks": [check], "next_action": "Keep pending",
    }
    return {
        "version": recorded,
        "final_release": {
            "readiness_score": 0, "overall": 0, "status": "BLOCKED",
            "gates": [gate], "production_missing": ["Evidence still pending"],
            "safe_scope": [],
        },
        "public_launch": {
            "global_score": 0, "status": "BLOCKED", "stages": [],
            "blockers": [{"stage": "Evidence still pending", "score": 0, "next": "Keep pending"}],
        },
        "go_live": {
            "global_score": 0, "status": "BLOCKED", "critical_blockers": [gate],
            "blockers": [gate], "gates": [gate], "safe_env": {}, "db": {"counts": {}},
            "decision": {
                "can_run_private_beta": False, "can_open_public_big": False,
                "recommended_next": "Keep pending",
            },
        },
        "validation_plan": [{
            "step": 1, "title": "Recorded evidence", "url": "/api/runtime-version",
            "expected": recorded, "detail": recorded,
        }],
    }


@pytest.mark.parametrize(
    "template,path",
    [
        ("admin_final_release.html", "/admin/final-release"),
        ("admin_public_launch.html", "/admin/public-launch"),
        ("admin_go_live.html", "/admin/go-live"),
    ],
)
def test_actual_commercial_templates_separate_product_from_recorded_evidence(
    app_module, template, path,
):
    data = commercial_payload()
    before = copy.deepcopy(data)
    user = {"id": "public-release-qa", "role": "ADMIN", "membership": "ADMIN"}
    with app_module.app.test_request_context(path):
        html = render_template(template, data=data, current_user=user)
    dom = TextStructure(html)
    if template == "admin_final_release.html":
        hero, = dom.with_class("ns-final-release")
        kicker, = [node for node in dom.with_class("kicker") if hero in node["parents"]]
        assert token("v1", text(kicker))
        assert token("001", text(kicker))
        assert data["version"] not in text(kicker)
    else:
        version_card, = [
            node for node in dom.with_class("stat-card")
            if any(
                child["tag"] == "strong" and text(child) == "v1"
                and node in child["parents"] for child in dom.nodes
            )
        ]
        assert token("001", text(version_card))
        assert data["version"] in text(version_card)
        assert "Compilación técnica" in text(version_card)
    # Renaming must not turn pending evidence into a successful release.
    assert "Evidence still pending" in body_text(dom)
    assert data["version"] in body_text(dom)
    assert data == before


def test_actual_admin_dashboard_retains_historical_technical_snapshot(app_module):
    recorded = "V940_RECORDED_ADMIN_SNAPSHOT"
    data = {"admin_master": {"version": recorded, "runtime": {"app_version": recorded}}}
    with app_module.app.test_request_context("/admin/control-center"):
        html = render_template(
            "admin_dashboard.html", data=data,
            current_user={"id": "public-release-qa", "role": "ADMIN", "membership": "ADMIN"},
        )
    dom = TextStructure(html)
    version, = [node for node in dom.nodes if "data-master-version" in node["attrs"]]
    assert text(version) == recorded
    assert "Compilación técnica" in body_text(dom)
    assert_public_shell(dom, app_module)


def test_standalone_admin_preview_has_public_brand_and_keeps_readonly_warning(app_module):
    with app_module.app.test_request_context("/admin/client-preview/frame?page=telegram"):
        html = render_template(
            "admin_client_preview.html", page="telegram", preview_title="Telegram",
            plan="FREE", pages={"telegram": "Telegram"}, settings={},
            preview_membership={}, preview_plan_limits={}, preview_prices={},
        )
    dom = TextStructure(html)
    brand, = dom.with_class("preview-brand")
    label, = [
        node for node in dom.nodes
        if node["tag"] == "strong" and node["parents"]
        and node["parents"][-1] is brand
    ]
    assert token("v1", text(label))
    assert not token("001", text(brand))
    assert meta(dom, "nemesis-product-version") == "v1"
    assert "No modifica cuentas, sesión ni membresías" in body_text(dom)
    assert any(
        node["tag"] == "link" and app_module.APP_VERSION in node["attrs"].get("href", "")
        for node in dom.nodes
    )


@pytest.mark.parametrize("route", ["/version", "/api/runtime-version"])
def test_existing_machine_version_key_remains_technical(identity_client, route):
    a, client = identity_client
    response = client.get(route)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == a.APP_VERSION
    assert payload["version"] not in {"v1", "001"}


def install_fingerprint(client):
    """Only the existing installed identity/icon contract, not a manifest copy."""
    payloads = []
    for path in ("/manifest.json", "/founder-manifest.json"):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        payloads.append(response.get_json())
    identity = [
        {key: payload[key] for key in ("id", "start_url", "scope", "name", "short_name", "icons")}
        for payload in payloads
    ]
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), [payload["id"] for payload in payloads]


def test_public_naming_does_not_drive_existing_pwa_installed_identity(
    identity_client, monkeypatch,
):
    a, client = identity_client
    before, ids = install_fingerprint(client)
    assert ids == ["/", "/admin/founder-os"]
    # Counterfactual public naming only. Do not change technical APP_VERSION,
    # icon version, manifest/worker implementations, storage, or native guards.
    monkeypatch.setattr(a, "PUBLIC_PRODUCT_VERSION", "v9")
    monkeypatch.setattr(a, "PUBLIC_PRODUCT_REVISION", "999")
    monkeypatch.setitem(a.app.jinja_env.globals, "public_product_version", "v9")
    monkeypatch.setitem(a.app.jinja_env.globals, "public_product_revision", "999")
    after, after_ids = install_fingerprint(client)
    assert (after, after_ids) == (before, ids)


def test_future_telegram_composer_uses_public_label_without_sending(app_module, monkeypatch):
    briefing_calls = []

    def briefing():
        briefing_calls.append(True)
        return {"summary": {"matches_today": 2, "live_now": 1, "picks_ready": 3}}

    def forbidden_send(*_args, **_kwargs):
        pytest.fail("Composing public naming must not send a Telegram message")

    monkeypatch.setattr(app_module, "shark_briefing", briefing)
    monkeypatch.setattr(app_module, "send_telegram_message", forbidden_send)
    monkeypatch.setattr(app_module, "telegram_send_http", forbidden_send)
    message = app_module.telegram_daily_message()
    assert "Versión: v1\n" in message
    assert "Partidos hoy: 2 | Live: 1 | Picks: 3" in message
    assert app_module.APP_VERSION not in message
    assert not token("001", message)
    assert briefing_calls == [True]
