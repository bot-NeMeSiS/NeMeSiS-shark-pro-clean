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
CURRENT = "V820_REAL_CRESTS_REFERENCE_VISUAL_PIXEL_POLISH_FINAL"
CURRENT_V821 = "V821_PRODUCTION_502_CRESTS_RUNTIME_HOTFIX"
CURRENT_V822 = "V822_PRODUCTION_STABILITY_RUNTIME_AUTOMATION_CRESTS_FINAL"
CURRENT_V823 = "V823_RENDER_VIDEO_REFERENCE_REAL_CRESTS_PIXEL_EXPERIENCE_FINAL"
CURRENT_V824 = "V824_RENDER_VIDEO_PIXEL_MATCH_FINAL_APP_EXPERIENCE"
CURRENT_V825 = "V825_SHARK_IDENTITY_FLOATING_BACKGROUND_REFERENCE_FINAL"
PREVIOUS = "V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL"
ACCEPTED_ACTIVE = {VERSION, CURRENT, CURRENT_V821, CURRENT_V822, CURRENT_V823, CURRENT_V824, CURRENT_V825}


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
        "version_txt_v819_or_newer": version_txt in ACCEPTED_ACTIVE,
        "app_version_v819_or_newer": any(
            f"APP_VERSION = '{value}'" in app_py or f'APP_VERSION = "{value}"' in app_py
            for value in ACCEPTED_ACTIVE
        ),
        "runtime_endpoint_exists": '@app.route("/api/runtime-version")' in app_py,
        "runtime_reports_v819": "has_v819_shell" in app_py and "has_v819_css" in app_py,
        "runtime_preserves_v818": "has_v818_shell" in app_py and "has_v818_css" in app_py and PREVIOUS in app_py,
        "meta_version_v819_or_newer": any(
            f'name="nemesis-version" content="{value}"' in base
            for value in ACCEPTED_ACTIVE
        ),
        "body_v819": 'data-v819-shell="true"' in base,
        "source_comment_v819": "NEMESIS V819 REFERENCE UI DEDUP LAYER PURGE ACTIVE" in base,
        "css_cache_busting_v819_or_newer": any(f"?v={value}" in base for value in ACCEPTED_ACTIVE),
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
