# V755 Telegram Real Auto Send Final Certification Runbook

## Objetivo

Certificar en Render que Telegram automático envía picks reales al canal global sin intervención del admin.

## Variables necesarias en Render

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `ENABLE_TELEGRAM_AUTOMATION=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `TELEGRAM_AUTO_SEND_ENABLED=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`
- `TELEGRAM_PICK_WINDOW_HOURS_BEFORE=24`
- `TELEGRAM_PICK_MIN_MINUTES_BEFORE=15`
- `TELEGRAM_PICK_PRO_SLOTS=10:00-13:30,17:00-21:30`
- `TELEGRAM_PICK_URGENT_MINUTES_BEFORE=90`
- `TELEGRAM_SUMMARY_WINDOWS=09:00-11:30,17:00-19:30`
- `TZ=Europe/Madrid`
- `APP_TIMEZONE=Europe/Madrid`

## Cron obligatorio

Render Web Service no garantiza threads internos vivos durante horas. Para producción se debe usar Render Cron.

### Telegram Tick

- Metodo: `GET`
- Frecuencia: cada 15 minutos
- URL:

`https://bot-apuestas-crgf.onrender.com/api/automation/telegram/tick?secret=VALOR_REAL_DE_AUTOMATION_SECRET&runner=render_cron`

### Daily Automation

- Metodo: `GET`
- Frecuencia: cada hora o diario a las 10:00 Europe/Madrid
- URL:

`https://bot-apuestas-crgf.onrender.com/api/automation/daily/run?secret=VALOR_REAL_DE_AUTOMATION_SECRET&runner=render_cron`

## Certificación real en Render

1. Abrir Admin Telegram Command Center.
2. Pulsar `Crear candidato Telegram de prueba`.
3. Confirmar que aparece un candidato con:
   - estado `telegram_test`;
   - hora Madrid futura;
   - mercado normalizado;
   - cuota normalizada;
   - destino canal global.
4. Ejecutar Render Cron manualmente con `Trigger Run` sobre Telegram Tick.
5. Confirmar respuesta JSON:
   - `status=SENT`;
   - `sent_count=1`;
   - `modules.auto_picks.sent=1`;
   - `last_cron_delivery_id` con valor.
6. Abrir el canal Telegram y verificar llegada del mensaje.
7. Ejecutar de nuevo el mismo Cron.
8. Confirmar:
   - `sent_count=0`;
   - `DUPLICATE_ALREADY_SENT` aparece en descartes;
   - no llega duplicado al canal.

## Interpretación de descartes

- `MISSING_MARKET`: el pick no tiene mercado real. `Principal` no cuenta.
- `MISSING_ODDS_WARNING`: la cuota falta, pero el pick puede enviarse con aviso si lo demás es válido.
- `MISSING_MATCH_TIME`: falta hora suficiente para programar envío.
- `OLD_MATCH`: el partido ya pasó.
- `MATCH_STARTED`: el partido ya empezó.
- `TOO_EARLY`: el partido está fuera de la ventana previa.
- `TOO_LATE`: queda menos del margen mínimo.
- `WAITING_FOR_PRO_SLOT`: el pick es válido, pero espera slot profesional.
- `DUPLICATE_ALREADY_SENT`: dedupe correcto, no reenviar.

## Resultado esperado

Con Render Cron configurado, un pick válido entra en cola, se procesa, se envía al canal global y queda marcado como enviado. Si existen usuarios privados vinculados, reciben según membresía. Si no existen privados, el canal global sigue recibiendo.
