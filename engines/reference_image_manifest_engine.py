"""V899 reference image manifest helpers.

Builds a safe manifest from reference_images without moving or deleting files.
The manifest is structural evidence only; it never claims visual similarity
without real captures.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REFERENCE_IMAGE_MANIFEST_VERSION = "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL"
MADRID_TZ = ZoneInfo("Europe/Madrid")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
CATEGORY_TARGETS = {
    "admin": "/admin/dashboard",
    "client": "/app",
    "mobile": "/app mobile",
    "picks": "/picks",
    "live": "/live",
    "telegram": "/telegram",
    "shark": "/shark",
    "memberships": "/membresias",
    "dashboard": "/app",
    "calendar": "/calendar",
    "unknown": "producto general",
}


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def reference_root(root: str | Path) -> Path:
    return Path(root) / "reference_images"


def classify_reference_image(path: Path, root: str | Path) -> dict[str, Any]:
    base = Path(root)
    rel = path.relative_to(base).as_posix()
    lower = rel.lower()
    category = "unknown"
    for candidate in ("admin", "client", "mobile", "picks", "live", "telegram", "shark", "memberships", "dashboard", "calendar"):
        if f"/{candidate}/" in lower or lower.startswith(f"reference_images/{candidate}/") or candidate in path.stem.lower():
            category = candidate
            break
    priority = "high" if category in {"admin", "client", "mobile", "picks", "live"} else "medium" if category != "unknown" else "low"
    return {
        "filename": rel,
        "category": category,
        "screen_target": CATEGORY_TARGETS.get(category, "producto general"),
        "notes": "Clasificada por carpeta/nombre; requiere browser QA para comparacion real.",
        "priority": priority,
        "size_bytes": path.stat().st_size,
    }


def find_reference_images(root: str | Path) -> list[Path]:
    folder = reference_root(root)
    if not folder.exists():
        return []
    return sorted(path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)


def build_reference_manifest(root: str | Path, *, write: bool = True) -> dict[str, Any]:
    base = Path(root)
    folder = reference_root(base)
    folder.mkdir(parents=True, exist_ok=True)
    references = [classify_reference_image(path, base) for path in find_reference_images(base)]
    categories: dict[str, int] = {}
    for item in references:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    payload = {
        "version": REFERENCE_IMAGE_MANIFEST_VERSION,
        "generated_at_madrid": _now(),
        "reference_root": "reference_images",
        "reference_count": len(references),
        "categories": categories,
        "items": references,
        "safe_notes": [
            "No se mueven ni borran imagenes.",
            "No se declara similitud visual sin capturas reales.",
            "Si no hay imagenes, se genera manifest vacio y gap seguro.",
        ],
    }
    if write:
        (folder / "reference_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload

