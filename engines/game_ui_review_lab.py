"""Game-inspired design disciplines for NeMeSiS. Roles, not deployed agents.

Borrow general UI principles from retro arcade, simulation and modern game UX,
without copying third-party artwork, source code, copyrighted layouts or assets.
The presence of a discipline cannot certify a QA run or founder approval.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import time


GAME_UI_REVIEW_CONTRACT = "NEMESIS-GAME-UI-REVIEW-V1"
NATIVE_REVIEW_CONTRACT = "NEMESIS-NATIVE-WORKFORCE-REVIEW-V1"
GAME_UI_REVIEW_TARGETS = (
    "reference_images/design_contracts.json",
    "static/img/approved-identity/manifest.json",
    "tools/visual_css_sources.json",
    "static/design-tokens.css",
    "static/design-system.css",
    "static/v968-directo-freshness.css",
    "static/v969-directo-mobile-calendar.css",
    "static/product-system.css",
    "templates/base.html",
    "static/platform-motion.js",
    "static/v1000-client-refinement.css",
    "templates/components/app_navigation.html",
    "templates/components/v933_navigation.html",
)
_FILE_LIMIT = 2 * 1024 * 1024
_TOTAL_LIMIT = 8 * 1024 * 1024
_STATES = {"PASS", "FAIL", "UNKNOWN"}

GAME_UI_DISCIPLINES = (
    {
        "id": "arcade_signal",
        "name": "Especialista de lectura instantánea · arcade clásico",
        "focus": "Escaneabilidad de marcadores, estados de partido, alertas y tiempos.",
        "surfaces": ("/directo", "/calendario", "/match"),
        "acceptance": "Reconocer equipos, resultado y estado sin animaciones ni etiquetas ambiguas.",
        "proof": "Capturas y revisión legible en 320/390/1440 px; no se fabrican estados deportivos.",
    },
    {
        "id": "strategy_information",
        "name": "Especialista de estrategia y simulación moderna",
        "focus": "Jerarquía de tablas, estadísticas, competiciones, filtros, odds y detalle.",
        "surfaces": ("/calendario", "/match", "/picks"),
        "acceptance": "Reducir búsqueda y clics sin eliminar contexto, trazabilidad o riesgos.",
        "proof": "Comparativa de rutas, densidad de información y navegación con usuarios reales.",
    },
    {
        "id": "technical_art",
        "name": "Artista técnico de interfaces premium",
        "focus": "Marca SHARK, contraste, profundidad, tipografía y componentes reutilizables.",
        "surfaces": ("/app", "/shark", "/admin/dashboard"),
        "acceptance": "Identidad única y coherente, sin superposición visual ni imágenes sin derechos.",
        "proof": "Referencias aprobadas, capturas antes/después y revisión humana independiente.",
    },
    {
        "id": "game_motion",
        "name": "Especialista de motion y respuesta táctil",
        "focus": "Transiciones cortas, estados de carga, interacción y feedback significativo.",
        "surfaces": ("/app", "/directo", "/picks"),
        "acceptance": "Estados comprensibles aun con animaciones desactivadas o datos lentos.",
        "proof": "Test prefers-reduced-motion, interacción teclado y escenarios sin conexión.",
    },
    {
        "id": "platform_accessibility",
        "name": "Diseñador de accesibilidad móvil y mandos",
        "focus": "Navegación táctil, teclado, foco, textos y safe-area en pantallas pequeñas.",
        "surfaces": ("/app", "/calendario", "/admin/company-os"),
        "acceptance": "Sin scroll lateral; foco visible, contrastes y objetivo táctil adecuados.",
        "proof": "QA a 320/390/768/1440 px, roles FREE/PRO/ELITE/Admin y lector de pantalla.",
    },
    {
        "id": "graphics_performance",
        "name": "Ingeniería de rendimiento visual",
        "focus": "Peso CSS/JS, imágenes, caché de assets, tiempos de respuesta y repaints.",
        "surfaces": ("/", "/calendario", "/directo", "/shark"),
        "acceptance": "Mejor tiempo de contenido útil sin ocultar errores 502 o datos obsoletos.",
        "proof": "Métricas LCP/INP/TTFB antes/después y revisión de logs, no puntuaciones inventadas.",
    },
    {
        "id": "visual_qa_director",
        "name": "Director de pruebas de interfaces interactivas",
        "focus": "Revisión de regresiones y evidencia por pantalla, estado y membresía.",
        "surfaces": ("/", "/picks", "/match", "/admin/dashboard"),
        "acceptance": "No fusionar cambios visuales si rompen permisos, datos, botones o móvil.",
        "proof": "Playwright real, screenshots, resultados comparables y aprobación humana.",
    },
)

def _text(value, limit=240):
    return value[:limit] if isinstance(value, str) else ""


def _source_snapshot(project_root, input_snapshot, deadline):
    """Read only fixed source paths, or reuse the caller's bounded snapshot."""
    root = Path(project_root).resolve() if input_snapshot is None else None
    result, total = {}, 0
    for relative in GAME_UI_REVIEW_TARGETS:
        result[relative] = None
        if deadline is not None and time.monotonic() >= deadline:
            continue
        try:
            if input_snapshot is not None:
                value = input_snapshot.get(relative) if isinstance(input_snapshot, dict) else None
                if not isinstance(value, str):
                    continue
                raw = value.encode("utf-8")
            else:
                path = (root / relative).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    continue
                with path.open("rb") as stream:
                    raw = stream.read(min(_FILE_LIMIT, max(0, _TOTAL_LIMIT - total)) + 1)
                value = raw.decode("utf-8").replace("\r\n", "\n")
            if len(raw) > _FILE_LIMIT or total + len(raw) > _TOTAL_LIMIT:
                continue
            total += len(raw)
            result[relative] = value.replace("\r\n", "\n")
        except (OSError, ValueError, UnicodeError, RuntimeError):
            continue
    return result


def _document(snapshot, path, deadline):
    if deadline is not None and time.monotonic() >= deadline:
        return {}
    try:
        data = json.loads(snapshot.get(path) or "null")
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError, RecursionError):
        return {}


def _check(identifier, state, detail):
    return {"id": identifier, "state": state, "scope": "STATIC_SOURCE", "detail": detail}


def _declared_asset_budget(manifest):
    rows = manifest.get("assets")
    if manifest.get("family") != "owner-approved-20261023" or not isinstance(rows, list) or not rows or len(rows) > 16:
        return _check("approved_asset_budget", "UNKNOWN", "Manifiesto aprobado no disponible o no reconocido.")
    sizes = {}
    for row in rows:
        if not isinstance(row, dict):
            return _check("approved_asset_budget", "UNKNOWN", "Entrada de manifiesto no válida.")
        name, size, digest = row.get("file"), row.get("bytes"), row.get("sha256")
        if (not isinstance(name, str) or not re.fullmatch(r"nemesis-approved-[a-z]+-[0-9]+\.webp", name)
                or type(size) is not int or size < 1 or size > _FILE_LIMIT
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or name in sizes):
            return _check("approved_asset_budget", "UNKNOWN", "Nombre, tamaño o huella de manifiesto no verificables.")
        sizes[name] = size
    mobile = ("nemesis-approved-mark-256.webp", "nemesis-approved-ocean-768.webp", "nemesis-approved-wireframe-480.webp")
    desktop = ("nemesis-approved-mark-256.webp", "nemesis-approved-ocean-1600.webp", "nemesis-approved-wireframe-960.webp")
    if any(name not in sizes for name in set(mobile + desktop)):
        return _check("approved_asset_budget", "UNKNOWN", "Faltan variantes declaradas para comparar presupuestos.")
    mobile_bytes, desktop_bytes = sum(sizes[x] for x in mobile), sum(sizes[x] for x in desktop)
    return _check("approved_asset_budget", "PASS" if mobile_bytes < 155000 and desktop_bytes < 400000 else "FAIL",
                  f"Bytes declarados: móvil {mobile_bytes}/155000; escritorio {desktop_bytes}/400000. No son transferencia medida ni integridad del binario.")


def _bundle_check(snapshot, deadline):
    if deadline is not None and time.monotonic() >= deadline:
        return _check("canonical_bundle_sources", "UNKNOWN", "Presupuesto temporal agotado antes de revisar el bundle.")
    try:
        names = json.loads(snapshot.get("tools/visual_css_sources.json") or "null")
        if (not isinstance(names, list) or not names or len(names) > 16
                or any(not isinstance(name, str) for name in names) or len(set(names)) != len(names)):
            raise ValueError("Invalid source list")
        paths = ["static/" + name for name in names]
        if any(path not in GAME_UI_REVIEW_TARGETS or snapshot.get(path) is None for path in paths):
            return _check("canonical_bundle_sources", "UNKNOWN", "Fuentes del bundle fuera de esta muestra limitada o no disponibles.")
        bundle = snapshot.get("static/product-system.css")
        if bundle is None:
            return _check("canonical_bundle_sources", "UNKNOWN", "Bundle no disponible en la muestra.")
        digest = sha256("\n".join(snapshot[path].replace("\r\n", "\n") for path in paths).encode()).hexdigest()
        expected = "/* Generated by npm run build:css; source-sha256: " + digest + " */\n"
        valid = bundle.startswith(expected) and bool(bundle[len(expected):].strip())
        return _check("canonical_bundle_sources", "PASS" if valid else "FAIL",
                      "Huella de fuentes y cabecera del bundle " + ("coinciden." if valid else "no coinciden.") + " No sustituye ejecutar el builder oficial.")
    except (ValueError, TypeError, RecursionError):
        return _check("canonical_bundle_sources", "UNKNOWN", "Lista de fuentes no válida; no se infiere el estado del bundle.")


def evaluate_game_ui_review(project_root, *, evidence=None, candidate_revision="", observed_at="", input_snapshot=None, deadline=None):
    """Actually inspect bounded local sources; never execute or impersonate browser QA.

    An injected source snapshot avoids a second filesystem scan in the native
    review cycle. Arbitrary evidence dictionaries cannot promote visual checks
    to PASS. Existing observed QA issues are joined by the parent cycle.
    """
    started_in_budget = deadline is None or time.monotonic() < deadline
    snapshot = _source_snapshot(project_root, input_snapshot, deadline)
    metadata = {path: {"path": path, "sha256": sha256(value.encode()).hexdigest() if value is not None else "",
                       "state": "READ" if value is not None else "UNAVAILABLE"}
                for path, value in snapshot.items()}
    fingerprint = sha256(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    contract = _document(snapshot, "reference_images/design_contracts.json", deadline)
    contract_ok = contract.get("contract") == "NEMESIS-CREATIVE-DESIGN-1"
    policy = contract.get("policy") if isinstance(contract.get("policy"), dict) else {}
    raw_screens = contract.get("screens") if contract_ok else None
    screens = {item.get("screen_id"): item for item in raw_screens if isinstance(item, dict) and isinstance(item.get("screen_id"), str)} if isinstance(raw_screens, list) and len(raw_screens) <= 64 else {}
    manifest = _document(snapshot, "static/img/approved-identity/manifest.json", deadline)
    base, motion, css = (snapshot.get(path) for path in ("templates/base.html", "static/platform-motion.js", "static/design-system.css"))
    sports = [screens.get(key) for key in ("LIVE", "MATCHES", "MATCH")]
    sports_defined = all(item and item.get("route") and isinstance(item.get("primary_content"), list) and item["primary_content"] for item in sports)
    actions_defined = all(screens.get(key, {}).get("actions") for key in ("HOME", "MATCHES", "PICKS", "MATCH"))
    bundle = _bundle_check(snapshot, deadline)
    budget = _declared_asset_budget(manifest)
    markers = bool(base and motion and "platform-motion.js" in base and "data-motion-toggle" in base
                   and "data-motion-toggle" in motion and "toggle.addEventListener('click'" in motion
                   and "prefers-reduced-motion" in motion and "visibilitychange" in motion)
    media = bool(css and all(item in css for item in ("prefers-contrast", "prefers-reduced-transparency", "forced-colors")))
    checks = {
        "arcade_signal": [
            _check("sports_screen_contracts", "PASS" if sports_defined else "FAIL" if contract_ok and screens else "UNKNOWN", "Contratos LIVE, calendario y detalle " + ("definidos." if sports_defined else "incompletos o no disponibles.")),
            _check("rendered_score_readability", "UNKNOWN", "No se ha ejecutado una medición de marcadores, estados y horas renderizados.")],
        "strategy_information": [
            _check("screen_action_contracts", "PASS" if actions_defined else "FAIL" if contract_ok and screens else "UNKNOWN", "Acciones declaradas de Inicio, calendario, picks y detalle " + ("disponibles." if actions_defined else "incompletas o no disponibles.")),
            _check("native_navigation_journey", "UNKNOWN", "Un contrato de rutas no acredita clics, filtros ni retorno de navegación.")],
        "technical_art": [bundle,
            _check("effective_shark_visibility", "UNKNOWN", "Carga, hash o alpha de una imagen no miden su oclusión por paneles; falta revisión renderizada.")],
        "game_motion": [
            _check("motion_source_binding", "PASS" if markers else "UNKNOWN", "Marcadores de pausa, vínculo del control, reducción de movimiento y visibilidad " + ("presentes en fuente." if markers else "no reconocidos en esta muestra.")),
            _check("motion_browser_behaviour", "UNKNOWN", "No se ejecutaron teclado, historial, pausa ni almacenamiento bloqueado en navegador.")],
        "platform_accessibility": [
            _check("accessibility_media_declarations", "PASS" if media else "UNKNOWN", "Preferencias de contraste, transparencia y colores forzados " + ("declaradas en fuente." if media else "no reconocidas en esta muestra.")),
            _check("viewport_role_accessibility", "UNKNOWN", "Sin medición de foco, contraste real, taps ni cobertura 320/390/768/1440 y FREE/PRO/ELITE/Admin en esta pasada.")],
        "graphics_performance": [budget,
            _check("browser_performance", "UNKNOWN", "Los bytes declarados no acreditan LCP, INP, TTFB, errores HTTP ni latencia de producción.")],
        "visual_qa_director": [
            _check("design_policy_boundary", "PASS" if contract_ok and policy.get("functional_pass_implies_design_match") is False and policy.get("automatic_publication") is False else "UNKNOWN", "La política estática debe separar funcionamiento, aprobación visual y publicación."),
            _check("current_revision_visual_evidence", "UNKNOWN", "No hay recibo de navegador validado por esta pasada; no se acredita captura, CI, aprobación humana ni producción.")],
    }
    target_groups = {
        "arcade_signal": ("reference_images/design_contracts.json",),
        "strategy_information": ("reference_images/design_contracts.json", "templates/components/app_navigation.html", "templates/components/v933_navigation.html"),
        "technical_art": ("tools/visual_css_sources.json", "static/design-tokens.css", "static/design-system.css", "static/product-system.css"),
        "game_motion": ("templates/base.html", "static/platform-motion.js", "static/v1000-client-refinement.css"),
        "platform_accessibility": ("reference_images/design_contracts.json", "static/design-system.css"),
        "graphics_performance": ("static/img/approved-identity/manifest.json", "static/product-system.css", "static/platform-motion.js"),
        "visual_qa_director": ("reference_images/design_contracts.json",),
    }
    proposals = {
        "arcade_signal": "Verificar lectura de equipos, marcador, estado y hora Madrid en las pantallas deportivas con una muestra renderizada del candidato.",
        "strategy_information": "Comprobar filtros, apertura de partido y navegación de vuelta con teclado y puntero, conservando contexto y permisos.",
        "technical_art": "Medir la presencia efectiva del tiburón y su oclusión por paneles con capturas del candidato; conservar recursos aprobados y legibilidad.",
        "game_motion": "Ejecutar los escenarios existentes de pausa, reduced-motion, retorno de historial y almacenamiento restringido para el candidato.",
        "platform_accessibility": "Completar la muestra de foco, contraste y targets táctiles en los viewports y roles del contrato, sin dar PASS a medidas desconocidas.",
        "graphics_performance": "Contrastar presupuestos de recursos con transferencia y tiempos observados; mantener errores HTTP y métricas desconocidas visibles.",
        "visual_qa_director": "Vincular resultados y capturas existentes a revisión, fecha, viewport y rol; mantener los rechazos del fundador hasta su revisión real.",
    }
    # A partially inspected group is conservatively not credited as seven
    # completed reviews. The caller records the budget outcome separately.
    completed_in_budget = started_in_budget and (deadline is None or time.monotonic() < deadline)
    results, findings = [], []
    for discipline in GAME_UI_DISCIPLINES:
        identifier = discipline["id"]
        items = checks[identifier]
        state = "FAIL" if any(item["state"] == "FAIL" for item in items) else "UNKNOWN" if any(item["state"] == "UNKNOWN" for item in items) else "PASS"
        details = [item["detail"] for item in items if item["state"] == "FAIL"] or [item["detail"] for item in items if item["state"] == "UNKNOWN"]
        proposal = proposals[identifier]
        if state == "FAIL" and identifier == "technical_art":
            proposal = "Reconciliar fuentes y bundle con el builder canónico y conservar después la revisión visual del tiburón."
        finding = {"reviewer": discipline["name"], "module": "GAME_UI_REVIEW", "screen": identifier,
                   "route": discipline["surfaces"][0], "component": identifier, "evidence": " ".join(details)[:620],
                   "priority": "P2" if state == "FAIL" else "P3", "impact_user": discipline["acceptance"],
                   "user_impact": discipline["acceptance"], "impact_business": "Conserva evidencia verificable de la calidad de la experiencia.",
                   "business_impact": "Conserva evidencia verificable de la calidad de la experiencia.", "proposal": proposal,
                   "source": GAME_UI_REVIEW_CONTRACT, "certification_state": "REQUIRES_REVIEW" if state == "FAIL" else "INSUFFICIENT_DATA",
                   "candidate_improvement_ready": True, "approved_for_execution": False, "automatic_execution_allowed": False}
        if completed_in_budget:
            findings.append(finding)
        results.append({"id": identifier, "group": "game_ui", "area": discipline["name"], "state": state,
                        "executed": completed_in_budget,
                        "check_ids": [item["id"] for item in items], "checks": items,
                        "targets": list(target_groups[identifier]), "source_fingerprint": fingerprint,
                        "evidence": [metadata[path] for path in target_groups[identifier]], "findings": [finding] if completed_in_budget else [],
                        "proposal": proposal, "limitation": "Revisión estática parcial; no ejecuta navegador, modelos, pagos ni envíos, y no acredita funcionamiento continuo."})
    return {"contract": GAME_UI_REVIEW_CONTRACT, "execution_kind": "DETERMINISTIC_LOCAL_READ_ONLY",
            "scope": "STATIC_PARTIAL", "checked_at": _text(observed_at, 80),
            "candidate_revision_advertised": _text(candidate_revision, 80), "source_fingerprint": fingerprint,
            "disciplines": results, "results": results, "findings": findings,
            "external_calls": 0, "browser_executed": False, "production_certified": False,
            "time_budget_exhausted": deadline is not None and time.monotonic() >= deadline,
            "unverified_evidence_promoted": False, "supplied_evidence_used": False}


def build_game_ui_lab(review=None):
    """Project an existing receipt; never schedule or execute the seven reviews."""
    lab = {
        "contract": "NEMESIS-GAME-UI-LAB-V1",
        "state": "PLANNED_NOT_EXECUTED",
        "members_are": "ROLES_DE_REVISION_NO_PERSONAS_CONTRATADAS",
        "autonomous_agents_started": 0,
        "external_calls": 0,
        "releases_approved": 0,
        "paid_credits_consumed": 0,
        "design_reference_authority": "REFERENCIAS_APROBADAS_EXISTENTES",
        "copyright_rule": "NO_COPIAR_ASSETS_DE_VIDEOJUEGOS",
        "founder_review_required": True,
        "target_viewports": [320, 390, 768, 1440],
        "tiers": ["FREE", "PRO", "ELITE", "ADMIN"],
        "disciplines": [
            {**item, "surfaces": list(item["surfaces"]), "execution_state": "UNVERIFIED"}
            for item in GAME_UI_DISCIPLINES
        ],
    }
    loaded = review if isinstance(review, dict) else {}
    receipt = loaded.get("receipt") if isinstance(loaded.get("receipt"), dict) else {}
    recent = loaded.get("state") == "RECENT" and receipt.get("contract") == NATIVE_REVIEW_CONTRACT
    records = loaded.get("results") if isinstance(loaded.get("results"), list) else []
    by_id = {row.get("id"): row for row in records if isinstance(row, dict) and isinstance(row.get("id"), str)}
    lab["receipt_state"] = loaded.get("state") if loaded.get("state") in {"RECENT", "STALE", "NOT_RUN", "UNAVAILABLE", "CLOCK_UNVERIFIED"} else "NOT_RUN"
    lab["last_review_at"] = _text(receipt.get("finished_at_madrid"), 80)
    lab["review_run_id"] = _text(receipt.get("run_id"), 100)
    lab["scope"] = "STATIC_PARTIAL" if recent else "UNVERIFIED"
    lab["reviewed_count"] = sum(1 for item in lab["disciplines"] if recent and by_id.get(item["id"], {}).get("state") in _STATES and by_id.get(item["id"], {}).get("executed") is True)
    if lab["reviewed_count"]:
        lab["state"] = "STATIC_REVIEW_RECORDED"
    for discipline in lab["disciplines"]:
        item = by_id.get(discipline["id"], {})
        if recent and item.get("state") in _STATES and item.get("executed") is True:
            discipline["execution_state"] = "STATIC_PARTIAL"
            discipline["review_state"] = item["state"]
            discipline["review_label"] = {"PASS": "Comprobación estática conforme", "FAIL": "Hallazgo estático que revisar", "UNKNOWN": "Revisión estática con evidencia pendiente"}[item["state"]]
            discipline["last_review_at"] = lab["last_review_at"]
            discipline["proposal"] = _text(item.get("proposal"), 420)
            discipline["limitation"] = _text(item.get("limitation"), 360)
            proofs = item.get("evidence") if isinstance(item.get("evidence"), list) else []
            discipline["evidence"] = [{"path": e["path"],
                                       "sha256": e.get("sha256") if isinstance(e.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", e["sha256"]) else "",
                                       "state": e.get("state") if isinstance(e.get("state"), str) and re.fullmatch(r"[A-Z_]{1,32}", e["state"]) else "UNAVAILABLE"}
                                      for e in proofs[:16] if isinstance(e, dict) and e.get("path") in GAME_UI_REVIEW_TARGETS]
            checks = item.get("checks") if isinstance(item.get("checks"), list) else []
            discipline["checks"] = [{"state": check["state"], "detail": _text(check.get("detail"), 360)}
                                   for check in checks[:16] if isinstance(check, dict) and isinstance(check.get("state"), str) and check["state"] in _STATES]
    return lab
