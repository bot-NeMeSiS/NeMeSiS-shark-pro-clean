from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from engines.match_context_engine import build_match_context
from engines.match_live_story_engine import build_match_live_story
from engines.project_operating_system_engine import (
    ARCHIVE_REQUIRED,
    build_company_board_snapshot,
    build_dev_source_archive,
    build_developer_center_snapshot,
    clear_project_snapshot_cache,
)
from engines.sports_platform_contracts import (
    EvidenceReference,
    build_assistant_context,
    build_entity_reference,
    build_sports_graph_edge,
    build_sports_memory_record,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


@pytest.fixture
def local_tmp_path():
    with tempfile.TemporaryDirectory(prefix=".nemesis_test_", dir=ROOT) as directory:
        yield Path(directory)


def test_developer_snapshot_has_one_evidence_backed_source():
    clear_project_snapshot_cache()
    snapshot = build_developer_center_snapshot(
        ROOT,
        VERSION,
        {"has_v939_autonomous_company_intelligence_growth_quality_platform": True},
        registered_routes=["/", "/admin/developer-center"],
    )

    assert snapshot["contract"] == "NEMESIS-COMPANY-DEVELOPER-OS-V1"
    assert snapshot["guardrails"] == {
        "external_calls": False,
        "database_writes": False,
        "secrets_returned": False,
        "automatic_push": False,
        "automatic_deploy": False,
    }
    assert snapshot["summary"]["exact_duplicate_groups"] == 0
    assert snapshot["summary"]["route_duplicates"] == 0
    assert snapshot["registered_routes"]["state"] == "CONFIRMED"
    assert snapshot["sports_platform"]["guardrails"]["telegram_sends"] is False
    capabilities = {item["key"]: item for item in snapshot["sports_platform"]["capabilities"]}
    assert capabilities["live_center"]["state"] == "FOUNDATION_READY"
    for key in ("team_center", "competition_center", "player_center"):
        assert capabilities[key]["state"] == "CONTRACT_READY"


def test_company_board_uses_shared_roadmap_and_reports_git_truth():
    company = build_company_board_snapshot(ROOT, VERSION, {})

    assert company["contract"] == "NEMESIS-COMPANY-DEVELOPER-OS-V1"
    assert company["roadmap"]["contract"] == "NEMESIS-PRODUCT-ROADMAP-V1"
    assert company["areas"]
    assert all(area["evidence"] and area["next_action"] for area in company["areas"])
    assert company["git"]["state"] in {"CONFIRMED", "REQUIRES_REVIEW", "BLOCKED_BY_ACCESS"}
    assert company["guardrails"]["database_writes"] is False


def test_dev_source_archive_uses_allowlist_and_excludes_private_artifacts(local_tmp_path):
    tmp_path = local_tmp_path
    for relative in ARCHIVE_REQUIRED:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("safe source\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("SECRET_KEY=replace-me\n", encoding="utf-8")
    (tmp_path / "env.example").write_text("DB_PATH=/data/app.db\n", encoding="utf-8")
    (tmp_path / "engines").mkdir(exist_ok=True)
    (tmp_path / "engines" / "safe_engine.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "real.sqlite").write_bytes(b"must-not-ship")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "screen.png").write_bytes(b"must-not-ship")
    (tmp_path / ".env").write_text("REAL_SECRET=blocked\n", encoding="utf-8")
    (tmp_path / "templates" / "home.html.orig").write_text(
        "obsolete backup\n",
        encoding="utf-8",
    )

    result = build_dev_source_archive(tmp_path, VERSION)

    assert result["forbidden_count"] == 0
    assert result["missing_required_root"] == []
    assert result["sha256"]
    with zipfile.ZipFile(tmp_path / result["path"]) as archive:
        names = set(archive.namelist())
    assert ARCHIVE_REQUIRED <= names
    assert ".env.example" in names
    assert "env.example" in names
    assert "data/real.sqlite" not in names
    assert "reports/screen.png" not in names
    assert ".env" not in names
    assert "templates/home.html.orig" not in names
    assert "DEV_SOURCE_MANIFEST.json" in names


def test_sports_memory_graph_and_assistant_contracts_never_authorize_effects():
    entity = build_entity_reference(
        "team",
        "team-1",
        "Equipo confirmado",
        source="provider-cache",
        evidence_state="VERIFIED",
    )
    memory = build_sports_memory_record(
        "favorite_added",
        entity,
        observed_at_madrid="2026-07-26T12:00:00+02:00",
        source="local-product-event",
        evidence_state="VERIFIED",
        payload={"favorite": True},
    )
    evidence = EvidenceReference(
        source="provider-cache",
        source_type="sports",
        observed_at_madrid="2026-07-26T12:00:00+02:00",
        state="VERIFIED",
        reference="fixture-1",
    )
    edge = build_sports_graph_edge(entity, "plays", entity, evidence)
    shark = build_assistant_context(
        "shark",
        sports_metrics={"contract": "sports-metrics-v1"},
        evidence_state="PARTIALLY_VERIFIED",
    )

    assert memory.persistence_authorized is False
    assert edge.persistence_authorized is False
    assert shark.external_action_authorized is False


def test_live_story_is_provider_confirmed_and_reused_by_match_context():
    match = {
        "id": "fixture-1",
        "home_team": "Local",
        "away_team": "Visitante",
        "status": "live",
        "source": "provider-cache",
    }
    events = [
        {
            "id": "event-1",
            "source": "provider-cache",
            "type": "goal",
            "minute": 12,
            "team": "Local",
            "player": "Jugador",
        },
        {
            "id": "event-1",
            "source": "provider-cache",
            "type": "goal",
            "minute": 12,
        },
        {"type": "yellow_card", "minute": 20},
    ]
    story = build_match_live_story(match, events)
    context = build_match_context(
        {
            "match": match,
            "timeline": events,
            "state": {"state": "LIVE", "shark_momentum": {"stats_available": False}},
        }
    )

    assert story["state"] == "story_available"
    assert story["counts"] == {"events": 1, "cycles": 1, "key_events": 1}
    assert context["live_story"] == story
    assert context["event_summary"]["count"] == 1
    assert context["event_summary"]["excluded_without_evidence"] == 2
    assert context["diagnostics"]["builder_database_writes"] == 0


def test_root_duplicates_are_compatibility_adapters():
    adapters = {
        "api_exploitation_engine.py": "engines.api_exploitation_engine",
        "architecture.py": "blueprints.architecture",
        "backup_service.py": "services.backup_service",
        "live_engine.py": "engines.live_engine",
        "shark_engine.py": "engines.shark_engine",
        "shark_learning_engine.py": "engines.shark_learning_engine",
        "shark_service.py": "services.shark_service",
        "telegram_autonomous_delivery_engine.py": "engines.telegram_autonomous_delivery_engine",
        "telegram_delivery_engine.py": "engines.telegram_delivery_engine",
        "telegram_engine.py": "engines.telegram_engine",
        "telegram_service.py": "services.telegram_service",
    }
    for relative, canonical in adapters.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "Compatibility adapter" in source
        assert f"from {canonical} import *" in source


def test_developer_and_company_routes_are_admin_only(client):
    assert client.get("/api/admin/developer-center/summary").status_code == 403
    assert client.post("/api/admin/developer-center/refresh").status_code == 403
    assert client.get("/admin/developer-center").status_code in {301, 302}
    assert client.get("/api/admin/company-board/summary").status_code == 403

    with client.session_transaction() as session:
        session["user_role"] = "ADMIN"
        session["user_id"] = "pytest-admin"

    assert client.post("/admin/developer-center/build").status_code == 403

    developer = client.get("/admin/developer-center")
    company = client.get("/admin/company-board")
    developer_api = client.get("/api/admin/developer-center/summary")
    company_api = client.get("/api/admin/company-board/summary")

    assert developer.status_code == 200
    assert company.status_code == 200
    assert developer_api.status_code == 200
    assert company_api.status_code == 200
    assert b'data-developer-center="NEMESIS-COMPANY-DEVELOPER-OS-V1"' in developer.data
    assert b'data-company-board="NEMESIS-COMPANY-DEVELOPER-OS-V1"' in company.data
