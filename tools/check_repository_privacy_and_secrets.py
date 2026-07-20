#!/usr/bin/env python3
"""Redacted repository privacy and secret classification for V938.

The scanner reports only file, line, type, severity and a non-reversible hash
prefix. It never prints the matched value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "reports" / "V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.md"
REPORT_JSON = ROOT / "reports" / "V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.json"
try:
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    MADRID_TZ = datetime.now().astimezone().tzinfo

SCAN_DIRS = ["app.py", "automation_workforce", "blueprints", "engines", "services", "static", "templates", "tests", "tools", ".github"]
TEXT_SUFFIXES = {".py", ".html", ".js", ".css", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".sh", ".ps1"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "release_output", "browser_qa", "reference_images", "logs", "backups"}
SELF_FILES = {
    "tools/check_repository_privacy_and_secrets.py",
    "automation_workforce/security_secret_guard.py",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "critical"),
    ("github_token", re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{30,}\b"), "critical"),
    ("stripe_live_key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"), "critical"),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"), "critical"),
    ("telegram_bot_token", re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"), "critical"),
    ("aws_access_key", re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "critical"),
    ("render_or_generic_token", re.compile(r"\brnd_[A-Za-z0-9_-]{24,}\b"), "critical"),
]

ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(SECRET_KEY|AUTOMATION_SECRET|TELEGRAM_BOT_TOKEN|STRIPE_SECRET_KEY|STRIPE_WEBHOOK_SECRET|OPENAI_API_KEY|RENDER_API_KEY|RENDER_DEPLOY_HOOK_URL)\b\s*[:=]\s*['\"]([^'\"\r\n]{8,})['\"]"
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PRIVATE_ID_PATTERN = re.compile(r"\b(?:cus|sub|pi|cs|evt)_(?:live_)?[A-Za-z0-9]{14,}\b")

PLACEHOLDER_MARKERS = {
    "example",
    "invalid",
    "placeholder",
    "changeme",
    "replace_me",
    "your_",
    "xxxx",
    "***",
    "pytest",
    "test-secret",
    "local-secret",
    "dummy",
    "fake",
    "not-a-real",
    "v887-local-secret",
    "v888-autopilot-secret",
}


def madrid_now_iso() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def _hash_prefix(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _is_placeholder(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return not lowered or any(marker in lowered for marker in PLACEHOLDER_MARKERS) or lowered.startswith(("${", "{{", "<"))


def _iter_files(root: Path) -> Iterable[Path]:
    for item in SCAN_DIRS:
        path = root / item
        if path.is_file():
            yield path
            continue
        if not path.exists():
            continue
        for candidate in path.rglob("*"):
            if not candidate.is_file() or any(part in SKIP_DIRS for part in candidate.relative_to(root).parts):
                continue
            if candidate.suffix.lower() in TEXT_SUFFIXES and candidate.stat().st_size <= 4 * 1024 * 1024:
                yield candidate


def _finding(path: Path, root: Path, line: int, finding_type: str, severity: str, value: str, classification: str, recommendation: str) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "line": line,
        "type": finding_type,
        "severity": severity,
        "classification": classification,
        "value_hash_prefix": _hash_prefix(value),
        "value_length": len(value),
        "recommendation": recommendation,
        "value_redacted": True,
    }


def scan_repository(root: str | Path = ROOT, include_privacy: bool = True) -> dict[str, Any]:
    root_path = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    privacy: list[dict[str, Any]] = []
    examples_ignored = 0
    files_scanned = 0

    for forbidden_name in [".env", "id_rsa", "id_ed25519"]:
        candidate = root_path / forbidden_name
        if candidate.exists() and candidate.is_file():
            findings.append({
                "path": forbidden_name,
                "line": 1,
                "type": "forbidden_sensitive_file",
                "severity": "critical",
                "classification": "CONFIRMADO",
                "value_hash_prefix": _hash_prefix(forbidden_name),
                "value_length": 0,
                "recommendation": "Retirar del repositorio, rotar credenciales relacionadas y revisar historial.",
                "value_redacted": True,
            })

    for path in _iter_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scan_secrets = rel not in SELF_FILES
        is_test_fixture = rel.startswith("tests/") or (
            rel.startswith("tools/")
            and (path.name.startswith("check_") or path.name.endswith("_check_support.py"))
        )
        for line_no, line in enumerate(text.splitlines(), 1):
            if scan_secrets:
                for finding_type, pattern, severity in SECRET_PATTERNS:
                    for match in pattern.finditer(line):
                        value = match.group(0)
                        if _is_placeholder(value):
                            examples_ignored += 1
                            continue
                        findings.append(_finding(path, root_path, line_no, finding_type, severity, value, "CONFIRMADO", "Revocar/rotar el valor y eliminarlo del arbol e historial Git."))
                for match in ASSIGNMENT_PATTERN.finditer(line) if not is_test_fixture else ():
                    value = match.group(2)
                    if _is_placeholder(value):
                        examples_ignored += 1
                        continue
                    findings.append(_finding(path, root_path, line_no, "sensitive_literal_assignment", "high", value, "REQUIERE_REVISION", "Confirmar si es valor real; si lo es, rotar y mover a variable de entorno."))
            if include_privacy:
                for match in EMAIL_PATTERN.finditer(line):
                    value = match.group(0)
                    if value.lower().endswith(("@example.com", "@example.invalid", "@test.com", "@localhost")):
                        examples_ignored += 1
                        continue
                    privacy.append(_finding(path, root_path, line_no, "email_or_contact_identifier", "medium", value, "REQUIERE_REVISION", "Confirmar si es dato personal real o fixture; anonimizar evidencia si no es necesaria."))
                for match in PRIVATE_ID_PATTERN.finditer(line):
                    value = match.group(0)
                    privacy.append(_finding(path, root_path, line_no, "external_private_identifier", "medium", value, "REQUIERE_REVISION", "Confirmar entorno y necesidad; sustituir por fixture si no pertenece a runtime."))

    dedupe: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for item in findings:
        dedupe[(item["path"], item["line"], item["type"], item["value_hash_prefix"])] = item
    privacy_dedupe: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for item in privacy:
        privacy_dedupe[(item["path"], item["line"], item["type"], item["value_hash_prefix"])] = item
    secret_findings = list(dedupe.values())
    privacy_findings = list(privacy_dedupe.values())
    return {
        "ok": not secret_findings,
        "checked_at_madrid": madrid_now_iso(),
        "root": str(root_path),
        "files_scanned": files_scanned,
        "confirmed_secret_findings": sum(1 for item in secret_findings if item["classification"] == "CONFIRMADO"),
        "secret_review_findings": sum(1 for item in secret_findings if item["classification"] == "REQUIERE_REVISION"),
        "privacy_review_findings": len(privacy_findings),
        "examples_ignored": examples_ignored,
        "secret_findings": secret_findings,
        "privacy_findings": privacy_findings,
        "values_printed": False,
        "production_modified": False,
    }


def write_report(result: dict[str, Any]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# V938 Repository Privacy and Secret Classification",
        "",
        f"- Fecha Madrid: `{result['checked_at_madrid']}`",
        f"- Archivos revisados: **{result['files_scanned']}**",
        f"- Secretos confirmados: **{result['confirmed_secret_findings']}**",
        f"- Literales sensibles por revisar: **{result['secret_review_findings']}**",
        f"- Identificadores de privacidad por revisar: **{result['privacy_review_findings']}**",
        f"- Ejemplos ignorados: **{result['examples_ignored']}**",
        "- Valores impresos: **no**",
        "- Produccion modificada: **no**",
        "",
        "## Secretos y asignaciones sensibles",
    ]
    if result["secret_findings"]:
        for item in result["secret_findings"]:
            lines.append(f"- `{item['path']}:{item['line']}` - {item['type']} - **{item['classification']} / {item['severity']}** - hash `{item['value_hash_prefix']}`. {item['recommendation']}")
    else:
        lines.append("- No se detectaron valores con forma de secreto real en el alcance revisado.")
    lines.extend(["", "## Privacidad", "Los candidatos siguientes se registran sin mostrar el valor. No son una filtracion confirmada hasta revisar su contexto."])
    if result["privacy_findings"]:
        for item in result["privacy_findings"][:200]:
            lines.append(f"- `{item['path']}:{item['line']}` - {item['type']} - **REQUIERE REVISIÓN** - hash `{item['value_hash_prefix']}`.")
    else:
        lines.append("- Sin candidatos de privacidad fuera de fixtures reconocibles.")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="V938 redacted repository privacy and secret scan")
    parser.add_argument("--secret-only", action="store_true", help="Skip privacy identifiers and scan only secrets")
    parser.add_argument("--no-report", action="store_true", help="Do not write report files")
    args = parser.parse_args()
    result = scan_repository(ROOT, include_privacy=not args.secret_only)
    if not args.no_report:
        write_report(result)
    safe_summary = {key: value for key, value in result.items() if key not in {"secret_findings", "privacy_findings", "root"}}
    safe_summary["secret_finding_locations"] = [f"{item['path']}:{item['line']}" for item in result["secret_findings"]]
    print(json.dumps(safe_summary, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
