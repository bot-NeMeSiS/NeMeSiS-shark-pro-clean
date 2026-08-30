"""Autonomous product QA evidence and memory.

This module consolidates real browser evidence for visual experience, user
journeys, sports truth and mobile/admin QA. It is deterministic, writes only
inside the Continuous Evolution storage root and never performs external or
business mutations.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha1
import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")
AUTONOMOUS_PRODUCT_QA_CONTRACT = "NEMESIS-AUTONOMOUS-PRODUCT-QA-WORKFORCE-V1"
PRODUCT_QA_ISSUE_CONTRACT = "NEMESIS-PRODUCT-QA-ISSUE-V1"

WORKERS = {
    "visual_experience_inspector": "Visual Experience Inspector",
    "digital_user_journey_tester": "Digital User Journey Tester",
    "sports_truth_qa": "Sports Truth QA",
    "mobile_qa": "Mobile QA",
    "admin_qa": "Admin QA",
}

QA_EXECUTION_POLICY = {
    "master_tick": "UNCHANGED",
    "daily": {
        "scope": "critical",
        "checks": ["navigation", "sports_truth", "basic_client_journey", "mobile_smoke", "health"],
        "browser_sessions_max": 3,
    },
    "after_change": {
        "scope": "full",
        "checks": ["navigation", "golden_journeys", "visual_critical", "sports_truth", "mobile_smoke"],
        "browser_sessions_max": 3,
    },
    "weekly": {
        "scope": "full",
        "checks": ["official_references", "golden_journeys", "admin", "mobile_extended"],
        "browser_sessions_max": 3,
    },
    "external_provider_calls": 0,
    "runs_inside_client_request": False,
}

FOUNDING_OVERRIDE_CATEGORIES = [
    "NAVIGATION",
    "VISUAL_SHARK",
    "VISUAL_BACKGROUND",
    "CLIENT_COPY",
    "SPORTS_TRUTH",
    "SPORTS_KNOWLEDGE",
    "SUMMARY_TRUTH",
    "MEDIA_RIGHTS",
    "UI_DENSITY",
]

TERMINAL_ISSUE_STATUSES = {"RESOLVED", "FALSE_POSITIVE", "FOUNDER_REJECTED"}
TECHNICAL_COPY_MARKERS = (
    "provider",
    "cache hit",
    "cache miss",
    "sync interval",
    "next refresh",
    "proxima revision en",
    "engine",
    "raw enum",
    "traceback",
    "sqlite3.",
)


def _now(value: str | datetime | None = None) -> str:
    if isinstance(value, datetime):
        current = value
    elif value:
        current = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        current = datetime.now(MADRID_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=MADRID_TZ)
    return current.astimezone(MADRID_TZ).replace(microsecond=0).isoformat()


def _safe_text(value: Any, limit: int = 900) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else dict(default)
    except (OSError, ValueError, TypeError):
        return dict(default)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def continuous_evolution_storage_root(project_root: str | Path | None = None, storage_root: str | Path | None = None) -> Path:
    if storage_root:
        return Path(storage_root)
    configured = os.getenv("CONTINUOUS_EVOLUTION_STORAGE_ROOT", "").strip()
    if configured:
        return Path(configured)
    return Path(project_root or Path.cwd()) / "data" / "runtime" / "continuous_evolution_os"


def product_qa_root(project_root: str | Path | None = None, storage_root: str | Path | None = None) -> Path:
    return continuous_evolution_storage_root(project_root, storage_root) / "autonomous_product_qa"


def _paths(project_root: str | Path | None = None, storage_root: str | Path | None = None) -> dict[str, Path]:
    root = product_qa_root(project_root, storage_root)
    return {
        "root": root,
        "latest": root / "latest_run.json",
        "memory": root / "memory.json",
        "control": root / "control.json",
        "history": root / "history",
        "evidence": root / "evidence",
    }


def _stable_issue_id(worker: str, category: str, screen: str, viewport: str, element: str) -> tuple[str, str]:
    stable_key = "|".join([worker, category, screen, viewport, element]).lower()
    digest = sha1(stable_key.encode("utf-8", errors="ignore")).hexdigest()[:12].upper()
    return f"PQA-{digest}", stable_key


def _issue(
    *,
    worker: str,
    category: str,
    severity: str,
    screen: str,
    viewport: str,
    element: str,
    expected: str,
    actual: str,
    evidence: str,
    screenshot: str = "",
    confidence: str = "HIGH",
    production_sha: str = "",
    detected_at: str = "",
) -> dict[str, Any]:
    issue_id, stable_key = _stable_issue_id(worker, category, screen, viewport, element)
    at = detected_at or _now()
    return {
        "contract": PRODUCT_QA_ISSUE_CONTRACT,
        "issue_id": issue_id,
        "stable_key": stable_key,
        "worker": worker,
        "category": category,
        "severity": severity if severity in {"P0", "P1", "P2", "P3"} else "P2",
        "screen": screen,
        "viewport": viewport,
        "element": element,
        "expected": _safe_text(expected),
        "actual": _safe_text(actual),
        "evidence": _safe_text(evidence, 1400),
        "screenshot": _safe_text(screenshot, 500),
        "first_seen": at,
        "last_seen": at,
        "seen_count": 1,
        "production_sha": _safe_text(production_sha, 80),
        "status": "OPEN",
        "confidence": confidence,
    }


def detect_product_qa_issues(observation: dict[str, Any], *, detected_at: str | None = None) -> list[dict[str, Any]]:
    """Turn browser observations into deterministic, explainable issues."""
    at = _now(detected_at)
    sha = _safe_text(observation.get("production_sha"), 80)
    issues: list[dict[str, Any]] = []

    for click in observation.get("navigation_clicks") or []:
        if not isinstance(click, dict):
            continue
        expected = str(click.get("expected_path") or click.get("expected") or "")
        actual = str(click.get("actual_path") or click.get("actual") or "")
        clicked = bool(click.get("clicked"))
        ready = bool(click.get("page_ready", True))
        hit_target = bool(click.get("hit_target", True))
        status = int(click.get("http_status") or 0)
        if clicked and hit_target and ready and actual == expected and status < 500:
            continue
        label = str(click.get("element") or click.get("label") or "navigation")
        issues.append(_issue(
            worker="digital_user_journey_tester",
            category="NAVIGATION",
            severity="P0",
            screen=str(click.get("screen") or "/"),
            viewport=str(click.get("viewport") or "unknown"),
            element=label,
            expected=f"Clic real navega a {expected} y la pagina queda lista.",
            actual=f"clicked={clicked}; hit_target={hit_target}; path={actual}; http={status}; ready={ready}",
            evidence=str(click.get("evidence") or "Contrato de clic exacto incumplido."),
            screenshot=str(click.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    sports = observation.get("sports_truth") or {}
    confirmed = int(sports.get("confirmed_live_count") or 0)
    displayed = int(sports.get("displayed_live_count") or 0)
    ft_rendered_live = int(sports.get("ft_rendered_live") or 0)
    if displayed != confirmed or ft_rendered_live:
        issues.append(_issue(
            worker="sports_truth_qa",
            category="SPORTS_TRUTH",
            severity="P0",
            screen=str(sports.get("screen") or "/"),
            viewport=str(sports.get("viewport") or "all"),
            element="live-kpi",
            expected=f"LIVE visible={confirmed}; terminales renderizados LIVE=0.",
            actual=f"LIVE visible={displayed}; FT/terminales renderizados LIVE={ft_rendered_live}.",
            evidence=str(sports.get("evidence") or "La UI no coincide con la verdad LIVE confirmada."),
            screenshot=str(sports.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    knowledge = observation.get("sports_knowledge") or {}
    if bool(knowledge.get("lineup_confirmed")) and int(knowledge.get("lineup_player_links") or 0) <= 0:
        issues.append(_issue(
            worker="sports_truth_qa",
            category="SPORTS_KNOWLEDGE",
            severity="P0",
            screen=str(knowledge.get("screen") or "/match"),
            viewport=str(knowledge.get("viewport") or "desktop_1366x768"),
            element="confirmed-lineup-player-links",
            expected="Toda alineación confirmada enlaza jugadores canónicos al Player Center.",
            actual="Alineación confirmada sin enlaces de jugador navegables.",
            evidence=str(knowledge.get("evidence") or "Contrato Sports Knowledge incumplido."),
            screenshot=str(knowledge.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))
    if int(knowledge.get("summary_unsupported_claims") or 0) > 0 or int(knowledge.get("summary_ai_calls") or 0) > 0:
        issues.append(_issue(
            worker="sports_truth_qa",
            category="SUMMARY_TRUTH",
            severity="P0",
            screen=str(knowledge.get("screen") or "/match"),
            viewport=str(knowledge.get("viewport") or "desktop_1366x768"),
            element="factual-match-summary",
            expected="Resumen determinista con 0 afirmaciones sin soporte y 0 llamadas de IA generativa.",
            actual=f"unsupported={knowledge.get('summary_unsupported_claims')}; ai_calls={knowledge.get('summary_ai_calls')}",
            evidence=str(knowledge.get("evidence") or "Contrato factual del resumen incumplido."),
            screenshot=str(knowledge.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))
    if int(knowledge.get("unsafe_media_visible") or 0) > 0:
        issues.append(_issue(
            worker="visual_experience_inspector",
            category="MEDIA_RIGHTS",
            severity="P0",
            screen=str(knowledge.get("screen") or "/match"),
            viewport=str(knowledge.get("viewport") or "desktop_1366x768"),
            element="client-visible-media",
            expected="Solo medios APPROVED o ATTRIBUTION_REQUIRED pueden ser visibles.",
            actual=f"unsafe_media_visible={knowledge.get('unsafe_media_visible')}",
            evidence=str(knowledge.get("evidence") or "Un medio sin derechos aprobados llegó a la superficie cliente."),
            screenshot=str(knowledge.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    copy_state = observation.get("client_copy") or {}
    copy_matches = [str(item) for item in (copy_state.get("technical_matches") or []) if str(item).strip()]
    visible_text = str(copy_state.get("visible_text") or "").lower()
    copy_matches.extend(marker for marker in TECHNICAL_COPY_MARKERS if marker in visible_text)
    copy_matches = list(dict.fromkeys(copy_matches))
    if copy_matches:
        issues.append(_issue(
            worker="digital_user_journey_tester",
            category="CLIENT_COPY",
            severity="P1",
            screen=str(copy_state.get("screen") or "/"),
            viewport=str(copy_state.get("viewport") or "unknown"),
            element="client-visible-copy",
            expected="Copy breve de producto, sin nombres de proveedor, cache, engines ni temporizadores internos.",
            actual="; ".join(copy_matches[:12]),
            evidence=str(copy_state.get("evidence") or "Texto tecnico visible en una superficie cliente."),
            screenshot=str(copy_state.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    visual = observation.get("visual") or {}
    for key, category, element in (
        ("shark", "VISUAL_SHARK", "official-shark-composition"),
        ("background", "VISUAL_BACKGROUND", "official-ocean-background"),
    ):
        state = visual.get(key) or {}
        classification = str(state.get("classification") or "NOT_OBSERVED").upper()
        if classification in {"MATCH", "CLOSE"}:
            continue
        issues.append(_issue(
            worker="visual_experience_inspector",
            category=category,
            severity="P1" if classification in {"MAJOR_DRIFT", "MAJOR_GAP"} else "P2",
            screen=str(state.get("screen") or "/"),
            viewport=str(state.get("viewport") or "unknown"),
            element=element,
            expected="MATCH o CLOSE respecto a la imagen oficial aplicable.",
            actual=classification,
            evidence=str(state.get("evidence") or "No existe evidencia visual suficiente para declarar coincidencia."),
            screenshot=str(state.get("screenshot") or ""),
            confidence=str(state.get("confidence") or "HIGH"),
            production_sha=sha,
            detected_at=at,
        ))

    density = observation.get("density") or {}
    if density.get("first_viewport_product") is False or int(density.get("nested_panel_depth") or 0) > 2:
        issues.append(_issue(
            worker="visual_experience_inspector",
            category="UI_DENSITY",
            severity="P2",
            screen=str(density.get("screen") or "/"),
            viewport=str(density.get("viewport") or "unknown"),
            element="first-viewport",
            expected="Producto deportivo visible en el primer viewport y profundidad de paneles <= 2.",
            actual=f"first_viewport_product={density.get('first_viewport_product')}; nested_panel_depth={density.get('nested_panel_depth')}",
            evidence=str(density.get("evidence") or "La composicion prioriza contenedores o explicaciones frente al producto."),
            screenshot=str(density.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    mobile = observation.get("mobile") or {}
    if bool(mobile.get("overflow")):
        issues.append(_issue(
            worker="mobile_qa",
            category="MOBILE_LAYOUT",
            severity="P1",
            screen=str(mobile.get("screen") or "/"),
            viewport=str(mobile.get("viewport") or "mobile_390x844"),
            element=str(mobile.get("element") or "document"),
            expected="Sin overflow horizontal y con navegacion tactil accesible.",
            actual=str(mobile.get("actual") or "overflow horizontal detectado"),
            evidence=str(mobile.get("evidence") or "scrollWidth supera viewportWidth."),
            screenshot=str(mobile.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    runtime = observation.get("runtime") or {}
    for category, severity, element, values, expected in (
        ("JAVASCRIPT", "P0", "browser-runtime", runtime.get("js_errors") or [], "0 errores JavaScript durante la inspeccion."),
        ("BROKEN_IMAGE", "P1", "rendered-images", runtime.get("broken_images") or [], "0 imagenes rotas en las pantallas inspeccionadas."),
    ):
        normalized = [str(value) for value in values if str(value).strip()]
        if not normalized:
            continue
        issues.append(_issue(
            worker="digital_user_journey_tester" if category == "JAVASCRIPT" else "visual_experience_inspector",
            category=category,
            severity=severity,
            screen=str(runtime.get("screen") or "multiple"),
            viewport=str(runtime.get("viewport") or "all"),
            element=element,
            expected=expected,
            actual="; ".join(normalized[:12]),
            evidence=str(runtime.get("evidence") or "Incidencia observada por el navegador real."),
            screenshot=str(runtime.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    for journey in observation.get("journeys") or []:
        if not isinstance(journey, dict) or journey.get("pass") is not False:
            continue
        label = str(journey.get("journey") or journey.get("selector") or "journey")
        issues.append(_issue(
            worker="digital_user_journey_tester",
            category="USER_JOURNEY",
            severity="P1",
            screen=str(journey.get("route") or journey.get("screen") or "/"),
            viewport=str(journey.get("viewport") or "desktop_1366x768"),
            element=label,
            expected=str(journey.get("expected") or "El viaje completa su destino y estado esperado."),
            actual=str(journey.get("error") or journey.get("actual") or "journey_failed"),
            evidence="Viaje dorado ejecutado mediante interaccion real en navegador.",
            screenshot=str(journey.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))
    return issues


def _default_memory(now: str) -> dict[str, Any]:
    return {
        "contract": AUTONOMOUS_PRODUCT_QA_CONTRACT,
        "created_at_madrid": now,
        "updated_at_madrid": now,
        "issues": {},
        "runs": [],
        "founder_overrides": [],
        "worker_calibration": {},
        "previous_good_run_id": None,
    }


def load_product_qa_memory(project_root: str | Path | None = None, storage_root: str | Path | None = None) -> dict[str, Any]:
    paths = _paths(project_root, storage_root)
    return _read_json(paths["memory"], _default_memory(_now()))


def ensure_founder_qa_override(memory: dict[str, Any], now: str) -> None:
    if any(item.get("override_id") == "FOUNDER-QA-OVERRIDE-001" for item in memory.get("founder_overrides") or []):
        return
    memory.setdefault("founder_overrides", []).append({
        "override_id": "FOUNDER-QA-OVERRIDE-001",
        "type": "FOUNDER_QA_OVERRIDE",
        "recorded_at_madrid": now,
        "previous_automation_result": "PASS",
        "founder_result": "FAIL",
        "categories": list(FOUNDING_OVERRIDE_CATEGORIES),
        "evidence": "El fundador reprodujo navegacion bloqueada, tiburon/fondo no coincidentes, copy tecnico, verdad LIVE incorrecta y densidad excesiva despues de un PASS automatico.",
        "missed_checks": [
            "exact_hit_target_navigation",
            "rendered_reference_composition",
            "confirmed_live_vs_visible_live",
            "client_technical_copy",
            "first_viewport_density",
        ],
        "new_coverage": [
            "real_click_contract",
            "shark_background_visual_contract",
            "sports_truth_contract",
            "client_copy_contract",
            "mobile_overflow_contract",
        ],
    })


def _calibrate_workers(memory: dict[str, Any]) -> dict[str, Any]:
    runs = memory.get("runs") or []
    result: dict[str, Any] = {}
    for worker_key, label in WORKERS.items():
        relevant = [run for run in runs if worker_key in (run.get("workers_executed") or [])]
        confirmed = sum(int((run.get("worker_outcomes") or {}).get(worker_key, {}).get("confirmed") or 0) for run in relevant)
        false_positive = sum(int((run.get("worker_outcomes") or {}).get(worker_key, {}).get("false_positive") or 0) for run in relevant)
        sample = confirmed + false_positive
        state = "INSUFFICIENT_HISTORY" if len(relevant) < 3 or sample < 5 else "HIGH_SIGNAL" if confirmed / max(sample, 1) >= .8 else "LOW_SIGNAL" if confirmed / max(sample, 1) < .5 else "NORMAL_SIGNAL"
        item = {
            "worker": worker_key,
            "label": label,
            "state": state,
            "runs": len(relevant),
            "confirmed": confirmed,
            "false_positive": false_positive,
            "why": "Se requieren al menos 3 ejecuciones y 5 resultados revisados para calibrar." if state == "INSUFFICIENT_HISTORY" else "Clasificacion determinista basada en incidencias confirmadas y falsos positivos revisados.",
        }
        if sample >= 5:
            item["useful_signal_rate"] = round(confirmed / sample, 3)
        result[worker_key] = item
    return result


def record_product_qa_run(
    observation: dict[str, Any],
    *,
    project_root: str | Path | None = None,
    storage_root: str | Path | None = None,
    trigger: str = "MANUAL",
    evidence_origin: str = "LOCAL_QA",
    now: str | datetime | None = None,
    write: bool = True,
) -> dict[str, Any]:
    at = _now(now)
    paths = _paths(project_root, storage_root)
    memory = load_product_qa_memory(project_root, storage_root)
    ensure_founder_qa_override(memory, at)
    detected = detect_product_qa_issues(observation, detected_at=at)
    scope = _safe_text(observation.get("scope") or "full", 20).lower()
    previous = memory.setdefault("issues", {})
    active_ids: set[str] = set()
    for issue in detected:
        issue_id = issue["issue_id"]
        active_ids.add(issue_id)
        old = previous.get(issue_id)
        if old:
            issue["first_seen"] = old.get("first_seen") or issue["first_seen"]
            issue["seen_count"] = int(old.get("seen_count") or 1) + 1
            if old.get("status") in TERMINAL_ISSUE_STATUSES:
                issue["status"] = "REOPENED"
            issue["history"] = [*(old.get("history") or []), {"at_madrid": at, "event": "SEEN_AGAIN"}][-40:]
        else:
            issue["history"] = [{"at_madrid": at, "event": "FIRST_DETECTED"}]
        previous[issue_id] = issue
    for issue_id, issue in previous.items():
        if issue_id in active_ids or issue.get("status") in TERMINAL_ISSUE_STATUSES:
            continue
        if scope != "full":
            continue
        issue["status"] = "RESOLVED_PENDING_HUMAN_REVIEW"
        issue["last_checked"] = at
        issue["history"] = [*(issue.get("history") or []), {"at_madrid": at, "event": "NOT_REPRODUCED"}][-40:]

    evidence_complete = bool(observation.get("evidence_complete"))
    blocking = [item for item in detected if item.get("severity") in {"P0", "P1"}]
    result = "PASS" if evidence_complete and not detected else "FAIL" if blocking else "WARNING"
    run_id = str(observation.get("run_id") or "PQA-" + datetime.fromisoformat(at).strftime("%Y%m%d%H%M%S"))
    workers_executed = list(observation.get("workers_executed") or WORKERS.keys())
    run = {
        "contract": AUTONOMOUS_PRODUCT_QA_CONTRACT,
        "run_id": run_id,
        "started_at_madrid": str(observation.get("started_at_madrid") or at),
        "finished_at_madrid": at,
        "trigger": trigger,
        "evidence_origin": evidence_origin,
        "production_sha": _safe_text(observation.get("production_sha"), 80),
        "scope": scope,
        "result": result,
        "evidence_complete": evidence_complete,
        "workers_executed": workers_executed,
        "worker_outcomes": observation.get("worker_outcomes") or {},
        "issues_detected": len(detected),
        "p0": sum(1 for item in detected if item.get("severity") == "P0"),
        "p1": sum(1 for item in detected if item.get("severity") == "P1"),
        "p2": sum(1 for item in detected if item.get("severity") == "P2"),
        "issue_ids": sorted(active_ids),
        "screenshots": list(observation.get("screenshots") or []),
        "dangerous_actions_executed": False,
        "telegram_sent": 0,
        "stripe_actions": 0,
        "provider_calls": int(observation.get("provider_calls") or 0),
    }
    memory.setdefault("runs", []).append(run)
    memory["runs"] = memory["runs"][-120:]
    if result == "PASS" and scope == "full":
        memory["previous_good_run_id"] = run_id
    elif result == "PASS":
        memory["previous_good_critical_run_id"] = run_id
    memory["updated_at_madrid"] = at
    memory["worker_calibration"] = _calibrate_workers(memory)
    latest = {
        **run,
        "issues": detected,
        "open_issues": [item for item in previous.values() if item.get("status") not in TERMINAL_ISSUE_STATUSES and item.get("status") != "RESOLVED_PENDING_HUMAN_REVIEW"],
        "worker_calibration": memory["worker_calibration"],
        "founder_override_active": True,
        "previous_good_run_id": memory.get("previous_good_run_id"),
        "previous_good_critical_run_id": memory.get("previous_good_critical_run_id"),
        "next_expected_run": observation.get("next_expected_run") or "Segun cadencia QA: daily, post-deploy o weekly visual.",
    }
    if write:
        paths["history"].mkdir(parents=True, exist_ok=True)
        _write_json(paths["history"] / f"{run_id}.json", latest)
        _write_json(paths["latest"], latest)
        _write_json(paths["memory"], memory)
        control = _read_json(paths["control"], {"paused": False, "history": []})
        if control.get("request_status") == "QUEUED_BROWSER_RUN":
            control["request_status"] = "COMPLETED" if result == "PASS" else "COMPLETED_WITH_FINDINGS"
            control["request_completed_at_madrid"] = at
            _write_json(paths["control"], control)
    return latest


def set_product_qa_pause(
    project_root: str | Path | None = None,
    *,
    paused: bool,
    actor: str,
    storage_root: str | Path | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    paths = _paths(project_root, storage_root)
    control = _read_json(paths["control"], {"paused": False, "history": []})
    at = _now(now)
    control["paused"] = bool(paused)
    control["updated_at_madrid"] = at
    control["updated_by"] = _safe_text(actor, 120) or "admin"
    control.setdefault("history", []).append({"at_madrid": at, "paused": bool(paused), "actor": control["updated_by"]})
    control["history"] = control["history"][-40:]
    _write_json(paths["control"], control)
    return control


def request_product_qa_run(
    project_root: str | Path | None = None,
    *,
    actor: str,
    storage_root: str | Path | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Queue a browser run without executing Playwright in a web request."""
    paths = _paths(project_root, storage_root)
    control = _read_json(paths["control"], {"paused": False, "history": []})
    at = _now(now)
    control["run_requested_at_madrid"] = at
    control["run_requested_by"] = _safe_text(actor, 120) or "admin"
    control["request_status"] = "QUEUED_BROWSER_RUN"
    control.setdefault("history", []).append({
        "at_madrid": at,
        "event": "RUN_REQUESTED",
        "actor": control["run_requested_by"],
    })
    control["history"] = control["history"][-40:]
    _write_json(paths["control"], control)
    return control


def build_autonomous_product_qa_status(
    project_root: str | Path | None = None,
    *,
    storage_root: str | Path | None = None,
) -> dict[str, Any]:
    paths = _paths(project_root, storage_root)
    latest = _read_json(paths["latest"], {})
    memory = load_product_qa_memory(project_root, storage_root)
    control = _read_json(paths["control"], {"paused": False, "history": []})
    ensure_founder_qa_override(memory, _now())
    issues = list(memory.get("issues", {}).values())
    open_issues = [item for item in issues if item.get("status") not in TERMINAL_ISSUE_STATUSES and item.get("status") != "RESOLVED_PENDING_HUMAN_REVIEW"]
    workers = []
    calibration = memory.get("worker_calibration") or _calibrate_workers(memory)
    for key, label in WORKERS.items():
        worker_issues = [item for item in open_issues if item.get("worker") == key]
        workers.append({
            "key": key,
            "label": label,
            "status": "PAUSED" if control.get("paused") else "ACTION_REQUIRED" if worker_issues else "PASS" if latest.get("evidence_complete") and key in (latest.get("workers_executed") or []) else "NOT_RUN",
            "last_run": latest.get("finished_at_madrid"),
            "issues": len(worker_issues),
            "result": latest.get("result") or "Sin ejecucion real",
            "next_run": latest.get("next_expected_run") or "Pendiente de cadencia",
            "calibration": calibration.get(key) or {"state": "INSUFFICIENT_HISTORY"},
        })
    return {
        "contract": AUTONOMOUS_PRODUCT_QA_CONTRACT,
        "status": "PAUSED" if control.get("paused") else "ACTION_REQUIRED" if open_issues else "PASS" if latest.get("evidence_complete") else "NOT_RUN",
        "paused": bool(control.get("paused")),
        "request_status": control.get("request_status"),
        "run_requested_at_madrid": control.get("run_requested_at_madrid"),
        "latest_run": latest,
        "last_run": latest.get("finished_at_madrid"),
        "next_expected_run": latest.get("next_expected_run") or "Pendiente de cadencia",
        "workers": workers,
        "issues": issues,
        "open_issues": open_issues,
        "open_issue_count": len(open_issues),
        "founder_overrides": memory.get("founder_overrides") or [],
        "worker_calibration": calibration,
        "previous_good_run_id": memory.get("previous_good_run_id"),
        "storage": "CONTINUOUS_EVOLUTION_NAMESPACE",
        "execution_policy": QA_EXECUTION_POLICY,
        "dangerous_actions_executed": False,
    }


def product_qa_review_findings(status: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for issue in status.get("open_issues") or []:
        findings.append({
            "id": issue.get("issue_id"),
            "reviewer": WORKERS.get(str(issue.get("worker")), str(issue.get("worker"))),
            "module": issue.get("category"),
            "screen": issue.get("screen"),
            "route": issue.get("screen"),
            "component": issue.get("element"),
            "evidence": issue.get("evidence"),
            "priority": issue.get("severity"),
            "impact_user": issue.get("actual"),
            "impact_business": "Reduce confianza de producto y puede ocultar una regresion real.",
            "proposal": f"Restaurar el comportamiento esperado: {issue.get('expected')}",
            "source": AUTONOMOUS_PRODUCT_QA_CONTRACT,
            "evidence_origin": "FOUNDER_QA_OVERRIDE" if issue.get("category") in FOUNDING_OVERRIDE_CATEGORIES else "SYSTEM_OBSERVATION",
            "certification_state": "OBSERVED",
            "candidate_improvement_ready": True,
            "approved_for_execution": False,
            "automatic_execution_allowed": False,
        })
    return findings


def product_qa_sentinel_issues(status: dict[str, Any]) -> list[dict[str, Any]]:
    severity_map = {"P0": "critical", "P1": "high", "P2": "medium", "P3": "low"}
    return [
        {
            "issue_id": item.get("issue_id"),
            "stable_key": item.get("stable_key"),
            "title": f"{item.get('category')}: {item.get('element')}",
            "area": item.get("category"),
            "category": item.get("category"),
            "severity": severity_map.get(str(item.get("severity")), "medium"),
            "priority": item.get("severity"),
            "source": AUTONOMOUS_PRODUCT_QA_CONTRACT,
            "worker": item.get("worker"),
            "route": item.get("screen"),
            "screen": item.get("screen"),
            "viewport": item.get("viewport"),
            "element": item.get("element"),
            "expected": item.get("expected"),
            "actual": item.get("actual"),
            "evidence": item.get("evidence"),
            "screenshot": item.get("screenshot"),
            "first_seen": item.get("first_seen"),
            "last_seen": item.get("last_seen"),
            "seen_count": item.get("seen_count"),
            "production_sha": item.get("production_sha"),
            "confidence": item.get("confidence"),
            "recommendation": f"Corregir y volver a ejecutar evidencia real. Esperado: {item.get('expected')}",
        }
        for item in status.get("open_issues") or []
    ]
