"""V892 Render/local alignment helpers.

No external call is performed here by default. The caller can pass Render runtime
JSON when it has been fetched explicitly.
"""
from __future__ import annotations

from typing import Any
from engines.reliability_engine import production_drift


SENTINEL_RENDER_ALIGNMENT_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"


def build_render_alignment(local_runtime: dict[str, Any], render_runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    render_runtime = render_runtime or {}
    local_version = str(local_runtime.get("app_version") or local_runtime.get("version") or "")
    render_version = str(render_runtime.get("app_version") or render_runtime.get("version") or "")
    drift = production_drift({"runtime_version":local_version,
        "app_version":local_runtime.get("app_version"), "version_file":local_runtime.get("version_file"),
        "main_sha":local_runtime.get("main_sha"), "candidate_sha":local_runtime.get("candidate_sha") or local_runtime.get("git_commit_hint"),
        "runtime_sha":local_runtime.get("git_commit_hint"),
        "deployed_sha":render_runtime.get("deployed_sha") or render_runtime.get("git_sha") or render_runtime.get("git_commit_hint"),
        "render_sha":render_runtime.get("render_sha"), "deployed_version":render_version,
        "production_observed_at":render_runtime.get("observed_at")})
    aligned = drift["state"] == "ALIGNED_CONFIRMED"
    issues = []
    if not render_runtime:
        issues.append({
            "title": "Render runtime no consultado en este scan",
            "area": "render",
            "severity": "info",
            "evidence": "El worker no hace llamadas externas por defecto.",
            "recommendation": "Consultar /api/runtime-version durante QA de despliegue.",
        })
    elif not aligned:
        issues.append({
            "title": "Identidad de produccion divergente o no confirmada",
            "area": "render",
            "severity": "high" if drift["state"] == "MISALIGNED_CONFIRMED" else "info",
            "evidence": f"local={local_version or 'desconocido'} render={render_version or 'desconocido'}",
            "recommendation": "Revisar SHA y fecha de evidencia; no desplegar automaticamente.",
        })
    return {
        "engine_version": SENTINEL_RENDER_ALIGNMENT_VERSION,
        "local_version": local_version,
        "render_version": render_version or "No consultado",
        "aligned": aligned,
        "state": drift["state"],
        "identity": drift,
        "issues": issues,
        "safe_notes": ["No se declara produccion alineada sin runtime Render real."],
    }
