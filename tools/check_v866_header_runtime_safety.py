from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
V867 = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"


def fail(message: str) -> None:
    raise SystemExit(f"V866 header/runtime safety FAILED: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")

    require("sanitize_http_header_value" in app_py, "header sanitizer missing")
    require("sanitize_runtime_error_value" in app_py, "runtime error sanitizer missing")
    require("last_error" in app_py and "sanitize_runtime_error_value" in app_py, "last_error not sanitized")
    require(read("VERSION.txt").strip() in {VERSION, V867}, "VERSION.txt not V866/V867")
    require(read("APP_VERSION").strip() in {VERSION, V867}, "APP_VERSION not V866/V867")
    require(VERSION in base or V867 in base, "base cache marker not V866/V867")
    require('data-v866-shell="true"' in base, "base missing data-v866-shell")
    require("V866 REAL RENDER VISUAL TELEGRAM PICKS PAYMENTS HOTFIX QA START" in css, "CSS V866 marker missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v866_runtime_check.sqlite"))
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    client = flask_app.app.test_client()
    response = client.get("/api/runtime-version")
    require(response.status_code == 200, f"runtime status {response.status_code}")
    payload = response.get_json() or {}
    require(payload.get("app_version") in {VERSION, V867}, "runtime app_version not V866/V867")
    require(payload.get("has_v866_real_render_visual_telegram_picks_payments") is True, "runtime V866 flag false")
    require("\n" not in str(payload.get("last_error", "")), "runtime last_error contains newline")
    require("\r" not in str(payload.get("last_error", "")), "runtime last_error contains carriage return")
    for header, value in response.headers.items():
        require("\n" not in str(value) and "\r" not in str(value), f"unsafe header value in {header}")

    print("V866 header/runtime safety OK")


if __name__ == "__main__":
    main()
