# V772 Telegram Visual Cards + App Global Polish Cleanup

## Versión

`V772_TELEGRAM_VISUAL_CARDS_APP_GLOBAL_POLISH_CLEANUP`

## Objetivo

V772 mantiene la base estable de V771 y añade una capa profesional para mensajes visuales de Telegram, sin rehacer Telegram, SHARK, picks, Render Cron ni la experiencia cliente existente.

## Cambios aplicados

- Se añadió `engines/telegram_visual_card_engine.py`.
- Se reforzó `engines/telegram_message_formatter.py` con textos premium en castellano.
- Se corrigieron caracteres corruptos visibles en mensajes Telegram.
- Se añadió formato específico para combinadas Telegram.
- Se añadió soporte opcional para tarjetas PNG mediante Pillow.
- Se integró envío visual con `sendPhoto` cuando existe PNG válido.
- Se mantiene fallback automático a `sendMessage` si no se puede generar o enviar imagen.
- Se añadieron variables Render para activar/desactivar tarjetas visuales.
- Se amplió el diagnóstico Telegram con estado de tarjetas visuales.
- Se dejó V771 activity, dedupe, quiet hours, World Cup override y Render Cron intactos.

## Telegram visual cards

La app puede generar tarjetas para:

- Pick premium.
- Combi.
- Resultado.
- Highlight.
- Live, desactivado por defecto para no saturar.

El motor no descarga escudos ni imágenes externas. Usa datos reales y fallback visual seguro. Si Pillow no está disponible, Telegram no falla: se envía el mensaje textual premium.

## Variables nuevas

- `TELEGRAM_VISUAL_CARDS_ENABLED=true`
- `TELEGRAM_SEND_PICK_CARDS=true`
- `TELEGRAM_SEND_COMBI_CARDS=true`
- `TELEGRAM_SEND_RESULT_CARDS=true`
- `TELEGRAM_SEND_HIGHLIGHT_CARDS=true`
- `TELEGRAM_SEND_LIVE_CARDS=false`

## Riesgos controlados

- No se inventan cuotas, picks, resultados ni highlights.
- No se envían imágenes enormes de escudos.
- No se rompe Telegram si falla la imagen.
- No se altera `DB_PATH`.
- No se cambia el flujo Render Cron.

## Resultado

V772 deja Telegram más visual y premium, con fallback seguro y trazabilidad clara para producción.
