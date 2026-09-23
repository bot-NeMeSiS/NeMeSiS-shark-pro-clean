# Provider Maintenance Control · 23/09/2026

## Objetivo

Integrar el estado de las APIs contratadas y servicios externos en el mantenimiento
administrativo existente, sin crear un sistema paralelo ni hacer llamadas al proveedor
al abrir la página.

## Contrato

- `/admin/system`, `/admin/platform-maintenance` y `/admin/mantenimiento-plataforma`
  son la misma superficie de mantenimiento.
- GET de mantenimiento: 0 llamadas externas.
- `/api/admin/provider-maintenance/status`: solo admin, lectura local.
- `/api/admin/provider-maintenance/check`: POST + admin + CSRF, una comprobación
  explícita por proveedor.
- Cooldown: 300 s. Pulsaciones repetidas reutilizan la última evidencia y realizan
  0 llamadas.
- Nunca se persisten o devuelven claves, tokens ni payloads completos.

## Proveedores

### API-Football / API-Sports
El test directo usa el endpoint de estado existente y conserva únicamente HTTP, plan,
activo/caducidad y cuota saneada. Solo se marca `PAID_PLAN_VERIFIED` si el proveedor
devuelve un plan distinto de FREE/INACCESSIBLE. Una clave configurada nunca se presenta
como plan pagado.

### The Odds API
El test directo valida la credencial mediante el cliente existente y conserva solo
HTTP, recuento y cabeceras de cuota admitidas. No se afirma un nombre de plan que la
respuesta no exponga.

### TheSportsDB
El test usa una lectura de catálogo y conserva únicamente si conectó y el número de
elementos observados. No guarda la respuesta.

## Otros servicios

Stripe, OpenAI y Telegram aparecen como configuración presente/ausente. Esta fase no
crea cobros, mensajes Telegram ni llamadas OpenAI.

## Seguridad y coste

La vista nunca ejecuta proveedores. Los tests manuales están separados de la
sincronización normal y no desactivan backoff, caché ni credit guards existentes.
La evidencia se guarda saneada en `automation_state` para que el administrador pueda
consultarla después sin repetir gasto.
