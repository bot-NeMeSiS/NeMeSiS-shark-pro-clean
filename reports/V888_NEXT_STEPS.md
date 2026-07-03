# V888 Next Steps

## Accion inmediata

1. Desplegar el ZIP V888 en el repo/raiz que Render usa realmente.
2. Ejecutar `Clear build cache & deploy` en Render.
3. Consultar `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
4. Confirmar que devuelve `V888_REAL_ERRORS_SWEEP_TELEGRAM_MATCHES_PICKS_NAV_SENTINEL_FINAL`.

## Validacion despues del deploy

- Probar `/api/automation/telegram/tick` con secret real solo en modo autorizado/dry-run.
- Confirmar que no reaparece `QUEUE_SKIPPED is not defined`.
- Confirmar que `/favicon.ico` responde sin 404.
- Revisar que Render ya no sirve V883.
- Revisar `last_error`, `static_app_css_hash`, `openai_configured`, `team_logo_cache_count` y `league_logo_cache_count`.

## QA visual pendiente

- Ejecutar browser QA real PC y movil.
- Validar no scroll horizontal.
- Revisar `/app`, `/partidos`, `/live`, `/picks`, `/shark`, `/telegram`, `/profile` y admin.
- No declarar pixel-perfect hasta tener capturas reales.

## No hacer sin autorizacion

- No enviar Telegram real.
- No tocar pagos reales.
- No hacer sync masivo de APIs.
- No tocar secretos.
- No borrar DB, usuarios ni sesiones.
