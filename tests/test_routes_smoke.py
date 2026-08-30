from __future__ import annotations

from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_duplicate_exact_routes(app_module):
    paths = [rule.rule for rule in app_module.app.url_map.iter_rules()]
    duplicates = sorted(path for path, count in Counter(paths).items() if count > 1)
    assert not duplicates, f"Rutas duplicadas exactas: {duplicates}"


def test_critical_routes_registered(app_module):
    paths = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    expected = {"/", "/live", "/picks", "/cliente-login", "/admin-login", "/registro"}
    missing = sorted(expected - paths)
    assert not missing, f"Rutas críticas faltantes: {missing}"


def test_shark_route_guard_does_not_emit_invalid_javascript_regex():
    base_text = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
    assert "window.location.pathname === '/shark'" in base_text
    assert r"/^\/shark(:\/|$|-|\)/" not in base_text


def test_canonical_shell_keeps_navigation_clickable_and_admin_isolated():
    base_text = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
    navigation = (ROOT / "templates" / "components" / "v933_navigation.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    client_js = (ROOT / "static" / "v937-product-client.js").read_text(encoding="utf-8")
    shark = (ROOT / "static" / "img" / "nemesis-shark-official.svg").read_text(encoding="utf-8")

    assert "{% if false %}" not in base_text
    assert "document.querySelectorAll('.nav a,.bottom-nav a,.ns-client-sidebar a')" not in base_text
    assert "{% set links = [('Inicio','/','home')" in navigation
    assert "body.ns-app .v933-shell-chrome {" in css
    assert "position: static;" in css
    assert "body.ns-app .v933-shell-chrome :is(a,button,input,select,textarea,summary) { pointer-events: auto; }" in css
    assert 'body.classList.contains("ns-admin")' in client_js
    assert 'viewBox="0 0 180 120"' in shark
    assert not (ROOT / "static" / "img" / "shark-logo.svg").exists()

    visual_sources = [
        ROOT / "app.py",
        *(ROOT / "static").glob("*.css"),
        *(ROOT / "templates").rglob("*.html"),
    ]
    visual_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in visual_sources
    )
    assert "official-brand-6" not in visual_text
    assert "official-brand-8" not in visual_text
    assert "official-atmosphere-5" not in visual_text
    assert "official-atmosphere-6" not in visual_text
    assert "official-atmosphere-7" not in visual_text


def test_public_pages_do_not_crash(client):
    for path in ["/", "/live", "/picks"]:
        response = client.get(path)
        assert response.status_code < 500, f"{path} devolvió {response.status_code}"


def test_qa_404_probe_does_not_create_a_real_sentinel_issue(client, app_module, monkeypatch):
    recorded = []
    monkeypatch.setattr(app_module, "v896_load_not_found_events", lambda: {"events": []})
    monkeypatch.setattr(app_module, "v896_save_not_found_events", lambda payload: None)
    monkeypatch.setattr(app_module, "v896_upsert_not_found_issue", recorded.append)

    qa_response = client.get(
        "/ruta-inventada-v910",
        headers={"X-NEMESIS-QA-PROBE": "1"},
    )
    assert qa_response.status_code == 404
    assert recorded == []

    synthetic_response = client.get("/ruta-inventada-v910")
    assert synthetic_response.status_code == 404
    assert recorded == []

    direct_response = client.get("/enlace-roto-real")
    assert direct_response.status_code == 404
    assert recorded == []

    internal_navigation = client.get(
        "/enlace-roto-real",
        headers={"Referer": "http://localhost/app"},
    )
    assert internal_navigation.status_code == 404
    assert len(recorded) == 1


def test_sports_empty_states_are_not_reported_as_missing(client):
    from engines.visual_company_worker_engine import inspect_route

    for route in ("/partidos", "/calendar", "/live"):
        result = inspect_route(client, route, "CLIENT")
        titles = {item.get("title") for item in result.get("issues") or []}
        assert "Pantalla deportiva vacia sin estado seguro" not in titles, route


def test_release_builder_excludes_browser_qa_and_keeps_manifest_inside_zip():
    builder = (ROOT / "tools" / "build_clean_release.py").read_text(encoding="utf-8")
    auditor = (ROOT / "tools" / "audit_release_zip.py").read_text(encoding="utf-8")

    include_block = builder.split("INCLUDE_TOP_LEVEL_DIRS = {", 1)[1].split("}", 1)[0]
    exclude_block = builder.split("EXCLUDE_DIRS = {", 1)[1].split("}", 1)[0]
    forbidden_block = auditor.split("FORBIDDEN_PARTS = {", 1)[1].split("}", 1)[0]

    assert '"browser_qa"' not in include_block
    assert '"browser_qa"' in exclude_block
    assert '"browser_qa"' in forbidden_block
    assert "MANIFEST_PATH.write_text" not in builder
    assert "zf.writestr(MANIFEST_NAME" in builder
    assert 'REPORT_DIR = ROOT / "release_output"' in auditor
