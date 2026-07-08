from __future__ import annotations

import urllib.error
import urllib.request
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import VERSION, env_bool, mask_secret, print_json, write_report


def run_render_deploy_guard(dry_run: bool = True, check_config: bool = False, trigger_deploy: bool = False) -> dict:
    enabled = env_bool("ENABLE_AUTOMATED_RENDER_DEPLOY", False)
    hook = os.getenv("RENDER_DEPLOY_HOOK_URL")
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")
    has_hook = bool(hook)
    has_api = bool(api_key and service_id)
    ready = enabled and (has_hook or has_api)
    status = "dry_run_disabled"
    triggered = False
    error = ""
    next_action = "enable_flag_and_configure_secret"

    if not enabled:
        status = "dry_run_disabled"
        next_action = "set ENABLE_AUTOMATED_RENDER_DEPLOY=1 only after Damian authorizes automated deploy"
    elif enabled and not (has_hook or has_api):
        status = "missing_deploy_hook"
        next_action = "configure RENDER_DEPLOY_HOOK_URL as a GitHub/Render secret"
    elif enabled and (has_hook or has_api):
        status = "ready"
        next_action = "run --trigger-deploy only with explicit authorization"

    if trigger_deploy and enabled and hook:
        try:
            req = urllib.request.Request(hook, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = f"deploy_hook_triggered_http_{resp.status}"
                triggered = 200 <= resp.status < 300
        except urllib.error.URLError as exc:
            status = "deploy_hook_error"
            error = str(exc)[:300]
    elif trigger_deploy and not enabled:
        status = "deploy_blocked_not_authorized"
        error = "ENABLE_AUTOMATED_RENDER_DEPLOY is not 1."
    elif trigger_deploy and enabled and not hook:
        status = "deploy_blocked_missing_deploy_hook"
        error = "RENDER_DEPLOY_HOOK_URL is missing."

    payload = {
        "ok": True,
        "version": VERSION,
        "dry_run": dry_run,
        "check_config": check_config,
        "trigger_deploy_requested": trigger_deploy,
        "automated_deploy_enabled": enabled,
        "deploy_ready": ready,
        "deploy_triggered": triggered,
        "status": status,
        "deploy_hook_state": mask_secret(hook),
        "render_api_key_state": mask_secret(api_key),
        "render_service_id_state": mask_secret(service_id),
        "error": error,
        "next_action": next_action,
    }
    write_report("V916_RENDER_DEPLOY_GUARD_DRY_RUN_QA.md", "V916 Render Deploy Guard Dry-Run QA", payload)
    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V916 render deploy guard")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--trigger-deploy", action="store_true")
    args = parser.parse_args()
    print_json(run_render_deploy_guard(dry_run=args.dry_run, check_config=args.check_config, trigger_deploy=args.trigger_deploy))
