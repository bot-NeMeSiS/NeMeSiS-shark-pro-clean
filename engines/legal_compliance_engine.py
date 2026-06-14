"""V788 legal and responsible subscription readiness helpers.

This module intentionally does not provide legal advice. It gives product-safe
copy, UI structure and operational checks so the app is positioned as an
informational sports analytics SaaS, not as a betting operator.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime

LEGAL_COMPLIANCE_VERSION = "V788-LEGAL-2026-06-14"

BUSINESS_POSITIONING = {
    "one_liner": "NeMeSiS SHARK PRO es una plataforma informativa de análisis deportivo, datos, alertas y seguimiento; no es casa de apuestas.",
    "not_operator": "No aceptamos apuestas, no custodiamos saldo para apostar, no pagamos premios y no garantizamos beneficios.",
    "risk": "Los picks, cuotas, estadísticas y señales pueden fallar. El deporte tiene incertidumbre y cualquier decisión es responsabilidad del usuario.",
}

LEGAL_NAV = [
    {"slug": "centro", "label": "Centro legal", "href": "/legal"},
    {"slug": "no_bookmaker", "label": "No somos casa de apuestas", "href": "/no-somos-casa-de-apuestas"},
    {"slug": "responsable", "label": "Juego responsable", "href": "/juego-responsable"},
    {"slug": "terminos", "label": "Términos", "href": "/terminos"},
    {"slug": "privacidad", "label": "Privacidad", "href": "/privacidad"},
    {"slug": "cookies", "label": "Cookies", "href": "/cookies"},
    {"slug": "reembolsos", "label": "Cancelaciones", "href": "/reembolsos"},
    {"slug": "aviso", "label": "Aviso legal", "href": "/aviso-legal"},
]

PAGES = {
    "centro": {
        "eyebrow": "Legalidad, transparencia y confianza",
        "title": "Centro legal de NeMeSiS SHARK PRO",
        "lead": "Antes de cobrar en real, la app queda posicionada como suscripción informativa de análisis deportivo, no como operador de juego.",
        "cards": [
            {"title": "+18 y responsabilidad", "body": "Contenido orientado a adultos. No fomenta decisiones impulsivas ni uso de dinero que no puedas permitirte perder."},
            {"title": "No somos operador", "body": "La app no acepta apuestas, depósitos para apostar ni pagos de premios."},
            {"title": "Sin promesas", "body": "No se prometen beneficios, aciertos garantizados ni rentabilidad segura."},
            {"title": "Datos permitidos", "body": "Uso de APIs, caché propia e importaciones autorizadas; sin scraping ilegal ni rehosting de contenido externo."},
        ],
        "sections": [
            {"title": "Qué vendemos", "body": "Vendemos acceso a software, análisis, organización de datos deportivos, alertas, histórico, explicaciones de mercados y herramientas informativas."},
            {"title": "Qué no vendemos", "body": "No vendemos apuestas, no gestionamos botes, no somos intermediario de apuestas y no damos asesoramiento financiero."},
            {"title": "Antes de pagar", "body": "El checkout exige aceptación expresa de +18, términos, privacidad, ausencia de garantía y condición de no operador."},
        ],
    },
    "no_bookmaker": {
        "eyebrow": "Diferencia clave",
        "title": "NeMeSiS SHARK PRO no es una casa de apuestas",
        "lead": "Esta página deja claro el límite del producto para clientes, Stripe, soporte y administración.",
        "cards": [
            {"title": "No depósitos", "body": "El usuario no deposita saldo en NeMeSiS para apostar."},
            {"title": "No apuestas internas", "body": "No existe cupón de apuesta, boleto, slip ni ejecución de apuesta dentro de la app."},
            {"title": "No premios", "body": "No pagamos premios, jackpots ni retornos de apuestas."},
            {"title": "No garantías", "body": "Un análisis puede ser útil y aun así fallar."},
        ],
        "sections": [
            {"title": "Descripción segura para Stripe", "body": "Software/SaaS de análisis deportivo, seguimiento de eventos, alertas y herramientas informativas para usuarios adultos."},
            {"title": "Lenguaje a evitar", "body": "Evitar 'ganancia segura', 'dinero garantizado', 'apuesta aquí', 'te hacemos ganar', 'cuota segura' o 'beneficio fijo'."},
        ],
    },
    "responsable": {
        "eyebrow": "Juego responsable",
        "title": "Control, límites y decisión consciente",
        "lead": "La app debe ayudar a entender riesgo, no empujar a apostar más.",
        "cards": [
            {"title": "+18", "body": "Uso solo por personas adultas y donde sea legal."},
            {"title": "Bankroll", "body": "Usa límites y stakes pequeños; no persigas pérdidas."},
            {"title": "Riesgo real", "body": "Cuota alta significa más incertidumbre; ningún pick es seguro."},
            {"title": "Pausa", "body": "Si pierdes control, para y busca ayuda profesional/local."},
        ],
        "sections": [
            {"title": "Regla de producto", "body": "La interfaz prioriza avisos de riesgo, histórico real y transparencia por encima de promesas comerciales."},
            {"title": "Soporte", "body": "El usuario puede contactar soporte para cuenta, facturación, Telegram o dudas del producto."},
        ],
    },
    "terminos": {
        "eyebrow": "Términos de suscripción",
        "title": "Términos y condiciones de uso",
        "lead": "Borrador operativo para la app. Debe revisarse por un profesional antes de lanzamiento masivo.",
        "cards": [
            {"title": "Servicio", "body": "Acceso a plataforma informativa deportiva y funciones según plan FREE/PRO/ELITE."},
            {"title": "Suscripción", "body": "PRO y ELITE son planes mensuales gestionados por Stripe."},
            {"title": "Sin garantía", "body": "No hay promesa de acierto, beneficio, ROI ni disponibilidad absoluta de datos externos."},
            {"title": "Uso correcto", "body": "Prohibido usar la app para fraude, scraping, reventa no autorizada o actividad ilícita."},
        ],
        "sections": [
            {"title": "Naturaleza informativa", "body": "El contenido es educativo/informativo y no constituye asesoramiento financiero, legal ni garantía de resultado."},
            {"title": "Planes", "body": "FREE ofrece acceso básico; PRO/ELITE desbloquean funciones premium como picks explicados, Telegram y SHARK según configuración vigente."},
            {"title": "Cambios", "body": "La plataforma puede ajustar funciones, fuentes o textos para mejorar seguridad, legalidad y calidad."},
        ],
    },
    "privacidad": {
        "eyebrow": "Datos personales",
        "title": "Política de privacidad",
        "lead": "Resumen claro de datos tratados por la app. Ajustar responsable, NIF/CIF y contacto antes del lanzamiento público real.",
        "cards": [
            {"title": "Cuenta", "body": "Nombre, usuario, email, contraseña cifrada y plan."},
            {"title": "Uso", "body": "Favoritos, actividad, Telegram, pagos y preferencias necesarias para prestar el servicio."},
            {"title": "Pagos", "body": "Stripe procesa pagos; la app guarda IDs técnicos y estado de suscripción, no números completos de tarjeta."},
            {"title": "Derechos", "body": "El usuario debe poder solicitar acceso, rectificación, supresión, oposición y limitación cuando aplique."},
        ],
        "sections": [
            {"title": "Base de tratamiento", "body": "Ejecución de la relación de usuario/suscripción, interés legítimo de seguridad y consentimiento cuando sea necesario."},
            {"title": "Encargados", "body": "Render aloja la app, Stripe procesa pagos, Telegram/OpenAI/TheSportsDB/The Odds API pueden intervenir según funciones activas."},
            {"title": "Seguridad", "body": "No se deben exponer secretos, tokens, números completos de tarjeta ni bases de datos en descargas o vistas públicas."},
        ],
    },
    "cookies": {
        "eyebrow": "Cookies y sesión",
        "title": "Política de cookies",
        "lead": "La app usa cookies técnicas de sesión y seguridad; cualquier analítica/marketing debe informarse y requerir consentimiento si aplica.",
        "cards": [
            {"title": "Técnicas", "body": "Inicio de sesión, CSRF, seguridad y funcionamiento básico."},
            {"title": "Preferencias", "body": "Estado de navegación, plan elegido o retorno tras login cuando sea necesario."},
            {"title": "Analítica", "body": "No activar herramientas de terceros sin revisar banner/consentimiento."},
            {"title": "Stripe", "body": "Checkout/Portal puede usar cookies propias de Stripe fuera de la app."},
        ],
        "sections": [
            {"title": "Control", "body": "El usuario puede gestionar cookies desde el navegador. Las cookies técnicas pueden ser necesarias para iniciar sesión o pagar."},
        ],
    },
    "reembolsos": {
        "eyebrow": "Facturación clara",
        "title": "Cancelaciones y reembolsos",
        "lead": "Regla comercial simple: suscripción mensual, cancelación desde portal Stripe y acceso hasta fin del periodo pagado salvo abuso/fraude.",
        "cards": [
            {"title": "Cancelación", "body": "El cliente puede gestionar o cancelar desde el portal de Stripe si está activado."},
            {"title": "Periodo activo", "body": "Al cancelar, normalmente conserva acceso hasta el fin del periodo ya pagado."},
            {"title": "Errores", "body": "Si hay cobro duplicado o problema técnico, soporte debe revisarlo manualmente."},
            {"title": "Sin premios", "body": "No existen devoluciones ligadas a resultados deportivos."},
        ],
        "sections": [
            {"title": "Reembolsos", "body": "Se valorarán caso por caso por incidencias técnicas, cobros duplicados o imposibilidad real de acceso imputable al servicio."},
        ],
    },
    "aviso": {
        "eyebrow": "Aviso legal",
        "title": "Aviso legal y datos del titular",
        "lead": "Completar con datos reales antes de lanzamiento público: titular, NIF/CIF, domicilio, email de soporte y jurisdicción.",
        "cards": [
            {"title": "Titular", "body": "Pendiente de completar por el responsable legal del proyecto."},
            {"title": "Contacto", "body": "Configurar email de soporte y facturación antes de cobrar en real."},
            {"title": "Actividad", "body": "Software de análisis deportivo informativo por suscripción."},
            {"title": "Jurisdicción", "body": "Definir ámbito territorial y condiciones aplicables con revisión profesional."},
        ],
        "sections": [
            {"title": "Pendiente crítico", "body": "Antes de pagos reales públicos, completar datos legales del titular y revisar textos con asesoría."},
        ],
    },
}


def checkout_legal_checklist() -> list[dict]:
    return [
        {"key": "accept_age", "label": "Confirmo que soy mayor de 18 años y uso la plataforma donde sea legal."},
        {"key": "accept_terms", "label": "Acepto los Términos y condiciones de suscripción."},
        {"key": "accept_privacy", "label": "Acepto la Política de privacidad y el tratamiento necesario para cuenta, pago y servicio."},
        {"key": "accept_no_guarantee", "label": "Entiendo que no hay ganancias garantizadas, aciertos seguros ni promesa de ROI."},
        {"key": "accept_not_betting_operator", "label": "Entiendo que NeMeSiS SHARK PRO no es casa de apuestas, no acepta apuestas ni paga premios."},
    ]


def legal_compliance_payload() -> dict:
    return {
        "version": LEGAL_COMPLIANCE_VERSION,
        "positioning": BUSINESS_POSITIONING,
        "nav": LEGAL_NAV,
        "checkout_checklist": checkout_legal_checklist(),
        "go_live_gate": [
            "Cuenta Stripe verificada y apta para el tipo de negocio.",
            "IBAN real añadido en modo live.",
            "Productos/precios live creados y conectados en Render.",
            "Webhook live configurado y probado.",
            "Aviso legal con titular real completado.",
            "Términos, privacidad, cookies y reembolsos revisados.",
            "Lenguaje comercial sin promesas de ganancias.",
        ],
        "unsafe_words": ["ganancia segura", "dinero garantizado", "apuesta segura", "beneficio fijo", "sin riesgo", "te hacemos ganar"],
    }


def legal_page_payload(page: str = "centro") -> dict:
    page = page if page in PAGES else "centro"
    data = dict(PAGES[page])
    data["slug"] = page
    data["nav"] = LEGAL_NAV
    data["positioning"] = BUSINESS_POSITIONING
    data["version"] = LEGAL_COMPLIANCE_VERSION
    data["disclaimer"] = "Contenido informativo y borrador operativo; debe revisarse por asesoría legal antes de lanzamiento público masivo."
    return data


def _table_count(db_path: str, table: str) -> int:
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row or not row[0]:
            conn.close()
            return 0
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.close()
        return int(count or 0)
    except Exception:
        return 0


def legal_admin_snapshot(db_path: str) -> dict:
    env = os.environ
    stripe_live = str(env.get("STRIPE_SECRET_KEY", "")).strip().startswith("sk_live_")
    price_live_ready = str(env.get("STRIPE_PRICE_PRO", "")).strip().startswith("price_") and str(env.get("STRIPE_PRICE_ELITE", "")).strip().startswith("price_")
    webhook_ready = str(env.get("STRIPE_WEBHOOK_SECRET", "")).strip().startswith("whsec_")
    accepted = _table_count(db_path, "user_legal_acceptances")
    checks = [
        {"title": "Posicionamiento", "status": "READY", "detail": BUSINESS_POSITIONING["one_liner"]},
        {"title": "Checkout legal", "status": "READY", "detail": "El pago exige aceptación expresa de +18, términos, privacidad, no garantías y no operador."},
        {"title": "Stripe live", "status": "READY" if stripe_live else "PENDING", "detail": "STRIPE_SECRET_KEY live detectada." if stripe_live else "Aún no se detecta sk_live_; sigue en test o falta configurar Render."},
        {"title": "Price IDs", "status": "READY" if price_live_ready else "PENDING", "detail": "PRO/ELITE usan price_..." if price_live_ready else "Revisa STRIPE_PRICE_PRO y STRIPE_PRICE_ELITE."},
        {"title": "Webhook", "status": "READY" if webhook_ready else "PENDING", "detail": "STRIPE_WEBHOOK_SECRET presente." if webhook_ready else "Falta whsec_ live/test en Render."},
        {"title": "Aceptaciones auditadas", "status": "READY" if accepted else "INFO", "detail": f"{accepted} aceptaciones registradas en la base de datos."},
        {"title": "Datos titular", "status": "ACTION", "detail": "Completar aviso legal con titular, NIF/CIF, domicilio y soporte antes de abrir pagos reales al público."},
        {"title": "Revisión profesional", "status": "ACTION", "detail": "Validar textos y modelo de negocio con asesoría antes de escalar."},
    ]
    ready = sum(1 for c in checks if c["status"] == "READY")
    score = int(round((ready / len(checks)) * 100))
    return {
        "version": LEGAL_COMPLIANCE_VERSION,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "score": score,
        "checks": checks,
        "accepted_count": accepted,
        "gate": legal_compliance_payload()["go_live_gate"],
        "unsafe_words": legal_compliance_payload()["unsafe_words"],
    }
