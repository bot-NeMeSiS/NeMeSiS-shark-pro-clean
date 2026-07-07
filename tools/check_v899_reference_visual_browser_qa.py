from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_WORKER_FINAL"
CURRENT_ALLOWED = {
    VERSION,
    "V900_REFERENCE_IMAGES_IMPORT_FIRST_REAL_VISUAL_GAP_AUDIT_FINAL",
    "V901_ADMIN_CONTINUOUS_SENTINEL_API_LAYOUT_RECOVERY_FINAL",
    "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL",
    "V902B_DEPLOY_ALIGNMENT_AND_AUTOMATION_SECRET_ROTATION_GUARD_FINAL",
    "V903_TOTAL_SENTINEL_AUTO_FIX_RENDER_ALIGNMENT_AND_STABILITY_FINAL",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def has_module(rel: str) -> bool:
    return (ROOT / rel).exists() and importlib.util.spec_from_file_location("check_mod", ROOT / rel) is not None


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    base = read("templates/base.html")
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")
    require(version_txt in CURRENT_ALLOWED, "VERSION.txt is not an allowed V899+ release", failures)
    require(app_version_file in CURRENT_ALLOWED, "APP_VERSION is not an allowed V899+ release", failures)
    require(any((f"APP_VERSION = '{item}'" in app_py or f'APP_VERSION = "{item}"' in app_py) for item in CURRENT_ALLOWED), "app.py APP_VERSION is not an allowed V899+ release", failures)
    require("has_v899_reference_visual_browser_qa_product_gap_worker" in app_py, "runtime flag V899 missing", failures)
    require('data-v899-shell="true"' in base, "base V899 shell marker missing", failures)

    for rel in [
        "engines/sentinel_reference_visual_engine.py",
        "engines/reference_image_manifest_engine.py",
        "engines/browser_visual_qa_engine.py",
        "engines/product_gap_engine.py",
        "engines/sentinel_codex_outbox_engine.py",
        "engines/autonomous_company_sentinel_engine.py",
        "tools/run_reference_visual_gap_scan.py",
        "tools/run_browser_reference_qa.py",
        "tools/check_v899_reference_visual_browser_qa.py",
    ]:
        require(has_module(rel), f"missing or invalid {rel}", failures)

    require((ROOT / "reference_images").exists(), "reference_images missing", failures)
    manifest_path = ROOT / "reference_images" / "reference_manifest.json"
    require(manifest_path.exists(), "reference_manifest.json missing", failures)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        require("items" in manifest, "reference manifest items missing", failures)
        require("reference_count" in manifest, "reference manifest count missing", failures)

    require("reference_scan" in app_py, "reference_scan mode missing in app.py", failures)
    outbox_engine_text = read("engines/sentinel_codex_outbox_engine.py")
    require("Prompts visuales / referencia" in outbox_engine_text or "VISUAL_REFERENCE_PROMPTS" in outbox_engine_text, "visual prompt outbox section missing", failures)
    require("Referencia visual" in read("templates/admin_autonomous_company_sentinel.html"), "admin reference visual section missing", failures)
    require("reference gap" in read("templates/admin_sentinel_issues.html").lower() or "visual gap" in read("templates/admin_sentinel_issues.html").lower(), "admin issues reference filters missing", failures)
    require("Prompts visuales" in read("templates/admin_sentinel_codex_outbox.html"), "admin outbox visual prompts missing", failures)
    require("pixel-perfect" not in read("reports/V899_REFERENCE_VISUAL_BROWSER_QA_PRODUCT_GAP_REPORT.md").lower(), "exact visual claim wording in V899 report", failures)

    for secret in ["TELEGRAM_BOT_TOKEN", "AUTOMATION_SECRET=", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"]:
        combined_reports = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (ROOT / "reports").glob("V899*.md"))
        require(secret not in combined_reports, f"secret-like token in V899 reports: {secret}", failures)

    if failures:
        print(json.dumps({"ok": False, "version": VERSION, "failures": failures}, ensure_ascii=False, indent=2))
        return 1
    print("V899 reference visual browser QA check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
