# V901 Admin Continuous Sentinel API Layout Recovery Report

## Version

`V901_ADMIN_CONTINUOUS_SENTINEL_API_LAYOUT_RECOVERY_FINAL`

## Causa probable

La pantalla admin de Continuous SHARK Sentinel tenia acciones construidas como enlaces directos a endpoints API:

`/api/admin/continuous-sentinel/run?mode=client&dry_run=1`

Al pulsar, el navegador abandonaba el panel admin y abria el endpoint como pagina. Si el ciclo interno lanzaba una excepcion, Flask terminaba mostrando una pantalla de error en vez de una respuesta controlada dentro del panel.

## Correccion aplicada

- `/api/admin/continuous-sentinel/run` acepta `GET`/`POST`, normaliza `mode`, fuerza `dry_run` seguro por defecto y devuelve JSON controlado.
- Si el ciclo falla, devuelve `ok=false`, `error=continuous_sentinel_run_failed`, `safe_message`, `mode`, `dry_run`, `version` e `issue_created`.
- El fallo se registra como incidencia Sentinel de area `admin_api` sin exponer secretos.
- Los botones del panel ahora son `<button type="button" data-sentinel-run="...">` y ejecutan `fetch` con CSRF.
- El resultado se pinta dentro del panel admin con estado, modo, dry-run, issues, prompts y ultima ejecucion.
- `/admin-login` se limpio: formulario visible, `next` correcto, texto sin mojibake y sin navegacion cliente.
- El rail admin ya no aparece en `/admin-login` sin sesion real.

## Preservado

V896, V897, V898, V899, V900, reference_images, outbox Codex, Madrid Time, DB_PATH, Telegram dedupe/no filler, SHARK safe mode, API guards y navegacion cliente/admin separada.

## Honestidad

Render real consultado durante la ejecucion devolvio V897, no V901. No se hizo push ni deploy automatico.
