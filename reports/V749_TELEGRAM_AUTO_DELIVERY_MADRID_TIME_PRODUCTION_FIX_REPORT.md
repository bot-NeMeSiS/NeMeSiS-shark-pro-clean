# V749 Telegram Auto Delivery Madrid Time Production Fix

## Estado inicial

La versión base era `V748_ADMIN_CLIENT_TELEGRAM_SECURITY_PRODUCTION_HOTFIX`. El envío manual de Telegram funcionaba: token, chat/canal, bot, cola y procesamiento manual estaban operativos.

El problema real estaba en el automático: Render Web Service no garantiza un scheduler interno vivo y, además, el flujo dependía demasiado de ajustes internos (`telegram_settings.auto_daily_picks`) aunque las variables Render de automático estuvieran activas. Esto podía dejar el tick Cron en estado aparentemente correcto, pero sin encolar picks automáticos.

## Causa raíz

Manual y automático no estaban diferenciados con suficiente claridad. Los botones admin usaban encolado/procesado manual y podían demostrar conectividad, pero eso no certificaba que Render Cron estuviera llamando al endpoint automático.

Además:

- El tick automático podía no generar picks si `auto_daily_picks` estaba desactivado en tabla, aunque `ENABLE_TELEGRAM_AUTO` o `AUTO_SEND_TELEGRAM_PICKS` estuvieran activos.
- El JSON del Cron podía responder de forma demasiado compacta sin explicar si no había trabajos vencidos, cola vacía o candidatos descartados.
- Algunas pruebas admin podían quedar clasificadas como automáticas por defecto.
- Los builders Telegram no tenían un helper específico que interpretara fecha/hora manual como hora Madrid sin desplazarla.

## Cambios aplicados

- Versión actualizada a `V749_TELEGRAM_AUTO_DELIVERY_MADRID_TIME_PRODUCTION_FIX`.
- Añadido helper central `format_telegram_match_time_madrid(match)` en `engines/madrid_time_engine.py`.
- Los builders Telegram usan el helper Madrid para evitar mostrar UTC crudo o desplazar horas manuales.
- El scheduler Telegram respeta variables Render nuevas y existentes:
  - `ENABLE_TELEGRAM_AUTO`
  - `ENABLE_TELEGRAM_AUTOMATION`
  - `AUTO_SEND_TELEGRAM_PICKS`
  - `TELEGRAM_AUTO_SEND_ENABLED`
- Si las variables de entorno activan automático, el tick puede ejecutar daily matches/picks aunque la tabla de settings no tenga `auto_daily_picks` activado.
- La cola y memoria Telegram añaden trazabilidad:
  - `source`
  - `trigger_type`
  - `auto_job_key`
  - `sent_at_madrid`
- Los botones manuales se registran como `source=manual_admin`.
- Los envíos Cron se registran como `source=automatic_cron`.
- `/api/automation/telegram/tick` devuelve JSON con:
  - `automation_enabled`
  - `telegram_ready`
  - `now_madrid`
  - `next_run_madrid`
  - `due_jobs`
  - `sent_count`
  - `skipped_count`
  - `discard_reasons`
  - `automation_source=cron`
  - estados claros como `QUEUE_EMPTY`, `NO_DUE_JOBS`, `NO_SENDABLE_ITEMS` o `QUEUE_PROCESSED`.
- `/admin/telegram/diagnostics` deja de mostrar JSON crudo y abre el Command Center visual.
- Command Center muestra:
  - último tick automático,
  - próximo tick esperado,
  - último envío automático,
  - último envío manual,
  - fuente de automatización,
  - aviso `MANUAL_OK_AUTO_NOT_RUNNING` cuando aplica.

## Render Cron

El endpoint oficial queda:

`/api/automation/telegram/tick?secret=AUTOMATION_SECRET`

Sin secret devuelve `403`.

Con secret válido devuelve `200` y ejecuta el flujo automático sin sesión admin.

## Madrid Time

Reglas aplicadas:

- ISO con `Z` u offset explícito: se convierte a Europe/Madrid.
- `match_date + match_time` manual: se interpreta como hora local Madrid y no se desplaza.
- El mensaje de prueba admin muestra hora Madrid.
- Los picks, resúmenes y partidos Telegram pasan por el helper central.

## Anti spam y dedupe

La dedupe key conserva:

- tipo de mensaje,
- fecha/pick,
- destino.

El segundo tick Cron normal no reenvía el mismo pick ni el mismo resumen al mismo destino. `force=1` sigue siendo una herramienta admin y puede forzar acciones controladas.

## Validaciones locales realizadas

- `python -m compileall -q app.py engines tools`: OK.
- `tools/check_v749_telegram_auto_delivery_madrid_time.py`: OK.
- `tools/check_v748_admin_client_telegram_security_production_hotfix.py`: OK heredado.
- `tools/check_madrid_times.py`: OK.
- Smoke funcional con DB temporal y Telegram mock:
  - Cron sin secret: `403`.
  - Cron con secret: `200`.
  - Primer tick sin force: encola/envía mediante mock.
  - Segundo tick sin force: no duplica por dedupe.
  - `source=automatic_cron` y `sent_at_madrid` quedan registrados.

## Pendiente en producción real

No se hizo envío real a Telegram desde el entorno local para evitar spam.

La certificación final real consiste en:

1. Configurar Render Cron con la URL exacta.
2. Confirmar que `/admin/telegram/command-center` muestra `last_automation_tick_madrid`.
3. Confirmar que el canal recibe un pick/resumen real cuando haya datos elegibles.
4. Confirmar que el segundo tick no duplica.

