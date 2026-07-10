from __future__ import annotations

from v929_check_support import finish, prepare_app


def main() -> int:
    app_module = prepare_app()
    resolver_ok = app_module.resolve_safe_internal_route(
        endpoint="match_detail_page", values={"match_id": "v929-check"}, fallback="/calendar"
    )
    resolver_missing = app_module.resolve_safe_internal_route(
        endpoint="v929_endpoint_missing", values={}, fallback="/calendar"
    )
    client = app_module.app.test_client()
    responses = {
        route: client.get(route, follow_redirects=False)
        for route in (
            "/match/v929-id-inexistente", "/team/v929-id-inexistente",
            "/highlight/v929-id-inexistente",
        )
    }
    checks = {
        "resolver_builds_dynamic_url": resolver_ok.get("ok") is True and resolver_ok.get("url") == "/partido/v929-check",
        "missing_endpoint_safe_fallback": resolver_missing.get("ok") is False and resolver_missing.get("url") == "/calendar",
        "dynamic_missing_contextual_404": all(response.status_code == 404 for response in responses.values()),
        "dynamic_missing_no_500": all(response.status_code < 500 for response in responses.values()),
        "dynamic_missing_has_actions": all(
            b"/calendar" in response.data and b"/picks" in response.data and b"/app" in response.data
            for response in responses.values()
        ),
    }
    return finish("V929 dynamic routes", checks, {
        "statuses": {route: response.status_code for route, response in responses.items()},
        "resolver_ok": resolver_ok,
        "resolver_missing": resolver_missing,
    })


if __name__ == "__main__":
    raise SystemExit(main())
