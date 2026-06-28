"""V859 company-wide audit board engine.

Safe structural audit only: no external calls, no DB writes, no invented real
business/data metrics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class AuditBoard:
    area: str
    status: str
    score: int
    findings: list[str]
    risks: list[str]
    recommended_actions: list[str]
    next_version_focus: str
    safe_notes: list[str]
    no_fake_data_notes: list[str]
    href: str


BOARD_BLUEPRINTS = [
    AuditBoard(
        area="Product Board",
        status="ok",
        score=8,
        findings=["La propuesta combina app deportiva, picks, SHARK, Telegram premium y admin.", "V857/V858 añadieron Company OS y dirección visual común."],
        risks=["La venta real depende de pruebas con usuarios, pagos reales y Render real."],
        recommended_actions=["Validar flujo comercial completo con capturas reales y sesión de usuario real."],
        next_version_focus="Validación comercial y demo guiada.",
        safe_notes=["No se inventan usuarios, ingresos ni resultados."],
        no_fake_data_notes=["Los scores son internos de auditoría estructural, no métricas comerciales reales."],
        href="/admin/company-os",
    ),
    AuditBoard(
        area="Client Experience Board",
        status="ok",
        score=8,
        findings=["Cliente móvil/PC tiene navegación, fondo SHARK, cards y estados premium.", "Rutas principales cliente están preservadas."],
        risks=["Sin screenshots reales no se puede declarar pixel-perfect."],
        recommended_actions=["Revisar vídeo/capturas reales por pantalla y ajustar densidad visual donde haga falta."],
        next_version_focus="QA visual con screenshots reales.",
        safe_notes=["Los estados vacíos deben usar textos seguros."],
        no_fake_data_notes=["No rellenar partidos, picks ni cuotas si no existen."],
        href="/app",
    ),
    AuditBoard(
        area="Admin Operations Board",
        status="strong",
        score=9,
        findings=["Admin tiene command center, Data Center, API-SPORTS, Telegram, SHARK, Company OS y rutas operativas.", "V859 añade Product Board para ordenar decisiones."],
        risks=["Algunas métricas operativas dependen de entorno real y claves reales."],
        recommended_actions=["Mantener Company OS y Company Audit como primeras entradas de diagnóstico."],
        next_version_focus="KPIs reales cuando Render y proveedores estén configurados.",
        safe_notes=["No exponer secrets ni tokens."],
        no_fake_data_notes=["No inventar consumo API, envíos Telegram ni errores."],
        href="/admin/dashboard",
    ),
    AuditBoard(
        area="Membership Revenue Board",
        status="needs_attention",
        score=7,
        findings=["FREE/PRO/ELITE tienen señales visuales y mensajes de valor.", "Pagos y revenue requieren prueba real para cerrar venta."],
        risks=["Pagos reales no validados en esta pasada.", "No se deben prometer beneficios garantizados."],
        recommended_actions=["Probar registro, upgrade, pago y perfil con flujo real antes de comercializar."],
        next_version_focus="Membresías y pagos reales.",
        safe_notes=["Usar Disponible en PRO/ELITE y Desbloquea análisis avanzado."],
        no_fake_data_notes=["No inventar ingresos, usuarios ni conversiones."],
        href="/admin/memberships",
    ),
    AuditBoard(
        area="Data Reality Board",
        status="blocked_by_real_api",
        score=7,
        findings=["API-SPORTS guard, live/escudos y estados seguros están preservados.", "The Odds API queda separada de datos deportivos."],
        risks=["Validación completa depende de claves reales en Render/local.", "No debe gastarse crédito por render."],
        recommended_actions=["Validar configuración real de API-SPORTS/The Odds API y revisar cache/TTL con datos reales."],
        next_version_focus="Provider QA real controlado.",
        safe_notes=["Cache-first y dry-run cuando sea posible."],
        no_fake_data_notes=["No inventar marcadores, minutos, cuotas, resultados ni escudos oficiales."],
        href="/admin/data-center",
    ),
    AuditBoard(
        area="SHARK Intelligence Board",
        status="ok",
        score=8,
        findings=["SHARK V845 y estados seguros siguen presentes.", "SHARK se integra con picks, partidos, Telegram y admin."],
        risks=["Calidad IA real depende de datos reales y proveedor OpenAI si está configurado."],
        recommended_actions=["Probar preguntas reales de partido/pick y fallback sin OpenAI."],
        next_version_focus="QA conversacional con datos reales.",
        safe_notes=["No usar seguro, fijo, garantizado, sin riesgo o apuesta segura."],
        no_fake_data_notes=["No inventar picks, cuotas, ROI ni confianza."],
        href="/admin/shark-ai",
    ),
    AuditBoard(
        area="Telegram Premium Board",
        status="blocked_by_real_render",
        score=8,
        findings=["Telegram V844 preserva no filler, dedupe y filtro premium.", "Admin command center está enlazado."],
        risks=["No se puede afirmar envío real sin prueba explícita.", "Tokens no deben mostrarse."],
        recommended_actions=["Probar dry-run, preview y envío real solo cuando el dueño lo pida."],
        next_version_focus="Telegram QA real en Render.",
        safe_notes=["No mandar mensajes reales en local por defecto."],
        no_fake_data_notes=["No inventar envíos, candidatos ni descartes."],
        href="/admin/telegram/command-center",
    ),
    AuditBoard(
        area="Technical Architecture Board",
        status="strong",
        score=9,
        findings=["Runtime, checks, build_clean_release y audit_release_zip están presentes.", "Compatibilidad V818-V858 preservada."],
        risks=["El tamaño de app.py y CSS sigue creciendo; requiere disciplina en futuras capas."],
        recommended_actions=["Priorizar refactors pequeños con tests, no reescrituras agresivas."],
        next_version_focus="Orden técnico gradual.",
        safe_notes=["No tocar DB_PATH ni rutas críticas sin smoke."],
        no_fake_data_notes=["No crear migraciones o writes durante render visual."],
        href="/admin/system",
    ),
    AuditBoard(
        area="Visual Reference Board",
        status="ok",
        score=8,
        findings=["V858 bloqueó tokens visuales y dirección común.", "Cliente, admin y Company OS comparten fondo, cards, chips y jerarquía."],
        risks=["La paridad exacta con referencias depende de screenshots reales."],
        recommended_actions=["Hacer QA con capturas 390/430/1440 y vídeo de flujo completo."],
        next_version_focus="Screenshot QA real.",
        safe_notes=["No declarar pixel-perfect sin capturas."],
        no_fake_data_notes=["No usar datos fake para que pantallas parezcan llenas."],
        href="/admin/visual-qa",
    ),
    AuditBoard(
        area="Render/GitHub/Release Board",
        status="blocked_by_real_render",
        score=8,
        findings=["ZIP limpio y audit_release_zip están operativos.", "Render real no se probó en esta pasada."],
        risks=["Deploy, variables y cron reales dependen de Render."],
        recommended_actions=["Validar deploy real, cron, health-check y runtime con logs de Render."],
        next_version_focus="Deploy/runtime real.",
        safe_notes=["No incluir .env real, DB local, logs, ZIPs internos ni secretos."],
        no_fake_data_notes=["No inventar deploys, logs ni consumo real."],
        href="/admin/production-readiness",
    ),
]


def build_audit_boards(runtime: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    runtime = runtime or {}
    boards: list[AuditBoard] = []
    for board in BOARD_BLUEPRINTS:
        if board.area == "Data Reality Board" and (runtime.get("api_sports_configured") or runtime.get("api_football_configured")):
            boards.append(board.__class__(**{**asdict(board), "status": "ok"}))
        else:
            boards.append(board)
    return [asdict(board) for board in boards]


def build_company_audit_summary(version: str = "", runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    boards = build_audit_boards(runtime)
    scores = [board["score"] for board in boards]
    top_risks = [risk for board in boards for risk in board["risks"]][:8]
    blocked = [board for board in boards if str(board["status"]).startswith("blocked")]
    needs_attention = [board for board in boards if board["status"] == "needs_attention"]
    next_actions = [board["recommended_actions"][0] for board in boards]
    return {
        "version": version,
        "global_score": round(mean(scores), 1) if scores else 0,
        "global_status": "needs_real_world_validation" if blocked or needs_attention else "strong",
        "audit_boards": boards,
        "top_risks": top_risks,
        "next_actions": next_actions,
        "blocked_by_real_world_validation": [board["area"] for board in blocked],
        "priority_roadmap": [
            "Deploy/runtime real",
            "Visual real con vídeo/capturas",
            "Móvil",
            "Admin",
            "Membresías/pagos",
            "Picks/live/datos",
            "SHARK/Telegram",
            "Rendimiento/caché",
            "Comercial/venta",
        ],
        "secrets_exposed": False,
        "external_calls": False,
        "database_writes": False,
        "data_invention_allowed": False,
    }
