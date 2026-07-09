from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def app_version_from_source(app_py: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_py)
    return match.group(1) if match else ""


def service_worker_cache_from_source(app_py: str) -> str:
    match = re.search(r"const\s+NEMESIS_CACHE=['\"]NEMESIS_CACHE_(V[0-9]+[A-Z]?)['\"]", app_py)
    return match.group(1) if match else "unknown"


def git_remote_hint() -> str:
    config = read(".git/config")
    match = re.search(r"url\s*=\s*(.+)", config)
    return match.group(1).strip() if match else "unavailable"


def git_branch_hint() -> str:
    head = read(".git/HEAD").strip()
    if head.startswith("ref: refs/heads/"):
        return head.rsplit("/", 1)[-1]
    return head or "unavailable"


def main() -> int:
    app_py = read("app.py")
    base = read("templates/base.html")
    payload = {
        "ok": True,
        "root": str(ROOT),
        "generated_at_madrid": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds"),
        "version_txt": read("VERSION.txt").strip().lstrip("\ufeff"),
        "app_version_file": read("APP_VERSION").strip().lstrip("\ufeff"),
        "app_py_app_version": app_version_from_source(app_py),
        "git_remote_hint": git_remote_hint(),
        "git_branch_hint": git_branch_hint(),
        "has_v902": "V902_SENTINEL_FULL_ACTIVE_ISSUES_FIX_AND_TRUTH_CLEANUP_FINAL" in app_py
        and "data-v902-shell" in base,
        "has_v902b": "data-v902b-shell" in base and "mask_secret_for_url" in app_py,
        "has_v903": "data-v903-shell" in base and "has_v903_total_sentinel_auto_fix_render_alignment" in app_py,
        "has_v904": "data-v904-shell" in base and "has_v904_autonomous_reference_gaps_rebuild" in app_py,
        "has_v905": "data-v905-shell" in base and "has_v905_bom_version_alignment_fix" in app_py,
        "has_v906": "data-v906-shell" in base and "has_v906_real_browser_qa" in app_py,
        "has_v906b": "data-v906b-shell" in base and "has_v906b_public_home_html_artifact_cleanup" in app_py,
        "has_v907": "data-v907-shell" in base and "has_v907_browser_qa_enablement" in app_py,
        "has_v908": "data-v908-shell" in base and "has_v908_screenshot_based_reference_ui_fix" in app_py,
        "has_v909": "data-v909-shell" in base and "has_v909_browser_qa_pipeline" in app_py,
        "service_worker_cache": service_worker_cache_from_source(app_py),
        "secret_policy": "safe_placeholders_only",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
