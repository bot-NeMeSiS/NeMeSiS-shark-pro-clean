# V819 Telegram Pro Filter Compatibility QA

## Estado

V819 no modifica filtros Telegram, colas, Cron, scheduler ni formateadores de mensajes.

## Compatibilidad preservada

- Telegram automatico V818 se mantiene.
- Rutas admin Telegram se mantienen.
- La shell admin conserva acceso a Telegram.
- No se toca `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `AUTOMATION_SECRET` ni variables de entorno.

## Riesgo

El unico cambio relacionado es visual: topbar admin compacta mantiene enlace a `/admin/telegram/command-center`.
