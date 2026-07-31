# Company Platform Report

## Decision

PASS LOCAL.

## Contract

`NEMESIS-COMPANY-PLATFORM-BUSINESS-ECOSYSTEM-V1`

## Scope

Infraestructura comercial publica para landing oficial, precios, FAQ, ayuda, conocimiento, roadmap publico, changelog, estado del servicio, contacto, legal, privacidad, cookies, partners, afiliados y blog.

## Pages

| pagina | ruta | estado |
| --- | --- | --- |
| Landing oficial | /landing | PREPARADA |
| Pagina de precios | /precios | PREPARADA |
| FAQ | /faq | PREPARADA |
| Centro de ayuda | /help-center | PREPARADA |
| Base de conocimiento | /knowledge-base | PREPARADA |
| Roadmap publico | /roadmap | PREPARADA |
| Changelog | /changelog | PREPARADA |
| Estado del servicio | /service-status | PREPARADA |
| Partners | /partners | PREPARADA |
| Afiliados | /afiliados | PREPARADA |
| Blog | /blog | PREPARADA |


## Guardrails

- 0 pagos ejecutados.
- 0 campanas lanzadas.
- 0 llamadas externas.
- 0 Telegram.
- 0 nuevas fuentes deportivas.
- 0 contenido ficticio publicado.

## QA

```json
{
  "ok": true,
  "contract": "NEMESIS-COMPANY-PLATFORM-BUSINESS-ECOSYSTEM-V1",
  "generated_at_madrid": "2026-07-31T11:02:31+02:00",
  "production_modified": false,
  "external_calls": 0,
  "telegram_sends": 0,
  "stripe_calls": 0,
  "new_sports_engines": 0,
  "new_sports_sources": 0,
  "required_routes": [
    "/affiliates",
    "/afiliados",
    "/base-conocimiento",
    "/blog",
    "/cambios",
    "/centro-ayuda",
    "/changelog",
    "/contact",
    "/cookies",
    "/empresa",
    "/estado-servicio",
    "/faq",
    "/help-center",
    "/knowledge-base",
    "/landing",
    "/oficial",
    "/partners",
    "/precios",
    "/preguntas-frecuentes",
    "/pricing",
    "/privacidad",
    "/roadmap",
    "/roadmap-publico",
    "/service-status",
    "/socios",
    "/status",
    "/support",
    "/terminos"
  ],
  "missing_routes": [],
  "public_pages": [
    {
      "pagina": "Landing oficial",
      "ruta": "/landing",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Pagina de precios",
      "ruta": "/precios",
      "estado": "PREPARADA"
    },
    {
      "pagina": "FAQ",
      "ruta": "/faq",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Centro de ayuda",
      "ruta": "/help-center",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Base de conocimiento",
      "ruta": "/knowledge-base",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Roadmap publico",
      "ruta": "/roadmap",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Changelog",
      "ruta": "/changelog",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Estado del servicio",
      "ruta": "/service-status",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Partners",
      "ruta": "/partners",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Afiliados",
      "ruta": "/afiliados",
      "estado": "PREPARADA"
    },
    {
      "pagina": "Blog",
      "ruta": "/blog",
      "estado": "PREPARADA"
    }
  ],
  "failures": [],
  "decision": "PASS LOCAL",
  "limitations": [
    "Produccion no certificada por este check.",
    "Contenido editorial, partners y afiliados permanecen pendientes de aprobacion humana.",
    "Pagos no conectados desde la plataforma comercial."
  ]
}
```
