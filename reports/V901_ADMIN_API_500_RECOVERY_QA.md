# V901 Admin API 500 Recovery QA

## Endpoint corregido

`/api/admin/continuous-sentinel/run`

## Comportamiento esperado

- Sin sesion admin: JSON `403`.
- Con sesion admin y `dry_run=1`: JSON `200`.
- Si el ciclo interno falla: JSON seguro con `ok=false`, no HTML blanco.
- No se exponen secretos ni tracebacks.
- No ejecuta acciones peligrosas.

## Validacion local

El check V901 simula un fallo interno sustituyendo temporalmente el runner del ciclo por una excepcion controlada. Resultado:

- status `200`;
- JSON seguro;
- `error=continuous_sentinel_run_failed`;
- `safe_message` presente;
- sin traceback visible.

## Incidencia Sentinel

Cuando hay fallo, se intenta crear una incidencia deduplicable:

- area: `admin_api`;
- severity: `critical`;
- route: `/api/admin/continuous-sentinel/run`;
- evidence: tipo de excepcion saneado;
- prompt Codex seguro.
