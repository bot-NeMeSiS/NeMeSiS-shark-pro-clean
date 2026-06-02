# V580 — Telegram Picks Full Audit & Delivery Fix

Objetivo: auditar de punta a punta por qué los picks no se envían por Telegram y dejar acciones directas para corregirlo desde Admin.

## Añadido

- Auditoría completa de Telegram para picks.
- Comprobación de `TELEGRAM_BOT_TOKEN`.
- Comprobación de `TELEGRAM_CHAT_ID`.
- Revisión de delivery automático y `auto_daily_picks`.
- Revisión de suscriptores activos con `chat_id`.
- Revisión de picks publicados disponibles.
- Revisión de cola, enviados y fallidos.
- Botones admin:
  - Auditar picks Telegram.
  - Preparar envíos picks.
  - Enviar picks ahora.
- APIs admin:
  - `/api/telegram/audit-picks`
  - `/api/telegram/fix-picks`
  - `/api/telegram/send-picks-now`

## Para que funcione en Render

Variables necesarias:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

El bot debe estar iniciado si es chat privado, o ser admin si se usa canal/grupo.

## Flujo recomendado

1. Entrar como admin.
2. Ir a `/admin/telegram`.
3. Pulsar `Auditar picks Telegram`.
4. Si algo sale en revisar, corregir lo indicado.
5. Pulsar `Preparar envios picks`.
6. Pulsar `Enviar picks ahora`.
7. Revisar logs y cola en la misma pantalla.
