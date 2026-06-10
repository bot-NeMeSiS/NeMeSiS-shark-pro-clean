# ChatGPT Continuation Report — V709 Render Cron Certification

## Estado Inicial

El envío manual de Telegram funcionaba. El canal global podía recibir mensajes y la cola manual procesaba correctamente. El problema pendiente era garantizar que los picks automáticos se enviaran sin que el administrador pulsara botones.

La aplicación estaba configurada como Render Web Service con Gunicorn, no como worker persistente ni Cron Job.

## Cambios Realizados

- Se certificaron los endpoints reales de automatización:
  - `/api/automation/telegram/tick`
  - `/api/automation/daily/run`
- Se verificó que ambos requieren `AUTOMATION_SECRET`.
- Se confirmó que el endpoint de Telegram Cron devuelve 200 con secreto válido.
- Se añadió trazabilidad explícita de última llamada Cron:
  - `last_cron_daily_call`
  - `last_cron_telegram_call`
- Se documentó la guía exacta de despliegue Render Cron.

## Veredicto

Render Cron Job es obligatorio.

El scheduler interno no es suficiente para garantizar ejecución autónoma en producción, porque Render Web Service con Gunicorn no garantiza ciclos de fondo durante horas, ni persistencia de threads ante reinicios, reposo o reciclado de workers.

## Estado Telegram

Telegram manual: funciona.

Telegram canal: funciona.

Telegram privado: soportado por código, requiere usuario vinculado real para certificación final.

Telegram automático: preparado por código.

Telegram automático sin admin: garantizado solo con Render Cron configurado.

## Qué Falta

Crear en Render:

Cron 1:

`Telegram Scheduler`

Cada 15 minutos:

`https://nemesis-shark-pro.onrender.com/api/automation/telegram/tick?secret=TU_AUTOMATION_SECRET`

Cron 2:

`Daily Automation`

Cada hora o diario:

`https://nemesis-shark-pro.onrender.com/api/automation/daily/run?secret=TU_AUTOMATION_SECRET`

## Certificación Final

Con Cron configurado:

Telegram automático queda garantizado.

Sin Cron configurado:

Telegram automático no queda garantizado.

## Próximo Paso

Configurar los dos Cron Jobs en Render y verificar `/admin/telegram/diagnostics` tras la primera ejecución.

