# V714 Telegram SHARK Client Polish Final

## Objetivo

Pulir Telegram, SHARK AI, combinadas, horarios, nombres deportivos en castellano y experiencia cliente sin rehacer el proyecto ni tocar el flujo estable de Render Cron.

## Cambios Principales

- Actualizada versión a `V714_TELEGRAM_SHARK_CLIENT_POLISH_FINAL`.
- Reforzado motor central de localización deportiva.
- Añadida traducción central de mercados: Local, Visitante, Empate, Más de, Menos de, Ambos equipos marcan, Doble oportunidad, Ganador del partido, Hándicap y Total.
- Añadido formato horario premium en Europe/Madrid: Hoy, Mañana y día de semana con hora.
- Mejoradas respuestas SHARK con hora contextual y mercado en castellano.
- Endurecido filtro de picks automáticos para Telegram:
  - no enviar partidos antiguos.
  - no enviar picks sin cuota real.
  - no enviar selecciones pendientes o tipo “esperar cuota”.
  - mantener dedupe por destino.
- Mejorado diagnóstico admin de Telegram con salud de auto picks:
  - candidatos.
  - enviables.
  - descartados.
  - motivos de descarte.
  - faltan cuotas.
  - faltan escudos.
  - faltan horarios.

## Flujo Cron Conservado

Se mantienen:

- `/api/automation/telegram/tick`
- `/api/automation/daily/run`
- `AUTOMATION_SECRET`
- `DB_PATH=/data/database.db`
- cola Telegram
- dedupe
- envíos automáticos

## Validación

Pendiente de entorno:

- datos reales de APIs para certificar volumen de picks.
- Telegram real en producción para verificar recepción final.

La validación técnica local debe comprobar:

- compileall.
- pytest si existe.
- smoke tests de rutas principales.
- endpoints Cron con y sin secret.

