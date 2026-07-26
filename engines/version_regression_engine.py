"""Evidence-aware local version comparison for V939."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


CRITICAL_FILES = (
    "app.py",
    "VERSION.txt",
    "templates/base.html",
    "static/app.css",
    "render.yaml",
    "requirements.txt",
)
ROUTE_RE = re.compile(r"@app\.route\(\s*[\"']([^\"']+)[\"']")
FLAG_RE = re.compile(r"[\"'](has_v\d+_[a-z0-9_]+)[\"']\s*:")


def _hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _routes(root: Path) -> set[str]:
    return set(ROUTE_RE.findall(_text(root / "app.py")))


def _flags(root: Path) -> set[str]:
    return set(FLAG_RE.findall(_text(root / "app.py")))


def compare_versions(
    current_root: str | Path,
    baseline_root: str | Path,
    current_version: str,
    baseline_version: str = "V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_FINAL",
) -> dict[str, Any]:
    current = Path(current_root)
    baseline = Path(baseline_root)
    if not baseline.exists():
        return {
            "certification_state": "NOT_CERTIFIED",
            "baseline_version": baseline_version,
            "current_version": current_version,
            "comparisons": [],
            "regressions": [],
            "limitations": ["No existe un deploy root V938 comparable."],
        }
    file_changes = []
    for relative in CRITICAL_FILES:
        current_path = current / relative
        baseline_path = baseline / relative
        current_hash = _hash(current_path)
        baseline_hash = _hash(baseline_path)
        file_changes.append({
            "path": relative,
            "current_exists": current_path.exists(),
            "baseline_exists": baseline_path.exists(),
            "changed": current_hash != baseline_hash,
            "current_hash": current_hash[:16],
            "baseline_hash": baseline_hash[:16],
            "classification": "CHANGE_REQUIRES_EVIDENCE" if current_hash != baseline_hash else "UNCHANGED",
        })
    current_routes = _routes(current)
    baseline_routes = _routes(baseline)
    removed_routes = sorted(baseline_routes - current_routes)
    added_routes = sorted(current_routes - baseline_routes)
    current_flags = _flags(current)
    baseline_flags = _flags(baseline)
    removed_flags = sorted(baseline_flags - current_flags)
    regressions = []
    regressions.extend({"kind": "route_removed", "value": route, "classification": "PROBABLE_REGRESSION"} for route in removed_routes)
    regressions.extend({"kind": "runtime_flag_removed", "value": flag, "classification": "PROBABLE_REGRESSION"} for flag in removed_flags)
    return {
        "certification_state": "REQUIRES_REVIEW" if regressions else "PARTIALLY_VERIFIED",
        "baseline_version": baseline_version,
        "current_version": current_version,
        "file_changes": file_changes,
        "routes": {"baseline": len(baseline_routes), "current": len(current_routes), "added": added_routes, "removed": removed_routes},
        "runtime_flags": {"baseline": len(baseline_flags), "current": len(current_flags), "added": sorted(current_flags - baseline_flags), "removed": removed_flags},
        "regressions": regressions,
        "improvements": [],
        "not_comparable": ["visual_quality", "production_latency", "production_data", "telegram_delivery", "customer_behavior"],
        "limitations": [
            "Un cambio de hash nunca se clasifica por si solo como regresion.",
            "Las mejoras requieren checks, Browser QA o evidencia operacional adicional.",
        ],
    }


def build_version_regression_snapshot(root: str | Path, app_version: str) -> dict[str, Any]:
    base = Path(root) / "release_output" / "V938_DEPLOY_ROOT_CONTENTS"
    snapshot = compare_versions(root, base, app_version)
    snapshot.update({"database_written": False, "external_calls": 0, "production_modified": False})
    return snapshot
