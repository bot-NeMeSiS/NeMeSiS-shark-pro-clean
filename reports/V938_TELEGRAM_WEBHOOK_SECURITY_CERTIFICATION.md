# V938 Telegram Webhook Security Certification

## Estado

**CONFIRMADO LOCAL / PRODUCCIÓN NO CERTIFICADA**

## Cambio

- En producción, `POST /telegram/webhook` exige `X-Telegram-Bot-Api-Secret-Token` y `TELEGRAM_WEBHOOK_SECRET` configurado.
- Firma ausente o inválida: 403.
- Producción sin secreto configurado: 503 seguro; no procesa el update.
- Payload mayor de 1 MiB: 413.
- `GET` mantiene un health seguro y solo informa si la firma está configurada.
- Local/test conserva compatibilidad explícita para no romper fixtures; no se confunde con certificación productiva.

## Límites

No se registró webhook real, no se cambió BotFather, no se envió mensaje y no se validó el secreto de Render. La activación productiva requiere configurar el secreto en Telegram y Render con el mismo valor, sin imprimirlo.
