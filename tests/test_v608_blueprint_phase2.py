from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_v608_blueprint_routes_registered(app_module):
    paths = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert "/admin/architecture" in paths
    assert "/api/architecture/summary" in paths
    assert "/api/v608/blueprint-migration-check" in paths


def test_v608_check_endpoint(client):
    response = client.get("/api/v608/blueprint-migration-check")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["module"] == "Blueprint Migration Phase 2"
    assert "architecture" in payload
