from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_PREFIXES = ("V890_", "V892_", "V893_", "V894_", "V895_", "V896_")
sys.path.insert(0, str(ROOT))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    version_txt = read("VERSION.txt").strip().lstrip("\ufeff")
    app_version_file = read("APP_VERSION").strip().lstrip("\ufeff")
    app_py = read("app.py")
    engine = read("engines/sentinel_issues_engine.py")
    template = read("templates/admin_sentinel_issues.html")

    require(version_txt.startswith(VERSION_PREFIXES), "VERSION.txt is not V890/V892/V893/V894/V895/V896 Sentinel issues lineage", failures)
    require(app_version_file == version_txt, "APP_VERSION does not match VERSION.txt", failures)
    require(f"APP_VERSION = '{version_txt}'" in app_py, "app.py APP_VERSION mismatch", failures)
    require((ROOT / "engines" / "sentinel_issues_engine.py").exists(), "sentinel_issues_engine.py missing", failures)
    require((ROOT / "templates" / "admin_sentinel_issues.html").exists(), "admin_sentinel_issues.html missing", failures)
    require("has_v890_sentinel_issues_command_center" in app_py, "runtime requested V890 issues flag missing", failures)
    require("has_v892_sentinel_issues_command_center" in app_py, "runtime V892 issues flag missing", failures)
    require("has_v891_telegram_premium_admin_endpoint_compatibility" in app_py, "V891 flag not preserved", failures)
    require("has_v890_runtime_dbpath_telegram_hardening" in app_py, "V890 DB flag not preserved", failures)
    require("has_v889_telegram_premium_picks_intelligence" in app_py, "V889 flag not preserved", failures)

    for route in [
        "/admin/sentinel-issues",
        "/admin/issues",
        "/admin/incidencias",
        "/admin/centro-incidencias",
        "/admin/sentinel-command-center",
        "/api/admin/sentinel/issues",
        "/api/admin/sentinel/issues/summary",
        "/api/admin/sentinel/issues/<issue_id>",
        "/api/admin/sentinel/issues/<issue_id>/status",
        "/api/admin/sentinel/issues/<issue_id>/resolve",
        "/api/admin/sentinel/issues/<issue_id>/reopen",
        "/api/admin/sentinel/issues/<issue_id>/codex-prompt",
        "/api/admin/sentinel/issues/scan",
        "/api/admin/sentinel/issues/sync-autopilot",
        "/api/admin/sentinel/issues/sync-visual-worker",
    ]:
        require(route in app_py, f"route missing: {route}", failures)

    for token in [
        "ISSUE_STATUSES",
        "sentinel_issues_memory.json",
        "generate_issue_prompt",
        "run_sentinel_issues_scan",
        "update_issue_status",
        "fingerprint",
        "occurrences",
        "last_seen_madrid",
    ]:
        require(token in engine, f"engine token missing: {token}", failures)

    for token in [
        "Copiar fallo",
        "Copiar prompt",
        "Copiar evidencia",
        "Checklist",
        "Marcar en revision",
        "Marcar como corregido",
        "Falso positivo",
        "Reabrir incidencia",
        "Escanear ahora",
        "Sincronizar AutoPilot",
        "Sincronizar Visual Worker",
        "data-copy",
        "data-issue-status",
    ]:
        require(token in template, f"template token missing: {token}", failures)

    require("javascript:void(0)" not in template and 'href="#"' not in template, "false links found in admin_sentinel_issues.html", failures)
    secret_surface = "\n".join([app_py, template])
    combined = "\n".join([app_py, engine, template])
    require(not re.search(r"(TELEGRAM_BOT_TOKEN\s*=\s*['\"][^'\"]+|AUTOMATION_SECRET\s*=\s*['\"][^'\"]+|sk_live_|bot[0-9]+:)", secret_surface), "possible secret assignment found", failures)
    require("apuesta segura" not in combined.lower(), "unsafe betting claim found", failures)

    for report in [
        "reports/V890_SENTINEL_ISSUES_COMMAND_CENTER_REPORT.md",
        "reports/V890_SENTINEL_COPY_CODEX_PROMPTS_QA.md",
        "reports/V890_AUTOPILOT_ISSUES_SYNC_QA.md",
        "reports/V890_ADMIN_ISSUES_PANEL_QA.md",
        "reports/V890_NEXT_STEPS.md",
    ]:
        require((ROOT / report).exists(), f"report missing: {report}", failures)

    os.environ["AUTOMATION_SECRET"] = "v892-secret"
    os.environ.pop("DB_PATH", None)
    import app  # noqa: WPS433

    client = app.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200", failures)
    runtime_json = runtime.get_json() or {}
    require(runtime_json.get("app_version") == version_txt, "runtime app_version mismatch", failures)
    require(runtime_json.get("has_v890_sentinel_issues_command_center") is True, "runtime V890 Sentinel issues flag false", failures)
    require(runtime_json.get("has_v892_sentinel_issues_command_center") is True, "runtime V892 Sentinel issues flag false", failures)

    for route in [
        "/api/admin/sentinel/issues",
        "/api/admin/sentinel/issues/summary",
        "/api/admin/sentinel/issues/scan",
        "/api/admin/sentinel/issues/sync-autopilot",
        "/api/admin/sentinel/issues/sync-visual-worker",
    ]:
        method = "post" if route.endswith(("scan", "sync-autopilot", "sync-visual-worker")) else "get"
        response = getattr(client, method)(route)
        require(response.status_code == 403, f"admin endpoint without session not 403: {route}", failures)
    require(client.get("/admin/sentinel-issues").status_code in {302, 303}, "admin page without session not redirected", failures)

    from engines.sentinel_issues_engine import normalize_sentinel_issue  # noqa: WPS433

    issue = normalize_sentinel_issue({
        "title": "Pick sin cuota no debe enviarse",
        "area": "telegram",
        "severity": "high",
        "route": "/telegram",
        "file": "engines/telegram_pick_quality_engine.py",
        "evidence": "Cuota pendiente",
    }, "check")
    require(issue.get("codex_prompt") and "Corrige esta incidencia" in issue["codex_prompt"], "Codex prompt not generated", failures)

    if failures:
        print("V890/V892/V893 Sentinel issues command center check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V890/V892/V893 Sentinel issues command center check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
