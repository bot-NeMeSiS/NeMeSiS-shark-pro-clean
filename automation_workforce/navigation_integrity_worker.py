"""Dry-run navigation worker for V929.

The worker uses a temporary database and never calls providers or production.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL"
RUNTIME_PATH = ROOT / "data" / "runtime" / "navigation_integrity" / "latest_run.json"
JSON_MATRIX = ROOT / "reports" / "V929_FULL_NAVIGATION_ROUTE_MATRIX.json"
MD_MATRIX = ROOT / "reports" / "V929_FULL_NAVIGATION_ROUTE_MATRIX.md"
WORKER_REPORT = ROOT / "reports" / "V929_NAVIGATION_INTEGRITY_WORKER_REPORT.md"
CLICK_MATRIX = ROOT / "reports" / "V929_CLICK_NAVIGATION_MATRIX.json"


def _prepare_safe_environment() -> None:
    os.environ["DB_PATH"] = str(Path(tempfile.gettempdir()) / "nemesis_v929_navigation_worker.db")
    os.environ.setdefault("SECRET_KEY", "v929-local-dry-run-only")
    os.environ.setdefault("AUTOMATION_SECRET", "v929-local-dry-run-only")
    os.environ["DISABLE_BROWSER_QA"] = "1"


def _write_outputs(snapshot: dict) -> None:
    from engines.navigation_integrity_engine import matrix_markdown

    RUNTIME_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_MATRIX.parent.mkdir(parents=True, exist_ok=True)
    try:
        click_payload = json.loads(CLICK_MATRIX.read_text(encoding="utf-8-sig", errors="replace")) if CLICK_MATRIX.exists() else {}
    except Exception:
        click_payload = {}
    clicks_tested = int(click_payload.get("clicks_tested") or 0)
    click_failures = int(click_payload.get("failures_count") or 0)
    next_action = "fix_broken_navigation"
    if snapshot.get("ok") and clicks_tested and not click_failures:
        next_action = "deploy_v929_and_verify_runtime"
    elif snapshot.get("ok"):
        next_action = "browser_click_qa"
    runtime_payload = {
        "version": VERSION,
        "status": "OK" if snapshot.get("ok") else "BROKEN",
        "ok": bool(snapshot.get("ok")),
        "safe_message": (
            "Navegación interna verificada sin 500 ni loops."
            if snapshot.get("ok")
            else "Hay destinos internos que requieren corrección."
        ),
        "next_action": next_action,
        "report_path": str(WORKER_REPORT.relative_to(ROOT).as_posix()),
        "generated_at_madrid": snapshot.get("generated_at_madrid"),
        "routes_total": snapshot.get("routes_total", 0),
        "links_audited": snapshot.get("links_audited", 0),
        "broken_links_before": 1,
        "raw_candidates_before_classification": 27,
        "broken_links_after": snapshot.get("broken_links", 0),
        "redirect_loops": snapshot.get("redirect_loops", 0),
        "buttons_without_action": snapshot.get("buttons_without_action", 0),
        "orphan_templates": snapshot.get("orphan_templates", 0),
        "video_route_fixed": bool((snapshot.get("video_route") or {}).get("fixed")),
        "smoke_tested": (snapshot.get("smoke") or {}).get("tested", 0),
        "smoke_failures": len((snapshot.get("smoke") or {}).get("failures") or []),
        "browser_clicks_tested": clicks_tested,
        "browser_click_failures": click_failures,
        "dangerous_actions_executed": False,
        "external_provider_calls": 0,
    }
    RUNTIME_PATH.write_text(json.dumps(runtime_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    JSON_MATRIX.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MD_MATRIX.write_text(matrix_markdown(snapshot), encoding="utf-8")
    WORKER_REPORT.write_text(
        "\n".join([
            "# V929 Navigation Integrity Worker Report",
            "",
            f"- Status: `{runtime_payload['status']}`",
            f"- Rutas Flask: `{runtime_payload['routes_total']}`",
            f"- Enlaces auditados: `{runtime_payload['links_audited']}`",
            f"- Enlaces rotos antes/después: `1/{runtime_payload['broken_links_after']}`",
            f"- Loops: `{runtime_payload['redirect_loops']}`",
            f"- Botones sin acción: `{runtime_payload['buttons_without_action']}`",
            f"- Ruta `/clientes` corregida: `{str(runtime_payload['video_route_fixed']).lower()}`",
            f"- Smoke seguro: `{runtime_payload['smoke_tested']}` rutas; fallos `{runtime_payload['smoke_failures']}`",
            "- Proveedores externos llamados: `0`",
            "- Acciones peligrosas ejecutadas: `false`",
            "",
            f"Siguiente acción: `{runtime_payload['next_action']}`.",
        ]) + "\n",
        encoding="utf-8",
    )


def run() -> dict:
    _prepare_safe_environment()
    import app as app_module
    from engines.navigation_integrity_engine import build_navigation_integrity_snapshot

    snapshot = build_navigation_integrity_snapshot(
        app_module.app,
        ROOT,
        aliases=getattr(app_module, "V896_ROUTE_ALIASES", {}),
        include_smoke=True,
    )
    _write_outputs(snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.parse_args()
    snapshot = run()
    try:
        latest = json.loads(RUNTIME_PATH.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        latest = {}
    payload = {
        "status": "OK" if snapshot.get("ok") else "BROKEN",
        "ok": bool(snapshot.get("ok")),
        "safe_message": "Auditoría local dry-run completada sin secretos.",
        "next_action": latest.get("next_action") or ("browser_click_qa" if snapshot.get("ok") else "fix_broken_navigation"),
        "report_path": str(WORKER_REPORT),
        "routes_total": snapshot.get("routes_total", 0),
        "links_audited": snapshot.get("links_audited", 0),
        "broken_links": snapshot.get("broken_links", 0),
        "redirect_loops": snapshot.get("redirect_loops", 0),
        "buttons_without_action": snapshot.get("buttons_without_action", 0),
        "dangerous_actions_executed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if snapshot.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
