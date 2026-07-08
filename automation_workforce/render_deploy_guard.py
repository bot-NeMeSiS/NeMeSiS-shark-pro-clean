from __future__ import annotations

import urllib.error
import urllib.request
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import VERSION, env_bool, mask_secret, print_json, workflow_arg_parser, write_report


def run_render_deploy_guard(dry_run: bool = True) -> dict:
    enabled = env_bool("ENABLE_AUTOMATED_RENDER_DEPLOY", False)
    hook = os.getenv("RENDER_DEPLOY_HOOK_URL")
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")
    status = "DEPLOY_NOT_TRIGGERED_DISABLED"
    triggered = False
    error = ""
    if enabled and not dry_run and hook:
        try:
            req = urllib.request.Request(hook, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = f"DEPLOY_HOOK_TRIGGERED_HTTP_{resp.status}"
                triggered = 200 <= resp.status < 300
        except urllib.error.URLError as exc:
            status = "DEPLOY_HOOK_ERROR"
            error = str(exc)[:300]
    elif enabled and not hook and not (api_key and service_id):
        status = "DEPLOY_NOT_TRIGGERED_MISSING_SECRETS"
    elif dry_run:
        status = "DRY_RUN_NO_DEPLOY"
    payload = {
        "ok": True,
        "version": VERSION,
        "dry_run": dry_run,
        "automated_deploy_enabled": enabled,
        "deploy_triggered": triggered,
        "status": status,
        "deploy_hook_state": mask_secret(hook),
        "render_api_key_state": mask_secret(api_key),
        "render_service_id_state": mask_secret(service_id),
        "error": error,
        "next_action": "configure GitHub secrets and set ENABLE_AUTOMATED_RENDER_DEPLOY=1 only when authorized",
    }
    write_report("V915_RENDER_DEPLOY_WORKER_QA.md", "V915 Render Deploy Worker QA", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 render deploy guard").parse_args()
    print_json(run_render_deploy_guard(dry_run=args.dry_run))
