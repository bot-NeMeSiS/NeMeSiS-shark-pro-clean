"""V892 Render/local alignment helpers.

No external call is performed here by default. The caller can pass Render runtime
JSON when it has been fetched explicitly.
"""
from __future__ import annotations

from typing import Any


SENTINEL_RENDER_ALIGNMENT_VERSION = "V892_AUTONOMOUS_COMPANY_SENTINEL_REFERENCE_CODEX_WORKFORCE_FINAL"


def build_render_alignment(local_runtime: dict[str, Any], render_runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    render_runtime = render_runtime or {}
    local_version = str(local_runtime.get("app_version") or local_runtime.get("version") or "")
    render_version = str(render_runtime.get("app_version") or render_runtime.get("version") or "")
    aligned = bool(render_version and local_version and render_version == local_version)
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
            "title": "Render y local no estan alineados",
            "area": "render",
            "severity": "high",
            "evidence": f"local={local_version or 'desconocido'} render={render_version or 'desconocido'}",
            "recommendation": "Subir raiz correcta a GitHub y ejecutar Clear build cache & deploy.",
        })
    return {
        "engine_version": SENTINEL_RENDER_ALIGNMENT_VERSION,
        "local_version": local_version,
        "render_version": render_version or "No consultado",
        "aligned": aligned,
        "issues": issues,
        "safe_notes": ["No se declara produccion alineada sin runtime Render real."],
    }
