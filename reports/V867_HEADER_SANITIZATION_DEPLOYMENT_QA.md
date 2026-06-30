# V867 header sanitization deployment QA

## Validado localmente
- `sanitize_http_header_value` existe.
- `sanitize_runtime_error_value` existe.
- `/api/runtime-version` sanea `runtime_stability.last_error`.
- Checks V863 y V866 de cabecera pasan localmente.

## Validado en Render real
Render devuelve `last_error` como diagnóstico seguro:
`Invalid header value b'386760cfa00b37f98d680113043f9768'`.

No se observó `\n` ni `\r` en el valor expuesto por `/api/runtime-version`.

## Criterio
- El error no se oculta.
- El error no se convierte en header peligroso.
- No se exponen secretos.
- No se tocaron variables de entorno.
