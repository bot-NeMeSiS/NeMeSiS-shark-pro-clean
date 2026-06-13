# V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX_REPORT

## Versión

`V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX`

## Resumen

V760 es una intervención directa sobre la experiencia real observada en vídeo. No es una capa decorativa: corrige errores funcionales, reduce el desorden del cliente, reordena el Home y deja la app más cerca de una experiencia vendible.

## Problemas corregidos

### SHARK no funcionaba

Se corrigieron errores JavaScript en `templates/base.html`:

- CSRF token roto por ternario inválido.
- Favoritos roto por método `POST/DELETE` mal escrito.
- Activación de navegación rota por ternario inválido.
- Detección mobile/tablet/desktop rota por ternarios inválidos.

Esto afectaba a SHARK, favoritos y experiencia adaptativa.

### Botones y navegación duplicada

Se simplificó la navegación del cliente:

- Inicio.
- Partidos.
- Directo.
- Picks.
- Histórico.
- Más.

Se retiró el botón flotante global PC/Móvil para no competir con SHARK. La experiencia PC/Móvil se mantiene en `/experiencia`, `/modo-app`, `/adaptive` y `/adaptativo`.

### Home desordenado

Se reescribió `templates/home.html` para usuario logueado:

- Panel principal claro.
- Estado del día.
- KPIs útiles.
- Acciones principales.
- Próximos partidos.
- Picks activos.
- Orden recomendado.
- Alertas y soporte.
- Mensaje de transparencia.

La landing pública sigue separada para usuarios no autenticados.

### Ruido técnico visible al cliente

Se añadió CSS V760 para ocultar bloques técnicos de versión V756/V757/V758/V759 en vistas cliente autenticadas, evitando que el usuario vea capas repetidas de evolución interna.

### Enlaces rotos

Se corrigieron enlaces rotos:

- `/calendarlane=` → `/calendar?lane=`
- `/livef=` → `/live?f=`
- `/picksfiltro=` → `/picks?filtro=`
- `/sharkpick=` → `/shark?pick=`
- `/match-hublane=` → `/match-hub?lane=`
- `/api/shark/core-summarypublic=` → `/api/shark/core-summary?public=`

## Archivos principales tocados

- `VERSION.txt`
- `app.py`
- `templates/base.html`
- `templates/home.html`
- `templates/calendar.html`
- `templates/live.html`
- `templates/picks.html`
- `templates/match_detail.html`
- `templates/match_hub.html`
- `templates/client_app_center.html`
- `templates/admin_shark_center.html`
- `static/app.css`
- `tools/check_v760_sale_ready_client_order.py`
- `tools/build_clean_release.py`
- `reports/V760_VIDEO_UX_AUDIT_AND_FIX_PLAN.md`
- `reports/V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX_REPORT.md`

## Validaciones esperadas

- `python -m py_compile app.py`
- `python -m compileall app.py engines tools`
- `python tools/check_v760_sale_ready_client_order.py`
- Jinja parse.
- Smoke de rutas cliente/admin/API.
- Cron sin secret 403.
- Cron con secret 200.
- ZIP limpio forbidden_count=0.

## Limitación honesta

La certificación de envío real Telegram depende de Render, variables reales, candidato válido y canal. V760 corrige SHARK y UX; no fuerza envío real desde local para evitar spam.
