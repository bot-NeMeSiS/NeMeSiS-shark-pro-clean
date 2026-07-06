"""Reference visual QA helpers for Autonomous Sentinel Worker."""
from __future__ import annotations

from pathlib import Path
from typing import Any


REFERENCE_DIRS = [
    "reference_images",
    "reports/reference_images",
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


REFERENCE_TARGETS = [
    {"category": "client", "screen_target": "/app", "expected_reference_folder": "reference_images/client"},
    {"category": "mobile", "screen_target": "/app mobile", "expected_reference_folder": "reference_images/mobile"},
    {"category": "admin", "screen_target": "/admin/dashboard", "expected_reference_folder": "reference_images/admin"},
    {"category": "picks", "screen_target": "/picks", "expected_reference_folder": "reference_images/picks"},
    {"category": "live", "screen_target": "/live", "expected_reference_folder": "reference_images/live"},
    {"category": "telegram", "screen_target": "/telegram", "expected_reference_folder": "reference_images/telegram"},
]


def classify_reference(path: str) -> dict[str, Any]:
    lower = path.lower()
    category = "general"
    for candidate in ("admin", "client", "mobile", "telegram", "picks", "live"):
        if f"/{candidate}/" in lower or lower.startswith(f"reference_images/{candidate}/"):
            category = candidate
            break
    target = next((item["screen_target"] for item in REFERENCE_TARGETS if item["category"] == category), "producto general")
    return {
        "filename": path,
        "category": category,
        "screen_target": target,
        "notes": "Referencia disponible para comparación visual cuando existan capturas reales.",
    }


def build_reference_gap_report(root: str | Path, visual_result: dict[str, Any] | None = None, browser_available: bool = False) -> dict[str, Any]:
    references = find_reference_assets(root)
    reference_items = [classify_reference(path) for path in references]
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
            "title": "REFERENCE_IMAGES_MISSING",
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
    else:
        issues.append({
            "title": "Referencia visual pendiente de browser QA",
            "area": "visual",
            "severity": "info",
            "source": "reference_qa",
            "route": "reference_images",
            "evidence": f"reference_count={len(references)}",
            "impact": "Hay referencias disponibles, pero la brecha visual requiere capturas reales para compararlas.",
            "recommendation": "Ejecutar tools/run_browser_reference_qa.py y comparar pantalla por pantalla.",
            "validation": ["Browser QA desktop/mobile"],
            "tags": ["visual", "reference", "browser"],
        })
    visual_issues = []
    if isinstance(visual_result, dict):
        visual_issues = [item for key in ("issues", "grouped_issues") for item in (visual_result.get(key) or []) if isinstance(item, dict)]
    return {
        "reference_assets": references,
        "reference_items": reference_items,
        "reference_count": len(references),
        "screen_targets": REFERENCE_TARGETS,
        "reference_gap_report": [
            {
                "screen_target": item["screen_target"],
                "references_available": [ref for ref in reference_items if ref["category"] == item["category"]],
                "gap_visual_detected": "Pendiente de capturas reales" if not browser_available else "Revisar captura real contra referencia",
                "priority": "high" if item["category"] in {"client", "mobile", "admin"} else "medium",
                "codex_prompt": f"Compara {item['screen_target']} contra referencias de {item['category']} y corrige solo diferencias visibles reales.",
            }
            for item in REFERENCE_TARGETS
        ],
        "browser_available": browser_available,
        "visual_worker_issues": visual_issues,
        "issues": issues,
        "notes": [
            "No se inventa comparacion visual si faltan referencias.",
            "Capturas reales requieren browser disponible.",
        ],
    }
