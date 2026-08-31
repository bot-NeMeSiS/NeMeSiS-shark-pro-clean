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
    "sports_knowledge_qa": "Sports Knowledge QA",
    "summary_truth_qa": "Summary Truth QA",
    "media_rights_qa": "Media Rights QA",
}

EVIDENCE_AUTHORITY = {
    "UNIT_STATIC_TEST": 10,
    "AUTOMATED_BROWSER_QA": 20,
    "REAL_PRODUCTION_EVIDENCE": 30,
    "REAL_BROWSER_FAILURE": 40,
    "FOUNDER_CONFIRMED_FAILURE": 50,
}

QUALITY_GATES = (
    "NAVIGATION",
    "VISUAL",
    "SPORTS_TRUTH",
    "TEMPORAL_CONTEXT",
    "MOBILE",
    "ADMIN",
    "SECURITY",
    "PERFORMANCE",
    "SPORTS_KNOWLEDGE",
    "MEDIA_RIGHTS",
    "SUMMARY_TRUTH",
    "DATA_QUALITY",
)

PINNED_REGRESSION_CONTRACTS = {
    "TOPBAR_REAL_NAVIGATION": {"category": "NAVIGATION", "severity": "P0", "test": "real_click_and_element_from_point"},
    "FALSE_LIVE_KPI": {"category": "SPORTS_TRUTH", "severity": "P0", "test": "confirmed_live_equals_visible_live"},
    "FT_NEVER_LIVE": {"category": "SPORTS_TRUTH", "severity": "P0", "test": "terminal_state_never_renders_live"},
    "CROSS_SURFACE_LIVE_TRUTH": {"category": "SPORTS_TRUTH", "severity": "P0", "test": "same_match_same_canonical_live_truth", "memory_key": "LIVE_TRUTH_CROSS_SURFACE_RECURRENCE"},
    "CROSS_SURFACE_COMPETITION_IDENTITY": {"category": "COMPETITION_IDENTITY", "severity": "P0", "test": "same_match_same_canonical_competition"},
    "OFFICIAL_SHARK_REFERENCE": {"category": "VISUAL", "severity": "P1", "test": "rendered_reference_comparison"},
    "OFFICIAL_BACKGROUND_REFERENCE": {"category": "VISUAL", "severity": "P1", "test": "rendered_reference_comparison"},
    "VISUAL_FALSE_PASS_RECURRENCE": {"category": "VISUAL", "severity": "P1", "test": "founder_rejection_overrides_automated_visual_pass"},
    "CLIENT_TECHNICAL_COPY_LEAK": {"category": "ADMIN", "severity": "P1", "test": "rendered_client_copy_scan"},
    "RECTANGLE_FATIGUE_CONTENT_DENSITY": {"category": "VISUAL", "severity": "P2", "test": "first_viewport_and_panel_depth"},
    "LARGE_UNJUSTIFIED_EMPTY_REGION": {"category": "VISUAL", "severity": "P1", "test": "rendered_viewport_occupancy"},
    "EMPTY_DASHBOARD": {"category": "VISUAL", "severity": "P1", "test": "rendered_empty_state_composition"},
    "SPORTS_ABOVE_FOLD_RATIO": {"category": "VISUAL", "severity": "P1", "test": "rendered_sports_first_viewport_ratio"},
    "IMPORTANT_MATCH_PRIORITY": {"category": "SPORTS_TRUTH", "severity": "P1", "test": "sports_priority_fixture_matrix"},
    "PERFORMANCE_P0": {"category": "PERFORMANCE", "severity": "P0", "test": "critical_route_performance_sample"},
    "TEAM_TO_PLAYER": {"category": "SPORTS_KNOWLEDGE", "severity": "P1", "test": "sports_knowledge_golden_journey"},
    "MEDIA_RIGHTS_FAIL_CLOSED": {"category": "MEDIA_RIGHTS", "severity": "P0", "test": "rights_decision_render_contract"},
    "MOJIBAKE": {"category": "ADMIN", "severity": "P2", "test": "rendered_text_encoding_scan"},
    "BROKEN_LINKS": {"category": "NAVIGATION", "severity": "P0", "test": "real_click_golden_journeys"},
    "MOBILE_BOTTOM_NAV": {"category": "MOBILE", "severity": "P1", "test": "mobile_real_tap_and_hit_target"},
    "NO_TEXT_BORDER_COLLISION": {"category": "LAYOUT_COLLISION", "severity": "P1", "test": "rendered_text_bounds_inside_control"},
    "NO_CARD_OVERFLOW": {"category": "LAYOUT_COLLISION", "severity": "P1", "test": "rendered_card_intrinsic_overflow"},
    "SPANISH_COPY_STRESS": {"category": "LAYOUT_COLLISION", "severity": "P1", "test": "long_spanish_labels_render_without_clipping"},
    "MOBILE_360_LAYOUT": {"category": "MOBILE_LAYOUT", "severity": "P1", "test": "mobile_360_collision_and_overflow_scan"},
    "CLIENT_ADMIN_SEPARATION": {"category": "SECURITY", "severity": "P0", "test": "client_session_admin_denied"},
    "TEMPORAL_CONTEXT_CONSISTENCY": {"category": "TEMPORAL_CONTEXT", "severity": "P1", "test": "madrid_datetime_cross_surface_contract"},
}

ISSUE_TO_REGRESSION = {
    "NAVIGATION": "TOPBAR_REAL_NAVIGATION",
    "SPORTS_TRUTH": "FALSE_LIVE_KPI",
    "COMPETITION_IDENTITY": "CROSS_SURFACE_COMPETITION_IDENTITY",
    "VISUAL_SHARK": "OFFICIAL_SHARK_REFERENCE",
    "VISUAL_BACKGROUND": "OFFICIAL_BACKGROUND_REFERENCE",
    "CLIENT_COPY": "CLIENT_TECHNICAL_COPY_LEAK",
    "UI_DENSITY": "RECTANGLE_FATIGUE_CONTENT_DENSITY",
    "SPORTS_KNOWLEDGE": "TEAM_TO_PLAYER",
    "MEDIA_RIGHTS": "MEDIA_RIGHTS_FAIL_CLOSED",
    "MOJIBAKE": "MOJIBAKE",
    "USER_JOURNEY": "BROKEN_LINKS",
    "MOBILE_LAYOUT": "MOBILE_BOTTOM_NAV",
    "LAYOUT_COLLISION": "NO_TEXT_BORDER_COLLISION",
    "SECURITY": "CLIENT_ADMIN_SEPARATION",
    "PERFORMANCE": "PERFORMANCE_P0",
    "TEMPORAL_CONTEXT": "TEMPORAL_CONTEXT_CONSISTENCY",
}

QA_EXECUTION_POLICY = {
    "master_tick": "UNCHANGED",
    "daily": {
        "scope": "critical",
        "checks": [
            "navigation",
            "sports_truth",
            "temporal_context",
            "sports_knowledge",
            "summary_truth",
            "media_rights",
            "basic_client_journey",
            "mobile_smoke",
            "health",
        ],
        "browser_sessions_max": 3,
    },
    "after_change": {
        "scope": "full",
        "checks": ["navigation", "golden_journeys", "visual_critical", "sports_truth", "temporal_context", "sports_knowledge", "summary_truth", "media_rights", "mobile_smoke"],
        "browser_sessions_max": 3,
    },
    "weekly": {
        "scope": "full",
        "checks": ["official_references", "golden_journeys", "admin", "temporal_context", "sports_knowledge", "summary_truth", "media_rights", "mobile_extended"],
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

ACTIVE_ISSUE_STATUSES = {"OPEN_REAL"}
TERMINAL_ISSUE_STATUSES = {"RESOLVED", "FALSE_POSITIVE", "DUPLICATE"}
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
        "status": "OPEN_REAL",
        "confidence": confidence,
        "evidence_origin": "LOCAL_QA",
        "evidence_sufficient": bool(evidence and actual),
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

    competition_identity = observation.get("competition_identity") or {}
    competition_mismatches = competition_identity.get("mismatches") or []
    if competition_identity and (
        competition_identity.get("pass") is not True
        or competition_mismatches
    ):
        issues.append(_issue(
            worker="sports_truth_qa",
            category="COMPETITION_IDENTITY",
            severity="P0",
            screen=str(competition_identity.get("screen") or "sports surfaces"),
            viewport=str(competition_identity.get("viewport") or "all"),
            element="CROSS_SURFACE_COMPETITION_IDENTITY",
            expected="El mismo partido conserva un ID canónico de competición en todas las superficies.",
            actual=f"compared={int(competition_identity.get('matches_compared') or 0)}; mismatches={len(competition_mismatches)}",
            evidence=str(competition_identity.get("evidence") or competition_mismatches[:6]),
            screenshot=str(competition_identity.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    knowledge = observation.get("sports_knowledge") or {}
    if bool(knowledge.get("lineup_confirmed")) and int(knowledge.get("lineup_player_links") or 0) <= 0:
        issues.append(_issue(
            worker="sports_knowledge_qa",
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
            worker="summary_truth_qa",
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
            worker="media_rights_qa",
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

    temporal = observation.get("temporal_context") or {}
    if temporal:
        missing = int(temporal.get("missing_cards") or 0)
        ambiguous = int(temporal.get("ambiguous_cards") or 0)
        cross_surface = temporal.get("cross_surface_consistent") is True
        madrid_time = temporal.get("madrid_time") is True
        if missing or ambiguous or not cross_surface or not madrid_time:
            issues.append(_issue(
                worker="digital_user_journey_tester",
                category="TEMPORAL_CONTEXT",
                severity="P1",
                screen=str(temporal.get("screen") or "match surfaces"),
                viewport=str(temporal.get("viewport") or "all"),
                element="MATCH_TEMPORAL_CONTEXT_REQUIRED",
                expected="Cada card relevante muestra fecha/hora Madrid y el mismo instante en todas las superficies.",
                actual=(
                    f"checked={int(temporal.get('checked_cards') or 0)}; missing={missing}; "
                    f"ambiguous={ambiguous}; cross_surface={cross_surface}; madrid_time={madrid_time}"
                ),
                evidence=str(temporal.get("evidence") or "Contrato temporal cliente incumplido."),
                screenshot=str(temporal.get("screenshot") or ""),
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
        if classification in {"MATCH", "MINOR_GAP"}:
            continue
        issues.append(_issue(
            worker="visual_experience_inspector",
            category=category,
            severity="P1" if classification in {"MAJOR_GAP", "REBUILD_REQUIRED"} else "P2",
            screen=str(state.get("screen") or "/"),
            viewport=str(state.get("viewport") or "unknown"),
            element=element,
            expected="MATCH o MINOR_GAP respecto a la imagen oficial aplicable; aprobación humana obligatoria.",
            actual=classification,
            evidence=str(state.get("evidence") or "No existe evidencia visual suficiente para declarar coincidencia."),
            screenshot=str(state.get("screenshot") or ""),
            confidence=str(state.get("confidence") or "HIGH"),
            production_sha=sha,
            detected_at=at,
        ))

    density = observation.get("density") or {}
    dead_space_flags = density.get("dead_space_flags") or []
    empty_dashboard_flags = density.get("empty_dashboard_flags") or []
    sports_above_fold_ratio = float(density.get("sports_above_fold_ratio") or 0)
    nested_depth = max(int(density.get("nested_panel_depth") or 0), int(density.get("nested_card_depth") or 0))
    if density.get("first_viewport_product") is False or nested_depth > 2 or dead_space_flags or empty_dashboard_flags or sports_above_fold_ratio < .05:
        issues.append(_issue(
            worker="visual_experience_inspector",
            category="UI_DENSITY",
            severity="P2",
            screen=str(density.get("screen") or "/"),
            viewport=str(density.get("viewport") or "unknown"),
            element="first-viewport",
            expected="Producto deportivo visible, sin dashboard vacío ni grandes regiones muertas, y profundidad de paneles <= 2.",
            actual=(
                f"first_viewport_product={density.get('first_viewport_product')}; nested_depth={nested_depth}; "
                f"dead_space={len(dead_space_flags)}; empty_dashboard={len(empty_dashboard_flags)}; "
                f"sports_above_fold_ratio={sports_above_fold_ratio:.3f}"
            ),
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

    for collision in observation.get("layout_collisions") or []:
        if not isinstance(collision, dict):
            continue
        collision_type = str(collision.get("type") or "layout_collision")
        severity = "P1" if collision_type in {
            "interactive_overlap", "text_border_collision", "text_clipping", "button_clipping", "card_overflow"
        } else "P2"
        issues.append(_issue(
            worker="visual_experience_inspector",
            category="LAYOUT_COLLISION",
            severity=severity,
            screen=str(collision.get("screen") or "/"),
            viewport=str(collision.get("viewport") or "unknown"),
            element=str(collision.get("element") or collision.get("selector") or "layout"),
            expected="Texto, controles y cards permanecen dentro de sus límites sin solaparse.",
            actual=f"{collision_type}: {collision.get('actual') or collision.get('text') or ''}",
            evidence=str(collision.get("evidence") or collision),
            screenshot=str(collision.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    text_quality = observation.get("text_quality") or {}
    mojibake_matches = [str(item) for item in text_quality.get("mojibake_matches") or [] if str(item).strip()]
    if mojibake_matches:
        issues.append(_issue(
            worker="digital_user_journey_tester",
            category="MOJIBAKE",
            severity="P2",
            screen=str(text_quality.get("screen") or "client surfaces"),
            viewport=str(text_quality.get("viewport") or "all"),
            element="rendered-client-copy",
            expected="Texto UTF-8 legible, sin secuencias de codificacion rotas.",
            actual="; ".join(mojibake_matches[:12]),
            evidence=str(text_quality.get("evidence") or "Texto roto observado en el navegador real."),
            screenshot=str(text_quality.get("screenshot") or ""),
            production_sha=sha,
            detected_at=at,
        ))

    security = observation.get("security") or {}
    if str(security.get("client_admin_separation") or "NOT_RUN").upper() == "FAIL":
        issues.append(_issue(
            worker="admin_qa",
            category="SECURITY",
            severity="P0",
            screen="/admin/founder-dashboard",
            viewport=str(security.get("viewport") or "desktop_1366x768"),
            element="client-admin-separation",
            expected="Una sesion cliente es rechazada por backend y termina en admin-login.",
            actual=str(security.get("actual") or "Cliente alcanzo una superficie admin."),
            evidence=str(security.get("evidence") or "Prueba autenticada de separacion cliente/admin fallida."),
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
        "regressions": {},
        "production_sentinel_runs": [],
        "previous_good_run_id": None,
    }


def load_product_qa_memory(project_root: str | Path | None = None, storage_root: str | Path | None = None) -> dict[str, Any]:
    paths = _paths(project_root, storage_root)
    return _read_json(paths["memory"], _default_memory(_now()))


def ensure_founder_qa_override(memory: dict[str, Any], now: str) -> None:
    overrides = memory.setdefault("founder_overrides", [])
    if not any(item.get("override_id") == "FOUNDER-QA-OVERRIDE-001" for item in overrides):
        overrides.append({
            "override_id": "FOUNDER-QA-OVERRIDE-001",
            "type": "FOUNDER_QA_OVERRIDE",
            "recorded_at_madrid": now,
            "previous_automation_result": "PASS",
            "founder_result": "FAIL",
            "categories": list(FOUNDING_OVERRIDE_CATEGORIES),
            "evidence": "El fundador reprodujo navegacion bloqueada, tiburon/fondo no coincidentes, copy tecnico, verdad LIVE incorrecta y densidad excesiva despues de un PASS automatico.",
            "missed_checks": ["exact_hit_target_navigation", "rendered_reference_composition", "confirmed_live_vs_visible_live", "client_technical_copy", "first_viewport_density"],
            "new_coverage": ["real_click_contract", "shark_background_visual_contract", "sports_truth_contract", "client_copy_contract", "mobile_overflow_contract"],
            "verification": {},
        })
    if not any(item.get("override_id") == "FOUNDER_VIDEO_REVIEW_2026_08_31" for item in overrides):
        overrides.append({
            "override_id": "FOUNDER_VIDEO_REVIEW_2026_08_31",
            "type": "FOUNDER_VIDEO_REVIEW",
            "recorded_at_madrid": now,
            "previous_automation_result": "PASS",
            "founder_result": "FAIL",
            "categories": ["SHARK", "BACKGROUND_DEPTH", "DEAD_SPACE", "RECTANGLE_DENSITY", "EMPTY_STATES", "SPORTS_HIERARCHY"],
            "evidence": "El vídeo real mostró tiburón plano, fondo sin profundidad sostenida, espacio muerto, dashboards vacíos y contenido deportivo por debajo de paneles secundarios.",
            "missed_checks": ["dead_space_detector", "empty_dashboard_detector", "bordered_container_count", "nested_card_depth", "sports_above_fold_ratio"],
            "new_coverage": ["rendered_viewport_occupancy", "rendered_empty_state_composition", "rendered_border_count", "rendered_nested_card_depth", "rendered_sports_above_fold_ratio"],
            "verification": {},
        })


def _quality_gate_for_issue(issue: dict[str, Any]) -> str:
    category = str(issue.get("category") or "").upper()
    if category in {"NAVIGATION", "USER_JOURNEY", "BROKEN_LINK"}:
        return "NAVIGATION"
    if category.startswith("VISUAL") or category in {"UI_DENSITY", "BROKEN_IMAGE", "LAYOUT_COLLISION"}:
        return "VISUAL"
    if category in {"SPORTS_TRUTH", "LIVE_TRUTH", "DATA_CONSISTENCY", "COMPETITION_IDENTITY"}:
        return "SPORTS_TRUTH"
    if category == "TEMPORAL_CONTEXT":
        return "TEMPORAL_CONTEXT"
    if category.startswith("MOBILE"):
        return "MOBILE"
    if category in {"ADMIN", "CLIENT_COPY", "MOJIBAKE"}:
        return "ADMIN"
    if category in {"SECURITY", "PRIVACY", "AUTH"}:
        return "SECURITY"
    if category == "PERFORMANCE":
        return "PERFORMANCE"
    if category == "SPORTS_KNOWLEDGE":
        return "SPORTS_KNOWLEDGE"
    if category == "MEDIA_RIGHTS":
        return "MEDIA_RIGHTS"
    if category == "SUMMARY_TRUTH":
        return "SUMMARY_TRUTH"
    return "DATA_QUALITY"


def _evidence_authority(origin: str) -> tuple[str, int]:
    value = str(origin or "").upper()
    if "FOUNDER" in value:
        key = "FOUNDER_CONFIRMED_FAILURE"
    elif "REAL_BROWSER_FAILURE" in value:
        key = "REAL_BROWSER_FAILURE"
    elif "REAL_PRODUCTION" in value or "CURRENT_PRODUCTION" in value:
        key = "REAL_PRODUCTION_EVIDENCE"
    elif "BROWSER" in value or "LOCAL_QA" in value:
        key = "AUTOMATED_BROWSER_QA"
    else:
        key = "UNIT_STATIC_TEST"
    return key, EVIDENCE_AUTHORITY[key]


def _regression_result_defaults(observation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    clicks = [item for item in observation.get("navigation_clicks") or [] if isinstance(item, dict)]
    click_pass = bool(clicks) and all(
        item.get("clicked") and item.get("hit_target") and item.get("page_ready")
        and int(item.get("http_status") or 0) < 500
        and str(item.get("actual_path") or "").startswith(str(item.get("expected_path") or ""))
        for item in clicks
    )
    sports = observation.get("sports_truth") or {}
    sports_pass = int(sports.get("confirmed_live_count") or 0) == int(sports.get("displayed_live_count") or 0)
    ft_pass = int(sports.get("ft_rendered_live") or 0) == 0
    cross_surface_mismatches = list(sports.get("cross_surface_live_mismatches") or [])
    cross_surface_observed = "cross_surface_live_truth" in sports or bool(cross_surface_mismatches)
    cross_surface_pass = sports.get("cross_surface_live_truth") is True and not cross_surface_mismatches

    visual = observation.get("visual") or {}
    shark = str((visual.get("shark") or {}).get("classification") or "NOT_RUN").upper()
    background = str((visual.get("background") or {}).get("classification") or "NOT_RUN").upper()
    copy_state = observation.get("client_copy") or {}
    copy_pass = not (copy_state.get("technical_matches") or [])
    density = observation.get("density") or {}
    composition = observation.get("composition") or {}
    dead_space_flags = composition.get("dead_space_flags") or density.get("dead_space_flags") or []
    empty_dashboard_flags = composition.get("empty_dashboard_flags") or density.get("empty_dashboard_flags") or []
    sports_above_fold_ratio = float(density.get("sports_above_fold_ratio") or composition.get("home_sports_above_fold_ratio") or 0)
    nested_depth = max(int(density.get("nested_panel_depth") or 0), int(density.get("nested_card_depth") or 0))
    density_pass = (
        density.get("first_viewport_product") is True
        and nested_depth <= 2
        and not dead_space_flags
        and not empty_dashboard_flags
        and sports_above_fold_ratio >= .05
    )
    mobile_clicks = [item for item in clicks if str(item.get("viewport") or "").startswith("mobile_")]
    mobile_pass = bool(mobile_clicks) and all(item.get("clicked") and item.get("hit_target") for item in mobile_clicks)
    journeys = {str(item.get("journey")): item for item in observation.get("journeys") or [] if isinstance(item, dict)}
    knowledge = observation.get("sports_knowledge") or {}
    rights_pass = int(knowledge.get("unsafe_media_visible") or 0) == 0
    runtime = observation.get("runtime") or {}
    text_quality = observation.get("text_quality") or {}
    temporal = observation.get("temporal_context") or {}
    temporal_observed = bool(temporal)
    temporal_pass = (
        temporal_observed
        and int(temporal.get("missing_cards") or 0) == 0
        and int(temporal.get("ambiguous_cards") or 0) == 0
        and temporal.get("cross_surface_consistent") is True
        and temporal.get("madrid_time") is True
    )
    competition = observation.get("competition_identity") or {}
    competition_observed = int(competition.get("matches_compared") or 0) > 0
    competition_pass = competition_observed and competition.get("pass") is True and not (competition.get("mismatches") or [])
    layout = observation.get("layout") or {}
    layout_observed = layout.get("observed") is True
    collision_types = {str(item).strip().lower() for item in (layout.get("collision_types") or []) if str(item).strip()}
    text_collision_types = {"button_clipping", "text_clipping", "interactive_overlap", "viewport_escape"}
    mobile_360_observed = int(layout.get("mobile_360_captures") or 0) > 0
    mobile_360_pass = (
        mobile_360_observed
        and int(layout.get("mobile_360_collisions") or 0) == 0
        and int(layout.get("mobile_360_overflow") or 0) == 0
    )
    competition = observation.get("competition_identity") or {}
    competition_observed = int(competition.get("matches_compared") or 0) > 0
    competition_pass = competition_observed and competition.get("pass") is True and not (competition.get("mismatches") or [])
    layout = observation.get("layout") or {}
    layout_observed = layout.get("observed") is True
    collision_types = {str(item).strip().lower() for item in (layout.get("collision_types") or []) if str(item).strip()}
    text_collision_types = {"button_clipping", "text_clipping", "interactive_overlap", "viewport_escape"}
    mobile_360_observed = int(layout.get("mobile_360_captures") or 0) > 0
    mobile_360_pass = (
        mobile_360_observed
        and int(layout.get("mobile_360_collisions") or 0) == 0
        and int(layout.get("mobile_360_overflow") or 0) == 0
    )
    return {
        "TOPBAR_REAL_NAVIGATION": {"status": "PASS" if click_pass else "FAIL", "evidence": f"real_clicks={len(clicks)}"},
        "FALSE_LIVE_KPI": {"status": "PASS" if sports_pass else "FAIL", "evidence": f"confirmed={sports.get('confirmed_live_count', 0)}; visible={sports.get('displayed_live_count', 0)}"},
        "FT_NEVER_LIVE": {"status": "PASS" if ft_pass else "FAIL", "evidence": f"terminal_rendered_live={sports.get('ft_rendered_live', 0)}"},
        "CROSS_SURFACE_LIVE_TRUTH": {
            "status": "PASS" if cross_surface_pass else "FAIL" if cross_surface_observed else "NOT_RUN",
            "evidence": f"observed={cross_surface_observed}; mismatches={len(cross_surface_mismatches)}",
        },
        "CROSS_SURFACE_COMPETITION_IDENTITY": {
            "status": "PASS" if competition_pass else "FAIL" if competition_observed else "NOT_RUN",
            "evidence": f"matches_compared={int(competition.get('matches_compared') or 0)}; mismatches={len(competition.get('mismatches') or [])}",
        },
        "CROSS_SURFACE_COMPETITION_IDENTITY": {
            "status": "PASS" if competition_pass else "FAIL" if competition_observed else "NOT_RUN",
            "evidence": f"matches_compared={int(competition.get('matches_compared') or 0)}; mismatches={len(competition.get('mismatches') or [])}",
        },
        "OFFICIAL_SHARK_REFERENCE": {"status": "FOUNDER_REVIEW_REQUIRED" if shark in {"MATCH", "MINOR_GAP"} else "FAIL" if shark not in {"NOT_RUN", "NOT_OBSERVED"} else "NOT_RUN", "evidence": (visual.get("shark") or {}).get("evidence")},
        "OFFICIAL_BACKGROUND_REFERENCE": {"status": "FOUNDER_REVIEW_REQUIRED" if background in {"MATCH", "MINOR_GAP"} else "FAIL" if background not in {"NOT_RUN", "NOT_OBSERVED"} else "NOT_RUN", "evidence": (visual.get("background") or {}).get("evidence")},
        "VISUAL_FALSE_PASS_RECURRENCE": {"status": "FOUNDER_REVIEW_REQUIRED", "evidence": "Automated visual acceptance was previously rejected by Founder; rendered comparison remains mandatory."},
        "CLIENT_TECHNICAL_COPY_LEAK": {"status": "PASS" if copy_pass else "FAIL", "evidence": f"technical_matches={len(copy_state.get('technical_matches') or [])}"},
        "RECTANGLE_FATIGUE_CONTENT_DENSITY": {"status": "PASS" if density_pass else "FAIL", "evidence": f"first_viewport={density.get('first_viewport_product')}; depth={nested_depth}; bordered={density.get('bordered_containers')}; sports_ratio={sports_above_fold_ratio:.3f}"},
        "LARGE_UNJUSTIFIED_EMPTY_REGION": {"status": "PASS" if composition.get("observed") is True and not dead_space_flags else "FAIL" if composition.get("observed") is True else "NOT_RUN", "evidence": f"flags={len(dead_space_flags)}; coverage={composition.get('home_viewport_content_coverage')}"},
        "EMPTY_DASHBOARD": {"status": "PASS" if composition.get("observed") is True and not empty_dashboard_flags else "FAIL" if composition.get("observed") is True else "NOT_RUN", "evidence": f"flags={len(empty_dashboard_flags)}"},
        "SPORTS_ABOVE_FOLD_RATIO": {"status": "PASS" if sports_above_fold_ratio >= .05 else "FAIL" if composition.get("observed") is True else "NOT_RUN", "evidence": f"ratio={sports_above_fold_ratio:.3f}"},
        "TEAM_TO_PLAYER": {"status": "PASS" if (journeys.get("golden_sports_knowledge") or {}).get("pass") is True else "NOT_RUN", "evidence": "golden_sports_knowledge"},
        "MEDIA_RIGHTS_FAIL_CLOSED": {"status": "PASS" if rights_pass else "FAIL", "evidence": f"unsafe_media_visible={knowledge.get('unsafe_media_visible', 0)}"},
        "MOJIBAKE": {"status": "PASS" if not (text_quality.get("mojibake_matches") or []) else "FAIL", "evidence": f"mojibake={len(text_quality.get('mojibake_matches') or [])}"},
        "BROKEN_LINKS": {"status": "PASS" if click_pass and all(item.get("pass") is True for item in journeys.values()) else "FAIL", "evidence": f"journeys={len(journeys)}; js_errors={len(runtime.get('js_errors') or [])}"},
        "MOBILE_BOTTOM_NAV": {"status": "PASS" if mobile_pass else "FAIL", "evidence": f"mobile_taps={len(mobile_clicks)}"},
        "NO_TEXT_BORDER_COLLISION": {
            "status": "PASS" if layout_observed and not (collision_types & text_collision_types) else "FAIL" if layout_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('captures') or 0)}; collisions={int(layout.get('collisions') or 0)}; types={sorted(collision_types)}",
        },
        "NO_CARD_OVERFLOW": {
            "status": "PASS" if layout_observed and "card_overflow" not in collision_types else "FAIL" if layout_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('captures') or 0)}; card_overflow={'card_overflow' in collision_types}",
        },
        "SPANISH_COPY_STRESS": {
            "status": "PASS" if layout_observed and not (collision_types & {"button_clipping", "text_clipping", "viewport_escape"}) else "FAIL" if layout_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('captures') or 0)}; clipping_types={sorted(collision_types & {'button_clipping', 'text_clipping', 'viewport_escape'})}",
        },
        "MOBILE_360_LAYOUT": {
            "status": "PASS" if mobile_360_pass else "FAIL" if mobile_360_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('mobile_360_captures') or 0)}; collisions={int(layout.get('mobile_360_collisions') or 0)}; overflow={int(layout.get('mobile_360_overflow') or 0)}",
        },
        "NO_TEXT_BORDER_COLLISION": {
            "status": "PASS" if layout_observed and not (collision_types & text_collision_types) else "FAIL" if layout_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('captures') or 0)}; collisions={int(layout.get('collisions') or 0)}; types={sorted(collision_types)}",
        },
        "NO_CARD_OVERFLOW": {
            "status": "PASS" if layout_observed and "card_overflow" not in collision_types else "FAIL" if layout_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('captures') or 0)}; card_overflow={'card_overflow' in collision_types}",
        },
        "SPANISH_COPY_STRESS": {
            "status": "PASS" if layout_observed and not (collision_types & {"button_clipping", "text_clipping", "viewport_escape"}) else "FAIL" if layout_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('captures') or 0)}; clipping_types={sorted(collision_types & {'button_clipping', 'text_clipping', 'viewport_escape'})}",
        },
        "MOBILE_360_LAYOUT": {
            "status": "PASS" if mobile_360_pass else "FAIL" if mobile_360_observed else "NOT_RUN",
            "evidence": f"captures={int(layout.get('mobile_360_captures') or 0)}; collisions={int(layout.get('mobile_360_collisions') or 0)}; overflow={int(layout.get('mobile_360_overflow') or 0)}",
        },
        "CLIENT_ADMIN_SEPARATION": {"status": str((observation.get("security") or {}).get("client_admin_separation") or "NOT_RUN").upper(), "evidence": (observation.get("security") or {}).get("evidence")},
        "IMPORTANT_MATCH_PRIORITY": {"status": str(sports.get("important_match_priority") or "NOT_RUN").upper(), "evidence": sports.get("priority_evidence")},
        "PERFORMANCE_P0": {"status": str((observation.get("performance") or {}).get("status") or "NOT_RUN").upper(), "evidence": (observation.get("performance") or {}).get("evidence")},
        "TEMPORAL_CONTEXT_CONSISTENCY": {
            "status": "PASS" if temporal_pass else "FAIL" if temporal_observed else "NOT_RUN",
            "evidence": (
                f"checked={int(temporal.get('checked_cards') or 0)}; "
                f"missing={int(temporal.get('missing_cards') or 0)}; "
                f"ambiguous={int(temporal.get('ambiguous_cards') or 0)}; "
                f"cross_surface={temporal.get('cross_surface_consistent')}; madrid_time={temporal.get('madrid_time')}"
            ),
        },
    }


def _update_regression_manager(memory: dict[str, Any], observation: dict[str, Any], detected: list[dict[str, Any]], at: str, run_id: str) -> dict[str, Any]:
    records = memory.setdefault("regressions", {})
    supplied = _regression_result_defaults(observation)
    supplied.update({
        str(key): dict(value)
        for key, value in (observation.get("regression_results") or {}).items()
        if isinstance(value, dict)
    })
    issues_by_regression: dict[str, list[dict[str, Any]]] = {}
    for issue in detected:
        regression_id = ISSUE_TO_REGRESSION.get(str(issue.get("category") or "").upper())
        if regression_id:
            issues_by_regression.setdefault(regression_id, []).append(issue)
    for regression_id, contract in PINNED_REGRESSION_CONTRACTS.items():
        record = records.setdefault(regression_id, {
            "regression_id": regression_id,
            "category": contract["category"],
            "severity": contract["severity"],
            "regression_test": contract["test"],
            "memory_key": contract.get("memory_key") or regression_id,
            "first_seen_sha": "FOUNDER_OVERRIDE_BASELINE",
            "last_good_sha": "",
            "fix_sha": "",
            "root_cause": "Pendiente de evidencia revisada.",
            "recurrence_count": 0,
            "status": "NOT_RUN",
            "verification_history": [],
        })
        record["memory_key"] = contract.get("memory_key") or regression_id
        result = supplied.get(regression_id) or {"status": "NOT_RUN", "evidence": "Sin cobertura en esta ejecucion."}
        status = str(result.get("status") or "NOT_RUN").upper()
        related = issues_by_regression.get(regression_id) or []
        previous_status = str(record.get("status") or "NOT_RUN")
        if related:
            status = "FAIL"
            record["root_cause"] = _safe_text(related[0].get("actual") or related[0].get("evidence"), 700)
            if record.get("first_seen_sha") == "FOUNDER_OVERRIDE_BASELINE" and related[0].get("production_sha"):
                record["first_seen_sha"] = related[0].get("production_sha")
        if status == "FAIL" and previous_status in {"PASS", "RESOLVED", "FOUNDER_REVIEW_REQUIRED"}:
            record["recurrence_count"] = int(record.get("recurrence_count") or 0) + 1
        elif status == "PASS":
            record["last_good_sha"] = _safe_text(observation.get("production_sha"), 80)
        elif status == "FOUNDER_REVIEW_REQUIRED":
            record["root_cause"] = "Founder visual approval pending; automated evidence cannot resolve this contract."
        record["status"] = status
        record["last_run_id"] = run_id
        record["last_checked_at_madrid"] = at
        record["verification"] = _safe_text(result.get("evidence"), 1200)
        record.setdefault("verification_history", []).append({
            "at_madrid": at,
            "run_id": run_id,
            "sha": _safe_text(observation.get("production_sha"), 80),
            "status": status,
            "evidence": record["verification"],
        })
        record["verification_history"] = record["verification_history"][-40:]
    return build_regression_manager_status(memory)


def build_regression_manager_status(memory: dict[str, Any]) -> dict[str, Any]:
    values = list((memory.get("regressions") or {}).values())
    return {
        "status": "FAIL" if any(item.get("status") == "FAIL" and item.get("severity") == "P0" for item in values) else "WARNING" if any(item.get("status") in {"FAIL", "NOT_RUN", "FOUNDER_REVIEW_REQUIRED"} for item in values) else "PASS",
        "protected_regressions": len(values),
        "pass": sum(1 for item in values if item.get("status") == "PASS"),
        "fail": sum(1 for item in values if item.get("status") == "FAIL"),
        "founder_review_required": sum(1 for item in values if item.get("status") == "FOUNDER_REVIEW_REQUIRED"),
        "not_run": sum(1 for item in values if item.get("status") == "NOT_RUN"),
        "recurrences": sum(int(item.get("recurrence_count") or 0) for item in values),
        "items": values,
    }


def build_quality_director_decision(
    issues: list[dict[str, Any]],
    *,
    evidence_complete: bool,
    regression_manager: dict[str, Any],
    supplemental_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    supplemental_evidence = supplemental_evidence or {}
    gates = []
    open_real = [item for item in issues if str(item.get("status") or "OPEN_REAL") == "OPEN_REAL"]
    pending = [item for item in issues if str(item.get("status") or "") == "FIXED_PENDING_VERIFICATION"]
    regression_items = regression_manager.get("items") or []
    for gate in QUALITY_GATES:
        related = [item for item in open_real if _quality_gate_for_issue(item) == gate]
        related_pending = [item for item in pending if _quality_gate_for_issue(item) == gate]
        regressions = [item for item in regression_items if item.get("category") == gate]
        explicit = str((supplemental_evidence.get(gate) or {}).get("status") or "").upper()
        p0 = sum(1 for item in related if str(item.get("severity") or "").upper() == "P0")
        p1 = sum(1 for item in related if str(item.get("severity") or "").upper() == "P1")
        founder_review = any(item.get("status") == "FOUNDER_REVIEW_REQUIRED" for item in regressions)
        regression_fail = any(item.get("status") == "FAIL" for item in regressions)
        if p0 or explicit == "FAIL":
            status = "FAIL"
        elif p1 or regression_fail:
            status = "BLOCKED"
        elif founder_review or related_pending or explicit in {"WARNING", "BLOCKED"}:
            status = "WARNING"
        elif explicit == "PASS" or (evidence_complete and regressions and all(item.get("status") == "PASS" for item in regressions)):
            status = "PASS"
        else:
            status = "WARNING"
        authorities = [_evidence_authority(item.get("evidence_origin") or item.get("source") or "") for item in related]
        authority = max(authorities, key=lambda item: item[1])[0] if authorities else "AUTOMATED_BROWSER_QA" if evidence_complete else "UNIT_STATIC_TEST"
        gates.append({
            "area": gate,
            "status": status,
            "open_p0": p0,
            "open_p1": p1,
            "pending_verification": len(related_pending),
            "authority": authority,
        })
    open_p0 = sum(1 for item in open_real if str(item.get("severity") or "").upper() == "P0")
    open_p1 = sum(1 for item in open_real if str(item.get("severity") or "").upper() == "P1")
    if open_p0 or any(item["status"] == "FAIL" for item in gates):
        decision = "FAIL"
    elif open_p1 or any(item["status"] == "BLOCKED" for item in gates):
        decision = "BLOCKED"
    elif any(item["status"] == "WARNING" for item in gates):
        decision = "WARNING"
    else:
        decision = "PASS"
    return {
        "decision": decision,
        "release_quality_pass": decision == "PASS" and open_p0 == 0,
        "open_p0": open_p0,
        "open_p1": open_p1,
        "authority_order": sorted(EVIDENCE_AUTHORITY, key=EVIDENCE_AUTHORITY.get, reverse=True),
        "gates": gates,
        "reason": "Un FAIL de mayor autoridad nunca es anulado por una evidencia inferior.",
    }


def evaluate_production_sentinel(observation: dict[str, Any], quality_director: dict[str, Any]) -> dict[str, Any]:
    deployment = observation.get("deployment") or {}
    if not deployment:
        return {"result": "NOT_RUN", "rollback_recommended": False, "reason": "No es una observacion post-deploy real."}
    checks = (
        "health", "sha_alignment", "logs_recent", "critical_routes", "topbar_click_journey",
        "mobile_nav", "sports_truth", "temporal_context", "performance_sample", "critical_visual_surfaces", "client_admin_protection",
    )
    results = {name: str(deployment.get(name) or "NOT_RUN").upper() for name in checks}
    failed = [name for name, status in results.items() if status == "FAIL"]
    missing = [name for name, status in results.items() if status not in {"PASS", "FAIL"}]
    p0 = int(quality_director.get("open_p0") or 0)
    if failed or p0:
        result = "REGRESSION_DETECTED"
    elif missing:
        result = "BLOCKED"
    else:
        result = "PRODUCTION_CERTIFIED"
    return {
        "result": result,
        "production_sha": _safe_text(observation.get("production_sha"), 80),
        "checks": results,
        "failed_checks": failed,
        "missing_checks": missing,
        "rollback_recommended": result == "REGRESSION_DETECTED" and p0 > 0,
        "dangerous_actions_executed": False,
    }


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
        issue["evidence_origin"] = evidence_origin
        issue_id = issue["issue_id"]
        active_ids.add(issue_id)
        old = previous.get(issue_id)
        if old:
            issue["first_seen"] = old.get("first_seen") or issue["first_seen"]
            issue["seen_count"] = int(old.get("seen_count") or 1) + 1
            if old.get("status") in TERMINAL_ISSUE_STATUSES:
                issue["status"] = "OPEN_REAL"
                issue["reopened_count"] = int(old.get("reopened_count") or 0) + 1
            issue["history"] = [*(old.get("history") or []), {"at_madrid": at, "event": "SEEN_AGAIN"}][-40:]
        else:
            issue["history"] = [{"at_madrid": at, "event": "FIRST_DETECTED"}]
        previous[issue_id] = issue
    for issue_id, issue in previous.items():
        if issue_id in active_ids or issue.get("status") in TERMINAL_ISSUE_STATUSES:
            continue
        if scope != "full":
            continue
        history = issue.get("history") or []
        prior_clean_retest = bool(history and history[-1].get("event") == "NOT_REPRODUCED")
        founder_visual_review = str(issue.get("category") or "").upper() in {"VISUAL_SHARK", "VISUAL_BACKGROUND"}
        if prior_clean_retest and not founder_visual_review:
            issue["status"] = "RESOLVED"
            issue["resolved_at"] = at
            issue["verification"] = "Dos ejecuciones Browser QA completas consecutivas no reprodujeron el problema."
            event = "DETERMINISTIC_RETEST_PASS"
        else:
            issue["status"] = "FIXED_PENDING_VERIFICATION"
            event = "NOT_REPRODUCED"
        issue["last_checked"] = at
        issue["history"] = [*history, {"at_madrid": at, "event": event}][-40:]

    evidence_complete = bool(observation.get("evidence_complete"))
    blocking = [item for item in detected if item.get("severity") in {"P0", "P1"}]
    result = "PASS" if evidence_complete and not detected else "FAIL" if blocking else "WARNING"
    run_id = str(observation.get("run_id") or "PQA-" + datetime.fromisoformat(at).strftime("%Y%m%d%H%M%S"))
    regression_manager = _update_regression_manager(memory, observation, detected, at, run_id)
    quality_director = build_quality_director_decision(
        list(previous.values()),
        evidence_complete=evidence_complete,
        regression_manager=regression_manager,
        supplemental_evidence=observation.get("quality_evidence") or {},
    )
    production_sentinel = evaluate_production_sentinel(observation, quality_director)
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
        "quality_director": quality_director,
        "regression_manager": regression_manager,
        "production_sentinel": production_sentinel,
    }
    memory.setdefault("runs", []).append(run)
    memory["runs"] = memory["runs"][-120:]
    if result == "PASS" and scope == "full":
        memory["previous_good_run_id"] = run_id
    elif result == "PASS":
        memory["previous_good_critical_run_id"] = run_id
    memory["updated_at_madrid"] = at
    memory["worker_calibration"] = _calibrate_workers(memory)
    if production_sentinel.get("result") != "NOT_RUN":
        memory.setdefault("production_sentinel_runs", []).append({
            "run_id": run_id,
            "at_madrid": at,
            **production_sentinel,
        })
        memory["production_sentinel_runs"] = memory["production_sentinel_runs"][-40:]
    latest = {
        **run,
        "issues": detected,
        "open_issues": [item for item in previous.values() if item.get("status") in ACTIVE_ISSUE_STATUSES],
        "worker_calibration": memory["worker_calibration"],
        "founder_override_active": True,
        "previous_good_run_id": memory.get("previous_good_run_id"),
        "previous_good_critical_run_id": memory.get("previous_good_critical_run_id"),
        "next_expected_run": observation.get("next_expected_run") or "Segun cadencia QA: daily, post-deploy o weekly visual.",
        "quality_director": quality_director,
        "regression_manager": regression_manager,
        "production_sentinel": production_sentinel,
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
    open_issues = [item for item in issues if item.get("status") in ACTIVE_ISSUE_STATUSES]
    regression_manager = latest.get("regression_manager") or build_regression_manager_status(memory)
    quality_director = latest.get("quality_director") or build_quality_director_decision(
        issues,
        evidence_complete=bool(latest.get("evidence_complete")),
        regression_manager=regression_manager,
    )
    production_sentinel = latest.get("production_sentinel") or (
        (memory.get("production_sentinel_runs") or [{}])[-1]
        if memory.get("production_sentinel_runs")
        else {"result": "NOT_RUN", "rollback_recommended": False}
    )
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
        "quality_director": quality_director,
        "regression_manager": regression_manager,
        "production_sentinel": production_sentinel,
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
            "issue_status": "OPEN_REAL",
            "evidence_sufficient": bool(issue.get("evidence_sufficient", True)),
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
            "status": "OPEN_REAL",
            "evidence_origin": item.get("evidence_origin") or "LOCAL_QA",
            "evidence_sufficient": bool(item.get("evidence_sufficient", True)),
            "recommendation": f"Corregir y volver a ejecutar evidencia real. Esperado: {item.get('expected')}",
        }
        for item in status.get("open_issues") or []
    ]
