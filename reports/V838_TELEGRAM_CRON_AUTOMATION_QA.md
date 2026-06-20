# V838 Telegram Cron Automation QA

## Validaciones objetivo

- Master tick sin secret debe responder 403.
- Master tick con secret y dry_run debe responder 200.
- Health-check con secret debe responder 200.
- Telegram admin/command center no debe romper sin secretos locales.

## Nota

No se env?an mensajes reales en local. La certificaci?n de env?o real depende de variables Render y Cron configurado.
