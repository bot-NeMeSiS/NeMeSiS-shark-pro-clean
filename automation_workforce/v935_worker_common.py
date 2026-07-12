"""Shared read-only implementation for the V935 launch workforce."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
VERSION = "V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL"
MADRID = ZoneInfo("Europe/Madrid")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.v935_launch_trust_engine import (  # noqa: E402
    build_data_trust_snapshot,
    enrich_match_lifecycle,
    enrich_pick_lifecycle,
)


ROLE_LABELS = {
    "match_lifecycle": "Match Lifecycle Worker",
    "pick_lifecycle": "Pick Lifecycle Worker",
    "odds_freshness": "Odds Freshness Worker",
    "data_trust": "Data Trust Worker",
    "customer_trust": "Customer Trust Worker",
    "product_experience": "Product Experience Worker",
    "visual_consistency": "Visual Consistency Worker",
    "performance_budget": "Performance Budget Worker",
    "accessibility": "Accessibility Worker",
    "launch_readiness": "Launch Readiness Worker",
}


def _read(relative: str) -> str:
    try:
        return (ROOT / relative).read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def _db_path(value: str = "") -> Path:
    configured = value or os.getenv("DB_PATH") or str(ROOT / "data" / "database.db")
    return Path(configured).expanduser().resolve()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return bool(row)


def _rows(connection: sqlite3.Connection, table: str, limit: int = 500) -> list[dict[str, Any]]:
    if not _table_exists(connection, table):
        return []
    cursor = connection.execute(f'SELECT * FROM "{table}" LIMIT ?', (max(1, min(limit, 1000)),))
    columns = [item[0] for item in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def read_snapshot(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        matches: list[dict[str, Any]] = []
        picks: list[dict[str, Any]] = []
        db_status = "db_missing_safe"
    else:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True, timeout=1.5) as connection:
                connection.execute("PRAGMA query_only=ON")
                matches = _rows(connection, "matches")
                picks = _rows(connection, "picks")
            db_status = "ok"
        except sqlite3.OperationalError as exc:
            matches, picks = [], []
            db_status = "db_locked_safe" if "locked" in str(exc).lower() else "db_read_unavailable_safe"
    normalized_matches = [enrich_match_lifecycle(item) for item in matches]
    normalized_picks = [enrich_pick_lifecycle(item) for item in picks]
    last_sync = max(
        [str(item.get("updated_at") or "") for item in matches + picks if item.get("updated_at")],
        default="",
    )
    trust = build_data_trust_snapshot(
        normalized_matches,
        normalized_picks,
        provider_status="local_db_read_only" if db_status == "ok" else db_status,
        last_sync=last_sync,
    )
    return {
        "db_status": db_status,
        "matches": normalized_matches,
        "picks": normalized_picks,
        "data_trust": trust,
        "last_sync": last_sync,
    }


def _finding(kind: str, priority: str, evidence: str, *, files: list[str], routes: list[str], next_action: str) -> dict[str, Any]:
    return {
        "type": kind,
        "priority": priority,
        "evidence": str(evidence)[:320],
        "files": files[:8],
        "routes": routes[:12],
        "next_action": next_action,
    }


def _static_role(role: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    app = _read("app.py")
    ui = _read("templates/components/v933_ui.html")
    nav = _read("templates/components/v933_navigation.html")
    css = _read("static/v933-product.css")
    base = _read("templates/base.html")
    js = _read("static/v934-realtime.js")
    findings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    if role == "customer_trust":
        required = ["customer_trust_panel", "v935-customer-trust", "no_publish_reason", "technical_details_hidden"]
        missing = [token for token in required if token not in app + ui + css]
        if missing:
            findings.append(_finding("customer_trust_contract_missing", "P1", ", ".join(missing), files=["app.py", "templates/components/v933_ui.html", "static/v933-product.css"], routes=["/app", "/picks", "/track-record", "/shark"], next_action="restore_customer_trust_contract"))
        metrics["contract_tokens_present"] = len(required) - len(missing)
    elif role == "product_experience":
        templates = ["client_app_center.html", "calendar.html", "live.html", "picks.html", "track_record.html", "shark.html", "telegram.html", "membership.html"]
        missing = [name for name in templates if not (ROOT / "templates" / name).exists()]
        if missing:
            findings.append(_finding("client_product_surface_missing", "P1", ", ".join(missing), files=[f"templates/{name}" for name in missing], routes=["/app", "/calendar", "/live", "/picks"], next_action="restore_client_surface"))
        metrics["client_surfaces_present"] = len(templates) - len(missing)
        metrics["no_publish_decision_visible"] = "No publicar" in _read("templates/shark.html")
    elif role == "visual_consistency":
        required = ["v933-client-shell", "v933-admin-shell", "v933-mobile-bottom-nav", "v935-customer-trust"]
        missing = [token for token in required if token not in base + nav + css]
        if missing:
            findings.append(_finding("visual_contract_missing", "P2", ", ".join(missing), files=["templates/base.html", "templates/components/v933_navigation.html", "static/v933-product.css"], routes=["/app", "/admin/dashboard"], next_action="restore_visual_contract"))
        metrics["visual_tokens_present"] = len(required) - len(missing)
    elif role == "performance_budget":
        metrics = {
            "css_bytes": len(css.encode("utf-8")),
            "realtime_js_bytes": len(js.encode("utf-8")),
            "shared_polling": "__nemesisV935Realtime" in js,
            "conditional_requests": "If-None-Match" in js and "set_etag" in app,
            "request_local_summary_cache": "v935_public_sports_summary" in app,
        }
        if metrics["css_bytes"] > 130000:
            findings.append(_finding("css_budget_attention", "P2", f"{metrics['css_bytes']} bytes", files=["static/v933-product.css"], routes=["all"], next_action="remove_dead_or_duplicate_rules"))
        if not all(metrics[key] for key in ("shared_polling", "conditional_requests", "request_local_summary_cache")):
            findings.append(_finding("cache_or_polling_contract_missing", "P1", json.dumps(metrics), files=["app.py", "static/v934-realtime.js"], routes=["/api/realtime/sports"], next_action="restore_shared_cache_contract"))
    elif role == "accessibility":
        token_css = _read("static/v933_design_tokens.css") + css
        checks = {
            "focus_visible": "focus-visible" in token_css,
            "reduced_motion": "prefers-reduced-motion" in token_css,
            "touch_targets": "min-height: 44px" in token_css,
            "navigation_labels": "aria-label=" in nav,
            "live_region": "aria-live=\"polite\"" in _read("templates/admin_data_trust_center.html"),
        }
        metrics.update(checks)
        missing = [key for key, value in checks.items() if not value]
        if missing:
            findings.append(_finding("accessibility_contract_missing", "P2", ", ".join(missing), files=["static/v933_design_tokens.css", "static/v933-product.css", "templates/components/v933_navigation.html"], routes=["all"], next_action="restore_accessibility_contract"))
    elif role == "launch_readiness":
        required = [
            "engines/v935_launch_trust_engine.py",
            "templates/admin_data_trust_center.html",
            "automation_workforce/v935_launch_orchestrator.py",
            "reports/V935_CHECKPOINT_STATUS.json",
        ]
        missing = [relative for relative in required if not (ROOT / relative).exists()]
        version = _read("VERSION.txt").strip()
        if missing:
            findings.append(_finding("launch_artifact_missing", "P1", ", ".join(missing), files=missing, routes=["/api/runtime-version"], next_action="complete_launch_artifacts"))
        if not version.startswith(("V935_", "V936_", "V937_")):
            findings.append(_finding("release_identity_pending", "P2", version or "missing", files=["VERSION.txt", "app.py"], routes=["/api/runtime-version"], next_action="finalize_v935_identity"))
        metrics["required_artifacts_present"] = len(required) - len(missing)
        metrics["version"] = version
    return findings, metrics


def evaluate(role: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    trust = snapshot.get("data_trust") or {}
    findings: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    if role == "match_lifecycle":
        counts = Counter(item.get("v935_lifecycle") or "INCOMPLETE" for item in snapshot.get("matches") or [])
        metrics["match_counts"] = dict(counts)
        for kind, priority in (("INCOMPLETE", "P1"), ("RESULT_PENDING", "P1")):
            if counts.get(kind):
                findings.append(_finding(f"matches_{kind.lower()}", priority, f"{counts[kind]} records", files=["engines/v935_launch_trust_engine.py"], routes=["/calendar", "/live", "/admin/data-trust-center"], next_action="run_authorized_data_quality_review"))
    elif role == "pick_lifecycle":
        counts = Counter(item.get("v935_lifecycle") or "INCOMPLETE" for item in snapshot.get("picks") or [])
        metrics.update({"pick_counts": dict(counts), "publicable": trust.get("publicable_picks", 0), "evaluable": trust.get("evaluable_picks", 0), "non_evaluable": trust.get("non_evaluable_picks", 0)})
        if counts.get("INCOMPLETE"):
            findings.append(_finding("incomplete_picks_blocked", "P1", f"{counts['INCOMPLETE']} blocked", files=["engines/v935_launch_trust_engine.py", "app.py"], routes=["/picks", "/track-record"], next_action="complete_or_archive_pick_safely"))
    elif role == "odds_freshness":
        metrics["odds_counts"] = trust.get("odds_counts") or {}
        stale = int((trust.get("odds_counts") or {}).get("STALE") or 0)
        invalid = int((trust.get("odds_counts") or {}).get("INVALID") or 0)
        if stale or invalid:
            findings.append(_finding("odds_not_publishable", "P1", f"stale={stale}, invalid={invalid}", files=["engines/v935_launch_trust_engine.py", "templates/components/v933_ui.html"], routes=["/picks", "/admin/data-trust-center"], next_action="run_authorized_odds_sync_or_keep_blocked"))
    elif role == "data_trust":
        metrics = {key: value for key, value in trust.items() if key not in {"issues", "blockers"}}
        for issue in trust.get("issues") or []:
            findings.append(_finding(str(issue.get("type") or "data_trust_issue"), str(issue.get("priority") or "P2"), f"{issue.get('count', 0)} records", files=["engines/v935_launch_trust_engine.py"], routes=["/admin/data-trust-center"], next_action=str(issue.get("next_action") or "review_data_trust")))
    else:
        findings, metrics = _static_role(role)
    deduped: dict[str, dict[str, Any]] = {}
    for finding in findings:
        key = f"{finding.get('type')}|{','.join(finding.get('routes') or [])}"
        deduped[key] = finding
    findings = list(deduped.values())
    blocker = any(item.get("priority") == "P0" for item in findings)
    attention = bool(findings)
    status = "blocked" if blocker else "attention" if attention else "ok"
    return {
        "worker": ROLE_LABELS.get(role, role),
        "role": role,
        "status": status,
        "ok": not blocker,
        "dry_run": True,
        "safe_message": "Lectura local completada sin proveedor, envios, pagos ni escrituras DB.",
        "next_action": findings[0]["next_action"] if findings else "continue_launch_validation",
        "findings": findings,
        "metrics": metrics,
        "database_status": snapshot.get("db_status"),
        "external_calls": 0,
        "database_writes": 0,
        "secrets_visible": False,
        "generated_at_madrid": datetime.now(MADRID).isoformat(timespec="seconds"),
    }


def write_evidence(result: dict[str, Any], slug: str | None = None) -> tuple[str, str]:
    slug = slug or str(result.get("role") or "worker")
    output_dir = ROOT / "data" / "runtime" / "automation_workforce" / "v935_workers"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{slug}.json"
    md_path = output_dir / f"{slug}.md"
    result["report_path"] = str(md_path.relative_to(ROOT)).replace("\\", "/")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# {result.get('worker')}", "", f"- Status: `{result.get('status')}`", f"- Dry-run: `{result.get('dry_run')}`",
        f"- Safe message: {result.get('safe_message')}", f"- Next action: `{result.get('next_action')}`", "", "## Findings", "",
    ]
    if result.get("findings"):
        lines.extend(f"- `{item.get('priority')}` {item.get('type')}: {item.get('evidence')}" for item in result["findings"])
    else:
        lines.append("- No reportable findings.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(json_path.relative_to(ROOT)).replace("\\", "/"), result["report_path"]


def run_role(role: str, db_path: str = "", *, slug: str | None = None, write: bool = True) -> dict[str, Any]:
    snapshot = read_snapshot(_db_path(db_path))
    result = evaluate(role, snapshot)
    if write:
        json_path, report_path = write_evidence(result, slug)
        result["json_path"] = json_path
        result["report_path"] = report_path
    return result


def worker_main(role: str) -> int:
    parser = argparse.ArgumentParser(description=ROLE_LABELS.get(role, role))
    parser.add_argument("--dry-run", action="store_true", help="Confirm safe read-only execution")
    parser.add_argument("--db-path", default="", help="Optional local database path")
    parser.add_argument("--no-write", action="store_true", help="Do not persist sanitized worker evidence")
    args = parser.parse_args()
    result = run_role(role, args.db_path, write=not args.no_write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1
