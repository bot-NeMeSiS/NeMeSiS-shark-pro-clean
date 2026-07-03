# V887 Telegram Cron Tick QA

## Endpoint

`/api/automation/telegram/tick`

## Validaciones previstas

- Sin `secret`: debe devolver `403`.
- Con `secret` local y entorno seguro: debe devolver `200`.
- No debe aparecer `NameError`.
- No debe aparecer `QUEUE_SKIPPED is not defined`.
- No debe enviar Telegram real durante la prueba local.
- Debe detectar `runner=render_cron`.
- Debe conservar no filler y dedupe.

## Prueba local segura

El check V887 usa:

- DB temporal.
- `AUTOMATION_SECRET` local de prueba.
- `TELEGRAM_BOT_TOKEN` vacío.
- `TELEGRAM_CHAT_ID` vacío.
- automatización Telegram desactivada por entorno de prueba.

Esto permite validar el endpoint sin tocar producción y sin enviar mensajes.

## Estado esperado si no hay Telegram configurado

La app debe responder con estado seguro, por ejemplo:

- `AUTO_DISABLED`
- `QUEUE_EMPTY`
- `NO_DUE_JOBS`
- `NO_SENDABLE_ITEMS`

Lo importante para V887 es que el tick no caiga por `NameError`.

## Render

No se declara corregido en Render hasta desplegar V887 y volver a ejecutar el Cron real.

## Resultado local V887

- Sin secret: 403.
- Con secret local: 200.
- `runner=render_cron`: detectado.
- `NameError`: no reproducido.
- `QUEUE_SKIPPED is not defined`: no reproducido.
- Envío real Telegram: no ejecutado.
