# V873 Invalid header root cause fix

## Hallazgo real

Render V871 expone `last_error` con texto `Invalid header value ...`. El valor parece venir de estado persistido del proveedor API-SPORTS/API-Football, no de CSS cache busting ni ETag activo.

## Causa probable

- `engines/api_sports_provider_engine.py` leía errores desde tablas de sync y devolvía el texto crudo.
- `app.py` saneaba el runtime visual, pero la causa persistida podía seguir apareciendo como error activo.

## Corrección V873

- Se añadió `sanitize_provider_error()` en `engines/api_sports_provider_engine.py`.
- `get_api_sports_status()` sanea errores leídos de DB y excepciones antes de devolver runtime/admin.
- `app.py` añade `runtime_error_state()` para distinguir:
  - `Sin errores registrados`;
  - `Histórico saneado`;
  - `Revisar`.
- `/api/runtime-version` expone `last_error_state` sin bytes crudos.

## Validación esperada tras deploy

Producción V873 debe dejar de exponer `Invalid header value b'...'` como texto crudo. Si aparece de nuevo, revisar qué job o provider vuelve a persistir el error.
