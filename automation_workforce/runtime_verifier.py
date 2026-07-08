from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import VERSION, print_json, read_text, workflow_arg_parser, write_report


DEFAULT_RUNTIME_URL = "https://bot-apuestas-crgf.onrender.com/api/runtime-version"


def fetch_runtime(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw)
    except Exception as exc:
        return 0, {"ok": False, "error": str(exc)[:500]}


def run_runtime_verifier(dry_run: bool = True, expected_version: str | None = None, url: str | None = None) -> dict:
    expected = expected_version or read_text("VERSION.txt").strip().lstrip("\ufeff")
    target = url or os.getenv("PUBLIC_RUNTIME_URL") or DEFAULT_RUNTIME_URL
    status_code, runtime = fetch_runtime(target)
    actual = runtime.get("version") or runtime.get("runtime_version")
    aligned = actual == expected and runtime.get("version_files_match") is True and runtime.get("deployment_alignment_status") == "aligned_local_files"
    payload = {
        "ok": status_code == 200,
        "version": VERSION,
        "dry_run": dry_run,
        "runtime_url": target,
        "http_status": status_code,
        "expected_version": expected,
        "render_version": actual,
        "version_files_match": runtime.get("version_files_match"),
        "deployment_alignment_status": runtime.get("deployment_alignment_status"),
        "sentinel_active_issues_count": runtime.get("sentinel_active_issues_count"),
        "secret_masking_ok": runtime.get("secret_masking_ok"),
        "db_path": runtime.get("db_path"),
        "telegram_configured": runtime.get("telegram_configured"),
        "alignment_status": "ALIGNED" if aligned else "DEPLOY_ALIGNMENT_FAILED",
        "status": "ok" if aligned else ("network_unavailable" if status_code == 0 else "deploy_alignment_failed"),
        "safe_message": "Runtime verifier no expone secretos y no modifica produccion.",
        "next_action": "deploy_expected_version" if status_code == 200 and not aligned else ("retry_from_network_enabled_environment" if status_code == 0 else "post_deploy_sentinel"),
        "report_path": "reports/V917_RUNTIME_VERIFIER_RUN_QA.md",
    }
    write_report("V917_RUNTIME_VERIFIER_RUN_QA.md", "V917 Runtime Verifier Run QA", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 runtime verifier").parse_args()
    print_json(run_runtime_verifier(dry_run=args.dry_run))
