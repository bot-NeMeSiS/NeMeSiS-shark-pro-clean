# V901 Continuous Sentinel Buttons Fetch QA

## Antes

Los botones `Quick cycle`, `Client cycle`, `Admin cycle` y `Visual cycle` navegaban directamente a:

`/api/admin/continuous-sentinel/run?...`

Eso podia abrir JSON o una pantalla blanca de error.

## Ahora

Los botones son:

- `<button type="button" data-sentinel-run="quick">`
- `<button type="button" data-sentinel-run="client">`
- `<button type="button" data-sentinel-run="admin">`
- `<button type="button" data-sentinel-run="visual">`

La pagina ejecuta `fetch` con:

- `method: POST`;
- `credentials: same-origin`;
- `Content-Type: application/json`;
- `X-CSRF-Token`;
- `dry_run=true`.

## Resultado visible

El panel muestra:

- estado;
- modo;
- dry-run;
- issues creadas;
- prompts generados;
- ultima ejecucion;
- enlaces a incidencias y outbox Codex.

Si falla la API, el usuario ve:

`No se pudo ejecutar la revision. Se ha registrado el fallo para corregirlo.`
