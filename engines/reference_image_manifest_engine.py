"""V900 reference image manifest helpers.

Builds a safe manifest from reference_images without moving or deleting files.
The manifest is structural evidence only; it never claims visual similarity
without real captures.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha1
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REFERENCE_IMAGE_MANIFEST_VERSION = "V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL"
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
    "profile": "/profile",
    "track-record": "/track-record",
    "dashboard": "/app",
    "calendar": "/calendar",
    "unknown": "producto general",
}

REFERENCE_TARGET_OVERRIDES = {
    "reference_import_v900_01.png": ("REF-01", "Admin Dashboard", "/admin/dashboard"),
    "reference_import_v900_02.png": ("REF-02", "Telegram Command Center", "/admin/telegram/command-center"),
    "reference_import_v900_03.png": ("REF-03", "Payments Admin", "/admin/payments"),
    "reference_import_v900_04.png": ("REF-04", "Automation Center", "/admin/automation-center"),
    "reference_import_v900_05.png": ("REF-05", "Data Marketplace", "/admin/data-marketplace"),
    "reference_import_v900_06.png": ("REF-06", "Real Launch", "/admin/real-launch"),
    "reference_import_v900_07.png": ("REF-07", "Picks Admin", "/admin/picks"),
    "reference_import_v900_08.png": ("REF-08", "Client Home", "/app"),
    "reference_import_v900_09.png": ("REF-09", "Directo", "/live"),
    "reference_import_v900_10.png": ("REF-10", "Partidos", "/calendar"),
    "reference_import_v900_11.png": ("REF-11", "Picks", "/picks"),
    "reference_import_v900_12.png": ("REF-12", "SHARK", "/shark"),
    "reference_import_v900_13.png": ("REF-13", "Track Record", "/track-record"),
    "reference_import_v900_14.png": ("REF-14", "Memberships", "/membresias"),
    "reference_import_v900_15.png": ("REF-15", "Profile", "/profile"),
    "reference_import_v900_16.png": ("REF-16", "Telegram Client", "/telegram"),
}

VISUAL_REGIONS = ["background", "shell", "first_viewport", "content", "actions"]
CATEGORY_CRITICAL_ELEMENTS = {
    "admin": ["sidebar", "topbar", "kpis", "tables", "actions"],
    "client": ["brand_shark", "atmospheric_shark", "sports_priority", "cards", "mobile_bottom_nav"],
    "live": ["competition", "teams", "crests", "score", "minute", "status"],
    "calendar": ["filters", "competition", "match_rows", "status", "match_navigation"],
    "picks": ["match", "selection", "odds", "shark_score", "status"],
    "shark": ["official_shark", "score", "confidence", "evidence", "risk"],
    "track-record": ["real_kpis", "filters", "results", "honest_empty_state"],
    "memberships": ["free", "pro", "elite", "cta"],
    "profile": ["identity", "plan", "security", "preferences", "logout"],
    "telegram": ["connection_state", "benefits", "plan", "actions"],
}


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def reference_root(root: str | Path) -> Path:
    return Path(root) / "reference_images"


def image_dimensions(path: Path) -> dict[str, int | None]:
    try:
        with path.open("rb") as handle:
            header = handle.read(32)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and header[12:16] == b"IHDR":
            return {"width": int.from_bytes(header[16:20], "big"), "height": int.from_bytes(header[20:24], "big")}
        if header[:2] == b"\xff\xd8":
            with path.open("rb") as handle:
                handle.read(2)
                while True:
                    marker = handle.read(2)
                    if len(marker) < 2:
                        break
                    while marker[0] != 0xFF:
                        marker = marker[1:] + handle.read(1)
                    code = marker[1]
                    size_bytes = handle.read(2)
                    if len(size_bytes) < 2:
                        break
                    size = int.from_bytes(size_bytes, "big")
                    if code in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                        handle.read(1)
                        height = int.from_bytes(handle.read(2), "big")
                        width = int.from_bytes(handle.read(2), "big")
                        return {"width": width, "height": height}
                    handle.seek(max(0, size - 2), 1)
    except Exception:
        pass
    return {"width": None, "height": None}


def classify_reference_image(path: Path, root: str | Path) -> dict[str, Any]:
    base = Path(root)
    rel = path.relative_to(base).as_posix()
    lower = rel.lower()
    category = "unknown"
    for candidate in ("track-record", "admin", "client", "mobile", "picks", "live", "telegram", "shark", "memberships", "profile", "dashboard", "calendar"):
        if f"/{candidate}/" in lower or lower.startswith(f"reference_images/{candidate}/") or candidate in path.stem.lower():
            category = candidate
            break
    priority = "high" if category in {"admin", "client", "mobile", "picks", "live"} else "medium" if category != "unknown" else "low"
    dims = image_dimensions(path)
    override = REFERENCE_TARGET_OVERRIDES.get(path.name)
    reference_id, screen, screen_target = override or (
        "REF-" + sha1(rel.encode("utf-8", errors="ignore")).hexdigest()[:8].upper(),
        category.replace("-", " ").title(),
        CATEGORY_TARGETS.get(category, "producto general"),
    )
    secondary: list[str] = []
    if category not in {"admin", "unknown"} and dims.get("width") and dims.get("height") and int(dims["width"] or 0) > int(dims["height"] or 0):
        secondary.extend(["desktop", "mobile"])
    return {
        "reference_id": reference_id,
        "filename": rel,
        "reference_file": rel,
        "category": category,
        "screen": screen,
        "viewport": ["desktop"] if category == "admin" else ["desktop", "mobile"],
        "visual_regions": list(VISUAL_REGIONS),
        "critical_elements": CATEGORY_CRITICAL_ELEMENTS.get(category, ["background", "navigation", "cards", "typography"]),
        "secondary_categories": secondary,
        "screen_target": screen_target,
        "notes": "Clasificada por carpeta/nombre; requiere browser QA para comparacion real.",
        "priority": priority,
        "size_bytes": path.stat().st_size,
        "width": dims.get("width"),
        "height": dims.get("height"),
        "source": "reference_images",
        "imported_at_madrid": _now(),
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
        "canonical_reference": len(references) == 16,
        "canonical_version": REFERENCE_IMAGE_MANIFEST_VERSION,
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
