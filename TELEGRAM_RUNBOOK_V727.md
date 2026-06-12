# Telegram Runbook V727

## Objetivo

Saber por qué Telegram no envía y corregirlo sin hacer spam ni exponer secrets.

## Rutas principales

- Command Center: `/admin/telegram/command-center`
- Estado seguro: `/api/admin/telegram/status`
- Dry-run sin envío: `/api/admin/telegram/dry-run`
- Preview sin envío: `/api/admin/telegram/preview-next`
- Test controlado: `POST /api/admin/telegram/test-send`
- Cron Telegram: `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`
- Cron Daily: `/api/automation/daily/run?secret=AUTOMATION_SECRET`

## Orden de revisión

1. Abrir `/admin/telegram/command-center`.
2. Leer el estado principal.
3. Revisar configuración:
   - BOT_TOKEN configurado.
   - CHAT_ID configurado.
   - AUTOMATION_SECRET configurado.
   - Auto Telegram activo.
   - Football-only activo.
4. Revisar Cron:
   - último Telegram Tick;
   - último Daily Run;
   - último dispatch.
5. Revisar candidatos:
   - candidatos totales;
   - candidatos fútbol;
   - premium elegibles;
   - sin cuota;
   - sin selección;
   - ya enviados/dedupe.
6. Revisar límites:
   - horario silencioso;
   - mensajes última hora;
   - mensajes hoy.
7. Revisar Data Memory:
   - últimos registros;
   - errores de memoria.
8. Usar dry-run.
9. Usar preview.
10. Solo si todo está correcto, hacer test controlado.

## Diagnósticos posibles

- `READY_TO_SEND`: hay pick premium listo.
- `NO_CANDIDATES`: no hay picks publicados/candidatos.
- `NO_FOOTBALL_CANDIDATES`: football-only descarta todo.
- `NO_PREMIUM_PICKS`: ningún pick cumple requisitos.
- `ALL_DISCARDED_NO_ODDS`: todos descartados por falta de cuota real.
- `ALL_DISCARDED_LOW_QUALITY`: todos descartados por baja calidad/score.
- `ALL_ALREADY_SENT`: dedupe detecta que ya se envió.
- `BLOCKED_BY_HOURLY_LIMIT`: límite horario alcanzado.
- `BLOCKED_BY_DAILY_LIMIT`: límite diario alcanzado.
- `BLOCKED_BY_QUIET_HOURS`: horario silencioso activo.
- `MISSING_BOT_TOKEN`: falta token.
- `MISSING_CHAT_ID`: falta canal/chat.
- `TELEGRAM_API_ERROR`: Telegram API falló.
- `DB_ERROR`: problema DB.
- `DATA_MEMORY_ERROR`: problema Data Memory.
- `UNKNOWN_ERROR`: faltan datos para diagnosticar.

## Cómo probar Cron

Sin secret debe devolver 403:

`/api/automation/telegram/tick`

Con secret debe devolver 200:

`/api/automation/telegram/tick?secret=VALOR_REAL`

Lo mismo para:

`/api/automation/daily/run?secret=VALOR_REAL`

## Cómo evitar spam

- No usar `test-send` salvo prueba admin controlada.
- Usar primero dry-run y preview.
- No activar `force` salvo mantenimiento puntual.
- Mantener límites por hora y día.
- No bajar filtros de calidad sin revisar picks.

## Variables necesarias en Render

- `AUTOMATION_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_BOT_USERNAME`
- `ENABLE_TELEGRAM_AUTO=true`
- `AUTO_SEND_TELEGRAM_PICKS=true`
- `AUTO_GENERATE_PICKS=true`
- `SCHEDULER_ENABLED=true`
- `DAILY_AUTOMATION_ENABLED=true`
- `DB_PATH=/data/database.db`

## Si Telegram no envía

- Si dice `MISSING_BOT_TOKEN`: configurar token.
- Si dice `MISSING_CHAT_ID`: configurar canal/chat.
- Si dice `NO_CANDIDATES`: ejecutar Daily Automation y revisar picks.
- Si dice `ALL_DISCARDED_NO_ODDS`: revisar cuotas.
- Si dice `BLOCKED_BY_QUIET_HOURS`: esperar fuera de silencio.
- Si dice `BLOCKED_BY_DAILY_LIMIT`: no es fallo, es límite anti-spam.
- Si dice `ALL_ALREADY_SENT`: revisar dedupe y si aparecieron picks nuevos.
- Si dice `TELEGRAM_API_ERROR`: revisar permisos del bot en canal.
