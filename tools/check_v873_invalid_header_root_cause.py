from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V873_REAL_PRODUCTION_VISUAL_LOGOS_SHARK_HEADER_FINAL"
VERSION_V874 = "V874_COMPANY_WIDE_PRODUCT_POLISH_VISUAL_DATA_SENTINEL_FINAL"
VERSION_V875 = "V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def fail(message: str) -> None:
    raise SystemExit(f"V873 invalid header root-cause check FAILED: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    app_py = read("app.py")
    provider_engine = read("engines/api_sports_provider_engine.py")

    require("def sanitize_http_header_value" in app_py, "HTTP header sanitizer missing")
    require("response.headers[key] = sanitize_http_header_value" in app_py, "response headers not sanitized")
    require("def sanitize_runtime_error_value" in app_py, "runtime error sanitizer missing")
    require("def runtime_error_state" in app_py, "runtime error state helper missing")
    require("def sanitize_provider_error" in provider_engine, "provider error sanitizer missing")
    require("Invalid header value histórico saneado" in provider_engine, "provider invalid-header safe message missing")
    require("last_error_state" in app_py, "runtime last_error_state missing")

    os.environ.setdefault("DB_PATH", str(ROOT / "tmp_v873_invalid_header.sqlite"))
    os.environ.setdefault("AUTOMATION_SECRET", "codex-v873-header")
    sys.path.insert(0, str(ROOT))
    import app as flask_app  # noqa: WPS433

    sanitized = flask_app.sanitize_runtime_error_value("Invalid header value b'abc\r\n'")
    require("Invalid header value b'" not in sanitized, "raw invalid header survives sanitizer")
    require("\n" not in sanitized and "\r" not in sanitized, "sanitized invalid header has line breaks")

    state = flask_app.runtime_error_state("Invalid header value b'abc'")
    require(state.get("status") == "Histórico saneado", "invalid header state is not historical/sanitized")

    client = flask_app.app.test_client()
    response = client.get("/api/runtime-version")
    require(response.status_code == 200, f"runtime status {response.status_code}")
    for key, value in response.headers.items():
        require("\n" not in str(value) and "\r" not in str(value), f"unsafe header value in {key}")
    payload = response.get_json() or json.loads(response.get_data(as_text=True))
    serialized = json.dumps(payload, ensure_ascii=False)
    require(payload.get("app_version") in {VERSION, VERSION_V874, VERSION_V875}, "runtime app_version not V873/V874")
    require(payload.get("has_v873_real_production_visual_logos_shark_header") is True, "runtime V873 flag false")
    require("Invalid header value b'" not in serialized, "runtime exposes raw invalid-header value")
    require(payload.get("static_css_cache_busting") is True, "CSS cache busting false")
    print("V873 invalid header root-cause OK")


if __name__ == "__main__":
    main()


