# V874 Telegram No Filler Dedupe QA

## Revisión

Se revisaron pantalla cliente Telegram, textos y botones de cola Telegram.

## Correcciones

- Se eliminó mojibake de iconos/botones Telegram en `app.py` y `templates/telegram.html`.
- Se preserva dedupe/no filler.
- No se envió Telegram real.

## Estado

Render real indica Telegram configurado, pero V874 local no ejecuta envíos reales.

