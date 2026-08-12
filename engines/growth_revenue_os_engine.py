"""Founder-controlled Growth & Revenue OS.

This module is a read-only commercial planning layer. It consumes existing
product, revenue, beta, roadmap and Founder evidence; it does not launch
campaigns, connect channels, call Stripe, send Telegram messages or mutate
customers.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Mapping
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


MADRID = ZoneInfo("Europe/Madrid")
GROWTH_REVENUE_OS_CONTRACT = "NEMESIS-GROWTH-REVENUE-OS-V1"
GROWTH_FUNNEL_EVENT_CONTRACT = "NEMESIS-GROWTH-FUNNEL-EVENT-V1"
INSUFFICIENT_REAL_DATA = "INSUFFICIENT_REAL_DATA"

ATTRIBUTION_CHANNELS: tuple[str, ...] = (
    "DIRECT",
    "ORGANIC_SEARCH",
    "INSTAGRAM",
    "TIKTOK",
    "YOUTUBE",
    "X",
    "FACEBOOK",
    "TELEGRAM",
    "REFERRAL",
    "PARTNER",
    "PAID",
    "OTHER",
)

FIRST_VALUE_DEFINITION = {
    "event": "FIRST_VALUE",
    "definition": "El usuario autenticado abre un Match Center canonico con un partido real resoluble.",
    "why": "Es la ruta mas corta que reune partido, contexto, evidencia, frescura y SHARK sin confundir registro con valor.",
    "evidence_required": ["authenticated_user", "canonical_match_id", "match_center_rendered"],
    "alternatives_not_selected": ["registro", "visita a landing", "apertura de precios", "click aislado"],
}

ACTIVATED_USER_DEFINITION = {
    "event": "ACTIVATED",
    "definition": "Usuario que alcanzo FIRST_VALUE y despues guardo un favorito o abrio un segundo partido canonico distinto.",
    "why": "Exige una segunda senal de utilidad y evita declarar activado a quien solo se registro o abrio una pagina.",
    "evidence_required": ["FIRST_VALUE", "favorite_saved_or_second_distinct_match"],
}


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


def _safe_token(value: Any, limit: int = 64) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    return token[:limit]


def normalize_growth_attribution(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a minimal attribution payload without URL, IP, user agent or PII."""

    raw = _mapping(values)
    source = _safe_token(raw.get("utm_source") or raw.get("source"), 40).lower()
    medium = _safe_token(raw.get("utm_medium") or raw.get("medium"), 40).lower()
    campaign_id = _safe_token(raw.get("utm_campaign") or raw.get("campaign_id"), 64)
    referral_code = _safe_token(raw.get("ref") or raw.get("referral_code"), 48)
    source_map = {
        "instagram": "INSTAGRAM",
        "ig": "INSTAGRAM",
        "tiktok": "TIKTOK",
        "youtube": "YOUTUBE",
        "yt": "YOUTUBE",
        "x": "X",
        "twitter": "X",
        "facebook": "FACEBOOK",
        "fb": "FACEBOOK",
        "telegram": "TELEGRAM",
        "google": "ORGANIC_SEARCH" if medium not in {"cpc", "paid", "ppc"} else "PAID",
        "bing": "ORGANIC_SEARCH" if medium not in {"cpc", "paid", "ppc"} else "PAID",
        "partner": "PARTNER",
        "referral": "REFERRAL",
    }
    if referral_code:
        channel = "REFERRAL"
    elif medium in {"cpc", "paid", "ppc", "display"}:
        channel = "PAID"
    elif source:
        channel = source_map.get(source, "OTHER")
    else:
        channel = "DIRECT"
    return {
        "channel": channel if channel in ATTRIBUTION_CHANNELS else "OTHER",
        "campaign_id": campaign_id,
        "referral_present": bool(referral_code),
        "source_present": bool(source),
        "medium_present": bool(medium),
        "privacy": {
            "full_url_stored": False,
            "ip_stored": False,
            "user_agent_stored": False,
            "fingerprint_used": False,
            "pii_stored": False,
        },
    }


def build_growth_funnel_event(
    stage: str,
    *,
    target_id: Any = "",
    attribution: Mapping[str, Any] | None = None,
    authenticated: bool = False,
    analytics_consent: bool = False,
    evidence_origin: str = "SYSTEM_OBSERVATION",
    occurred_at_madrid: str | None = None,
) -> dict[str, Any]:
    """Build a versioned event contract; anonymous persistence remains consent-gated."""

    allowed = {item["label"] for item in FUNNEL_DEFINITIONS}
    normalized_stage = str(stage or "").strip().upper()
    if normalized_stage not in allowed:
        raise ValueError("growth_stage_not_allowed")
    safe_attribution = normalize_growth_attribution(attribution)
    safe_origin = str(evidence_origin or "UNKNOWN").strip().upper()
    if safe_origin not in {"SIMULATED_QA", "REAL_USER", "SYSTEM_OBSERVATION", "MANUAL_ADMIN", "UNKNOWN"}:
        safe_origin = "UNKNOWN"
    return {
        "contract": GROWTH_FUNNEL_EVENT_CONTRACT,
        "stage": normalized_stage,
        "occurred_at_madrid": _now(occurred_at_madrid),
        "target_id": _safe_token(target_id, 120),
        "origin": "FIRST_PARTY_PRODUCT",
        "evidence_origin": safe_origin,
        "channel": safe_attribution["channel"],
        "campaign_id": safe_attribution["campaign_id"],
        "authenticated": bool(authenticated),
        "analytics_consent": bool(analytics_consent),
        "persistence_allowed": bool(authenticated or analytics_consent),
        "anonymous_session_only": bool(not authenticated and not analytics_consent),
        "privacy": safe_attribution["privacy"],
    }


def _conversion_metric(numerator: Any, denominator: Any) -> dict[str, Any]:
    num = _int(numerator)
    den = _int(denominator)
    if den <= 0:
        return {"numerator": num, "denominator": den, "value": 0.0, "label": "0 / INSUFFICIENT_REAL_DATA", "state": INSUFFICIENT_REAL_DATA}
    value = round((num / den) * 100, 1)
    return {"numerator": num, "denominator": den, "value": value, "label": f"{value:.1f}%", "state": "PARTIALLY_VERIFIED"}


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
    {"key": "discovery", "label": "DISCOVERY", "definition": "Una persona descubre NeMeSiS por un canal medible y permitido.", "owner": "Marketing Director"},
    {"key": "landing", "label": "LANDING", "definition": "Visita una superficie publica; sin consentimiento la visita permanece solo en la sesion.", "owner": "Content & SEO Lead"},
    {"key": "registration", "label": "REGISTRATION", "definition": "Crea una cuenta sin datos innecesarios y conserva atribucion minimizada.", "owner": "Head of Growth"},
    {"key": "free", "label": "FREE", "definition": "Usa el plan gratuito y puede alcanzar valor real antes de pagar.", "owner": "CRO / Conversion Lead"},
    {"key": "first_value", "label": "FIRST_VALUE", "definition": FIRST_VALUE_DEFINITION["definition"], "owner": "Head of Growth"},
    {"key": "activated", "label": "ACTIVATED", "definition": ACTIVATED_USER_DEFINITION["definition"], "owner": "CRM / Lifecycle Lead"},
    {"key": "returning", "label": "RETURNING", "definition": "Vuelve en otro dia con una senal first-party agregable.", "owner": "CRM / Lifecycle Lead"},
    {"key": "premium_intent", "label": "PREMIUM_INTENT", "definition": "Consulta conscientemente planes o una superficie de valor premium.", "owner": "Revenue & Membership Lead"},
    {"key": "pro", "label": "PRO", "definition": "Tiene plan PRO confirmado por la fuente de membresias.", "owner": "Revenue & Membership Lead"},
    {"key": "elite", "label": "ELITE", "definition": "Tiene plan ELITE o ELITE+ confirmado por la fuente de membresias.", "owner": "Revenue & Membership Lead"},
    {"key": "retained", "label": "RETAINED", "definition": "Permanece activo dentro de una ventana de retencion definida y suficiente.", "owner": "Customer Success Lead"},
    {"key": "referral", "label": "REFERRAL", "definition": "Una invitacion progresa hasta registro y activacion, sin recompensa monetaria.", "owner": "Partnerships / Affiliates Lead"},
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
    measured = _mapping(product.get("growth_funnel"))
    measured_stages = _mapping(measured.get("stages"))
    users = _mapping(product.get("users"))
    commerce = _mapping(product.get("commerce"))
    memberships = _mapping(revenue.get("memberships")) or _mapping(users.get("memberships"))
    stage_values = {
        "discovery": measured_stages.get("DISCOVERY"),
        "landing": measured_stages.get("LANDING"),
        "registration": raw_funnel.get("registered") or users.get("registered_users") or measured_stages.get("REGISTRATION"),
        "free": memberships.get("FREE"),
        "first_value": measured_stages.get("FIRST_VALUE"),
        "activated": measured_stages.get("ACTIVATED") or raw_funnel.get("active"),
        "returning": measured_stages.get("RETURNING"),
        "premium_intent": measured_stages.get("PREMIUM_INTENT") or raw_funnel.get("pro_interest") or raw_funnel.get("checkout_started") or commerce.get("checkout_started"),
        "pro": memberships.get("PRO"),
        "elite": _int(memberships.get("ELITE")) + _int(memberships.get("ELITE+")),
        "retained": measured_stages.get("RETAINED"),
        "referral": measured_stages.get("REFERRAL"),
    }
    evidence_sources = {
        "discovery": "Atribucion minimizada de cuentas registradas; no equivale a visitantes anonimos.",
        "landing": "Sesion publica temporal vinculada al registro; no hay analitica anonima persistente.",
        "registration": "Tabla de usuarios agregada y evento REGISTRATION cuando esta instrumentado.",
        "free": "Planes agregados, sin PII.",
        "first_value": "Match Center canonico real abierto por un usuario autenticado.",
        "activated": "FIRST_VALUE seguido de favorito o segundo partido canonico distinto.",
        "returning": "Retorno autenticado en un dia posterior, deduplicado.",
        "premium_intent": "Vista autenticada de membresias o valor premium.",
        "pro": "Plan PRO agregado; no implica MRR certificado.",
        "elite": "Plan ELITE/ELITE+ agregado; no implica MRR certificado.",
        "retained": "Requiere ventana de retencion y cohorte suficiente.",
        "referral": "Referral MVP disenado, todavia no activo.",
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
        "discovery": "Mantener UTM seguro y contar solo atribucion registrada.",
        "landing": "Solicitar consentimiento antes de analitica anonima persistente.",
        "registration": "Mantener conteo agregado de altas.",
        "free": "Relacionar plan FREE con actividad agregada.",
        "first_value": "Registrar Match Center canonico tras render valido.",
        "activated": "Exigir favorito o segundo partido distinto tras FIRST_VALUE.",
        "returning": "Medir retorno en otro dia por cohorte agregada.",
        "premium_intent": "Registrar vistas autenticadas de planes y previews.",
        "pro": "Certificar plan y pago test antes de ingreso real.",
        "elite": "Certificar plan y pago test antes de ingreso real.",
        "retained": "Definir ventana cuando exista historial real suficiente.",
        "referral": "Aprobar MVP anti-abuso antes de activar enlaces.",
    }
    return mapping.get(stage, "Definir medicion segura.")


def _build_funnel_metrics(funnel: list[dict[str, Any]]) -> dict[str, Any]:
    values = {item["key"]: _int(item.get("value")) for item in funnel}
    paid = values.get("pro", 0) + values.get("elite", 0)
    return {
        "visitor_to_registration": {"numerator": values.get("registration", 0), "denominator": 0, "value": 0.0, "label": "0 / INSUFFICIENT_REAL_DATA", "state": INSUFFICIENT_REAL_DATA, "limitation": "No se persisten visitantes anonimos sin consentimiento."},
        "registration_to_first_value": _conversion_metric(values.get("first_value"), values.get("registration")),
        "first_value_to_activation": _conversion_metric(values.get("activated"), values.get("first_value")),
        "activation_to_returning": _conversion_metric(values.get("returning"), values.get("activated")),
        "free_to_premium_intent": _conversion_metric(values.get("premium_intent"), values.get("free")),
        "premium_intent_to_paid": _conversion_metric(paid, values.get("premium_intent")),
    }


def _build_revenue_brief(product: dict[str, Any], revenue: dict[str, Any], funnel: list[dict[str, Any]], now_iso: str) -> dict[str, Any]:
    memberships = _mapping(revenue.get("memberships")) or _mapping(_mapping(product.get("users")).get("memberships"))
    commerce = _mapping(revenue.get("payment_event_counts")) or _mapping(product.get("commerce"))
    measured = _mapping(product.get("growth_funnel"))
    channels = _list(measured.get("channels"))
    channel_label = ", ".join(f"{item.get('channel')}: {_int(item.get('registered'))}" for item in channels[:3]) or "Sin atribucion real"
    registered = next((item for item in funnel if item["key"] == "registration"), {})
    premium = next((item for item in funnel if item["key"] == "premium_intent"), {})
    pro_stage = next((item for item in funnel if item["key"] == "pro"), {})
    elite_stage = next((item for item in funnel if item["key"] == "elite"), {})
    paid_evidence = {"evidence_state": "PARTIALLY_VERIFIED" if any(item.get("evidence_state") != INSUFFICIENT_REAL_DATA for item in (pro_stage, elite_stage)) else INSUFFICIENT_REAL_DATA}
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
        "visits": next((item.get("value_label") for item in funnel if item["key"] == "landing"), "Sin datos reales"),
        "registrations": registered.get("value_label", "Sin datos reales"),
        "activations": next((item.get("value_label") for item in funnel if item["key"] == "activated"), "Sin datos reales"),
        "returning_users": next((item.get("value_label") for item in funnel if item["key"] == "returning"), "Sin datos reales"),
        "premium_intent": premium.get("value_label", "Sin datos reales"),
        "pro": _int(memberships.get("PRO")),
        "elite": _int(memberships.get("ELITE")) + _int(memberships.get("ELITE+")),
        "mrr": revenue.get("mrr") if revenue.get("mrr") not in (None, "") else "No certificado",
        "churn": "Sin cohorte suficiente",
        "conversions": _rate_label(product.get("conversion_registered_to_paid")),
        "main_channels": channel_label,
        "winning_content": "Sin contenido medido",
        "main_friction": _main_friction(funnel),
        "main_opportunity": _main_opportunity(funnel, paid_evidence),
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


def _main_opportunity(funnel: list[dict[str, Any]], paid_evidence: dict[str, Any]) -> str:
    if paid_evidence.get("evidence_state") == INSUFFICIENT_REAL_DATA:
        return "Explicar valor PRO/ELITE con previews responsables antes de cobrar."
    registration = next((stage for stage in funnel if stage["key"] == "registration"), {})
    if registration.get("evidence_state") != INSUFFICIENT_REAL_DATA:
        return "Convertir registrados en primer valor medible y retorno semanal."
    return "Preparar beta cerrada con medicion honesta del primer uso."



def build_first100_attribution_links(base_url: str = "") -> list[dict[str, Any]]:
    """Build copy-ready FIRST100 links without identifiers or personal data."""

    root = str(base_url or "").strip().rstrip("/")
    rows = (
        ("DIRECT", "Directo", "", "", "Acceso compartido sin atribucion de canal."),
        ("INSTAGRAM", "Instagram", "instagram", "social", "Bio y publicaciones propias."),
        ("TIKTOK", "TikTok", "tiktok", "social", "Perfil y publicaciones propias."),
        ("YOUTUBE", "YouTube", "youtube", "video", "Canal y descripciones propias."),
        ("X", "X", "x", "social", "Perfil y publicaciones propias."),
        ("FACEBOOK", "Facebook", "facebook", "social", "Pagina propia y comunidades que permiten promocion."),
        ("TELEGRAM", "Telegram", "telegram", "owned", "Solo espacios propios u opt-in; no se envia automaticamente."),
        ("REFERRAL", "Invitacion directa", "referral", "manual", "Contacto individual y consentido."),
        ("ORGANIC_SEARCH", "Busqueda organica", "google", "organic", "Enlace de verificacion; la busqueda natural puede llegar sin UTM."),
    )
    result: list[dict[str, Any]] = []
    for channel, label, source, medium, use in rows:
        params: dict[str, str] = {}
        if source:
            params = {"utm_source": source, "utm_medium": medium, "utm_campaign": "FIRST100_ORGANIC"}
        if channel == "REFERRAL":
            params["ref"] = "first100-founder"
        path = "/landing" + ("?" + urlencode(params) if params else "")
        result.append(
            {
                "channel": channel,
                "label": label,
                "path": path,
                "url": f"{root}{path}" if root else path,
                "campaign_id": "FIRST100_ORGANIC" if params else "DIRECT_NO_UTM",
                "contains_pii": False,
                "use": use,
                "state": "READY_TO_COPY" if root else "RELATIVE_LINK_READY",
            }
        )
    return result


def _link_for_channel(links: list[dict[str, Any]], channel: str) -> str:
    return next((str(item.get("url") or item.get("path") or "") for item in links if item.get("channel") == channel), "/landing")


def build_first_10_launch_kit(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    common_feedback = "Tras abrir tu primer partido: que entendiste, que falto y si volverias manana."
    return [
        {
            "path_id": "DIRECT_CONTACT",
            "label": "Contacto directo",
            "message": "Estoy abriendo la beta de NeMeSiS para un grupo pequeno. Organiza partidos, equipos y contexto SHARK con evidencia y limites visibles. Puedes probarla gratis y decirme si entiendes el valor al abrir tu primer partido.",
            "cta": "Abrir NeMeSiS",
            "link": _link_for_channel(links, "REFERRAL"),
            "onboarding": "Registro -> calendario -> partido real -> feedback breve.",
            "feedback": common_feedback,
            "follow_up": "Un unico seguimiento 24-48 horas despues, solo si acepto probarla.",
            "metric": "REGISTRATION -> FIRST_VALUE -> ACTIVATED",
            "status": "READY_NOT_SENT",
        },
        {
            "path_id": "OWNED_SOCIAL",
            "label": "Redes propias",
            "message": "NeMeSiS ya esta preparada para sus primeros usuarios: menos ruido, mas contexto y ninguna afirmacion sin evidencia. Empieza gratis y abre un partido real.",
            "cta": "Empezar gratis",
            "link": _link_for_channel(links, "INSTAGRAM"),
            "onboarding": "Landing -> registro -> partido real -> favorito o segundo partido.",
            "feedback": common_feedback,
            "follow_up": "Responder preguntas publicas; no perseguir a quien no interactua.",
            "metric": "Canal -> REGISTRATION -> FIRST_VALUE -> ACTIVATED",
            "status": "READY_NOT_PUBLISHED",
        },
        {
            "path_id": "PERMITTED_COMMUNITIES",
            "label": "Comunidades con promocion permitida",
            "message": "Con permiso de moderacion: estoy validando NeMeSiS, una plataforma para entender partidos con datos reales, contexto y limites visibles. Busco feedback honesto de personas adultas; el acceso inicial es gratuito.",
            "cta": "Probar y dar feedback",
            "link": _link_for_channel(links, "REFERRAL"),
            "onboarding": "Leer reglas -> publicar una vez -> responder dudas -> retirar si lo solicita moderacion.",
            "feedback": common_feedback,
            "follow_up": "Compartir resultados agregados solo si existen y sin identificar usuarios.",
            "metric": "Publicacion permitida -> registros atribuidos -> FIRST_VALUE",
            "status": "REQUIRES_COMMUNITY_PERMISSION",
        },
    ]


def build_first_7_day_organic_schedule(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = (
        (1, "POST-10", "INSTAGRAM", "Buscamos 10 personas que prefieran claridad al ruido.", "Abrimos una beta manual para aprender donde NeMeSiS aporta valor. Sin promesas ni resultados inventados.", "Empezar gratis", "REGISTRATION"),
        (2, "REEL-01", "TIKTOK", "De buscar un partido a entenderlo en 15 segundos.", "Recorrido con interfaz propia: calendario, Match Center, evidencia y limitaciones.", "Abrir tu primer partido", "FIRST_VALUE"),
        (3, "SHORT-01", "YOUTUBE", "Tu primer partido, sin perderte.", "Guion breve con calendario, marcador, cronologia, evidencia y limites; sin clips de terceros.", "Empezar gratis", "FIRST_VALUE"),
        (4, "X-03", "X", "Nuestro objetivo no es que te registres.", "Es que entiendas tu primer partido. FIRST_VALUE mide utilidad, no vanidad.", "Probar NeMeSiS", "FIRST_VALUE"),
        (5, "POST-05", "FACEBOOK", "Tu equipo, sin perderte entre veinte pantallas.", "Team Center reune forma, partidos y contexto solo cuando existen datos reales.", "Buscar equipo", "ACTIVATED"),
        (6, "TG-01", "TELEGRAM", "Bienvenido a la beta de NeMeSiS.", "Calendario, primer partido y feedback breve. Contenido preparado, no enviado automaticamente.", "Abrir primer partido", "FIRST_VALUE"),
        (7, "POST-02", "INSTAGRAM", "SHARK no adivina.", "Explica que sabemos, que evidencia existe y que informacion falta.", "Ver SHARK", "TRUST"),
    )
    items = []
    for day, content_id, channel, hook, content, cta, objective in rows:
        items.append(
            {
                "day": day,
                "content_id": content_id,
                "channel": channel,
                "hook": hook,
                "content": content,
                "cta": cta,
                "link": _link_for_channel(links, channel),
                "objective": objective,
                "why": "Seleccionado del paquete FIRST_10_USERS por claridad, valor visible y bajo riesgo de compliance.",
                "compliance": ["sin promesas", "sin testimonios", "sin contenido protegido", "+18 cuando aplique"],
                "status": "READY_FOR_REVIEW",
                "publication_state": "NOT_PUBLISHED",
            }
        )
    return items


def build_social_launch_kit(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first_posts = {item["channel"]: item for item in build_first_7_day_organic_schedule(links)}
    rows = (
        ("INSTAGRAM", "Instagram", "Deporte con contexto, evidencia y limites visibles. Empieza gratis.", "Captura propia del Match Center en formato vertical.", "3 piezas por semana como maximo al inicio."),
        ("TIKTOK", "TikTok", "Entiende un partido sin ruido. Datos reales y SHARK explicable.", "Video vertical de la interfaz propia, sin clips deportivos protegidos.", "2 piezas por semana al inicio."),
        ("YOUTUBE", "YouTube", "Partidos, equipos y SHARK con evidencia visible.", "Cabecera de marca y captura propia en formato horizontal/Short.", "1 Short por semana al inicio."),
        ("X", "X", "Menos ruido. Mas contexto deportivo verificable.", "Avatar de marca y captura propia opcional.", "3 publicaciones por semana al inicio."),
        ("FACEBOOK", "Facebook", "Sigue el deporte con datos reales, contexto y soporte claro.", "Portada de marca y captura propia legible.", "2 publicaciones por semana al inicio."),
        ("TELEGRAM", "Telegram", "Briefings deportivos con evidencia y limites.", "Avatar de marca ya autorizado; no descargar activos externos.", "Solo opt-in y aprobacion; sin envios automaticos."),
    )
    result = []
    for channel, name, bio, image, frequency in rows:
        first = first_posts.get(channel) or {}
        result.append(
            {
                "channel": channel,
                "name": "NeMeSiS SHARK PRO",
                "label": name,
                "bio": bio,
                "image_needed": image,
                "link": _link_for_channel(links, channel),
                "first_publication": first.get("content") or "Usar la primera pieza aprobada del calendario.",
                "second_publication": "Usar la siguiente pieza aprobada del mismo canal; no rellenar por frecuencia.",
                "frequency": frequency,
                "measure": "Registros atribuidos, FIRST_VALUE y ACTIVATED; nunca solo impresiones.",
                "status": "READY_NOT_CONNECTED",
            }
        )
    return result


def build_growth_seo_launch_plan() -> dict[str, Any]:
    return {
        "checks": ["robots", "sitemap", "canonical", "titles", "descriptions", "open_graph", "structured_data", "indexability", "internal_linking"],
        "search_console_steps": [
            "Verificar que el dominio de produccion es el definitivo.",
            "Crear la propiedad de dominio en Google Search Console.",
            "Completar la verificacion DNS con el proveedor autorizado.",
            "Enviar /sitemap.xml.",
            "Inspeccionar /landing, /calendar, /shark y /precios.",
            "Esperar datos reales antes de evaluar consultas o posiciones.",
        ],
        "account_connection": "NOT_CONNECTED_REQUIRES_FOUNDER",
        "production_indexability": "BLOCKED_UNTIL_DEPLOY_AND_OBSERVATION",
    }


def build_first_paid_customer_path() -> dict[str, Any]:
    return {
        "path": ["FREE", "PREMIUM_INTENT", "PRICING", "PRO_OR_ELITE", "STRIPE"],
        "state": "BLOCKED_UNTIL_CERTIFIED",
        "charging_allowed": False,
        "missing": [
            "Stripe en modo seguro con claves y Price IDs certificados.",
            "Webhook firmado y persistencia del resultado certificados.",
            "Checkout, retorno, cancelacion y recuperacion probados de extremo a extremo.",
            "Terminos de renovacion y soporte revisados.",
            "Una compra de prueba controlada con evidencia sanitizada.",
        ],
    }


def apply_content_review_state(items: list[dict[str, Any]], reviews: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    mapped = _mapping(reviews)
    result = []
    for item in items:
        review = _mapping(mapped.get(str(item.get("content_id") or "")))
        result.append(
            {
                **item,
                "status": review.get("state") or item.get("status"),
                "reviewed_at_madrid": review.get("reviewed_at_madrid") or "",
                "hook": review.get("edited_hook") or item.get("hook"),
                "content": review.get("edited_content") or item.get("content"),
                "publication_state": "NOT_PUBLISHED",
            }
        )
    return result


def growth_launch_content_ids() -> set[str]:
    links = build_first100_attribution_links()
    return {str(item["content_id"]) for item in build_first_7_day_organic_schedule(links)}
def _channel_plan() -> list[dict[str, Any]]:
    shared = {"link": "/landing?utm_campaign=FIRST_10_USERS", "status": "READY_FOR_REVIEW_NOT_CONNECTED", "automatic_publication": False}
    return [
        {**shared, "channel": "Instagram", "brand_name": "NeMeSiS SHARK PRO", "bio": "Deporte con contexto, evidencia y limites visibles. +18. No somos casa de apuestas.", "content": "Reels educativos y carruseles", "frequency": "3 piezas/semana propuestas", "metric": "Registros atribuidos y activados", "cta": "Empezar gratis", "restrictions": ["sin claims de beneficio", "sin fake social proof"]},
        {**shared, "channel": "TikTok", "brand_name": "NeMeSiS SHARK PRO", "bio": "Entiende un partido en segundos. Datos reales, SHARK y juego responsable.", "content": "Videos educativos breves", "frequency": "3 piezas/semana propuestas", "metric": "Retencion y registros activados", "cta": "Abrir el partido", "restrictions": ["+18 si aplica", "sin targeting de menores"]},
        {**shared, "channel": "YouTube", "brand_name": "NeMeSiS SHARK PRO", "bio": "Contexto deportivo explicable: partidos, equipos, competiciones y SHARK.", "content": "Shorts y guias", "frequency": "2 Shorts/semana propuestos", "metric": "Tiempo visto y FIRST_VALUE", "cta": "Probar NeMeSiS", "restrictions": ["fuentes permitidas", "sin copiar highlights"]},
        {**shared, "channel": "X", "brand_name": "NeMeSiS SHARK PRO", "bio": "Menos ruido. Mas contexto deportivo verificable. +18.", "content": "Posts cortos e hilos", "frequency": "4 posts/semana propuestos", "metric": "Registros atribuidos y FIRST_VALUE", "cta": "Empezar gratis", "restrictions": ["sin certezas inventadas", "sin urgencia falsa"]},
        {**shared, "channel": "Facebook", "brand_name": "NeMeSiS SHARK PRO", "bio": "Sigue el deporte con datos reales, contexto y soporte claro.", "content": "Posts, guias y comunidad", "frequency": "2 piezas/semana propuestas", "metric": "Preguntas utiles y activados", "cta": "Conocer la plataforma", "restrictions": ["moderacion manual", "sin grupos no autorizados"]},
        {**shared, "channel": "Telegram", "brand_name": "NeMeSiS SHARK PRO", "bio": "Briefings deportivos controlados, deduplicados y con evidencia.", "content": "3 contenidos preparados; sin envio", "frequency": "Solo tras opt-in y aprobacion", "metric": "Opt-in, activacion y bajas", "cta": "Activar cuando este certificado", "restrictions": ["no spam", "no picks en esta campana", "deduplicacion intacta"]},
    ]


def _first_10_campaign() -> dict[str, Any]:
    return {
        "campaign_id": "FIRST_10_USERS",
        "status": "READY_FOR_REVIEW",
        "objective": "Conseguir 10 registros reales y aprender cuantos alcanzan FIRST_VALUE y ACTIVATED.",
        "paid_ads": False,
        "audience": "Adultos apropiados del circulo propio o comunidades donde la promocion este permitida.",
        "message": "Estoy preparando la beta cerrada de NeMeSiS: una forma mas clara de seguir partidos con contexto, evidencia y limites visibles. Puedes empezar gratis y contarme si entiendes el valor en tu primer partido.",
        "landing": "/landing?utm_source=referral&utm_medium=manual&utm_campaign=FIRST_10_USERS",
        "cta": "EMPEZAR GRATIS",
        "onboarding": ["registro", "calendario", "Match Center", "FIRST_VALUE", "feedback posterior al valor"],
        "support": ["FAQ", "Centro de ayuda", "contacto", "bug reporter", "recuperacion de cuenta"],
        "success_measure": {"primary": "ACTIVATED", "target_direction": "10 registros; maximizar activados sin fijar una tasa sin baseline", "guardrails": ["0 spam", "0 claims de beneficio", "0 menores", "0 gasto"]},
        "automatic_send": False,
        "founder_approval_required": True,
    }


def _content_package() -> dict[str, Any]:
    groups = [
        ("SHORT_POST", 10, "Post corto", "Explicar una capacidad real en menos de diez segundos", "Empezar gratis"),
        ("REEL_IDEA", 5, "Idea Reel/TikTok", "Mostrar un recorrido de producto sin material protegido", "Ver el partido"),
        ("SHORT_SCRIPT", 3, "Guion Short", "Ensenar evidencia, frescura y limitaciones", "Probar NeMeSiS"),
        ("X_POST", 5, "Post X", "Posicionar claridad y criterio frente al ruido", "Abrir la beta"),
        ("TELEGRAM_CONTENT", 3, "Contenido Telegram", "Preparar briefing opt-in sin enviar", "Revisar en NeMeSiS"),
        ("SEO_EVERGREEN", 3, "Idea SEO evergreen", "Resolver una duda deportiva o de producto de forma durable", "Conocer la metodologia"),
    ]
    items: list[dict[str, Any]] = []
    for kind, count, label, value, cta in groups:
        for index in range(1, count + 1):
            items.append({"id": f"CONTENT-{kind}-{index:02d}", "type": kind, "title": f"{label} {index}", "objective": "FIRST_10_USERS", "audience": "Adultos interesados en contexto deportivo", "hook": "Entender antes de decidir.", "value": value, "cta": cta, "channel": label, "evidence": "Capacidades existentes de NeMeSiS", "compliance": ["+18 cuando aplique", "sin promesas", "sin contenido protegido"], "status": "READY_FOR_REVIEW"})
    for index in range(1, 4):
        items.append({"id": f"CONTENT-CURRENT-SPORTS-{index:02d}", "type": "CURRENT_SPORTS", "title": f"Actualidad deportiva {index}", "objective": "Contenido actual solo con fuente aprobada", "audience": "Adultos interesados en deporte", "hook": "PENDIENTE_DE_FUENTE", "value": "No redactado: no existe evidencia permitida adjunta a este ciclo.", "cta": "Ninguno hasta aprobar fuente", "channel": "Por decidir", "evidence": INSUFFICIENT_REAL_DATA, "compliance": ["Source Compliance obligatorio", "no copiar articulos", "no imagenes protegidas"], "status": "BLOCKED_BY_SOURCE"})
    return {
        "status": "READY_FOR_REVIEW",
        "items": items,
        "ready_count": len([item for item in items if item["status"] == "READY_FOR_REVIEW"]),
        "blocked_by_source_count": len([item for item in items if item["status"] == "BLOCKED_BY_SOURCE"]),
        "automatic_publication": False,
        "review_document": "reports/FIRST_10_USERS_CAMPAIGN_PACK.md",
    }


def _experiment_board() -> list[dict[str, Any]]:
    rows = [
        ("EXP-001", "CTA Empezar gratis", "LANDING", "La CTA literal reduce ambiguedad", "registration_to_first_value"),
        ("EXP-002", "Primer partido guiado", "ONBOARDING", "Abrir un partido real acelera FIRST_VALUE", "registration_to_first_value"),
        ("EXP-003", "Feedback despues del valor", "BETA", "Pedir feedback tras FIRST_VALUE mejora calidad", "feedback_completion"),
        ("EXP-004", "Comparativa por caso de uso", "PRICING", "Casos de uso aclaran FREE/PRO/ELITE", "free_to_premium_intent"),
        ("EXP-005", "SHARK explicable en landing", "LANDING", "Evidencia y limites aumentan confianza", "visitor_to_registration"),
        ("EXP-006", "Favorito como segundo paso", "ACTIVATION", "Guardar un favorito mejora ACTIVATED", "first_value_to_activation"),
        ("EXP-007", "Briefing de retorno", "RETENTION", "El briefing ayuda a volver otro dia", "activation_to_returning"),
        ("EXP-008", "Contenido metodologia", "ORGANIC", "Metodologia atrae usuarios mas cualificados", "registration_to_first_value"),
        ("EXP-009", "Invitacion personal beta", "REFERRAL", "Una invitacion contextual supera el mensaje generico", "registration_to_first_value"),
        ("EXP-010", "Ayuda visible en registro", "SUPPORT", "Soporte visible reduce abandono", "registration_completion"),
    ]
    return [{"id": row[0], "experiment": row[1], "hypothesis": row[3], "channel": row[2], "audience": "FIRST_10_USERS", "metric": row[4], "baseline": INSUFFICIENT_REAL_DATA, "target_direction": "IMPROVE", "status": "READY", "result": "NOT_RUN", "decision": "FOUNDER_APPROVAL_REQUIRED"} for row in rows]


def _first_100_progress(funnel: list[dict[str, Any]], real_stages: Mapping[str, Any] | None = None) -> dict[str, Any]:
    values = {item["key"]: _int(item.get("value")) for item in funnel}
    real = _mapping(real_stages)
    current = {
        "REGISTERED": _int(real.get("REGISTRATION")) if real_stages is not None else values.get("registration", 0),
        "ACTIVATED": _int(real.get("ACTIVATED")) if real_stages is not None else values.get("activated", 0),
        "RETURNING": _int(real.get("RETURNING")) if real_stages is not None else values.get("returning", 0),
        "PAID": _int(real.get("PRO")) + _int(real.get("ELITE")) if real_stages is not None else values.get("pro", 0) + values.get("elite", 0),
    }
    return {
        "current": current,
        "milestones": [{"target": target, "registered": f"{current['REGISTERED']} / {target}", "activated": f"{current['ACTIVATED']} / {target}", "returning": f"{current['RETURNING']} / {target}", "paid": f"{current['PAID']} / {target}"} for target in (10, 25, 50, 100)],
        "success_rule": "Nunca celebrar registros sin mostrar ACTIVATED, RETURNING y PAID por separado.",
    }


def _paid_ads_lab() -> list[dict[str, Any]]:
    return [
        {"campaign_id": "META_FIRST100_TEST", "channel": "Meta", "status": "READY_NOT_ACTIVE", "objective": "Registro cualificado", "audience_legal": "+18, sin segmentacion vulnerable", "landing": "/landing", "creative": "Pendiente de aprobacion", "proposed_budget": "NO_APPROVED", "duration": "Por decidir", "kpi": "ACTIVATED, no solo click", "stop_condition": "Cualquier problema legal, de privacidad o calidad", "compliance": "REVIEW_REQUIRED", "spend": 0},
        {"campaign_id": "GOOGLE_FIRST100_TEST", "channel": "Google Search", "status": "READY_NOT_ACTIVE", "objective": "Demanda intencional", "audience_legal": "+18 cuando aplique", "landing": "/landing", "creative": "Pendiente de aprobacion", "proposed_budget": "NO_APPROVED", "duration": "Por decidir", "kpi": "ACTIVATED, no solo registro", "stop_condition": "Terminos sensibles, claims o trafico no cualificado", "compliance": "REVIEW_REQUIRED", "spend": 0},
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
    content_review_snapshot: Mapping[str, Any] | None = None,
    public_base_url: str = "",
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
    funnel_metrics = _build_funnel_metrics(funnel)
    instrumentation = _mapping(product.get("growth_instrumentation"))
    measured = _mapping(product.get("growth_funnel"))
    seo_snapshot = _mapping(product.get("growth_seo"))
    content_reviews = _mapping(content_review_snapshot)
    review_items = _mapping(content_reviews.get("items"))
    attribution_links = build_first100_attribution_links(public_base_url)
    first_10_campaign = _first_10_campaign()
    first_10_campaign["landing"] = _link_for_channel(attribution_links, "REFERRAL")
    content_package = _content_package()
    weekly_content = apply_content_review_state(build_first_7_day_organic_schedule(attribution_links), review_items)
    approved_content = len([item for item in weekly_content if item.get("status") == "APPROVED"])
    experiments = _experiment_board()
    acquisition_controls = {
        "event_contract": instrumentation.get("event_contract") == GROWTH_FUNNEL_EVENT_CONTRACT,
        "first_value_defined": True,
        "activated_defined": True,
        "safe_attribution": bool(instrumentation.get("safe_attribution")),
        "anonymous_persistence_consent_gated": bool(instrumentation.get("anonymous_persistence_consent_gated")),
        "landing_cro": bool(instrumentation.get("landing_cro")),
        "seo_foundation": seo_snapshot.get("status") in {"PASS", "PARTIAL"},
        "first_10_campaign_ready": first_10_campaign.get("status") == "READY_FOR_REVIEW",
        "content_ready_for_review": content_package.get("ready_count") == 29,
        "experiment_board_ready": len(experiments) == 10,
        "no_spend": True,
        "no_publication": True,
    }
    launch_controls = {
        "nine_attribution_paths": len(attribution_links) == 9,
        "first_10_kit_ready": len(build_first_10_launch_kit(attribution_links)) == 3,
        "seven_day_plan_ready": len(weekly_content) == 7,
        "content_approval_is_non_publishing": all(item.get("publication_state") == "NOT_PUBLISHED" for item in weekly_content),
        "real_and_simulated_separated": "simulated_stages" in measured,
        "seo_launch_plan_ready": True,
        "stripe_held_until_certified": build_first_paid_customer_path().get("charging_allowed") is False,
        "paid_ads_held": True,
    }
    acquisition_ready = all(acquisition_controls.values())
    live_acquisition_ready_local = acquisition_ready and all(launch_controls.values())
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
    real_stages = _mapping(measured.get("stages"))
    simulated_stages = _mapping(measured.get("simulated_stages"))
    today_real = _mapping(measured.get("today_stages"))
    milestone_specs = (
        ("FIRST_REAL_VISITOR", "PRIMER VISITANTE REAL", real_stages.get("LANDING"), "Landing atribuida tras registro; no se persiste navegacion anonima sin consentimiento."),
        ("FIRST_REAL_REGISTRATION", "PRIMER REGISTRO REAL", real_stages.get("REGISTRATION"), "Evento REGISTRATION con evidence_origin REAL_USER."),
        ("FIRST_REAL_FIRST_VALUE", "PRIMER FIRST_VALUE REAL", real_stages.get("FIRST_VALUE"), "Match Center canonico real abierto por usuario autenticado."),
        ("FIRST_REAL_ACTIVATED", "PRIMER ACTIVATED REAL", real_stages.get("ACTIVATED"), "FIRST_VALUE seguido de favorito o segundo partido distinto."),
        ("FIRST_REAL_RETURNING", "PRIMER RETURNING REAL", real_stages.get("RETURNING"), "Retorno autenticado en una fecha posterior."),
        ("FIRST_REAL_PREMIUM_INTENT", "PRIMER PREMIUM INTENT REAL", real_stages.get("PREMIUM_INTENT"), "Consulta autenticada de membresias o valor premium."),
        ("FIRST_REAL_PRO", "PRIMER PRO REAL", real_stages.get("PRO"), "Requiere evento REAL_USER y certificacion Stripe; un plan agregado no basta."),
        ("FIRST_REAL_ELITE", "PRIMER ELITE REAL", real_stages.get("ELITE"), "Requiere evento REAL_USER y certificacion Stripe; un plan agregado no basta."),
        ("FIRST_REAL_MRR", "PRIMER MRR REAL", revenue.get("mrr"), "Solo importes confirmados; nunca se estima MRR."),
    )
    milestones = [
        {"key": key, "label": label, "value": value if value not in (None, "") else 0, "state": "OBSERVED" if value not in (None, "", 0, "0") else "WAITING_REAL_USER", "evidence": evidence}
        for key, label, value, evidence in milestone_specs
    ]
    published_content = len([item for item in weekly_content if item.get("publication_state") == "PUBLISHED"])
    daily_growth_brief = {
        "title": f"Founder Growth Brief - {now_iso[:10]}",
        "clients_today": {
            "visitors": today_real.get("LANDING", 0),
            "registrations": today_real.get("REGISTRATION", 0),
            "first_value": today_real.get("FIRST_VALUE", 0),
            "activated": today_real.get("ACTIVATED", 0),
            "returning": today_real.get("RETURNING", 0),
            "premium_intent": today_real.get("PREMIUM_INTENT", 0),
            "pro": _int(real_stages.get("PRO")),
            "elite": _int(real_stages.get("ELITE")),
            "mrr": revenue.get("mrr") if revenue.get("mrr") not in (None, "") else "No certificado",
        },
        "marketing": {
            "content_ready": len([item for item in weekly_content if item.get("status") in {"READY_FOR_REVIEW", "APPROVED", "EDITED"}]),
            "content_approved": approved_content,
            "content_published": published_content,
            "best_channel": revenue_brief.get("main_channels") if revenue_brief.get("main_channels") != "Sin atribucion real" else INSUFFICIENT_REAL_DATA,
            "best_cta": INSUFFICIENT_REAL_DATA,
            "best_content": INSUFFICIENT_REAL_DATA,
        },
        "funnel": {"largest_leak": _main_friction(funnel)},
        "recommendation": "Aprobar una invitacion directa y enviarla manualmente a una sola persona adecuada; despues comprobar FIRST_VALUE antes de ampliar.",
        "evidence_origin": "SYSTEM_OBSERVATION",
        "limitations": ["Las cifras SIMULATED_QA no aparecen en clientes reales.", "No se declara canal, CTA o contenido ganador sin muestra real."],
    }
    return {
        "contract": GROWTH_REVENUE_OS_CONTRACT,
        "version": app_version,
        "generated_at_madrid": now_iso,
        "mode": "founder_controlled_read_only",
        "status": "LIVE_ACQUISITION_READY_LOCAL" if live_acquisition_ready_local else "ACQUISITION_READY" if acquisition_ready else "FOUNDATION_READY",
        "growth_evidence_state": "PARTIAL" if real_stage_count >= 3 else INSUFFICIENT_REAL_DATA,
        "acquisition_readiness": {"state": "PASS_LOCAL" if acquisition_ready else "PARTIAL", "controls": acquisition_controls, "score": round(sum(1 for value in acquisition_controls.values() if value) / len(acquisition_controls) * 100)},
        "live_acquisition_readiness": {"state": "PASS_LOCAL_NOT_DEPLOYED" if live_acquisition_ready_local else "PARTIAL", "controls": launch_controls, "score": round(sum(1 for value in launch_controls.values() if value) / len(launch_controls) * 100), "production_state": "BLOCKED_UNTIL_PUSH_AND_DEPLOY"},
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
        "funnel_event_contract": GROWTH_FUNNEL_EVENT_CONTRACT,
        "instrumentation": instrumentation,
        "funnel_metrics": funnel_metrics,
        "first_value_definition": FIRST_VALUE_DEFINITION,
        "activated_user_definition": ACTIVATED_USER_DEFINITION,
        "attribution": {"channels": list(ATTRIBUTION_CHANNELS), "measured_channels": measured.get("channels") or [], "links": attribution_links, "utm_supported": True, "anonymous_session_only_without_consent": True, "fingerprinting": False},
        "first_100_progress": _first_100_progress(funnel, _mapping(measured.get("stages"))),
        "metrics": {
            "registered_label": next((item["value_label"] for item in funnel if item["key"] == "registration"), "Sin datos reales"),
            "free_label": next((item["value_label"] for item in funnel if item["key"] == "free"), "Sin datos reales"),
            "premium_intent_label": next((item["value_label"] for item in funnel if item["key"] == "premium_intent"), "Sin datos reales"),
            "pro_label": next((item["value_label"] for item in funnel if item["key"] == "pro"), "Sin datos reales"),
            "elite_label": next((item["value_label"] for item in funnel if item["key"] == "elite"), "Sin datos reales"),
            "paid_label": str(sum(_int(item.get("value")) for item in funnel if item["key"] in {"pro", "elite"})),
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
        "first_10_campaign": first_10_campaign,
        "first_10_launch_kit": build_first_10_launch_kit(attribution_links),
        "first_7_days_organic": weekly_content,
        "social_launch_kit": build_social_launch_kit(attribution_links),
        "first_user_observability": {
            "real_user": {"stages": real_stages, "events_total": measured.get("real_events_total", 0), "milestones": milestones},
            "simulated_qa": {"stages": simulated_stages, "events_total": measured.get("simulated_events_total", 0), "label": "SIMULATED_QA"},
            "separation_state": "PASS" if "simulated_stages" in measured else "PARTIAL",
            "anonymous_visitor_limitation": "No se persiste un visitante anonimo sin consentimiento; LANDING real se confirma al registrarse.",
        },
        "daily_founder_growth_brief": daily_growth_brief,
        "customer_feedback_prompt": {
            "route": "/beta",
            "timing": "Despues de FIRST_VALUE, nunca antes de que el usuario vea valor.",
            "questions": [
                "Entendiste que hace NeMeSiS?",
                "Encontraste un partido facilmente?",
                "Entendiste SHARK?",
                "Que te falto?",
                "Volverias manana?",
            ],
            "optional": True,
            "sensitive_data_requested": False,
        },
        "marketing_intelligence": {
            "status": "PREPARED_ONLY",
            "external_market_automation": "DISABLED_BY_DEFAULT",
            "source_compliance_required": True,
            "allowed_observation_types": ["FACT", "OBSERVATION", "INFERENCE", "IDEA"],
            "areas": ["tendencias deportivas", "busquedas", "competidores", "formatos", "SEO", "partners"],
            "limitations": ["No crawling masivo", "No copiar contenido", "No saltar paywalls", "No activar fuentes sin aprobacion"],
        },
        "content_package": content_package,
        "content_review": {**content_reviews, "reviewable_count": len(weekly_content), "approved_count": approved_content, "published_count": published_content, "publication_side_effect": False},
        "content_factory": {
            "status": "APPROVAL_FIRST",
            "content_types": ["posts", "articulos SEO", "newsletter", "scripts de video", "posts sociales", "Telegram", "calendario editorial", "campanas"],
            "states": ["DRAFT", "READY_FOR_REVIEW", "APPROVED", "SCHEDULED", "PUBLISHED", "MEASURED"],
            "founder_only_can_approve": True,
            "automatic_publication": False,
        },
        "social_media": _channel_plan(),
        "social_launch": build_social_launch_kit(attribution_links),
        "seo_launch": build_growth_seo_launch_plan(),
        "seo": {
            **seo_snapshot,
            "status": seo_snapshot.get("status") or "PARTIAL",
            "checklist": ["titles", "descriptions", "canonical", "sitemap", "robots", "structured_data", "internal_linking", "performance", "evergreen_content"],
            "quality_guardrail": "No crear paginas masivas de baja calidad.",
            "backlog": [
                {"priority": "P0", "item": "Certificar Core Web Vitals con observacion de produccion", "state": "BLOCKED_BY_PRODUCTION_EVIDENCE"},
                {"priority": "P1", "item": "Publicar tres contenidos evergreen aprobados y enlazados desde ayuda", "state": "READY_FOR_REVIEW"},
                {"priority": "P1", "item": "Validar indexacion real en buscadores tras despliegue", "state": "BLOCKED_BY_PRODUCTION_EVIDENCE"},
                {"priority": "P2", "item": "Ampliar datos estructurados solo en paginas con contenido real", "state": "READY_FOR_REVIEW"},
            ],
        },
        "crm_lifecycle": [
            "WELCOME",
            "FIRST_VALUE_HELP",
            "ACTIVATION_HELP",
            "SHARK_DISCOVERY",
            "FAVORITES",
            "PREMIUM_EDUCATION",
            "INACTIVE",
            "RETURN",
            "CANCELLATION",
            "WINBACK",
        ],
        "crm_journeys": [
            {"id": "WELCOME", "trigger": "REGISTRATION", "purpose": "Orientar hacia un partido real", "cta": "Abrir calendario", "status": "READY_FOR_REVIEW"},
            {"id": "FIRST_VALUE_HELP", "trigger": "REGISTRATION_WITHOUT_FIRST_VALUE", "purpose": "Reducir friccion inicial", "cta": "Encontrar un partido", "status": "READY_FOR_REVIEW"},
            {"id": "ACTIVATION_HELP", "trigger": "FIRST_VALUE_WITHOUT_ACTIVATED", "purpose": "Explicar favorito o segundo partido", "cta": "Guardar favorito", "status": "READY_FOR_REVIEW"},
            {"id": "SHARK_DISCOVERY", "trigger": "FIRST_VALUE", "purpose": "Explicar evidencia y limites de SHARK", "cta": "Ver contexto", "status": "READY_FOR_REVIEW"},
            {"id": "FAVORITES", "trigger": "ACTIVATED_BY_FAVORITE", "purpose": "Facilitar el retorno", "cta": "Ver favoritos", "status": "READY_FOR_REVIEW"},
            {"id": "PREMIUM_EDUCATION", "trigger": "PREMIUM_INTENT", "purpose": "Comparar planes sin presion", "cta": "Comparar planes", "status": "READY_FOR_REVIEW"},
            {"id": "INACTIVE", "trigger": "NO_RETURN_IN_CERTIFIED_WINDOW", "purpose": "Ofrecer ayuda, no urgencia", "cta": "Volver a NeMeSiS", "status": "READY_FOR_REVIEW"},
            {"id": "RETURN", "trigger": "RETURNING", "purpose": "Recuperar el contexto guardado", "cta": "Continuar", "status": "READY_FOR_REVIEW"},
            {"id": "CANCELLATION", "trigger": "CANCELLATION_REQUEST", "purpose": "Explicar baja clara y soporte", "cta": "Gestionar cuenta", "status": "READY_FOR_REVIEW"},
            {"id": "WINBACK", "trigger": "CANCELLED_AND_OPTED_IN", "purpose": "Informar solo con consentimiento", "cta": "Revisar novedades", "status": "READY_FOR_REVIEW"},
        ],
        "crm_guardrails": {"automatic_send": False, "consent_required": True, "unsubscribe_required": True, "mass_communications": False},
        "conversion_strategy": {
            "free": "Calendario, directo, resultados y SHARK base para demostrar valor antes de pagar.",
            "pro": "Seguimiento y contexto ampliado, Telegram premium y mas lectura SHARK cuando esten certificados.",
            "elite": "Alertas live, prioridad Telegram y SHARK contextual cuando esten certificados.",
            "upgrade_moments": ["primer valor", "favorito recurrente", "preview premium", "briefing diario", "Telegram opt-in"],
            "dark_patterns": False,
        },
        "pricing_validation": {
            "current_labels": {"FREE": "0 EUR", "PRO": "9,99 EUR/mes", "ELITE": "24,99 EUR/mes"},
            "stripe_price_ids_certified": False,
            "monthly_annual_clarity": "PARTIAL_MONTHLY_ONLY",
            "cancellation_visibility": "AVAILABLE",
            "renewal_terms": "REQUIRES_CHECKOUT_CERTIFICATION",
            "decision": "NO_CHANGE_RECOMMENDED",
            "reason": "No existe evidencia real suficiente de conversion, disposicion a pagar o churn para cambiar precios.",
            "automatic_price_change": False,
        },
        "customer_success": {
            "status": "PREPARED",
            "inputs": ["Beta Program", "Support Center", "Product Memory"],
            "tracks": ["onboarding", "FAQ", "incidencias", "cancelacion clara", "recuperacion", "satisfaccion", "churn reasons", "feature requests"],
        },
        "referrals": {
            "status": "DESIGNED_NOT_ACTIVE",
            "flow": "usuario -> enlace seguro -> registro -> FIRST_VALUE -> ACTIVATED",
            "events": ["referral_sent", "referral_registration", "referral_activated"],
            "measures": ["invite", "accepted", "activated"],
            "anti_abuse_required": True,
            "real_rewards": False,
            "automatic_activation": False,
            "founder_review_required": True,
        },
        "affiliates_partners": {
            "status": "GOVERNANCE_READY_NOT_ACTIVE",
            "separation_rule": "SHARK_ANALYSIS != COMMERCIAL_RELATIONSHIP",
            "fields": ["partner", "jurisdiction", "compliance", "commercial_model", "attribution", "status"],
        },
        "first_paid_customer_path": build_first_paid_customer_path(),
        "paid_ads_lab": _paid_ads_lab(),
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
            "items": experiments,
        },
        "automation_levels": list(AUTOMATION_LEVELS),
        "responsible_marketing": {
            "required": ["+18 donde aplique", "juego responsable", "sin promesas de beneficio", "sin dinero facil", "sin urgencia enganosa", "sin targeting de menores"],
            "blocked": ["fake_metrics", "fake_testimonials", "fake_partners", "misleading_claims", "automatic_spend", "automatic_mass_publishing"],
        },
        "growth_daily_workforce": {
            "status": "PREPARED_NO_PUBLICATION",
            "opportunities": [
                {"type": "CONTENT", "recommendation": "Revisar la pieza del siguiente dia antes de publicarla.", "evidence": "Calendario FIRST100 aprobado manualmente."},
                {"type": "SEO", "recommendation": "Conectar Search Console solo tras el despliegue y la autorizacion.", "evidence": "SEO local PASS; indexacion real no observada."},
                {"type": "FUNNEL", "recommendation": _main_friction(funnel), "evidence": "Embudo REAL_USER; SIMULATED_QA excluido."},
                {"type": "CHANNEL", "recommendation": "No declarar canal ganador hasta tener activados reales.", "evidence": revenue_brief.get("main_channels") or INSUFFICIENT_REAL_DATA},
                {"type": "EXPERIMENT", "recommendation": experiments[0].get("experiment") if experiments else "No disponible", "evidence": "Backlog approval-first; no ejecutado."},
            ],
            "automatic_actions": ["OBSERVE", "ANALYZE", "COMPARE", "PROPOSE", "PREPARE"],
            "blocked_actions": ["PUBLISH", "SPEND", "SEND", "CHARGE"],
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
        "first_customer_readiness": {"can_register": True, "understands_product": bool(instrumentation.get("landing_cro")), "can_reach_first_value": True, "help_available": bool(support), "plans_explained": True, "can_pay_when_stripe_certified": True, "can_cancel": True, "can_contact": True, "source_attribution_after_registration": True, "anonymous_dropoff_known": False, "state": "PARTIAL"},
        "next_action": "Aprobar manualmente FIRST_10_USERS y lanzar solo las primeras invitaciones controladas." if acquisition_ready else revenue_brief["daily_recommendation"],
    }
