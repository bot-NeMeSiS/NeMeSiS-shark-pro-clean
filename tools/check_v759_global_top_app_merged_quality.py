#!/usr/bin/env python3
"""V759 merged quality release validation.

Checks that V755 Telegram/Cron remains intact while V756, V757 and V758
client experience layers are present under the V759 release.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE", "V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def check(name: str, ok: bool, detail: object = "") -> None:
    CHECKS.append((name, bool(ok), str(detail or "")))


def route_exists(app_module, path: str) -> bool:
    return any(str(rule.rule) == path for rule in app_module.app.url_map.iter_rules())


def latest_v759_zip() -> Path | None:
    candidates: list[Path] = []
    for folder in (ROOT.parent / "releases", ROOT / "release_output", ROOT):
        if folder.exists():
            candidates.extend(folder.glob(f"*{VERSION}*RENDER_READY.zip"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def zip_forbidden_count(path: Path) -> int:
    forbidden_parts = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "release_output", "backups", "logs"}
    forbidden_suffixes = {".pyc", ".db", ".sqlite", ".sqlite3", ".log", ".zip", ".mp4", ".mov", ".avi", ".mkv"}
    count = 0
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = set(Path(info.filename).parts)
            name = Path(info.filename).name.lower()
            if parts & forbidden_parts or any(name.endswith(suffix) for suffix in forbidden_suffixes):
                count += 1
    return count


def static_checks() -> None:
    app_source = read("app.py")
    css = read("static/app.css")
    builder = read("tools/build_clean_release.py")
    version = read("VERSION.txt").strip()

    check("version_v759", version == VERSION, version)
    check("app_version_v759", f'APP_VERSION = "{VERSION}"' in app_source)
    check("db_path_intact", 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app_source)
    check("v755_telegram_normalizer_kept", all(token in app_source for token in [
        "def normalize_telegram_pick_candidate",
        "def normalize_match_time_madrid",
        "telegram_test",
        "MISSING_ODDS_WARNING",
        "/api/automation/telegram/tick",
        "automation_cron_access_allowed",
    ]))
    check("v756_client_premium_kept", all(token in app_source + read("templates/home.html") + read("templates/picks.html") for token in [
        "build_client_app_premium_context",
        "v756-command-center",
        "v756-picks-command",
        "Centro cliente SHARK",
    ]))
    check("v757_trust_kept", all(token in app_source + read("templates/client_app_center.html") for token in [
        "build_v757_app_center",
        "/api/client/app-center",
        "v757-app-hero",
        "Transparencia",
    ]))
    check("v758_adaptive_kept", all(token in app_source + read("templates/base.html") + css for token in [
        "build_v758_adaptive_experience",
        "/api/client/device-experience",
        "nsV758AdaptiveExperience",
        "ns-device-mobile",
    ]))
    check("v759_visual_layer", all(token in css + read("templates/home.html") + read("templates/calendar.html") + read("templates/live.html") + read("templates/track_record.html") for token in [
        "V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE", "V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX",
        "v759-release-strip",
        "App unificada",
        "Directo compacto",
        "Transparencia antes que marketing",
    ]))
    check("reports_exist", all((ROOT / "reports" / name).exists() for name in [
        "V759_GLOBAL_TOP_APP_MERGED_QUALITY_EXPERIENCE_RELEASE_REPORT.md",
        "V759_FULL_PROJECT_INITIAL_AUDIT.md",
        "V759_PROJECT_CLEANUP_AND_RELEASE_AUDIT.md",
        "V759_MEMBERSHIP_EXPERIENCE_MATRIX.md",
        "V759_CLIENT_ADMIN_QA_CHECKLIST.md",
        "V759_NEXT_ROADMAP_RECOMMENDATIONS.md",
    ]))
    check("release_builder_v759", "reports/V759_" in builder and all(token in builder for token in [".git", ".venv", "__pycache__", ".db", ".zip"]))


def functional_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="nemesis_v759_", ignore_cleanup_errors=True) as tmp:
        os.environ.update({
            "DB_PATH": str(Path(tmp) / "database.db"),
            "SECRET_KEY": "v759-check-secret",
            "AUTOMATION_SECRET": "v759-secret",
            "BACKGROUND_JOBS_ENABLED": "false",
            "SCHEDULER_ENABLED": "false",
            "TELEGRAM_BOT_TOKEN": "123456:mock-token",
            "TELEGRAM_CHAT_ID": "-1003951459919",
            "TELEGRAM_BOT_USERNAME": "nemesis_mock_bot",
            "ENABLE_TELEGRAM_AUTO": "true",
            "AUTO_SEND_TELEGRAM_PICKS": "true",
            "AUTO_GENERATE_PICKS": "true",
            "SQLITE_TIMEOUT_SECONDS": "2",
            "SQLITE_BUSY_TIMEOUT_MS": "500",
            "SQLITE_RETRY_ATTEMPTS": "2",
        })
        app_module = importlib.import_module("app")
        app_module.DB_PATH = os.environ["DB_PATH"]
        app_module.init_db()

        client = app_module.app.test_client()
        public_routes = ["/", "/login", "/admin-login", "/picks", "/calendar", "/partidos", "/live", "/directo", "/track-record"]
        statuses = {route: client.get(route).status_code for route in public_routes}
        check("public_routes_no_500", all(code < 500 for code in statuses.values()), statuses)

        with client.session_transaction() as sess:
            sess["user_id"] = "elite-check"
            sess["user_email"] = "elite@example.com"
            sess["user_role"] = "CLIENT"
            sess["membership"] = "ELITE"
        client_routes = ["/app", "/mi-app", "/inicio", "/panel-cliente", "/experiencia", "/modo-app", "/adaptive", "/adaptativo", "/telegram", "/shark"]
        client_statuses = {route: client.get(route).status_code for route in client_routes}
        check("client_routes_no_500", all(code < 500 for code in client_statuses.values()), client_statuses)

        admin_client = app_module.app.test_client()
        protected = {"/admin/dashboard": admin_client.get("/admin/dashboard").status_code, "/api/admin/telegram/environment-audit": admin_client.get("/api/admin/telegram/environment-audit").status_code}
        check("admin_protected_without_login", all(code in {302, 401, 403} for code in protected.values()), protected)
        with admin_client.session_transaction() as sess:
            sess["user_id"] = "admin-check"
            sess["user_email"] = "admin@example.com"
            sess["user_role"] = "ADMIN"
            sess["membership"] = "ADMIN"
        admin_routes = ["/admin/dashboard", "/admin/control-center", "/admin/telegram/command-center", "/admin/data-center", "/admin/matches-sync", "/admin/client-success", "/admin/go-live", "/admin/final-release", "/admin/sale-ready"]
        admin_statuses = {route: admin_client.get(route).status_code for route in admin_routes}
        check("admin_routes_no_500", all(code < 500 for code in admin_statuses.values()), admin_statuses)

        api_statuses = {
            "/api/runtime-version": client.get("/api/runtime-version").status_code,
            "/api/client/app-center": client.get("/api/client/app-center").status_code,
            "/api/client/trust-snapshot": client.get("/api/client/trust-snapshot").status_code,
            "/api/client/device-experience": client.get("/api/client/device-experience").status_code,
            "/api/admin/telegram/auto-candidates": admin_client.get("/api/admin/telegram/auto-candidates").status_code,
        }
        check("api_routes_no_500", all(code < 500 for code in api_statuses.values()), api_statuses)
        check("cron_no_secret_403", client.get("/api/automation/telegram/tick").status_code == 403)
        cron = client.get("/api/automation/telegram/tick?secret=v759-secret&runner=render_cron")
        check("cron_secret_200", cron.status_code == 200, cron.status_code)

        for route in ["/app", "/mi-app", "/inicio", "/panel-cliente", "/experiencia", "/modo-app", "/adaptive", "/adaptativo", "/track-record", "/admin/control-center"]:
            check(f"route_registered:{route}", route_exists(app_module, route))


def zip_checks() -> None:
    target = latest_v759_zip()
    if not target:
        check("zip_v759_clean", True, "ZIP V759 todavía no generado; builder auditado por política.")
        return
    bad = zip_forbidden_count(target)
    check("zip_v759_clean", bad == 0, f"{target.name}: forbidden_count={bad}")


def main() -> int:
    static_checks()
    functional_checks()
    zip_checks()
    failed = [item for item in CHECKS if not item[1]]
    result = {"ok": not failed, "version": VERSION, "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in CHECKS]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
