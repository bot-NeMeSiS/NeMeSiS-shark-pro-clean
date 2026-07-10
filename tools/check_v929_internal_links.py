from __future__ import annotations

from v929_check_support import ROOT, finish, prepare_app


def main() -> int:
    app_module = prepare_app()
    from engines.navigation_integrity_engine import build_navigation_integrity_snapshot

    snapshot = build_navigation_integrity_snapshot(
        app_module.app,
        ROOT,
        aliases=app_module.V896_ROUTE_ALIASES,
        include_smoke=True,
    )
    checks = {
        "links_audited": int(snapshot.get("links_audited") or 0) > 800,
        "broken_links_zero": int(snapshot.get("broken_links") or 0) == 0,
        "known_404_zero": int(snapshot.get("broken_404") or 0) == 0,
        "endpoint_missing_zero": int(snapshot.get("endpoint_missing") or 0) == 0,
        "redirect_loops_zero": int(snapshot.get("redirect_loops") or 0) == 0,
        "buttons_without_action_zero": int(snapshot.get("buttons_without_action") or 0) == 0,
        "important_orphans_zero": int(snapshot.get("orphan_templates") or 0) == 0,
        "smoke_no_500_or_loop": not (snapshot.get("smoke") or {}).get("failures"),
    }
    return finish("V929 internal links", checks, {
        "routes_total": snapshot.get("routes_total"),
        "links_audited": snapshot.get("links_audited"),
        "historical_templates_archived": snapshot.get("archived_orphan_templates"),
    })


if __name__ == "__main__":
    raise SystemExit(main())
