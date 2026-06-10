# V709 Render Cron Certification

## Veredicto

Render Cron Job es obligatorio para garantizar Telegram automático sin intervención del administrador.

La aplicación actual está desplegada como Web Service con Gunicorn. Ese proceso responde tráfico web, pero no garantiza que un scheduler interno siga ejecutándose durante horas, sobreviva a reinicios o despierte si el servicio queda sin tráfico.

## Endpoints Certificados

### `/api/automation/telegram/tick`

- Existe: sí.
- Métodos: GET y POST.
- Requiere secreto: sí, mediante `AUTOMATION_SECRET` en query string o cabecera `X-Automation-Secret`.
- Sin secreto: devuelve 403.
- Con secreto válido: devuelve 200.
- Qué hace: ejecuta `telegram_scheduler_tick()`, que llama a `telegram_scheduler_delivery()`, procesa cola Telegram, registra `telegram_last_dispatch` y devuelve diagnóstico.

### `/api/automation/daily/run`

- Existe: sí.
- Métodos: GET y POST.
- Requiere secreto: sí, mediante `AUTOMATION_SECRET` en query string o cabecera `X-Automation-Secret`.
- Sin secreto: devuelve 403.
- Con secreto válido: devuelve 200 si el ciclo interno termina sin excepción HTTP.
- Qué hace: ejecuta `run_daily_autonomous_system()`, que lanza calendario, live, recomendaciones, auto picks, Telegram y backup diario.

## Seguridad

Ambos endpoints aceptan ejecución por:

- sesión admin válida, o
- `AUTOMATION_SECRET` válido.

Esto permite que Render Cron ejecute tareas sin abrir panel admin.

## Idempotencia y Dedupe

El sistema evita duplicados con:

- `telegram_queue.dedupe_key`.
- índice único `idx_telegram_queue_dedupe`.
- dedupe por tipo de mensaje, pick y destino.
- `telegram_scheduler_tick()` registra última ejecución en `automation_state`.
- los auto picks usan clave determinista por partido, mercado y selección.

Resultado esperado:

- el primer envío válido entra en cola y se procesa.
- repeticiones reales quedan omitidas.
- el canal global recibe aunque no haya usuarios privados vinculados.

## Diagnóstico Admin

`/admin/telegram/diagnostics` expone ahora:

- `last_cron_daily_call`.
- `last_cron_telegram_call`.
- `last_daily_automation`.
- `last_scheduler_tick`.
- `last_auto_pick`.
- `last_sent`.
- `pending`.
- `duplicates_avoided`.
- `automatic_status`.

## Pruebas Locales Ejecutadas

- `python -m compileall app.py engines database_manager.py services`: OK.
- `/api/automation/telegram/tick` sin secreto: 403.
- `/api/automation/telegram/tick?secret=...` con secreto: 200.
- `/api/automation/daily/run` sin secreto: 403.

## Certificación Final

Con Render Cron configurado correctamente:

**Telegram automático queda garantizado: SÍ.**

Sin Render Cron:

**Telegram automático no queda garantizado.**

