from __future__ import annotations

import hashlib
import json
import pathlib
import re
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED"


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
        "version_txt": version_txt == VERSION,
        "app_version": f"APP_VERSION = '{VERSION}'" in app_py or f'APP_VERSION = "{VERSION}"' in app_py,
        "runtime_endpoint_exists": '@app.route("/api/runtime-version")' in app_py,
        "runtime_reports_app_version": "app_version" in app_py and "version_txt" in app_py,
        "runtime_reports_paths": "python_file_path" in app_py and "current_working_directory" in app_py,
        "runtime_reports_css": "static_css_hash" in app_py and "static_css_size" in app_py,
        "runtime_reports_flags": "api_football_configured" in app_py and "telegram_configured" in app_py and "the_odds_configured" in app_py,
        "meta_version": f'name="nemesis-version" content="{VERSION}"' in base,
        "body_v815": 'data-v815-shell="true"' in base,
        "source_comment": "NEMESIS V815 CLIENT SHELL ACTIVE" in base,
        "cache_busting": f"?v={VERSION}" in base,
        "client_backdrop": "v815-client-shark-backdrop" in base,
        "css_v815_layer": VERSION in css_text and "data-v815-shell" in css_text,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail("Fallan checks runtime V815: " + ", ".join(failed))

    release_dir = ROOT / "release_output"
    zips = sorted(release_dir.glob("*V815*RENDER_READY.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
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
