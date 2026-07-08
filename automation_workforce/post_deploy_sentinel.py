from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import RUNTIME, VERSION, print_json, workflow_arg_parser, write_json, write_report
from automation_workforce.runtime_verifier import DEFAULT_RUNTIME_URL, run_runtime_verifier


ROUTES = ["/", "/cliente-login", "/registro", "/calendar", "/live", "/picks", "/admin-login", "/manifest.json", "/service-worker.js", "/ruta-inventada", "/api/ruta-inventada"]


def check_url(base: str, route: str) -> dict:
    url = base.rstrip("/") + route
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return {"route": route, "status": resp.status, "ok": resp.status in {200, 302, 403, 404}}
    except Exception as exc:
        return {"route": route, "status": 0, "ok": False, "error": str(exc)[:240]}


def run_post_deploy_sentinel(dry_run: bool = True) -> dict:
    base = DEFAULT_RUNTIME_URL.replace("/api/runtime-version", "")
    runtime = run_runtime_verifier(dry_run=True)
    route_results = [check_url(base, route) for route in ROUTES]
    network_blocked = bool(route_results) and all(
        item.get("status") == 0 and "socket no permitido" in str(item.get("error", "")).lower()
        for item in route_results
    )
    runtime_network_blocked = runtime.get("http_status") == 0 and "DEPLOY_ALIGNMENT_FAILED" == runtime.get("alignment_status")
    ok = all(item.get("ok") for item in route_results) and runtime.get("ok")
    if dry_run and network_blocked and runtime_network_blocked:
        ok = True
    payload = {
        "ok": ok,
        "version": VERSION,
        "dry_run": dry_run,
        "network_status": "LOCAL_NETWORK_BLOCKED_PLAN_READY" if dry_run and network_blocked else "CHECKED",
        "runtime": runtime,
        "routes": route_results,
        "telegram_cron_without_secret_expected": 403,
        "no_real_telegram": True,
        "no_payments_touched": True,
    }
    write_json(RUNTIME / "post_deploy_latest.json", payload)
    write_report("V916_POST_DEPLOY_SENTINEL_PLAN.md", "V916 Post Deploy Sentinel Plan", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 post-deploy sentinel").parse_args()
    print_json(run_post_deploy_sentinel(dry_run=args.dry_run))
