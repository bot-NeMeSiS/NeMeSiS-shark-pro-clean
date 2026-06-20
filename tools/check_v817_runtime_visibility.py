from __future__ import annotations

import hashlib
import json
import pathlib
import re
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "V817_REFERENCE_PIXEL_POLISH_CLIENT_ADMIN_FINAL"
CURRENT_VERSION = "V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL"


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2))
    raise SystemExit(1)


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> None:
    app_py = read_text(ROOT / "app.py")
    version_txt = read_text(ROOT / "VERSION.txt").strip()
    base = read_text(ROOT / "templates" / "base.html")
    css_path = ROOT / "static" / "app.css"
    css = css_path.read_bytes()
    css_text = css.decode("utf-8", errors="replace")

    checks = {
        "version_txt": version_txt in {VERSION, CURRENT_VERSION},
        "app_version": f"APP_VERSION = '{VERSION}'" in app_py or f'APP_VERSION = "{VERSION}"' in app_py or f"APP_VERSION = '{CURRENT_VERSION}'" in app_py or f'APP_VERSION = "{CURRENT_VERSION}"' in app_py,
        "runtime_endpoint_exists": '@app.route("/api/runtime-version")' in app_py,
        "runtime_reports_v817": "has_v817_shell" in app_py and "has_v817_css" in app_py,
        "runtime_preserves_v816": "has_v816_shell" in app_py and "has_v816_css" in app_py,
        "runtime_reports_paths": "app_py_path" in app_py and "current_working_directory" in app_py and "template_base_path" in app_py,
        "runtime_reports_css": "static_app_css_hash" in app_py and "static_app_css_size" in app_py and "static_app_css_mtime" in app_py,
        "meta_version": f'name="nemesis-version" content="{VERSION}"' in base or f'name="nemesis-version" content="{CURRENT_VERSION}"' in base,
        "body_v817": 'data-v817-shell="true"' in base,
        "source_comment": "NEMESIS V817 REFERENCE PIXEL POLISH ACTIVE" in base,
        "cache_busting": f"?v={VERSION}" in base or f"?v={CURRENT_VERSION}" in base,
        "css_v817_layer": VERSION in css_text and "data-v817-shell" in css_text,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Fallan checks runtime V817: " + ", ".join(failed))

    release_dir = ROOT / "release_output"
    zips = sorted(release_dir.glob("*V817*RENDER_READY.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    zip_info = {}
    if zips:
        with zipfile.ZipFile(zips[0]) as zf:
            names = set(zf.namelist())
            zip_info = {
                "zip": str(zips[0]),
                "has_root_app": "app.py" in names,
                "has_root_templates": any(n.startswith("templates/") for n in names),
                "has_root_static": any(n.startswith("static/") for n in names),
                "has_nested_project": any(re.search(r"NeMeSiS shark pro/.+app\.py$", n) for n in names),
            }

    print(json.dumps({
        "ok": True,
        "version": VERSION,
        "css_hash": hashlib.sha256(css).hexdigest()[:16],
        "css_size": len(css),
        "checks": checks,
        "zip_info": zip_info,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


