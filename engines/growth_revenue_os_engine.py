"""Founder-controlled Growth & Revenue OS.

This module is a read-only commercial planning layer. It consumes existing
product, revenue, beta, roadmap and Founder evidence; it does not launch
campaigns, connect channels, call Stripe, send Telegram messages or mutate
customers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo


MADRID = ZoneInfo("Europe/Madrid")
GROWTH_REVENUE_OS_CONTRACT = "NEMESIS-GROWTH-REVENUE-OS-V1"
INSUFFICIENT_REAL_DATA = "INSUFFICIENT_REAL_DATA"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _label(value: Any) -> str:
    if value in (None, "", "None"):
        return "Sin datos reales"
    return str(value)


def _rate_label(rate: Mapping[str, Any] | None) -> str:
    rate = _mapping(rate)
    if rate.get("value") in (None, ""):
        return "Sin muestra suficiente"
    try:
        return f"{float(rate['value']):.1f}%"
    except (TypeError, ValueError):
        return "Sin muestra suficiente"


def _evidence_state(value: Any, *, minimum: int = 1) -> str:
    if value in (None, ""):
        return INSUFFICIENT_REAL_DATA
    return "PARTIALLY_VERIFIED" if _int(value) >= minimum else INSUFFICIENT_REAL_DATA


def _now(now_madrid: str | None = None) -> str:
    return now_madrid or datetime.now(MADRID).isoformat(timespec="seconds")


GROWTH_ROLES: tuple[dict[str, Any], ...] = (
    {
        "key": "head_of_growth",
        "title": "Head of Growth",
        "scope": "Coordina adquisicion, activacion, conversion, retencion y experimentos.",
        "inputs": ["Go To Market Office", "User Intelligence", "Product Memory", "TOP100"],
    },
    {
        "key": "marketing_director",
        "title": "Marketing Director",
        "scope": "Ordena canales, posicionamiento, mensajes y lanzamiento sin publicar automaticamente.",
        "inputs": ["Company Platform", "Executive Board", "Market Intelligence"],
    },
    {
        "key": "content_seo_lead",
        "title": "Content & SEO Lead",
        "scope": "Prepara contenido evergreen, arquitectura SEO y calendario editorial approval-first.",
        "inputs": ["Company Platform", "Source Compliance", "Product Memory"],
    },
    {
        "key": "social_media_lead",
        "title": "Social Media Lead",
        "scope": "Define formatos por canal sin conectar cuentas ni publicar.",
        "inputs": ["Content Factory", "Responsible Marketing Policy"],
    },
    {
        "key": "crm_lifecycle_lead",
        "title": "CRM / Lifecycle Lead",
        "scope": "Disena ciclos welcome, first value, retorno, renovacion y winback con consentimiento.",
        "inputs": ["User Intelligence", "Beta Program", "Customer Success"],
    },
    {
        "key": "customer_success_lead",
        "title": "Customer Success Lead",
        "scope": "Reduce friccion, soporte, cancelacion confusa y motivos de churn.",
        "inputs": ["Beta Program", "Support Center", "Product Review"],
    },
    {
        "key": "cro_conversion_lead",
        "title": "CRO / Conversion Lead",
        "scope": "Mejora FREE -> PRO -> ELITE sin patrones oscuros ni presion falsa.",
        "inputs": ["Memberships", "Product Analytics", "Browser QA"],
    },
    {
        "key": "revenue_membership_lead",
        "title": "Revenue & Membership Lead",
        "scope": "Vigila valor por plan, MRR cuando exista y seguridad comercial.",
        "inputs": ["Revenue Analytics", "Stripe certification", "Founder Center"],
    },
    {
        "key": "partnerships_affiliates_lead",
        "title": "Partnerships / Affiliates Lead",
        "scope": "Prepara gobernanza de partners sin acuerdos activos ni sesgo comercial en SHARK.",
        "inputs": ["Source Compliance", "Responsible Marketing", "Legal"],
    },
    {
        "key": "growth_analytics_lead",
        "title": "Growth Analytics Lead",
        "scope": "Define metricas, baselines y guardrails; bloquea metricas falsas.",
        "inputs": ["Product Analytics", "Revenue Analytics", "Beta Metrics"],
    },
)


FUNNEL_DEFINITIONS: tuple[dict[str, str], ...] = (
    {"key": "discovery", "label": "DISCOVERY", "definition": "Una persona descubre NeMeSiS por un canal medible y consentido.", "owner": "Marketing Director"},
    {"key": "landing", "label": "LANDING", "definition": "Visita una superficie publica y entiende la propuesta de valor.", "owner": "Content & SEO Lead"},
    {"key": "registration", "label": "REGISTRATION", "definition": "Crea una cuenta sin friccion ni datos innecesarios.", "owner": "Head of Growth"},
    {"key": "free", "label": "FREE", "definition": "Usa el plan gratuito y ve valor basico real.", "owner": "CRO / Conversion Lead"},
    {"key": "first_value", "label": "FIRST VALUE", "definition": "Encuentra un partido, equipo, competicion o briefing util.", "owner": "Head of UX"},
    {"key": "activated", "label": "ACTIVATED", "definition": "Repite una accion clave o configura un favorito.", "owner": "CRM / Lifecycle Lead"},
    {"key": "returning", "label": "RETURNING", "definition": "Vuelve en otra sesion o dia con senal agregada.", "owner": "CRM / Lifecycle Lead"},
    {"key": "premium_intent", "label": "PREMIUM INTENT", "definition": "Consulta membresias, preview premium o valor PRO/ELITE.", "owner": "Revenue & Membership Lead"},
    {"key": "pro_elite", "label": "PRO / ELITE", "definition": "Tiene plan de pago confirmado o evento de pago certificado.", "owner": "Revenue & Membership Lead"},
    {"key": "retained", "label": "RETAINED", "definition": "Permanece activo tras un periodo definido y medible.", "owner": "Customer Success Lead"},
    {"key": "referral", "label": "REFERRAL", "definition": "Invita a otra persona y esa invitacion progresa sin abuso.", "owner": "Partnerships / Affiliates Lead"},
)


AUTOMATION_LEVELS: tuple[dict[str, Any], ...] = (
    {"level": 0, "name": "OBSERVE", "allowed": True, "human_approval_required": False},
    {"level": 1, "name": "ANALYZE", "allowed": True, "human_approval_required": False},
    {"level": 2, "name": "PROPOSE", "allowed": True, "human_approval_required": False},
    {"level": 3, "name": "PREPARE", "allowed": True, "human_approval_required": False},
    {"level": 4, "name": "SCHEDULE_AFTER_APPROVAL", "allowed": True, "human_approval_required": True},
    {"level": 5, "name": "PUBLISH_OR_SPEND", "allowed": False, "human_approval_required": True},
)


def _build_funnel(product: dict[str, Any], revenue: dict[str, Any]) -> list[dict[str, Any]]:
    raw_funnel = _mapping(product.get("funnel"))
    users = _mapping(product.get("users"))
    activity = _mapping(product.get("activity"))
    commerce = _mapping(product.get("commerce"))
    memberships = _mapping(revenue.get("memberships")) or _mapping(users.get("memberships"))
    active_events = _int(raw_funnel.get("active"))
    registered = _int(raw_funnel.get("registered") or users.get("registered_users"))
    pro_interest = _int(raw_funnel.get("pro_interest"))
    checkout_started = _int(raw_funnel.get("checkout_started") or commerce.get("checkout_started"))
    paid = _int(memberships.get("PRO")) + _int(memberships.get("ELITE")) + _int(memberships.get("ELITE+"))
    stage_values = {
        "discovery": None,
        "landing": None,
        "registration": registered,
        "free": _int(memberships.get("FREE")),
        "first_value": None,
        "activated": active_events,
        "returning": None,
        "premium_intent": pro_interest or checkout_started,
        "pro_elite": paid,
        "retained": None,
        "referral": None,
    }
    evidence_sources = {
        "discovery": "Sin fuente de trafico consentida conectada.",
        "landing": "Company Platform preparada; visitas anonimas no estimadas.",
        "registration": "Tabla de usuarios agregada si existe.",
        "free": "Planes agregados, sin PII.",
        "first_value": "Pendiente de evento minimizado de primer valor.",
        "activated": "Eventos propios si existen; sin usuarios identificables.",
        "returning": "Requiere cohorte o sesiones recurrentes.",
        "premium_intent": "Eventos de membresias o checkout si existen.",
        "pro_elite": "Planes agregados o pagos confirmados certificados.",
        "retained": "Requiere ventana de retencion definida.",
        "referral": "Programa de referidos no activado.",
    }
    rows = []
    for item in FUNNEL_DEFINITIONS:
        key = item["key"]
        value = stage_values.get(key)
        state = _evidence_state(value)
        rows.append(
            {
                **item,
                "value": value,
                "value_label": _label(value),
                "evidence_state": state,
                "evidence": evidence_sources[key],
                "data_quality": "LOW_SAMPLE" if state == INSUFFICIENT_REAL_DATA else "PARTIAL_REAL_DATA",
                "next_measurement": _next_measurement_for_stage(key),
            }
        )
    return rows


def _next_measurement_for_stage(stage: str) -> str:
    mapping = {
        "discovery": "Definir fuente de adquisicion con consentimiento y UTM seguro.",
        "landing": "Medir visitas agregadas sin fingerprinting.",
        "registration": "Mantener conteo agregado de altas.",
        "free": "Relacionar plan FREE con actividad agregada.",
        "first_value": "Instrumentar primer partido/equipo/briefing consultado.",
        "activated": "Definir activacion por accion repetible.",
        "returning": "Medir retorno diario/semanal por cohorte agregada.",
        "premium_intent": "Registrar visitas a valor premium y previews.",
        "pro_elite": "Certificar pagos test antes de ingreso real.",
        "retained": "Medir renovacion y uso sostenido.",
        "referral": "Disenar invitacion anti-abuso antes de activar.",
    }
    return mapping.get(stage, "Definir medicion segura.")


def _build_revenue_brief(product: dict[str, Any], revenue: dict[str, Any], funnel: list[dict[str, Any]], now_iso: str) -> dict[str, Any]:
    memberships = _mapping(revenue.get("memberships")) or _mapping(_mapping(product.get("users")).get("memberships"))
    commerce = _mapping(revenue.get("payment_event_counts")) or _mapping(product.get("commerce"))
    registered = next((item for item in funnel if item["key"] == "registration"), {})
    premium = next((item for item in funnel if item["key"] == "premium_intent"), {})
    pro_elite = next((item for item in funnel if item["key"] == "pro_elite"), {})
    no_traffic = all(item.get("evidence_state") == INSUFFICIENT_REAL_DATA for item in funnel[:2])
    recommendation = (
        "Cerrar medicion de visitas, primer valor y activacion antes de invertir en adquisicion."
        if no_traffic
        else "Analizar donde cae el embudo antes de proponer una campana."
    )
    return {
        "title": f"Founder Revenue Brief - {now_iso[:10]}",
        "state": "PREPARED",
        "traffic_state": INSUFFICIENT_REAL_DATA if no_traffic else "PARTIALLY_VERIFIED",
        "visits": "Sin datos reales",
        "registrations": registered.get("value_label", "Sin datos reales"),
        "activations": next((item.get("value_label") for item in funnel if item["key"] == "activated"), "Sin datos reales"),
        "returning_users": "Sin datos reales",
        "premium_intent": premium.get("value_label", "Sin datos reales"),
        "pro": _int(memberships.get("PRO")),
        "elite": _int(memberships.get("ELITE")) + _int(memberships.get("ELITE+")),
        "mrr": revenue.get("mrr") if revenue.get("mrr") not in (None, "") else "No certificado",
        "churn": "Sin cohorte suficiente",
        "conversions": _rate_label(product.get("conversion_registered_to_paid")),
        "main_channels": "Sin atribucion real",
        "winning_content": "Sin contenido medido",
        "main_friction": _main_friction(funnel),
        "main_opportunity": _main_opportunity(funnel, pro_elite),
        "daily_recommendation": recommendation,
        "evidence": ["Product Analytics", "Revenue Analytics", "Founder Center", "Go To Market Office"],
        "limitations": [
            "No se estima trafico si no existe fuente consentida.",
            "No se calcula MRR sin importes, moneda e intervalo certificados.",
            "No se mezcla SIMULATED_GROWTH_QA con usuarios reales.",
        ],
    }


def _main_friction(funnel: list[dict[str, Any]]) -> str:
    for key in ("discovery", "landing", "first_value", "returning", "retained"):
        item = next((stage for stage in funnel if stage["key"] == key), {})
        if item.get("evidence_state") == INSUFFICIENT_REAL_DATA:
            return f"Falta evidencia real en {item.get('label', key)}."
    return "La muestra comercial aun es pequena; no declarar ganadores."


def _main_opportunity(funnel: list[dict[str, Any]], pro_elite: dict[str, Any]) -> str:
    if pro_elite.get("evidence_state") == INSUFFICIENT_REAL_DATA:
        return "Explicar valor PRO/ELITE con previews responsables antes de cobrar."
    registration = next((stage for stage in funnel if stage["key"] == "registration"), {})
    if registration.get("evidence_state") != INSUFFICIENT_REAL_DATA:
        return "Convertir registrados en primer valor medible y retorno semanal."
    return "Preparar beta cerrada con medicion honesta del primer uso."


def _channel_plan() -> list[dict[str, Any]]:
    return [
        {"channel": "Instagram", "status": "DISCONNECTED", "goal": "Marca y prueba social responsable", "format": "Reels cortos y carruseles", "frequency": "Propuesta, no programada", "metric": "Alcance cualificado", "cta": "Unirse a beta"},
        {"channel": "TikTok", "status": "DISCONNECTED", "goal": "Descubrimiento rapido", "format": "Videos educativos breves", "frequency": "Propuesta, no programada", "metric": "Retencion de video", "cta": "Ver briefing"},
        {"channel": "YouTube", "status": "DISCONNECTED", "goal": "Confianza y metodologia", "format": "Shorts y guias", "frequency": "Propuesta, no programada", "metric": "Tiempo visto", "cta": "Aprender metodologia"},
        {"channel": "X", "status": "DISCONNECTED", "goal": "Actualidad y posicionamiento", "format": "Hilos y updates", "frequency": "Propuesta, no programada", "metric": "Clicks cualificados", "cta": "Leer analisis"},
        {"channel": "Facebook", "status": "DISCONNECTED", "goal": "Audiencia amplia y soporte", "format": "Posts y comunidad", "frequency": "Propuesta, no programada", "metric": "Preguntas utiles", "cta": "Centro de ayuda"},
        {"channel": "Telegram", "status": "DISCONNECTED_FOR_MARKETING", "goal": "Retencion opt-in", "format": "Briefings aprobados", "frequency": "Solo con aprobacion", "metric": "Opt-in y bajas", "cta": "Activar notificaciones"},
    ]


def _top20_revenue_actions() -> list[dict[str, Any]]:
    items = [
        ("GR-001", "Medir visitas y fuente de llegada sin fingerprinting", "Activacion", "Alta", "Media", "Company Platform, privacidad"),
        ("GR-002", "Definir primer valor como evento medible", "Activacion", "Alta", "Media", "User Intelligence"),
        ("GR-003", "Crear preview PRO responsable con datos reales", "Conversion", "Alta", "Media", "Membresias, copy legal"),
        ("GR-004", "Comparar FREE, PRO y ELITE por casos de uso", "Conversion", "Alta", "Baja", "Company Platform"),
        ("GR-005", "Cerrar Stripe test antes de cualquier cobro", "Revenue", "Critica", "Media", "Gate Stripe"),
        ("GR-006", "Certificar Telegram como valor premium controlado", "Retencion", "Alta", "Media", "Gate Telegram"),
        ("GR-007", "Publicar metodologia responsable de picks", "Confianza", "Alta", "Media", "Track Record"),
        ("GR-008", "Instrumentar retorno diario/semanal agregado", "Retencion", "Alta", "Media", "User Intelligence"),
        ("GR-009", "Crear calendario editorial beta sin publicar", "Marketing", "Media", "Baja", "Content approval"),
        ("GR-010", "Preparar SEO basico de landing, precios, FAQ y ayuda", "SEO", "Media", "Baja", "Company Platform"),
        ("GR-011", "Diseñar lifecycle welcome y first value", "CRM", "Alta", "Media", "Consentimiento"),
        ("GR-012", "Crear motivos de cancelacion sin friccion oscura", "Retencion", "Alta", "Media", "Customer Success"),
        ("GR-013", "Preparar feedback post-valor, no al primer segundo", "Aprendizaje", "Media", "Baja", "Beta Program"),
        ("GR-014", "Definir referral anti-abuso sin recompensa economica", "Referral", "Media", "Media", "Legal"),
        ("GR-015", "Separar partners de SHARK Analysis por contrato", "Compliance", "Alta", "Media", "Legal, Source Compliance"),
        ("GR-016", "Crear Campaign Lab sin gasto real", "Paid Ads", "Media", "Baja", "Founder approval"),
        ("GR-017", "Definir CAC objetivo como hipotesis, no realidad", "Analytics", "Media", "Baja", "Traffic data"),
        ("GR-018", "Crear dashboard de canales solo con datos reales", "Analytics", "Alta", "Media", "UTM consentido"),
        ("GR-019", "Vincular Product Memory con resultados de experimentos", "Learning", "Alta", "Media", "Continuous Evolution"),
        ("GR-020", "Preparar runbook de primeros 100 usuarios", "Go To Market", "Alta", "Baja", "Beta Program"),
    ]
    return [
        {
            "id": item[0],
            "title": item[1],
            "area": item[2],
            "user_impact": item[3],
            "business_impact": item[3],
            "effort": item[4],
            "dependencies": item[5],
            "status": "PENDING",
            "human_approval_required": True,
            "source": "Growth & Revenue OS + TOP100 alignment",
        }
        for item in items
    ]


def build_growth_revenue_os_snapshot(
    *,
    product_snapshot: Mapping[str, Any] | None = None,
    revenue_snapshot: Mapping[str, Any] | None = None,
    beta_snapshot: Mapping[str, Any] | None = None,
    support_snapshot: Mapping[str, Any] | None = None,
    top100_snapshot: Mapping[str, Any] | None = None,
    roadmap_snapshot: Mapping[str, Any] | None = None,
    app_version: str = "LOCAL",
    now_madrid: str | None = None,
) -> dict[str, Any]:
    """Build a founder-controlled commercial operating snapshot."""

    product = _mapping(product_snapshot)
    revenue = _mapping(revenue_snapshot)
    beta = _mapping(beta_snapshot)
    support = _mapping(support_snapshot)
    top100 = _mapping(top100_snapshot)
    roadmap = _mapping(roadmap_snapshot)
    now_iso = _now(now_madrid)
    funnel = _build_funnel(product, revenue)
    real_stage_count = len([stage for stage in funnel if stage["evidence_state"] != INSUFFICIENT_REAL_DATA])
    partial_controls = [
        bool(real_stage_count),
        bool(beta),
        bool(support),
        bool(top100.get("total")),
        bool(roadmap.get("modules") or roadmap.get("current_sprint")),
    ]
    score = round(((real_stage_count / len(funnel)) * 55) + (sum(partial_controls) / len(partial_controls) * 45))
    revenue_brief = _build_revenue_brief(product, revenue, funnel, now_iso)
    return {
        "contract": GROWTH_REVENUE_OS_CONTRACT,
        "version": app_version,
        "generated_at_madrid": now_iso,
        "mode": "founder_controlled_read_only",
        "status": "READY_FOR_BETA_MEASUREMENT" if real_stage_count >= 3 else "FOUNDATION_READY",
        "readiness_score": score,
        "score_explanation": f"{real_stage_count} de {len(funnel)} etapas del funnel tienen senal real parcial; el resto permanece sin datos reales.",
        "evidence_origin": "SYSTEM_OBSERVATION",
        "real_user_data_state": "PARTIAL" if real_stage_count >= 3 else "INSUFFICIENT_REAL_DATA",
        "roles": [
            {
                **role,
                "automation_allowed": ["OBSERVE", "ANALYZE", "PROPOSE", "PREPARE"],
                "approval_required": ["APPROVE_CONTENT", "SCHEDULE_CAMPAIGN", "PUBLISH", "SPEND", "CHANGE_PRICE", "CONNECT_CHANNEL"],
                "status": "ROLE_READY",
            }
            for role in GROWTH_ROLES
        ],
        "funnel": funnel,
        "metrics": {
            "registered_label": next((item["value_label"] for item in funnel if item["key"] == "registration"), "Sin datos reales"),
            "free_label": next((item["value_label"] for item in funnel if item["key"] == "free"), "Sin datos reales"),
            "premium_intent_label": next((item["value_label"] for item in funnel if item["key"] == "premium_intent"), "Sin datos reales"),
            "pro_elite_label": next((item["value_label"] for item in funnel if item["key"] == "pro_elite"), "Sin datos reales"),
            "conversion_label": _rate_label(product.get("conversion_registered_to_paid")),
            "mrr_label": revenue.get("mrr") if revenue.get("mrr") not in (None, "") else "No certificado",
            "churn_label": "Sin cohorte suficiente",
        },
        "founder_questions": {
            "what_is_working": "La infraestructura comercial, soporte, beta y medicion agregada existen; la venta real aun no esta certificada.",
            "what_is_not_working": "No hay atribucion de trafico, contenido ganador, MRR ni retencion real suficientes.",
            "where_we_lose_users": _main_friction(funnel),
            "where_we_gain_users": "Aun no hay canal ganador confirmado.",
            "best_channel": "INSUFFICIENT_REAL_DATA",
            "why_pro": "Solo se podra afirmar con eventos reales de premium intent y conversion.",
            "why_cancel": "INSUFFICIENT_REAL_DATA; se requiere motivo de cancelacion consentido.",
            "what_should_we_do_today": revenue_brief["daily_recommendation"],
        },
        "founder_revenue_brief": revenue_brief,
        "marketing_intelligence": {
            "status": "PREPARED_ONLY",
            "external_market_automation": "DISABLED_BY_DEFAULT",
            "source_compliance_required": True,
            "allowed_observation_types": ["FACT", "OBSERVATION", "INFERENCE", "IDEA"],
            "areas": ["tendencias deportivas", "busquedas", "competidores", "formatos", "SEO", "partners"],
            "limitations": ["No crawling masivo", "No copiar contenido", "No saltar paywalls", "No activar fuentes sin aprobacion"],
        },
        "content_factory": {
            "status": "APPROVAL_FIRST",
            "content_types": ["posts", "articulos SEO", "newsletter", "scripts de video", "posts sociales", "Telegram", "calendario editorial", "campanas"],
            "states": ["DRAFT", "READY_FOR_REVIEW", "APPROVED", "SCHEDULED", "PUBLISHED", "MEASURED"],
            "founder_only_can_approve": True,
            "automatic_publication": False,
        },
        "social_media": _channel_plan(),
        "seo": {
            "status": "FOUNDATION_READY",
            "checklist": ["titles", "descriptions", "canonical", "sitemap", "robots", "structured_data", "internal_linking", "performance", "evergreen_content"],
            "quality_guardrail": "No crear paginas masivas de baja calidad.",
        },
        "crm_lifecycle": [
            "WELCOME",
            "FIRST_VALUE",
            "ACTIVATION",
            "FAVORITE",
            "SHARK_DISCOVERY",
            "PREMIUM_EDUCATION",
            "INACTIVE",
            "RETURN",
            "RENEWAL",
            "CANCELLATION",
            "WINBACK",
        ],
        "conversion_strategy": {
            "free": "Valor basico real sin bloqueo artificial.",
            "pro": "Contexto, Telegram premium y seguimiento avanzado cuando exista evidencia.",
            "elite": "Experiencia intensiva con control y transparencia.",
            "upgrade_moments": ["primer valor", "favorito recurrente", "preview premium", "briefing diario", "Telegram opt-in"],
            "dark_patterns": False,
        },
        "customer_success": {
            "status": "PREPARED",
            "inputs": ["Beta Program", "Support Center", "Product Memory"],
            "tracks": ["onboarding", "FAQ", "incidencias", "cancelacion clara", "recuperacion", "satisfaccion", "churn reasons", "feature requests"],
        },
        "referrals": {
            "status": "DESIGNED_NOT_ACTIVE",
            "measures": ["invite", "accepted", "activated", "converted"],
            "anti_abuse_required": True,
            "real_rewards": False,
        },
        "affiliates_partners": {
            "status": "GOVERNANCE_READY_NOT_ACTIVE",
            "separation_rule": "SHARK_ANALYSIS != COMMERCIAL_RELATIONSHIP",
            "fields": ["partner", "jurisdiction", "compliance", "commercial_model", "attribution", "status"],
        },
        "paid_ads": {
            "status": "CAMPAIGN_LAB_ONLY",
            "spend_allowed": False,
            "founder_budget_approval_required": True,
            "fields": ["canal", "audiencia", "creatividad", "landing", "CTA", "presupuesto propuesto", "CAC objetivo", "hipotesis", "riesgo", "compliance"],
        },
        "experiments": {
            "status": "BACKLOG_READY",
            "schema": ["HYPOTHESIS", "METRIC", "BASELINE", "CHANGE", "EXPECTED_DIRECTION", "RESULT", "DECISION"],
            "success_requires_data": True,
        },
        "automation_levels": list(AUTOMATION_LEVELS),
        "responsible_marketing": {
            "required": ["+18 donde aplique", "juego responsable", "sin promesas de beneficio", "sin dinero facil", "sin urgencia enganosa", "sin targeting de menores"],
            "blocked": ["fake_metrics", "fake_testimonials", "fake_partners", "misleading_claims", "automatic_spend", "automatic_mass_publishing"],
        },
        "continuous_evolution_integration": [
            "PRODUCT_SIGNALS",
            "USER_SIGNALS",
            "GROWTH_SIGNALS",
            "REVENUE_SIGNALS",
            "MARKET_SIGNALS",
            "EXECUTIVE_BOARD",
            "FOUNDER_BRIEF",
            "TOP_PRIORITIES",
            "PREPARED_FOR_CODEX_OR_CAMPAIGN",
            "HUMAN_APPROVAL",
            "MEASURE",
            "PRODUCT_MEMORY",
        ],
        "simulation": {
            "allowed": True,
            "label": "SIMULATED_GROWTH_QA",
            "personas": ["new visitor", "FREE", "PRO candidate", "ELITE candidate", "inactive", "returning", "cancellation"],
            "never_mix_with_real_users": True,
        },
        "top20_revenue_actions": _top20_revenue_actions(),
        "plans": {
            "first_10_clients": ["Cerrar gates operativos", "Invitar beta manualmente", "Medir primer valor", "Hablar con cada usuario", "No gastar en ads"],
            "first_100_clients": ["Activar contenido aprobado", "SEO basico", "Lifecycle opt-in", "Referidos controlados", "Stripe certificado"],
            "first_1000_clients": ["Canales medidos", "Paid ads aprobados", "Customer Success operativo", "Retencion semanal", "Observabilidad de revenue"],
        },
        "guardrails": {
            "external_calls": 0,
            "campaigns_published": False,
            "mass_messages_sent": False,
            "telegram_sent": False,
            "stripe_called": False,
            "ad_spend": False,
            "price_changes": False,
            "affiliate_activation": False,
            "production_modified": False,
            "push_executed": False,
            "deploy_executed": False,
            "fake_metrics": False,
            "fake_testimonials": False,
            "fake_partners": False,
        },
        "next_action": revenue_brief["daily_recommendation"],
    }
