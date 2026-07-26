"""Safety gate for the shared Company and Developer operating system."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.project_operating_system_engine import (  # noqa: E402
    ARCHIVE_FORBIDDEN_NAMES,
    ARCHIVE_FORBIDDEN_SUFFIXES,
    ARCHIVE_REQUIRED,
    OPERATING_SYSTEM_CONTRACT,
    build_company_board_snapshot,
    build_dev_source_archive,
    build_developer_center_snapshot,
)
from engines.sports_platform_contracts import EVIDENCE_STATES  # noqa: E402


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()

    developer = build_developer_center_snapshot(ROOT, version, {})
    company = build_company_board_snapshot(ROOT, version, {})

    require(developer.get("contract") == OPERATING_SYSTEM_CONTRACT, "developer_contract", failures)
    require(company.get("contract") == OPERATING_SYSTEM_CONTRACT, "company_contract", failures)
    require(developer.get("quality", {}).get("exact_source_duplicates") == [],
            "functional_source_duplicates", failures)
    require(developer.get("guardrails", {}).get("database_writes") is False,
            "developer_db_write_guard", failures)
    require(developer.get("guardrails", {}).get("external_calls") is False,
            "developer_external_call_guard", failures)
    require(company.get("guardrails", {}).get("automatic_push") is False,
            "company_automatic_push_guard", failures)
    require(company.get("guardrails", {}).get("automatic_deploy") is False,
            "company_automatic_deploy_guard", failures)
    require(company.get("roadmap", {}).get("contract") == "NEMESIS-PRODUCT-ROADMAP-V1",
            "live_roadmap_contract", failures)

    contracts = developer.get("sports_platform", {})
    require(contracts.get("contract") == "NEMESIS-SPORTS-PLATFORM-CONTRACTS-V1",
            "sports_platform_contract", failures)
    require(set(contracts.get("evidence_states", [])) == set(EVIDENCE_STATES),
            "evidence_states", failures)

    archive_result = build_dev_source_archive(ROOT, version)
    archive_path = ROOT / archive_result["path"]
    require(archive_result.get("forbidden_count") == 0, "archive_forbidden_count", failures)
    require(archive_result.get("missing_required_root") == [], "archive_required_root", failures)
    require(archive_path.is_file(), "archive_missing", failures)

    if archive_path.is_file():
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            require(ARCHIVE_REQUIRED <= names, "archive_required_entries", failures)
            require("DEV_SOURCE_MANIFEST.json" in names, "archive_manifest_missing", failures)
            blocked = []
            for name in names:
                path = Path(name)
                lower_parts = {part.lower() for part in path.parts}
                if lower_parts & {
                    ".git", ".venv", "__pycache__", ".pytest_cache", ".cache",
                    "release_output", "logs", "backups", "tmp", "data",
                    "reports", "browser_qa", "reference_images",
                }:
                    blocked.append(name)
                if path.name.lower() in ARCHIVE_FORBIDDEN_NAMES:
                    blocked.append(name)
                if path.suffix.lower() in ARCHIVE_FORBIDDEN_SUFFIXES:
                    blocked.append(name)
                if path.name.startswith(".env") and path.name != ".env.example":
                    blocked.append(name)
            require(not blocked, f"archive_blocked_entries:{blocked[:10]}", failures)

            if "DEV_SOURCE_MANIFEST.json" in names:
                manifest = json.loads(archive.read("DEV_SOURCE_MANIFEST.json"))
                require(manifest.get("contract") == OPERATING_SYSTEM_CONTRACT,
                        "archive_manifest_contract", failures)
                require(manifest.get("version") == version, "archive_manifest_version", failures)
                require(manifest.get("production_modified") is False,
                        "archive_manifest_production_guard", failures)

    if failures:
        print("MASTER_OPERATING_SYSTEM_FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("MASTER_OPERATING_SYSTEM_OK")
    print(f"VERSION={version}")
    print(f"DEV_SOURCE_SHA256={archive_result['sha256']}")
    print(f"DEV_SOURCE_FILES={archive_result['source_files']}")
    print("FUNCTIONAL_SOURCE_DUPLICATES=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
