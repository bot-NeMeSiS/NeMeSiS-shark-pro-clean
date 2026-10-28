"""Game-inspired design disciplines for NeMeSiS. Roles, not deployed agents.

Borrow general UI principles from retro arcade, simulation and modern game UX,
without copying third-party artwork, source code, copyrighted layouts or assets.
The presence of a discipline cannot certify a QA run or founder approval.
"""
from __future__ import annotations

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

def build_game_ui_lab():
    """Pure responsibility contract, not an executor or agent scheduler."""
    return {
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
