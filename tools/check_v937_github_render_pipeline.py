"""Compatibility regression guard for the active GitHub-to-Render pipeline."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "render-deploy.yml"
CERTIFIER = ROOT / "tools" / "v937_post_deploy_certification.py"
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    workflow = WORKFLOW.read_text(encoding="utf-8")
    certifier = CERTIFIER.read_text(encoding="utf-8")
    app_text = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    version_text = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()

    require(bool(VERSION) and version_text == VERSION, "VERSION.txt has no active release identity", errors)
    require(VERSION in app_text, "APP_VERSION does not match the active release identity", errors)
    require("pull_request:" in workflow and "push:" in workflow and "workflow_dispatch:" in workflow,
            "workflow triggers are incomplete", errors)
    require(workflow.count("branches: [main]") >= 2, "main branch filters are missing", errors)
    require('python-version: "3.11.9"' in workflow, "CI Python does not match Render", errors)
    require('cache: "pip"' in workflow and "cache-dependency-path: requirements.txt" in workflow,
            "safe pip cache is missing", errors)
    require("permissions:\n  contents: read" in workflow, "minimum permissions are missing", errors)
    require("concurrency:" in workflow and "cancel-in-progress: true" in workflow,
            "deployment concurrency guard is missing", errors)
    require("timeout-minutes:" in workflow, "workflow timeout is missing", errors)
    require("environment:\n      name: production" in workflow, "production environment is missing", errors)
    require("persist-credentials: false" in workflow, "checkout credential persistence is not disabled", errors)
    require("RENDER_DEPLOY_HOOK_URL" not in workflow, "deploy hook must not coexist with Auto-Deploy", errors)
    require("curl -fsS -X POST" not in workflow, "workflow still triggers a deploy hook", errors)
    require("pipeline-dry-run" in workflow and "--mode dry-run" in workflow,
            "network-free dry-run is missing", errors)
    require("--expected-sha" in workflow and "git_commit_hint" in certifier,
            "exact SHA verification is missing", errors)
    require("0,120,300,900,3600" in workflow, "post-deploy observation windows are incomplete", errors)
    require("public_stale_live" in certifier and "false_live" in certifier,
            "live evidence certification is missing", errors)
    require("POST" not in certifier and "DELETE" not in certifier,
            "post-deploy certifier must remain read-only", errors)

    required_steps = [
        "Checkout",
        "Set up Python",
        "Upgrade pip",
        "Install production dependencies",
        "Verify installed imports",
        "Compile Python",
        "Parse Jinja",
        "Critical release checks",
        "Navigation Integrity",
        "Continuous Sentinel",
        "Secret Guard",
        "Route and link audit",
        "Release and manifest identity",
        "Authorize auto-deploy certification",
    ]
    positions = [workflow.find(f"- name: {name}") for name in required_steps]
    require(all(position >= 0 for position in positions), "one or more preflight steps are missing", errors)
    require(positions == sorted(positions), "preflight steps are out of safe order", errors)

    install_position = workflow.find("python -m pip install -r requirements.txt")
    import_position = workflow.find("import app")
    workforce_check_position = workflow.find("check_v915_automated_company_workforce.py")
    require(install_position >= 0, "requirements installation is missing", errors)
    require(import_position > install_position, "app is imported before requirements are installed", errors)
    require(workforce_check_position > install_position,
            "workforce check runs before requirements are installed", errors)

    dry_run = subprocess.run(
        [
            sys.executable,
            str(CERTIFIER),
            "--mode", "dry-run",
            "--base-url", "https://bot-apuestas-crgf.onrender.com",
            "--expected-version", VERSION,
            "--expected-sha", "261213048fe3f92a58488b1119092922cdfc5db5",
            "--check-offsets", "0,120,300,900,3600",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    require(dry_run.returncode == 0, "post-deploy dry-run failed", errors)
    require('"network_requests": 0' in dry_run.stdout, "dry-run may perform network requests", errors)
    require('"deploy_requested": false' in dry_run.stdout.lower(), "dry-run may request deploy", errors)

    if re.search(r"(?:AUTOMATION_SECRET|TELEGRAM_BOT_TOKEN|STRIPE_SECRET_KEY)\s*[:=]\s*[^$\n][^\n]+", workflow):
        errors.append("workflow appears to contain a literal production secret")

    if errors:
        print("V937_GITHUB_RENDER_PIPELINE_CHECK=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("V937_GITHUB_RENDER_PIPELINE_CHECK=PASS")
    print("strategy=RENDER_AUTO_DEPLOY")
    print("preflight_dependency_order=PASS")
    print("dry_run_network_requests=0")
    print("deploy_hook_present=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
