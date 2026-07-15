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


def test_public_pages_do_not_crash(client):
    for path in ["/", "/live", "/picks"]:
        response = client.get(path)
        assert response.status_code < 500, f"{path} devolvió {response.status_code}"
