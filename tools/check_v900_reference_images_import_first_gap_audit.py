from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V900_REFERENCE_IMAGES_IMPORT_FIRST_REAL_VISUAL_GAP_AUDIT_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V901_ADMIN_CONTINUOUS_SENTINEL_API_LAYOUT_RECOVERY_FINAL",
    "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")

    require(version_txt in CURRENT_ALLOWED, "VERSION.txt is not V900/V901", failures)
    require(app_version_file in CURRENT_ALLOWED, "APP_VERSION file is not V900/V901", failures)
    require(app_version_from_source(app_py) in CURRENT_ALLOWED, "app.py APP_VERSION is not V900/V901", failures)
    require("has_v900_reference_images_import_first_real_visual_gap_audit" in app_py, "runtime V900 flag missing", failures)
    require('data-v900-shell="true"' in base, "base V900 shell marker missing", failures)

    reference_root = ROOT / "reference_images"
    images = sorted(path for path in reference_root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    require(bool(images), "reference_images contains no real images", failures)

    manifest_path = reference_root / "reference_manifest.json"
    require(manifest_path.exists(), "reference_manifest.json missing", failures)
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        items = manifest.get("items") or []
        require(manifest.get("reference_count") == len(images), "manifest reference_count does not match image files", failures)
        require(len(items) == len(images), "manifest items do not match image files", failures)
        require(all(item.get("filename") and item.get("category") and item.get("screen_target") for item in items), "manifest item missing filename/category/screen_target", failures)
        require(all(item.get("source") == "reference_images" for item in items), "manifest item source must be reference_images", failures)
        require(all(item.get("imported_at_madrid") for item in items), "manifest item missing imported_at_madrid", failures)
        require(all(item.get("width") and item.get("height") for item in items), "manifest item missing width/height", failures)
        require("admin" in (manifest.get("categories") or {}), "manifest missing admin category", failures)
        require("client" in (manifest.get("categories") or {}), "manifest missing client category", failures)
        require("picks" in (manifest.get("categories") or {}), "manifest missing picks category", failures)
        require("live" in (manifest.get("categories") or {}), "manifest missing live category", failures)

    gap_path = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
    require(gap_path.exists(), "reference_gap_report.json missing", failures)
    if gap_path.exists():
        gap = json.loads(gap_path.read_text(encoding="utf-8"))
        require(gap.get("reference_count", 0) > 0, "gap report did not receive imported references", failures)
        require(gap.get("gaps") or gap.get("issues"), "gap report has no gaps/issues", failures)
        require("REFERENCE_IMAGES_MISSING" not in gap_path.read_text(encoding="utf-8"), "gap report still claims missing reference images", failures)

    outbox = ROOT / "data" / "runtime" / "autonomous_company_sentinel" / "outbox" / "codex_outbox.md"
    if outbox.exists():
        outbox_text = outbox.read_text(encoding="utf-8", errors="replace")
        require("Prompts visuales / referencia" in outbox_text or "VISUAL_REFERENCE_PROMPTS" in outbox_text, "outbox missing visual prompts section", failures)
        require("REFGAP-" in outbox_text, "outbox missing reference gap prompts", failures)

    reports_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "reports").glob("V900*.md"))
    require("pixel-perfect" not in reports_text.lower(), "V900 reports claim pixel-perfect", failures)
    for secret in ["TELEGRAM_BOT_TOKEN", "AUTOMATION_SECRET=", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"]:
        require(secret not in reports_text, f"secret-like token in V900 reports: {secret}", failures)

    zip_path = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
        require(any(name.startswith("reference_images/") and Path(name).suffix.lower() in IMAGE_SUFFIXES for name in names), "release zip does not include reference images", failures)
        forbidden = [name for name in names if name.startswith((".git/", ".venv/", "release_output/")) or name.endswith((".db", ".sqlite", ".zip"))]
        require(not forbidden, f"release zip contains forbidden files: {forbidden[:8]}", failures)

    if failures:
        print(json.dumps({"ok": False, "version": VERSION, "failures": failures}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "version": VERSION, "reference_images": len(images), "categories": manifest.get("categories", {})}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
