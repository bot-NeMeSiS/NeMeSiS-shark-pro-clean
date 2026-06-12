# V744 Telegram Certification QA

## Resultado

La certificación V744 es no invasiva: revisa configuración y diagnósticos sin enviar mensajes reales.

## Puntos verificados

- `TELEGRAM_BOT_TOKEN` se detecta por entorno.
- `TELEGRAM_CHAT_ID` se detecta por entorno.
- `TELEGRAM_BOT_USERNAME` se detecta por entorno.
- `ENABLE_TELEGRAM_AUTO` y `AUTO_SEND_TELEGRAM_PICKS` se leen por entorno.
- Diagnóstico admin permanece separado.

## Limitación honesta

El envío real solo puede certificarse en producción con variables reales y canal real. El código no fuerza envíos durante QA local.
