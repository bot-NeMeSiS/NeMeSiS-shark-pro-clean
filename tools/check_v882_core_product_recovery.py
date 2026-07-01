from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = "V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL"
ZIP_NAME = f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"

REPORTS = [
    "V882_CORE_PRODUCT_RECOVERY_MATCHES_VISUAL_ORDER_REPORT.md",
    "V882_PREFLIGHT_CORE_PRODUCT_RECOVERY.md",
    "V882_CORE_PRODUCT_GAP_AUDIT.md",
    "V882_MATCH_DATA_END_TO_END_AUDIT.md",
    "V882_MATCHES_FIXES_APPLIED.md",
    "V882_LIVE_DIRECT_RECOVERY_QA.md",
    "V882_PICKS_ODDS_RECOVERY_QA.md",
    "V882_LOGOS_CRESTS_RECOVERY_QA.md",
    "V882_CLIENT_SPORTS_PRODUCT_RECOVERY_QA.md",
    "V882_ADMIN_DATA_OPERATIONS_RECOVERY_QA.md",
    "V882_SENTINEL_REALISTIC_PRODUCT_RULES_QA.md",
    "V882_UI_CHAOS_QUICK_FIX_QA.md",
    "V882_CODEX_RENDER_CONNECTION_STATUS.md",
    "V882_NEXT_STEPS.md",
]


def fail(message: str) -> None:
    raise SystemExit(f"V882 check failed: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig", errors="replace")


def visible_text(blob: str) -> str:
    return " ".join(blob.replace("\n", " ").split())


def main() -> None:
    version_txt = read("VERSION.txt").strip()
    app_version_txt = read("APP_VERSION").strip()
    app_py = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    sentinel = read("engines/shark_sentinel_engine.py")
    continuous = read("engines/continuous_shark_sentinel_engine.py")
    calendar = read("templates/calendar.html")
    app_center = read("templates/client_app_center.html")
    picks = read("templates/picks.html")

    require(version_txt == VERSION, "VERSION.txt is not V882")
    require(app_version_txt == VERSION, "APP_VERSION is not V882")
    require(f"APP_VERSION = '{VERSION}'" in app_py, "app.py APP_VERSION is not V882")
    require(VERSION in base, "base.html missing V882 cache/version")
    require("data-v882-shell" in base, "base.html missing data-v882-shell")
    require("has_v882_core_product_recovery" in app_py, "runtime V882 flag missing")
    require("V882 CORE PRODUCT RECOVERY MATCHES VISUAL ORDER START" in css, "CSS V882 marker missing")

    for report in REPORTS:
        require((ROOT / "reports" / report).exists(), f"missing report {report}")

    require("sports_screen_empty_without_safe_explanation" in continuous, "Continuous Sentinel V882 rules missing")
    require("Pantalla deportiva vacía sin explicación" in sentinel or "sports_screen_empty_without_safe_explanation" in continuous, "Sentinel product-empty issue missing")
    require("sin partidos reales" in sentinel.lower(), "Sentinel safe state for matches missing")

    for template_name, content in {
        "calendar": calendar,
        "client_app_center": app_center,
        "picks": picks,
    }.items():
        lower = content.lower()
        require("sin partidos reales" in lower or "sin picks activos" in lower, f"{template_name} missing core safe state")
        require("esperando proveedor" in lower or "sincronizaciÃ³n real" in lower or "cuota pendiente" in lower, f"{template_name} missing provider/sync/odds state")

    combined_visible = visible_text(calendar + app_center + picks + base)
    bad_tokens = ["Ãƒ", "Ã‚", "ï¿½", "None visible", "null visible", "undefined visible"]
    for token in bad_tokens:
        require(token not in combined_visible, f"bad visible token remains: {token}")

    forbidden_claims = ["apuesta segura", "garantizado", "apuesta fija", "sin riesgo"]
    lower_all = combined_visible.lower()
    for claim in forbidden_claims:
        require(claim not in lower_all, f"forbidden betting claim remains: {claim}")

    require("No se inventaron datos" in read("reports/V882_CORE_PRODUCT_RECOVERY_MATCHES_VISUAL_ORDER_REPORT.md"), "final V882 report lacks no-fake-data note")

    os.environ["DB_PATH"] = str(ROOT / "tmp_v882_runtime_check.sqlite")
    os.environ.setdefault("AUTOMATION_SECRET", "v882-check-secret")
    import app as appmod  # noqa: WPS433

    client = appmod.app.test_client()
    runtime = client.get("/api/runtime-version")
    require(runtime.status_code == 200, "runtime-version not 200")
    payload = runtime.get_json()
    require(payload.get("app_version") == VERSION, "runtime app_version is not V882")
    require(payload.get("version_txt") == VERSION, "runtime version_txt is not V882")
    require(payload.get("has_v882_core_product_recovery") is True, "runtime V882 flag false")
    require(payload.get("has_v881_sidebar_nav_duplication_fix") is True, "runtime V881 flag false")

    for route in ["/partidos", "/calendar", "/live", "/directo", "/picks"]:
        response = client.get(route)
        require(response.status_code in {200, 302}, f"{route} unexpected status {response.status_code}")
        if response.status_code == 200:
            html = response.get_data(as_text=True).lower()
            has_row = any(marker in html for marker in ["v799-agenda-row", "v799-live-card", "v799-pick-card", "ns-match-row", "ns-pick-card"])
            has_safe = any(state in html for state in ["sin partidos reales", "sin directos reales", "sin picks activos", "esperando proveedor", "sincronizaciÃ³n real", "cuota pendiente", "pick en revisiÃ³n"])
            require(has_row or has_safe, f"{route} has no sports rows or safe state")

    zip_path = ROOT / "release_output" / ZIP_NAME
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            require("app.py" in names and "VERSION.txt" in names and "requirements.txt" in names, "ZIP missing required root files")
            require(not any(name.startswith(".git/") or name.startswith(".venv/") or name.startswith("release_output/") for name in names), "ZIP contains forbidden root")

    for suffix in ["", "-wal", "-shm"]:
        try:
            (ROOT / f"tmp_v882_runtime_check.sqlite{suffix}").unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            pass

    print("V882 core product recovery OK")


if __name__ == "__main__":
    main()

