"""Governed experiment definitions for V939. No experiment is auto-started."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


SAFE_SURFACES = {"cta", "block_order", "copy", "landing", "upsell", "telegram_preview", "onboarding"}
PROHIBITED_SURFACES = {
    "security",
    "authentication",
    "privacy",
    "legal",
    "payments",
    "prices",
    "payouts",
    "picks",
    "odds",
    "risk",
    "stake",
}
REQUIRED_FIELDS = {"experiment_id", "hypothesis", "owner", "start", "end", "audience", "variants", "metric", "guardrails", "sample_size", "stop_condition"}


def validate_experiment_definition(experiment: dict[str, Any]) -> dict[str, Any]:
    item = dict(experiment or {})
    missing = sorted(field for field in REQUIRED_FIELDS if item.get(field) in (None, "", [], {}))
    surface = str(item.get("surface") or "").strip().lower()
    errors = []
    if surface in PROHIBITED_SURFACES:
        errors.append("PROHIBITED_SURFACE")
    elif surface not in SAFE_SURFACES:
        errors.append("SURFACE_NOT_ALLOWLISTED")
    variants = item.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        errors.append("AT_LEAST_TWO_VARIANTS_REQUIRED")
    try:
        sample_size = int(item.get("sample_size") or 0)
    except (TypeError, ValueError):
        sample_size = 0
    if sample_size <= 0:
        errors.append("POSITIVE_SAMPLE_SIZE_REQUIRED")
    errors.extend(f"MISSING_{field.upper()}" for field in missing)
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "surface": surface,
        "activation_state": "REQUIRES_REVIEW",
        "automatic_activation": False,
        "production_modified": False,
    }


def propose_experiment(experiment: dict[str, Any]) -> dict[str, Any]:
    validation = validate_experiment_definition(experiment)
    return {
        "experiment": dict(experiment or {}),
        "validation": validation,
        "state": "REQUIRES_REVIEW" if validation.get("valid") else "BLOCKED",
        "launch_executed": False,
        "approval_required": True,
    }


def _catalog_path(root: str | Path) -> Path:
    return Path(root) / "data" / "runtime" / "company_experiments.json"


def build_experimentation_snapshot(root: str | Path, app_version: str, environment: str = "local") -> dict[str, Any]:
    path = _catalog_path(root)
    raw: list[dict[str, Any]] = []
    state = "INSUFFICIENT_DATA"
    limitations = ["No hay experimentos activos por defecto."]
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw = payload.get("experiments", []) if isinstance(payload, dict) else []
            raw = [item for item in raw if isinstance(item, dict)][:200]
            state = "PARTIALLY_VERIFIED" if raw else "INSUFFICIENT_DATA"
        except (OSError, ValueError, json.JSONDecodeError):
            state = "REQUIRES_REVIEW"
            limitations.append("El catalogo local no se pudo validar.")
    proposals = [propose_experiment(item) for item in raw]
    return {
        "version": app_version,
        "environment": environment,
        "certification_state": state,
        "experiments": proposals,
        "counts": {
            "total": len(proposals),
            "valid": sum(1 for item in proposals if (item.get("validation") or {}).get("valid")),
            "blocked": sum(1 for item in proposals if item.get("state") == "BLOCKED"),
            "active": 0,
        },
        "safe_surfaces": sorted(SAFE_SURFACES),
        "prohibited_surfaces": sorted(PROHIBITED_SURFACES),
        "automatic_activation": False,
        "production_modified": False,
        "limitations": limitations,
    }

