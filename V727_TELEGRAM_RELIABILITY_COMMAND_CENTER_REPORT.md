# V727 Telegram Reliability Command Center Report

## Objetivo

V727 convierte Telegram en un flujo diagnosticable y controlado. No cambia secrets, no fuerza envíos automáticos y no modifica el contrato de Render Cron. El objetivo es saber por qué Telegram no envía:

- Cron no ejecutado.
- Cron ejecutado sin candidatos.
- Picks descartados por calidad, cuota, selección, deporte o partido inválido.
- Bloqueo por horario silencioso.
- Bloqueo por límite horario o diario.
- Dedupe ya enviado.
- Falta de configuración.
- Error Telegram API.
- Error Data Memory o DB.

## Archivos revisados

- `app.py`
- `engines/telegram_delivery_engine.py`
- `engines/telegram_autonomous_delivery_engine.py`
- `engines/telegram_sport_filter_engine.py`
- `engines/data_memory_engine.py`
- `engines/picks_quality_engine.py`
- `engines/spanish_localization_engine.py`
- `engines/madrid_time_engine.py`
- `templates/admin_telegram.html`
- `tools/smoke_check.py`
- `tools/validate_release.py`
- `tools/nemesis_daily_codex.py`
- tests relacionados con Telegram.

## Flujo real detectado

1. Render Cron llama a `/api/automation/telegram/tick?secret=...` o `/api/automation/daily/run?secret=...`.
2. La app valida `AUTOMATION_SECRET`.
3. El endpoint registra estado de Cron en `automation_state`.
4. `telegram_scheduler_tick()` ejecuta `telegram_scheduler_delivery()`.
5. Según settings y hora Madrid, se intentan encolar:
   - partidos diarios;
   - picks diarios;
   - auto picks;
   - alertas live.
6. `process_premium_telegram_queue()` procesa `telegram_queue`.
7. `telegram_send_http()` llama a Telegram API.
8. La cola queda `sent`, `failed`, `skipped` o pendiente.
9. Los envíos se registran en `telegram_logs`, `telegram_deliveries` y Data Memory si está disponible.

## Puntos donde puede detenerse

- Falta `TELEGRAM_BOT_TOKEN`.
- Falta `TELEGRAM_CHAT_ID`.
- Falta `AUTOMATION_SECRET` o Cron llama sin secret.
- `ENABLE_TELEGRAM_AUTO` / `AUTO_SEND_TELEGRAM_PICKS` desactivados y settings internos apagados.
- `auto_daily_picks` desactivado.
- Horario silencioso activo.
- Ventana de picks fuera de horario.
- No hay picks publicados.
- Picks sin cuota real.
- Picks sin selección clara.
- Picks no fútbol bloqueados por `football_only`.
- Picks de baja calidad o score insuficiente.
- Dedupe ya existe para el pick/día/destino.
- Límite horario o diario alcanzado.
- Error de permisos del bot en Telegram.
- Error DB/Data Memory.

## Qué se corrigió

- Se añadió `engines/telegram_reliability_engine.py`.
- Se añadió `/admin/telegram/command-center`.
- Se añadieron endpoints admin seguros:
  - `/api/admin/telegram/status`
  - `/api/admin/telegram/dry-run`
  - `/api/admin/telegram/preview-next`
  - `/api/admin/telegram/test-send`
- Se añadió `tools/check_telegram_reliability.py`.
- Se añadió `tests/test_v727_telegram_reliability.py`.
- Se actualizó `APP_VERSION` y `VERSION.txt`.
- Se actualizó el builder para incluir entregables V727.

## Qué no se tocó

- No se modificaron secrets.
- No se cambió `DB_PATH=/data/database.db` para producción.
- No se rompió `AUTOMATION_SECRET`.
- No se cambió el envío manual existente.
- No se eliminó Telegram football-only.
- No se cambió calibración PRO de forma agresiva.
- No se alteró Render Cron.

## Por qué no llega Telegram desde las 12:00

Desde el entorno local no se puede determinar el motivo exacto de producción porque no están disponibles:

- variables reales Render;
- base persistente `/data/database.db`;
- logs reales de Render;
- cola real de producción;
- estado real de `automation_state`.

V727 deja el diagnóstico listo para verlo en producción. El Command Center indicará si el bloqueo real es configuración, Cron, límites, horario silencioso, falta de candidatos, descartes, dedupe, Telegram API o Data Memory.

## Cómo probar sin spam

1. Entrar como admin.
2. Abrir `/admin/telegram/command-center`.
3. Revisar estado actual y explicación.
4. Abrir `/api/admin/telegram/dry-run`.
5. Abrir `/api/admin/telegram/preview-next`.
6. Solo si hace falta, pulsar el test controlado desde Command Center o hacer `POST /api/admin/telegram/test-send`.

El dry-run y el preview no envían mensajes.

## Validación esperada en Render

- Cron sin secret: 403.
- Cron con secret: 200.
- Command Center admin: 200 con sesión admin.
- Endpoints admin sin sesión: 403 o redirect, nunca 500.
- ZIP limpio: sin `.git`, `.venv`, caches, DB local, logs ni ZIPs internos.
