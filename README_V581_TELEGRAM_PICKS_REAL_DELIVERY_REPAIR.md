# V581 — Telegram Picks Real Delivery Repair

Objetivo: arreglar el caso real donde el mensaje de prueba de Telegram llega, pero los picks no llegan.

## Cambios

- Importado `QUEUE_SKIPPED` para evitar fallo al procesar cola con límite horario.
- Corregido bug crítico en `process_premium_telegram_queue`: `conn.execute` recibía parámetros duplicados y podía romper el envío al actualizar estado.
- `build_daily_picks_message()` ya no filtra solo ELITE de forma rígida. Ahora recoge picks publicados visibles para ADMIN/ELITE y, si no hay publicados, usa candidatos `pending/active` para auditoría/envío manual.
- Auditoría de picks ahora cuenta candidatos enviables, no solo publicados.
- `send_published_picks_to_telegram_now()` procesa una cola amplia para que los nuevos picks no queden bloqueados detrás de mensajes antiguos.

## Ruta recomendada en admin

1. Entrar como admin.
2. Ir a Admin > Telegram.
3. Pulsar auditoría/fix picks.
4. Pulsar enviar picks ahora.

## Variables necesarias en Render

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DB_PATH=/data/database.db`

Si el canal/grupo recibe pruebas pero no picks, esta versión corrige el flujo de picks/cola/filtros.
