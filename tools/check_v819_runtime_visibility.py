#!/usr/bin/env python3
"""V819 runtime visibility and release-source checks."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "V819_REFERENCE_UI_DEDUP_LAYER_PURGE_CLIENT_ADMIN_FINAL"
PREVIOUS = "V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL"


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def fail(message: str, checks: dict[str, bool]) -> None:
    print(json.dumps({"ok": False, "error": message, "checks": checks}, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def main() -> None:
    app_py = read_text(ROOT / "app.py")
    version_txt = read_text(ROOT / "VERSION.txt").strip()
    base = read_text(ROOT / "templates" / "base.html")
    css_path = ROOT / "static" / "app.css"
    css_bytes = css_path.read_bytes()
    css = css_bytes.decode("utf-8", errors="replace")

    checks = {
        "version_txt_v819": version_txt == VERSION,
        "app_version_v819": f"APP_VERSION = '{VERSION}'" in app_py or f'APP_VERSION = "{VERSION}"' in app_py,
        "runtime_endpoint_exists": '@app.route("/api/runtime-version")' in app_py,
        "runtime_reports_v819": "has_v819_shell" in app_py and "has_v819_css" in app_py,
        "runtime_preserves_v818": "has_v818_shell" in app_py and "has_v818_css" in app_py and PREVIOUS in app_py,
        "meta_version_v819": f'name="nemesis-version" content="{VERSION}"' in base,
        "body_v819": 'data-v819-shell="true"' in base,
        "source_comment_v819": "NEMESIS V819 REFERENCE UI DEDUP LAYER PURGE ACTIVE" in base,
        "css_cache_busting_v819": f"?v={VERSION}" in base,
        "css_v819_layer": "V819 REFERENCE UI DEDUP LAYER PURGE START" in css and "data-v819-shell" in css,
        "css_preserves_v818_marker": PREVIOUS in css,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Fallan checks de visibilidad V819: " + ", ".join(failed), checks)

    zip_dirs = [ROOT.parent / "releases", ROOT / "release_output"]
    zips = sorted(
        [z for folder in zip_dirs if folder.exists() for z in folder.glob("*V819*RENDER_READY.zip")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    zip_info: dict[str, object] = {}
    if zips:
        with zipfile.ZipFile(zips[0]) as zf:
            names = set(zf.namelist())
            zip_info = {
                "zip": str(zips[0]),
                "has_root_app": "app.py" in names,
                "has_templates": any(n.startswith("templates/") for n in names),
                "has_static": any(n.startswith("static/") for n in names),
                "has_nested_project": any(re.search(r"NeMeSiS shark pro/.+app\.py$", n) for n in names),
            }

    print(json.dumps({
        "ok": True,
        "version": VERSION,
        "css_hash": hashlib.sha256(css_bytes).hexdigest()[:16],
        "css_size": len(css_bytes),
        "checks": checks,
        "zip_info": zip_info,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
