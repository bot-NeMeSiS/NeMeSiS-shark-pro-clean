# V752 Telegram Full Auto Artillery Production Certification

## Estado inicial

La base real del proyecto era `V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE`. El runner de Render Cron ya existía, el endpoint `/api/automation/telegram/tick` ya respondía con secret válido y el envío manual a Telegram ya estaba separado del flujo automático.

El punto débil era de trazabilidad y precisión: `NO_DUE_JOBS` podía confundirse con fallo, el diagnóstico no exponía suficientes contadores del último tick, los descartes de picks no estaban normalizados para producción y la llave de deduplicación de auto-picks podía ser demasiado genérica para distinguir pick, partido, mercado, destino, fecha Madrid y origen.

## Qué ya funcionaba

- Render Cron puede ejecutar `python tools/render_cron_telegram_tick.py`.
- El endpoint `/api/automation/telegram/tick` valida `AUTOMATION_SECRET`.
- Telegram manual usa `source=manual_admin`.
- Telegram automático usa `source=automatic_cron`.
- El builder V751 de picks premium sigue activo en `engines/telegram_delivery_engine.py`.
- Las horas visibles de Telegram pasan por helpers de Europe/Madrid.
- La cola `telegram_queue` conserva estados `pending`, `sent`, `failed` y metadatos de origen.

## Qué se reforzó en V752

- `APP_VERSION` y `VERSION.txt` quedan alineados en `V752_TELEGRAM_FULL_AUTO_ARTILLERY_PRODUCTION_CERTIFICATION`.
- El endpoint Cron devuelve estados compactos más claros: `SENT`, `NO_DUE_JOBS`, `QUEUE_EMPTY`, `NO_ELIGIBLE_PICKS`, `OUTSIDE_PRO_WINDOW`, `NO_LIVE_ALERTS`, `DUPLICATE_ALREADY_SENT`, `NO_DESTINATION` o errores reales.
- La respuesta compacta incluye `cron_status`, `discard_reasons` normalizados y `last_delivery_id` cuando hay envío.
- Los descartes de candidatos se normalizan a códigos operativos como `MISSING_ODDS`, `MISSING_MARKET`, `NOT_TELEGRAM_ELIGIBLE`, `OLD_MATCH`, `OUTSIDE_PRO_WINDOW` y `NO_DESTINATION`.
- La deduplicación admite la forma profesional:
  `telegram:<source>:<message_type>:<pick_id>:<match_id>:<market>:<destination>:<madrid_date>`.
- Los auto-picks usan dedupe con `source=automatic_cron`, `pick_id`, `match_id`, `market`, destino y fecha Madrid.
- El Command Center muestra último tick, último resultado, enviados, saltados, fallidos, procesados, encolados, `last_delivery_id` y motivos de no envío.
- El runner de Render Cron mantiene secrets ocultos e identifica la llamada como `NeMeSiS-SHARK-PRO-Render-Cron/752`.

## Flujo automático real

1. Render Cron ejecuta `python tools/render_cron_telegram_tick.py`.
2. El runner lee `PUBLIC_BASE_URL` y `AUTOMATION_SECRET`.
3. El runner llama a `/api/automation/telegram/tick?secret=...`.
4. Flask valida el secret mediante `automation_secret_valid()`.
5. `automation_cron_result()` registra la llamada y ejecuta `telegram_scheduler_tick()`.
6. `telegram_scheduler_tick()` llama a `telegram_scheduler_delivery()`.
7. El scheduler revisa resumen diario, auto-picks, picks diarios, live alerts y cola.
8. `enqueue_auto_pick_alerts()` filtra picks candidatos y encola mensajes con `source=automatic_cron`.
9. `process_premium_telegram_queue()` envía con `telegram_send_http()`, marca `sent` o `failed`, guarda `sent_at_madrid` y registra memoria.
10. Si no hay trabajo, el endpoint devuelve estado controlado y motivos claros.

## Diagnóstico de no envío

- `NO_DUE_JOBS`: Cron despertó la app, pero no tocaba enviar.
- `QUEUE_EMPTY`: la cola no tenía elementos procesables.
- `NO_ELIGIBLE_PICKS`: había revisión, pero ningún pick pasaba filtros.
- `OUTSIDE_PRO_WINDOW`: el envío está fuera de ventana profesional.
- `NO_LIVE_ALERTS`: no hay live alert real o está desactivada.
- `DUPLICATE_ALREADY_SENT`: dedupe evitó repetir mensaje.
- `NO_DESTINATION`: no hay canal global ni privados elegibles.

Estos estados no son fallo de Telegram.

## Diagnóstico de envío real

Cuando se envía al menos un mensaje, el endpoint devuelve:

- `status=SENT`
- `sent_count > 0`
- `last_delivery_id`
- `state_saved=true`

Además, `/admin/telegram/command-center` muestra el último envío automático y el detalle del último tick.

## Madrid Time

Los mensajes premium mantienen `format_telegram_match_time_madrid()` y el Cron expone `now_madrid`, `next_run_madrid` y `sent_at_madrid`. La validación local comprueba que el mensaje mockeado contiene hora Madrid y no depende de ISO UTC crudo.

## Validación local sin spam

Se añadió `tools/check_v752_telegram_full_auto_artillery.py`.

El check valida:

- versión V752,
- endpoint con 403 sin secret,
- endpoint con 200 con secret,
- runner sin exposición de secret,
- builder ultra pro,
- dedupe específico,
- panel con últimos ticks y descartes,
- documentación environment,
- flujo funcional con DB temporal y `telegram_send_http` mockeado,
- primer envío mock `sent=1`,
- segundo tick sin duplicar.

## Limitación honesta

No se envió Telegram real durante esta validación para evitar spam. La prueba real de producción sigue siendo esperar a un pick candidato real o crear uno válido y confirmar en Render:

- `status=SENT`,
- `sent_count > 0`,
- `last_delivery_id`,
- mensaje recibido en Telegram.

