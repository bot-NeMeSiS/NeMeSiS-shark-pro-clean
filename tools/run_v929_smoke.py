from __future__ import annotations

import json

from v929_check_support import ROOT, VERSION, mock_session, prepare_app


def check_paths(client, paths: list[str], label: str) -> list[dict]:
    results = []
    for path in paths:
        response = client.get(path, follow_redirects=False)
        results.append({
            "profile": label,
            "path": path,
            "status": int(response.status_code),
            "ok": int(response.status_code) < 500,
            "content_type": response.headers.get("Content-Type", ""),
        })
    return results


def main() -> int:
    app_module = prepare_app()
    public = app_module.app.test_client()
    results = check_paths(public, [
        "/", "/cliente-login", "/login", "/registro", "/calendar", "/calendario",
        "/live", "/directo", "/picks", "/shark", "/telegram", "/support",
        "/admin-login", "/admin/dashboard", "/admin/automation-workforce",
        "/admin/navigation-integrity", "/api/runtime-version", "/manifest.json",
        "/service-worker.js", "/clientes", "/clients",
    ], "public")

    client = app_module.app.test_client()
    mock_session(client, "client")
    results += check_paths(client, [
        "/app", "/calendar", "/partidos", "/partidos-hoy", "/live", "/picks",
        "/track-record", "/historico", "/shark", "/telegram", "/profile",
        "/memberships", "/favoritos", "/clientes",
    ], "client_mock")

    admin = app_module.app.test_client()
    mock_session(admin, "admin")
    results += check_paths(admin, [
        "/admin/dashboard", "/admin/users", "/admin/memberships", "/admin/payments",
        "/admin/picks", "/admin/matches", "/admin/data-center",
        "/admin/telegram/command-center", "/admin/automation-workforce",
        "/admin/daily-automation", "/admin/autonomous-company-sentinel",
        "/admin/sentinel-issues", "/admin/sentinel-codex-outbox",
        "/admin/not-found-events", "/admin/launch-certification",
        "/admin/final-certification", "/admin/settings", "/admin/navigation-integrity",
        "/clientes",
    ], "admin_mock")

    dynamic = check_paths(client, [
        "/match/v929-id-inexistente", "/team/v929-id-inexistente",
        "/highlight/v929-id-inexistente", "/liga/slug-v929-inexistente",
    ], "dynamic_missing")
    results += dynamic
    html_404 = public.get("/ruta-inventada-v929")
    api_404 = public.get("/api/ruta-inventada-v929")
    false_login = public.post("/cliente-login", data={
        "login": "v929-invalid@example.invalid",
        "password": "invalid-local-check",
    })
    protected = {
        "/api/admin/navigation-integrity/summary": public.get("/api/admin/navigation-integrity/summary").status_code,
        "/api/admin/navigation-integrity/run": public.post("/api/admin/navigation-integrity/run").status_code,
        "/api/admin/navigation-integrity/issues": public.get("/api/admin/navigation-integrity/issues").status_code,
    }
    failures = [item for item in results if not item["ok"]]
    api_payload = api_404.get_json(silent=True) or {}
    checks = {
        "routes_no_500": not failures,
        "html_404_premium": html_404.status_code == 404 and b"Ruta no encontrada" in html_404.data,
        "api_404_safe_json": api_404.status_code == 404 and api_payload.get("error_type") == "not_found" and api_payload.get("ok") is False,
        "dynamic_resources_contextual_404": all(item["status"] == 404 for item in dynamic),
        "false_login_controlled": false_login.status_code < 500 and "/app" not in (false_login.headers.get("Location") or ""),
        "admin_apis_403": all(status == 403 for status in protected.values()),
    }
    payload = {
        "version": VERSION,
        "ok": all(checks.values()),
        "checks": checks,
        "routes_tested": len(results),
        "failures": failures,
        "protected_api_statuses": protected,
        "dangerous_actions_executed": False,
        "database": "temporary",
        "external_provider_calls": 0,
    }
    output = ROOT / "reports" / "V929_SMOKE_RESULTS.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
