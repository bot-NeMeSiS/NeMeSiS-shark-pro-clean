from __future__ import annotations

import ast
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V925_REFERENCE_MODEL_FULL_APP_REBUILD_QUALITY_PASS_FINAL"
ZIP = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
REQUIRED_ZIP_ROOT = {"app.py", "VERSION.txt", "requirements.txt", "templates", "static", "engines", "tools", "reports"}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def app_version(source: str) -> str:
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    return str(getattr(node.value, "value", ""))
    return ""


def audit_zip(failures: list[str]) -> dict:
    if not ZIP.exists():
        return {"status": "not_built_yet", "forbidden_count": None, "missing_required_root": None}
    forbidden = []
    with zipfile.ZipFile(ZIP) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist() if not name.endswith("/")]
    roots = {name.split("/", 1)[0] for name in names}
    missing = sorted(REQUIRED_ZIP_ROOT - roots)
    for name in names:
        low = name.lower()
        if low.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".log", ".pyc", ".pyo")) or any(
            marker in f"/{low}/" for marker in ("/.git/", "/.venv/", "/__pycache__/", "/.pytest_cache/", "/release_output/")
        ):
            forbidden.append(name)
    if forbidden:
        failures.append(f"ZIP contains forbidden entries: {forbidden[:3]}")
    if missing:
        failures.append(f"ZIP missing required root: {missing}")
    return {"status": "audited", "forbidden_count": len(forbidden), "missing_required_root": missing}


def main() -> int:
    failures: list[str] = []
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    version_text = version_bytes.decode("utf-8")
    app_source = read("app.py")
    css = read("static/app.css")
    home = read("templates/home.html")
    client = read("templates/client_app_center.html")
    calendar = read("templates/calendar.html")
    live = read("templates/live.html")
    picks = read("templates/picks.html")
    admin = read("templates/admin_dashboard.html")
    workforce = read("templates/admin_automation_workforce.html")

    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt has UTF-8 BOM")
    if version_text.strip() != VERSION:
        failures.append(f"VERSION.txt mismatch: {version_text.strip()}")
    if app_version(app_source) != VERSION:
        failures.append(f"APP_VERSION mismatch: {app_version(app_source)}")

    for marker in (
        "has_v925_reference_model_full_app_rebuild",
        "has_v925_home_reference_rebuild",
        "has_v925_client_dashboard_reference_rebuild",
        "has_v925_sports_data_reference_rebuild",
        "has_v925_admin_command_center_reference_rebuild",
        "has_v925_picks_odds_safe_rebuild",
    ):
        if marker not in app_source:
            failures.append(f"missing runtime flag {marker}")

    for name in (
        "get_safe_sports_calendar_context",
        "get_safe_live_context",
        "get_safe_picks_context",
        "get_safe_odds_context",
        "v925_reference_model_runtime_summary",
    ):
        if f"def {name}" not in app_source:
            failures.append(f"missing safe context {name}")

    required_css = (
        "/* V925 reference model full app rebuild */",
        ".v925-shell",
        ".v925-kpi-card",
        ".v925-status-chip",
        ".v925-command-card",
        ".v925-client-match-card",
        ".v925-sports-board",
        ".v925-admin-command-center",
    )
    for marker in required_css:
        if marker not in css:
            failures.append(f"missing CSS marker {marker}")

    if home.count('class="v925-public-hero v925-above-fold"') != 1:
        failures.append("home does not contain exactly one V925 public hero")
    if "v783-public-hero" in home:
        failures.append("legacy duplicate public hero still present")
    if "V925 client dashboard reference rebuild" not in client:
        failures.append("client dashboard V925 marker missing")
    if "V925 calendar reference rebuild" not in calendar:
        failures.append("calendar V925 marker missing")
    if "V925 live reference rebuild" not in live:
        failures.append("live V925 marker missing")
    if "V925 picks and odds safe reference rebuild" not in picks:
        failures.append("picks V925 marker missing")
    if "V925 admin command center reference rebuild" not in admin:
        failures.append("admin V925 marker missing")
    if "V925 automation workforce command center rebuild" not in workforce:
        failures.append("workforce V925 marker missing")

    if "Salir cliente" in "\n".join((admin, workforce)):
        failures.append("admin contains Salir cliente")
    for glued in ("Capturas0", "Comparaciones18"):
        if glued in "\n".join((admin, workforce)):
            failures.append(f"glued admin value found: {glued}")
    if 'href="/api/admin/continuous-sentinel/run"' in "\n".join((admin, workforce)):
        failures.append("direct admin run API href found")

    if "api_live_tracker = live_tracker_status(DB_PATH)" not in app_source or "if force_refresh:" not in app_source:
        failures.append("live route is not cache-first with explicit refresh gate")
    if "safe_picks_context.get('picks')" not in picks:
        failures.append("picks template is not using gated safe picks")
    if "v925_pixel_perfect_claim_allowed\": False" not in app_source:
        failures.append("pixel-perfect gate is not false")

    secret_prefixes = ("sk_live_", "xoxb-", "ghp_", "github_pat_", "rnd_")
    for rel in ("app.py", "static/app.css", "templates/home.html", "templates/admin_dashboard.html"):
        text = read(rel)
        for prefix in secret_prefixes:
            if prefix in text:
                failures.append(f"suspicious secret prefix in {rel}: {prefix}")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    client_http = app_module.app.test_client()
    routes = ["/", "/cliente-login", "/registro", "/app", "/calendar", "/calendario", "/live", "/directo", "/picks", "/shark", "/telegram", "/profile", "/support", "/admin-login", "/admin/dashboard", "/admin/automation-workforce", "/api/runtime-version", "/ruta-inventada", "/api/ruta-inventada", "/manifest.json", "/service-worker.js"]
    smoke = {}
    for route in routes:
        response = client_http.get(route, follow_redirects=False)
        smoke[route] = response.status_code
        if response.status_code >= 500:
            failures.append(f"route {route} returned {response.status_code}")
    if smoke.get("/") != 200 or smoke.get("/calendar") != 200 or smoke.get("/live") != 200 or smoke.get("/picks") != 200:
        failures.append(f"critical route status mismatch: {smoke}")
    if smoke.get("/ruta-inventada") != 404 or smoke.get("/api/ruta-inventada") != 404:
        failures.append("404 contract mismatch")
    runtime = client_http.get("/api/runtime-version").get_json() or {}
    if runtime.get("version") != VERSION or not runtime.get("version_files_match"):
        failures.append("runtime identity is not aligned with V925")

    for template in (ROOT / "templates").glob("*.html"):
        try:
            app_module.app.jinja_env.parse(template.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception as exc:
            failures.append(f"Jinja parse failed {template.name}: {exc.__class__.__name__}")

    zip_audit = audit_zip(failures)
    result = {
        "ok": not failures,
        "version": VERSION,
        "failures": failures,
        "smoke": smoke,
        "runtime": {
            "version": runtime.get("version"),
            "version_files_match": runtime.get("version_files_match"),
            "deployment_alignment_status": runtime.get("deployment_alignment_status"),
            "v925_browser_qa_still_required": runtime.get("v925_browser_qa_still_required"),
            "v925_pixel_perfect_claim_allowed": runtime.get("v925_pixel_perfect_claim_allowed"),
        },
        "zip_audit": zip_audit,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
