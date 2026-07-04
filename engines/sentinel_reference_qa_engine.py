"""Reference visual QA helpers for Autonomous Sentinel Worker."""
from __future__ import annotations

from pathlib import Path
from typing import Any


REFERENCE_DIRS = [
    "reports/reference_images",
    "reference_images",
    "docs/reference_ui",
    "imagenes bot proyecto",
    "static/reference",
]


def find_reference_assets(root: str | Path) -> list[str]:
    base = Path(root)
    assets: list[str] = []
    for rel in REFERENCE_DIRS:
        folder = base / rel
        if not folder.exists():
            continue
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            assets.extend(str(path.relative_to(base)) for path in folder.glob(pattern))
    return sorted(set(assets))


def build_reference_gap_report(root: str | Path, visual_result: dict[str, Any] | None = None, browser_available: bool = False) -> dict[str, Any]:
    references = find_reference_assets(root)
    issues: list[dict[str, Any]] = []
    if not browser_available:
        issues.append({
            "title": "Browser capture unavailable",
            "area": "visual",
            "severity": "low",
            "source": "reference_qa",
            "route": "browser",
            "evidence": "BROWSER_CAPTURE_UNAVAILABLE",
            "impact": "No se puede declarar pixel-perfect ni validar capturas reales en esta ejecucion.",
            "recommendation": "Ejecutar browser QA con Playwright cuando este disponible.",
            "validation": ["Browser QA desktop/mobile"],
            "tags": ["visual", "browser"],
        })
    if not references:
        issues.append({
            "title": "No hay imagenes de referencia locales",
            "area": "visual",
            "severity": "low",
            "source": "reference_qa",
            "route": "reference_images",
            "evidence": "REFERENCE_IMAGES_MISSING",
            "impact": "La comparacion visual queda limitada a reglas estaticas y no a fotos reales.",
            "recommendation": "Anadir referencias en reports/reference_images o docs/reference_ui.",
            "validation": ["Verificar carpeta de referencias"],
            "tags": ["visual", "reference"],
        })
    visual_issues = []
    if isinstance(visual_result, dict):
        visual_issues = [item for key in ("issues", "grouped_issues") for item in (visual_result.get(key) or []) if isinstance(item, dict)]
    return {
        "reference_assets": references,
        "reference_count": len(references),
        "browser_available": browser_available,
        "visual_worker_issues": visual_issues,
        "issues": issues,
        "notes": [
            "No se inventa comparacion visual si faltan referencias.",
            "Capturas reales requieren browser disponible.",
        ],
    }
