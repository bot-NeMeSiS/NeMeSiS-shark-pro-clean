from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation_workforce.common import ROOT, VERSION, print_json, workflow_arg_parser, write_report


SCAN_DIRS = ["app.py", "tools", "engines", "automation_workforce", "reports", "templates", ".github", "browser_qa"]
PATTERN = re.compile(r"(secret|token|api_key|apikey|password|RENDER_DEPLOY_HOOK_URL|RENDER_API_KEY)\s*[=:]\s*([^\s`'\"<>)]+)", re.IGNORECASE)
ALLOWED = {"hidden", "configured", "missing", "***hidden***", "***configured***", "***missing***", "$AUTOMATION_SECRET", "$RENDER_DEPLOY_HOOK_URL", "${{", "None", "False", "True"}


def candidate_files() -> list[Path]:
    files: list[Path] = []
    for rel in SCAN_DIRS:
        path = ROOT / rel
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for p in path.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in {".py", ".md", ".html", ".yml", ".yaml", ".txt", ".json", ".css", ".sh", ".ps1", ".bat"}:
                    continue
                if path.name == "tools" and p.name.startswith("check_v") and not p.name.startswith("check_v915"):
                    continue
                files.append(p)
    return files


def run_security_secret_guard(dry_run: bool = True) -> dict:
    findings = []
    for path in candidate_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in PATTERN.finditer(text):
            value = match.group(2).strip().strip(",.;")
            if value in ALLOWED or value.startswith("***") or value.startswith("$") or value.startswith("{") or value in {"1", "0", "false", "true"}:
                continue
            if value.startswith("codex-v") or value.startswith("customer."):
                continue
            if len(value) < 24:
                continue
            if any(fragment in value for fragment in ("os.getenv", "request.", "mask_secret", "env_present", ".get(", "getenv(", "secrets.token_urlsafe", "generate_csrf_token", "create_password_reset_token", "check_password_hash", "str(")):
                continue
            if re.fullmatch(r"[A-Z0-9_{}$.\-]+", value):
                continue
            if "AUTOMATION_SECRET" in value or "RENDER_" in value:
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append({"file": str(path.relative_to(ROOT)), "line": line, "kind": match.group(1), "value": "***masked***"})
            break
    payload = {
        "ok": not findings,
        "version": VERSION,
        "dry_run": dry_run,
        "files_scanned": len(candidate_files()),
        "findings_count": len(findings),
        "findings": findings[:20],
        "status": "ok" if not findings else "findings_require_review",
        "safe_message": "Secret Guard completo; los valores detectados se enmascaran.",
        "next_action": "continue" if not findings else "remove_or_mask_findings",
        "report_path": "reports/V918_SECRET_GUARD_RUN_QA.md",
        "secret_masking_policy": "configured/missing/hidden only",
    }
    write_report("V918_SECRET_GUARD_RUN_QA.md", "V918 Secret Guard Run QA", payload)
    return payload


if __name__ == "__main__":
    args = workflow_arg_parser("V915 security secret guard").parse_args()
    print_json(run_security_secret_guard(dry_run=args.dry_run))
