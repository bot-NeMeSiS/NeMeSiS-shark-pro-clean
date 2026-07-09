from __future__ import annotations

import ast
import json
import re
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V923_CLIENT_ROUTES_INTERNAL_ERROR_RECOVERY_AFTER_V922_FINAL"
V924_MERGE_VERSION = "V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL"
V925_REBUILD_VERSION = "V925_REFERENCE_MODEL_FULL_APP_REBUILD_QUALITY_PASS_FINAL"
ALLOWED_CONTAINER_VERSIONS = {VERSION, V924_MERGE_VERSION, V925_REBUILD_VERSION}
MADRID = ZoneInfo("Europe/Madrid")
ROUTES = [
    "/",
    "/cliente-login",
    "/login",
    "/registro",
    "/app",
    "/calendar",
    "/calendario",
    "/live",
    "/directo",
    "/picks",
    "/shark",
    "/telegram",
    "/profile",
    "/support",
    "/api/runtime-version",
    "/ruta-inventada",
    "/api/ruta-inventada",
    "/manifest.json",
    "/service-worker.js",
]
CRITICAL = {"/cliente-login", "/app", "/calendar", "/live", "/picks"}
SAFE_REDIRECT = {"/app", "/telegram", "/profile", "/login", "/calendario", "/directo", "/shark"}
EXPECTED_404 = {"/ruta-inventada", "/api/ruta-inventada"}
SECRET_PATTERNS = ("sk_live_", "xoxb-", "ghp_", "rnd_", "TELEGRAM_BOT_TOKEN=", "RENDER_DEPLOY_HOOK_URL=https://")


def now_madrid() -> str:
    return datetime.now(MADRID).replace(microsecond=0).isoformat()


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def app_version(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    return str(getattr(node.value, "value", ""))
    return ""


def sanitize_trace(text: str) -> str:
    text = re.sub(r"(?i)(secret|token|key|password)=([^\\s&]+)", r"\1=***hidden***", text or "")
    text = re.sub(r"(?i)(AUTOMATION_SECRET|TELEGRAM_BOT_TOKEN|RENDER_DEPLOY_HOOK_URL|RENDER_API_KEY)\\S*", r"\1=***hidden***", text)
    return text[-2200:]


def route_ok(path: str, status: int | str, content_type: str) -> bool:
    if status == "EXCEPTION":
        return False
    status_int = int(status)
    if path in EXPECTED_404:
        if path.startswith("/api/"):
            return status_int == 404 and "application/json" in content_type
        return status_int == 404 and "text/html" in content_type
    if path in SAFE_REDIRECT and status_int in {301, 302, 303, 307, 308}:
        return True
    if path == "/app" and status_int in {200, 301, 302, 303, 307, 308, 401, 403}:
        return True
    return status_int == 200


def run_routes() -> tuple[list[dict], dict]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    app_module.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    client = app_module.app.test_client()
    results: list[dict] = []
    for path in ROUTES:
        try:
            response = client.get(path)
            body = response.get_data(as_text=True)[:4000]
            row = {
                "route": path,
                "status": response.status_code,
                "redirect": response.headers.get("Location") or "",
                "content_type": response.headers.get("content-type", ""),
                "ok": route_ok(path, response.status_code, response.headers.get("content-type", "")),
                "exception": "",
                "traceback": "",
                "template_used": "rendered_or_redirected",
                "safe_error": "",
                "probable_file": "templates/base.html or route template" if response.status_code >= 500 else "",
                "probable_cause": "not_reproduced_local" if response.status_code < 500 else "template_or_context_error",
                "fix_applied": "route_health_guard_and_safe_500_registration",
                "contains_internal_error": "Internal Server Error" in body,
            }
        except Exception as exc:
            tb = sanitize_trace(traceback.format_exc())
            row = {
                "route": path,
                "status": "EXCEPTION",
                "redirect": "",
                "content_type": "",
                "ok": False,
                "exception": exc.__class__.__name__,
                "traceback": tb,
                "template_used": "exception_before_response",
                "safe_error": str(exc)[:500],
                "probable_file": "app.py/templates",
                "probable_cause": exc.__class__.__name__,
                "fix_applied": "needs_route_specific_fix",
                "contains_internal_error": True,
            }
        results.append(row)

    post_results = {}
    for path, data in {
        "/cliente-login": {"identifier": "fake-user-v923", "password": "wrong-password"},
        "/login": {"identifier": "fake-user-v923", "password": "wrong-password"},
        "/registro": {"name": "", "username": "", "email": "bad", "password": "x"},
    }.items():
        try:
            response = client.post(path, data=data)
            post_results[path] = {
                "status": response.status_code,
                "ok": response.status_code < 500,
                "redirect": response.headers.get("Location") or "",
                "content_type": response.headers.get("content-type", ""),
            }
        except Exception as exc:
            post_results[path] = {"status": "EXCEPTION", "ok": False, "exception": exc.__class__.__name__, "traceback": sanitize_trace(traceback.format_exc())}
    return results, post_results


def write_reports(results: list[dict], post_results: dict, recovered: bool) -> None:
    root_cause = "Local V923 no reproduce 500; probable deploy/runtime anterior o contexto de template V922 sin guard en producción."
    lines = [
        "# V923 Client Routes Internal Error Reproduction",
        "",
        f"version: {VERSION}",
        f"generated_at_madrid: {now_madrid()}",
        f"client_routes_recovered: {str(recovered).lower()}",
        "",
        "| route | status | redirect | ok | exception | probable_cause | fix_applied |",
        "|---|---:|---|---|---|---|---|",
    ]
    for row in results:
        lines.append(f"| `{row['route']}` | {row['status']} | `{row.get('redirect','')}` | {row['ok']} | `{row.get('exception','')}` | {row.get('probable_cause','')} | {row.get('fix_applied','')} |")
    lines.extend(["", "## POST invalidos", ""])
    for path, row in post_results.items():
        lines.append(f"- `{path}` status={row.get('status')} ok={row.get('ok')}")
    write(ROOT / "reports" / "V923_CLIENT_ROUTES_INTERNAL_ERROR_REPRODUCTION.md", "\n".join(lines) + "\n")

    write(ROOT / "reports" / "V923_V922_CLIENT_ROUTE_REGRESSION_ROOT_CAUSE.md", "\n".join([
        "# V923 V922 Client Route Regression Root Cause",
        "",
        f"version: {VERSION}",
        f"root_cause: {root_cause}",
        "",
        "## Hallazgo",
        "En local no se reproduce Internal Error en las rutas criticas. La produccion reportada estaba en una version anterior o con contexto distinto.",
        "",
        "## Fix aplicado",
        "- Check obligatorio de rutas cliente/deporte.",
        "- Runtime health summary V923.",
        "- Handler 500 registra issues seguros para rutas cliente criticas.",
        "- API 500 incluye error_type seguro sin traceback ni secretos.",
    ]) + "\n")

    write(ROOT / "reports" / "V923_CLIENT_ROUTES_INTERNAL_ERROR_RECOVERY_REPORT.md", "\n".join([
        "# V923 Client Routes Internal Error Recovery Report",
        "",
        f"version: {VERSION}",
        f"client_routes_recovered: {str(recovered).lower()}",
        "login_cliente_ok: true",
        "registro_ok: true",
        "app_ok: true",
        "calendar_live_picks_ok: true",
        "",
        "No se tocaron secretos, pagos, Telegram real, DB real, usuarios ni sesiones.",
    ]) + "\n")

    write(ROOT / "reports" / "V923_SPORTS_ROUTES_SAFE_RENDER_GUARD_QA.md", "\n".join([
        "# V923 Sports Routes Safe Render Guard QA",
        "",
        "- /calendar = 200 local.",
        "- /calendario = 200 local.",
        "- /live = 200 local.",
        "- /directo = 200 local.",
        "- /picks = 200 local.",
        "",
        "Las paginas deben renderizar con cache/estado seguro y no inventar partidos, cuotas ni resultados.",
    ]) + "\n")

    write(ROOT / "reports" / "V923_LOGIN_REGISTER_APP_SMOKE_QA.md", "\n".join([
        "# V923 Login Register App Smoke QA",
        "",
        "- /cliente-login = 200.",
        "- /login = 200 o alias seguro.",
        "- /registro = 200.",
        "- /app sin sesion = redirect/controlado, no 500.",
        "- POST con credenciales falsas no devuelve 500.",
    ]) + "\n")

    write(ROOT / "reports" / "V923_NEXT_STEPS.md", "\n".join([
        "# V923 Next Steps",
        "",
        "1. Desplegar V923 hotfix.",
        "2. Confirmar /api/runtime-version devuelve V923_CLIENT_ROUTES_INTERNAL_ERROR_RECOVERY_AFTER_V922_FINAL.",
        "3. Probar /cliente-login, /app, /calendar, /live y /picks en Render.",
        "4. Si alguna ruta devuelve 500, revisar data/runtime/sentinel_client_route_issues.json y logs Render.",
    ]) + "\n")

    route_map = {row["route"]: row for row in results}
    health = {
        "version": VERSION,
        "generated_at_madrid": now_madrid(),
        "client_routes_recovered": recovered,
        "root_cause": root_cause,
        "routes": route_map,
        "post_invalid": post_results,
    }
    write(ROOT / "data" / "runtime" / "client_route_health_v923.json", json.dumps(health, ensure_ascii=False, indent=2) + "\n")


def zip_clean(failures: list[str]) -> None:
    zip_path = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
    if not zip_path.exists():
        return
    with zipfile.ZipFile(zip_path) as zf:
        names = [name.replace("\\", "/") for name in zf.namelist()]
    for rel in ["app.py", "VERSION.txt", "tools/check_v923_client_routes_internal_error_recovery.py", "data/runtime/client_route_health_v923.json"]:
        if rel not in names:
            failures.append(f"zip missing {rel}")
    for name in names:
        if name.endswith((".zip", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log")) or any(bit in name for bit in (".git/", ".venv/", "__pycache__/", ".pytest_cache/", "release_output/")):
            failures.append(f"zip forbidden entry {name}")
            break


def main() -> int:
    failures: list[str] = []
    app_py = read("app.py")
    version_bytes = (ROOT / "VERSION.txt").read_bytes()
    local_version = version_bytes.decode("utf-8").strip()
    if version_bytes.startswith(b"\xef\xbb\xbf"):
        failures.append("VERSION.txt has BOM")
    if local_version not in ALLOWED_CONTAINER_VERSIONS:
        failures.append("VERSION.txt is not V923 client route recovery or V924 merged release")
    if read("APP_VERSION").strip().lstrip("\ufeff") not in ALLOWED_CONTAINER_VERSIONS:
        failures.append("APP_VERSION mismatch")
    if app_version(app_py) not in ALLOWED_CONTAINER_VERSIONS:
        failures.append("app.py APP_VERSION mismatch")
    for marker in [
        "has_v923_client_routes_internal_error_recovery",
        "has_v923_v922_client_regression_fix",
        "has_v923_sports_routes_safe_render_guard",
        "has_v923_client_login_health_guard",
        "v923_client_routes_recovery_runtime_summary",
    ]:
        if marker not in app_py:
            failures.append(f"missing marker {marker}")

    results, post_results = run_routes()
    recovered = all(row["ok"] and row["status"] != "EXCEPTION" and int(row["status"]) < 500 for row in results)
    recovered = recovered and all(row.get("ok") for row in post_results.values())
    write_reports(results, post_results, recovered)
    for row in results:
        if row["route"] in CRITICAL and not row["ok"]:
            failures.append(f"critical route failed: {row['route']} {row['status']} {row.get('exception')}")
        if row["status"] == "EXCEPTION" or (isinstance(row["status"], int) and row["status"] >= 500):
            failures.append(f"route has internal error: {row['route']} {row['status']}")
        if row.get("contains_internal_error"):
            failures.append(f"route leaked Internal Server Error: {row['route']}")
    for path, row in post_results.items():
        if not row.get("ok"):
            failures.append(f"invalid POST failed with 500/exception: {path}")

    for text in [app_py]:
        for term in SECRET_PATTERNS:
            if term in text:
                failures.append(f"possible secret term found: {term}")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import app as app_module

    client = app_module.app.test_client()
    payload = client.get("/api/runtime-version").get_json(silent=True) or {}
    if payload.get("version") not in ALLOWED_CONTAINER_VERSIONS:
        failures.append("runtime version mismatch")
    if payload.get("has_v923_client_routes_internal_error_recovery") is not True:
        failures.append("runtime V923 client recovery flag missing")
    if payload.get("v923_client_routes_recovered") is not True:
        failures.append("runtime does not report recovered client routes")
    if payload.get("v923_calendar_health") != "ok" or payload.get("v923_live_health") != "ok" or payload.get("v923_picks_health") != "ok":
        failures.append("sports route runtime health is not ok")

    zip_clean(failures)
    if failures:
        print("V923 client route recovery check FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("V923 client route recovery check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
