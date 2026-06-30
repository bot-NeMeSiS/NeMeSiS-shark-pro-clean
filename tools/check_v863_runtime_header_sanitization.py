from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL"
NEXT_VERSION = "V864_PC_MOBILE_VISUAL_REFERENCE_BIG_LEAP_REAL_SCREEN_QA_FINAL"
NEXT_NEXT_VERSION = "V865_SENTINEL_ISSUE_TO_IMPROVEMENT_WORKFLOW_FINAL"
V866 = "V866_REAL_RENDER_VISUAL_TELEGRAM_PICKS_PAYMENTS_HOTFIX_QA_FINAL"
V867 = "V867_RENDER_DEPLOYMENT_ALIGNMENT_AND_REAL_V866_CERTIFICATION_FINAL"
V868 = "V868_REAL_CLIENT_ADMIN_VISUAL_PRODUCTION_POLISH_AND_SENTINEL_VALUE_FINAL"
V868_PRO = "V868_PRO_MAX_CLIENT_ADMIN_MOBILE_VISUAL_REVENUE_SENTINEL_FINAL"
V869 = "V869_FULL_COMPANY_REFERENCE_ALIGNMENT_DEEP_CLEAN_VISUAL_REBUILD_FINAL"
V870 = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_FINAL"
V870_PRO_MAX = "V870_REFERENCE_STYLE_MATCH_AND_WORKSPACE_PURGE_PRO_MAX_FINAL"
V871 = "V871_VISIBLE_UI_DEFECTS_EMPTY_SPACE_SCREEN_BY_SCREEN_PRO_MAX_FINAL"


def fail(message: str) -> None:
    raise SystemExit(f"V863 runtime header sanitization FAILED: {message}")


def main() -> None:
    app_py = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    required = [
        "def sanitize_http_header_value",
        "def sanitize_runtime_value",
        "response.headers[key] = sanitize_http_header_value",
        "sanitize_runtime_value(v822_runtime_stability_snapshot())",
        "return jsonify(sanitize_runtime_value({",
    ]
    for needle in required:
        if needle not in app_py:
            fail(f"missing {needle}")

    import sys

    sys.path.insert(0, str(ROOT))
    import app  # noqa: WPS433

    client = app.app.test_client()
    response = client.get("/api/runtime-version")
    if response.status_code != 200:
        fail(f"runtime returned {response.status_code}")

    for key, value in response.headers.items():
        if "\n" in str(value) or "\r" in str(value):
            fail(f"header {key} contains a line break")

    payload = response.get_json() or json.loads(response.get_data(as_text=True))
    if payload.get("app_version") not in {VERSION, NEXT_VERSION, NEXT_NEXT_VERSION, V866, V867, V868, V868_PRO, V869, V870, V870_PRO_MAX, V871}:
        fail("runtime app_version is not V863/V864/V865/V866/V867/V868")
    if payload.get("has_v863_real_world_certification") is not True:
        fail("runtime flag has_v863_real_world_certification is not true")

    serialized = json.dumps(payload, ensure_ascii=False)
    if "Invalid header value b'" in serialized and "\\n" not in serialized:
        fail("unsafe raw header error serialization detected")
    print("V863 runtime header sanitization OK")


if __name__ == "__main__":
    main()


